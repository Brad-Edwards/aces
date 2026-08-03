---
id: SEM-204
title: "Workflow Compensation Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:40.306252Z
updated_at: 2026-04-05T02:41:37.997067Z
---

# SEM-204 — Workflow Compensation Semantics

## Statement

The ecosystem shall define explicit compensation semantics for registration, triggering, ordering, and observation of compensating actions.

## Rationale

Current state: implemented. Compensation behavior must be declared and portable rather than invented as backend-local rollback logic.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL Sections Reference)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (SDL Runtime Architecture)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/testing.md` (SDL Testing Guide)
- CONSTRAINS → ADR `ADR-006` (Workflow Control Language Redesign)
- CONSTRAINS → SPEC `specs/formal/workflows/compensation.md` (Workflow Compensation Semantics)
- CONSTRAINS → SPEC `specs/formal/workflows/README.md` (Workflow Semantics Overview)
- CONSTRAINS → SPEC `specs/formal/runtime-contracts/workflow-results.md` (Workflow Result Contracts)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/orchestration.py` (SDL Workflow Compensation Authoring Models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (Workflow Compensation Runtime State Models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/manager.py` (Workflow Compensation Runtime Validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/control_plane_api.py` (Workflow Compensation Control Plane Surface)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (Workflow Compensation Validator Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Workflow Compensation Runtime Model Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_manager.py` (Workflow Compensation Runtime Manager Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane_api.py` (Workflow Compensation Control Plane Tests)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#4` (SEM-200: Shared Semantic Integrity)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (Workflow Compensation Validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (Workflow Compensation Contract Compilation)
