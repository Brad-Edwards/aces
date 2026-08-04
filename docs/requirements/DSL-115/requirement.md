---
id: DSL-115
title: "Author-Selectable Specificity And Constraint Surface"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T00:54:58.287304Z
updated_at: 2026-07-09T05:54:46.937375Z
---

# DSL-115 — Author-Selectable Specificity And Constraint Surface

## Statement

The language shall allow scenario, participant, evaluation, and experiment concerns to be authored at different levels of specificity, including open or underspecified forms, constrained forms, and exact binding requirements where relevant.

## Rationale

Current state: identified gap. Authors need to be able to leave concerns open in some experiments while requiring exact properties in others without forcing one global abstraction level.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/lineage.md` (SDL lineage and prior work)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/precedents.md` (SDL design precedents for participant semantics and language adequacy)
- IMPLEMENTS → DOCUMENTATION `docs/explain/reference/explicitness-realization-semantics.md` (DSL-115 authoring specificity reference)
- TESTS → TEST `implementations/python/tests/test_dsl_115_authoring_specificity.py` (DSL-115 authoring specificity regression tests)
- IMPLEMENTS → GITHUB_ISSUE `73` (Author-selectable specificity & constraint surface (DSL-115))
- IMPLEMENTS → PULL_REQUEST `710` (feat(sdl): add DSL-115 authoring specificity helper)
