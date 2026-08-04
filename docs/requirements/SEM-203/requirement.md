---
id: SEM-203
title: "Workflow Control Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:40.192269Z
updated_at: 2026-04-05T02:40:10.318695Z
---

# SEM-203 — Workflow Control Semantics

## Statement

The ecosystem shall define explicit, portable control semantics for workflow branching, joining, calling, retry, completion, and execution history.

## Rationale

Current state: implemented. Workflow behavior needs explicit state-machine-style meaning so it is not reconstructed differently by each execution environment.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL Sections Reference)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (SDL Runtime Architecture)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (SDL Semantic Validation)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/testing.md` (SDL Testing Guide)
- CONSTRAINS → ADR `ADR-006` (Workflow Control Language Redesign)
- CONSTRAINS → ADR `ADR-007` (Lightweight Formal Methods Policy for Semantic Systems)
- CONSTRAINS → SPEC `specs/formal/workflows/state-machine.md` (Workflow State Machine)
- CONSTRAINS → SPEC `specs/formal/workflows/README.md` (Workflow Semantics Overview)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (Workflow Validator Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Workflow Runtime Model Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_manager.py` (Workflow Runtime Manager Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Workflow Planner Semantics Tests)
