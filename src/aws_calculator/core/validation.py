"""Config key validation with Levenshtein-based fuzzy matching."""

from __future__ import annotations

import math
from typing import Any

from aws_calculator.core.builder import EC2_SERVICE_KEY
from aws_calculator.core.catalog import CatalogError, ManifestClient
from aws_calculator.core.types import Partition


def levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    d = list(range(m + 1))
    for j in range(1, n + 1):
        prev = d[0]
        d[0] = j
        for i in range(1, m + 1):
            tmp = d[i]
            d[i] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, d[i], d[i - 1])
            prev = tmp
    return d[m]


def suggest_matches(invalid: str, valid_ids: list[str], max_suggestions: int = 3) -> list[str]:
    lower = invalid.lower()
    threshold = max(math.floor(len(invalid) * 0.6), 2)
    scored = [(vid, levenshtein(lower, vid.lower())) for vid in valid_ids]
    return [vid for vid, dist in sorted(scored, key=lambda x: x[1]) if dist <= threshold][
        :max_suggestions
    ]


async def validate_config_keys(
    service_key: str,
    calculation_components: dict[str, Any],
    catalog: ManifestClient,
    partition: Partition,
) -> str | None:
    """Return an error message with suggestions, or None if valid.

    Best-effort: returns None on any CatalogError rather than blocking.
    Skips EC2 (has custom fields).
    """
    if service_key.lower() == EC2_SERVICE_KEY.lower():
        return None

    if not calculation_components:
        return None

    try:
        manifest = await catalog.load_manifest(partition)
        svc = catalog.find_service(manifest, service_key)
        if svc is None:
            return None

        definition = await catalog.fetch_definition(manifest, svc.key, partition)
        if definition is None:
            return None

        valid_ids = [f.id for f in catalog.extract_fields(definition)]
        valid_set = set(valid_ids)
        invalid = [k for k in calculation_components if k not in valid_set]
        if not invalid:
            return None

        lines = []
        for k in invalid:
            suggestions = suggest_matches(k, valid_ids)
            if suggestions:
                quoted = ", ".join(f'"{s}"' for s in suggestions)
                lines.append(f'  "{k}" -- did you mean: {quoted}?')
            else:
                lines.append(f'  "{k}" -- no close match found')

        return (
            f"invalid field IDs for {svc.key}:\n"
            + "\n".join(lines)
            + "\nuse get_service_fields to discover valid field IDs."
        )
    except CatalogError:
        return None
