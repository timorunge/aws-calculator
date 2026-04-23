"""Tests for MCP server tool handlers and lifespan."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from mcp.server.fastmcp import Context
from mcp.shared.context import RequestContext

from aws_calculator.core.client import (
    EstimateClient,
    EstimateFetchError,
)
from aws_calculator.core.discovery import CALCULATOR_ESC_URL, CALCULATOR_GLOBAL_URL
from aws_calculator.core.types import (
    Estimate,
    GetEstimateInput,
    GetServiceDetailInput,
    ListServicesInput,
    SummarizeEstimateInput,
)
from aws_calculator.server import (
    app_lifespan,
    aws_calculator_get_estimate,
    aws_calculator_get_service_detail,
    aws_calculator_list_services,
    aws_calculator_summarize_estimate,
    mcp,
)


def _make_ctx(
    estimate: Estimate | None = None, *, exc: EstimateFetchError | None = None
) -> Context:
    client = AsyncMock(spec=EstimateClient)
    if exc is not None:
        client.get_estimate.side_effect = exc
    else:
        client.get_estimate.return_value = estimate
    rc = RequestContext(
        request_id="test",
        meta=None,
        session=None,  # type: ignore[arg-type]
        lifespan_context={"client": client},
    )
    return Context(request_context=rc, fastmcp=mcp)


class TestGetEstimate:
    async def test_returns_text_overview(self, sample_estimate: Estimate) -> None:
        result = await aws_calculator_get_estimate(
            GetEstimateInput(url_or_id="abc123"), _make_ctx(sample_estimate)
        )
        assert "Serverless API" in result
        assert "USD 29.58" in result

    async def test_fetch_error_returned_as_string(self) -> None:
        result = await aws_calculator_get_estimate(
            GetEstimateInput(url_or_id="abc123"),
            _make_ctx(exc=EstimateFetchError("network failure")),
        )
        assert result == "error: network failure"


class TestListServices:
    async def test_returns_all_services(self, startup_saas_estimate: Estimate) -> None:
        result = await aws_calculator_list_services(
            ListServicesInput(url_or_id="abc123"), _make_ctx(startup_saas_estimate)
        )
        assert "Amazon EC2" in result
        assert "Amazon RDS for PostgreSQL" in result

    async def test_group_filter_case_insensitive_substring(
        self, startup_saas_estimate: Estimate
    ) -> None:
        result = await aws_calculator_list_services(
            ListServicesInput(url_or_id="abc123", group="DATA"),
            _make_ctx(startup_saas_estimate),
        )
        assert "Amazon RDS for PostgreSQL" in result
        assert "Amazon EC2" not in result

    async def test_no_matching_group_includes_group_in_message(
        self, sample_estimate: Estimate
    ) -> None:
        result = await aws_calculator_list_services(
            ListServicesInput(url_or_id="abc123", group="nonexistent"),
            _make_ctx(sample_estimate),
        )
        assert "no services found" in result
        assert "nonexistent" in result


class TestGetServiceDetail:
    async def test_returns_service_detail(self, sample_estimate: Estimate) -> None:
        key = "amazonApiGateway-124c6a96-cd94-4c85-a162-6a4a3254d184"
        result = await aws_calculator_get_service_detail(
            GetServiceDetailInput(url_or_id="abc123", service_key=key),
            _make_ctx(sample_estimate),
        )
        assert "Amazon API Gateway" in result

    async def test_unknown_key_shows_available_keys(self, sample_estimate: Estimate) -> None:
        result = await aws_calculator_get_service_detail(
            GetServiceDetailInput(url_or_id="abc123", service_key="bad-key"),
            _make_ctx(sample_estimate),
        )
        assert "error: service key 'bad-key' not found" in result
        assert "amazonApiGateway" in result
        assert "and" not in result

    async def test_unknown_key_truncates_long_list(
        self, enterprise_data_pipeline_estimate: Estimate
    ) -> None:
        from aws_calculator.server import _MAX_KEYS_IN_ERROR

        result = await aws_calculator_get_service_detail(
            GetServiceDetailInput(url_or_id="abc123", service_key="bad-key"),
            _make_ctx(enterprise_data_pipeline_estimate),
        )
        expected_more = len(enterprise_data_pipeline_estimate.services) - _MAX_KEYS_IN_ERROR
        assert f"and {expected_more} more" in result


class TestSummarizeEstimate:
    async def test_returns_summary(self, startup_saas_estimate: Estimate) -> None:
        result = await aws_calculator_summarize_estimate(
            SummarizeEstimateInput(url_or_id="abc123"), _make_ctx(startup_saas_estimate)
        )
        assert "Startup SaaS Platform" in result
        assert "USD 2,266.05" in result


class TestAppLifespan:
    async def test_yields_client_with_both_api_urls(self) -> None:
        with patch(
            "aws_calculator.server.discover_estimate_api_url",
            new_callable=AsyncMock,
        ) as mock_discover:
            mock_discover.side_effect = [
                "https://global-api.example.com/{estimateKey}",
                "https://esc-api.example.com/{estimateKey}",
            ]
            async with app_lifespan(mcp) as ctx:
                client = ctx["client"]
                assert isinstance(client, EstimateClient)
                assert mock_discover.call_count == 2
                assert CALCULATOR_GLOBAL_URL in client._api_urls
                assert CALCULATOR_ESC_URL in client._api_urls

    async def test_esc_failure_excludes_esc_from_api_urls(self) -> None:
        with patch(
            "aws_calculator.server.discover_estimate_api_url",
            new_callable=AsyncMock,
        ) as mock_discover:
            mock_discover.side_effect = [
                "https://global-api.example.com/{estimateKey}",
                "",  # ESC discovery failed
            ]
            async with app_lifespan(mcp) as ctx:
                client = ctx["client"]
                assert CALCULATOR_GLOBAL_URL in client._api_urls
                assert CALCULATOR_ESC_URL not in client._api_urls
