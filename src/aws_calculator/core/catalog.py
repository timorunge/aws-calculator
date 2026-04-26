"""ManifestClient for fetching the AWS service catalog from CDN."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from aws_calculator.core.types import (
    FieldOption,
    Partition,
    ServiceEntry,
    ServiceField,
)

logger = logging.getLogger(__name__)

CATALOG_TIMEOUT: float = 20.0

_CDN_BASE = "https://d1qsjq9pzbk1k6.cloudfront.net"
_SAVE_URL = "https://dnd5zrqcec4or.cloudfront.net/Prod/v2/saveAs"


@dataclass(frozen=True)
class PartitionConfig:
    cdn_base: str
    manifest_path: str
    cdn_prefix: str
    save_url: str
    share_base: str
    contract: str | None


PARTITION_CONFIG: dict[Partition, PartitionConfig] = {
    Partition.AWS: PartitionConfig(
        cdn_base=_CDN_BASE,
        manifest_path="/manifest/en_US.json",
        cdn_prefix="",
        save_url=_SAVE_URL,
        share_base="https://calculator.aws",
        contract=None,
    ),
    Partition.AWS_ESC: PartitionConfig(
        cdn_base="https://pricing.calculator.aws.eu",
        manifest_path="/getAllServiceDetails/aws-eusc/manifest/en_US.json",
        cdn_prefix="/getAllServiceDetails/aws-eusc",
        save_url="https://bieyocog1d.execute-api.eusc-de-east-1.amazonaws.eu/Prod/v2/saveAs",
        share_base="https://pricing.calculator.aws.eu",
        contract=None,
    ),
    Partition.AWS_ISO: PartitionConfig(
        cdn_base=_CDN_BASE,
        manifest_path="/aws-iso/manifest/en_US.json",
        cdn_prefix="/aws-iso",
        save_url=_SAVE_URL,
        share_base="https://calculator.aws",
        contract="5423f8cd3b711c6f899ba4dade31b50c",
    ),
    Partition.AWS_ISO_B: PartitionConfig(
        cdn_base=_CDN_BASE,
        manifest_path="/aws-iso-b/manifest/en_US.json",
        cdn_prefix="/aws-iso-b",
        save_url=_SAVE_URL,
        share_base="https://calculator.aws",
        contract="5423f8cd3b711c6f899ba4dade31b50c",
    ),
}


_INPUT_TYPES = frozenset(
    {"input", "numericInput", "frequency", "fileSize", "durationInput", "percentInput"}
)
_INPUT_SUBTYPES = frozenset(
    {
        "dropdown",
        "numericInput",
        "frequency",
        "fileSize",
        "durationInput",
        "columnFormIPM",
        "dataTransferV2",
    }
)
_SKIP_SUBTYPES = frozenset({"bodyText", "headerText", "alert"})


class CatalogError(Exception):
    """Base for all catalog errors."""


class ManifestFetchError(CatalogError):
    """Manifest could not be fetched or parsed."""


class DefinitionFetchError(CatalogError):
    """Service definition could not be fetched."""


def _decode_json(resp: httpx.Response) -> Any:
    # ESC endpoint returns base64-encoded JSON (content-type: application/octet-stream)
    raw = resp.content
    if raw and raw[:1] not in (b"{", b"["):
        raw = base64.b64decode(raw)
    return json.loads(raw)


class ManifestClient:
    """Fetches and caches the service catalog and definitions from CDN."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client
        self._manifests: dict[Partition, dict[str, ServiceEntry]] = {}
        self._definitions: dict[str, dict[str, Any]] = {}

    async def load_manifest(self, partition: Partition = Partition.AWS) -> dict[str, ServiceEntry]:
        if partition in self._manifests:
            return self._manifests[partition]

        config = PARTITION_CONFIG[partition]
        url = f"{config.cdn_base}{config.manifest_path}"
        try:
            resp = await self._http.get(url, timeout=CATALOG_TIMEOUT)
        except httpx.HTTPError as exc:
            raise ManifestFetchError(f"network error fetching manifest: {exc}") from exc

        if not resp.is_success:
            raise ManifestFetchError(f"manifest fetch failed: HTTP {resp.status_code}")

        try:
            data = _decode_json(resp)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ManifestFetchError(f"invalid JSON in manifest response: {exc}") from exc

        index: dict[str, ServiceEntry] = {}
        for raw_svc in data.get("awsServices", []):
            key = raw_svc.get("key") or raw_svc.get("serviceCode")
            if key:
                raw_svc.setdefault("key", key)
                index[key] = ServiceEntry.model_validate(raw_svc)

        self._manifests[partition] = index
        logger.info(
            "Loaded %d services from manifest (partition: %s)",
            len(index),
            partition.value,
        )
        return index

    @staticmethod
    def find_service(manifest: dict[str, ServiceEntry], name: str) -> ServiceEntry | None:
        lower = name.lower()
        for key, svc in manifest.items():
            if key.lower() == lower:
                return svc
        return None

    @staticmethod
    def search_services(
        manifest: dict[str, ServiceEntry],
        query: str,
        max_results: int = 20,
    ) -> list[dict[str, str]] | dict[str, list[dict[str, str]]]:
        terms = [t.strip().lower() for t in query.split(",") if t.strip()]
        if not terms:
            return []

        def _search_one(term: str) -> list[dict[str, str]]:
            matches: list[dict[str, str]] = []
            for key, svc in manifest.items():
                if svc.sub_type == "subServiceSelector":
                    continue
                if svc.is_active == "false":
                    continue
                hit = (
                    term in key.lower()
                    or term in svc.name.lower()
                    or any(term in kw.lower() for kw in svc.search_keywords)
                )
                if hit:
                    matches.append({"key": key, "name": svc.name})
                    if len(matches) >= max_results:
                        break
            return matches

        if len(terms) == 1:
            return _search_one(terms[0])
        return {term: _search_one(term) for term in terms}

    async def fetch_definition(
        self,
        manifest: dict[str, ServiceEntry],
        service_code: str,
        partition: Partition = Partition.AWS,
    ) -> dict[str, Any] | None:
        cache_key = f"{partition.value}:{service_code}"
        if cache_key in self._definitions:
            return self._definitions[cache_key]

        svc = manifest.get(service_code)
        if svc is None:
            return None

        config = PARTITION_CONFIG[partition]
        url_path = svc.service_definition_url_path or f"/data/{service_code}/en_US.json"
        url = f"{config.cdn_base}{config.cdn_prefix}{url_path}"
        try:
            resp = await self._http.get(url, timeout=CATALOG_TIMEOUT)
        except httpx.HTTPError as exc:
            raise DefinitionFetchError(
                f"network error fetching definition for {service_code}: {exc}"
            ) from exc

        if not resp.is_success:
            raise DefinitionFetchError(
                f"definition fetch failed for {service_code}: HTTP {resp.status_code}"
            )

        try:
            data: dict[str, Any] = _decode_json(resp)
        except (ValueError, UnicodeDecodeError) as exc:
            raise DefinitionFetchError(
                f"invalid JSON in definition for {service_code}: {exc}"
            ) from exc

        self._definitions[cache_key] = data
        return data

    @staticmethod
    def extract_fields(definition: dict[str, Any]) -> list[ServiceField]:
        fields: list[ServiceField] = []
        seen: set[str] = set()

        def _walk(obj: Any) -> None:
            if not isinstance(obj, dict | list):
                return
            if isinstance(obj, list):
                for item in obj:
                    _walk(item)
                return

            field_id = obj.get("id")
            field_type = obj.get("type")
            field_subtype = obj.get("subType")
            effective_type = field_subtype or field_type

            if (
                field_id
                and (field_type in _INPUT_TYPES or field_subtype in _INPUT_SUBTYPES)
                and effective_type not in _SKIP_SUBTYPES
                and "WithoutFreeTier" not in field_id
                and "_withoutFree" not in field_id
                and not field_id.endswith("_MVP")
            ):
                dedup_key = f"{field_id}:{effective_type}"
                if dedup_key not in seen:
                    seen.add(dedup_key)

                    kwargs: dict[str, Any] = {
                        "id": field_id,
                        "type": effective_type or "",
                    }

                    label = obj.get("label")
                    if label:
                        kwargs["label"] = label

                    raw_options = obj.get("options")
                    if raw_options and isinstance(raw_options, list):
                        kwargs["options"] = [
                            FieldOption.model_validate(o)
                            for o in raw_options
                            if isinstance(o, dict)
                            and (o.get("id") is not None or o.get("label") is not None)
                        ]

                    unit = obj.get("unit")
                    if unit:
                        kwargs["unit"] = unit

                    if effective_type == "fileSize":
                        sizes = [
                            s.get("value") or s.get("id") or "gb"
                            for s in (obj.get("dropDownSize") or [])
                        ]
                        if not sizes:
                            sizes = ["gb"]
                        default_option = obj.get("defaultOption") or {}
                        default_size = default_option.get("size", "gb")
                        default_freq = default_option.get("frequency", "NA")
                        kwargs["valid_sizes"] = sizes
                        kwargs["default_unit"] = f"{default_size}|{default_freq}"
                        kwargs["unit_format"] = (
                            f"{{value}}|{{size}}|{{frequency}}"
                            f" -- sizes: [{', '.join(sizes)}],"
                            f' default: "{default_size}|{default_freq}"'
                        )

                    fields.append(ServiceField(**kwargs))

            for v in obj.values():
                _walk(v)

        _walk(definition.get("templates", definition))
        return fields

    async def resolve_fields(
        self,
        manifest: dict[str, ServiceEntry],
        keys: list[str],
        partition: Partition,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        errors: list[str] = []
        found: list[ServiceEntry] = []
        for key in keys:
            svc = self.find_service(manifest, key)
            if svc is None:
                errors.append(f"service '{key}' not found in catalog")
            else:
                found.append(svc)

        definitions = await asyncio.gather(
            *[self.fetch_definition(manifest, svc.key, partition) for svc in found]
        )

        services: list[dict[str, Any]] = []
        for svc, definition in zip(found, definitions, strict=True):
            if definition is None:
                errors.append(f"no definition available for '{svc.key}'")
                continue
            fields = self.extract_fields(definition)
            services.append({"key": svc.key, "name": svc.name, "fields": fields})

        return services, errors

    @staticmethod
    def resolve_partition(region: str | None) -> Partition:
        if not region:
            return Partition.AWS
        if region.startswith("eusc-"):
            return Partition.AWS_ESC
        if region.startswith("us-iso-"):
            return Partition.AWS_ISO
        if region.startswith("us-isob-"):
            return Partition.AWS_ISO_B
        return Partition.AWS
