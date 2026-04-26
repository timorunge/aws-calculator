"""Read-only MCP tools for fetching shared AWS Pricing Calculator estimates."""

from __future__ import annotations

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from aws_calculator.core.client import EstimateFetchError
from aws_calculator.core.formatters import (
    format_estimate_overview,
    format_estimate_summary,
    format_service_detail,
    format_services_list,
)
from aws_calculator.core.types import (
    MAX_KEYS_IN_ERROR,
    GetEstimateInput,
    GetServiceDetailInput,
    ListServicesInput,
    SummarizeEstimateInput,
)
from aws_calculator.tools._ctx import get_client

_READONLY_ANNOTATIONS = ToolAnnotations(
    title=None,
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="aws_calculator_get_estimate", annotations=_READONLY_ANNOTATIONS)
    async def aws_calculator_get_estimate(params: GetEstimateInput, ctx: Context) -> str:
        """Estimate overview: name, costs, service count, metadata."""
        try:
            client = get_client(ctx)
            estimate = await client.get_estimate(params.url_or_id)
            return format_estimate_overview(estimate, params.format)
        except EstimateFetchError as e:
            return f"error: {e}"

    @mcp.tool(name="aws_calculator_list_services", annotations=_READONLY_ANNOTATIONS)
    async def aws_calculator_list_services(params: ListServicesInput, ctx: Context) -> str:
        """List services with costs and config summaries."""
        try:
            client = get_client(ctx)
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
        """Full configuration for one service: all parameters, values, units."""
        try:
            client = get_client(ctx)
            estimate = await client.get_estimate(params.url_or_id)

            service = estimate.services.get(params.service_key)
            if not service:
                available = ", ".join(
                    f"`{k}`" for k in list(estimate.services.keys())[:MAX_KEYS_IN_ERROR]
                )
                n = len(estimate.services)
                more = f" (and {n - MAX_KEYS_IN_ERROR} more)" if n > MAX_KEYS_IN_ERROR else ""
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
    async def aws_calculator_summarize_estimate(
        params: SummarizeEstimateInput, ctx: Context
    ) -> str:
        """Cost breakdown sorted by price with group subtotals."""
        try:
            client = get_client(ctx)
            estimate = await client.get_estimate(params.url_or_id)
            return format_estimate_summary(estimate, params.format)
        except EstimateFetchError as e:
            return f"error: {e}"
