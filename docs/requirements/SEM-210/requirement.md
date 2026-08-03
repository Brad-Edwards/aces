---
id: SEM-210
title: "Visibility And Information-Boundary Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:15:26.481393Z
updated_at: 2026-05-19T05:36:35.549033Z
---

# SEM-210 — Visibility And Information-Boundary Semantics

## Statement

The ecosystem shall define explicit semantics for what participants can observe, infer, conceal, discover, or disclose over time.

## Rationale

Requirement inventory expansion. Participant behavior depends on information boundaries, not only on externally visible topology.

## Traceability

- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (Runtime conformance checks for SEM-210 participant visibility anchors)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Runtime contract model fields for SEM-210 participant observation details)
- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (SEM-210 runtime conformance tests for participant-local visibility validation)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-semantic-integrity.md` (Shared semantic integrity SEM-210 coverage row)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (Participant visibility validation diagnostics)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#71` (Participant behavior & interaction semantics (SEM-208…213, 215))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#187` (Visibility And Information-Boundary Semantics (SEM-210))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#71` (Participant behavior & interaction semantics (SEM-208, SEM-209, SEM-210, SEM-211, SEM-212, SEM-213, SEM-215))
- DOCUMENTS → SPEC `specs/formal/participant-semantics/README.md` (Participant Semantics Formal Design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md` (ADR-022: Participant Behavior and Interaction Semantics)
- DOCUMENTS → PULL_REQUEST `Brad-Edwards/aces#348` (Add participant semantics design)
- TESTS → TEST `implementations/python/tests/test_sem_208_participant_behavior.py` (SEM-210 participant visibility leakage and disclosure tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/participant_behavior.py` (Participant behavior visibility and information-boundary SDL models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (Runtime participant observation-boundary visibility metadata)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#351` (Implement SEM-210 visibility boundaries)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/semantics/participant_behavior.py` (Participant visibility semantic reference validation)
- TESTS → TEST `implementations/python/tests/test_participant_semantics_invariant_oracle.py` (Participant semantics invariant oracle for SEM-210 visibility semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (Compiler mapping for participant observation-boundary visibility metadata)
