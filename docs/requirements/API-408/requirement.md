---
id: API-408
title: "Participant Observation And Retrieval Contracts"
status: ACTIVE
type: INTERFACE
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:16:04.481738Z
updated_at: 2026-06-21T06:15:21.734239Z
---

# API-408 — Participant Observation And Retrieval Contracts

## Statement

The control-plane contract shall provide portable retrieval surfaces for participant status, derived context views, and histories.

## Rationale

Requirement inventory expansion. Participant execution must be observable through portable contracts, not only through backend-local inspection.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#76` (Participant backend-facing contracts (API-405…408, 411))
- DOCUMENTS → ADR `docs/decisions/adrs/adr-060-participant-backend-facing-contract-surface.md` (ADR-060 participant backend-facing contract surface)
- DOCUMENTS → SPEC `specs/formal/runtime-contracts/participant-backend-contracts.md` (Participant backend-facing contracts formal design (API-408 retrieval projections))
- DOCUMENTS → SPEC `contracts/schemas/control-plane/participant-status-view-v1.json` (Generated participant status view schema)
- DOCUMENTS → SPEC `contracts/schemas/control-plane/participant-history-view-v1.json` (Generated participant history view schema)
- DOCUMENTS → SPEC `contracts/schemas/control-plane/participant-context-view-v1.json` (Generated participant context view schema)
- TESTS → TEST `implementations/python/tests/test_participant_backend_contracts.py` (Participant retrieval-view fixture and schema tests)
- DOCUMENTS → PULL_REQUEST `Brad-Edwards/aces#515` (added: participant backend-facing contract surface and participant-semantics remediation)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#202` (Participant Observation And Retrieval Contracts (API-408))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/participant_retrieval.py` (Runtime participant retrieval projections)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane_api_participant_retrieval.py` (HTTP participant retrieval routes)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane.py` (Runtime control-plane participant retrieval mixin wiring)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane_api.py` (Control-plane API participant retrieval route registration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane_execution.py` (Participant-scoped operation status targets for retrieval views)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane.py` (Runtime participant retrieval projection tests)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane_api.py` (HTTP participant retrieval route tests)
