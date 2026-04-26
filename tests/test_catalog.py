"""Tests for the ManifestClient catalog module."""

import base64
import json

import httpx

from aws_calculator.core.catalog import (
    ManifestClient,
    _decode_json,
)
from aws_calculator.core.types import ServiceEntry

FAKE_MANIFEST_JSON = {
    "awsServices": [
        {"key": "aWSLambda", "name": "AWS Lambda", "searchKeywords": ["serverless", "function"]},
        {"key": "amazonS3Standard", "name": "Amazon S3 Standard", "searchKeywords": ["storage"]},
        {
            "key": "ec2Enhancement",
            "name": "Amazon EC2",
            "isActive": "true",
            "searchKeywords": ["ec2", "compute"],
        },
        {"key": "oldService", "name": "Old Service", "isActive": "false", "searchKeywords": []},
        {
            "key": "subSelector",
            "name": "Sub Selector",
            "subType": "subServiceSelector",
            "searchKeywords": [],
        },
    ]
}

FAKE_LAMBDA_DEFINITION_JSON = {
    "version": "2.0.0",
    "serviceCode": "aWSLambda",
    "templates": [
        {
            "id": "lambda-template-1",
            "inputComponents": [
                {"id": "numberOfRequests", "type": "numericInput", "label": "Number of requests"},
                {"id": "durationOfEachRequest", "type": "numericInput", "label": "Duration"},
                {
                    "id": "memoryAllocated",
                    "subType": "dropdown",
                    "label": "Memory",
                    "options": [
                        {"id": "128", "label": "128 MB"},
                        {"id": "256", "label": "256 MB"},
                    ],
                },
                {"id": "numberOfRequestsWithoutFreeTier", "type": "numericInput"},
                {"id": "someField_MVP", "type": "numericInput"},
                {"id": "decorative", "type": "input", "subType": "bodyText"},
                {"id": "numberOfRequests", "type": "numericInput", "label": "Duplicate"},
            ],
        }
    ],
}


def _mock_transport(responses: dict[str, tuple[int, dict]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        for pattern, (status, body) in responses.items():
            if pattern in str(request.url):
                return httpx.Response(status, json=body)
        return httpx.Response(404, json={})

    return httpx.MockTransport(handler)


class TestLoadManifest:
    async def test_indexes_by_key(self) -> None:
        transport = _mock_transport({"/manifest/en_US.json": (200, FAKE_MANIFEST_JSON)})
        async with httpx.AsyncClient(transport=transport) as http:
            client = ManifestClient(http)
            manifest = await client.load_manifest()
        assert "aWSLambda" in manifest
        assert manifest["aWSLambda"].name == "AWS Lambda"


class TestSearchServices:
    def test_filters_inactive_and_sub_selectors(self) -> None:
        manifest = {
            k: ServiceEntry.model_validate(v)
            for k, v in {
                "aWSLambda": {
                    "key": "aWSLambda",
                    "name": "AWS Lambda",
                    "searchKeywords": ["serverless"],
                },
                "oldService": {
                    "key": "oldService",
                    "name": "Old",
                    "isActive": "false",
                    "searchKeywords": ["old"],
                },
                "subSelector": {
                    "key": "subSelector",
                    "name": "Sub",
                    "subType": "subServiceSelector",
                    "searchKeywords": ["sub"],
                },
            }.items()
        }
        results = ManifestClient.search_services(manifest, "lambda")
        assert isinstance(results, list)
        assert any(r["key"] == "aWSLambda" for r in results)

        multi = ManifestClient.search_services(manifest, "old, sub")
        assert isinstance(multi, dict)
        assert len(multi["old"]) == 0
        assert len(multi["sub"]) == 0


class TestFetchDefinition:
    async def test_happy_path(self) -> None:
        transport = _mock_transport(
            {
                "/manifest/en_US.json": (200, FAKE_MANIFEST_JSON),
                "/data/aWSLambda/en_US.json": (200, FAKE_LAMBDA_DEFINITION_JSON),
            }
        )
        async with httpx.AsyncClient(transport=transport) as http:
            client = ManifestClient(http)
            manifest = await client.load_manifest()
            definition = await client.fetch_definition(manifest, "aWSLambda")
        assert definition is not None
        assert definition["version"] == "2.0.0"


class TestExtractFields:
    def test_dedup_and_filtering(self) -> None:
        fields = ManifestClient.extract_fields(FAKE_LAMBDA_DEFINITION_JSON)
        ids = [f.id for f in fields]
        assert "numberOfRequests" in ids
        assert "memoryAllocated" in ids
        assert ids.count("numberOfRequests") == 1
        assert "numberOfRequestsWithoutFreeTier" not in ids
        assert "someField_MVP" not in ids
        assert "decorative" not in ids


class TestDecodeJson:
    def test_base64_encoded(self) -> None:
        payload = {"services": [1, 2]}
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        resp = httpx.Response(200, content=encoded.encode())
        assert _decode_json(resp) == payload
