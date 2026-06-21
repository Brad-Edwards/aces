# Issue 551 Import Lockfile Portability Preflight

Date: 2026-06-15

Issue: #551.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture preflight guardrails for making SDL import
lockfiles checkout-independent. It is guidance for implementation only: it does
not change module resolution, lockfile serialization, CLI behavior, tests, or
published documentation.

## Binding Sources

- ADR-053 owns SDL module composition: imports are resolved through the module
  registry, locked, checked against trust/digest/version/export policy, expanded
  before semantic validation, and compiled as one canonical scenario.
- `docs/explain/sdl/parser.md`, `docs/explain/sdl/sections.md`, and
  `docs/explain/sdl/runtime-architecture.md` describe the current user-facing
  import source classes and CLI workflow.
- `aces_sdl.module_registry` owns `LockRecord`, `Lockfile`,
  `ResolvedModule`, `resolve_import()`, `resolve_lock_records()`,
  `load_lockfile()`, and `write_lockfile()`. The CLI should consume that model
  rather than define a second lockfile contract.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and
  `implementations/python/pyproject.toml` define the repository workflow and
  verification graph for the eventual implementation.

## Architecture Decisions

- Store the persisted `resolved_source` for `local:` imports as a stable
  SDL-base-relative identity, not an absolute checkout path. Use POSIX-style
  separators so the lockfile is stable across supported developer and CI
  checkouts.
- Keep `ResolvedModule.root_file` as the runtime filesystem path used for file
  reads, parsing, digest calculation, cycle detection, and recursive expansion.
  Do not reuse persisted lock identity as the runtime path.
- Preserve full structural lockfile comparison in `aces sdl verify-imports`
  once `resolve_lock_records()` emits checkout-stable records. Excluding
  `resolved_source` from comparison would not satisfy the acceptance criterion
  that `aces sdl resolve` writes no absolute local machine paths.
- Keep OCI `resolved_source` semantics unchanged. Registry coordinates plus
  manifest digest are already checkout-independent and supply-chain relevant.
- Treat previously committed absolute-path lockfiles as stale. The portable
  behavior should come from rerunning `aces sdl resolve`, not from silently
  accepting host-specific lock records forever.
- Keep `source` as the authored import declaration and `resolved_source` as the
  resolved lock identity. Do not conflate either field with `root_file`, package
  source shorthand, or module descriptor identity.

## Required Incumbents

- Lockfile model and persistence:
  `LockRecord`, `Lockfile`, `LOCKFILE_NAME`, `LOCKFILE_SCHEMA_VERSION`,
  `load_lockfile()`, `write_lockfile()`, and the deterministic
  `json.dumps(..., sort_keys=True)` serialization already in the registry and
  CLI.
- Resolution and validation:
  `ImportDecl.normalized_source`, `ModuleDescriptor`, `_satisfies_version()`,
  `_validate_digest_pin()`, `_descriptor_digest()`,
  `_verify_allowed_parameters()`, `TrustPolicy`, and
  `RegistryTrustPolicy`.
- Composition and parse flow:
  `parse_sdl_file()`, `_load_normalized_data()`,
  `aces_sdl.composition.expand_sdl_modules()`, import cycle detection,
  namespace collision checks, and whole-scenario `SemanticValidator`
  validation.
- Error handling:
  `SDLParseError` / `SDLValidationError` inside SDL code and Typer
  `BadParameter` for the existing CLI stale-lock envelope.
- Tests and workflow:
  `implementations/python/tests/test_sdl_module_registry.py`,
  `test_pipeline_determinism.py`, `nox -s tests`, `nox -s lint`,
  `nox -s hygiene`, and `nox -s verify`.
- Compatibility boundary:
  `implementations/python/src/aces/` is compatibility-only re-export code and
  must not receive new implementation logic.

## Cross-Cutting Layers

- YAML/config parsing: local imports must still enter through
  `_load_normalized_data()` and `ImportDecl` validation, with `SDLModel`
  `extra="forbid"` closure. No ad hoc YAML or JSON parser should be introduced
  for lockfile comparison.
- Filesystem security: continue resolving local imports from the SDL base
  directory before reading files. The persisted identity may be relative, but
  filesystem reads, existence checks, digesting, and recursive traversal must
  use validated `Path` objects, not string concatenation.
- Trust and supply-chain policy: preserve `TrustPolicy`,
  `allow_unsigned_local_sources`, registry allowlists, signature verification,
  digest pins, lockfile digest checks, version matching, and export-hash checks.
  The portability fix must not create a path that bypasses these gates.
- Persistence and determinism: keep one Pydantic lockfile model and one JSON
  serialization shape. Do not add a parallel DTO, lockfile schema, comparison
  schema, or CLI-only normalization map.
- CLI error envelope: keep missing/stale lockfile failures in Typer's existing
  user-facing error path. Do not dump structural diffs that include host paths,
  file contents, raw YAML payloads, environment variables, or tracebacks.
- OS/process exposure: the CLI may accept absolute scenario paths, but those
  paths must not be persisted into local lock records. No shelling out,
  environment-variable configuration, tokens, private keys, or network access
  are required for this issue.
- Auth, API, persistence services, and logging: no control-plane auth,
  authorization, HTTP API, database, audit-log, or runtime-manager behavior is
  in scope. Do not add logging just to observe lock comparison.
- Repository policy: implementation changes should remain under
  `implementations/python/packages/` and tests under
  `implementations/python/tests/`; user-visible behavior needs a towncrier
  fragment under `changelog.d/551.fixed.md`.

## Extension Boundary

Use one private lock-identity normalization seam in the module registry,
parameterized by import source class and SDL base directory. Local imports use
base-relative POSIX paths; OCI imports keep registry/digest identity. A future
source class should add one branch to that seam rather than change CLI
comparison or duplicate lock serialization.

The seam must return only persisted identity. Runtime path resolution belongs
to `ResolvedModule.root_file`, so future changes such as additional local path
policy, packaged-resource imports, or alternate registry schemes do not force
callers to reinterpret `resolved_source` as a filesystem path.

## Gotchas And Anti-Patterns

Avoid:

- excluding `resolved_source` from `verify-imports` while continuing to write
  absolute local paths;
- adding `resolved_path`, `relative_source`, or another duplicate field instead
  of fixing the existing `resolved_source` contract;
- computing relative strings before the path has been resolved and checked;
- using `Path.relative_to()` without a clear fallback or error policy for
  existing local imports that intentionally resolve outside the SDL directory;
- letting Windows backslashes or drive roots leak into committed lockfiles;
- changing OCI lock identity, signature/trust behavior, digest pinning,
  descriptor validation, or export-hash checks;
- comparing pretty JSON text, dict insertion order, object reprs, or partial
  hand-built dictionaries instead of the canonical Pydantic lockfile dump;
- editing compatibility-only `implementations/python/src/aces/` wrappers;
- bumping published contract schemas, changing schema publication manifests, or
  creating a new authority surface for this narrow bug fix;
- widening the issue into import sandboxing, registry caching, lockfile
  migration tooling, or module packaging redesign.

## Non-Goals

- Implementing the portability change, tests, changelog, or documentation
  updates in this preflight.
- Changing SDL import source classes, module descriptor semantics, trust policy
  defaults, or OCI publishing behavior.
- Introducing a new lockfile schema version, duplicate schema, duplicate
  validator, duplicate exception hierarchy, or alternate CLI verification path.
- Changing parser normalization, semantic validation, instantiation, compiler,
  runtime, control-plane, backend conformance, or MCP behavior.
- Guaranteeing compatibility for stale absolute-path lockfiles without rerun of
  `aces sdl resolve`.
