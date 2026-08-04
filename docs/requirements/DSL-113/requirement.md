---
id: DSL-113
title: "Declarative Workflow Surface"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:55:58.479340Z
updated_at: 2026-04-05T02:29:58.596280Z
---

# DSL-113 — Declarative Workflow Surface

## Statement

The language shall support declarative workflows over objectives and portable workflow state without embedding backend-specific execution logic.

## Rationale

Requirement inventory phase. Status audit deferred until the full canonical graph is complete.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/index.md` (SDL Overview)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL Sections Reference)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (SDL Runtime Architecture)
- CONSTRAINS → ADR `ADR-006` (Workflow Control-Language Redesign)
- CONSTRAINS → SPEC `specs/formal/workflows/README.md` (Workflow Semantics Overview)
- CONSTRAINS → SPEC `specs/formal/workflows/state-machine.md` (Workflow State Machine Spec)
- CONSTRAINS → SPEC `specs/formal/runtime-contracts/workflow-results.md` (Workflow Result Contract Spec)
- CONSTRAINS → DOCUMENTATION `docs/explain/sdl/validation.md` (SDL Validation Guide)
- TESTS → TEST `implementations/python/tests/test_sdl_models.py` (SDL Workflow Model Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (SDL Parser Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (SDL Workflow Validation Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_manager.py` (Runtime Workflow Contract Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime Workflow Model Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Runtime Planner Tests)
