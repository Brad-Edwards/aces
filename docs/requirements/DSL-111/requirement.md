---
id: DSL-111
title: "Entity And Exercise Timeline Modeling"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:55:58.251562Z
updated_at: 2026-04-05T01:25:56.822025Z
---

# DSL-111 — Entity And Exercise Timeline Modeling

## Statement

The language shall model entities, injects, events, scripts, and stories for exercise organization and timeline structure.

## Rationale

Requirement inventory phase. Status audit deferred until the full canonical graph is complete.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL sections reference for entities, injects, events, scripts, and stories)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (Validation rules for entity references and orchestration timeline integrity)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/parser.md` (Parser normalization for timeline fields such as start-time and end-time)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (Runtime architecture for orchestrated inject, event, script, and story execution)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-001-scenario-description-language.md` (ADR-001: entities and timeline orchestration are first-class SDL sections)
- CONSTRAINS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema for entities and orchestration sections)
- CONSTRAINS → SPEC `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated SDL schema carrying normalized entities and timeline structures)
- TESTS → TEST `implementations/python/tests/test_sdl_models.py` (Model tests for entity nesting, duration parsing, injects, scripts, and stories)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (Validator tests for entity, inject, event, script, and story reference checks)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime model tests for inject bindings and orchestration window resolution)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Planner tests for inject, event, script, and story scheduling behavior)
- TESTS → TEST `implementations/python/tests/test_sdl_realworld.py` (Real-world scenarios exercising nested entities and timeline orchestration together)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/scenario.py` (Scenario model exposing entities, injects, events, scripts, and stories as first-class sections)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/entities.py` (Recursive entity model with flattened dot-path addressing for exercise roles)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/orchestration.py` (Inject, event, script, and story models plus timeline duration parsing)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/composition.py` (Namespace-aware rewriting for imported entities, injects, events, scripts, and stories)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (Semantic validation for entity references and orchestration timeline integrity)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (Runtime compilation of entity specs and orchestration resources for injects, events, scripts, and stories)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/planner/__init__.py` (Planner capability validation and ordering for orchestration resources and inject bindings)
