---
id: SEM-213
title: "Temporal Participant Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:15:26.834118Z
updated_at: 2026-05-21T06:03:03.199773Z
---

# SEM-213 — Temporal Participant Semantics

## Statement

The ecosystem shall define explicit semantics for schedules, cadence, deadlines, dwell, latency, and time-windowed participant behavior.

## Rationale

Requirement inventory expansion. Temporal behavior must have shared meaning beyond backend-local scheduling choices.

## Traceability

- IMPLEMENTS → CONFIG `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated scenario schema temporal contracts)
- IMPLEMENTS → CONFIG `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema temporal contracts)
- IMPLEMENTS → CONFIG `contracts/schemas/control-plane/participant-behavior-history-event-stream-v1.json` (Participant behavior history temporal context schema)
- IMPLEMENTS → CONFIG `contracts/schemas/snapshots/runtime-snapshot-v1.json` (Runtime snapshot temporal context schema)
- IMPLEMENTS → SPEC `specs/formal/participant-semantics/README.md` (SEM-213 implemented participant temporal semantics section)
- DOCUMENTS → DOCUMENTATION `docs/decisions/sem-213-temporal-participant-preflight.md` (SEM-213 implementation preflight notes)
- TESTS → TEST `implementations/python/tests/test_sem_213_temporal_participant_semantics.py` (SEM-213 temporal participant semantics tests)
- DOCUMENTS → SPEC `specs/formal/participant-semantics/README.md` (Participant Semantics Formal Design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md` (ADR-022: Participant Behavior and Interaction Semantics)
- TESTS → TEST `implementations/python/tests/test_participant_semantics_invariant_oracle.py` (Participant semantics invariant oracle for SEM-213 temporal semantics)
