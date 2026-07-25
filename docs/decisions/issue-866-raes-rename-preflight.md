# Issue 866 RAES Rename Preflight

Date: 2026-07-24

Issue: #866. Requirement: GOV-866, `ae359130-4cf5-4043-9a2e-58e6ada0c47c`.

This note records architecture preflight guardrails for renaming the project to
Reproducible Agentic Environments System (RAES). The initial pass classified
rename surfaces; the implementation follows the July 24, 2026 hard-cutover
clarification for public command, MCP, distribution, and guidance surfaces.

## Binding Sources

- ADR-088 records the RAES rename decision, workshop context, project
  provenance, and hard-cutover boundary.
- ADR-009, ADR-019, and `specs/authority/authority-boundary.yaml` define
  normative authority roots. Rename source-of-truth files first; regenerate or
  verify derived outputs afterward.
- ADR-010, ADR-036, and `tools/policy/adr_policy.yaml` define Python package
  ownership and the compatibility-only `implementations/python/src/aces/`
  layer.
- ADR-061, `contracts/schema-publication-manifest.json`,
  `contracts/schema-publication/`, and `tools/check_schema_publication.py`
  govern published schema identifiers and schema change records.
- ADR-075, `specs/evolution/versioning-deprecation-and-migration.md`, and
  `specs/evolution/deprecation-records.yaml` govern compatibility,
  deprecation, removal, and migration records across repository-governed
  surfaces.
- ADR-014, `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `.pre-commit-config.yaml`, and `.github/workflows/ci.yml` define the
  canonical verification workflow.

## Architecture Guardrails

- Treat the rename as a classified migration. Every ACES-bearing occurrence
  must be classified as current prose, source API, distribution metadata,
  CLI/MCP surface, contract/profile id, fixture data, generated artifact,
  removed legacy public alias, historical record, or external reference before
  it is changed or intentionally left alone.
- Keep project identity separate from SDL semantics. RAES names the ecosystem;
  SDL remains the scenario description language unless a separate language
  decision changes that term.
- Keep contract identity separate from package identity. A package rename,
  import rename, CLI rename, MCP tool rename, schema `$id`, profile id, wire
  discriminator, and artifact envelope id are different surfaces with different
  compatibility rules.
- Leave retained identifiers at the owning boundary. `aces.*` compatibility
  imports stay in `implementations/python/src/aces/`; owning packages must not
  start importing from that tree. Public CLI and MCP aliases are removed by the
  hard cutover. Contract readers remain in `aces_contracts`, and SDL source
  migration remains in `aces_sdl`.
- Prefer source-of-truth edits and regeneration. Published schemas remain
  hand-governed under `contracts/schemas/`; generated-schema parity must be
  restored through `schema_bundle()` and `tools/check_generated_schemas.py`.
  Sphinx output, package metadata, corpus packaging, and release artifacts
  must be produced by their existing tooling rather than hand-edited.
- Document every retained or removed old name. The downstream migration note
  should map old ACES names to RAES names by surface and state each surface as
  migrated, removed, retained source/contract identity, historical, or external.
- Treat machine-readable guidance fields as public contracts, not prose.
  In `specs/agent-guidance/agent-guidance.yaml`, classify the `profile` id,
  `recommended_workflow` tool ids, and `source_refs` path values separately.
  The hard cutover changes the canonical guidance id to `raes-agent-guidance`
  and updates its existing structural checker and consumer. Do not silently
  transform guidance values at runtime.
- Do not add a central rename registry, runtime lookup service, persistence
  table, endpoint, or exception hierarchy. The extension point is a
  surface-class migration mapping in docs plus the owning surface's existing
  checker, validator, alias, or deprecation record.

## Required Incumbents

- Repository policy and workflow:
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_adr_immutability.py`, `tools/check_deprecation_lifecycle.py`,
  `tools/check_authority_boundary.py`, `tools/verify_all.py`, and the `nox`
  `hygiene`, `policy`, `contracts`, `tests`, `docs`, and `verify` sessions.
