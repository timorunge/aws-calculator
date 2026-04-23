"""MCP server for reading shared AWS Pricing Calculator estimates."""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from aws_calculator import __version__
from aws_calculator.core import (
    CALCULATOR_ESC_URL,
    CALCULATOR_GLOBAL_URL,
    EstimateClient,
    EstimateFetchError,
    GetEstimateInput,
    GetServiceDetailInput,
    ListServicesInput,
    SummarizeEstimateInput,
    discover_estimate_api_url,
    format_estimate_overview,
    format_estimate_summary,
    format_service_detail,
    format_services_list,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Initialize httpx client and discover estimate API URLs at startup."""
    async with httpx.AsyncClient(
        headers={
            "Accept": "application/json",
            "User-Agent": f"aws-calculator-mcp-server/{__version__}",
        },
    ) as http_client:
        logger.info("Discovering estimate API URLs...")
        global_api_url, esc_api_url = await asyncio.gather(
            discover_estimate_api_url(http_client, CALCULATOR_GLOBAL_URL),
            discover_estimate_api_url(http_client, CALCULATOR_ESC_URL),
        )
        logger.info("Global estimate API: %s", global_api_url)
        if esc_api_url:
            logger.info("ESC estimate API: %s", esc_api_url)
        else:
            logger.warning("ESC estimate API discovery failed; ESC URLs will not be available")

        api_urls = {CALCULATOR_GLOBAL_URL: global_api_url}
        if esc_api_url:
            api_urls[CALCULATOR_ESC_URL] = esc_api_url

        client = EstimateClient(http_client, api_urls)
        yield {"client": client}


mcp = FastMCP(
    "aws_calculator_mcp_server",
    lifespan=app_lifespan,
    instructions=(
        "Read shared AWS Pricing Calculator estimates from calculator.aws or "
        "pricing.calculator.aws.eu URLs. "
        "All tools accept a full URL (https://calculator.aws/#/estimate?id=... "
        "or https://pricing.calculator.aws.eu/#/estimate?id=...) "
        "or a bare estimate ID. Typical workflow: "
        "1) get_estimate for the overview, "
        "2) list_services to see what is in the estimate, "
        "3) get_service_detail for a specific service's configuration, "
        "4) summarize_estimate for a cost breakdown sorted by price."
    ),
)

_MAX_KEYS_IN_ERROR = 5

_READONLY_ANNOTATIONS = ToolAnnotations(
    title=None,
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


def _get_client(ctx: Context) -> EstimateClient:
    return cast(EstimateClient, ctx.request_context.lifespan_context["client"])


@mcp.tool(name="aws_calculator_get_estimate", annotations=_READONLY_ANNOTATIONS)
async def aws_calculator_get_estimate(params: GetEstimateInput, ctx: Context) -> str:
    """Fetch a shared AWS Pricing Calculator estimate by URL or ID."""
    try:
        client = _get_client(ctx)
        estimate = await client.get_estimate(params.url_or_id)
        return format_estimate_overview(estimate, params.format)
    except EstimateFetchError as e:
        return f"error: {e}"


@mcp.tool(name="aws_calculator_list_services", annotations=_READONLY_ANNOTATIONS)
async def aws_calculator_list_services(params: ListServicesInput, ctx: Context) -> str:
    """List all services in a shared AWS Pricing Calculator estimate."""
    try:
        client = _get_client(ctx)
        estimate = await client.get_estimate(params.url_or_id)

        services = estimate.services
        if params.group:
            group_lower = params.group.lower()
            services = {
                k: v for k, v in services.items() if v.group and group_lower in v.group.lower()
            }

        if not services:
            group_msg = f" in group '{params.group}'" if params.group else ""
            return f"no services found{group_msg}."

        return format_services_list(estimate, services, params.format)
    except EstimateFetchError as e:
        return f"error: {e}"


@mcp.tool(name="aws_calculator_get_service_detail", annotations=_READONLY_ANNOTATIONS)
async def aws_calculator_get_service_detail(params: GetServiceDetailInput, ctx: Context) -> str:
    """Get detailed configuration and cost for a specific service in an estimate."""
    try:
        client = _get_client(ctx)
        estimate = await client.get_estimate(params.url_or_id)

        service = estimate.services.get(params.service_key)
        if not service:
            available = ", ".join(
                f"`{k}`" for k in list(estimate.services.keys())[:_MAX_KEYS_IN_ERROR]
            )
            n = len(estimate.services)
            more = f" (and {n - _MAX_KEYS_IN_ERROR} more)" if n > _MAX_KEYS_IN_ERROR else ""
            return (
                f"error: service key '{params.service_key}' not found in estimate. "
                f"available keys: {available}{more}. "
                f"use aws_calculator_list_services to see all service keys."
            )

        return format_service_detail(
            params.service_key, service, params.format, estimate.meta_data.currency
        )
    except EstimateFetchError as e:
        return f"error: {e}"


@mcp.tool(name="aws_calculator_summarize_estimate", annotations=_READONLY_ANNOTATIONS)
async def aws_calculator_summarize_estimate(params: SummarizeEstimateInput, ctx: Context) -> str:
    """Get a cost breakdown summary of a shared AWS Pricing Calculator estimate."""
    try:
        client = _get_client(ctx)
        estimate = await client.get_estimate(params.url_or_id)
        return format_estimate_summary(estimate, params.format)
    except EstimateFetchError as e:
        return f"error: {e}"


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    mcp.run()


if __name__ == "__main__":
    main()
