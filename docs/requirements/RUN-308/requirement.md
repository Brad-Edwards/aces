---
id: RUN-308
title: "Concurrent Participant Execution"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:15:47.508932Z
updated_at: 2026-06-20T18:23:28.229464Z
---

# RUN-308 — Concurrent Participant Execution

## Statement

The runtime shall support concurrent participant execution and interaction over shared scenario state.

## Rationale

Requirement inventory expansion. Multi-participant experiments require runtime support for concurrent behavior over shared state.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#74` (Participant runtime: state/history, lifecycle, shared state, concurrency (RUN-305…308))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#195` (Concurrent Participant Execution (RUN-308))
- DOCUMENTS → GITHUB_ISSUE `74` (Participant runtime: state/history, lifecycle, shared state, concurrency (RUN-305-308))
- DOCUMENTS → PULL_REQUEST `414` (PR #414: docs: add participant runtime design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-054-participant-runtime-observable-lifecycle.md` (ADR-054: Participant Runtime Observable Lifecycle)
- DOCUMENTS → SPEC `specs/formal/participant-runtime/README.md` (Participant Runtime Formal Design)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (ACES contracts concurrency models and Pydantic validators)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/participant_concurrency.py` (Participant concurrency semantic validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/participant_concurrency_time.py` (Participant concurrency time-management semantic validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/runtime_state.py` (Runtime snapshot participant concurrency state)
- IMPLEMENTS → SPEC `contracts/schemas/participant-runtime/participant-joint-action-record-v1.json` (Participant joint-action record schema v1)
- IMPLEMENTS → SPEC `contracts/schemas/participant-runtime/participant-time-management-context-v1.json` (Participant time-management context schema v1)
- TESTS → TEST `implementations/python/tests/test_run_308_concurrent_participant_execution.py` (RUN-308 concurrent participant execution contract tests)
- TESTS → TEST `implementations/python/tests/test_participant_backend_contracts.py` (Participant backend runtime contract regression tests)
