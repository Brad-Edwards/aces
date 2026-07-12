# Issue 39 Processor Models Package Split Preflight

Date: 2026-07-13

Issue: #39.

Requirement: none. The GitHub issue is the implementation contract.

This note records the guardrails for converting `aces_processor.models` from a
module to a package. It does not implement the split or change behavior.

## Binding Decisions

- ADR-015 enforces a 500-line cap, not the issue's older 600-line cap. Every
  non-test Python file in the replacement package, including `__init__.py`,
  must be at or below 500 lines once the allowlist entry is removed.
- ADR-036 keeps `aces_processor` as the compiled-model layer and requires
  runtime callers to use the public `aces_processor.models` surface. Its
  submodules are implementation detail, not a new public API.
- `aces_contracts` owns neutral runtime/backend DTOs. The current facade
  deliberately re-exports several of them; preserve their identities rather
  than copying, wrapping, or redefining them.
- Release-please owns `CHANGELOG.md`; despite the issue acceptance criterion,
  this feature PR must not edit it or add a fragment.

## Architecture Boundary

`models/__init__.py` is the only public facade. It must retain every existing
external import from `aces_processor.models`, including contract re-exports
verified by `test_runtime_contract_boundaries.py`; no current external import
line is to move to a child module.

Split by the existing dependency direction, not arbitrary line ranges:

- compiled-resource records and workflow/resource records depend only on the
  shared model foundation;
- participant action contracts and compiled observation/outcome declarations
  own their current SEM-211/213/215 contract checks;
- participant result, attribution, outcome, and temporal value records own
  their parsing and local invariant checks;
- the history-event record owns payload decoding; history validation remains
  one ordered coordinator over visibility/authorization, grounding, temporal,
  contract, and joint-action checks.

Private helpers may move with the smallest domain that owns their invariant.
Do not create a new DTO, validation service, exception hierarchy, registry, or
plugin layer. Keep the two public history iterators as the single validation
coordination seam so a future validation concern is added once to the existing
ordered flow.

The module currently has no `__all__`. Do not add one casually: it changes
star-import behavior. Preserve the current facade namespace intentionally,
including the shared-contract aliases used by callers, and compare its public
name set and exported-object identities with the pre-split module before
calling the refactor complete. Preserve public classes' and functions'
observable module/serialization behavior where compatibility requires it;
moving a definition changes `__module__`, repr and pickle metadata unless that
is handled deliberately.

## Cross-Cutting Guardrails

- **Schemas and validation:** retain `aces_contracts` DTOs, their validators,
  `require_compiled_address`, and the existing participant semantic validators.
  Do not duplicate address parsing, enum coercion, result-envelope checks, or
  SEM-211/213/215 rules in new modules.
- **Errors and observability:** preserve `Diagnostic`/`Severity`, current
  `ValueError`/`TypeError` conditions, iterator ordering, and diagnostic text.
  This refactor adds no logging; it must not expose payloads, credentials,
  environment values, or tracebacks.
- **Security and operating surface:** the split passes only Python import,
  dataclass, contract-validation, and repository-policy layers. It must add no
  auth, secret, environment, subprocess, network, filesystem, persistence, or
  control-plane behavior; therefore no new OS-level token or error-envelope
  exposure is permitted.
- **Repository policy:** retain processor-only dependencies on
  `aces_backend_protocols`, `aces_contracts`, and `aces_sdl`; do not import
  `aces_runtime`. Use package-relative internal imports to avoid facade
  partial-initialization cycles. Remove only the allowlist entry for the
  deleted module and do not alter policy code or its fixed reference set.

## Verification And Anti-Patterns

Treat package conversion as a simultaneous delete of `models.py` and creation
of `models/`; never leave both import candidates. Verify the exact external
import grep is unchanged, the facade re-exports its names, the shared DTOs are
object-identical, all new files meet the 500-line cap, and the canonical nox
`verify` session passes.

Avoid direct external imports of child modules, circular imports through the
facade, a fat `__init__.py`, changing dataclass defaults/field order or helper
evaluation order, moving runtime DTO ownership back from `aces_contracts`, and
using this mechanical split to fix incidental semantic behavior. No schema,
runtime API, persistence, logging, CLI, compatibility-wrapper, or test-relaxing
change is in scope.
