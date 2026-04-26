"""Tests for URL routing and EstimateClient."""

import json

import httpx

from aws_calculator.core.client import (
    EstimateClient,
)
from aws_calculator.core.discovery import CALCULATOR_ESC_URL, CALCULATOR_GLOBAL_URL
from tests.conftest import SAMPLE_ESTIMATE_ID, SAMPLE_ESTIMATE_JSON

_REDISCOVERY_HTML = '<html><script src="assets/config.js"></script></html>'
_REDISCOVERY_CONFIG_JS = "window.PRC_CONFIG = {};".format(
    json.dumps(
        {
            "RESOURCES": {
                "GET_SAVED_ESTIMATES_API": "https://d3knqfixx3sbls.cloudfront.net/{estimateKey}"
            }
        }
    )
)


class TestEstimateClient:
    async def test_fetch_and_cache(self) -> None:
        call_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json=SAMPLE_ESTIMATE_JSON)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as http:
            client = EstimateClient(
                http, {CALCULATOR_GLOBAL_URL: "https://example.com/{estimateKey}"}
            )
            est1 = await client.get_estimate(SAMPLE_ESTIMATE_ID)
            assert est1.name == "Serverless API"
            assert est1.total_cost.monthly == 29.58
            assert len(est1.services) == 2

            est2 = await client.get_estimate(SAMPLE_ESTIMATE_ID)
            assert est2 is est1
            assert call_count == 1

    async def test_eu_url_routes_to_eu_api(self) -> None:
        requested_urls: list[str] = []

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            requested_urls.append(str(request.url))
            return httpx.Response(200, json=SAMPLE_ESTIMATE_JSON)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as http:
            client = EstimateClient(
                http,
                {
                    CALCULATOR_GLOBAL_URL: "https://us-api.example.com/{estimateKey}",
                    CALCULATOR_ESC_URL: "https://eu-api.example.com/{estimateKey}",
                },
            )
            eu_url = f"https://pricing.calculator.aws.eu/#/estimate?id={SAMPLE_ESTIMATE_ID}"
            await client.get_estimate(eu_url)
            assert "eu-api.example.com" in requested_urls[0]

    async def test_rediscovery_on_403(self) -> None:
        call_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            url = str(request.url)
            if "calculator.aws" in url:
                if url.endswith("config.js"):
                    return httpx.Response(200, text=_REDISCOVERY_CONFIG_JS)
                return httpx.Response(200, text=_REDISCOVERY_HTML)
            call_count += 1
            if call_count == 1:
                return httpx.Response(403)
            return httpx.Response(200, json=SAMPLE_ESTIMATE_JSON)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as http:
            client = EstimateClient(
                http, {CALCULATOR_GLOBAL_URL: "https://old-api.example.com/{estimateKey}"}
            )
            est = await client.get_estimate("deadbeef" * 5)
            assert est.name == "Serverless API"
            assert call_count == 2
