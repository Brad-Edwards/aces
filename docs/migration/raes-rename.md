# RAES Rename Migration Map

Issue #866 renames the current project identity from Agentic Cyber Environment
System (ACES) to Reproducible Agentic Environments System (RAES). The rename is
surface-specific: RAES is the preferred current identity, while some ACES
identifiers remain because they are compatibility aliases, governed contract
ids, historical records, or external service names.

## Compatibility Rule

Use RAES for current prose, CLI examples, MCP discovery, and emitted public
titles. Keep ACES where the identifier is a published package, import namespace,
schema/profile id, wire discriminator, historical citation, accepted decision
record, generated artifact, or external integration that has not migrated.

Legacy ACES aliases are supported unless a future deprecation record names the
exact surface, replacement, notice window, and verification evidence required
by `specs/evolution/versioning-deprecation-and-migration.md`.

## Surface Map

| Surface class | Old identifier | Preferred identifier | Owner | Compatibility status | Notice/removal rule | Verification evidence |
|---|---|---|---|---|---|---|
| Project prose | Agentic Cyber Environment System (ACES), ACES SDL | Reproducible Agentic Environments System (RAES), RAES SDL | Repository docs | Migrated for current-state prose | Historical records remain unchanged | Docs build and prose review |
| Documentation paths | `docs/aces/` | `docs/aces/` | Documentation tree | Retained path for link compatibility | Rename requires redirect/link audit and docs build evidence | Docs build |
| Python distribution | `aces-sdl` | `aces-sdl` | `implementations/python/pyproject.toml` | Retained external package name | Rename requires package publication plan and release evidence | Version tests derive from `aces-sdl` metadata |
| Python import packages | `aces`, `aces_sdl`, `aces_mcp`, `aces_runtime`, `aces_contracts`, other `aces_*` packages | Unchanged | Python package owners | Retained source/API compatibility names | Rename requires package/module compatibility layer and import tests | Existing import, module-boundary, and package tests |
| CLI command | `aces` | `raes` | `aces_cli` | `aces` remains a supported console-script alias | Removal needs deprecation record and release notice | CLI version/help tests |
| MCP server command | `aces-mcp` | `raes-mcp` | `aces_mcp` | `aces-mcp` remains a supported console-script alias | Removal needs deprecation record and release notice | MCP construction and packaging tests |
| MCP server id | `aces-sdl` | `raes-sdl` | `aces_mcp.server` | Old id is documented as a legacy surface, not emitted by the current server | Re-emitting old id would be a compatibility decision on this surface | MCP server construction tests |
| MCP discovery tool | `aces_tool_surface` | `raes_tool_surface` | `aces_mcp.tools.operations` | Old tool remains a supported alias returning the RAES surface payload | Removal needs deprecation record and MCP client evidence | MCP tool-surface tests |
| MCP guidance tool | `aces_agent_guidance` | `raes_agent_guidance` | `aces_mcp.tools.operations` | Old tool remains a supported alias | Removal needs deprecation record and MCP client evidence | MCP guidance tests |
| MCP intended-use tool | `aces_intended_use_profiles` | `raes_intended_use_profiles` | `aces_mcp.tools.completeness` | Old tool remains a supported alias | Removal needs deprecation record and MCP client evidence | MCP intended-use tests |
| MCP reference-manifest tool | `aces_reference_manifests` | `raes_reference_manifests` | `aces_mcp.tools.operations` | Old tool remains a supported alias | Removal needs deprecation record and MCP client evidence | MCP advertised-tool tests |
| Agent guidance profile id | `aces-agent-guidance` | `aces-agent-guidance` | `specs/agent-guidance/agent-guidance.yaml` | Retained governed profile id | Rename requires checker, consumer, and migration evidence | `tools/check_agent_guidance.py` |
| Intended-use scope string | `aces-delivery-capability` | `raes-delivery-capability` | `aces_mcp.tools.completeness` | Old scope is emitted as `legacy_scope` | Removing `legacy_scope` needs deprecation record | MCP intended-use tests |
| Runtime OpenAPI title | ACES Runtime Control Plane | RAES Runtime Control Plane | `aces_runtime.control_plane_api` | Migrated emitted title | No compatibility promise for presentation title | Version-classification tests |
| HTTP headers and config keys | `x-aces-*`, `ACES_REQUIREMENT_UID` | Unchanged | Runtime/security and workflow owners | Retained integration names | Rename requires trusted-proxy/config alias handling and conflict tests | Runtime security and repo-policy gates |
| Published schemas and wire ids | `io.aces.*`, `aces-*`, contract discriminators | Unchanged | `contracts/` and ADR-061 schema publication | Retained governed contract identifiers | Rename requires schema-publication metadata, fixtures, parity checks, and lifecycle records | Contract and schema-publication checks |
| Processor/backend identities | `aces-reference-processor`, package-specific manifest ids | Unchanged | Manifest owners | Retained apparatus identity | Rename requires manifest compatibility evidence | Manifest and conformance tests |
| Release and external services | GitHub/Sonar/PyPI repository names and URLs | Current external names | Owning external services | Retained external references | Rename only after the external service exists and automation is updated | Release, CI, and policy checks |
| Accepted ADRs, changelog, research snapshots | Historical ACES references | Unchanged | Historical record owners | Retained history | Amend or supersede through existing record process | ADR immutability and docs checks |

## User Guidance

New command examples should use `raes` and `raes-mcp`. Existing `aces` and
`aces-mcp` command lines remain valid aliases for downstream users.

New MCP clients should start with `raes_tool_surface`, then call
`raes_agent_guidance` and `raes_intended_use_profiles`. Existing clients using
`aces_tool_surface`, `aces_agent_guidance`, `aces_intended_use_profiles`, or
`aces_reference_manifests` remain supported.

Do not rename SDL fields, schema ids, profile ids, package imports, or
published contract identifiers as part of ordinary prose cleanup. Those
surfaces have separate compatibility rules and must carry their own tests and
lifecycle evidence.
