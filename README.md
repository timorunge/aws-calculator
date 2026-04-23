# aws-calculator

CLI and MCP server for reading shared
[AWS Pricing Calculator](https://calculator.aws) estimates.

Pass a calculator.aws URL or estimate ID and get the full estimate back --
services, configurations, costs, and groupings -- as plain text or JSON.

- No AWS account or credentials required
- Works with publicly shared estimate links
- Supports both global (`calculator.aws`) and ESC
  (`pricing.calculator.aws.eu`) endpoints
- Two interfaces: command-line tool and
  [MCP](https://modelcontextprotocol.io/) server

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Getting started

```bash
git clone https://github.com/timorunge/aws-calculator.git
cd aws-calculator
uv sync
```

The project provides two console scripts, available via `uv run`:

| Script | Entry point | Purpose |
|--------|-------------|---------|
| `aws-calculator` | `aws_calculator.cli:main` | Command-line interface |
| `aws-calculator-mcp-server` | `aws_calculator.server:main` | MCP server |

## CLI

### Commands

```bash
aws-calculator get-estimate <URL-or-ID>
aws-calculator list-services <URL-or-ID> [--group <name>]
aws-calculator get-service-detail <URL-or-ID> --service-key <key>
aws-calculator summarize <URL-or-ID>
```

All commands accept `-f json` or `--format json` for structured output
(default: `text`).

### Examples

```bash
# Estimate overview
aws-calculator get-estimate \
  "https://calculator.aws/#/estimate?id=<your-estimate-id>"

# List services, filter by group
aws-calculator list-services <your-estimate-id> --group Data

# Full configuration for one service
aws-calculator get-service-detail <your-estimate-id> \
  --service-key "<service-key>"

# Cost breakdown as JSON
aws-calculator summarize <your-estimate-id> -f json
```

### Sample output

```
My Estimate

Monthly cost: USD 241.21
Upfront cost: USD 0.00
Services: 4
Created: 2025-01-15T10:30:00.000Z
Estimate ID: <your-estimate-id>
```

## MCP server

### Configuration

Add the server to your MCP client configuration:

```json
{
  "mcpServers": {
    "aws-calculator": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/aws-calculator",
        "aws-calculator-mcp-server"
      ]
    }
  }
}
```

### Tools

| Tool | Description |
|------|-------------|
| `aws_calculator_get_estimate` | Estimate overview: name, total costs, service count, metadata |
| `aws_calculator_list_services` | All services with costs and config, filterable by group |
| `aws_calculator_get_service_detail` | Full configuration for one service: all parameters, values, units |
| `aws_calculator_summarize_estimate` | Cost breakdown with group subtotals, services ranked by cost |

All tools accept a full calculator.aws URL or a bare estimate ID. Bare IDs
default to the global endpoint. Pass a full `pricing.calculator.aws.eu` URL
to query the ESC endpoint.

All tools support `format: "text"` (default) and `format: "json"`.

### Typical workflow

1. `aws_calculator_get_estimate` -- get the overview
2. `aws_calculator_list_services` -- see what is in the estimate
3. `aws_calculator_get_service_detail` -- drill into a specific service
4. `aws_calculator_summarize_estimate` -- get a cost breakdown sorted by price

### MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run aws-calculator-mcp-server
```

### Sample tool output

#### aws_calculator_list_services

```
4 services in "My Estimate"

- Amazon EC2 | Europe (Frankfurt) | USD 63.07 | key: ec2-e01bdf4a-... -- Tenancy (Shared Instances), ...
- Amazon RDS for MySQL | Europe (Frankfurt) | USD 166.79 | key: rds-2e5fc3a0-... -- Storage amount (20 GB), ...
- Amazon CloudFront | Europe (Frankfurt) | USD 8.90 | key: cf-a1b2c3d4-...
- Amazon Simple Storage Service (S3) | Europe (Frankfurt) | USD 2.45 | key: s3-b2c3d4e5-...
```

#### aws_calculator_summarize_estimate

```
My Estimate

Total monthly: USD 241.21
Total upfront: USD 0.00

Services by cost:
  Amazon RDS for MySQL | Europe (Frankfurt) | USD 166.79
  Amazon EC2 | Europe (Frankfurt) | USD 63.07
  Amazon CloudFront | Europe (Frankfurt) | USD 8.90
  Amazon Simple Storage Service (S3) | Europe (Frankfurt) | USD 2.45
```

## Project structure

```
src/aws_calculator/
    core/               shared library
        client.py       HTTP client, URL parsing, caching
        discovery.py    runtime API URL discovery from config.js
        formatters.py   plain-text and JSON renderers
        types.py        Pydantic models for API responses and tool inputs
    cli.py              CLI entry point (argparse)
    server.py           MCP server entry point (FastMCP)
```

## Development

```bash
make install    # install all deps including dev
make check      # all quality gates (fmt, lint, type, test)
make test       # unit tests only (no network)
make test-ci    # all tests including integration (hits live API)
make help       # show all available targets
```

See [AGENTS.md](AGENTS.md) for code conventions and style rules.

## CI

GitHub Actions runs on every push and PR to `main`:

- **Format** -- `ruff format --check`
- **Lint** -- `ruff check`
- **Type check** -- `mypy --strict`
- **Test** -- `pytest` across Python 3.11--3.14

Releases are triggered by `v*` tags. All checks must pass before
creating a GitHub release.

## Related

For advanced AWS pricing queries beyond shared estimates -- such as looking
up on-demand rates, reserved pricing, or Savings Plans across services and
regions -- see the
[AWS Pricing MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-pricing-mcp-server)
from the official [awslabs/mcp](https://github.com/awslabs/mcp) collection.

## Good to know

- Shared estimates expire after one year (AWS platform behavior)
- Parameter names and values reflect the calculator API's internal
  representation, which is not always human-readable
- The CLI discovers the API URL at startup (adds ~1s latency on first run)

## License

MIT -- see [LICENSE](LICENSE).
