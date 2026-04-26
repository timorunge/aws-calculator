"""Tests for the CLI module."""

from __future__ import annotations

import argparse
import json
import pathlib
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from aws_calculator.cli import (
    _build_parser,
    _cmd_compose_estimate,
    _run,
)
from aws_calculator.core.catalog import ManifestClient
from aws_calculator.core.client import EstimateFetchError
from aws_calculator.core.save import SaveClient
from aws_calculator.core.types import Estimate
from tests.conftest import SAMPLE_ESTIMATE_JSON

FAKE_MANIFEST_JSON = {
    "awsServices": [
        {"key": "aWSLambda", "name": "AWS Lambda", "searchKeywords": ["serverless"]},
    ]
}

FAKE_LAMBDA_DEFINITION_JSON = {
    "version": "2.0.0",
    "serviceCode": "aWSLambda",
    "templates": [
        {
            "id": "t1",
            "inputComponents": [
                {"id": "numberOfRequests", "type": "numericInput", "label": "Requests"},
            ],
        }
    ],
}


class TestBuildParser:
    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        parser = _build_parser()
        with pytest.raises(SystemExit, match="0"):
            parser.parse_args(["--version"])
        captured = capsys.readouterr()
        assert "aws-calculator" in captured.out


class TestRun:
    async def test_fetch_error_prints_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        args = argparse.Namespace(format="text", command="get-estimate", url_or_id="abc123")
        with (
            patch(
                "aws_calculator.cli.discover_estimate_api_url",
                new_callable=AsyncMock,
                return_value="https://example.com/{estimateKey}",
            ),
            patch(
                "aws_calculator.cli.EstimateClient",
            ) as mock_cls,
        ):
            instance = mock_cls.return_value
            instance.get_estimate = AsyncMock(side_effect=EstimateFetchError("network failure"))
            result = await _run(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "network failure" in captured.err


class TestCmdListServices:
    async def test_group_no_match_exits_1(self, capsys: pytest.CaptureFixture[str]) -> None:
        args = argparse.Namespace(
            format="text", command="list-services", url_or_id="test", group="nonexistent"
        )
        with (
            patch(
                "aws_calculator.cli.discover_estimate_api_url",
                new_callable=AsyncMock,
                return_value="https://example.com/{estimateKey}",
            ),
            patch("aws_calculator.cli.EstimateClient") as mock_cls,
        ):
            instance = mock_cls.return_value
            instance.get_estimate = AsyncMock(
                return_value=Estimate.model_validate(SAMPLE_ESTIMATE_JSON)
            )
            result = await _run(args)
        assert result == 1
        assert "no services found" in capsys.readouterr().err


class TestCmdComposeEstimate:
    async def test_creates_and_saves(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        spec_file = tmp_path / "spec.json"
        spec_file.write_text(
            json.dumps(
                {
                    "name": "CLI Test",
                    "services": [
                        {"serviceCode": "aWSLambda", "region": "us-east-1"},
                    ],
                }
            )
        )

        def _save_handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "manifest" in url:
                return httpx.Response(200, json=FAKE_MANIFEST_JSON)
            if "aWSLambda" in url:
                return httpx.Response(200, json=FAKE_LAMBDA_DEFINITION_JSON)
            if "saveAs" in url:
                body = json.dumps({"savedKey": "c11ce7000123"})
                return httpx.Response(200, text=json.dumps({"statusCode": 200, "body": body}))
            return httpx.Response(404, json={})

        transport = httpx.MockTransport(_save_handler)
        async with httpx.AsyncClient(transport=transport) as http:
            catalog = ManifestClient(http)
            saver = SaveClient(http)
            args = argparse.Namespace(
                command="compose-estimate",
                services_file=str(spec_file),
                format="text",
            )
            result = await _cmd_compose_estimate(args, catalog, saver)

        assert result == 0
        captured = capsys.readouterr()
        assert "Estimate saved" in captured.out
        assert "c11ce7000123" in captured.out
