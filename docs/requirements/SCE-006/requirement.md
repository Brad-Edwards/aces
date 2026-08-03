---
id: SCE-006
title: "Isolated Batch Trial Scheduling"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-07-15T03:17:25.961655Z
updated_at: 2026-07-30T14:48:41.795604Z
---

# SCE-006 — Isolated Batch Trial Scheduling

## Statement

APTL shall schedule trials from an admitted experiment plan over the existing ACES single-scenario execution path. Scheduling shall default to serial execution and support explicitly configured bounded parallelism only when independent range instances, host capacity, ports, storage, and control-plane locks can be proven isolated. Every trial shall receive a clean or declared reusable initial state, deterministic ordering and identity, bounded timeouts, and verified cleanup. The scheduler shall not implement a second scenario lifecycle or a private comparison/scoring engine.

## Rationale

Batch execution is the apparatus mechanism that turns an ACES run allocation into executions. Isolation and clean-state guarantees are more important than throughput because cross-trial contamination invalidates experimental evidence.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `785` (SCE-006 — Isolated Batch Trial Scheduling)
- DOCUMENTS → GITHUB_ISSUE `788` (SCE-002: publish the admitted experiment trial-plan contract)
- DOCUMENTS → GITHUB_ISSUE `790` (SCE-002: integrate trial realization with SDL instantiation and run provenance)
- DOCUMENTS → SPEC `contracts/schemas/plans/admitted-trial-plan-v1.json` (Admitted trial-plan contract the isolated-batch scheduler consumes (serial-default + isolation-proof, cleanup, timeouts))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/contracts/batch_execution.py` (SCE-006 batch execution receipt contract + plan-to-schedule isolation-proof and receipt validators)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/trial_scheduler.py` (SCE-006 deterministic batch scheduling policy (canonical order + sealed-plan admitted ceiling) over the one-entry realization seam)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_contracts/contracts/trial_coordinate_order.py` (SCE-006 single-owner canonical trial-coordinate dispatch order helper (SVR-014/SVR-031))
- IMPLEMENTS → SPEC `contracts/schemas/control-plane/batch-execution-receipt-v1.json` (SCE-006 published batch-execution-receipt-v1 contract (immutable per-attempt scheduling + cleanup evidence))
- TESTS → TEST `implementations/python/tests/test_sce_006_batch_scheduler.py` (SCE-006 batch scheduler tests: deterministic order, sealed-plan isolation authority, receipt validation, conformance corpus)
