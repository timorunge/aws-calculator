"""Manual MCP tool validation -- exercises every tool with real API calls.

Requires network access. Hits the live AWS Pricing Calculator API.
Creates its own estimates -- no hardcoded IDs that can expire.

Usage:
    uv run python tests/manual/test_mcp.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from mcp.server.fastmcp import Context
from mcp.shared.context import RequestContext

from aws_calculator.core.types import (
    AddServiceInput,
    CreateEstimateInput,
    ExportEstimateInput,
    GetEstimateInput,
    GetServiceDetailInput,
    GetServiceFieldsInput,
    ListServicesInput,
    Partition,
    ResponseFormat,
    SearchServicesInput,
    SummarizeEstimateInput,
)
from aws_calculator.server import app_lifespan, mcp

PASS = 0
FAIL = 0


def _get_tool_fn(name: str) -> Any:
    return mcp._tool_manager._tools[name].fn


def _check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    status = "PASS" if ok else "FAIL"
    if not ok:
        FAIL += 1
        print(f"  {status:4}  {name}")
        if detail:
            print(f"         {detail[:300]}")
    else:
        PASS += 1
        print(f"  {status:4}  {name}")


async def main() -> None:
    global PASS, FAIL

    print("=" * 50)
    print("  MCP Manual Test Suite")
    print("=" * 50)

    fn_create = _get_tool_fn("aws_calculator_create_estimate")
    fn_add = _get_tool_fn("aws_calculator_add_service")
    fn_export = _get_tool_fn("aws_calculator_export_estimate")
    fn_get = _get_tool_fn("aws_calculator_get_estimate")
    fn_list = _get_tool_fn("aws_calculator_list_services")
    fn_detail = _get_tool_fn("aws_calculator_get_service_detail")
    fn_sum = _get_tool_fn("aws_calculator_summarize_estimate")
    fn_search = _get_tool_fn("aws_calculator_search_services")
    fn_fields = _get_tool_fn("aws_calculator_get_service_fields")

    async with app_lifespan(mcp) as lifespan_ctx:
        rc = RequestContext(
            request_id="manual-test",
            meta=None,
            session=None,  # type: ignore[arg-type]
            lifespan_context=lifespan_ctx,
        )
        ctx = Context(request_context=rc, fastmcp=mcp)

        # ============================================================
        # PHASE 1: Create a seed estimate for read tests
        # ============================================================
        print("\n--- setup: create seed estimate ---")

        result = await fn_create(CreateEstimateInput(name="MCP Seed Estimate"), ctx)
        _check("create seed estimate", "MCP Seed Estimate" in result)
        seed_builder_id = result.split("\n")[1].replace("ID: ", "").strip()

        result = await fn_add(
            AddServiceInput(
                estimate_id=seed_builder_id,
                services=json.dumps(
                    [
                        {
                            "serviceCode": "aWSLambda",
                            "region": "us-east-1",
                            "description": "API handler",
                            "group": "Compute",
                            "calculationComponents": {
                                "numberOfRequests": "5000000",
                                "durationOfEachRequest": "200",
                            },
                        },
                        {
                            "serviceCode": "amazonS3Standard",
                            "region": "us-east-1",
                            "group": "Storage",
                            "calculationComponents": {
                                "s3StandardStorageSize": "500|gb|month",
                            },
                        },
                        {
                            "serviceCode": "AmazonRoute53",
                            "region": "us-east-1",
                            "group": "Network",
                            "calculationComponents": {
                                "numberOfHostedZones": "5",
                            },
                        },
                    ]
                ),
            ),
            ctx,
        )
        _check("add seed services", "3 added" in result)

        result = await fn_export(
            ExportEstimateInput(estimate_id=seed_builder_id, format=ResponseFormat.JSON), ctx
        )
        seed_data = json.loads(result)
        seed_id = seed_data["id"]
        seed_url = seed_data["url"]
        _check("export seed estimate", bool(seed_id) and "calculator.aws" in seed_url)

        print(f"         seed ID:  {seed_id}")
        print(f"         seed URL: {seed_url}")

        # ============================================================
        # PHASE 2: Read tools (using seed estimate)
        # ============================================================
        print("\n--- read tools ---")

        result = await fn_get(GetEstimateInput(url_or_id=seed_id), ctx)
        _check("get_estimate (text, bare ID)", "Monthly cost" in result)

        result = await fn_get(GetEstimateInput(url_or_id=seed_url), ctx)
        _check("get_estimate (text, full URL)", "Monthly cost" in result)

        result = await fn_get(GetEstimateInput(url_or_id=seed_id, format=ResponseFormat.JSON), ctx)
        data = json.loads(result)
        _check("get_estimate (json)", "monthly" in data and "name" in data)

        result = await fn_list(ListServicesInput(url_or_id=seed_id), ctx)
        _check("list_services (text)", "key:" in result)

        result = await fn_list(
            ListServicesInput(url_or_id=seed_id, format=ResponseFormat.JSON), ctx
        )
        list_data = json.loads(result)
        _check("list_services (json)", len(list_data["services"]) > 0)
        first_key = list_data["services"][0]["key"]

        result = await fn_list(ListServicesInput(url_or_id=seed_id, group="NONEXISTENT"), ctx)
        _check("list_services (group filter, no match)", "no services found" in result)

        result = await fn_list(ListServicesInput(url_or_id=seed_id, group="Compute"), ctx)
        _check("list_services (group filter, match)", "Lambda" in result)

        result = await fn_detail(
            GetServiceDetailInput(url_or_id=seed_id, service_key=first_key), ctx
        )
        _check("get_service_detail (text)", "Service code" in result or "Key:" in result)

        result = await fn_detail(
            GetServiceDetailInput(
                url_or_id=seed_id, service_key=first_key, format=ResponseFormat.JSON
            ),
            ctx,
        )
        data = json.loads(result)
        _check("get_service_detail (json)", "components" in data)

        result = await fn_detail(
            GetServiceDetailInput(url_or_id=seed_id, service_key="nonexistent-key"),
            ctx,
        )
        _check("get_service_detail (bad key)", "error:" in result)

        result = await fn_sum(SummarizeEstimateInput(url_or_id=seed_id), ctx)
        _check("summarize_estimate (text)", "Services by cost" in result)

        result = await fn_sum(
            SummarizeEstimateInput(url_or_id=seed_id, format=ResponseFormat.JSON), ctx
        )
        data = json.loads(result)
        _check("summarize_estimate (json)", "services" in data and "monthly" in data)

        # ============================================================
        # PHASE 3: Catalog tools (no estimate needed)
        # ============================================================
        print("\n--- catalog tools ---")

        result = await fn_search(SearchServicesInput(query="lambda"), ctx)
        _check("search_services (text, single)", "aWSLambda" in result)

        result = await fn_search(
            SearchServicesInput(query="lambda", format=ResponseFormat.JSON), ctx
        )
        data = json.loads(result)
        _check("search_services (json, single)", isinstance(data, list) and len(data) > 0)

        result = await fn_search(
            SearchServicesInput(query="lambda, s3", format=ResponseFormat.JSON), ctx
        )
        data = json.loads(result)
        _check("search_services (multi-term)", "lambda" in data and "s3" in data)

        result = await fn_search(
            SearchServicesInput(query="ec2", max_results=2, format=ResponseFormat.JSON), ctx
        )
        data = json.loads(result)
        _check("search_services (max_results=2)", isinstance(data, list) and len(data) <= 2)

        result = await fn_search(
            SearchServicesInput(
                query="lambda", partition=Partition.AWS_ESC, format=ResponseFormat.JSON
            ),
            ctx,
        )
        data = json.loads(result)
        _check("search_services (aws-esc)", isinstance(data, list) and len(data) > 0)

        result = await fn_fields(GetServiceFieldsInput(service="aWSLambda"), ctx)
        _check("get_service_fields (text)", "fields" in result)

        result = await fn_fields(
            GetServiceFieldsInput(service="aWSLambda", format=ResponseFormat.JSON), ctx
        )
        data = json.loads(result)
        _check(
            "get_service_fields (json)",
            "services" in data and len(data["services"]) > 0,
        )

        result = await fn_fields(
            GetServiceFieldsInput(
                service="aWSLambda, amazonS3Standard", format=ResponseFormat.JSON
            ),
            ctx,
        )
        data = json.loads(result)
        _check("get_service_fields (multi-service)", len(data["services"]) == 2)

        result = await fn_fields(
            GetServiceFieldsInput(
                service="aWSLambda", partition=Partition.AWS_ESC, format=ResponseFormat.JSON
            ),
            ctx,
        )
        data = json.loads(result)
        _check("get_service_fields (aws-esc)", len(data["services"]) > 0)

        result = await fn_fields(GetServiceFieldsInput(service="nonexistentService123"), ctx)
        _check("get_service_fields (bad service)", "not found" in result)

        # ============================================================
        # PHASE 4: Estimate write tool edge cases
        # ============================================================
        print("\n--- estimate write edge cases ---")

        result = await fn_add(
            AddServiceInput(
                estimate_id="nonexistent-id",
                services=json.dumps({"serviceCode": "aWSLambda", "region": "us-east-1"}),
            ),
            ctx,
        )
        _check("add_service (bad estimate)", "error:" in result)

        result = await fn_add(
            AddServiceInput(estimate_id="x", services="not valid json"),
            ctx,
        )
        _check("add_service (invalid JSON)", "error:" in result)

        empty_result = await fn_create(CreateEstimateInput(name="Empty"), ctx)
        empty_id = empty_result.split("\n")[1].replace("ID: ", "").strip()

        result = await fn_add(
            AddServiceInput(
                estimate_id=empty_id,
                services=json.dumps({"region": "us-east-1"}),
            ),
            ctx,
        )
        _check("add_service (no serviceCode)", "missing" in result.lower())

        result = await fn_export(ExportEstimateInput(estimate_id=empty_id), ctx)
        _check("export_estimate (empty)", "error:" in result)

        result = await fn_export(ExportEstimateInput(estimate_id="no-such-builder"), ctx)
        _check("export_estimate (bad ID)", "error:" in result)

        # ============================================================
        # PHASE 5: ESC round-trip
        # ============================================================
        print("\n--- ESC round-trip ---")

        result = await fn_create(
            CreateEstimateInput(name="MCP Test ESC", partition=Partition.AWS_ESC), ctx
        )
        _check("create_estimate (esc)", "MCP Test ESC" in result)
        esc_id = result.split("\n")[1].replace("ID: ", "").strip()

        result = await fn_add(
            AddServiceInput(
                estimate_id=esc_id,
                services=json.dumps(
                    {
                        "serviceCode": "aWSLambda",
                        "region": "eusc-de-east-1",
                        "description": "ESC Lambda",
                        "calculationComponents": {
                            "numberOfRequests": "1000000",
                            "durationOfEachRequest": "100",
                        },
                    }
                ),
            ),
            ctx,
        )
        _check("add_service (esc)", "1 added" in result)

        result = await fn_export(ExportEstimateInput(estimate_id=esc_id), ctx)
        _check(
            "export_estimate (esc)",
            "pricing.calculator.aws.eu" in result,
            result,
        )

        if "ID:" in result:
            esc_saved_id = result.split("ID: ")[1].strip()
            esc_url = f"https://pricing.calculator.aws.eu/#/estimate?id={esc_saved_id}"
            result = await fn_get(GetEstimateInput(url_or_id=esc_url), ctx)
            _check(
                "read back ESC (get_estimate)",
                "MCP Test ESC" in result,
                result,
            )

        # ============================================================
        # PHASE 6: Edge cases
        # ============================================================
        print("\n--- edge cases ---")

        result = await fn_get(
            GetEstimateInput(url_or_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"), ctx
        )
        _check("get_estimate (404)", "error:" in result)

    # ============================================================
    # SUMMARY
    # ============================================================
    print()
    print("=" * 50)
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print("=" * 50)

    sys.exit(FAIL)


if __name__ == "__main__":
    asyncio.run(main())
