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
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_base.py` (SDL variable placeholder parsing helpers)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/parser.py` (SDL parser key-stability enforcement)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/variables.py` (SDL variable declarations, types, defaults, and allowed values)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/scenario.py` (SDL scenario model including variables section)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/instantiate.py` (SDL instantiation and value substitution)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/accounts.py` (SDL account fields supporting parameterized values)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/entities.py` (SDL entity role fields supporting parameterized values)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/infrastructure.py` (SDL infrastructure fields supporting parameterized values)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/nodes.py` (SDL node fields supporting parameterized values)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/objectives.py` (SDL objective success fields supporting parameterized values)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (Parser tests for stable keys and placeholder acceptance)
- TESTS → TEST `implementations/python/tests/test_sdl_models.py` (Model tests for variable-capable leaf fields and variable definitions)
- TESTS → TEST `implementations/python/tests/test_scenarios.py` (Scenario loading tests preserving placeholders in examples)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Runtime planner tests for variable-backed OS and count values)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (SDL semantic validation for declared variable refs)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#401` (SDL gap: first-class directory and domain identity semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_directory_identity.py` (Identity authority stable local identifier namespace)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#407` (fix(sdl): harden identity authority refs)
