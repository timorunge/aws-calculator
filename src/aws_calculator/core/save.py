"""SaveClient: POST estimate payloads to the AWS save API."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from aws_calculator.core.catalog import PARTITION_CONFIG
from aws_calculator.core.types import Partition, SaveResult

logger = logging.getLogger(__name__)

SAVE_TIMEOUT: float = 30.0
_SAVED_KEY_RE = re.compile(r"^[0-9a-fA-F]+$")


class SaveError(Exception):
    """Raised when the AWS save API returns an error."""


def _parse_double_encoded(raw: str) -> dict[str, Any]:
    try:
        outer = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SaveError(f"save API returned invalid JSON: {exc}") from exc

    body_str = outer.get("body")
    if not isinstance(body_str, str):
        raise SaveError(f"save API response missing 'body' string: {raw[:200]}")

    try:
        body: dict[str, Any] = json.loads(body_str)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SaveError(f"save API returned invalid body JSON: {exc}") from exc
    return body


def _build_share_url(saved_key: str, partition: Partition) -> str:
    config = PARTITION_CONFIG[partition]
    if config.contract:
        return (
            f"{config.share_base}/#/estimate"
            f"?ctrct={config.contract}&volume_discount=0&id={saved_key}"
        )
    return f"{config.share_base}/#/estimate?id={saved_key}"


class SaveClient:
    """Saves estimate payloads to the AWS calculator save API."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client

    async def save(self, payload: dict[str, Any], partition: Partition) -> SaveResult:
        config = PARTITION_CONFIG[partition]
        json_body = json.dumps(payload)
        logger.info(
            "Saving estimate: %d bytes, %d groups, %d ungrouped services",
            len(json_body),
            len(payload.get("groups", {})),
            len(payload.get("services", {})),
        )

        try:
            resp = await self._http.post(
                config.save_url,
                content=json_body,
                headers={
                    "Content-Type": "application/json",
                    "Referer": f"{config.share_base}/",
                },
                timeout=SAVE_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise SaveError(f"network error saving estimate: {exc}") from exc

        raw = resp.text
        if not resp.is_success:
            detail = raw[:200]
            try:
                body = _parse_double_encoded(raw)
                detail = body.get("message", detail)
            except SaveError:
                logger.debug("could not parse error body, using raw response")
            raise SaveError(f"save API returned HTTP {resp.status_code}: {detail}")

        body = _parse_double_encoded(raw)
        saved_key = body.get("savedKey")
        if not saved_key:
            raise SaveError(f"save API did not return a savedKey: {json.dumps(body)[:200]}")
        if not _SAVED_KEY_RE.match(saved_key):
            raise SaveError(f"save API returned invalid savedKey: {saved_key[:80]}")

        url = _build_share_url(saved_key, partition)
        logger.info("Estimate saved: %s", saved_key)
        return SaveResult(estimate_id=saved_key, shareable_url=url)
