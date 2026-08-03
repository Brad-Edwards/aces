---
id: DSL-108
title: "Feature, Condition, And Vulnerability Modeling"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:55:57.908015Z
updated_at: 2026-04-05T01:04:22.622618Z
---

# DSL-108 — Feature, Condition, And Vulnerability Modeling

## Statement

The language shall model deployed features, health and assertion conditions, and classified vulnerabilities with explicit dependency and reference semantics.

## Rationale

Requirement inventory phase. Status audit deferred until the full canonical graph is complete.

## Traceability

- IMPLEMENTS → PULL_REQUEST `369` (PR #369 feat(sdl): add runtime inventory surfaces)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL sections reference for features, conditions, and vulnerabilities)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (SDL validation rules for feature dependencies and condition/vulnerability references)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/testing.md` (SDL testing matrix covering condition and vulnerability validation)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-001-scenario-description-language.md` (ADR-001: features, conditions, and vulnerabilities are core SDL sections)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-004-sdl-runtime-layer.md` (ADR-004: node-scoped condition bindings and fail-closed condition references)
- CONSTRAINS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema for feature, condition, and vulnerability sections)
- CONSTRAINS → SPEC `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated SDL schema carrying conditions and vulnerabilities after normalization)
- TESTS → TEST `implementations/python/tests/test_sdl_models.py` (Model tests for feature types, condition XOR rules, and CWE validation)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (Validator tests for undefined vulnerabilities, condition refs, and feature dependency cycles)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime model tests for feature dependency and condition binding semantics)
- TESTS → TEST `implementations/python/tests/test_sdl_stress.py` (Stress scenarios exercising features, conditions, and vulnerabilities together)
- TESTS → TEST `implementations/python/tests/test_sdl_realworld.py` (Real-world scenario tests modeling deployed vulnerabilities and condition-backed scoring)
- DOCUMENTS → GITHUB_ISSUE `368` (Issue #368 container health observations and runtime condition facts)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (Parser tests for runtime health and container observation fields)
- VERIFIES → SPEC `examples/scenarios/techvault.sdl.yaml` (TechVault scenario example exercising runtime health observation facts)
