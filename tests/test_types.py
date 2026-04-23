"""Tests for Pydantic models (estimate JSON parsing + tool input validation)."""

import pytest
from pydantic import ValidationError

from aws_calculator.core.types import (
    Estimate,
    GetEstimateInput,
)
from tests.conftest import (
    ECOMMERCE_PLATFORM_ESTIMATE_JSON,
    ENTERPRISE_DATA_PIPELINE_ESTIMATE_JSON,
    STARTUP_SAAS_ESTIMATE_JSON,
)


class TestEstimateModel:
    def test_startup_saas_parses(self) -> None:
        est = Estimate.model_validate(STARTUP_SAAS_ESTIMATE_JSON)
        assert est.name == "Startup SaaS Platform"
        assert est.total_cost.monthly == 2266.05
        assert len(est.services) == 10
        assert est.meta_data.currency == "USD"

    def test_ecommerce_parses_upfront_costs(self) -> None:
        est = Estimate.model_validate(ECOMMERCE_PLATFORM_ESTIMATE_JSON)
        assert est.total_cost.upfront == 6480.00
        backend_ec2 = est.services["amazonEC2-be1f7a8b-c9d0-1234-fabc-be1234567890"]
        assert backend_ec2.service_cost.upfront == 6480.00

    def test_calculation_components_parse(self) -> None:
        est = Estimate.model_validate(ENTERPRISE_DATA_PIPELINE_ESTIMATE_JSON)
        kinesis = est.services["amazonKinesis-1a2b3c4d-e5f6-7890-abcd-aabbccddeeff"]
        assert kinesis.calculation_components["numberOfShards"].value == "4"
        assert kinesis.calculation_components["numberOfShards"].unit == "shards"

    def test_defaults_for_minimal_json(self) -> None:
        minimal = {"name": "Bare", "services": {}, "totalCost": {"monthly": 0}}
        est = Estimate.model_validate(minimal)
        assert est.name == "Bare"
        assert est.meta_data.currency == "USD"


class TestGetEstimateInput:
    def test_empty_url_rejected(self) -> None:
        with pytest.raises(ValidationError, match="string_too_short"):
            GetEstimateInput(url_or_id="")

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            GetEstimateInput(url_or_id="abc123", bogus="field")  # type: ignore[call-arg]
