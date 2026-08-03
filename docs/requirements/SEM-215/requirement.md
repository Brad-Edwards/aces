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

- TESTS → TEST `implementations/python/tests/test_sem_215_participant_outcome_interpretation.py` (SEM-215 participant outcome interpretation tests)
- DOCUMENTS → SPEC `specs/formal/participant-semantics/README.md` (Participant Semantics Formal Design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md` (ADR-022: Participant Behavior and Interaction Semantics)
- TESTS → TEST `implementations/python/tests/test_participant_semantics_invariant_oracle.py` (Participant semantics invariant oracle for SEM-215 outcome semantics)
