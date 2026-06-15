# Issue 42 Validator Package Split Preflight

Date: 2026-06-15

Issue: #42.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the implementation contract.

This note records architecture preflight guardrails for splitting
`aces_sdl.validator` into a package. It is guidance for implementation only: it
does not split the validator, alter validation behavior, change tests, drain
the oversized allowlist, or add release-note content.

## Binding Sources

- ADR-015 owns the SDL-to-processor layering rule and the 600-line source-file
  cap. `aces_sdl` must not import `aces_processor`, and the oversized allowlist
  may only shrink.
- In this checkout, `implementations/python/packages/aces_sdl/validator.py` is
  4,139 lines. Treat the issue body's older 1,440-line count as stale; the
  acceptance criteria still require every file in the replacement package to be
  at or below 600 lines.
- `tools/policy/oversized_allowlist.yaml` currently carries
  `implementations/python/packages/aces_sdl/validator.py`; the split PR removes
  that entry only after the file has genuinely become a package whose Python
  files are all below the cap.
- `specs/sdl/diagnostics.md` owns the error/advisory boundary. Validation
  errors remain fatal and collect-all; advisories remain non-fatal and
  structurally separate.
- `implementations/python/packages/aces_sdl/parser.py` and
  `instantiate.py` are the in-package callers of `SemanticValidator`.
- Direct `aces_sdl.validator` import sites are currently limited to
  `implementations/python/tests/test_runtime_service_units.py` importing
  `SemanticValidator` and
  `implementations/python/tests/test_sdl_diagnostic_boundary.py` importing the
  module. Legacy `aces.core.sdl.validator` imports also resolve through the
  same public package surface and currently import only `SemanticValidator`.
- `implementations/python/src/aces/core/sdl/validator.py` is compatibility-only
  and re-exports `aces_sdl.validator` through `aces._compat.reexport`.
- `implementations/python/tests/test_sdl_diagnostic_boundary.py` imports
  `aces_sdl.validator` as a module and calls `inspect.getsource()` on it, so the
  package shim must not make the diagnostic-boundary lint blind by accident.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and
  `tools/check_repo_policy.py` define the eventual verification graph.

## Architecture Decisions

- Treat the change as a pure module-boundary refactor. Public behavior,
  validation order, error strings, warning strings, and exception types are not
  part of the refactor surface.
- Convert `aces_sdl.validator` into a package with a thin public surface. The
  package must export `SemanticValidator` and any deliberately preserved public
  names. The current module has no `__all__`, so adding one changes star-import
  behavior even though `aces._compat.reexport` still copies module attributes;
  do that only after an explicit public-surface comparison.
- Preserve direct import compatibility for both owning-package callers
  (`aces_sdl.validator`) and compatibility callers (`aces.core.sdl.validator`).
  Do not move implementation logic into `implementations/python/src/aces/`.
- Split by validation domain, not by arbitrary line ranges. Cohesive domains in
  the current file are: core state/error collection and reference indexes,
  diagnostic renderers, runtime network/application/listener/process checks,
  runtime identity/file/database/DNS/datastore/platform/forwarding/orchestration
  and mail checks, relationship cross-checks, participant/objective/workflow
  checks, and legacy SDL section checks.
- If private mixins are used to keep one `SemanticValidator` type while moving
  methods into domain files, keep them stateless and package-private. They are
  a mechanical source split, not a new validator service, registry, DTO layer,
  exception hierarchy, or plugin mechanism.
- Keep the explicit `validate()` ordering as the coordination seam. A future
  semantic pass should add one domain method plus one ordered call there, not a
  second pass registry or competing workflow engine.

## Required Incumbents

- Validation model and errors: `Scenario`, Pydantic model validators,
  `SDLValidationError`, `SDLError`, `SDLParseError`, and
  `SDLInstantiationError`.
- Shared SDL helpers: `is_variable_ref()`, `extract_variable_name()`,
  `flatten_entities()`, `classify_scenario_explicitness()`,
  `collect_qualified_runtime_family_refs()`, `SimpleProperties`, `NodeType`,
  and the runtime enum/model modules already imported by the validator.
- Existing semantic analyzers:
  `aces_sdl.semantics.assessment`, `objective_semantics`,
  `participant_behavior`, `participant_outcome`, and `workflow`. Do not inline
  or duplicate their schemas, issue codes, or dependency logic inside the
  package split.
- Compatibility helper: `aces._compat.reexport` remains the only compatibility
  shim pattern for `aces.core.sdl.validator`.
- Repository policy: ADR-015 line cap, layering rule, allowlist-drain checks,
  changelog-fragment policy, and the canonical nox `verify` session.

## Cross-Cutting Layers

- Structural/schema layer: YAML normalization and Pydantic closed-world parsing
  still run before `SemanticValidator`. The split must not add schema files,
  change published contracts, or move cross-reference checks into structural
  model validators.
- Semantic-validation layer: all cross-section reference checks continue to
  append through `_err()` and raise one `SDLValidationError` containing the full
  collected list. Advisory checks continue through `_warn()` and `warnings`.
- Diagnostic-boundary layer: package conversion must keep the
  error/advisory-channel guard meaningful. If inherited/private split methods
  make `inspect.getsource(aces_sdl.validator)` insufficient, add package-aware
  coverage rather than weakening or deleting the guard.
- Import/layering layer: package submodules remain under `aces_sdl`, use
  relative imports where appropriate, do not import `aces_processor`, and do not
  introduce implementation code under the compatibility tree.
- Error-envelope and leakage layer: preserve existing human-readable error
  strings and do not add logging that dumps raw SDL payloads, environment
  variables, credentials, file contents, or tracebacks.
- OS/process exposure layer: this refactor should not introduce subprocesses,
  command-line token handling, environment-variable configuration, network
  calls, database state, or filesystem traversal behavior.
- Repository-policy layer: every Python file under the new
  `aces_sdl/validator/` package, including `__init__.py`, must be at or below
  600 lines after the allowlist entry is removed.

## Extension Boundary

The extension seam is the package-private validation-domain module plus the
single public `SemanticValidator` coordinator. Future validation domains should
land in a new or existing subdomain file, export only private helpers or private
mixin methods, and be wired once into the explicit `validate()` order. The
package surface should remain stable so callers never need to know which
submodule owns a pass.

## Gotchas And Anti-Patterns

Avoid:

- changing import lines that reference `aces_sdl.validator`, even if a direct
  submodule import looks cleaner;
- losing the module-level source-inspection contract used by
  `test_sdl_diagnostic_boundary.py`;
- changing error text, error ordering, warning ordering, or advisory severity
  while moving code;
- "fixing" incidental validation behavior during the split, including
  reference-parsing edge cases;
- duplicating issue-renderer dictionaries, semantic analyzers, named-reference
  indexes, service-ref parsing, exception classes, or schema definitions;
- making `__init__.py` a second large implementation module that violates the
  same size-cap pressure the issue is meant to remove;
- editing `CHANGELOG.md` directly. Repo policy expects a fragment such as
  `changelog.d/42.changed.md` for the implementation PR.

## Non-Goals

- No behavior change, schema change, validation-rule change, parser change, or
  instantiation change.
- No new authorization, persistence, runtime API, logging, CLI, environment, or
  network surface.
- No new public validator abstraction beyond preserving `SemanticValidator` at
  `aces_sdl.validator`.
- No changes to existing tests just to make the refactor pass; add focused
  package-aware coverage only if the split would otherwise weaken an existing
  guard.
