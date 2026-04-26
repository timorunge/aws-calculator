"""Manual CLI validation -- exercises every subcommand and flag combination.

Requires network access. Hits the live AWS Pricing Calculator API.
Creates its own estimates -- no hardcoded IDs that can expire.

Usage:
    uv run python tests/manual/test_cli.py
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CMD = ["uv", "run", "aws-calculator"]

PASS = 0
FAIL = 0


def _run(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        [*CMD, *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def _check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    status = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"  {status:4}  {name}")
    if not ok and detail:
        print(f"         {detail[:300]}")


def _check_run(name: str, expected: str, *args: str) -> str:
    rc, output = _run(*args)
    _check(name, rc == 0 and expected.lower() in output.lower(), output)
    return output


def _write_spec(spec: dict[str, Any]) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(spec, f)
        return f.name


def main() -> None:
    global PASS, FAIL

    print("=" * 50)
    print("  CLI Manual Test Suite")
    print("=" * 50)

    temp_files: list[str] = []

    try:
        # ============================================================
        # PHASE 1: Create a seed estimate for read tests
        # ============================================================
        print("\n--- setup: create seed estimate ---")

        spec_seed = {
            "name": "CLI Seed Estimate",
            "partition": "aws",
            "services": [
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
                    "description": "Asset storage",
                    "group": "Storage",
                    "calculationComponents": {
                        "s3StandardStorageSize": "500|gb|month",
                    },
                },
            ],
        }
        seed_path = _write_spec(spec_seed)
        temp_files.append(seed_path)

        _, seed_json = _run("compose-estimate", seed_path, "-f", "json")
        seed_id = ""
        seed_url = ""
        with contextlib.suppress(json.JSONDecodeError, KeyError):
            seed_data = json.loads(seed_json)
            seed_id = seed_data["id"]
            seed_url = seed_data["url"]

        _check(
            "create seed estimate",
            bool(seed_id) and "calculator.aws" in seed_url,
            seed_json,
        )
        print(f"         seed ID:  {seed_id}")
        print(f"         seed URL: {seed_url}")

        if not seed_id:
            print("\nFATAL: cannot continue without a seed estimate")
            sys.exit(1)

        # ============================================================
        # PHASE 2: Version
        # ============================================================
        print("\n--- version ---")
        _check_run("--version", "aws-calculator", "--version")

        # ============================================================
        # PHASE 3: Read commands (using seed estimate)
        # ============================================================
        print("\n--- read commands (bare ID, text) ---")
        _check_run("get-estimate (text)", "Monthly cost", "get-estimate", seed_id)
        _check_run("list-services (text)", "key:", "list-services", seed_id)
        _check_run("summarize (text)", "Services by cost", "summarize", seed_id)

        print("\n--- read commands (full URL, text) ---")
        _check_run("get-estimate (URL)", "Monthly cost", "get-estimate", seed_url)

        print("\n--- read commands (JSON) ---")
        _check_run(
            "get-estimate -f json",
            "monthly",
            "get-estimate",
            seed_id,
            "-f",
            "json",
        )
        list_json = _check_run(
            "list-services -f json",
            "services",
            "list-services",
            seed_id,
            "-f",
            "json",
        )
        _check_run(
            "summarize -f json",
            "monthly",
            "summarize",
            seed_id,
            "-f",
            "json",
        )

        # -- list-services --group --
        print("\n--- list-services --group ---")
        rc, output = _run("list-services", seed_id, "--group", "nonexistent_group_xyz")
        _check(
            "list-services --group (no match, expect exit 1)",
            rc == 1 and "no services found" in output.lower(),
            output,
        )
        _check_run(
            "list-services --group (match)",
            "Lambda",
            "list-services",
            seed_id,
            "--group",
            "Compute",
        )

        # -- get-service-detail --
        print("\n--- get-service-detail ---")
        first_key = ""
        with contextlib.suppress(json.JSONDecodeError, KeyError, IndexError):
            first_key = json.loads(list_json)["services"][0]["key"]

        if first_key:
            _check_run(
                "get-service-detail (text)",
                "Service code",
                "get-service-detail",
                seed_id,
                "--service-key",
                first_key,
            )
            _check_run(
                "get-service-detail -f json",
                "components",
                "get-service-detail",
                seed_id,
                "--service-key",
                first_key,
                "-f",
                "json",
            )
        else:
            print("  SKIP  get-service-detail (could not extract service key)")

        # ============================================================
        # PHASE 4: Catalog commands (no estimate needed)
        # ============================================================
        print("\n--- search-services ---")
        _check_run("search-services (text)", "lambda", "search-services", "lambda")
        _check_run(
            "search-services (json)",
            "key",
            "search-services",
            "lambda",
            "-f",
            "json",
        )
        _check_run(
            "search-services multi-term",
            "lambda",
            "search-services",
            "lambda, s3",
        )
        _check_run(
            "search-services --partition aws",
            "lambda",
            "search-services",
            "lambda",
            "--partition",
            "aws",
        )
        _check_run(
            "search-services --max-results 3",
            "Lambda",
            "search-services",
            "lambda",
            "--max-results",
            "3",
        )
        _check_run(
            "search-services --partition aws-esc",
            "Lambda",
            "search-services",
            "lambda",
            "--partition",
            "aws-esc",
        )

        print("\n--- get-service-fields ---")
        _check_run(
            "get-service-fields (text)",
            "fields",
            "get-service-fields",
            "aWSLambda",
        )
        _check_run(
            "get-service-fields (json)",
            "fields",
            "get-service-fields",
            "aWSLambda",
            "-f",
            "json",
        )
        _check_run(
            "get-service-fields multi-service",
            "fields",
            "get-service-fields",
            "aWSLambda, amazonS3Standard",
        )
        _check_run(
            "get-service-fields --partition aws-esc",
            "fields",
            "get-service-fields",
            "aWSLambda",
            "--partition",
            "aws-esc",
        )

        # ============================================================
        # PHASE 5: compose-estimate additional tests
        # ============================================================
        print("\n--- compose-estimate (text format) ---")
        _check_run(
            "compose-estimate (text)",
            "calculator.aws",
            "compose-estimate",
            seed_path,
        )

        print("\n--- compose-estimate (ESC) ---")
        spec_esc = {
            "name": "CLI Test ESC",
            "partition": "aws-esc",
            "services": [
                {
                    "serviceCode": "aWSLambda",
                    "region": "eusc-de-east-1",
                    "description": "EU sovereign handler",
                    "group": "Compute",
                    "calculationComponents": {
                        "numberOfRequests": "1000000",
                        "durationOfEachRequest": "150",
                    },
                },
            ],
        }
        esc_path = _write_spec(spec_esc)
        temp_files.append(esc_path)

        _check_run(
            "compose-estimate (ESC, text)",
            "pricing.calculator.aws.eu",
            "compose-estimate",
            esc_path,
        )

    finally:
        for p in temp_files:
            Path(p).unlink(missing_ok=True)

    # -- Summary --
    print()
    print("=" * 50)
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print("=" * 50)

    sys.exit(FAIL)


if __name__ == "__main__":
    main()
