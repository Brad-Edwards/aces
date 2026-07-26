# RAES Rename Migration Map

Issue #866 hard-cuts the current project identity from Agentic Cyber
Environment System (ACES) to Reproducible Agentic Environments System (RAES).
Repository-owned current prose, package distribution metadata, command examples,
MCP discovery, MCP public tool names, emitted public titles, and
machine-readable guidance identifiers use RAES.

Old ACES public command and MCP aliases are removed, not preserved as
compatibility surfaces.

## Cutover Rule

Use RAES for current user-facing and machine-readable surfaces owned by this
repository. Do not add new ACES aliases for current public commands, MCP tools,
package distribution metadata, or guidance profile identifiers.

Keep ACES only when the identifier is one of these historical or governed
surfaces:

- governed SDL, schema, profile, fixture, provenance, or wire identifier whose
  rename requires a separate versioned contract migration
- retained documentation path or asset-inventory reference that still has
  tests, links, or downstream evidence attached to the old path
- workflow or quality-service key owned by external automation
- accepted historical decision record, changelog history, research snapshot,
  archived citation, external URL, or third-party reference

## Surface Map

| Surface class | Old identifier | Current identifier | Owner | Status | Verification evidence |
|---|---|---|---|---|---|
| Project prose | Agentic Cyber Environment System (ACES), ACES SDL | Reproducible Agentic Environments System (RAES), RAES SDL | Repository docs | Migrated for current-state prose | Docs build and prose review |
| Documentation links | `Brad-Edwards/aces` current README/docs links | `RAESystem/rae` | Current README and docs config | Migrated for current user-facing links | Docs build |
| Documentation paths | `docs/aces/` | `docs/raes/` | Documentation tree | Hard cut to the current project name | Docs build and existing path tests |
| Python distribution | `aces-sdl` | `raes` | `implementations/python/pyproject.toml` | Renamed for new PyPI publication | Version and corpus packaging tests |
| Canonical Python SDL import | `aces_sdl` | `raes` | SDL package owner | Hard cut by #884; no alias or shim | Source import tests plus isolated wheel/sdist tests |
| Other Python packages | `aces_mcp`, `aces_runtime`, `aces_contracts`, other owning `aces_*` packages | `raes_mcp`, `raes_runtime`, `raes_contracts`, and corresponding `raes_*` owners | Python package owners | Hard cut; no alias packages | Module-boundary and installed-wheel negative import tests |
| CLI command | `aces` | `raes` | `raes_cli` | Old console script removed | CLI version/help and installed-wheel tests |
| MCP server command | `aces-mcp` | `raes-mcp` | `raes_mcp` | Old console script removed | Packaging and MCP construction tests |
| MCP server id | `aces-sdl` | `raes` | `raes_mcp.server` | Migrated emitted server name | MCP server construction tests |
| MCP discovery tool | `aces_tool_surface` | `raes_tool_surface` | `raes_mcp.tools.operations` | Old tool removed | MCP tool-surface tests |
| MCP guidance tool | `aces_agent_guidance` | `raes_agent_guidance` | `raes_mcp.tools.operations` | Old tool removed | MCP guidance tests |
| MCP intended-use tool | `aces_intended_use_profiles` | `raes_intended_use_profiles` | `raes_mcp.tools.completeness` | Old tool removed | MCP intended-use tests |
| MCP reference-manifest tool | `aces_reference_manifests` | `raes_reference_manifests` | `raes_mcp.tools.operations` | Old tool removed | MCP advertised-tool tests |
| Agent guidance profile id | `aces-agent-guidance` | `raes-agent-guidance` | `specs/agent-guidance/agent-guidance.yaml` | Migrated canonical profile id | `tools/check_agent_guidance.py` and MCP guidance tests |
| Intended-use scope string | `aces-delivery-capability` | `raes-delivery-capability` | `raes_mcp.tools.completeness` | Migrated emitted scope; `legacy_scope` removed | MCP intended-use tests |
| Runtime OpenAPI title | ACES Runtime Control Plane | RAES Runtime Control Plane | `raes_runtime.control_plane_api` | Migrated emitted title | Version-classification tests |
| HTTP security headers | `x-aces-client-verified`, `x-aces-client-identity` | Retained security-protocol keys | `ControlPlaneSecurityConfig` and the trusted-proxy boundary | Not aliases for project prose; a future migration must preserve fail-closed auth and reject conflicting old/new values | Runtime auth, role, request-size, denial-audit, and redacted-error tests |
| Environment and external workflow keys | `ACES_REQUIREMENT_UID`, `ACES_REAL_LIBVIRT_URI` | Retained external/workflow keys | Requirement governance and opt-in real-libvirt certification | Outside the Python namespace cut; uppercase provenance enum members such as `ACES_NATIVE` are not environment variables | Repo-policy and opt-in integration-test gates |
| Published schema URI namespace | `https://aces.dev/schemas/...` | Retained for every current schema lineage | `contracts/schemas/`, schema-publication records, and `schema_bundle()` | Not retired by #908; a future namespace must coexist with old identities and prove target ownership/redirect behavior | Contract, generated-schema parity, and schema-publication checks |
| Published schemas and wire ids | `io.aces.*`, `x-aces-*`, `aces-*`, contract discriminators and wire field names | Retained governed contract identifiers | `contracts/`, closed DTOs, and ADR-061 schema publication | Current lineages are not renamed in place; a replacement requires its owning versioned contract migration | Contract models, fixtures, JSON Schema validation, and publication checks |
| Module registry artifacts | `aces.lock.json`, `aces-trust.yaml`, `.aces/module-cache`, `application/vnd.aces.*`, `io.aces.module.id` | Retained module/config protocol | `raes.module_registry` | User-authored, persisted, signed, or registry-visible values; not prose cleanup | Closed SDL models, safe YAML/JSON parsing, digest/signature, registry, archive, and CLI tests |
| Runtime and evidence artifact ids | `aces.libvirt.*`, `aces.cross-backend-*`, `aces.participant_runtime.*`, `aces.lifecycle.*` and related values | Retained artifact/wire vocabularies | Owning evidence builders, participant-runtime spec, DTOs, and fixtures | These are schema/discriminator/status values, not a broker topic registry; migrate only with the owning artifact lineage | Artifact validators, redaction gates, DTO/fixture tests, and persistence round trips |
| Host/runtime ownership names | `aces.workspace`, `aces.address`, `aces.*` kernel parameters, libvirt/OCI name prefixes, fixed UUID namespace, guest paths | Retained host ownership and guest-protocol values | OCI/libvirt drivers and guest appliance | A cosmetic rename can orphan resources or defeat ownership proof; requires a separately bounded host migration | Fixed-argv, ownership-conflict, teardown, guest-probe, and real-daemon tests |
| Processor/backend identities | `aces-reference-processor`, package-specific manifest ids | Retained apparatus identities | Manifest owners | Outside the Python namespace cut in issue #884 | Manifest and conformance tests |
| Accepted ADRs, changelog, research snapshots | Historical ACES references | Retained history | Historical record owners | Not rewritten solely to erase the old name | ADR immutability and docs checks |

## User Guidance

Use `raes` and `raes-mcp` in command examples and automation. The old `aces`
and `aces-mcp` console scripts are not installed by the current package.

New MCP clients should start with `raes_tool_surface`, then call
`raes_agent_guidance` and `raes_intended_use_profiles`. Clients must update off
`aces_tool_surface`, `aces_agent_guidance`, `aces_intended_use_profiles`, and
`aces_reference_manifests`; those tools are no longer registered.

Use `raes` for PyPI publication, downstream package pins, and the canonical SDL
import:

```python
from raes import parse_sdl_file
```

The old `aces`, `aces_sdl`, and `aces_*` namespaces are not installed and have
no compatibility aliases, shims, fallback imports, or namespace-package
residue. Code using those imports must change before upgrading. This
package-boundary cut is released as a breaking change.

Do not rename SDL fields, schema ids, wire discriminators, or published
contract identifiers as part of ordinary prose cleanup. Those surfaces require
separate contract migrations with their own fixtures and publication evidence.
