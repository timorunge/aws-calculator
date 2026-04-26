"""EstimateBuilder: in-memory estimate assembly and AWS payload generation."""

from __future__ import annotations

import asyncio
import itertools
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any, NamedTuple

from aws_calculator.core.catalog import CatalogError, ManifestClient
from aws_calculator.core.ec2 import transform_config as _ec2_transform
from aws_calculator.core.types import DEFAULT_CURRENCY, DEFAULT_LOCALE, Partition, ServiceEntry

logger = logging.getLogger(__name__)

EC2_SERVICE_KEY = "ec2Enhancement"
DEFAULT_REGION = "us-east-1"

_REGION_NAMES: dict[str, str] | None = None


def _load_region_names() -> dict[str, str]:
    global _REGION_NAMES
    if _REGION_NAMES is not None:
        return _REGION_NAMES
    regions: dict[str, str] = {}
    try:
        from botocore.loaders import Loader  # type: ignore[import-not-found,import-untyped,unused-ignore]  # isort: skip

        data = Loader().load_data("endpoints")
        for partition in data.get("partitions", []):
            for code, info in partition.get("regions", {}).items():
                regions[code] = info.get("description", code)
    except (ImportError, KeyError, AttributeError, OSError):
        logger.debug("botocore not available, region display names disabled")
    _REGION_NAMES = regions
    return regions


def _region_name(region: str) -> str:
    return _load_region_names().get(region, region)


class EstimateBuildError(Exception):
    """Raised when the estimate payload cannot be built."""


class _BuilderEntry(NamedTuple):
    composite_key: str
    region: str
    description: str
    calculation_components: dict[str, Any]
    group: str | None


def _sanitize(s: str) -> str:
    return re.sub(r"[<>&]", "", s or "")


def _is_ec2(service_key: str) -> bool:
    return service_key.lower() == EC2_SERVICE_KEY.lower()


def _wrap_values(components: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v if isinstance(v, dict) else {"value": str(v)}
        for k, v in components.items()
        if v is not None
    }


def _config_summary(components: dict[str, Any]) -> str:
    return ", ".join(
        f"{k} ({v.get('value') if isinstance(v, dict) else v})"
        for k, v in components.items()
        if v is not None
    )


def _resolve_partition_from_region(region: str | None) -> Partition:
    return ManifestClient.resolve_partition(region)


async def _build_service_config(
    catalog: ManifestClient,
    manifest: dict[str, ServiceEntry],
    svc: ServiceEntry,
    entry: _BuilderEntry,
    partition: Partition,
    payload_key: str,
) -> dict[str, Any]:
    is_ec2 = _is_ec2(svc.key)

    version = "0.0.1"
    service_code = payload_key
    estimate_for = "template"
    try:
        definition = await catalog.fetch_definition(manifest, payload_key, partition)
        if definition:
            version = definition.get("version", version)
            service_code = definition.get("serviceCode", service_code)
            templates = definition.get("templates")
            if isinstance(templates, list) and templates:
                estimate_for = templates[0].get("id", estimate_for)
    except CatalogError:
        logger.warning("failed to fetch definition for %s, using fallback values", payload_key)

    if is_ec2:
        ec2_config = dict(entry.calculation_components)
        ec2_config["region"] = entry.region
        calc_components = _ec2_transform(ec2_config)
    else:
        calc_components = _wrap_values(entry.calculation_components)

    return {
        "serviceCode": service_code,
        "region": entry.region,
        "estimateFor": estimate_for,
        "description": _sanitize(entry.description),
        "serviceCost": {"monthly": 0, "upfront": 0},
        "serviceName": svc.name,
        "regionName": _region_name(entry.region),
        "version": version,
        "calculationComponents": calc_components,
        "configSummary": _config_summary(entry.calculation_components),
    }


