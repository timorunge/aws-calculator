"""Command-line interface for reading and writing AWS Pricing Calculator estimates."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from aws_calculator import __version__
from aws_calculator.core import (
    CALCULATOR_ESC_URL,
    CALCULATOR_GLOBAL_URL,
    DEFAULT_REGION,
    CatalogError,
    EstimateBuilder,
    EstimateBuildError,
    EstimateClient,
    EstimateFetchError,
    ManifestClient,
    Partition,
    ResponseFormat,
    SaveClient,
    SaveError,
    discover_estimate_api_url,
    format_estimate_overview,
    format_estimate_summary,
    format_export_result,
    format_search_results,
    format_service_detail,
    format_service_fields,
    format_services_list,
)
from aws_calculator.core.types import MAX_KEYS_IN_ERROR


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
        available = ", ".join(f"'{k}'" for k in list(estimate.services.keys())[:MAX_KEYS_IN_ERROR])
        n = len(estimate.services)
        more = f" (and {n - MAX_KEYS_IN_ERROR} more)" if n > MAX_KEYS_IN_ERROR else ""
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


_READ_COMMANDS: dict[str, Callable[[argparse.Namespace, EstimateClient], Awaitable[int]]] = {
    "get-estimate": _cmd_get_estimate,
    "list-services": _cmd_list_services,
    "get-service-detail": _cmd_get_service_detail,
    "summarize": _cmd_summarize,
}


async def _cmd_search_services(args: argparse.Namespace, catalog: ManifestClient) -> int:
    partition = Partition(args.partition)
    manifest = await catalog.load_manifest(partition)
    results = catalog.search_services(manifest, args.query, args.max_results)
    print(format_search_results(results, ResponseFormat(args.format)))
    return 0


async def _cmd_get_service_fields(args: argparse.Namespace, catalog: ManifestClient) -> int:
    partition = Partition(args.partition)
    manifest = await catalog.load_manifest(partition)
    keys = [k.strip() for k in args.service.split(",") if k.strip()]
    services, errors = await catalog.resolve_fields(manifest, keys, partition)
    print(format_service_fields(services, errors, ResponseFormat(args.format)))
    return 1 if not services else 0


async def _cmd_compose_estimate(
    args: argparse.Namespace, catalog: ManifestClient, saver: SaveClient
) -> int:
    try:
        with open(args.services_file) as f:
            spec: dict[str, Any] = json.load(f)
    except FileNotFoundError:
        print(f"error: file not found: {args.services_file}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in {args.services_file}: {e}", file=sys.stderr)
        return 1

    name = spec.get("name", "My Estimate")
    partition_str = spec.get("partition", Partition.AWS.value)
    try:
        partition = Partition(partition_str)
    except ValueError:
        print(f"error: invalid partition '{partition_str}'", file=sys.stderr)
        return 1

    entries = spec.get("services") or []
    if not isinstance(entries, list):
        print("error: 'services' must be a JSON array", file=sys.stderr)
        return 1

    if not entries:
        print("error: no services in spec file", file=sys.stderr)
        return 1

    builder = EstimateBuilder(name, partition)
    for entry in entries:
        service_code = entry.get("serviceCode")
        if not service_code:
            print("error: service entry missing 'serviceCode' key", file=sys.stderr)
            return 1
        builder.add_service(
            service_code,
            region=entry.get("region", DEFAULT_REGION),
            description=entry.get("description", ""),
            calculation_components=entry.get("calculationComponents", {}),
            group=entry.get("group"),
        )

    payload = await builder.build_payload(catalog)
    result = await saver.save(payload, partition)
    print(format_export_result(result, ResponseFormat(args.format)))
    return 0


_CATALOG_COMMANDS: dict[str, Callable[[argparse.Namespace, ManifestClient], Awaitable[int]]] = {
    "search-services": _cmd_search_services,
    "get-service-fields": _cmd_get_service_fields,
}


def _build_parser() -> argparse.ArgumentParser:
    common_read = argparse.ArgumentParser(add_help=False)
    common_read.add_argument("url_or_id", help="Calculator URL or bare estimate ID")
    common_read.add_argument(
        "-f",
        "--format",
        choices=["text", "json"],
        default="text",
        dest="format",
        help="output format (default: text)",
    )

    _partition_choices = [p.value for p in Partition]

    common_partition = argparse.ArgumentParser(add_help=False)
    common_partition.add_argument(
        "--partition",
        choices=_partition_choices,
        default=Partition.AWS.value,
        help="AWS partition (default: aws)",
    )

    common_format = argparse.ArgumentParser(add_help=False)
    common_format.add_argument(
        "-f",
        "--format",
        choices=["text", "json"],
        default="text",
        dest="format",
        help="output format (default: text)",
    )

    parser = argparse.ArgumentParser(
        prog="aws-calculator",
        description="Read and create AWS Pricing Calculator estimates.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "get-estimate",
        parents=[common_read],
        help="estimate overview (name, costs, metadata)",
    )

    ls = subparsers.add_parser(
        "list-services",
        parents=[common_read],
        help="list all services with costs and config",
    )
    ls.add_argument(
        "--group",
        default=None,
        help="filter services by group name (case-insensitive substring match)",
    )

    detail = subparsers.add_parser(
        "get-service-detail",
        parents=[common_read],
        help="full configuration for one service",
    )
    detail.add_argument(
        "--service-key",
        required=True,
        help="service key from the estimate (use list-services to find valid keys)",
    )

    subparsers.add_parser(
        "summarize",
        parents=[common_read],
        help="cost breakdown with group subtotals, services ranked by cost",
    )

    search = subparsers.add_parser(
        "search-services",
        parents=[common_format, common_partition],
        help="search the AWS service catalog",
    )
    search.add_argument("query", help="search terms (comma-separated)")
    search.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="max results per term (default: 20)",
    )

    fields = subparsers.add_parser(
        "get-service-fields",
        parents=[common_format, common_partition],
        help="show configuration fields for a service",
    )
    fields.add_argument("service", help="service key(s), comma-separated")

    compose = subparsers.add_parser(
        "compose-estimate",
        parents=[common_format],
        help="create an estimate from a JSON spec file and save to calculator.aws",
    )
    compose.add_argument("services_file", help="path to JSON spec file")

    return parser


async def _run(args: argparse.Namespace) -> int:
    async with httpx.AsyncClient(
        headers={
            "Accept": "application/json",
            "User-Agent": f"aws-calculator/{__version__}",
        },
    ) as http_client:
        if args.command in _READ_COMMANDS:
            global_api_url, esc_api_url = await asyncio.gather(
                discover_estimate_api_url(http_client, CALCULATOR_GLOBAL_URL),
                discover_estimate_api_url(http_client, CALCULATOR_ESC_URL),
            )
            api_urls: dict[str, str] = {}
            if global_api_url:
                api_urls[CALCULATOR_GLOBAL_URL] = global_api_url
            if esc_api_url:
                api_urls[CALCULATOR_ESC_URL] = esc_api_url
            client = EstimateClient(http_client, api_urls)
            try:
                return await _READ_COMMANDS[args.command](args, client)
            except EstimateFetchError as e:
                print(f"error: {e}", file=sys.stderr)
                return 1

        catalog = ManifestClient(http_client)

        if args.command in _CATALOG_COMMANDS:
            try:
                return await _CATALOG_COMMANDS[args.command](args, catalog)
            except CatalogError as e:
                print(f"error: {e}", file=sys.stderr)
                return 1

        if args.command == "compose-estimate":
            saver = SaveClient(http_client)
            try:
                return await _cmd_compose_estimate(args, catalog, saver)
            except (CatalogError, EstimateBuildError, SaveError) as e:
                print(f"error: {e}", file=sys.stderr)
                return 1

        print(f"error: unknown command '{args.command}'", file=sys.stderr)
        return 1


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
