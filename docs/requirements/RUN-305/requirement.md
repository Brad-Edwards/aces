---
id: RUN-305
title: "Participant Runtime State And History"
status: DRAFT
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:15:47.109300Z
updated_at: 2026-04-03T06:15:47.109300Z
---

# RUN-305 — Participant Runtime State And History

## Statement

The runtime shall expose portable state and history for participants, including actions, observations, state changes, and outcomes.

## Rationale

Requirement inventory expansion. Participant behavior requires observable runtime state and history independent of backend internals.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#74` (Participant runtime: state/history, lifecycle, shared state, concurrency (RUN-305…308))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#192` (Participant Runtime State And History (RUN-305))
- DOCUMENTS → GITHUB_ISSUE `74` (Participant runtime: state/history, lifecycle, shared state, concurrency (RUN-305-308))
- DOCUMENTS → PULL_REQUEST `414` (PR #414: docs: add participant runtime design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-054-participant-runtime-observable-lifecycle.md` (ADR-054: Participant Runtime Observable Lifecycle)
- DOCUMENTS → SPEC `specs/formal/participant-runtime/README.md` (Participant Runtime Formal Design)
- TESTS → TEST `implementations/python/tests/test_run_305_participant_runtime_state_history.py` (RUN-305 participant runtime state/history regression tests)
- DOCUMENTS → CODE_FILE `implementations/python/packages/aces_contracts/participant_behavior.py` (RUN-305 participant behavior-history snapshot validator)
- DOCUMENTS → CODE_FILE `implementations/python/packages/aces_runtime/participant_result_contracts.py` (RUN-305 participant runtime state contract diagnostics)
- DOCUMENTS → CODE_FILE `implementations/python/packages/aces_runtime/backend_calls.py` (RUN-305 backend apply contract gate wiring)
- DOCUMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane_api_models.py` (RUN-305 HTTP runtime snapshot behavior-history parity)
- DOCUMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (RUN-305 published participant behavior-history schema model)
- DOCUMENTS → CODE_FILE `implementations/python/packages/aces_runtime/result_contracts.py` (RUN-305 participant runtime diagnostics export surface)
- DOCUMENTS → PULL_REQUEST `467` (PR #467: Implement RUN-305 participant runtime history)
