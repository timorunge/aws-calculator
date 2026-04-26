"""Tests for the EC2 config transform module."""

from aws_calculator.core.ec2 import transform_config


class TestTransformConfig:
    def test_minimal_config_has_required_fields(self) -> None:
        result = transform_config({})
        assert result["tenancy"] == {"value": "shared"}
        assert result["selectedOS"] == {"value": "linux"}
        assert result["workload"] == {"value": {"workloadType": "consistent", "data": "1"}}
        assert result["pricingStrategy"]["value"]["selectedOption"] == "on-demand"
        assert "dataTransferForEC2" in result
        assert "storageType" not in result

    def test_pricing_shorthand_compute_savings(self) -> None:
        result = transform_config({"pricingStrategy": "computeSavings1yrNoUpfront"})
        ps = result["pricingStrategy"]["value"]
        assert ps["selectedOption"] == "compute-savings"
        assert ps["term"] == "1 Year"
        assert ps["upfrontPayment"] == "None"
        assert ps["model"] == "computeSavings"

    def test_reserved_remapped_to_instance_savings_for_shared_tenancy(self) -> None:
        result = transform_config({"pricingStrategy": "reserved1yrNoUpfront", "tenancy": "shared"})
        ps = result["pricingStrategy"]["value"]
        assert ps["selectedOption"] == "instance-savings"
        assert ps["model"] == "instanceSavings"