- Package and import boundaries:
  `implementations/python/pyproject.toml`, `implementations/python/hatch_build.py`,
  `implementations/python/src/aces/_compat.py`,
  `implementations/python/packages/aces_*`, and `tools/policy/adr_policy.yaml`
  `compatibility_layer` / `module_boundaries`.
- Contracts, schemas, profiles, and corpus:
  `contracts/schemas/`, `contracts/profiles/`, `contracts/concept-authority/`,
  `contracts/schema-publication-manifest.json`,
  `contracts/schema-publication/entries/`,
  `aces_contracts.contracts.schema_bundle()`,
  `tools/generate_contract_schemas.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_json_artifacts.py`, `aces_contracts.corpus`, and
  `manifest_authority` / closed DTO validators.
- SDL and authoring migration:
  `aces_sdl.parser`, `SDLMigrationPolicy`, source diagnostics,
  `format_sdl_source()`, module registry lockfile/trust/signature handling,
  `aces_sdl.language_service`, and existing parser/validator tests.
- Machine-readable agent guidance:
  `specs/agent-guidance/agent-guidance.yaml`,
  `tools/check_agent_guidance.py`, `aces_sdl.agent_guidance`, and the MCP
  `raes_agent_guidance` / `raes_tool_surface` registrations. Retain the
  existing YAML-shape gate and structured response rather than adding a second
  guidance schema or an identity-translation layer.
- CLI, MCP, and user-facing adapters:
  `aces_cli.main` / Typer command modules, console scripts in
  `pyproject.toml`, `aces_mcp.server`, MCP tool registration modules,
  `aces_mcp.tools.operation_support.json_response()`,
  size-limit guards, and existing CLI/MCP tests.
- Runtime API and security patterns:
  `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneIdentity`,
  `ControlPlaneRole`, request-size guards, bearer/proxy identity handling,
  request fingerprints/idempotency keys, append-only audit events, redacted
  unexpected-error responses, and existing FastAPI DTO adapters.
- Release, docs, and external service metadata:
  `release-please-config.json`, `.release-please-manifest.json`,
  `.github/workflows/release-please.yml`, `docs/conf.py`, `docs/Makefile`,
  `sonar-project.properties`, `.github` issue/PR templates, `SECURITY.md`,
  `SUPPORT.md`, `CONTRIBUTING.md`, and top-level README/citation prose.

## Cross-Cutting Layers

- Security validators: if HTTP/OpenAPI titles, routes, docs, or the
  `ControlPlaneSecurityConfig` identity-header defaults are renamed, the
  control-plane API must still authenticate through
  `ControlPlaneSecurityConfig`, authorize through `ControlPlaneRole`, enforce
  `request_size_guard_response()`, record audit denials, and return bounded
  `HTTPException` / JSON error envelopes. A temporary old/new header alias is
  safe only behind the existing trusted proxy boundary, must reject conflicting
  values, and must not make caller-supplied headers trusted. Rename work must
  not bypass these guards or introduce unauthenticated inspection endpoints.
- Secret-handling surface: do not read or require `/home/atomik/.secrets` or
  `~/.secrets`. Runtime scenario values still follow ADR-057 explicit
  redaction rules; real operator secrets must not be captured into docs,
  examples, fixtures, logs, package metadata, schema examples, or migration
  records. Gitleaks/hygiene remain the repository-level guard.
- Environment and config shapes: existing workflow/config keys such as
  `ACES_REQUIREMENT_UID`, Ground Control project ids, Sonar project keys,
  console-script names, and MCP server ids are external integration surfaces.
  Rename them only when their owning integration is updated and the current
  verification graph proves the new surface.
- OS/process exposure: do not pass tokens, private keys, PR titles, schema
  payloads, or migration mappings through shell interpolation or logged argv.
  Existing workflows use fixed command argv and scoped environment variables;
  keep that pattern for any new RAES/removal checks.
