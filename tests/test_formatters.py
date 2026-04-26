"""Tests for plain-text and JSON formatters."""

import json

from aws_calculator.core.formatters import (
    format_estimate_overview,
    format_estimate_summary,
    format_service_detail,
)
from aws_calculator.core.types import Estimate, ResponseFormat


class TestFormatEstimateOverview:
    def test_text(self, startup_saas_estimate: Estimate) -> None:
        result = format_estimate_overview(startup_saas_estimate, ResponseFormat.TEXT)
        assert "Startup SaaS Platform" in result
        assert "USD 2,266.05" in result
        assert "Services: 10" in result


class TestFormatServiceDetail:
    def test_text_with_components(self, startup_saas_estimate: Estimate) -> None:
        key = "AmazonRDS-d4e5f6a7-b8c9-0123-defa-444455556666"
        svc = startup_saas_estimate.services[key]
        result = format_service_detail(key, svc, ResponseFormat.TEXT)
        assert "Amazon RDS for PostgreSQL" in result
        assert "USD 751.20" in result
        assert "db.r5.2xlarge" in result


class TestFormatEstimateSummary:
    def test_json_cost_ordering_and_group_totals(self, startup_saas_estimate: Estimate) -> None:
        result = format_estimate_summary(startup_saas_estimate, ResponseFormat.JSON)
        data = json.loads(result)
        costs = [s["monthly"] for s in data["services"]]
        assert costs == sorted(costs, reverse=True)
        group_total = sum(data["groups"].values())
        assert abs(group_total - data["monthly"]) < 0.01
