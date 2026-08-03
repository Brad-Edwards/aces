---
id: DSL-109
title: "Content, Account, And Relationship Modeling"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:55:58.023501Z
updated_at: 2026-04-05T01:21:31.612399Z
---

# DSL-109 — Content, Account, And Relationship Modeling

## Statement

The language shall model placed content, system and user accounts, and typed relationships among named scenario elements.

## Rationale

Requirement inventory phase. Status audit deferred until the full canonical graph is complete.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL sections reference for content, accounts, and typed relationships)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (Validation rules for content targets, account nodes, and relationship endpoint resolution)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/precedents.md` (Design precedents for content, accounts, and relationship modeling)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (Runtime architecture covering content/account provisioning semantics and capability validation)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-001-scenario-description-language.md` (ADR-001: content, accounts, and relationships are first-class SDL sections)
- CONSTRAINS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema for content, account, and relationship sections)
- CONSTRAINS → SPEC `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated SDL schema carrying normalized content, accounts, and relationships)
- TESTS → TEST `implementations/python/tests/test_sdl_models.py` (Model tests for content types, account fields, and relationship kinds)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (Validator tests for content targets, account nodes, and relationship reference resolution)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Planner tests for content/account lifecycle behavior and ordering)
- TESTS → TEST `implementations/python/tests/test_sdl_stress.py` (Stress scenarios exercising content, accounts, relationships, and supporting SDL surfaces together)
- TESTS → TEST `implementations/python/tests/test_sdl_realworld.py` (Real-world scenarios modeling placed content, accounts, and service relationships)
- IMPLEMENTS → PULL_REQUEST `369` (PR #369 feat(sdl): add runtime inventory surfaces)
- DOCUMENTS → GITHUB_ISSUE `363` (Issue #363 runtime filesystem inventory metadata and checksums)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (Parser tests for runtime filesystem inventory metadata and digest fields)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime compiler tests preserving filesystem inventory facts without diagnostics)
- VERIFIES → SPEC `examples/scenarios/techvault.sdl.yaml` (TechVault scenario example exercising runtime filesystem inventory metadata and digest fields)
- IMPLEMENTS → GITHUB_ISSUE `441` (Issue #441 runtime family registry convergence)
- IMPLEMENTS → PULL_REQUEST `448` (PR #448 fix: unify runtime service family registry)
- TESTS → TEST `implementations/python/tests/test_runtime_ssh_server.py` (Runtime service-family registry and SSH nested-node reference coverage tests)
