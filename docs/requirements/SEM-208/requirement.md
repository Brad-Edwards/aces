---
id: SEM-208
title: "Participant Behavior Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:15:26.256501Z
updated_at: 2026-05-18T20:11:35.427367Z
---

# SEM-208 — Participant Behavior Semantics

## Statement

The ecosystem shall define explicit semantics for participant actions, observations, state transitions, and role-neutral behavior interpretation.

## Rationale

Requirement inventory expansion. Participant behavior must have shared meaning across validation, runtime, and backend contracts.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#4` (SEM-200: Shared Semantic Integrity)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#71` (Participant behavior & interaction semantics (SEM-208…213, 215))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#185` (Participant Behavior Semantics (SEM-208))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#71` (Participant behavior & interaction semantics (SEM-208, SEM-209, SEM-210, SEM-211, SEM-212, SEM-213, SEM-215))
- DOCUMENTS → SPEC `specs/formal/participant-semantics/README.md` (Participant Semantics Formal Design)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/lineage.md` (SDL lineage and prior work)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/precedents.md` (SDL design precedents for participant semantics and language adequacy)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md` (ADR-022: Participant Behavior and Interaction Semantics)
- DOCUMENTS → PULL_REQUEST `Brad-Edwards/aces#348` (Add participant semantics design)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#349` (Implement SEM-208 participant behavior semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/participant_behavior.py` (SDL participant behavior contract models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (Participant behavior runtime history invariants)
- TESTS → TEST `implementations/python/tests/test_sem_208_participant_behavior.py` (SEM-208 participant behavior semantics regression tests)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#185` (Participant Behavior Semantics (SEM-208))
- TESTS → TEST `implementations/python/tests/test_participant_semantics_invariant_oracle.py` (Participant semantics invariant oracle for SEM-208 behavior semantics)
