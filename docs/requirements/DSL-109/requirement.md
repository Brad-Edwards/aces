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
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/scenario.py` (Scenario model exposing content, accounts, and relationships as first-class sections)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/content.py` (Content model for files, datasets, directories, and dataset items)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/accounts.py` (Account model with password/auth fields and AD-oriented properties)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/relationships.py` (Typed relationship model spanning authentication, trust, federation, and connectivity)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/composition.py` (Namespace-aware rewriting for imported content, accounts, and relationships)
- IMPLEMENTS → PULL_REQUEST `369` (PR #369 feat(sdl): add runtime inventory surfaces)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (Semantic validation for content/account VM targeting and relationship endpoint resolution)
- DOCUMENTS → GITHUB_ISSUE `363` (Issue #363 runtime filesystem inventory metadata and checksums)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_filesystem.py` (Runtime filesystem inventory entries with metadata, digests, provenance, stability, and sensitivity)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_configuration.py` (Node runtime aggregation model for filesystem inventory entries)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (Parser tests for runtime filesystem inventory metadata and digest fields)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime compiler tests preserving filesystem inventory facts without diagnostics)
- VERIFIES → SPEC `examples/scenarios/techvault.sdl.yaml` (TechVault scenario example exercising runtime filesystem inventory metadata and digest fields)
- IMPLEMENTS → GITHUB_ISSUE `441` (Issue #441 runtime family registry convergence)
- IMPLEMENTS → PULL_REQUEST `448` (PR #448 fix: unify runtime service family registry)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_runtime_service_families.py` (Canonical runtime service-family registry for exports, qualified refs, and nested-node aliases)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_module_runtime_aliases.py` (Runtime module alias facade delegated to the canonical runtime service-family registry)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_module_symbols.py` (Module symbol index integration for registry-generated runtime-family nested-node aliases)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/nodes.py` (Node facade exports runtime service-family symbols from the canonical registry)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_directory_identity.py` (Runtime identity attribute origin/provenance reconciliation for lossless relationship-target inventory capture)
- TESTS → TEST `implementations/python/tests/test_runtime_ssh_server.py` (Runtime service-family registry and SSH nested-node reference coverage tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/account_features.py` (Provisioner account-feature extraction (shared by planner capability validation))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (Runtime compilation of relationship specs plus content/account placements)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/planner/__init__.py` (Planner capability validation and lifecycle ordering for content/account provisioning)
