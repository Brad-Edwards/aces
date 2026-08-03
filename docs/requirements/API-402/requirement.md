---
id: API-402
title: "Plain-Data Execution, Result, And History Contracts"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:40:04.988670Z
updated_at: 2026-04-05T03:06:54.035699Z
---

# API-402 — Plain-Data Execution, Result, And History Contracts

## Statement

The ecosystem shall define plain-data contracts for submission, live execution state, results, and history that are independent of implementation language and distinct from archival run provenance artifacts.

## Rationale

Current state: implemented. Portable live-execution contracts are required so independent implementations can interoperate without sharing internal object models or conflating operational state with experiment records.

## Traceability

- CONSTRAINS → SPEC `specs/formal/runtime-contracts/README.md` (Runtime Contracts Overview)
- CONSTRAINS → SPEC `specs/formal/runtime-contracts/workflow-results.md` (Workflow Result Contracts)
- CONSTRAINS → SPEC `specs/formal/runtime-contracts/evaluator-results.md` (Evaluator Result Contracts)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Runtime Contract Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_manager.py` (Runtime Manager Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane_api.py` (Runtime Control Plane API Tests)
- DOCUMENTS → DOCUMENTATION `contracts/README.md` (Contracts Overview)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (SDL Runtime Architecture)
- CONSTRAINS → SPEC `contracts/schemas/control-plane/workflow-result-envelope-v1.json` (Workflow Result Envelope Schema)
- CONSTRAINS → SPEC `contracts/schemas/control-plane/evaluation-result-envelope-v1.json` (Evaluation Result Envelope Schema)
- CONSTRAINS → SPEC `contracts/schemas/control-plane/workflow-history-event-stream-v1.json` (Workflow History Event Stream Schema)
- CONSTRAINS → SPEC `contracts/schemas/control-plane/evaluation-history-event-stream-v1.json` (Evaluation History Event Stream Schema)
- CONSTRAINS → SPEC `contracts/schemas/snapshots/runtime-snapshot-v1.json` (Runtime Snapshot Schema)
