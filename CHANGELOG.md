# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] -- 2026-04-26

### Added

- **Write workflow** -- create estimates from scratch via CLI and MCP
  (`compose-estimate`, `create_estimate`, `add_service`,
  `export_estimate`)
- **Service catalog** -- `search-services` and `get-service-fields` CLI
  commands; `search_services` and `get_service_fields` MCP tools
- **Config key validation** -- fuzzy matching warns on invalid field IDs
  and suggests closest matches
- **EC2 config transform** -- pricing shorthand strings
  (`computeSavings1yrNoUpfront`) expand to the calculator's internal
  format; storage, tenancy, and workload defaults filled automatically
- **Four partitions** -- aws, aws-esc, aws-iso, aws-iso-b with
  partition-specific catalog CDNs, save APIs, and share URLs
- **MCP tool annotations** -- `readOnlyHint`, `destructiveHint`, etc.
  on all tools

### Changed

- **Spec format (breaking)** -- service entries now use AWS payload
  field names: `serviceCode`, `region`, `calculationComponents`,
  `description`, `group` (replaces `service` + flat `config` dict)
- **JSON output** -- compact separators, shortened keys (`monthly` not
  `total_monthly`, `name` not `estimate_name`), null fields omitted
- **MCP server instructions** -- condensed with workflow hints
- **Tool docstrings** -- terse, workflow-aware
- **Field descriptions** -- shortened for smaller tool schemas

### Fixed

- **EC2 spot pricing** -- no longer sends irrelevant `upfrontPayment`
  and `term` fields
- **Nested group flattening** -- recursively processes group
  hierarchies in estimate responses

## [0.1.0] -- 2026-04-23

Initial release.

### Added

- **CLI** -- `get-estimate`, `list-services`, `get-service-detail`,
  `summarize`; all commands support `-f json`
- **MCP server** -- four read-only tools via FastMCP stdio transport
- **Dual endpoint support** -- global (`calculator.aws`) and ESC
  (`pricing.calculator.aws.eu`)
- **Runtime API discovery** -- extracts estimate API URL from
  `config.js`; falls back to hardcoded CloudFront URL
- **Auto re-discovery** -- on 403, re-discovers and retries once
- **LRU caching** -- 128-entry cache for fetched estimates
- **Pydantic models** -- strict parsing with `extra="allow"` for
  forward compatibility
- **SSRF protection** -- resolved URLs checked against known hosts

[0.2.0]: https://github.com/timorunge/aws-calculator/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/timorunge/aws-calculator/releases/tag/v0.1.0
