---
id: SEM-200
title: "Shared Semantic Integrity"
status: DRAFT
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:07.447647Z
updated_at: 2026-04-04T22:54:53.197510Z
---

# SEM-200 — Shared Semantic Integrity

## Statement

The ecosystem shall provide a shared semantic layer that gives scenario constructs explicit, consistent meaning across validation, instantiation, compilation, planning, execution, live observation, and experiment interpretation.

## Rationale

Current state: partially implemented. Semantic consistency is required so language constructs mean the same thing across authoring, processing, contracts, and experiment interpretation rather than drifting between stages or implementations.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (SDL Runtime Architecture)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/index.md` (SDL Overview)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/coding-standards.md` (Coding Standards for Semantic Systems)
- CONSTRAINS → ADR `ADR-007` (Lightweight Formal Methods Policy for Semantic Systems)
- CONSTRAINS → SPEC `specs/formal/README.md` (Formal Specs Overview)
- CONSTRAINS → SPEC `specs/formal/objectives/README.md` (Formal Objective Semantics Overview)
- CONSTRAINS → SPEC `specs/formal/workflows/README.md` (Workflow Semantics Overview)
- CONSTRAINS → SPEC `specs/formal/planner/README.md` (Planner Graph Semantics Overview)
- CONSTRAINS → SPEC `specs/formal/runtime-contracts/README.md` (Runtime Contract Semantics Overview)
- TESTS → TEST `implementations/python/tests/test_fm2_semantics.py` (Cross-Stage FM2 Semantic Agreement Tests)
- TESTS → TEST `implementations/python/tests/test_semantics_objectives.py` (Objective Semantics Tests)
- TESTS → TEST `implementations/python/tests/test_semantics_planner.py` (Planner Semantics Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime Model Semantics Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_manager.py` (Runtime Contract Validation Tests)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#4` (SEM-200: Shared Semantic Integrity)
- DOCUMENTS → ADR `ADR-016` (Semantic Layer Scope and Coverage Model (SEM-200))
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-semantic-integrity.md` (Shared Semantic Integrity — guardrails note and live coverage model)
- VERIFIES → CODE_FILE `tools/check_semantic_coverage.py` (Structural gate for the SEM-200 coverage model)
- TESTS → TEST `implementations/python/tests/test_semantic_coverage.py` (Tests for the SEM-200 semantic-coverage structural gate (existence + integration + stub + report))
- DOCUMENTS → GITHUB_ISSUE `834` (Implement SEM-200: Shared Semantic Integrity (aces #834))