class EstimateBuilder:
    """Accumulates services and builds the AWS save payload."""

    def __init__(
        self,
        name: str = "My Estimate",
        partition: Partition | None = None,
    ) -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.partition: Partition | None = partition
        self._entries: list[_BuilderEntry] = []
        self._used_keys: set[str] = set()

    def add_service(
        self,
        service_code: str,
        *,
        region: str = DEFAULT_REGION,
        description: str | None = None,
        calculation_components: dict[str, Any] | None = None,
        group: str | None = None,
    ) -> None:
        composite_key = service_code
        if composite_key in self._used_keys and description is not None:
            suffix = description.replace(" ", "")
            composite_key = f"{service_code}:{suffix}"
        self._used_keys.add(composite_key)
        self._entries.append(
            _BuilderEntry(
                composite_key,
                region,
                description or "",
                calculation_components or {},
                group,
            )
        )

    def is_empty(self) -> bool:
        return not self._entries

    def _resolve_partition(self) -> Partition:
        if self.partition is not None:
            return self.partition
        for entry in self._entries:
            p = _resolve_partition_from_region(entry.region)
            if p != Partition.AWS:
                return p
        return Partition.AWS

    def _validate_partition_consistency(self) -> None:
        partitions: set[Partition] = set()
        for entry in self._entries:
            if entry.region:
                partitions.add(_resolve_partition_from_region(entry.region))
        if len(partitions) > 1:
            raise EstimateBuildError(
                "mixed-partition estimates are not supported: "
                f"found regions from partitions: {', '.join(p.value for p in partitions)}"
            )

    async def build_payload(self, catalog: ManifestClient) -> dict[str, Any]:
        """Build the full AWS save payload. Requires catalog for manifest lookups."""
        partition = self._resolve_partition()
        self._validate_partition_consistency()
        manifest = await catalog.load_manifest(partition)

        async def _build_entry(
            entry: _BuilderEntry,
        ) -> tuple[str, dict[str, Any]] | None:
            base_key = entry.composite_key.split(":")[0]
            svc = catalog.find_service(manifest, base_key)
            if svc is None:
                logger.warning("service '%s' not found in manifest, skipping", base_key)
                return None
            payload_key = EC2_SERVICE_KEY if _is_ec2(svc.key) else svc.key
            config = await _build_service_config(
                catalog, manifest, svc, entry, partition, payload_key
            )
            return f"{payload_key}-{uuid.uuid4()}", config

        groups_map: dict[str, list[_BuilderEntry]] = {}
        ungrouped_entries: list[_BuilderEntry] = []

        for entry in self._entries:
            if entry.group is None:
                ungrouped_entries.append(entry)
            else:
                groups_map.setdefault(entry.group, []).append(entry)

        all_entries = list(itertools.chain(ungrouped_entries, *groups_map.values()))
        built = await asyncio.gather(*[_build_entry(e) for e in all_entries])

        built_iter = iter(built)
        ungrouped = {r[0]: r[1] for r in itertools.islice(built_iter, len(ungrouped_entries)) if r}

        payload_groups: dict[str, Any] = {}
        for group_name, group_entries in groups_map.items():
            safe_name = _sanitize(group_name)
            group_services = {
                r[0]: r[1] for r in itertools.islice(built_iter, len(group_entries)) if r
            }
            group_key = f"{safe_name}-{uuid.uuid4()}"
            payload_groups[group_key] = {
                "name": safe_name,
                "services": group_services,
                "groups": {},
                "groupSubtotal": {"monthly": 0},
                "totalCost": {"monthly": 0, "upfront": 0},
            }

        payload: dict[str, Any] = {
            "name": self.name,
            "services": ungrouped,
            "groups": payload_groups,
            "groupSubtotal": {},
            "totalCost": {"monthly": 0, "upfront": 0},
            "support": {},
            "metaData": {
                "locale": DEFAULT_LOCALE,
                "currency": DEFAULT_CURRENCY,
                "createdOn": datetime.now(UTC).isoformat(),
                "source": "calculator-platform",
            },
        }

        if partition not in (Partition.AWS, Partition.AWS_ESC):
            payload["settings"] = {
                "subTotalModifier": {
                    "type": "VOLUME_DISCOUNT",
                    "value": 0,
                    "valuePercentage": 0,
                    "label": "Discount",
                },
                "monthlyTimeFrame": 12,
                "timeFrame": {"length": 12, "unit": "month"},
                "awsPartition": partition.value,
            }

        return payload
