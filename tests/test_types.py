"""Tests for Pydantic model validators in types.py."""

from aws_calculator.core.types import Estimate


class TestHoistGroupedServices:
    def test_services_under_groups_hoisted_to_top_level(self) -> None:
        data = {
            "name": "Grouped",
            "services": {},
            "groups": {
                "grp1": {
                    "name": "Web Tier",
                    "services": {
                        "svc-a": {
                            "serviceCode": "svcA",
                            "serviceName": "Service A",
                            "serviceCost": {"monthly": 10.0},
                        },
                    },
                },
            },
            "totalCost": {"monthly": 10.0},
        }
        estimate = Estimate.model_validate(data)
        assert "svc-a" in estimate.services
        assert estimate.services["svc-a"].group == "Web Tier"
