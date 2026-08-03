---
id: SEM-214
title: "Portable Semantics For Derived Context Views"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 3
created_at: 2026-04-03T06:15:26.934801Z
updated_at: 2026-06-23T00:11:28.940437Z
---

# SEM-214 — Portable Semantics For Derived Context Views

## Statement

The ecosystem shall define explicit meaning and comparability semantics for derived operational context views so their interpretation remains portable across runtimes and backends.

## Rationale

Requirement inventory expansion. Derived context views need normative meaning if they are to support portable participant behavior.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#4` (SEM-200: Shared Semantic Integrity)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#92` (Derived-context, evidence-boundary & external-knowledge semantics (SEM-214, 216, 217))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Participant context-view SEM-214 contract model)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/participant_retrieval.py` (Runtime participant context-view SEM-214 projection)
- IMPLEMENTS → SPEC `contracts/schemas/control-plane/participant-context-view-v1.json` (Published participant context-view JSON Schema)
- IMPLEMENTS → SPEC `specs/formal/participant-semantics/README.md` (SEM-214 participant semantics formal reference)
- IMPLEMENTS → SPEC `specs/formal/runtime-contracts/participant-backend-contracts.md` (Participant backend context-view contract semantics)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-060-participant-backend-facing-contract-surface.md` (ADR-060 participant backend-facing contract surface)
- IMPLEMENTS → DOCUMENTATION `docs/explain/reference/shared-semantic-integrity.md` (Shared semantic integrity reference for SEM-214)
- TESTS → TEST `implementations/python/tests/test_participant_backend_contracts.py` (Participant context-view contract and fixture tests)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane.py` (Runtime control-plane context-view tests)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane_api.py` (HTTP participant context-view and auth tests)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#247` (Portable Semantics For Derived Context Views (SEM-214))
