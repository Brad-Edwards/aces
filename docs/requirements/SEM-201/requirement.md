---
id: SEM-201
title: "Fail-Closed Semantic Validation"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:39.964723Z
updated_at: 2026-04-05T02:37:32.171675Z
---

# SEM-201 — Fail-Closed Semantic Validation

## Statement

The ecosystem shall reject semantically ambiguous, dangling, cyclic, or otherwise inconsistent scenario descriptions before runtime compilation.

## Rationale

Current state: implemented. Fail-closed validation prevents unresolved meaning from leaking into planners, runtimes, or backends.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (SDL Semantic Validation)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/index.md` (SDL Overview)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL Sections Reference)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/testing.md` (SDL Testing Guide)
- CONSTRAINS → ADR `ADR-007` (Lightweight Formal Methods Policy for Semantic Systems)
- CONSTRAINS → POLICY `docs/explain/reference/coding-standards.md` (Coding Standards for Semantic Systems)
- CONSTRAINS → SPEC `specs/formal/README.md` (Formal Specs Overview)
- CONSTRAINS → SPEC `specs/formal/workflows/README.md` (Workflow Semantics Overview)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/parser.py` (SDL Parser)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/instantiate.py` (SDL Instantiation Revalidation)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (SDL Validator Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (SDL Parser Tests)
- TESTS → TEST `implementations/python/tests/test_fm2_semantics.py` (Cross-Stage FM2 Semantic Agreement Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_realworld.py` (Real-World SDL Semantic Validation Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_fuzz.py` (SDL Fuzz Validation Tests)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#4` (SEM-200: Shared Semantic Integrity)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (SDL Semantic Validator)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#401` (SDL gap: first-class directory and domain identity semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_directory_identity.py` (SDL Runtime Directory Identity Models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_configuration.py` (SDL Runtime Configuration Models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/nodes.py` (SDL Node Runtime Exports)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_module_symbols.py` (SDL Module Symbol Rewriting)
- TESTS → TEST `implementations/python/tests/test_sdl_models.py` (SDL Model Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime Compilation Tests)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#407` (fix(sdl): harden identity authority refs)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/identity_domains.py` (Authored identity-domain declarations)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/domain_topology.py` (Provisioning domain-topology validation)
- TESTS → TEST `implementations/python/tests/test_authored_domain_topology.py` (Authored domain-topology regression tests)
- IMPLEMENTS → ADR `ADR-082` (Authored Identity Domain Topology)
- IMPLEMENTS → GITHUB_ISSUE `763` (SDL gap: authored domain topology (DC role / domain-join) for domain-backed realization)
