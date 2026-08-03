---
id: DSL-102
title: "Unambiguous Qualified References"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:39.601484Z
updated_at: 2026-04-05T01:18:33.771466Z
---

# DSL-102 — Unambiguous Qualified References

## Statement

The language shall support unambiguous qualified references across sections, workflows, and imported namespaces.

## Rationale

Current state: implemented. Cross-cutting references are central to scenario meaning and need one consistent surface instead of section-specific special cases.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/index.md` (SDL overview documenting bare and section-qualified cross-section references)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL sections reference for relationship endpoints, objective targets, named services, ACLs, and workflow step refs)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (Semantic validation rules for ambiguous refs, qualified alternatives, and workflow/window resolution)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (Runtime architecture for fail-closed bound references and canonical resolved runtime addresses)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-003-workflows-targetable-subobjects-and-enum-variables.md` (ADR-003: targetable sub-objects and workflow step reference syntax)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-004-sdl-runtime-layer.md` (ADR-004: canonical runtime addresses and fail-closed bound reference resolution)
- CONSTRAINS → SPEC `specs/formal/objectives/window-consistency.md` (Formal window-reference normalization and composition-ready invariants)
- CONSTRAINS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema exposing imports, objectives, workflows, and named cross-section surfaces)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (Validator tests for ambiguous bare refs, qualified refs, named services/ACLs, and target resolution)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (Parser tests for namespaced imports rewriting cross-section references)
- TESTS → TEST `implementations/python/tests/test_sdl_module_registry.py` (Module registry tests for namespaced imports, collisions, and semantic validation after expansion)
- TESTS → TEST `implementations/python/tests/test_semantics_objectives.py` (Semantic tests for normalized workflow step references and fail-closed window analysis)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime compiler tests for namespaced workflows/objectives and canonical resolved addresses)
- TESTS → TEST `implementations/python/tests/test_runtime_planner.py` (Planner tests for ambiguous bound condition refs failing closed)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/composition.py` (Namespace rewriting for imported modules across objectives, workflows, and cross-section references)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/parser.py` (Parser integration for expanded namespaced imports before semantic validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/semantics/objectives.py` (Normalized workflow and workflow-step reference analysis for objective windows)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (Shared named-reference index and ambiguity checks for relationships, objectives, and workflows)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#401` (SDL gap: first-class directory and domain identity semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_directory_identity.py` (Identity authority unambiguous local reference namespace)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#407` (fix(sdl): harden identity authority refs)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (Fail-closed bound reference resolution and canonical runtime addresses)
