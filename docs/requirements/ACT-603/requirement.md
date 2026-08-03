---
id: ACT-603
title: "Abstract Participant Interaction Model"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T05:40:05.975556Z
updated_at: 2026-06-24T00:50:07.597198Z
---

# ACT-603 — Abstract Participant Interaction Model

## Statement

The ecosystem shall define an abstract, portable participant interaction model covering participant actions, observations, state, preconditions, effects, and failure classes independent of backend wire formats.

## Rationale

Requirement inventory expansion. Participant behavior cannot be portable until its action, observation, state, and effect surfaces are explicit.

## Traceability

- IMPLEMENTS → ADR `docs/decisions/adrs/adr-067-participant-behavior-model.md` (ADR-067 Participant Behavior Model)
- IMPLEMENTS → SPEC `specs/formal/participant-behavior-model/README.md` (Formal participant behavior model specification)
- IMPLEMENTS → GITHUB_ISSUE `77` (Issue #77 - Participant behavior model)
- IMPLEMENTS → GITHUB_ISSUE `205` (Issue #205 - Abstract Participant Interaction Model)
- TESTS → TEST `implementations/python/tests/test_sem_208_participant_behavior.py` (SEM-208 participant behavior model tests)
- TESTS → TEST `implementations/python/tests/test_sem_211_participant_action_semantics.py` (SEM-211 participant action semantics tests)
- TESTS → TEST `implementations/python/tests/test_run_305_participant_runtime_state_history.py` (RUN-305 participant runtime state history tests)
- TESTS → TEST `implementations/python/tests/test_sem_215_participant_outcome_interpretation.py` (SEM-215 participant outcome interpretation tests)
