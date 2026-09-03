---
id: REP-004
title: "CybORG simulation-backend conformant adapter"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 4
created_at: 2026-07-01T17:48:19.768767Z
updated_at: 2026-08-01T16:58:24.599823Z
---

# REP-004 — CybORG simulation-backend conformant adapter

## Statement

The adapters monorepo shall provide a CybORG simulation-backend adapter that conforms to the published RAES backend protocols (Provisioner, Orchestrator, Evaluator, ParticipantRuntime). The adapter shall translate RAES provisioning, orchestration, and evaluation plans and the participant-episode lifecycle (initialize/reset/restart/terminate, preserving episode identity, sequence numbers, and previous-episode links) to and from CybORG's scenario, action, and observation model, surfacing only portable RAES references in snapshots and diagnostics. The adapter shall pass the backend conformance suite and be the first package in the adapters monorepo, built on the shared sim-adapter base.

## Rationale

The conformant wrapper that makes an external simulator a drivable RAES backend; the reusable protocol skeleton is shared, the CybORG-specific translation is the substantive work.

## Traceability

- TESTS → TEST `tests/test_cyborg_execution.py` (CybORG execution and participant runtime tests)
- TESTS → TEST `tests/test_cyborg_provisioner.py` (CybORG provisioner and scenario translation tests)
- TESTS → TEST `tools/verify_cyborg_qualification.py` (CybORG native qualification reproducer)
- TESTS → TEST `tests/test_cyborg_smoke.py` (CybORG smoke tests)
- TESTS → TEST `tests/test_cyborg_qualification_driver.py` (CybORG qualification driver tests)
- TESTS → TEST `tests/test_cyborg_qualification.py` (CybORG qualification evidence tests)
- TESTS → TEST `tests/test_cyborg_source_ledger.py` (CybORG source-ledger tests)
- DOCUMENTS → GITHUB_ISSUE `638` (REP-004 — CybORG simulation-backend conformant adapter)
- DOCUMENTS → GITHUB_ISSUE `15` (feat(cyborg): implement the Provisioner and evidence-backed backend manifest)
- DOCUMENTS → PULL_REQUEST `59` (feat(cyborg): implement RAES scenario projection)
- DOCUMENTS → DOCUMENTATION `docs/decisions/cyborg-cage2-provisioner-manifest-guardrails.md` (CybORG Provisioner and manifest guardrails)
- IMPLEMENTS → GITHUB_ISSUE `17` (feat(cyborg): implement participant episodes and observation projection)
- IMPLEMENTS → PULL_REQUEST `62` (feat(cyborg): implement participant episode projection)
- IMPLEMENTS → CODE_FILE `src/raes_adapters/cyborg/participant_runtime.py` (CybORG participant runtime)
- IMPLEMENTS → CODE_FILE `src/raes_adapters/cyborg/driver.py` (CybORG native driver)
- IMPLEMENTS → CODE_FILE `src/raes_adapters/cyborg/scenario.py` (CybORG scenario translation)
- IMPLEMENTS → CODE_FILE `src/raes_adapters/cyborg/manifest.py` (CybORG backend manifest)
- IMPLEMENTS → CODE_FILE `src/raes_adapters/cyborg/provisioner.py` (CybORG provisioner)
- IMPLEMENTS → CODE_FILE `src/raes_adapters/cyborg/orchestrator.py` (CybORG orchestrator)
- IMPLEMENTS → CODE_FILE `src/raes_adapters/cyborg/target.py` (CybORG runtime target composition)
- DOCUMENTS → DOCUMENTATION `docs/decisions/cyborg-participant-runtime-guardrails.md` (CybORG participant runtime guardrails)
