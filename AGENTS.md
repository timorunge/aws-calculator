# AGENTS.md

Code conventions for aws-calculator.

## Commands

```bash
make check          # all quality gates (fmt, lint, type, test)
make test           # unit tests only
make test-ci        # all tests including integration (live API)
make test-manual    # exercises every CLI/MCP tool against live API
```

Single test: `uv run pytest -v -k "test_name" tests/test_file.py`
MCP Inspector: `npx @modelcontextprotocol/inspector uv run aws-calculator-mcp-server`

Zero tolerance for lint, format, or type errors.

## Style

- Python 3.11+. `X | None` not `Optional[X]`.
- All source passes `ruff check`, `ruff format --check`, `mypy --strict`.
  `server.py` and `tools/*` have relaxed mypy (MCP SDK limitation).
- ASCII only -- no emojis, em-dashes, en-dashes, tree-drawing characters.
- Three import groups: stdlib, external, internal. Enforced by ruff.
- Guard clause pattern: return early, avoid nesting.
- Lowercase error messages. MCP tool handlers return error strings, never raise.
- Comments explain **why**, not **what**. Skip if the name and signature
  are self-describing. No `Parameters:`/`Returns:` sections.

## Testing

- **Unit tests**: mocked HTTP via `httpx.MockTransport`, no network.
- **Integration tests**: `@pytest.mark.integration`, hit live API.
- **Manual tests**: `tests/manual/`, exercise every CLI/MCP tool live.

Each test must earn its keep. No redundant edge cases, no tautological
tests, no one-test-per-guard-clause. Two tests hitting the same branch
should be collapsed. If it cannot fail, delete it.

`asyncio_mode = "auto"` -- no `@pytest.mark.asyncio` needed.

## Git

Conventional Commits: `<type>(<scope>): <subject>`

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore`

Scopes: `core`, `client`, `discovery`, `server`, `cli`, `types`,
`formatters`, `builder`, `catalog`, `save`, `ec2`, `validation`,
`tools`, `ci`, `docs`

Imperative present tense, no capital, no period, max 72 chars.

## Markdown

ASCII only. `--` for em-dashes. Wrap prose at ~80 chars.
