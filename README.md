# aws-calculator

CLI and MCP server for reading and creating
[AWS Pricing Calculator](https://calculator.aws) estimates.

- No AWS account or credentials required
- Works with publicly shared estimate links
- Supports global (`calculator.aws`), ESC
  (`pricing.calculator.aws.eu`), and isolated (ISO/ISO-B) partitions
- Two interfaces: command-line tool and
  [MCP](https://modelcontextprotocol.io/) server

## Getting started

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/timorunge/aws-calculator.git
cd aws-calculator
uv sync
```

Optional -- region display names (e.g. "US East (N. Virginia)") via
botocore:

```bash
uv sync --extra regions
```

Two console scripts are available via `uv run`:

- `aws-calculator` -- command-line interface
- `aws-calculator-mcp-server` -- MCP server

## CLI

### Read commands

```bash
aws-calculator get-estimate <URL-or-ID>
aws-calculator list-services <URL-or-ID> [--group <name>]
aws-calculator get-service-detail <URL-or-ID> --service-key <key>
aws-calculator summarize <URL-or-ID>
```

### Write commands

```bash
aws-calculator search-services <query> [--partition aws|aws-esc|aws-iso|aws-iso-b] [--max-results N]
aws-calculator get-service-fields <service-key> [--partition aws|aws-esc|aws-iso|aws-iso-b]
aws-calculator compose-estimate <spec-file>
```

All commands accept `-f json` for structured output (default: `text`).

### Spec file format

```json
{
  "name": "My Estimate",
  "partition": "aws",
  "services": [
    {
      "serviceCode": "aWSLambda",
      "region": "us-east-1",
      "description": "API handler",
      "group": "Compute",
      "calculationComponents": {
        "numberOfRequests": "1000000"
      }
    }
  ]
}
```

Use `search-services` to find service keys and `get-service-fields` to
discover valid `calculationComponents` fields.

## MCP server

### Configuration

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
| `aws_calculator_get_estimate` | Estimate overview: name, costs, service count, metadata |
| `aws_calculator_list_services` | Services with costs and config, filterable by group |
| `aws_calculator_get_service_detail` | Full configuration for one service |
| `aws_calculator_summarize_estimate` | Cost breakdown with group subtotals, ranked by cost |
| `aws_calculator_search_services` | Search service catalog by name or keyword |
| `aws_calculator_get_service_fields` | Configuration fields for a service (IDs, types, options) |
| `aws_calculator_create_estimate` | Start a new in-memory estimate |
| `aws_calculator_add_service` | Add services (serviceCode, region, calculationComponents) |
| `aws_calculator_export_estimate` | Save and return a shareable URL |

### Workflows

**Read** (have a calculator.aws URL):
get_estimate > list_services > get_service_detail > summarize_estimate

**Write** (create from scratch):
search_services > get_service_fields > create_estimate > add_service > export_estimate

### MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run aws-calculator-mcp-server
```

## Partitions

| Partition | Value | Catalog | Share URL |
|-----------|-------|---------|-----------|
| Commercial | `aws` | Global CDN | `calculator.aws` |
| European Sovereign Cloud | `aws-esc` | ESC endpoint | `pricing.calculator.aws.eu` |
| ISO | `aws-iso` | ISO CDN path | `calculator.aws` (with contract) |
| ISO-B | `aws-iso-b` | ISO-B CDN path | `calculator.aws` (with contract) |

Read tools auto-detect partition from the URL. Write tools use the
partition set in `create_estimate` or the spec file.

## Development

```bash
make check        # all quality gates (fmt, lint, type, test)
make test         # unit tests only (no network)
make test-ci      # all tests including integration
make test-manual  # exercises every CLI/MCP tool against live API
```

See [AGENTS.md](AGENTS.md) for code conventions.

## CI

GitHub Actions on push/PR to `main`: format, lint, type check, and
tests across Python 3.11--3.14. Releases triggered by `v*` tags.

## Notes

- Shared estimates expire after one year (AWS platform behavior)
- The CLI discovers the API URL at startup (~1s latency on first run)
- Parameter names reflect the calculator API's internal representation

## Related

[AWS Pricing MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-pricing-mcp-server)
from [awslabs/mcp](https://github.com/awslabs/mcp) -- for on-demand
rates, reserved pricing, and Savings Plans queries.

## License

MIT -- see [LICENSE](LICENSE).
