---
id: RUN-316
title: "Operational Apparatus Observability"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T01:59:50.614372Z
updated_at: 2026-06-28T18:07:50.939592Z
---

# RUN-316 — Operational Apparatus Observability

## Statement

The processing layer shall support operational observability surfaces for processors and backends needed to realize, monitor, verify, and troubleshoot scenarios and experiments, distinct from scenario-native observability systems and captured experiment evidence.

## Rationale

Processors and backends require their own operational observability, but that concern must remain distinct from both in-world observability and the evidence captured for analysis.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#128` (Operational apparatus observability; observation-augmentation disclosure contracts; observability-plane/augmentation conformance; evidence-requirement refinement & realized-evidence provenance (RUN-316, API-419, ASR-525, EXP-731, 732))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#338` (Operational Apparatus Observability (RUN-316))
- DOCUMENTS → GITHUB_ISSUE `347` (Issue #347 — Multi-Organizational Authority And Governance Contracts)
- IMPLEMENTS → GITHUB_ISSUE `128` (Issue #128 - Observability evidence conformance implementation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/capabilities.py` (Observation capability required contracts include experiment-run-v1)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_backend/manifest.py` (Reference backend declares experiment-run-v1 evidence support)
- TESTS → TEST `implementations/python/tests/test_backend_manifest.py` (Backend manifest tests cover observation contract vocabulary and experiment-run-v1 support)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/operational_apparatus.py` (Operational apparatus summary derivation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane.py` (Runtime control-plane operational apparatus summary entrypoint)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane_api.py` (GET /apparatus/operational-summary control-plane API route)
- TESTS → TEST `implementations/python/tests/test_runtime_control_plane_api.py` (Operational apparatus summary API tests)
- IMPLEMENTS → GITHUB_ISSUE `338` (Operational Apparatus Observability (RUN-316))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_stubs/manifest.py` (Stub backend declares experiment-run-v1 evidence support when observation is enabled)
