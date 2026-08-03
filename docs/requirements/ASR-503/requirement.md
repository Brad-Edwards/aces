---
id: ASR-503
title: "Formal Semantic Artifacts"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:40:05.484258Z
updated_at: 2026-04-05T03:16:57.016627Z
---

# ASR-503 — Formal Semantic Artifacts

## Statement

The ecosystem shall maintain formal semantic artifacts that describe the normative meaning of key language and runtime constructs.

## Rationale

Current state: implemented. Normative semantic artifacts are required so high-risk constructs have documented meaning beyond code-level convention.

## Traceability

- TESTS → TEST `implementations/python/tests/test_semantics_objectives.py` (Objective Semantic Tests)
- TESTS → TEST `implementations/python/tests/test_semantics_planner.py` (Planner Semantic Tests)
- DOCUMENTS → DOCUMENTATION `specs/formal/README.md` (Formal Specs Overview)
- CONSTRAINS → ADR `ADR-007` (Lightweight Formal Methods Policy for Semantic Systems)
- CONSTRAINS → SPEC `specs/formal/workflows/state-machine.md` (Workflow State Machine)
- CONSTRAINS → SPEC `specs/formal/workflows/compensation.md` (Workflow Compensation Semantics)
- CONSTRAINS → SPEC `specs/formal/objectives/window-consistency.md` (Objective Window Consistency)
- CONSTRAINS → SPEC `specs/formal/planner/dependency-ordering.md` (Planner Dependency Ordering)
- CONSTRAINS → SPEC `specs/formal/runtime-contracts/workflow-results.md` (Workflow Result Contract)
- CONSTRAINS → SPEC `specs/formal/runtime-contracts/evaluator-results.md` (Evaluator Result Contract)
- TESTS → TEST `implementations/python/tests/test_fm2_semantics.py` (FM2 Semantic Tests)
