---
id: API-406
title: "Backend-Facing Participant Plain-Data Contracts"
status: ACTIVE
type: INTERFACE
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:16:04.201040Z
updated_at: 2026-06-20T23:30:29.358323Z
---

# API-406 — Backend-Facing Participant Plain-Data Contracts

## Statement

The ecosystem shall define backend-facing plain-data contracts for serializing participant actions, observations, state snapshots, histories, and state-change reports.

## Rationale

Requirement inventory expansion. Participant behavior requires portable external contracts rather than backend-local object models.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#76` (Participant backend-facing contracts (API-405…408, 411))
- DOCUMENTS → SPEC `contracts/schemas/participant-runtime/participant-lifecycle-event-v1.json` (Generated participant lifecycle event schema)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-060-participant-backend-facing-contract-surface.md` (ADR-060 participant backend-facing contract surface)
- DOCUMENTS → SPEC `specs/formal/runtime-contracts/participant-backend-contracts.md` (Participant backend-facing contracts formal design (API-406 carriers))
- DOCUMENTS → SPEC `contracts/schemas/participant-runtime/participant-observation-envelope-v1.json` (Generated participant observation envelope schema)
- DOCUMENTS → SPEC `contracts/schemas/participant-runtime/participant-shared-state-record-v1.json` (Generated participant shared-state record schema)
- TESTS → TEST `implementations/python/tests/test_participant_backend_contracts.py` (Participant backend-contract carrier fixture and schema tests)
- DOCUMENTS → PULL_REQUEST `Brad-Edwards/aces#515` (added: participant backend-facing contract surface and participant-semantics remediation)
- IMPLEMENTS → CONFIG `contracts/profiles/backend/full-remote-control-plane.json` (Full remote control-plane backend profile API-406 carrier requirements)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (API-406 carrier contract conformance validators)
- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (API-406 carrier profile and fixture-suite conformance tests)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#568` (feat: register API-406 backend carrier contracts)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#200` (Backend-Facing Participant Plain-Data Contracts (API-406))
