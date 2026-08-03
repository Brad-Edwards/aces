---
id: DSL-139
title: "Runtime Service-Family Structural Uniformity"
status: ACTIVE
type: CONSTRAINT
priority: MUST
wave: 1
created_at: 2026-05-30T06:21:25.596962Z
updated_at: 2026-05-30T06:21:58.525583Z
---

# DSL-139 — Runtime Service-Family Structural Uniformity

## Statement

The runtime service-family inventory surface shall be describable by one enforced set of structural invariants — singular-noun identifier fields validated as concrete symbols, Runtime-prefixed model classes, runtime_&lt;family&gt;.py module naming, plural typed-child containers, an open-taxonomy/closed-vocabulary enum-sentinel rule, in-class validator wiring through a single dispatch with no free-function validators, a single runtime enum-parse helper, a single shared secret-redaction helper, registry registration with child references, and a required-profile guard on every discriminated spine — verified by an executable cross-family invariant lint, with all existing families reconciled to the same invariants.

## Rationale

Consistency epic #439 documents that the runtime service families forked conventions because each landed in its own PR with no shared chokepoint; #440/#441 are done, #442 (validation wiring, dual enum-parse helpers), #443 (3 id-naming styles, SshServerConfig class-name violation, process/processes twin, unenforced enum sentinels), and #444 (uneven doc/ADR coverage) remain. To survive expert review the SDL must be describable by one small invariant set, made executable rather than aspirational.

## Traceability

- VERIFIES → TEST `implementations/python/tests/test_runtime_family_invariants.py` (Cross-family invariant lint)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_values.py` (Shared name_indicates_secret helper)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#458` (PR #458)
- TESTS → TEST `implementations/python/tests/test_runtime_observed_values.py` (Runtime observed-value secret-name classifier regression tests)
- IMPLEMENTS → GITHUB_ISSUE `471` (Issue #471 runtime secret-name classifier boundary)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-057-runtime-secret-name-classifier-boundaries.md` (ADR-057 Runtime Secret-Name Classifier Boundaries)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#530` (PR #530 runtime profile guard invariant lint)
- TESTS → TEST `implementations/python/tests/test_runtime_family_invariants.py` (Runtime required-profile guard invariant lint)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (Runtime required-profile guard validation convention)
