---
id: DSL-103
title: "Deterministic Module Composition And Packaging"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:39.720387Z
updated_at: 2026-04-05T00:48:05.913509Z
---

# DSL-103 — Deterministic Module Composition And Packaging

## Statement

The language shall support deterministic module composition and distributable packaging with versioned imports, namespace isolation, integrity protection, and lockable resolution.

## Rationale

Current state: implemented. Large scenarios and reusable assets require composition that remains reproducible and supply-chain aware across environments.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/parser.md` (SDL parser documentation for imports and deterministic file-backed composition)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL sections reference for module descriptors and imports)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/precedents.md` (SDL precedents documenting Terraform-style composition patterns)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/limitations.md` (SDL limitations for hosted registry operations and ecosystem distribution)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-009-normative-artifact-authority-and-repository-structure.md` (ADR-009: normative artifact authority and repository structure)
- CONSTRAINS → SPEC `specs/formal/composition-readiness.md` (Formal composition-readiness invariants)
- CONSTRAINS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema with ImportDecl and ModuleDescriptor)
- CONSTRAINS → SPEC `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated SDL schema carrying import and module metadata)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/scenario.py` (Scenario model for ModuleDescriptor and ImportDecl)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/parser.py` (Parser integration for file-backed import expansion)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/composition.py` (Module composition and namespace rewriting)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/module_registry.py` (Lockfile resolution, trust policy, digest verification, and OCI packaging)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_cli/sdl.py` (SDL CLI commands for resolve, verify-imports, and publish)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (Parser tests for namespaced imports and version/collision handling)
- TESTS → TEST `implementations/python/tests/test_sdl_module_registry.py` (Registry and packaging tests for lockfiles, signed OCI imports, and fail-closed behavior)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-053-sdl-module-composition-for-inventory-backed-scenarios.md` (ADR-053: SDL Module Composition for Inventory-Backed Scenarios)
