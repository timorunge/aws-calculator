"""HTTP client for fetching shared estimates from calculator.aws."""

from __future__ import annotations

import logging
import re
from urllib.parse import parse_qs, urlparse

import httpx
from pydantic import ValidationError

from aws_calculator.core.discovery import (
    CALCULATOR_ESC_URL,
    CALCULATOR_GLOBAL_URL,
    FETCH_TIMEOUT,
    discover_estimate_api_url,
)
from aws_calculator.core.types import Estimate

logger = logging.getLogger(__name__)

_ESTIMATE_ID_RE = re.compile(r"^[0-9a-fA-F]{20,64}$")
_MAX_CACHE_SIZE = 128


class EstimateFetchError(Exception):
    """Raised when an estimate cannot be fetched."""


class EstimateNotFoundError(EstimateFetchError):
    """Raised when an estimate ID is not found (404)."""


class EstimateClient:
    """Fetches and caches shared AWS Pricing Calculator estimates."""

    def __init__(self, http_client: httpx.AsyncClient, api_urls: dict[str, str]) -> None:
        self._http = http_client
        self._api_urls = api_urls
        self._cache: dict[tuple[str, str], Estimate] = {}

    async def get_estimate(self, url_or_id: str) -> Estimate:
        """Fetch an estimate by URL or ID. Returns cached result if available."""
        estimate_id = parse_estimate_id(url_or_id)
        if not _ESTIMATE_ID_RE.match(estimate_id):
            raise EstimateFetchError(
                f"invalid estimate ID: '{estimate_id}'. "
                "expected a hex string (e.g. 'e459751ce5e5aa93f254ea8ad3e825af92906379')."
            )
        calculator_base = detect_calculator_base(url_or_id)
        cache_key = (calculator_base, estimate_id)

        if cache_key in self._cache:
            return self._cache[cache_key]

        estimate = await self._fetch(estimate_id, calculator_base)
        if len(self._cache) >= _MAX_CACHE_SIZE:
            del self._cache[next(iter(self._cache))]
        self._cache[cache_key] = estimate
        return estimate

    async def _fetch(
        self, estimate_id: str, calculator_base: str, *, _allow_rediscovery: bool = True
    ) -> Estimate:
        api_url_template = self._api_urls.get(calculator_base)
        if api_url_template is None:
            raise EstimateFetchError(
                f"no API URL configured for {calculator_base}. "
                "discovery may have failed at startup."
            )

        url = api_url_template.replace("{estimateKey}", estimate_id)
        try:
            resp = await self._http.get(url, timeout=FETCH_TIMEOUT)
        except httpx.HTTPError as e:
            raise EstimateFetchError(f"network error fetching estimate: {e}") from e

        if resp.status_code in (403, 404):
            if _allow_rediscovery:
                retried = await self._rediscover_and_retry(
                    estimate_id, calculator_base, resp.status_code
                )
                if retried is not None:
                    return retried
            if resp.status_code == 404:
                raise EstimateNotFoundError(
                    f"estimate '{estimate_id}' not found. "
                    "it may have expired or the ID may be incorrect."
                )
            raise EstimateFetchError(
                "access denied fetching estimate. the API endpoint may have changed."
            )

        if not resp.is_success:
            raise EstimateFetchError(f"failed to fetch estimate: HTTP {resp.status_code}")

        try:
            data = resp.json()
        except (ValueError, UnicodeDecodeError) as e:
            raise EstimateFetchError(f"invalid JSON in estimate response: {e}") from e

        try:
            return Estimate.model_validate(data)
        except ValidationError as e:
            raise EstimateFetchError(f"could not parse estimate response: {e}") from e

    async def _rediscover_and_retry(
        self, estimate_id: str, calculator_base: str, status_code: int
    ) -> Estimate | None:
        logger.info("Got %d, attempting API URL re-discovery...", status_code)
        new_url = await discover_estimate_api_url(self._http, calculator_base)
        old_url = self._api_urls.get(calculator_base)
        if new_url and new_url != old_url:
            self._api_urls[calculator_base] = new_url
            return await self._fetch(estimate_id, calculator_base, _allow_rediscovery=False)
        return None


def parse_estimate_id(url_or_id: str) -> str:
    """Extract the estimate ID from a calculator URL or bare hex string."""
    url_or_id = url_or_id.strip()

    if _ESTIMATE_ID_RE.match(url_or_id):
        return url_or_id

    parsed = urlparse(url_or_id)
    # calculator.aws uses hash-based routing
    fragment = parsed.fragment
    if fragment:
        frag_parsed = urlparse(f"http://x{fragment}")
        qs = parse_qs(frag_parsed.query)
        if "id" in qs:
            return qs["id"][0]

    qs = parse_qs(parsed.query)
    if "id" in qs:
        return qs["id"][0]

    return url_or_id


def detect_calculator_base(url_or_id: str) -> str:
    """Return the calculator base URL inferred from a URL or bare ID."""
    s = url_or_id.strip()
    if _ESTIMATE_ID_RE.match(s):
        return CALCULATOR_GLOBAL_URL
    parsed = urlparse(s if "://" in s else f"https://{s}")
    if parsed.hostname and parsed.hostname in (
        "pricing.calculator.aws.eu",
        "calculator.aws.eu",
    ):
        return CALCULATOR_ESC_URL
    return CALCULATOR_GLOBAL_URL
