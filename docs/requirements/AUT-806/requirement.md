---
id: AUT-806
title: "Examples, Templates, And Pattern Libraries"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T07:15:30.275877Z
updated_at: 2026-05-24T05:36:11.479760Z
---

# AUT-806 — Examples, Templates, And Pattern Libraries

## Statement

The ecosystem shall maintain worked examples, templates, and reusable pattern libraries for scenarios, workflows, participant behavior, tasks, runs, and studies.

## Rationale

Requirement inventory expansion. Mature ecosystems need reusable examples and patterns, not just validation fixtures.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#86` (Canonical documentation, glossary & reference; examples, templates & pattern libraries (AUT-805, 806))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#227` (Examples, Templates, And Pattern Libraries (AUT-806))
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#404` (feat: add AUT-806 example library)
- IMPLEMENTS → CODE_FILE `examples/library/catalog.yaml` (AUT-806 example template and pattern library catalog)
- IMPLEMENTS → POLICY `tools/check_example_library.py` (AUT-806 example library policy checker)
- TESTS → TEST `implementations/python/tests/test_example_library_policy.py` (AUT-806 example library policy tests)
- DOCUMENTS → DOCUMENTATION `README.md` (Agentic Cyber Environment System README)
- DOCUMENTS → DOCUMENTATION `examples/README.md` (ACES Examples)
- DOCUMENTS → DOCUMENTATION `docs/explain/getting-started.md` (Getting Started With ACES)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/canonical-reference-map.md` (Canonical Reference Map)
