---
id: DSL-101
title: "Stable Identifiers And Parameterized Values"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:39.447109Z
updated_at: 2026-04-05T00:39:53.401396Z
---

# DSL-101 — Stable Identifiers And Parameterized Values

## Statement

The language shall preserve stable declared identifiers while allowing parameter values to specialize attributes without changing symbol identity.

## Rationale

Current state: implemented. Stable identifiers and parameterized values are required so reference resolution, composition, and validation remain deterministic across authoring and runtime stages.

## Traceability

- CONSTRAINS → ADR `docs/decisions/adrs/adr-003-workflows-targetable-subobjects-and-enum-variables.md` (ADR-003: leaf enum variables and stable symbol table policy)
- CONSTRAINS → SPEC `specs/formal/composition-readiness.md` (Composition readiness and canonical identity)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/parser.md` (SDL parser behavior and placeholder rules)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/index.md` (SDL overview: stable IDs, variable values)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL sections reference: variable-capable fields)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/limitations.md` (SDL limitations and placeholder constraints)
- CONSTRAINS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring input schema)
- CONSTRAINS → SPEC `contracts/schemas/sdl/scenario-instantiation-request-v1.json` (Scenario instantiation request schema)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (Parser tests for stable keys and placeholder acceptance)
- TESTS → TEST `implementations/python/tests/test_sdl_models.py` (Model tests for variable-capable leaf fields and variable definitions)
- TESTS → TEST `implementations/python/tests/test_scenarios.py` (Scenario loading tests preserving placeholders in examples)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Runtime planner tests for variable-backed OS and count values)
