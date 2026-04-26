"""Shared lifespan-context accessors for MCP tool modules."""

from __future__ import annotations

from typing import cast

from mcp.server.fastmcp import Context

from aws_calculator.core.builder import EstimateBuilder
from aws_calculator.core.catalog import ManifestClient
from aws_calculator.core.client import EstimateClient
from aws_calculator.core.save import SaveClient


def get_client(ctx: Context) -> EstimateClient:
    return cast(EstimateClient, ctx.request_context.lifespan_context["client"])


def get_catalog(ctx: Context) -> ManifestClient:
    return cast(ManifestClient, ctx.request_context.lifespan_context["catalog"])


def get_saver(ctx: Context) -> SaveClient:
    return cast(SaveClient, ctx.request_context.lifespan_context["saver"])


def get_builders(ctx: Context) -> dict[str, EstimateBuilder]:
    return cast(dict[str, EstimateBuilder], ctx.request_context.lifespan_context["builders"])
