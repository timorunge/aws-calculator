"""Tests for API URL discovery from calculator.aws config.js."""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from aws_calculator.core.discovery import (
    FALLBACK_GLOBAL_ESTIMATE_API,
    _extract_balanced_braces,
    discover_estimate_api_url,
)


def _make_config_js(api_url: str) -> str:
    config = {"RESOURCES": {"GET_SAVED_ESTIMATES_API": api_url}}
    return f"window.PRC_CONFIG = {json.dumps(config)};"


_DISCOVERY_HTML = '<html><script src="assets/config.js"></script></html>'


@asynccontextmanager
async def _discovery_client(config_js: str) -> AsyncIterator[httpx.AsyncClient]:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("config.js"):
            return httpx.Response(200, text=config_js)
        return httpx.Response(200, text=_DISCOVERY_HTML)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        yield http


class TestDiscoverEstimateApiUrl:
    async def test_successful_discovery(self) -> None:
        api_url = "https://d3knqfixx3sbls.cloudfront.net/{estimateKey}"
        async with _discovery_client(_make_config_js(api_url)) as http:
            assert await discover_estimate_api_url(http) == api_url

    async def test_off_host_api_url_rejected(self) -> None:
        async with _discovery_client(_make_config_js("https://evil.com/{estimateKey}")) as http:
            assert await discover_estimate_api_url(http) == FALLBACK_GLOBAL_ESTIMATE_API


class TestExtractBalancedBraces:
    def test_nested(self) -> None:
        text = '{"a": {"b": 1}}'
        assert _extract_balanced_braces(text, 0) == '{"a": {"b": 1}}'
