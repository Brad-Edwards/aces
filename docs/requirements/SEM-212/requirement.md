---
id: SEM-212
title: "Participant Causality And Attribution Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:15:26.736996Z
updated_at: 2026-05-21T04:14:30.426372Z
---

# SEM-212 — Participant Causality And Attribution Semantics

## Statement

The ecosystem shall define explicit semantics linking participant actions to observed state changes, detections, alerts, and downstream outcomes.

## Rationale

Requirement inventory expansion. Rich experimentation needs portable semantics for causality and attribution across participant behavior and observed results.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#71` (Participant behavior & interaction semantics (SEM-208…213, 215))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/participant_attribution_semantics.py` (SEM-212 participant attribution semantic vocabularies)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (SEM-212 participant attribution runtime models and validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (SEM-212 participant attribution contract models)
- TESTS → TEST `implementations/python/tests/test_sem_212_participant_attribution_semantics.py` (SEM-212 participant attribution adversarial tests)
- IMPLEMENTS → CONFIG `contracts/schemas/control-plane/participant-behavior-history-event-stream-v1.json` (SEM-212 participant behavior history event-stream schema)
- IMPLEMENTS → CONFIG `contracts/schemas/snapshots/runtime-snapshot-v1.json` (SEM-212 runtime snapshot attribution schema)
- IMPLEMENTS → SPEC `specs/formal/participant-semantics/README.md` (SEM-212 participant attribution formal implementation mapping)
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#189` (Participant Causality And Attribution Semantics (SEM-212))
- IMPLEMENTS → DOCUMENTATION `docs/explain/reference/shared-semantic-integrity.md` (SEM-212 shared semantic integrity attribution row)
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#71` (Participant behavior & interaction semantics (SEM-208, SEM-209, SEM-210, SEM-211, SEM-212, SEM-213, SEM-215))
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#357` (added: participant attribution semantics)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#189` (Participant Causality And Attribution Semantics (SEM-212))
- IMPLEMENTS → GITHUB_ISSUE `189` (Participant Causality And Attribution Semantics (SEM-212))
- DOCUMENTS → SPEC `specs/formal/participant-semantics/README.md` (Participant Semantics Formal Design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md` (ADR-022: Participant Behavior and Interaction Semantics)
- DOCUMENTS → PULL_REQUEST `Brad-Edwards/aces#348` (Add participant semantics design)
- TESTS → TEST `implementations/python/tests/test_participant_semantics_invariant_oracle.py` (Participant semantics invariant oracle for SEM-212 attribution semantics)
