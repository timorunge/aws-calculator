"""Tests for the SaveClient module."""

import json

import httpx

from aws_calculator.core.save import SaveClient
from aws_calculator.core.types import Partition


def _double_encode(body: dict) -> str:
    return json.dumps({"statusCode": 200, "body": json.dumps(body)})


class TestSaveClient:
    async def test_save_happy_path(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text=_double_encode({"savedKey": "abc123def456"}))

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http:
            client = SaveClient(http)
            result = await client.save({"name": "test"}, Partition.AWS)

        assert result.estimate_id == "abc123def456"
        assert "calculator.aws" in result.shareable_url

    async def test_save_esc_uses_esc_url(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "eusc-de-east-1" in str(request.url)
            return httpx.Response(200, text=_double_encode({"savedKey": "e5c0001234ab"}))

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http:
            client = SaveClient(http)
            result = await client.save({"name": "test"}, Partition.AWS_ESC)

        assert "pricing.calculator.aws.eu" in result.shareable_url
