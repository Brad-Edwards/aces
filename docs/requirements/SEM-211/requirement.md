---
id: SEM-211
title: "Participant Preconditions, Effects, And Failure Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:15:26.628942Z
updated_at: 2026-05-20T04:39:58.547151Z
---

# SEM-211 — Participant Preconditions, Effects, And Failure Semantics

## Statement

The ecosystem shall define explicit semantics for participant action applicability, effects, side effects, and failure classes.

## Rationale

Requirement inventory expansion. Participant actions need portable meaning for what must hold, what changes, and how failure is interpreted.

## Traceability

- IMPLEMENTS → SPEC `contracts/schemas/control-plane/participant-behavior-history-event-stream-v1.json` (Participant behavior history event stream schema)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated scenario schema participant action semantics)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring input schema participant action semantics)
- IMPLEMENTS → SPEC `contracts/schemas/snapshots/runtime-snapshot-v1.json` (Runtime snapshot schema participant action semantics)
- TESTS → TEST `implementations/python/tests/test_sem_211_participant_action_semantics.py` (SEM-211 participant action semantics tests)
- TESTS → TEST `implementations/python/tests/test_sem_208_participant_behavior.py` (Participant behavior tests with action result publication)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-semantic-integrity.md` (Shared semantic integrity reference)
- DOCUMENTS → SPEC `specs/formal/participant-semantics/README.md` (Participant Semantics Formal Design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md` (ADR-022: Participant Behavior and Interaction Semantics)
- TESTS → TEST `implementations/python/tests/test_participant_semantics_invariant_oracle.py` (Participant semantics invariant oracle for SEM-211 action semantics)
