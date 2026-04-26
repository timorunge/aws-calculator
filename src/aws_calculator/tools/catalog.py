"""Catalog MCP tools for searching services and discovering config fields."""

from __future__ import annotations

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from aws_calculator.core.catalog import CatalogError
from aws_calculator.core.formatters import format_search_results, format_service_fields
from aws_calculator.core.types import GetServiceFieldsInput, SearchServicesInput
from aws_calculator.tools._ctx import get_catalog

_CATALOG_ANNOTATIONS = ToolAnnotations(
    title=None,
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="aws_calculator_search_services", annotations=_CATALOG_ANNOTATIONS)
    async def aws_calculator_search_services(params: SearchServicesInput, ctx: Context) -> str:
        """Search service catalog. Returns keys for get_service_fields and add_service."""
        try:
            catalog = get_catalog(ctx)
            manifest = await catalog.load_manifest(params.partition)
            results = catalog.search_services(manifest, params.query, params.max_results)
            return format_search_results(results, params.format)
        except CatalogError as e:
            return f"error: {e}"

    @mcp.tool(name="aws_calculator_get_service_fields", annotations=_CATALOG_ANNOTATIONS)
    async def aws_calculator_get_service_fields(params: GetServiceFieldsInput, ctx: Context) -> str:
        """Get calculationComponents fields (IDs, types, options) for add_service."""
        try:
            catalog = get_catalog(ctx)
            manifest = await catalog.load_manifest(params.partition)
            keys = [k.strip() for k in params.service.split(",") if k.strip()]
            services, errors = await catalog.resolve_fields(manifest, keys, params.partition)
            return format_service_fields(services, errors, params.format)
        except CatalogError as e:
            return f"error: {e}"
