"""JSON and plain-text formatters for estimate data."""

from __future__ import annotations

import json
from typing import Any

from aws_calculator.core.types import (
    DEFAULT_CURRENCY,
    Estimate,
    EstimateService,
    ResponseFormat,
    SaveResult,
    ServiceField,
)

_MAX_COMPONENT_VALUE_LEN = 80
_UNGROUPED_LABEL = "(ungrouped)"


def _json(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"))


def _format_component_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    s = json.dumps(value, separators=(",", ":"))
    if len(s) > _MAX_COMPONENT_VALUE_LEN:
        return s[: _MAX_COMPONENT_VALUE_LEN - 3] + "..."
    return s


def _format_cost(amount: float, currency: str) -> str:
    return f"{currency} {amount:,.2f}"


def _build_overview_dict(estimate: Estimate) -> dict[str, Any]:
    d: dict[str, Any] = {
        "name": estimate.name,
        "monthly": estimate.total_cost.monthly,
        "upfront": estimate.total_cost.upfront,
        "services": len(estimate.services),
        "currency": estimate.meta_data.currency,
    }
    if estimate.meta_data.created_on:
        d["created"] = estimate.meta_data.created_on
    if estimate.meta_data.estimate_id:
        d["id"] = estimate.meta_data.estimate_id
    if estimate.groups:
        d["groups"] = list(estimate.groups.keys())
    return d


def _aggregate_group_costs(
    services: list[tuple[str, EstimateService]],
) -> dict[str, float]:
    costs: dict[str, float] = {}
    for _key, svc in services:
        g = svc.group or _UNGROUPED_LABEL
        costs[g] = costs.get(g, 0.0) + svc.service_cost.monthly
    return costs


def format_estimate_overview(estimate: Estimate, fmt: ResponseFormat) -> str:
    if fmt == ResponseFormat.JSON:
        return _json(_build_overview_dict(estimate))

    e = estimate
    c = e.meta_data.currency
    lines = [
        e.name,
        "",
        f"Monthly cost: {_format_cost(e.total_cost.monthly, c)}",
        f"Upfront cost: {_format_cost(e.total_cost.upfront, c)}",
        f"Services: {len(e.services)}",
    ]
    if e.meta_data.created_on:
        lines.append(f"Created: {e.meta_data.created_on}")
    if e.meta_data.estimate_id:
        lines.append(f"Estimate ID: {e.meta_data.estimate_id}")
    return "\n".join(lines)


def format_services_list(
    estimate: Estimate,
    services: dict[str, EstimateService],
    fmt: ResponseFormat,
) -> str:
    if fmt == ResponseFormat.JSON:
        items = []
        for key, svc in services.items():
            item: dict[str, Any] = {
                "key": key,
                "name": svc.service_name or "",
                "region": svc.region_name or svc.region or "",
                "monthly": svc.service_cost.monthly,
            }
            if svc.config_summary:
                item["config"] = svc.config_summary
            if svc.group:
                item["group"] = svc.group
            items.append(item)
        return _json({"name": estimate.name, "services": items})

    c = estimate.meta_data.currency

    grouped: dict[str | None, list[tuple[str, EstimateService]]] = {}
    for key, svc in services.items():
        grouped.setdefault(svc.group, []).append((key, svc))

    lines: list[str] = []
    for group_name, group_services in grouped.items():
        if group_name:
            lines.append(f"[{group_name}]")

        for key, svc in group_services:
            region = svc.region_name or svc.region or ""
            cost = _format_cost(svc.service_cost.monthly, c)
            name = svc.service_name or ""
            config = f" -- {svc.config_summary}" if svc.config_summary else ""
            lines.append(f"  {name} | {region} | {cost} | key: {key}{config}")

        lines.append("")

    return "\n".join(lines)


def format_service_detail(
    key: str, service: EstimateService, fmt: ResponseFormat, currency: str = DEFAULT_CURRENCY
) -> str:
    if fmt == ResponseFormat.JSON:
        components = {
            name: {"value": comp.value, "unit": comp.unit}
            for name, comp in service.calculation_components.items()
        }
        d: dict[str, Any] = {
            "key": key,
            "name": service.service_name or "",
            "code": service.service_code or "",
            "region": service.region_name or service.region or "",
            "monthly": service.service_cost.monthly,
            "components": components,
        }
        if service.config_summary:
            d["config"] = service.config_summary
        if service.description:
            d["description"] = service.description
        if service.group:
            d["group"] = service.group
        return _json(d)

    lines = [
        service.service_name or "",
        "",
        f"Key: {key}",
        f"Service code: {service.service_code or ''}",
        f"Region: {service.region_name or service.region or ''}",
        f"Monthly cost: {_format_cost(service.service_cost.monthly, currency)}",
    ]
    if service.description:
        lines.append(f"Description: {service.description}")
    if service.config_summary:
        lines.append(f"Config summary: {service.config_summary}")
    if service.group:
        lines.append(f"Group: {service.group}")

    if service.calculation_components:
        lines.append("")
        lines.append("Configuration:")
        for name, comp in service.calculation_components.items():
            val = _format_component_value(comp.value)
            unit = f" {comp.unit}" if comp.unit else ""
            lines.append(f"  {name}: {val}{unit}")

    return "\n".join(lines)


def format_estimate_summary(estimate: Estimate, fmt: ResponseFormat) -> str:
    services_by_cost = sorted(
        estimate.services.items(),
        key=lambda kv: kv[1].service_cost.monthly,
        reverse=True,
    )
    group_costs = _aggregate_group_costs(services_by_cost)

    if fmt == ResponseFormat.JSON:
        return _json(
            {
                "name": estimate.name,
                "currency": estimate.meta_data.currency,
                "monthly": estimate.total_cost.monthly,
                "upfront": estimate.total_cost.upfront,
                "groups": group_costs,
                "services": [
                    {
                        "name": svc.service_name or "",
                        "region": svc.region_name or svc.region or "",
                        "monthly": svc.service_cost.monthly,
                        "group": svc.group,
                    }
                    for _key, svc in services_by_cost
                ],
            }
        )

    c = estimate.meta_data.currency
    lines = [
        estimate.name,
        "",
        f"Total monthly: {_format_cost(estimate.total_cost.monthly, c)}",
        f"Total upfront: {_format_cost(estimate.total_cost.upfront, c)}",
    ]

    if group_costs and (len(group_costs) > 1 or set(group_costs) != {_UNGROUPED_LABEL}):
        lines.append("")
        lines.append("Group subtotals:")
        for group_name, cost in sorted(group_costs.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {group_name}: {_format_cost(cost, c)}/mo")

    lines.append("")
    lines.append("Services by cost:")
    for _key, svc in services_by_cost:
        region = svc.region_name or svc.region or ""
        monthly = _format_cost(svc.service_cost.monthly, c)
        lines.append(f"  {svc.service_name or ''} | {region} | {monthly}")

    if estimate.support:
        lines.append("")
        lines.append("Support:")
        for plan_key, plan_data in estimate.support.items():
            if isinstance(plan_data, dict):
                support_cost = plan_data.get("monthlyCost", plan_data.get("monthly"))
                cost_str = (
                    f"{_format_cost(support_cost, c)}/mo"
                    if isinstance(support_cost, (int, float))
                    else "N/A"
                )
                lines.append(f"  {plan_key}: {cost_str}")

    return "\n".join(lines)


def format_search_results(
    results: list[dict[str, str]] | dict[str, list[dict[str, str]]],
    fmt: ResponseFormat,
) -> str:
    if fmt == ResponseFormat.JSON:
        return _json(results)

    if isinstance(results, list):
        if not results:
            return "No services found."
        return "\n".join(f"  {r['key']} -- {r['name']}" for r in results)

    lines: list[str] = []
    for term, matches in results.items():
        lines.append(f"[{term}] {len(matches)} results")
        for r in matches:
            lines.append(f"  {r['key']} -- {r['name']}")
    return "\n".join(lines)


def format_service_fields(
    services: list[dict[str, Any]],
    errors: list[str],
    fmt: ResponseFormat,
) -> str:
    if fmt == ResponseFormat.JSON:
        compact_services = []
        for svc_info in services:
            fields: list[ServiceField] = svc_info["fields"]
            compact_fields = []
            for f in fields:
                fd: dict[str, Any] = {"id": f.id, "type": f.type}
                if f.label:
                    fd["label"] = f.label
                if f.options:
                    fd["options"] = [o.id or o.label or "" for o in f.options]
                if f.unit_format:
                    fd["format"] = f.unit_format
                compact_fields.append(fd)
            compact_services.append(
                {
                    "key": svc_info["key"],
                    "name": svc_info["name"],
                    "fields": compact_fields,
                }
            )
        obj: dict[str, Any] = {"services": compact_services}
        if errors:
            obj["errors"] = errors
        return _json(obj)

    lines: list[str] = []
    for svc_info in services:
        name = svc_info.get("name") or svc_info["key"]
        text_fields: list[ServiceField] = svc_info["fields"]
        lines.append(f"{name} ({len(text_fields)} fields):")
        for f in text_fields:
            label = f" -- {f.label}" if f.label else ""
            lines.append(f"  {f.id} ({f.type}){label}")
            if f.options:
                opts = ", ".join(o.id or o.label or "" for o in f.options[:10])
                lines.append(f"    options: [{opts}]")
            if f.unit_format:
                lines.append(f"    format: {f.unit_format}")
        lines.append("")

    for err in errors:
        lines.append(f"error: {err}")

    return "\n".join(lines)


def format_estimate_created(estimate_id: str, name: str, fmt: ResponseFormat) -> str:
    if fmt == ResponseFormat.JSON:
        return _json({"id": estimate_id, "name": name})
    return f"Estimate created: {name}\nID: {estimate_id}"


def format_add_service_results(results: list[dict[str, Any]], fmt: ResponseFormat) -> str:
    if fmt == ResponseFormat.JSON:
        return _json({"results": results})

    added = sum(1 for r in results if r.get("status") == "added")
    lines = [f"{added} added"]
    for r in results:
        service = r.get("service", "")
        if r.get("status") == "added":
            lines.append(f"  + {service}")
        else:
            lines.append(f"  ! {service}: {r.get('error', 'unknown error')}")
    return "\n".join(lines)


def format_export_result(result: SaveResult, fmt: ResponseFormat) -> str:
    if fmt == ResponseFormat.JSON:
        return _json({"id": result.estimate_id, "url": result.shareable_url})
    return f"Estimate saved\nURL: {result.shareable_url}\nID: {result.estimate_id}"
