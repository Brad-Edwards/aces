---
id: SEM-207
title: "Declarative Objective Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:55:58.710666Z
updated_at: 2026-05-10T19:42:47.837158Z
---

# SEM-207 — Declarative Objective Semantics

## Statement

The ecosystem shall define explicit semantics for objective actor binding, target resolution, success interpretation, windows, and dependency ordering.

## Rationale

Requirement inventory phase. Status audit deferred until the full canonical graph is complete.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#4` (SEM-200: Shared Semantic Integrity)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (Declarative-objective validation pass (_verify_objectives via analyze_objective_semantics))
- IMPLEMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#64` (Declarative objective semantics (SEM-207))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/semantics/objective_semantics.py` (Declarative-objective semantic analyzer (analyze_objective_semantics, partition_objective_dependencies))
- IMPLEMENTS → DOCUMENTATION `specs/formal/objectives/declarative-objective-semantics.md` (SEM-207 formal semantic boundary (canonical inputs, required semantics, cross-cutting gates, anti-patterns, implementation mapping))
- IMPLEMENTS → DOCUMENTATION `docs/explain/reference/objective-semantics.md` (SEM-207 implementer-facing reference note (ADR-016 governed))
- TESTS → TEST `implementations/python/tests/test_semantics_objectives.py` (Objective semantics analyzer + dependency-partition unit tests (TestObjectiveSemantics, TestObjectiveDependencyPartition))
- TESTS → TEST `implementations/python/tests/test_fm2_semantics.py` (Cross-stage objective-semantics agreement (TestObjectiveSemanticAgreement))
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (SDL validator objective-binding tests (TestVerifyObjectives))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (Compiled ObjectiveRuntime ordering/refresh derivation via partition_objective_dependencies)
