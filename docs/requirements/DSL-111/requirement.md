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
