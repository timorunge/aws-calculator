"""Integration tests that hit the real calculator.aws API."""

from collections.abc import AsyncIterator

import httpx
import pytest

from aws_calculator.core.builder import EstimateBuilder
from aws_calculator.core.catalog import ManifestClient
from aws_calculator.core.client import EstimateClient
from aws_calculator.core.discovery import (
    CALCULATOR_ESC_URL,
    CALCULATOR_GLOBAL_URL,
    discover_estimate_api_url,
)
from aws_calculator.core.save import SaveClient
from aws_calculator.core.types import Partition
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


class TestWriteWorkflowLive:
    async def test_search_build_save(self) -> None:
        async with httpx.AsyncClient(
            headers={"Accept": "application/json", "User-Agent": "aws-calculator-test"}
        ) as http:
            catalog = ManifestClient(http)
            saver = SaveClient(http)

            manifest = await catalog.load_manifest(Partition.AWS)
            results = catalog.search_services(manifest, "lambda", max_results=5)
            assert isinstance(results, list)
            assert len(results) > 0

            svc = catalog.find_service(manifest, "aWSLambda")
            assert svc is not None
            definition = await catalog.fetch_definition(manifest, svc.key, Partition.AWS)
            assert definition is not None
            fields = catalog.extract_fields(definition)
            assert any(f.id == "numberOfRequests" for f in fields)

            builder = EstimateBuilder("Integration Test", Partition.AWS)
            builder.add_service(
                "aWSLambda",
                region="us-east-1",
                calculation_components={"numberOfRequests": "1000000"},
            )
            payload = await builder.build_payload(catalog)
            result = await saver.save(payload, Partition.AWS)

            assert result.estimate_id
            assert "calculator.aws" in result.shareable_url


class TestWriteWorkflowEscLive:
    async def test_esc_build_save(self) -> None:
        async with httpx.AsyncClient(
            headers={"Accept": "application/json", "User-Agent": "aws-calculator-test"}
        ) as http:
            catalog = ManifestClient(http)
            saver = SaveClient(http)

            manifest = await catalog.load_manifest(Partition.AWS_ESC)
            assert len(manifest) > 0

            builder = EstimateBuilder("Integration Test ESC", Partition.AWS_ESC)
            builder.add_service(
                "aWSLambda",
                region="eusc-de-east-1",
                calculation_components={"numberOfRequests": "1000000"},
            )
            payload = await builder.build_payload(catalog)
            result = await saver.save(payload, Partition.AWS_ESC)

            assert result.estimate_id
            assert "pricing.calculator.aws.eu" in result.shareable_url
