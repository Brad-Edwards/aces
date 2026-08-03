---
id: SEM-215
title: "Participant Outcome Interpretation Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:15:27.040461Z
updated_at: 2026-05-21T08:49:36.914659Z
---

# SEM-215 — Participant Outcome Interpretation Semantics

## Statement

The ecosystem shall define explicit semantics for interpreting participant-local outcomes and relating them to scenario, objective, workflow, and evaluation meaning.

## Rationale

Requirement inventory expansion. Participant-local outcomes need normative meaning rather than ad hoc interpretation by individual backends.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#4` (SEM-200: Shared Semantic Integrity)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#191` (Participant Outcome Interpretation Semantics (SEM-215))
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#362` (feat: add participant outcome interpretation semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/participant_outcome_semantics.py` (SDL participant outcome interpretation rule models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/semantics/participant_outcome.py` (SDL participant outcome semantic analyzer)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (Runtime participant outcome interpretation records and validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Published participant outcome interpretation contract models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/scenario.py` (Scenario outcome interpretation rule section)
- TESTS → TEST `implementations/python/tests/test_sem_215_participant_outcome_interpretation.py` (SEM-215 participant outcome interpretation tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (Participant outcome interpretation validation integration)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#71` (Participant behavior & interaction semantics (SEM-208…213, 215))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#71` (Participant behavior & interaction semantics (SEM-208, SEM-209, SEM-210, SEM-211, SEM-212, SEM-213, SEM-215))
- DOCUMENTS → SPEC `specs/formal/participant-semantics/README.md` (Participant Semantics Formal Design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md` (ADR-022: Participant Behavior and Interaction Semantics)
- DOCUMENTS → PULL_REQUEST `Brad-Edwards/aces#348` (Add participant semantics design)
- TESTS → TEST `implementations/python/tests/test_participant_semantics_invariant_oracle.py` (Participant semantics invariant oracle for SEM-215 outcome semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (Compiled participant outcome interpretation rules)
