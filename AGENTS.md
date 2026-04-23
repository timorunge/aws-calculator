# AGENTS.md

Code conventions and style rules for aws-calculator. This is the
authoritative reference for AI agents and contributors working on the codebase.

## Build / Lint / Test Commands

- `make check` -- all quality gates (fmt, lint, type, test)
- `make fmt` -- check formatting (`ruff format --check`)
- `make fmt-fix` -- auto-fix formatting (`ruff format`)
- `make lint` -- linter (`ruff check`)
- `make lint-fix` -- auto-fix lint issues (`ruff check --fix`)
- `make type` -- type checker (`mypy --strict`)
- `make test` -- unit tests only (no network)
- `make test-ci` -- all tests including integration (hits live API)
- `make test-coverage` -- unit tests with coverage report
- `make install` -- install all dependencies including dev extras
- `make ci-local` -- run CI workflow locally via `act`
- `make clean` -- remove build artifacts
- Single test: `uv run pytest -v -k "test_name" tests/test_file.py`
- MCP Inspector: `npx @modelcontextprotocol/inspector uv run aws-calculator-mcp-server`

Zero tolerance for lint, format, or type errors. Run `make check` before every
commit.

## Code Style

### Imports

Three groups separated by blank lines:

1. Standard library (`os`, `re`, `asyncio`, etc.)
2. External packages (`httpx`, `pydantic`, `mcp`, etc.)
3. Internal modules (`aws_calculator.core.types`, etc.)

Enforced by ruff (isort rules).

### File Organization

One module per concern. If a file needs section-divider banners, it is doing
too much -- split into a new module. No comment banners.

### Declaration Ordering

Per module, top to bottom:

1. Module docstring (if needed)
2. Imports (three groups)
3. Constants (`UPPER_SNAKE_CASE`)
4. Type definitions (Pydantic models, TypedDict, type aliases)
5. Classes
6. Functions
7. `if __name__ == "__main__":` guard (if applicable)

Within a class: class variables first, `__init__` next, public methods, then
private methods (`_prefixed`).

## Naming

- **Modules:** short, lowercase, underscores (`client`, `discovery`, `types`)
- **Classes:** PascalCase (`EstimateClient`, `ServiceGroup`)
- **Functions/methods:** snake_case (`get_estimate`, `parse_estimate_id`)
- **Constants:** SCREAMING_SNAKE_CASE (`DEFAULT_TIMEOUT`, `MAX_CACHE_SIZE`)
- **Variables:** short for short scope (`e`, `s`, `i`), descriptive for long
  (`estimate_id`, `calculator_base`)

## Type Annotations

- Python 3.11+ syntax throughout: `X | None` not `Optional[X]`, `list[T]` not
  `List[T]`
- All function signatures fully annotated (enforced by `mypy --strict`)
- `server.py` has relaxed mypy settings because the MCP SDK's `Context` type
  is not fully parameterizable

## Error Handling

- Guard clause pattern: return early, avoid nesting
- Never silently swallow exceptions -- no bare `except:` or `except Exception:`
  without re-raising or logging
- Use specific exception types where possible
- Lowercase error messages (they get wrapped into larger messages)
- MCP tool handlers: return user-facing error strings, do not raise

## Types and Patterns

- Pydantic models for all API response types and tool inputs
- `model_validator` for cross-field validation
- `StrEnum` for string-valued enumerations
- `X | None` for optional fields, not empty string sentinels

## Comment Discipline

### Docstrings

- Exported functions/classes: one sentence describing purpose. Multi-sentence
  only when behavior is non-obvious.
- No `Parameters:`, `Returns:`, `Raises:` sections -- the signature and type
  annotations convey this.
- Skip entirely if the name and signature are self-describing.

### Inline comments

- Never narrate the next line of code.
- Never restate a condition.
- Do comment: non-obvious algorithms, performance trade-offs, workarounds with
  references, "why not the obvious approach".

### Test code

- Test function docstrings almost never needed -- the test name documents intent.
- No section-divider banners in test code.

## Testing

Two layers:

- **Unit tests** -- mocked HTTP responses via `httpx.MockTransport`, no network
- **Integration tests** -- marked `@pytest.mark.integration`, hit live
  calculator.aws API

Rules:

- Each test must earn its keep -- no redundant edge cases
- No tautological tests -- if it cannot fail, delete it
- Two tests hitting the same branch should be collapsed
- Fixtures and helpers go in `conftest.py`
- `asyncio_mode = "auto"` -- no need for `@pytest.mark.asyncio`

## Git Conventions

Conventional Commits: `<type>(<scope>): <subject>`

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`,
`ci`, `chore`

Scopes: `core`, `client`, `discovery`, `server`, `cli`, `types`, `formatters`,
`ci`, `docs`

Rules: imperative present tense, no capital first letter, no period, max 72
chars. Use commit body for context when the change is non-obvious.

## Markdown Documentation

- ASCII only -- no emojis or special Unicode
- Use `--` for em-dashes
- Wrap prose at ~80 characters; code blocks and tables exempt
- Command blocks use `bash` language tag, no `$` prefix
