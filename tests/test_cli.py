"""Tests for the CLI module."""

from __future__ import annotations

import argparse
from unittest.mock import AsyncMock, patch

import pytest

from aws_calculator.cli import (
    _build_parser,
    _cmd_get_estimate,
    _cmd_get_service_detail,
    _cmd_list_services,
    _cmd_summarize,
    _run,
)
from aws_calculator.core.client import EstimateClient, EstimateFetchError
from aws_calculator.core.types import Estimate


def _mock_client(estimate: Estimate) -> AsyncMock:
    client = AsyncMock(spec=EstimateClient)
    client.get_estimate.return_value = estimate
    return client


def _make_args(**kwargs: object) -> argparse.Namespace:
    defaults = {"format": "text", "command": "get-estimate", "url_or_id": "abc123"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestBuildParser:
    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        parser = _build_parser()
        with pytest.raises(SystemExit, match="0"):
            parser.parse_args(["--version"])
        captured = capsys.readouterr()
        assert "aws-calculator" in captured.out

    def test_no_command_exits_with_error(self) -> None:
        parser = _build_parser()
        with pytest.raises(SystemExit, match="2"):
            parser.parse_args([])


class TestCmdGetEstimate:
    async def test_prints_overview_to_stdout(
        self, sample_estimate: Estimate, capsys: pytest.CaptureFixture[str]
    ) -> None:
        args = _make_args(command="get-estimate")
        result = await _cmd_get_estimate(args, _mock_client(sample_estimate))
        assert result == 0
        captured = capsys.readouterr()
        assert "Serverless API" in captured.out


class TestCmdListServices:
    async def test_group_filter_no_match_prints_stderr(
        self, sample_estimate: Estimate, capsys: pytest.CaptureFixture[str]
    ) -> None:
        args = _make_args(command="list-services", group="nonexistent")
        result = await _cmd_list_services(args, _mock_client(sample_estimate))
        assert result == 1
        captured = capsys.readouterr()
        assert "no services found" in captured.err


class TestCmdGetServiceDetail:
    async def test_unknown_key_prints_stderr(
        self, sample_estimate: Estimate, capsys: pytest.CaptureFixture[str]
    ) -> None:
        args = _make_args(command="get-service-detail", service_key="bad-key")
        result = await _cmd_get_service_detail(args, _mock_client(sample_estimate))
        assert result == 1
        captured = capsys.readouterr()
        assert "not found in estimate" in captured.err


class TestCmdSummarize:
    async def test_prints_summary_to_stdout(
        self, startup_saas_estimate: Estimate, capsys: pytest.CaptureFixture[str]
    ) -> None:
        args = _make_args(command="summarize")
        result = await _cmd_summarize(args, _mock_client(startup_saas_estimate))
        assert result == 0
        captured = capsys.readouterr()
        assert "Startup SaaS Platform" in captured.out


class TestRun:
    async def test_fetch_error_prints_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        args = _make_args(command="get-estimate")
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
