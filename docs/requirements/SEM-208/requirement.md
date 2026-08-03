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

- DOCUMENTS → SPEC `specs/formal/participant-semantics/README.md` (Participant Semantics Formal Design)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/lineage.md` (SDL lineage and prior work)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/precedents.md` (SDL design precedents for participant semantics and language adequacy)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md` (ADR-022: Participant Behavior and Interaction Semantics)
- TESTS → TEST `implementations/python/tests/test_sem_208_participant_behavior.py` (SEM-208 participant behavior semantics regression tests)
- TESTS → TEST `implementations/python/tests/test_participant_semantics_invariant_oracle.py` (Participant semantics invariant oracle for SEM-208 behavior semantics)
