---
id: SEM-205
title: "Canonical Namespace-Extensible Identities"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:40.418697Z
updated_at: 2026-04-05T02:43:01.647110Z
---

# SEM-205 — Canonical Namespace-Extensible Identities

## Statement

The ecosystem shall preserve canonical identities that remain stable across module expansion, compilation, planning, and backend contracts.

## Rationale

Current state: implemented. Stable canonical identities are required so composition and runtime semantics do not depend on source-file layout or local naming accidents.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/parser.md` (SDL Parser Guide)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/index.md` (SDL Overview)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL Sections Reference)
- CONSTRAINS → SPEC `specs/formal/composition-readiness.md` (Composition Readiness)
- CONSTRAINS → SPEC `specs/formal/objectives/window-consistency.md` (Objective Window Consistency)
- CONSTRAINS → SPEC `specs/formal/planner/dependency-ordering.md` (Planner Dependency Ordering)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (SDL Parser Namespace Import Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_module_registry.py` (SDL Module Registry Namespace Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Canonical Runtime Identity Tests)
- TESTS → TEST `implementations/python/tests/test_semantics_planner.py` (Planner Canonical Identity Semantics Tests)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-053-sdl-module-composition-for-inventory-backed-scenarios.md` (ADR-053: SDL Module Composition for Inventory-Backed Scenarios)
- TESTS → TEST `implementations/python/tests/test_semantics_assessment.py` (Assessment composition-readiness invariant tests)
- TESTS → TEST `implementations/python/tests/test_semantics_objectives.py` (Objective-window composition-readiness invariant tests)
