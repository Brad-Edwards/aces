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

- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#190` (Temporal Participant Semantics (SEM-213))
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#360` (added: add temporal participant semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/participant_temporal_semantics.py` (SEM-213 participant temporal semantics SDL models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/participant_behavior.py` (Participant action contract temporal fields and validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (Runtime participant temporal context and state-machine validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Published participant temporal context contract model)
- IMPLEMENTS → CONFIG `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated scenario schema temporal contracts)
- IMPLEMENTS → CONFIG `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema temporal contracts)
- IMPLEMENTS → CONFIG `contracts/schemas/control-plane/participant-behavior-history-event-stream-v1.json` (Participant behavior history temporal context schema)
- IMPLEMENTS → CONFIG `contracts/schemas/snapshots/runtime-snapshot-v1.json` (Runtime snapshot temporal context schema)
- IMPLEMENTS → SPEC `specs/formal/participant-semantics/README.md` (SEM-213 implemented participant temporal semantics section)
- DOCUMENTS → DOCUMENTATION `docs/decisions/sem-213-temporal-participant-preflight.md` (SEM-213 implementation preflight notes)
- TESTS → TEST `implementations/python/tests/test_sem_213_temporal_participant_semantics.py` (SEM-213 temporal participant semantics tests)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#71` (Participant behavior & interaction semantics (SEM-208…213, 215))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#71` (Participant behavior & interaction semantics (SEM-208, SEM-209, SEM-210, SEM-211, SEM-212, SEM-213, SEM-215))
- DOCUMENTS → SPEC `specs/formal/participant-semantics/README.md` (Participant Semantics Formal Design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md` (ADR-022: Participant Behavior and Interaction Semantics)
- DOCUMENTS → PULL_REQUEST `Brad-Edwards/aces#348` (Add participant semantics design)
- TESTS → TEST `implementations/python/tests/test_participant_semantics_invariant_oracle.py` (Participant semantics invariant oracle for SEM-213 temporal semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (Compiled participant temporal metadata)
