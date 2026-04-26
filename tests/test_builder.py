"""Tests for the EstimateBuilder module."""

from unittest.mock import patch

import httpx

from aws_calculator.core.builder import EstimateBuilder
from aws_calculator.core.catalog import ManifestClient
from tests.conftest import make_catalog_transport

_TEST_REGIONS = {
    "us-east-1": "US East (N. Virginia)",
    "us-west-2": "US West (Oregon)",
}


@patch("aws_calculator.core.builder._REGION_NAMES", _TEST_REGIONS)
class TestEstimateBuilder:
    async def test_build_payload_structure(self) -> None:
        transport = make_catalog_transport(
            {"awsServices": [{"key": "aWSLambda", "name": "AWS Lambda", "searchKeywords": []}]},
            {
                "aWSLambda": {
                    "version": "2.0.0",
                    "serviceCode": "aWSLambda",
                    "templates": [
                        {
                            "id": "t1",
                            "inputComponents": [{"id": "numberOfRequests", "type": "numericInput"}],
                        }
                    ],
                }
            },
        )
        async with httpx.AsyncClient(transport=transport) as http:
            catalog = ManifestClient(http)
            builder = EstimateBuilder(name="Test Estimate")
            builder.add_service(
                "aWSLambda",
                region="us-east-1",
                calculation_components={"numberOfRequests": "100"},
            )
            payload = await builder.build_payload(catalog)

        assert payload["name"] == "Test Estimate"
        assert payload["totalCost"] == {"monthly": 0, "upfront": 0}
        assert payload["metaData"]["currency"] == "USD"

        services = payload["services"]
        assert len(services) == 1
        svc = next(iter(services.values()))
        assert svc["serviceCode"] == "aWSLambda"
        assert svc["regionName"] == "US East (N. Virginia)"
        assert svc["version"] == "2.0.0"

    async def test_build_payload_grouped_services(self) -> None:
        manifest = {
            "awsServices": [
                {"key": "aWSLambda", "name": "AWS Lambda", "searchKeywords": []},
                {"key": "amazonS3Standard", "name": "Amazon S3 Standard", "searchKeywords": []},
            ]
        }
        transport = make_catalog_transport(manifest, {})
        async with httpx.AsyncClient(transport=transport) as http:
            catalog = ManifestClient(http)
            builder = EstimateBuilder()
            builder.add_service("aWSLambda", region="us-east-1", group="Compute")
            builder.add_service("amazonS3Standard", region="us-east-1", group="Storage")
            payload = await builder.build_payload(catalog)

        assert len(payload["services"]) == 0
        groups = payload["groups"]
        assert len(groups) == 2
        group_names = {g["name"] for g in groups.values()}
        assert group_names == {"Compute", "Storage"}

    async def test_build_payload_ec2_uses_transform(self) -> None:
        manifest = {
            "awsServices": [
                {
                    "key": "ec2Enhancement",
                    "name": "Amazon EC2",
                    "searchKeywords": ["ec2"],
                },
            ]
        }
        ec2_def = {
            "version": "1.5.0",
            "serviceCode": "ec2Enhancement",
            "templates": [{"id": "ec2-template-1"}],
        }
        transport = make_catalog_transport(manifest, {"ec2Enhancement": ec2_def})
        async with httpx.AsyncClient(transport=transport) as http:
            catalog = ManifestClient(http)
            builder = EstimateBuilder()
            builder.add_service(
                "ec2Enhancement",
                region="us-east-1",
                calculation_components={"instanceType": "m5.large", "quantity": "2"},
            )
            payload = await builder.build_payload(catalog)

        svc = next(iter(payload["services"].values()))
        calc = svc["calculationComponents"]
        assert "tenancy" in calc
        assert calc["workload"]["value"]["data"] == "2"
