---
id: SEM-202
title: "Objective Window Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:40.080129Z
updated_at: 2026-04-05T02:39:01.699426Z
---

# SEM-202 — Objective Window Semantics

## Statement

The ecosystem shall define a shared semantic model for objective windows, referenced scopes, reachability, and refresh behavior.

## Rationale

Current state: implemented. Objective windows are a semantic surface whose meaning must remain consistent across validation, compilation, and planning.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (SDL Semantic Validation)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL Sections Reference)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (SDL Runtime Architecture)
- CONSTRAINS → ADR `ADR-007` (Lightweight Formal Methods Policy for Semantic Systems)
- CONSTRAINS → POLICY `docs/explain/reference/coding-standards.md` (Coding Standards for Semantic Systems)
- CONSTRAINS → SPEC `specs/formal/objectives/window-consistency.md` (Objective Window Consistency)
- CONSTRAINS → SPEC `specs/formal/objectives/README.md` (Objective Semantics Overview)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/semantics/objectives.py` (Shared Objective Window Semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (Runtime Objective Window Model)
- TESTS → TEST `implementations/python/tests/test_semantics_objectives.py` (Shared Objective Window Semantic Tests)
- TESTS → TEST `implementations/python/tests/test_fm2_semantics.py` (Cross-Stage FM2 Objective Window Agreement Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (Objective Window Validator Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime Objective Window Model Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Objective Window Planner Refresh Tests)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#4` (SEM-200: Shared Semantic Integrity)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (SDL Objective Window Validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (Runtime Compiler Objective Window Binding)
