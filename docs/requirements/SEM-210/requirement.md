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

- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (SEM-210 runtime conformance tests for participant-local visibility validation)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-semantic-integrity.md` (Shared semantic integrity SEM-210 coverage row)
- DOCUMENTS → SPEC `specs/formal/participant-semantics/README.md` (Participant Semantics Formal Design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md` (ADR-022: Participant Behavior and Interaction Semantics)
- TESTS → TEST `implementations/python/tests/test_sem_208_participant_behavior.py` (SEM-210 participant visibility leakage and disclosure tests)
- TESTS → TEST `implementations/python/tests/test_participant_semantics_invariant_oracle.py` (Participant semantics invariant oracle for SEM-210 visibility semantics)
