"""Tests for URL parsing and EstimateClient."""

import json

import httpx
import pytest

from aws_calculator.core.client import (
    EstimateClient,
    EstimateFetchError,
    EstimateNotFoundError,
    detect_calculator_base,
    parse_estimate_id,
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


class TestParseEstimateId:
    def test_bare_hex_id(self) -> None:
        assert parse_estimate_id("2f74122a33c80a5ec394545a7b375c6a15b1a906") == (
            "2f74122a33c80a5ec394545a7b375c6a15b1a906"
        )

    @pytest.mark.parametrize(
        "input_url",
        [
            "https://calculator.aws/#/estimate?id=abc123def456789012345678",
            "  https://calculator.aws/#/estimate?id=abc123def456789012345678  ",
        ],
    )
    def test_extracts_id_from_url_variants(self, input_url: str) -> None:
        assert parse_estimate_id(input_url) == "abc123def456789012345678"


class TestDetectCalculatorBase:
    def test_global_url(self) -> None:
        result = detect_calculator_base("https://calculator.aws/#/estimate?id=abc")
        assert result == CALCULATOR_GLOBAL_URL

    def test_esc_url(self) -> None:
        result = detect_calculator_base("https://pricing.calculator.aws.eu/#/estimate?id=abc")
        assert result == CALCULATOR_ESC_URL

    def test_bare_id_defaults_to_global(self) -> None:
        result = detect_calculator_base("2f74122a33c80a5ec394545a7b375c6a15b1a906")
        assert result == CALCULATOR_GLOBAL_URL

    def test_esc_url_without_scheme(self) -> None:
        result = detect_calculator_base("pricing.calculator.aws.eu/#/estimate?id=abc")
        assert result == CALCULATOR_ESC_URL


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

    async def test_404_raises_not_found(self) -> None:
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            if "calculator.aws" in str(request.url):
                return httpx.Response(200, text="<html>no config</html>")
            return httpx.Response(404)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as http:
            client = EstimateClient(
                http, {CALCULATOR_GLOBAL_URL: "https://example.com/{estimateKey}"}
            )
            with pytest.raises(EstimateNotFoundError, match="not found"):
                await client.get_estimate("deadbeef" * 5)

    async def test_500_raises_fetch_error(self) -> None:
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as http:
            client = EstimateClient(
                http, {CALCULATOR_GLOBAL_URL: "https://example.com/{estimateKey}"}
            )
            with pytest.raises(EstimateFetchError, match="HTTP 500"):
                await client.get_estimate("deadbeef" * 5)

    async def test_invalid_json_raises_fetch_error(self) -> None:
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="not json at all")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as http:
            client = EstimateClient(
                http, {CALCULATOR_GLOBAL_URL: "https://example.com/{estimateKey}"}
            )
            with pytest.raises(EstimateFetchError, match="Invalid JSON"):
                await client.get_estimate("deadbeef" * 5)

    async def test_invalid_estimate_schema_raises_fetch_error(self) -> None:
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"totalCost": "not-a-dict"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as http:
            client = EstimateClient(
                http, {CALCULATOR_GLOBAL_URL: "https://example.com/{estimateKey}"}
            )
            with pytest.raises(EstimateFetchError, match="Could not parse estimate response"):
                await client.get_estimate("deadbeef" * 5)

    async def test_non_hex_id_rejected(self) -> None:
        async def unreachable(request: httpx.Request) -> httpx.Response:
            raise AssertionError("no request expected")

        transport = httpx.MockTransport(unreachable)
        async with httpx.AsyncClient(transport=transport) as http:
            client = EstimateClient(
                http, {CALCULATOR_GLOBAL_URL: "https://example.com/{estimateKey}"}
            )
            with pytest.raises(EstimateFetchError, match="Invalid estimate ID"):
                await client.get_estimate("not-a-hex-id")

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
            assert len(requested_urls) == 1
            assert "eu-api.example.com" in requested_urls[0]
            assert "us-api.example.com" not in requested_urls[0]

    async def test_missing_eu_api_url_raises_fetch_error(self) -> None:
        async def unreachable(request: httpx.Request) -> httpx.Response:
            raise AssertionError("no request expected")

        transport = httpx.MockTransport(unreachable)
        async with httpx.AsyncClient(transport=transport) as http:
            client = EstimateClient(
                http, {CALCULATOR_GLOBAL_URL: "https://example.com/{estimateKey}"}
            )
            eu_url = "https://pricing.calculator.aws.eu/#/estimate?id=" + "ab" * 20
            with pytest.raises(EstimateFetchError, match="No API URL configured"):
                await client.get_estimate(eu_url)

    async def test_cache_evicts_oldest_at_capacity(self) -> None:
        from aws_calculator.core.client import _MAX_CACHE_SIZE

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=SAMPLE_ESTIMATE_JSON)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as http:
            client = EstimateClient(
                http, {CALCULATOR_GLOBAL_URL: "https://example.com/{estimateKey}"}
            )
            for i in range(_MAX_CACHE_SIZE):
                hex_id = f"{i:040x}"
                await client.get_estimate(hex_id)
            assert len(client._cache) == _MAX_CACHE_SIZE

            await client.get_estimate("ff" * 20)
            assert len(client._cache) == _MAX_CACHE_SIZE

    async def test_403_with_unchanged_rediscovery_raises_access_denied(self) -> None:
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "calculator.aws" in url:
                return httpx.Response(200, text="<html>no config</html>")
            return httpx.Response(403)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as http:
            client = EstimateClient(
                http, {CALCULATOR_GLOBAL_URL: "https://example.com/{estimateKey}"}
            )
            with pytest.raises(EstimateFetchError, match="Access denied"):
                await client.get_estimate("deadbeef" * 5)

    async def test_rediscovery_success_retries_with_new_url(self) -> None:
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

    async def test_rediscovery_does_not_recurse_on_second_failure(self) -> None:
        estimate_call_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal estimate_call_count
            url = str(request.url)
            if "calculator.aws" in url:
                if url.endswith("config.js"):
                    return httpx.Response(200, text=_REDISCOVERY_CONFIG_JS)
                return httpx.Response(200, text=_REDISCOVERY_HTML)
            estimate_call_count += 1
            return httpx.Response(403)

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as http:
            client = EstimateClient(
                http, {CALCULATOR_GLOBAL_URL: "https://old-api.example.com/{estimateKey}"}
            )
            with pytest.raises(EstimateFetchError, match="Access denied"):
                await client.get_estimate("deadbeef" * 5)
            assert estimate_call_count == 2
