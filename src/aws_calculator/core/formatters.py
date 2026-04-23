"""JSON and plain-text formatters for estimate data."""

from __future__ import annotations

import json
from typing import Any

from aws_calculator.core.types import Estimate, EstimateService, ResponseFormat

_MAX_COMPONENT_VALUE_LEN = 80


def _format_component_value(value: Any) -> str:
    """Render a component value as a short string."""
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
    return {
        "name": estimate.name,
        "total_monthly": estimate.total_cost.monthly,
        "total_upfront": estimate.total_cost.upfront,
        "service_count": len(estimate.services),
        "currency": estimate.meta_data.currency,
        "created_on": estimate.meta_data.created_on,
        "estimate_id": estimate.meta_data.estimate_id,
        "groups": list(estimate.groups.keys()) if estimate.groups else [],
    }


def _aggregate_group_costs(
    services: list[tuple[str, EstimateService]],
) -> dict[str, float]:
    costs: dict[str, float] = {}
    for _key, svc in services:
        g = svc.group or "(ungrouped)"
        costs[g] = costs.get(g, 0.0) + svc.service_cost.monthly
    return costs


def format_estimate_overview(estimate: Estimate, fmt: ResponseFormat) -> str:
    if fmt == ResponseFormat.JSON:
        return json.dumps(_build_overview_dict(estimate), indent=2)

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
        items = [
            {
                "key": key,
                "service_name": svc.service_name or "",
                "service_code": svc.service_code or "",
                "region": svc.region_name or svc.region or "",
                "monthly_cost": svc.service_cost.monthly,
                "config_summary": svc.config_summary,
                "group": svc.group,
            }
            for key, svc in services.items()
        ]
        return json.dumps(
            {
                "estimate_name": estimate.name,
                "service_count": len(items),
                "services": items,
            },
            indent=2,
        )

    c = estimate.meta_data.currency
    lines = [f'{len(services)} services in "{estimate.name}"', ""]

    grouped: dict[str | None, list[tuple[str, EstimateService]]] = {}
    for key, svc in services.items():
        grouped.setdefault(svc.group, []).append((key, svc))

    for group_name, group_services in grouped.items():
        if group_name:
            lines.append(f"[{group_name}]")

        for key, svc in group_services:
            region = svc.region_name or svc.region or ""
            cost = _format_cost(svc.service_cost.monthly, c)
            name = svc.service_name or ""
            config = f" -- {svc.config_summary}" if svc.config_summary else ""
            lines.append(f"- {name} | {region} | {cost} | key: {key}{config}")

        lines.append("")

    return "\n".join(lines)


def format_service_detail(
    key: str, service: EstimateService, fmt: ResponseFormat, currency: str = "USD"
) -> str:
    if fmt == ResponseFormat.JSON:
        components = {
            name: {"value": comp.value, "unit": comp.unit}
            for name, comp in service.calculation_components.items()
        }
        return json.dumps(
            {
                "key": key,
                "service_name": service.service_name or "",
                "service_code": service.service_code or "",
                "region": service.region_name or service.region or "",
                "monthly_cost": service.service_cost.monthly,
                "config_summary": service.config_summary,
                "description": service.description,
                "group": service.group,
                "calculation_components": components,
            },
            indent=2,
        )

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
        return json.dumps(
            {
                "estimate_name": estimate.name,
                "currency": estimate.meta_data.currency,
                "total_monthly": estimate.total_cost.monthly,
                "total_upfront": estimate.total_cost.upfront,
                "group_subtotals": group_costs,
                "services_by_cost": [
                    {
                        "service_name": svc.service_name or "",
                        "region": svc.region_name or svc.region or "",
                        "monthly_cost": svc.service_cost.monthly,
                        "group": svc.group,
                    }
                    for _key, svc in services_by_cost
                ],
                "support": estimate.support or None,
            },
            indent=2,
        )

    c = estimate.meta_data.currency
    lines = [
        estimate.name,
        "",
        f"Total monthly: {_format_cost(estimate.total_cost.monthly, c)}",
        f"Total upfront: {_format_cost(estimate.total_cost.upfront, c)}",
    ]

    if len(group_costs) > 1 or list(group_costs.keys()) != ["(ungrouped)"]:
        lines.append("")
        lines.append("Group subtotals:")
        for group_name, cost in sorted(group_costs.items(), key=lambda x: -x[1]):
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
