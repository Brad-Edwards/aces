---
id: RUN-311
title: "Participant Episode Lifecycle And Reset"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T01:39:33.701478Z
updated_at: 2026-04-12T06:35:41.845947Z
---

# RUN-311 — Participant Episode Lifecycle And Reset

## Statement

The runtime shall support episodic participant execution with explicit initialization, reset, completion, timeout, truncation, interruption, and restart handling.

## Rationale

Primary-source refresh shows that participant-supporting runtimes commonly depend on explicit episode lifecycle and reset handling rather than one long-lived undifferentiated run loop.

## Traceability

- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (Participant episode runtime models (enums + frozen dataclasses))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Participant episode contract models and schema bundle entries)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/versions.py` (participant-episode-state/v1 schema version constant)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-013-participant-episode-lifecycle-boundaries.md` (ADR-013 Participant Episode Lifecycle Boundaries)
- TESTS → TEST `implementations/python/tests/test_run_311_participant_episode_lifecycle.py` (RUN-311 participant episode lifecycle integrity tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/control_plane_api.py` (Control plane snapshot serializer wiring for participant episode surface)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/control_plane_store.py` (Durable snapshot persistence for participant episode surface)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (Conformance snapshot converter wiring for participant episode surface)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/manifest_authority.py` (Backend/processor manifest authority registration for participant-episode contract ids)
- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (Conformance fixture suite and semantic diagnostics coverage for RUN-311)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/manager.py` (Runtime manager apply-path validation for participant episode snapshot data)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/protocols.py` (ParticipantRuntime backend protocol for RUN-311)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/capabilities.py` (ParticipantRuntimeCapabilities + has_participant_runtime manifest declaration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/manifest.py` (backend_manifest_v2_model serialization of participant_runtime capability)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_stubs/stubs.py` (StubParticipantRuntime reference implementation for RUN-311)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/control_plane.py` (RuntimeControlPlane participant episode initialize/reset/restart/terminate methods)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/registry.py` (RuntimeTarget participant_runtime field and shape validation)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane.py` (TestParticipantEpisodeControlPlane lifecycle and rejection paths)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane_api.py` (TestParticipantEpisodeHttpRoutes HTTP surface coverage)
- TESTS → TEST `implementations/python/tests/test_runtime_manager.py` (Manager apply path coverage extended for participant runtime kwarg)
- TESTS → TEST `implementations/python/tests/test_runtime_registry.py` (Registry shape validation for participant_runtime field)
- IMPLEMENTS → GITHUB_ISSUE `599` (Issue 599 participant implementation action admission binding)
- IMPLEMENTS → PULL_REQUEST `617` (PR 617 participant implementation action admission binding)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/participant_binding.py` (Participant action admission request and binding evidence validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/participant_control.py` (Runtime control-plane participant action admission path)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_backend/participant_runtime.py` (Reference participant runtime action admission behavior history append)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane.py` (RuntimeControlPlane participant control mixin integration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/registry.py` (Participant runtime admit_action shape validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/participant_runtime_base.py` (BaseParticipantRuntime.admit_action — shared action admission with behavior-history append (extracted from reference/stub runtimes))
