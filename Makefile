.DEFAULT_GOAL := help

.PHONY: install fmt fmt-fix lint lint-fix type test test-ci test-coverage test-manual check ci-local clean help

## install: Install all dependencies (including dev extras)
install:
	uv sync --all-extras

## fmt: Check formatting (fails on diff)
fmt:
	uv run ruff format --check .

## fmt-fix: Fix formatting (destructive)
fmt-fix:
	uv run ruff format .

## lint: Run linter
lint:
	uv run ruff check .

## lint-fix: Fix lint issues (destructive)
lint-fix:
	uv run ruff check --fix .

## type: Run type checker
type:
	uv run mypy

## test: Run unit tests
test:
	uv run pytest -m "not integration" -q

## test-ci: Run all tests including integration
test-ci:
	uv run pytest -q

## test-coverage: Run tests with coverage report
test-coverage:
	uv run pytest -m "not integration" --cov=aws_calculator --cov-report=term-missing

## test-manual: Run manual tests (hits live API)
test-manual:
	uv run python tests/manual/test_cli.py
	uv run python tests/manual/test_mcp.py

## check: Run all quality gates (fmt lint type test)
check: fmt lint type test

## ci-local: Run CI workflow locally via act
ci-local:
	@command -v act >/dev/null 2>&1 || { echo "error: act not installed. Run: brew install act"; exit 1; }
	act push -W .github/workflows/ci.yml

## clean: Remove build artifacts
clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

## help: Show this help
help:
	@echo "aws-calculator Makefile"
	@echo ""
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## //' | column -t -s ':'
