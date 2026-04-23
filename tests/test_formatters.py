"""Tests for plain-text and JSON formatters."""

import json

import pytest

from aws_calculator.core.formatters import (
    _format_component_value,
    format_estimate_overview,
    format_estimate_summary,
    format_service_detail,
    format_services_list,
)
from aws_calculator.core.types import Estimate, EstimateService, ResponseFormat


class TestFormatComponentValue:
    def test_truncates_long_values(self) -> None:
        long_list = list(range(50))
        result = _format_component_value(long_list)
        assert result.endswith("...")
        assert len(result) == 80

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(None, ""), ("hello", "hello")],
    )
    def test_passthrough_values(self, value: object, expected: str) -> None:
        assert _format_component_value(value) == expected


class TestFormatEstimateOverview:
    def test_text(self, startup_saas_estimate: Estimate) -> None:
        result = format_estimate_overview(startup_saas_estimate, ResponseFormat.TEXT)
        assert "Startup SaaS Platform" in result
        assert "USD 2,266.05" in result
        assert "Services: 10" in result

    def test_json(self, startup_saas_estimate: Estimate) -> None:
        result = format_estimate_overview(startup_saas_estimate, ResponseFormat.JSON)
        data = json.loads(result)
        assert data["name"] == "Startup SaaS Platform"
        assert data["total_monthly"] == 2266.05
        assert data["service_count"] == 10


class TestFormatServicesList:
    def test_lists_all_services_with_config(self, startup_saas_estimate: Estimate) -> None:
        result = format_services_list(
            startup_saas_estimate, startup_saas_estimate.services, ResponseFormat.TEXT
        )
        assert "Amazon EC2" in result
        assert "AWS Lambda" in result
        assert "Amazon RDS for PostgreSQL" in result
        assert "Amazon ElastiCache" in result
        assert "Amazon CloudFront" in result
        assert "m5.xlarge" in result

    def test_filter_by_group_json(self, enterprise_data_pipeline_estimate: Estimate) -> None:
        analytics = {
            k: v
            for k, v in enterprise_data_pipeline_estimate.services.items()
            if v.group and "analytics" in v.group.lower()
        }
        result = format_services_list(
            enterprise_data_pipeline_estimate, analytics, ResponseFormat.JSON
        )
        data = json.loads(result)
        assert data["service_count"] == 3
        names = {s["service_name"] for s in data["services"]}
        assert {"Amazon Athena", "Amazon SageMaker", "Amazon Redshift"} == names
        sagemaker = next(s for s in data["services"] if s["service_name"] == "Amazon SageMaker")
        assert isinstance(sagemaker["config_summary"], str)


class TestFormatServiceDetail:
    def test_text_with_components(self, startup_saas_estimate: Estimate) -> None:
        key = "AmazonRDS-d4e5f6a7-b8c9-0123-defa-444455556666"
        svc = startup_saas_estimate.services[key]
        result = format_service_detail(key, svc, ResponseFormat.TEXT)
        assert "Amazon RDS for PostgreSQL" in result
        assert "USD 751.20" in result
        assert "db.r5.2xlarge" in result
        assert "Multi-AZ" in result

    def test_json_with_components(self, enterprise_data_pipeline_estimate: Estimate) -> None:
        key = "AmazonSageMaker-6f7a8b9c-d0e1-2345-fabc-ff0011223344"
        svc = enterprise_data_pipeline_estimate.services[key]
        result = format_service_detail(key, svc, ResponseFormat.JSON)
        data = json.loads(result)
        assert data["service_name"] == "Amazon SageMaker"
        assert data["monthly_cost"] == 4320.00
        comps = data["calculation_components"]
        assert comps["trainingInstanceType"]["value"] == "ml.p3.2xlarge"
        assert comps["inferenceInstanceCount"]["value"] == "2"

    def test_components_without_units(self) -> None:
        svc = EstimateService.model_validate(
            {
                "serviceCode": "testSvc",
                "serviceName": "Test Service",
                "regionName": "US East (N. Virginia)",
                "serviceCost": {"monthly": 10.0},
                "calculationComponents": {
                    "paramA": {"value": "foo"},
                    "paramB": {"value": "bar"},
                },
            }
        )
        result = format_service_detail("test-key", svc, ResponseFormat.TEXT)
        assert "paramA: foo" in result
        assert "paramB: bar" in result


class TestFormatEstimateSummary:
    def test_text_with_groups(self, startup_saas_estimate: Estimate) -> None:
        result = format_estimate_summary(startup_saas_estimate, ResponseFormat.TEXT)
        assert "USD 2,266.05" in result
        assert "Group subtotals:" in result
        assert "Application" in result
        assert "Data" in result

    def test_json_cost_ordering_and_group_totals(self, startup_saas_estimate: Estimate) -> None:
        result = format_estimate_summary(startup_saas_estimate, ResponseFormat.JSON)
        data = json.loads(result)
        costs = [s["monthly_cost"] for s in data["services_by_cost"]]
        assert costs == sorted(costs, reverse=True)
        group_total = sum(data["group_subtotals"].values())
        assert abs(group_total - data["total_monthly"]) < 0.01

    def test_upfront_costs(self, ecommerce_platform_estimate: Estimate) -> None:
        result = format_estimate_summary(ecommerce_platform_estimate, ResponseFormat.JSON)
        data = json.loads(result)
        assert data["total_upfront"] == 6480.00

    def test_ungrouped_estimate_no_group_section(self, sample_estimate: Estimate) -> None:
        result = format_estimate_summary(sample_estimate, ResponseFormat.TEXT)
        assert "Group subtotals:" not in result

    def test_support_section_rendered(self) -> None:
        estimate = Estimate.model_validate(
            {
                "name": "With Support",
                "services": {},
                "groups": {},
                "totalCost": {"monthly": 100.00, "upfront": 0},
                "support": {
                    "businessSupport": {"monthlyCost": 100.0, "tier": "Business"},
                },
                "metaData": {"currency": "USD"},
            }
        )
        result = format_estimate_summary(estimate, ResponseFormat.TEXT)
        assert "Support:" in result
        assert "businessSupport" in result
        assert "USD 100.00/mo" in result
