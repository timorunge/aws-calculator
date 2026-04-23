# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] -- 2026-04-23

Initial release.

### Added

- **CLI** -- `get-estimate`, `list-services`, `get-service-detail`,
  `summarize`; all commands support `-f json` for structured output
- **MCP server** -- four read-only tools mirroring the CLI commands;
  stdio transport via FastMCP
- **Dual endpoint support** -- works with both the global calculator
  (`calculator.aws`) and the EU/ESC endpoint
  (`pricing.calculator.aws.eu`)
- **Runtime API discovery** -- extracts the estimate API URL from the
  calculator's `config.js` at startup; falls back to a hardcoded
  CloudFront URL for the global endpoint
- **Automatic re-discovery** -- on 403/404, re-runs discovery once and
  retries with the new URL before failing
- **In-memory caching** -- LRU cache (128 entries) avoids redundant
  fetches for the same estimate
- **Pydantic models** -- strict parsing and validation of the calculator
  API response; extra fields allowed for forward compatibility
- **SSRF protection** -- resolved URLs are checked against an allowlist
  of known calculator hosts
- **skills.sh skill** -- documents the CLI and MCP interfaces for LLM
  agents

[0.1.0]: https://github.com/timorunge/aws-calculator/releases/tag/v0.1.0