- Config/schema parsers: use `json.loads`, `yaml.safe_load` or existing SDL
  loaders, Pydantic/contract models, and repo-relative path checks. Do not
  evaluate metadata, fetch remote `$ref` targets, follow unchecked paths, or
  coerce malformed migration/deprecation records into empty defaults.
- Error envelopes and diagnostics: CLI errors stay Typer `BadParameter` /
  `Exit`; MCP tools use structured `json_response()` / diagnostics payloads;
  SDL failures use `SDLParseError` / `SDLValidationError`; conformance and
  planning failures use `Diagnostic`; runtime HTTP failures use bounded JSON.
  Do not create a rename-specific exception hierarchy or leak raw payloads,
  absolute site-packages paths, environment variables, or tracebacks.
- Logging and observability: preserve the existing logging/audit surfaces.
  Logger names may need a compatibility decision, but logs must not become a
  second migration record and must not expose secrets or raw rejected payloads.
- Persistence: the rename does not add runtime persistence or database
  migrations. If persisted operation/audit payloads retain old identifiers,
  treat that as historical data plus a reader compatibility decision, not as
  an instruction to reinterpret stored records silently.

## Extension Boundary

The extension seam is a surface-class migration mapping in the downstream
migration note, with these fields per row: surface class, old identifier, new
identifier, owner, compatibility status, notice/removal rule, and verification
evidence. Future rebrands or namespace moves should extend that table and the
owning checker/validator for the surface, not add a central alias service.

The important parameter is the surface class. A future RAES package rename,
contract-id rename, CLI alias, MCP alias, workflow variable rename, or external
service rename should be handled by adding or updating one mapping row and the
owning surface's existing tests/gates.

## Gotchas And Anti-Patterns

Avoid:

- blind replacement in accepted ADRs, changelog history, citations, external
  URLs, issue records, generated outputs, lock/build artifacts, or fixtures
  that intentionally preserve old identifiers;
- treating every `aces` substring as the same concept. `aces-sdl`, `aces`,
  `aces_mcp`, `aces.*`, `aces.dev`, `aces.lock.json`, `io.aces.*`,
  `aces.challenge`, `aces-reference-processor`, and
  `aces-semantic-invariants-v1` are different surfaces;
- treating `aces-agent-guidance`, `aces_tool_surface`,
  `aces_agent_guidance`, and old `recommended_workflow` entries as prose.
  Their identifiers and the guidance consumer/checker must evolve together;
- adding new implementation logic under `implementations/python/src/aces/` or
  importing `aces.*` from owning packages;
- changing published schema ids, `$id` URIs, profile ids, or wire
  discriminators without ADR-061 manifest metadata, deprecation/migration
  records, fixtures, and generated-schema parity;
- hand-editing generated schemas, Sphinx output, wheel/sdist contents,
  release notes, or version literals;
- renaming GitHub, SonarCloud, PyPI, docs, or source repository URLs to values
  that do not yet exist externally;
- leaving old public CLI commands or MCP tools in place after the hard cutover;
- renaming import paths, config variables, media types, OCI labels, kernel
  parameters, lockfile names, or published contract identifiers without the
  owning migration evidence;
- introducing duplicate schema registries, alias tables, validators,
  exception hierarchies, nox sessions, release scripts, or migration services;
- weakening the request-size, auth, redacted-error, gitleaks, JSON-artifact,
  schema-publication, module-boundary, or ADR pin gates to get the rename
  through.

## Non-Goals

- Implementing the rename in this preflight note.
- Changing SDL language semantics, runtime behavior, contract meaning,
  conformance semantics, auth policy, audit policy, or persistence behavior.
- Creating a new central alias registry, runtime migration service, API
  endpoint, database table, or cross-package exception hierarchy.
- Editing `CHANGELOG.md`, release-please version literals, generated docs, or
  build outputs by hand.
- Renaming old ACES source imports, published contract identifiers, historical
  records, or external integration keys without their owning migration evidence.
- Rewriting historical records solely to erase the old project name.
