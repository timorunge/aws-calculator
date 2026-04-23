"""Auto-discover the estimate API URL from a calculator's config.js."""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

CALCULATOR_GLOBAL_URL = "https://calculator.aws/"
CALCULATOR_ESC_URL = "https://pricing.calculator.aws.eu/"
FALLBACK_GLOBAL_ESTIMATE_API = "https://d3knqfixx3sbls.cloudfront.net/{estimateKey}"
FETCH_TIMEOUT: float = 20.0

_DISCOVERY_TIMEOUT: float = 15.0

# No hardcoded fallback for the ESC calculator; it must be discovered at runtime.
_FALLBACK_APIS: dict[str, str] = {
    CALCULATOR_GLOBAL_URL: FALLBACK_GLOBAL_ESTIMATE_API,
}

# Hosts we trust for outbound requests during discovery.
_ALLOWED_HOSTS = frozenset(
    {
        urlparse(CALCULATOR_GLOBAL_URL).hostname,
        urlparse(CALCULATOR_ESC_URL).hostname,
        urlparse(FALLBACK_GLOBAL_ESTIMATE_API).hostname,
    }
)

# Matches: src="<path>/config.js"
_CONFIG_JS_RE = re.compile(r'src="([^"]*config\.js)"')


def _extract_balanced_braces(text: str, start: int) -> str | None:
    """Extract a balanced {...} block from text starting at position start."""
    depth = 0
    string_char: str | None = None
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\":
            if string_char is not None:
                escape_next = True
            continue

        if ch in ('"', "'"):
            if string_char is None:
                string_char = ch
            elif string_char == ch:
                string_char = None
            continue

        if string_char is not None:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def _find_nested_value(obj: object, target: str) -> str | None:
    """Recursively search a nested dict/list for a key, return its value."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == target and isinstance(v, str):
                return v
            result = _find_nested_value(v, target)
            if result is not None:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _find_nested_value(item, target)
            if result is not None:
                return result
    return None


def _extract_config_js_path(html: str) -> str | None:
    match = _CONFIG_JS_RE.search(html)
    return match.group(1) if match else None


def _extract_estimate_api_url(config_js: str) -> str | None:
    marker = "window.PRC_CONFIG"
    idx = config_js.find(marker)
    if idx == -1:
        return None

    brace_start = config_js.find("{", idx)
    if brace_start == -1:
        return None

    json_str = _extract_balanced_braces(config_js, brace_start)
    if not json_str:
        return None

    try:
        config = json.loads(json_str)
    except json.JSONDecodeError:
        return None

    # GET_SAVED_ESTIMATES_API nesting path varies across calculator versions
    return _find_nested_value(config, "GET_SAVED_ESTIMATES_API")


def _resolve_url(base_url: str, path_or_url: str) -> str:
    """Resolve a path or URL against a base, rejecting off-host results."""
    resolved = urljoin(base_url, path_or_url)
    host = urlparse(resolved).hostname
    if not host or host not in _ALLOWED_HOSTS:
        raise ValueError(f"resolved URL has disallowed host: {host}")
    return resolved


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    resp = await client.get(url, follow_redirects=True, timeout=_DISCOVERY_TIMEOUT)
    resp.raise_for_status()
    return resp.text


async def discover_estimate_api_url(
    client: httpx.AsyncClient,
    base_url: str = CALCULATOR_GLOBAL_URL,
) -> str:
    """Discover the GET_SAVED_ESTIMATES_API URL from a calculator's config.js."""
    fallback = _FALLBACK_APIS.get(base_url, "")
    try:
        html = await _fetch_text(client, base_url)
        config_path = _extract_config_js_path(html)
        if not config_path:
            logger.warning("Could not find config.js path in %s HTML", base_url)
            return fallback

        config_url = _resolve_url(base_url, config_path)
        config_js = await _fetch_text(client, config_url)

        api_url = _extract_estimate_api_url(config_js)
        if not api_url:
            logger.warning("Could not extract GET_SAVED_ESTIMATES_API from config.js")
            return fallback

        # The API URL may be relative (e.g. "/getSavedEstimates/{estimateKey}").
        # Resolve it against the calculator base URL so callers always get
        # an absolute URL. _resolve_url rejects hosts outside the allowlist.
        api_url = _resolve_url(base_url, api_url)

        logger.info("Discovered estimate API URL: %s", api_url)
        return api_url

    except (httpx.HTTPError, OSError, ValueError, json.JSONDecodeError) as e:
        logger.warning("Discovery failed (%s), using fallback URL", e)
        return fallback
