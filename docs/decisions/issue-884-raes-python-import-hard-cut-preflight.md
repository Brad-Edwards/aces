# Issue 884 MOD-884 RAES Python Import Hard-Cut Preflight

Date: 2026-07-25

Requirement: MOD-884. This note governs the package-boundary migration reserved
by ADR-093 and the issue-866 preflight; it does not alter SDL, runtime, or
contract semantics.

## Decision And Boundaries

- `raes` is the top-level Python package for the canonical SDL API. Its public
  root exports and supported submodules retain the current SDL API and behavior
  of the owning `aces_sdl` package.
- `aces_sdl` is removed from the source tree and every built wheel/sdist. Do not
  provide a re-export package, import hook, `sys.modules` alias, namespace-only
  directory, warning shim, or fallback import. An old import must fail with the
  normal `ModuleNotFoundError`.
- The deprecated `aces.*` compatibility tree is removed. No source, wheel, or
  sdist may provide that namespace.
- Other owning Python packages move from `aces_*` to corresponding `raes_*`
  namespaces without aliases. Contract ids, schema `$id` values, wire
  discriminators, SDL fields, and persisted artifact meaning remain governed
  separately. Do not create a `raes_sdl` compatibility package.

ADR-093 is amended to replace its intentionally temporary retained-source-
namespace position. The release is a breaking 1.0.0 release; release-please,
not this change, owns the version literal and `CHANGELOG.md`.

## Required Existing Owners

- `implementations/python/packages/aces_sdl/` is the historical SDL owner moved to
  `raes/`; preserve its parser, source-profile, semantic-validator,
  instantiation, canonicalization, formatting, language-service, and module
  registry implementations rather than duplicating any of them.
- `implementations/python/pyproject.toml` and `hatch_build.py` own wheel/sdist
  inclusion; the package list, coverage roots, and Ruff per-file exception must
  name the moved owner. The distribution name remains `raes`.
- `tools/policy/adr_policy.yaml` and `tools/policy/repo_policy.py` own package
  layering and module boundaries. Retarget the existing SDL lower-layer rule
  and every allowed/public import prefix from `aces_sdl` to `raes`; do not add a
  parallel policy or weaken existing edges.
- `tools/check_sdl_lineage.py`, `tools/check_sdl_catalog_parity.py`,
  `tools/check_example_library.py`, `tools/check_specification_coverage.py`,
  and `tools/check_formal_semantic_validation.py` are the existing repository
  tooling consumers. They must use the canonical package and current source
  paths.
- `docs/api/sdl.rst`, `docs/api/sdl-semantics.rst`, the current SDL guides,
  README/getting-started examples, and `examples/README.md` own user-visible
  imports and Sphinx autodoc targets.
- `test_version_classification.py` is the existing hard-cut release-surface
  test, while `test_corpus_packaging.py` is the installed-wheel isolation
  harness. Extend those incumbents to prove `raes` works from a clean install
  and `aces_sdl` is absent; do not add a second packaging harness.

## Cross-Cutting Guardrails

| Layer | Required treatment |
| --- | --- |
| SDL ingress and validation | Keep `raes.parser`, `_yaml_loader`, `SDLParserLimits`, closed Pydantic models, `SemanticValidator`, `instantiate_scenario()`, and `admit_instantiated_scenario()` as the same validation chain. A namespace migration must not bypass, duplicate, or relax a parse/shape/semantic gate. |
| Module/import security | Keep `raes.module_registry` as the sole lockfile, digest, signature/trust-policy, URL, path-containment, archive-shape, and resource-limit boundary. Its import paths are module-asset paths, not Python package aliases. No new environment variable, registry, or fallback resolution is permitted. |
| Diagnostics and adapters | Preserve `SDLError`, `SDLParseError`, `SDLValidationError`, structured language diagnostics, `aces_contracts.Diagnostic`, Typer error handling, and MCP `json_response()` envelopes. Only their import owner changes; do not add a namespace-specific exception or leak traceback, payload, path, or environment data. |
| Contract/schema publication | `aces_contracts.contracts.schema_invariants` publishes qualified validator references. Retargeting those strings to `raes` changes the generated SDL/satisfiability schemas. Update the owning source and the hand-governed schemas together, record a `last_change` summary and current hash in each affected `contracts/schema-publication/entries/` record, and retain `schema_bundle()` parity. Schema ids and semantics stay unchanged. |
| Evidence and documentation locators | Update current executable/source locators in policy tools, contracts, specs, API docs, and assurance records. Preserve historical changelog entries, accepted historical ADR text, pinned research snapshots, external URLs, and evidence about an earlier checkout unless their authority says they describe the current source location. |
| Build and OS/process boundary | Use the existing fixed-argv `uv build` and isolated-wheel tests. The installed-distribution check must run without `PYTHONPATH` or a checkout source tree, inspect the wheel's names, import `raes`, and prove the legacy package is unavailable. No secret, token, private key, or package mapping belongs in argv, environment, logs, fixtures, or docs. |
| Workflow governance | The branch `884-reframe-raes-docs` has no UID. Before implementation, map `MOD-884` to a requirement-order phase with ownership covering the moved package, consumers, policy, current locators, schemas, tests, and docs; run with `ACES_REQUIREMENT_UID=MOD-884`, not `--skip-requirement`. Reconcile Ground Control IMPLEMENTS and TESTS links for the changed code and tests. |

The module-boundary policy's package identifier/root is the extension seam. A
future package-boundary migration changes that one owner and its approved import
edges; it must not restore an alias or teach every consumer a second import
spelling. The stable consumer parameter is the `raes` root plus its existing
public submodule names.

## Gotchas

- A source-tree test can pass while a wheel accidentally ships `aces_sdl`, or
  while an ignored empty/`__pycache__` directory becomes a namespace package.
  The clean installed-wheel negative import test is required evidence.
- Do not retain an `except ModuleNotFoundError: import aces_sdl`, dynamic name
  fallback, `pkgutil` alias, or compatibility package. Those all violate the
  hard cut even if they emit a warning.
- Changing `validator="aces_sdl..."` annotations without the generated schema
  and publication ledger leaves public contracts pointing at a nonexistent
  implementation. Conversely, changing schema ids or semantic rules merely to
  rename that annotation is out of scope.
- Do not mechanically rewrite historical evidence or accepted ADR canonical
  content. Update current locators; use ADR amendments for live-decision
  changes and preserve historical truth.
- The package move is a breaking Python API change, including qualified class
  names used by external importers or pickles. Do not claim data or binary
  compatibility, silently reinterpret persisted data, or add a migration
  service; document the no-rollback import cut in the existing migration note.

## Release And Non-Goals

The merge must carry a breaking Conventional Commit (`feat!:` or an equivalent
`BREAKING CHANGE:` footer) and a `Release-As: 1.0.0` footer so release-please
opens the 1.0.0 release PR. Do not hand-edit `[project].version`,
`.release-please-manifest.json`, or `CHANGELOG.md`.

This work does not add or change auth, control-plane routes, persistence,
logging policy, secret handling, SDL syntax, runtime behavior, schema meaning,
contract identifiers, or any new validation/error hierarchy. It is a package
ownership and public-import cutover only.
