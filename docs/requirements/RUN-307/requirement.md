---
id: RUN-307
title: "Shared Operational State Model"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:15:47.404051Z
updated_at: 2026-06-20T05:57:33.819954Z
---

# RUN-307 — Shared Operational State Model

## Statement

The runtime shall provide a portable shared operational state model for evolving participant and environment state.

## Rationale

Requirement inventory expansion. Participant behavior depends on shared evolving state that cannot be left implicit.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#74` (Participant runtime: state/history, lifecycle, shared state, concurrency (RUN-305…308))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#194` (Shared Operational State Model (RUN-307))
- DOCUMENTS → GITHUB_ISSUE `74` (Participant runtime: state/history, lifecycle, shared state, concurrency (RUN-305-308))
- DOCUMENTS → PULL_REQUEST `414` (PR #414: docs: add participant runtime design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-054-participant-runtime-observable-lifecycle.md` (ADR-054: Participant Runtime Observable Lifecycle)
- DOCUMENTS → SPEC `specs/formal/participant-runtime/README.md` (Participant Runtime Formal Design)
- IMPLEMENTS → PULL_REQUEST `562` (PR #562: feat(runtime): add shared operational state snapshots)
- IMPLEMENTS → GITHUB_ISSUE `194` (Issue #194: Shared Operational State Model (RUN-307))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/runtime_state.py` (Runtime snapshot shared-state record/history fields)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Runtime snapshot envelope and participant shared-state model validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/participant_shared_state.py` (RUN-307 shared operational state semantic validators)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/_participant_behavior_types.py` (Reserved runtime-state key guard for shared-state smuggling)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/participant_result_contracts.py` (Runtime apply diagnostics for shared-state snapshots and append-only history)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane_api_models.py` (Control-plane snapshot API shared-state serialization)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane_store.py` (Control-plane snapshot persistence for shared-state records/history)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (Conformance preservation and semantic diagnostics for shared-state snapshots)
- IMPLEMENTS → SPEC `contracts/schemas/snapshots/runtime-snapshot-v1.json` (Runtime snapshot schema with first-class shared-state fields)
- IMPLEMENTS → SPEC `contracts/schemas/participant-runtime/participant-shared-state-record-v1.json` (Participant shared-state record schema with revision/digest discipline)
- IMPLEMENTS → CONFIG `contracts/schema-publication-manifest.json` (Schema publication manifest entries for RUN-307 shared-state schemas)
- TESTS → TEST `implementations/python/tests/test_run_307_shared_operational_state.py` (RUN-307 shared operational state regression tests)
