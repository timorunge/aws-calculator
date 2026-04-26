"""MCP server for the AWS Pricing Calculator."""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from aws_calculator import __version__
from aws_calculator.core.catalog import ManifestClient
from aws_calculator.core.client import EstimateClient
from aws_calculator.core.discovery import (
    CALCULATOR_ESC_URL,
    CALCULATOR_GLOBAL_URL,
    discover_estimate_api_url,
)
from aws_calculator.core.save import SaveClient
from aws_calculator.tools import catalog, estimate, read

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

        api_urls: dict[str, str] = {}
        if global_api_url:
            api_urls[CALCULATOR_GLOBAL_URL] = global_api_url
        if esc_api_url:
            api_urls[CALCULATOR_ESC_URL] = esc_api_url

        yield {
            "client": EstimateClient(http_client, api_urls),
            "catalog": ManifestClient(http_client),
            "saver": SaveClient(http_client),
            "builders": {},
        }


mcp = FastMCP(
    "aws_calculator_mcp_server",
    lifespan=app_lifespan,
    instructions=(
        "AWS Pricing Calculator MCP server.\n\n"
        "Partitions: aws (calculator.aws), aws-esc "
        "(pricing.calculator.aws.eu), aws-iso, aws-iso-b.\n\n"
        "Read: get_estimate > list_services > get_service_detail > "
        "summarize_estimate.\n"
        "Write: search_services > get_service_fields > "
        "create_estimate > add_service > export_estimate.\n\n"
        "add_service JSON: [{serviceCode, region, "
        "calculationComponents, description?, group?}]."
    ),
)

read.register(mcp)
catalog.register(mcp)
estimate.register(mcp)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    mcp.run()


if __name__ == "__main__":
    main()
