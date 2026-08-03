---
id: RUN-304
title: "Live Execution State And Lifecycle"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:39:40.890839Z
updated_at: 2026-04-05T03:20:38.706731Z
---

# RUN-304 — Live Execution State And Lifecycle

## Statement

The processing layer shall expose portable plain-data forms for live execution state and lifecycle observation for scenarios, workflows, evaluations, and operations, distinct from archival run records and experiment provenance.

## Rationale

Current state: implemented. Portable live state is required so execution behavior can be inspected, validated, and implemented independently of any one implementation language while remaining distinct from experiment-record artifacts.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (SDL Runtime Architecture)
- CONSTRAINS → SPEC `specs/formal/runtime-contracts/README.md` (Runtime Contract Semantics)
- CONSTRAINS → SPEC `specs/formal/runtime-contracts/workflow-results.md` (Workflow Result Contract)
- CONSTRAINS → SPEC `specs/formal/runtime-contracts/evaluator-results.md` (Evaluator Result Contract)
- CONSTRAINS → SPEC `contracts/schemas/snapshots/runtime-snapshot-v1.json` (Runtime Snapshot Schema)
- CONSTRAINS → SPEC `contracts/schemas/control-plane/workflow-result-envelope-v1.json` (Workflow Result Envelope Schema)
- CONSTRAINS → SPEC `contracts/schemas/control-plane/evaluation-result-envelope-v1.json` (Evaluation Result Envelope Schema)
- CONSTRAINS → SPEC `contracts/schemas/control-plane/operation-status-v1.json` (Operation Status Schema)
- TESTS → TEST `implementations/python/tests/test_runtime_manager.py` (Runtime Manager Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane.py` (Runtime Control Plane Tests)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane_api.py` (Runtime Control Plane API Tests)
