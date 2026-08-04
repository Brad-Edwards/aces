---
id: DSL-112
title: "Declarative Objective Surface"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:55:58.365295Z
updated_at: 2026-04-05T02:27:45.780469Z
---

# DSL-112 — Declarative Objective Surface

## Statement

The language shall support declarative objectives that bind actors, targets, success criteria, windows, and dependency ordering.

## Rationale

Requirement inventory phase. Status audit deferred until the full canonical graph is complete.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/index.md` (SDL Overview)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL Sections Reference)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/complex-scenarios.md` (Complex SDL Scenarios)
- CONSTRAINS → ADR `ADR-002` (Declarative Experiment Objectives in the SDL)
- CONSTRAINS → DOCUMENTATION `docs/explain/sdl/validation.md` (SDL Validation Guide)
- CONSTRAINS → SPEC `specs/formal/objectives/README.md` (Formal Objective Semantics Overview)
- CONSTRAINS → SPEC `specs/formal/objectives/window-consistency.md` (Objective Window Consistency Spec)
- TESTS → TEST `implementations/python/tests/test_sdl_models.py` (SDL Objective Model Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (SDL Parser Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (SDL Objective Validation Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime Objective Model Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Runtime Objective Planner Tests)
- TESTS → TEST `implementations/python/tests/test_semantics_objectives.py` (Objective Semantics Tests)
