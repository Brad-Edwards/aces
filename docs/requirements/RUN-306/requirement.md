---
id: RUN-306
title: "Participant Decision And Execution Lifecycle"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:15:47.291760Z
updated_at: 2026-06-06T18:13:21.822388Z
---

# RUN-306 — Participant Decision And Execution Lifecycle

## Statement

The runtime shall define a portable lifecycle for participant action proposal, selection, execution, observation, and state update.

## Rationale

Requirement inventory expansion. Participant execution needs a normative lifecycle rather than ad hoc backend-local loops.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#74` (Participant runtime: state/history, lifecycle, shared state, concurrency (RUN-305…308))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#193` (Participant Decision And Execution Lifecycle (RUN-306))
- DOCUMENTS → GITHUB_ISSUE `74` (Participant runtime: state/history, lifecycle, shared state, concurrency (RUN-305-308))
- DOCUMENTS → PULL_REQUEST `414` (PR #414: docs: add participant runtime design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-054-participant-runtime-observable-lifecycle.md` (ADR-054: Participant Runtime Observable Lifecycle)
- DOCUMENTS → SPEC `specs/formal/participant-runtime/README.md` (Participant Runtime Formal Design)
- IMPLEMENTS → GITHUB_ISSUE `193` (Participant Decision And Execution Lifecycle (RUN-306))
- IMPLEMENTS → PULL_REQUEST `474` (PR #474: added: participant runtime lifecycle contracts)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/participant_behavior.py` (Participant behavior lifecycle vocabulary and validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Participant behavior history event contract model)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (Processor participant behavior history lifecycle payload model)
- IMPLEMENTS → SPEC `contracts/schemas/snapshots/runtime-snapshot-v1.json` (Runtime snapshot schema lifecycle fields)
- IMPLEMENTS → SPEC `contracts/schemas/control-plane/participant-behavior-history-event-stream-v1.json` (Participant behavior history event stream schema lifecycle fields)
- TESTS → TEST `implementations/python/tests/test_run_306_participant_decision_lifecycle.py` (RUN-306 participant decision lifecycle tests)
