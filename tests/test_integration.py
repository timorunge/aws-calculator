"""Integration tests that hit the real calculator.aws API."""

import json
from collections.abc import AsyncIterator

import httpx
import pytest

from aws_calculator.core.client import EstimateClient, EstimateFetchError
from aws_calculator.core.discovery import (
    CALCULATOR_ESC_URL,
    CALCULATOR_GLOBAL_URL,
    discover_estimate_api_url,
)
from aws_calculator.core.formatters import (
    format_estimate_overview,
    format_estimate_summary,
)
from aws_calculator.core.types import ResponseFormat
from tests.conftest import SAMPLE_ESTIMATE_ID

pytestmark = pytest.mark.integration


@pytest.fixture
async def live_client() -> AsyncIterator[EstimateClient]:
    async with httpx.AsyncClient(
        headers={"Accept": "application/json", "User-Agent": "aws-calculator-test"}
    ) as http:
        api_url = await discover_estimate_api_url(http, CALCULATOR_GLOBAL_URL)
        yield EstimateClient(http, {CALCULATOR_GLOBAL_URL: api_url})


class TestDiscoveryLive:
    async def test_discovers_url_from_live_site(self) -> None:
        async with httpx.AsyncClient() as http:
            url = await discover_estimate_api_url(http, CALCULATOR_GLOBAL_URL)
            assert "{estimateKey}" in url
            assert url.startswith("https://")

    async def test_discovers_eu_url_from_live_site(self) -> None:
        async with httpx.AsyncClient() as http:
            url = await discover_estimate_api_url(http, CALCULATOR_ESC_URL)
            assert "{estimateKey}" in url
            assert url.startswith("https://")


class TestFetchEstimateLive:
    async def test_fetch_and_parse(self, live_client: EstimateClient) -> None:
        est = await live_client.get_estimate(SAMPLE_ESTIMATE_ID)
        assert est.name == "My Estimate"
        assert abs(est.total_cost.monthly - 241.21) < 1.0
        assert len(est.services) == 4
        for _key, svc in est.services.items():
            assert svc.service_name is not None
            assert svc.region is not None

    async def test_nonexistent_estimate(self, live_client: EstimateClient) -> None:
        with pytest.raises(EstimateFetchError):
            await live_client.get_estimate("00000000000000000000deadbeefcafe00000000")


class TestFormattersLive:
    async def test_overview_json(self, live_client: EstimateClient) -> None:
        est = await live_client.get_estimate(SAMPLE_ESTIMATE_ID)
        result = format_estimate_overview(est, ResponseFormat.JSON)
        data = json.loads(result)
        assert data["name"] == "My Estimate"
        assert data["service_count"] == 4
        assert data["total_monthly"] > 0

    async def test_summary_text(self, live_client: EstimateClient) -> None:
        est = await live_client.get_estimate(SAMPLE_ESTIMATE_ID)
        result = format_estimate_summary(est, ResponseFormat.TEXT)
        assert "Services by cost:" in result
        assert "Amazon RDS for MySQL" in result
