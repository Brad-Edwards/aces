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

Keep ACES only when the identifier is one of these surfaces:

- an internal owning package outside the SDL import cut, such as `aces_mcp`,
  `aces_runtime`, or `aces_contracts`
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
| Documentation paths | `docs/aces/` | `docs/aces/` | Documentation tree | Retained path/reference area, not a command alias | Docs build and existing path tests |
| Python distribution | `aces-sdl` | `raes` | `implementations/python/pyproject.toml` | Renamed for new PyPI publication | Version and corpus packaging tests |
| Canonical Python SDL import | `aces_sdl` | `raes` | SDL package owner | Hard cut by #884; no alias or shim | Source import tests plus isolated wheel/sdist tests |
| Other internal Python packages | `aces_mcp`, `aces_runtime`, `aces_contracts`, other owning `aces_*` packages | Retained internal owner names | Python package owners | Outside #884 | Existing module-boundary and package tests |
| CLI command | `aces` | `raes` | `aces_cli` | Old console script removed | CLI version/help and installed-wheel tests |
| MCP server command | `aces-mcp` | `raes-mcp` | `aces_mcp` | Old console script removed | Packaging and MCP construction tests |
| MCP server id | `aces-sdl` | `raes` | `aces_mcp.server` | Migrated emitted server name | MCP server construction tests |
| MCP discovery tool | `aces_tool_surface` | `raes_tool_surface` | `aces_mcp.tools.operations` | Old tool removed | MCP tool-surface tests |
| MCP guidance tool | `aces_agent_guidance` | `raes_agent_guidance` | `aces_mcp.tools.operations` | Old tool removed | MCP guidance tests |
| MCP intended-use tool | `aces_intended_use_profiles` | `raes_intended_use_profiles` | `aces_mcp.tools.completeness` | Old tool removed | MCP intended-use tests |
| MCP reference-manifest tool | `aces_reference_manifests` | `raes_reference_manifests` | `aces_mcp.tools.operations` | Old tool removed | MCP advertised-tool tests |
| Agent guidance profile id | `aces-agent-guidance` | `raes-agent-guidance` | `specs/agent-guidance/agent-guidance.yaml` | Migrated canonical profile id | `tools/check_agent_guidance.py` and MCP guidance tests |
| Intended-use scope string | `aces-delivery-capability` | `raes-delivery-capability` | `aces_mcp.tools.completeness` | Migrated emitted scope; `legacy_scope` removed | MCP intended-use tests |
| Runtime OpenAPI title | ACES Runtime Control Plane | RAES Runtime Control Plane | `aces_runtime.control_plane_api` | Migrated emitted title | Version-classification tests |
| HTTP headers and config keys | `x-aces-*`, `ACES_REQUIREMENT_UID` | Retained external/workflow keys | Runtime/security and workflow owners | Not renamed by issue #866 | Runtime security and repo-policy gates |
| Published schemas and wire ids | `io.aces.*`, `aces-*`, contract discriminators | Retained governed contract identifiers | `contracts/` and ADR-061 schema publication | Not renamed by issue #866 | Contract and schema-publication checks |
| Processor/backend identities | `aces-reference-processor`, package-specific manifest ids | Retained apparatus identities | Manifest owners | Not renamed by issue #866 | Manifest and conformance tests |
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

The old `aces_sdl` namespace is not installed and has no compatibility alias,
shim, fallback import, or namespace-package residue. Code using that import must
change before upgrading. This package-boundary cut is released as version
1.0.0.

Do not rename SDL fields, schema ids, wire discriminators, other internal
owning packages, or published contract identifiers as part of ordinary prose
cleanup. Those surfaces require separate contract or module-boundary
migrations with their own fixtures, compatibility analysis, and verification
evidence.
