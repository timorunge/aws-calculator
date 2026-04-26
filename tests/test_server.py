"""Tests for MCP server tool handlers and lifespan."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from mcp.server.fastmcp import Context
from mcp.shared.context import RequestContext

from aws_calculator.core.catalog import ManifestClient
from aws_calculator.core.client import (
    EstimateClient,
)
from aws_calculator.core.discovery import CALCULATOR_ESC_URL, CALCULATOR_GLOBAL_URL
from aws_calculator.core.save import SaveClient
from aws_calculator.core.types import (
    Estimate,
    ListServicesInput,
)
from aws_calculator.server import app_lifespan, mcp
from tests.conftest import get_tool_fn


def _make_ctx(estimate: Estimate) -> Context:
    client = AsyncMock(spec=EstimateClient)
    client.get_estimate.return_value = estimate
    rc = RequestContext(
        request_id="test",
        meta=None,
        session=None,  # type: ignore[arg-type]
        lifespan_context={"client": client},
    )
    return Context(request_context=rc, fastmcp=mcp)


class TestListServices:
    async def test_group_filter_case_insensitive_substring(
        self, startup_saas_estimate: Estimate
    ) -> None:
        fn = get_tool_fn("aws_calculator_list_services")
        result = await fn(
            ListServicesInput(url_or_id="abc123", group="DATA"),
            _make_ctx(startup_saas_estimate),
        )
        assert "Amazon RDS for PostgreSQL" in result
        assert "Amazon EC2" not in result


class TestAppLifespan:
    async def test_yields_context_with_all_keys(self) -> None:
        with patch(
            "aws_calculator.server.discover_estimate_api_url",
            new_callable=AsyncMock,
        ) as mock_discover:
            mock_discover.side_effect = [
                "https://global-api.example.com/{estimateKey}",
                "https://esc-api.example.com/{estimateKey}",
            ]
            async with app_lifespan(mcp) as ctx:
                assert isinstance(ctx["client"], EstimateClient)
                assert isinstance(ctx["catalog"], ManifestClient)
                assert isinstance(ctx["saver"], SaveClient)
                assert isinstance(ctx["builders"], dict)
                assert CALCULATOR_GLOBAL_URL in ctx["client"]._api_urls
                assert CALCULATOR_ESC_URL in ctx["client"]._api_urls
