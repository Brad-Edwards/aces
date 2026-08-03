---
id: DSL-104
title: "Scenario-Level Scope Boundary"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:39.842217Z
updated_at: 2026-04-05T00:56:49.930208Z
---

# DSL-104 — Scenario-Level Scope Boundary

## Statement

The language shall express scenario and experiment meaning without requiring backend-specific deployment configuration details.

## Rationale

Current state: implemented. The language core needs a stable scope boundary so author intent stays portable even when deployment mechanisms vary.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL sections reference for declarative, backend-agnostic scenario surface)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/limitations.md` (SDL limitations documenting deployment-layer exclusions by design)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/precedents.md` (SDL precedents for backend-agnostic and plain-data boundary decisions)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (Runtime architecture separating SDL meaning from backend execution details)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-001-scenario-description-language.md` (ADR-001: SDL as backend-agnostic specification language)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-002-declarative-sdl-objectives.md` (ADR-002: declarative objectives stay outside backend-specific probes)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-004-sdl-runtime-layer.md` (ADR-004: compile-plan-execute boundary after SDL authoring)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-008-processor-layer-and-execution-artifact-boundaries.md` (ADR-008: processor and execution artifact boundaries)
- CONSTRAINS → SPEC `specs/formal/runtime-contracts/README.md` (Formal runtime contract semantics for portable backend boundaries)
- CONSTRAINS → SPEC `specs/formal/runtime-contracts/workflow-results.md` (Portable workflow result envelope boundary)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_base.py` (SDL base model forbidding undeclared extra fields)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_source.py` (Provider-neutral source references delegated to backends)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/objectives.py` (Declarative objectives without backend-specific runtime probes)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (Portable runtime contract models beyond the SDL surface)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/manager.py` (Manager-side validation of backend payloads against compiled contracts)
- TESTS → TEST `implementations/python/tests/test_sdl_fuzz.py` (Fuzz tests ensuring unknown SDL fields fail cleanly)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (Parser tests for SDL-only boundary and legacy-format rejection)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime model tests for compiled result-contract boundaries)
- TESTS → TEST `implementations/python/tests/test_runtime_manager.py` (Manager tests validating backend payloads against compiled contracts)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (Compiler handoff from SDL meaning to runtime model)
