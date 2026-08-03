---
id: API-409
title: "Participant External Input And Intervention Contracts"
status: ACTIVE
type: INTERFACE
priority: SHOULD
wave: 3
created_at: 2026-04-03T06:16:04.587331Z
updated_at: 2026-07-25T16:22:35.566014Z
---

# API-409 — Participant External Input And Intervention Contracts

## Statement

The ecosystem shall define portable plain-data contracts for external action proposals, approvals or denials, directions, interventions, handoffs, overrides, and cancellations where mixed-control participant modes are supported, preserving controller and authority identity, order, policy revision, provenance, evidence, and explicit disposition.

## Rationale

Issue #794 found that mixed-control input needs more than an undifferentiated external-input envelope: approval, direction, intervention, handoff, override, cancellation, admission, and execution are separate facts.

## Traceability

- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/contracts/participant_flow_control_incumbent_validation.py` (API-409 flow-control incumbent carrier joins)
- TESTS → TEST `implementations/python/tests/test_sem_233_flow_control_contracts.py` (API-409 flow-control incumbent join tests)
- IMPLEMENTS → GITHUB_ISSUE `1002` (Issue #1002 portable flow-control contracts)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#94` (Participant intervention & shared-state contracts (API-409, 410))
- DOCUMENTS → GITHUB_ISSUE `794` (Assess and design formal participant I/O control with information-flow and bisimulation semantics)
- DOCUMENTS → DOCUMENTATION `docs/research/participant-io-control/requirement-disposition.md` (Issue #794 participant information-flow/control requirement disposition)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#252` (Participant External Input And Intervention Contracts (API-409))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts/participant_control.py` (API-409 participant control occurrence contract models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts/participant_control_validation.py` (API-409 participant control occurrence semantic validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts/__init__.py` (API-409 public contract exports)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts/bundle.py` (API-409 schema bundle registration)
- IMPLEMENTS → CODE_FILE `tools/generate_contract_schemas.py` (API-409 published schema generation routing)
- IMPLEMENTS → CONFIG `contracts/schema-publication/entries/participant-control-occurrence-v1.json` (API-409 schema publication entry)
- IMPLEMENTS → SPEC `contracts/schemas/participant-runtime/participant-control-occurrence-v1.json` (API-409 participant control occurrence v1 schema)
- TESTS → TEST `implementations/python/tests/test_api_409_participant_control_occurrences.py` (API-409 contract, schema, and fail-closed validation tests)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-252-api-409-participant-intervention-contracts-preflight.md` (API-409 architecture preflight)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/lineage.md` (API-409 participant-control lineage and nonclaims)
