---
id: SEM-217
title: "Semantics Of External Knowledge Bindings"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 3
created_at: 2026-04-03T07:17:04.690343Z
updated_at: 2026-06-23T06:18:46.988350Z
---

# SEM-217 — Semantics Of External Knowledge Bindings

## Statement

The ecosystem shall define the semantic effect of external knowledge bindings, including when they annotate, constrain, refine, or align native meaning.

## Rationale

Requirement inventory expansion. External knowledge bindings need explicit semantics so they do not distort native meaning.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#92` (Derived-context, evidence-boundary & external-knowledge semantics (SEM-214, 216, 217))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#249` (Semantics Of External Knowledge Bindings (SEM-217))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/semantic_binding_effects.py` (SEM-217 external knowledge binding effect classifier)
- IMPLEMENTS → SPEC `specs/formal/participant-semantics/README.md` (SEM-217 external knowledge binding effect semantics)
- IMPLEMENTS → DOCUMENTATION `docs/explain/reference/shared-concept-model.md` (SEM-217 shared concept model binding-effect guidance)
- TESTS → TEST `implementations/python/tests/test_sem_217_knowledge_bindings.py` (SEM-217 external knowledge binding effect tests)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#585` (PR 585: added: define external knowledge bindings)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#249` (Issue 249: Semantics Of External Knowledge Bindings (SEM-217))
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-semantic-integrity.md` (Shared semantic integrity SEM-217 coverage row)
