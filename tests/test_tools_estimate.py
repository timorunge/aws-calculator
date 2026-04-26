"""Tests for estimate MCP tools (create, add_service, export)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import httpx
from mcp.server.fastmcp import Context
from mcp.shared.context import RequestContext

from aws_calculator.core.builder import EstimateBuilder
from aws_calculator.core.catalog import ManifestClient
from aws_calculator.core.save import SaveClient
from aws_calculator.core.types import (
    AddServiceInput,
    CreateEstimateInput,
    ExportEstimateInput,
    SaveResult,
)
from aws_calculator.server import mcp
from tests.conftest import get_tool_fn, make_catalog_transport

FAKE_MANIFEST = {
    "awsServices": [
        {"key": "aWSLambda", "name": "AWS Lambda", "searchKeywords": []},
    ]
}

FAKE_LAMBDA_DEFINITION = {
    "version": "2.0.0",
    "serviceCode": "aWSLambda",
    "templates": [
        {
            "id": "t1",
            "inputComponents": [
                {"id": "numberOfRequests", "type": "numericInput"},
            ],
        }
    ],
}


def _make_ctx(
    catalog: ManifestClient | None = None,
    saver: SaveClient | AsyncMock | None = None,
    builders: dict | None = None,
) -> Context:
    rc = RequestContext(
        request_id="test",
        meta=None,
        session=None,  # type: ignore[arg-type]
        lifespan_context={
            "client": AsyncMock(),
            "catalog": catalog or AsyncMock(),
            "saver": saver or AsyncMock(),
            "builders": builders if builders is not None else {},
        },
    )
    return Context(request_context=rc, fastmcp=mcp)


class TestCreateEstimate:
    async def test_returns_id_and_name(self) -> None:
        fn = get_tool_fn("aws_calculator_create_estimate")
        builders: dict[str, EstimateBuilder] = {}
        result = await fn(
            CreateEstimateInput(name="Test Estimate"),
            _make_ctx(builders=builders),
        )
        assert "Estimate created" in result
        assert "Test Estimate" in result
        assert len(builders) == 1


class TestAddService:
    async def test_adds_valid_service(self) -> None:
        fn = get_tool_fn("aws_calculator_add_service")
        builders: dict[str, EstimateBuilder] = {}
        builder = EstimateBuilder(name="Test")
        builders[builder.id] = builder

        transport = make_catalog_transport(FAKE_MANIFEST, {"aWSLambda": FAKE_LAMBDA_DEFINITION})
        async with httpx.AsyncClient(transport=transport) as http:
            catalog = ManifestClient(http)
            services_json = json.dumps([{"serviceCode": "aWSLambda", "region": "us-east-1"}])
            result = await fn(
                AddServiceInput(estimate_id=builder.id, services=services_json),
                _make_ctx(catalog=catalog, builders=builders),
            )

        assert "1 added" in result
        assert not builder.is_empty()


class TestExportEstimate:
    async def test_returns_url(self) -> None:
        fn = get_tool_fn("aws_calculator_export_estimate")
        builder = EstimateBuilder()
        builder.add_service("aWSLambda", region="us-east-1")

        saver = AsyncMock(spec=SaveClient)
        saver.save.return_value = SaveResult(
            estimate_id="saved123",
            shareable_url="https://calculator.aws/#/estimate?id=saved123",
        )

        transport = make_catalog_transport(FAKE_MANIFEST, {"aWSLambda": FAKE_LAMBDA_DEFINITION})
        async with httpx.AsyncClient(transport=transport) as http:
            catalog = ManifestClient(http)
            result = await fn(
                ExportEstimateInput(estimate_id=builder.id),
                _make_ctx(catalog=catalog, saver=saver, builders={builder.id: builder}),
            )

        assert "Estimate saved" in result
        assert "saved123" in result
