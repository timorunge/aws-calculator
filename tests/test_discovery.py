"""Tests for API URL discovery from calculator.aws config.js."""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest

from aws_calculator.core.discovery import (
    CALCULATOR_ESC_URL,
    FALLBACK_GLOBAL_ESTIMATE_API,
    _extract_balanced_braces,
    _extract_config_js_path,
    _extract_estimate_api_url,
    _find_nested_value,
    discover_estimate_api_url,
)

_DISCOVERY_HTML = '<html><script src="assets/config.js"></script></html>'


def _make_config_js(api_url: str) -> str:
    config = {"RESOURCES": {"GET_SAVED_ESTIMATES_API": api_url}}
    return f"window.PRC_CONFIG = {json.dumps(config)};"


@asynccontextmanager
async def _discovery_client(config_js: str) -> AsyncIterator[httpx.AsyncClient]:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("config.js"):
            return httpx.Response(200, text=config_js)
        return httpx.Response(200, text=_DISCOVERY_HTML)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        yield http


class TestExtractBalancedBraces:
    def test_nested_object(self) -> None:
        text = '{"a": {"b": {"c": 1}}}'
        assert _extract_balanced_braces(text, 0) == text

    def test_with_strings_containing_braces(self) -> None:
        text = '{"a": "hello { world }"}'
        assert _extract_balanced_braces(text, 0) == text

    def test_with_escaped_quotes(self) -> None:
        text = r'{"a": "say \"hello\""}'
        assert _extract_balanced_braces(text, 0) == text

    def test_with_offset(self) -> None:
        text = 'var x = {"key": "val"};'
        assert _extract_balanced_braces(text, 8) == '{"key": "val"}'

    def test_with_single_quoted_braces(self) -> None:
        text = "{'a': 'hello { world }'}"
        assert _extract_balanced_braces(text, 0) == text

    def test_returns_none_for_unbalanced(self) -> None:
        assert _extract_balanced_braces('{"a": 1', 0) is None


class TestFindNestedValue:
    def test_deeply_nested(self) -> None:
        obj = {
            "CONTENT": {
                "RESOURCES": {"GET_SAVED_ESTIMATES_API": "https://example.com/{estimateKey}"}
            }
        }
        assert (
            _find_nested_value(obj, "GET_SAVED_ESTIMATES_API")
            == "https://example.com/{estimateKey}"
        )

    def test_in_list(self) -> None:
        obj = {"items": [{"target": "found"}]}
        assert _find_nested_value(obj, "target") == "found"

    @pytest.mark.parametrize(
        ("obj", "key"),
        [
            ({"a": "b"}, "missing"),
            ({"target": 42}, "target"),
        ],
    )
    def test_returns_none(self, obj: dict, key: str) -> None:
        assert _find_nested_value(obj, key) is None


class TestExtractConfigJsPath:
    @pytest.mark.parametrize(
        ("html", "expected"),
        [
            ('<script src="abc/def/config.js"></script>', "abc/def/config.js"),
            (
                '<script src="e75d6288-606e/[Pkg-1.0]pkg.assets/config.js"></script>',
                "e75d6288-606e/[Pkg-1.0]pkg.assets/config.js",
            ),
        ],
    )
    def test_finds_config_js(self, html: str, expected: str) -> None:
        assert _extract_config_js_path(html) == expected

    def test_returns_none_if_not_found(self) -> None:
        html = '<script src="bundle.js"></script>'
        assert _extract_config_js_path(html) is None


class TestExtractEstimateApiUrl:
    def test_extracts_from_config(self) -> None:
        config = {
            "CONTENT": {
                "RESOURCES": {"GET_SAVED_ESTIMATES_API": "https://cdn.example.com/{estimateKey}"}
            }
        }
        config_js = f"window.PRC_CONFIG = {json.dumps(config)};\nvar x = 1;"
        assert _extract_estimate_api_url(config_js) == "https://cdn.example.com/{estimateKey}"

    @pytest.mark.parametrize(
        "config_js",
        [
            "var x = 1;",  # no PRC_CONFIG marker
            'window.PRC_CONFIG = {"FEATURES": {}};\n',  # marker but no key
        ],
    )
    def test_returns_none(self, config_js: str) -> None:
        assert _extract_estimate_api_url(config_js) is None


class TestDiscoverEstimateApiUrl:
    async def test_successful_discovery(self) -> None:
        api_url = "https://d3knqfixx3sbls.cloudfront.net/{estimateKey}"
        async with _discovery_client(_make_config_js(api_url)) as http:
            assert await discover_estimate_api_url(http) == api_url

    async def test_fallback_on_network_error(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http:
            assert await discover_estimate_api_url(http) == FALLBACK_GLOBAL_ESTIMATE_API

    async def test_eu_fallback_is_empty_on_network_error(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http:
            assert await discover_estimate_api_url(http, CALCULATOR_ESC_URL) == ""

    async def test_eu_discovery_uses_eu_base_url(self) -> None:
        api_url = "https://pricing.calculator.aws.eu/getSavedEstimates/{estimateKey}"
        requested_urls: list[str] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requested_urls.append(str(request.url))
            if str(request.url).endswith("config.js"):
                return httpx.Response(200, text=_make_config_js(api_url))
            return httpx.Response(200, text=_DISCOVERY_HTML)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http:
            assert await discover_estimate_api_url(http, CALCULATOR_ESC_URL) == api_url
            assert requested_urls[0].startswith("https://pricing.calculator.aws.eu")

    async def test_relative_api_url_resolved_against_base(self) -> None:
        async with _discovery_client(_make_config_js("/getSavedEstimates/{estimateKey}")) as http:
            result = await discover_estimate_api_url(http, CALCULATOR_ESC_URL)
            assert result == "https://pricing.calculator.aws.eu/getSavedEstimates/{estimateKey}"

    async def test_off_host_api_url_rejected(self) -> None:
        async with _discovery_client(_make_config_js("https://evil.com/{estimateKey}")) as http:
            assert await discover_estimate_api_url(http) == FALLBACK_GLOBAL_ESTIMATE_API
