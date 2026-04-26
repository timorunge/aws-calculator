"""Tests for config key validation with Levenshtein fuzzy matching."""

import httpx

from aws_calculator.core.catalog import ManifestClient
from aws_calculator.core.types import Partition
from aws_calculator.core.validation import validate_config_keys
from tests.conftest import make_catalog_transport

FAKE_MANIFEST = {
    "awsServices": [
        {"key": "aWSLambda", "name": "AWS Lambda", "searchKeywords": []},
    ]
}

FAKE_LAMBDA_DEFINITION = {
    "version": "2.0.0",
    "serviceCode": "aWSLambda",
    "templates": [
        {
            "id": "t1",
            "inputComponents": [
                {"id": "numberOfRequests", "type": "numericInput"},
                {"id": "durationOfEachRequest", "type": "numericInput"},
            ],
        }
    ],
}


class TestValidateConfigKeys:
    async def test_invalid_returns_suggestions(self) -> None:
        transport = make_catalog_transport(FAKE_MANIFEST, {"aWSLambda": FAKE_LAMBDA_DEFINITION})
        async with httpx.AsyncClient(transport=transport) as http:
            catalog = ManifestClient(http)
            result = await validate_config_keys(
                "aWSLambda",
                {"numbrOfRequests": {"value": "100"}},
                catalog,
                Partition.AWS,
            )
        assert result is not None
        assert "numbrOfRequests" in result
        assert "numberOfRequests" in result

    async def test_skips_ec2(self) -> None:
        transport = make_catalog_transport(FAKE_MANIFEST, {"aWSLambda": FAKE_LAMBDA_DEFINITION})
        async with httpx.AsyncClient(transport=transport) as http:
            catalog = ManifestClient(http)
            result = await validate_config_keys(
                "ec2Enhancement",
                {"bogusField": "value"},
                catalog,
                Partition.AWS,
            )
        assert result is None
