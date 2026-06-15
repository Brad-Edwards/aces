# Issue 505 Error/Advisory Boundary Preflight

Date: 2026-06-15

Issue: #505.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture guardrails for specifying the SDL
error-vs-advisory boundary. It is non-normative preflight guidance only: it does
not amend the SDL specification, reclassify validator passes, add lint, or
update explanatory documentation.

## Architecture Decisions

- Use `specs/sdl/diagnostics.md` as the single normative source for the
  boundary. `specs/sdl/` is already registered as normative SDL prose in
  `specs/authority/authority-boundary.yaml`, so adding a separate ADR for the
  same rule would create a second authority surface.
- Collapse the current diagnostics text that defers case-by-case
  classification to IMP-3 into one normative boundary statement. The
  explanatory `docs/explain/sdl/validation.md` page should cite that statement,
  not restate it.
- Keep the boundary conceptual, not implementation-shaped: errors cover
  structural and semantic invariants that affect SDL meaning; advisories cover
  deployability or quality heuristics that leave SDL meaning intact.
- Decide borderline cases by meaning preservation. If a condition changes parse
  shape, reference resolution, uniqueness, ambiguity, cycle safety, required
  profile guards, variable instantiation, or explicit redaction semantics, it is
  an error. If it only warns that a valid SDL document may be hard to deploy,
  may need backend defaults, or may benefit from author review, it is an
  advisory.

## Required Incumbents

- Normative authority: ADR-009, ADR-019, `specs/sdl/README.md`,
  `specs/sdl/diagnostics.md`, and `specs/authority/authority-boundary.yaml`.
- Explanatory docs: `docs/explain/sdl/validation.md` remains non-normative and
  should cite the spec instead of carrying a competing rule.
- Runtime/value security lineage: ADR-056, ADR-057, `runtime_values.py`, and
  `enforce_observed_value_redaction()`. Explicit redaction remains an
  error-enforced invariant; name-shaped secret heuristics remain advisory-only.
- Parser and diagnostic envelopes: `parse_sdl()`, `parse_sdl_file()`,
  `SemanticValidator`, `SDLParseError`, `SDLValidationError`,
  `SDLInstantiationError`, `Scenario.advisories`, `instantiate_scenario()`,
  `language_diagnostics()`, and `load_scenario()` advisory logging.
- Policy and verification: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_authority_boundary.py`, and the
  canonical `nox -s verify` graph.

## Audit Guidance

- Treat `_verify_*` methods in `SemanticValidator` as error passes unless the
  audit finds a method that only describes deployability or quality without
  affecting SDL meaning.
- Treat `_collect_advisories()` and `_warn_*` methods as the advisory pass
  surface. The current concrete advisory, VM nodes without `resources`, fits the
  deployability-heuristic side of the boundary.
- Do not classify `runtime_values.name_indicates_secret()` as a validation
  error source. It is explicitly advisory helper logic after ADR-057.
- Record the audit result in the PR even if it is a clean bill. The acceptance
  criterion asks for the result, not just code changes.

## Lint/Checklist Seam

Prefer a lightweight executable guard in tests if it stays simple:

- `_collect_advisories()` is the only place that invokes advisory pass methods.
- Advisory pass method names use `_warn_*`.
- Validation pass registration in `validate()` continues to use `_verify_*` for
  error-producing passes and invokes `_collect_advisories()` once after those
  passes.

If an AST/introspection lint becomes brittle, use a documented review checklist
hook instead. Do not introduce a new validator framework or diagnostic registry
for one advisory pass.

## Security And Cross-Cutting Layers

- YAML/config parsing: preserve the safe loader, string top-level keys,
  user-defined key preservation, variable-key rejection, and Pydantic
  `extra="forbid"` structural closure. This issue should not loosen any parser
  gate.
- Semantic validation: keep fail-closed reference resolution, ambiguity,
  uniqueness, cycle, visibility, profile-guard, and explicit-redaction failures
  on `SDLValidationError` or the existing Pydantic `ValidationError` path.
- Secret handling: advisory text must not echo raw values, credentials, or host
  operator secrets. If a future secret-name advisory is surfaced, report field
  paths or names only and keep explicit `redacted`/`operator_secret` raw-value
  omission as the enforced rule.
- Error envelopes: do not add a new SDL exception hierarchy or diagnostics
  envelope. Language-service behavior should continue to route errors through
  the existing structured diagnostics; adding warning diagnostics is out of
  scope unless separately required and tested.
- OS/process exposure: no command examples or tooling added for this issue
  should require tokens, private keys, credentials, or scenario secrets in
  process argv.

## Gotchas And Anti-Patterns

Avoid:

- creating both an ADR and a spec section that each state the boundary;
- leaving `docs/explain/sdl/validation.md` as an uncited duplicate authority;
- treating advisories as optional errors or allowing tools to promote them to
  failures by default;
- demoting structural or semantic validity failures to advisories for backend
  convenience;
- inventing a second warning list, exception type, schema, validator registry,
  or language-service diagnostic channel;
- editing compatibility-only wrappers under `implementations/python/src/aces/`;
- expanding this issue into backend deployability policy or resource-default
  selection.

## Non-Goals

- Implementing the normative text, lint, audit, or reclassification.
- Changing parser, validator, instantiation, language-service, schema, runtime,
  or backend behavior during this preflight.
- Adding a changelog fragment for this preflight note.
- Deciding backend defaults for VM resources or changing whether missing
  resources are valid SDL.
