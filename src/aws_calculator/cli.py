"""Command-line interface for reading shared AWS Pricing Calculator estimates."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable

import httpx

from aws_calculator import __version__
from aws_calculator.core import (
    CALCULATOR_ESC_URL,
    CALCULATOR_GLOBAL_URL,
    EstimateClient,
    EstimateFetchError,
    ResponseFormat,
    discover_estimate_api_url,
    format_estimate_overview,
    format_estimate_summary,
    format_service_detail,
    format_services_list,
)

_MAX_KEYS_IN_ERROR = 5


async def _cmd_get_estimate(args: argparse.Namespace, client: EstimateClient) -> int:
    estimate = await client.get_estimate(args.url_or_id)
    print(format_estimate_overview(estimate, ResponseFormat(args.format)))
    return 0


async def _cmd_list_services(args: argparse.Namespace, client: EstimateClient) -> int:
    estimate = await client.get_estimate(args.url_or_id)

    services = estimate.services
    if args.group:
        group_lower: str = args.group.lower()
        services = {k: v for k, v in services.items() if v.group and group_lower in v.group.lower()}

    if not services:
        group_msg = f" in group '{args.group}'" if args.group else ""
        print(f"no services found{group_msg}.", file=sys.stderr)
        return 1

    print(format_services_list(estimate, services, ResponseFormat(args.format)))
    return 0


async def _cmd_get_service_detail(args: argparse.Namespace, client: EstimateClient) -> int:
    estimate = await client.get_estimate(args.url_or_id)

    service = estimate.services.get(args.service_key)
    if not service:
        available = ", ".join(f"'{k}'" for k in list(estimate.services.keys())[:_MAX_KEYS_IN_ERROR])
        n = len(estimate.services)
        more = f" (and {n - _MAX_KEYS_IN_ERROR} more)" if n > _MAX_KEYS_IN_ERROR else ""
        print(
            f"error: service key '{args.service_key}' not found in estimate. "
            f"available keys: {available}{more}. "
            f"use 'aws-calculator list-services' to see all service keys.",
            file=sys.stderr,
        )
        return 1

    print(
        format_service_detail(
            args.service_key, service, ResponseFormat(args.format), estimate.meta_data.currency
        )
    )
    return 0


async def _cmd_summarize(args: argparse.Namespace, client: EstimateClient) -> int:
    estimate = await client.get_estimate(args.url_or_id)
    print(format_estimate_summary(estimate, ResponseFormat(args.format)))
    return 0


_COMMANDS: dict[str, Callable[[argparse.Namespace, EstimateClient], Awaitable[int]]] = {
    "get-estimate": _cmd_get_estimate,
    "list-services": _cmd_list_services,
    "get-service-detail": _cmd_get_service_detail,
    "summarize": _cmd_summarize,
}


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("url_or_id", help="Calculator URL or bare estimate ID")
    common.add_argument(
        "-f",
        "--format",
        choices=["text", "json"],
        default="text",
        dest="format",
        help="output format (default: text)",
    )

    parser = argparse.ArgumentParser(
        prog="aws-calculator",
        description="Read shared AWS Pricing Calculator estimates.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "get-estimate",
        parents=[common],
        help="estimate overview (name, costs, metadata)",
    )

    ls = subparsers.add_parser(
        "list-services",
        parents=[common],
        help="list all services with costs and config",
    )
    ls.add_argument(
        "--group",
        default=None,
        help="filter services by group name (case-insensitive substring match)",
    )

    detail = subparsers.add_parser(
        "get-service-detail",
        parents=[common],
        help="full configuration for one service",
    )
    detail.add_argument(
        "--service-key",
        required=True,
        help="service key from the estimate (use list-services to find valid keys)",
    )

    subparsers.add_parser(
        "summarize",
        parents=[common],
        help="cost breakdown with group subtotals, services ranked by cost",
    )

    return parser


async def _run(args: argparse.Namespace) -> int:
    async with httpx.AsyncClient(
        headers={
            "Accept": "application/json",
            "User-Agent": f"aws-calculator/{__version__}",
        },
    ) as http_client:
        global_api_url, esc_api_url = await asyncio.gather(
            discover_estimate_api_url(http_client, CALCULATOR_GLOBAL_URL),
            discover_estimate_api_url(http_client, CALCULATOR_ESC_URL),
        )

        api_urls = {CALCULATOR_GLOBAL_URL: global_api_url}
        if esc_api_url:
            api_urls[CALCULATOR_ESC_URL] = esc_api_url

        client = EstimateClient(http_client, api_urls)

        handler = _COMMANDS[args.command]
        try:
            return await handler(args, client)
        except EstimateFetchError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
