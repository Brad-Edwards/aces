---
id: RUN-302
title: "Compiled Processing Representation"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:40.655338Z
updated_at: 2026-04-05T03:19:48.490694Z
---

# RUN-302 — Compiled Processing Representation

## Statement

The processing layer shall compile valid scenarios into a typed processing representation that preserves semantic meaning across execution stages.

## Rationale

Current state: implemented. A compiled representation is required so processing behavior is driven by explicit meaning rather than ad hoc reinterpretation of authoring inputs.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (SDL Runtime Architecture)
- CONSTRAINS → ADR `ADR-008` (Processor Layer And Execution Artifact Boundaries)
- CONSTRAINS → SPEC `specs/formal/composition-readiness.md` (Composition Readiness)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime Model Compilation Tests)
- TESTS → TEST `implementations/python/tests/test_fm2_semantics.py` (FM2 Semantic Tests)
