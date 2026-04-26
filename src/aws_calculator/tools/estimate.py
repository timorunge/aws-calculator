"""Estimate MCP tools for creating, populating, and exporting estimates."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from aws_calculator.core.builder import DEFAULT_REGION, EstimateBuilder, EstimateBuildError
from aws_calculator.core.formatters import (
    format_add_service_results,
    format_estimate_created,
    format_export_result,
)
from aws_calculator.core.save import SaveError
from aws_calculator.core.types import (
    AddServiceInput,
    CreateEstimateInput,
    ExportEstimateInput,
    Partition,
    ResponseFormat,
)
from aws_calculator.core.validation import validate_config_keys
from aws_calculator.tools._ctx import get_builders, get_catalog, get_saver

_BUILD_ANNOTATIONS = ToolAnnotations(
    title=None,
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)

_EXPORT_ANNOTATIONS = ToolAnnotations(
    title=None,
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="aws_calculator_create_estimate", annotations=_BUILD_ANNOTATIONS)
    async def aws_calculator_create_estimate(params: CreateEstimateInput, ctx: Context) -> str:
        """Create in-memory estimate. Returns ID for add_service and export_estimate."""
        builder = EstimateBuilder(params.name, params.partition)
        builders = get_builders(ctx)
        builders[builder.id] = builder
        return format_estimate_created(builder.id, builder.name, ResponseFormat.TEXT)

    @mcp.tool(name="aws_calculator_add_service", annotations=_BUILD_ANNOTATIONS)
    async def aws_calculator_add_service(params: AddServiceInput, ctx: Context) -> str:
        """Add services to an estimate. Requires serviceCode and region per entry."""
        builders = get_builders(ctx)
        builder = builders.get(params.estimate_id)
        if builder is None:
            return f"error: estimate '{params.estimate_id}' not found"

        try:
            raw = json.loads(params.services)
        except json.JSONDecodeError as e:
            return f"error: invalid JSON in services field: {e}"

        if isinstance(raw, list):
            entries: list[dict[str, Any]] = raw
        elif isinstance(raw, dict):
            entries = [raw]
        else:
            return "error: 'services' must be a JSON object or array"
        catalog = get_catalog(ctx)
        partition = builder.partition or Partition.AWS

        results: list[dict[str, Any]] = []
        for entry in entries:
            service_code = entry.get("serviceCode")
            region = entry.get("region", DEFAULT_REGION)
            description = entry.get("description", "")
            calc_components: dict[str, Any] = entry.get("calculationComponents", {})
            group = entry.get("group")

            if not service_code:
                results.append(
                    {"service": "(missing)", "status": "error", "error": "no serviceCode"}
                )
                continue

            warning = await validate_config_keys(service_code, calc_components, catalog, partition)
            if warning:
                results.append({"service": service_code, "status": "error", "error": warning})
                continue

            builder.add_service(
                service_code,
                region=region,
                description=description,
                calculation_components=calc_components,
                group=group,
            )
            results.append({"service": service_code, "status": "added"})

        return format_add_service_results(results, ResponseFormat.TEXT)

    @mcp.tool(name="aws_calculator_export_estimate", annotations=_EXPORT_ANNOTATIONS)
    async def aws_calculator_export_estimate(params: ExportEstimateInput, ctx: Context) -> str:
        """Save estimate and return shareable URL."""
        builders = get_builders(ctx)
        builder = builders.get(params.estimate_id)
        if builder is None:
            return f"error: estimate '{params.estimate_id}' not found"

        if builder.is_empty():
            return "error: estimate has no services. use add_service first."

        try:
            catalog = get_catalog(ctx)
            payload = await builder.build_payload(catalog)
            saver = get_saver(ctx)
            partition = builder.partition or Partition.AWS
            result = await saver.save(payload, partition)
            del builders[params.estimate_id]
            return format_export_result(result, params.format)
        except (EstimateBuildError, SaveError) as e:
            return f"error: {e}"
