---
name: aws-calculator
description: Read shared AWS Pricing Calculator estimates via CLI or MCP. Use when the user pastes a calculator.aws or pricing.calculator.aws.eu URL, mentions an estimate ID, asks about AWS cost estimates, wants to break down pricing for a shared calculator link, or needs to wire up the MCP server for estimate lookups. No AWS credentials required.
license: MIT
compatibility: Requires Python 3.11+ and uv. No AWS account or credentials needed.
metadata:
  author: timorunge
  version: "0.1.0"
---

# aws-calculator

CLI for reading shared AWS Pricing Calculator estimates. Pass a URL or
estimate ID, get costs and configurations back as plain text or JSON.

## Decision tree

```
What does the user need?
+- Pasted a calculator.aws URL or estimate ID
|  +- Wants a quick overview -> get-estimate
|  +- Wants to see all services -> list-services
|  +- Wants detail on one service -> get-service-detail
|  `- Wants a cost breakdown -> summarize
+- Wants JSON output
|  `- Add -f json to any command
+- Wants to filter by group
|  `- list-services --group <name>
`- Wants to compare services by cost
   `- summarize (services sorted highest to lowest)
```

## Installation

```bash
git clone https://github.com/timorunge/aws-calculator.git
cd aws-calculator
uv sync
uv run aws-calculator <command> ...
```

## CLI commands

| Command | Description |
|---------|-------------|
| `get-estimate` | Estimate overview: name, monthly/upfront costs, service count, creation date |
| `list-services` | All services with region, cost, config summary, and service key |
| `get-service-detail` | Full configuration for one service: all parameters, values, units |
| `summarize` | Cost breakdown with group subtotals, services ranked by cost |

### Shared options

All commands take these arguments:

| Argument | Description |
|----------|-------------|
| `url_or_id` | Calculator URL or bare estimate ID (positional, required) |
| `-f` / `--format` | Output format: `text` (default) or `json` |

Accepted URL forms:

- `https://calculator.aws/#/estimate?id=<id>`
- `https://pricing.calculator.aws.eu/#/estimate?id=<id>`
- `calculator.aws/#/estimate?id=<id>` (no scheme)
- `<bare-hex-id>` (defaults to global endpoint)

### get-estimate

```bash
aws-calculator get-estimate "https://calculator.aws/#/estimate?id=abc123"
```

```
My Estimate

Monthly cost: USD 241.21
Upfront cost: USD 0.00
Services: 4
Created: 2025-01-15T10:30:00.000Z
Estimate ID: abc123
```

### list-services

```bash
aws-calculator list-services <id>
aws-calculator list-services <id> --group Data
```

| Option | Description |
|--------|-------------|
| `--group <name>` | Filter by group name (case-insensitive substring match) |

```
4 services in "My Estimate"

- Amazon EC2 | Europe (Frankfurt) | USD 63.07 | key: ec2-e01bdf4a-...
- Amazon RDS for MySQL | Europe (Frankfurt) | USD 166.79 | key: rds-2e5fc3a0-...
- Amazon CloudFront | Europe (Frankfurt) | USD 8.90 | key: cf-a1b2c3d4-...
- Amazon S3 | Europe (Frankfurt) | USD 2.45 | key: s3-b2c3d4e5-...
```

### get-service-detail

```bash
aws-calculator get-service-detail <id> --service-key "rds-2e5fc3a0-..."
```

| Option | Required | Description |
|--------|----------|-------------|
| `--service-key <key>` | Yes | Service key from list-services output |

Returns the full configuration: every parameter name, value, and unit.

### summarize

```bash
aws-calculator summarize <id>
aws-calculator summarize <id> -f json
```

```
My Estimate

Total monthly: USD 241.21
Total upfront: USD 0.00

Services by cost:
  Amazon RDS for MySQL | Europe (Frankfurt) | USD 166.79
  Amazon EC2 | Europe (Frankfurt) | USD 63.07
  Amazon CloudFront | Europe (Frankfurt) | USD 8.90
  Amazon S3 | Europe (Frankfurt) | USD 2.45
```

## Typical workflow

1. Get the overview to confirm the estimate loads:

   ```bash
   aws-calculator get-estimate <url-or-id>
   ```

2. List services to find service keys:

   ```bash
   aws-calculator list-services <url-or-id>
   ```

3. Drill into a specific service:

   ```bash
   aws-calculator get-service-detail <url-or-id> --service-key "<key>"
   ```

4. Get the full cost breakdown:

   ```bash
   aws-calculator summarize <url-or-id>
   ```

For structured processing, add `-f json` to any step:

```bash
aws-calculator summarize <url-or-id> -f json
```

## MCP server

aws-calculator also ships as an MCP server. If your agent already has the
`aws-calculator-mcp-server` connected, prefer the MCP tools over the CLI
-- they avoid the per-invocation startup cost and return structured data
directly.

MCP client configuration:

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

| MCP tool | CLI equivalent |
|----------|----------------|
| `aws_calculator_get_estimate` | `get-estimate` |
| `aws_calculator_list_services` | `list-services` |
| `aws_calculator_get_service_detail` | `get-service-detail` |
| `aws_calculator_summarize_estimate` | `summarize` |

All MCP tools accept the same `url_or_id` and `format` parameters as
the CLI commands.

## Gotchas

- **Startup latency** -- the CLI discovers the API URL from the
  calculator's config.js at startup, adding roughly 1 second on each
  invocation.
- **Bare IDs default to the global endpoint.** To query the EU/ESC
  endpoint, pass the full `pricing.calculator.aws.eu` URL.
- **Shared estimates expire after one year** (AWS platform behavior).
- **Parameter names in service detail reflect the calculator API's
  internal representation**, which is not always human-readable.
- **get-service-detail requires a service key.** Run list-services first
  to find valid keys.
