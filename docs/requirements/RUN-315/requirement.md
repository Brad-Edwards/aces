---
id: RUN-315
title: "Reference Simulation Backend"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T01:46:38.922163Z
updated_at: 2026-06-21T00:48:51.731612Z
---

# RUN-315 — Reference Simulation Backend

## Statement

The ecosystem shall provide a reference simulation backend, including via an adapter over an existing simulator where appropriate, that realizes scenarios against modeled or simulated systems while publishing manifest, conformance, and provenance data through the ecosystem's standard contracts.

## Rationale

A simulation reference backend complements emulation by demonstrating portability across a materially different realization strategy with lower-cost, more controllable execution surfaces.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#75` (Reference processor & backend implementations (RUN-313, RUN-314, RUN-315))
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#198` (Reference Simulation Backend (RUN-315))
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#569` (added: reference simulation backend)
- IMPLEMENTS → CONFIG `implementations/python/pyproject.toml` (Python package registration for the reference simulation backend)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/reference-simulation-backend.md` (Reference simulation backend operator documentation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_simulation_backend/__init__.py` (Reference simulation backend public package surface)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_simulation_backend/engine.py` (Hermetic in-process simulation engine boundary)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_simulation_backend/manifest.py` (Reference simulation backend manifest)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_simulation_backend/target.py` (Reference simulation runtime target and registry registration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_simulation_backend/realization.py` (Provisioning-plan to simulation-spec realization interpreter)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_simulation_backend/provisioner.py` (Reference simulation provisioner and runtime snapshot provenance)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_simulation_backend/orchestrator.py` (Reference simulation orchestration role)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_simulation_backend/evaluator.py` (Reference simulation evaluator role)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_simulation_backend/participant_runtime.py` (Reference simulation participant runtime role)
- TESTS → TEST `implementations/python/tests/test_reference_simulation_backend_conformance.py` (Reference simulation backend conformance tests)
- TESTS → TEST `implementations/python/tests/test_reference_simulation_backend_manifest.py` (Reference simulation backend manifest tests)
- TESTS → TEST `implementations/python/tests/test_reference_simulation_backend_provenance.py` (Reference simulation provenance tests)
- TESTS → TEST `implementations/python/tests/test_reference_simulation_backend_provisioner.py` (Reference simulation provisioner tests)
- TESTS → TEST `implementations/python/tests/test_reference_simulation_backend_realization.py` (Reference simulation realization tests)
- TESTS → TEST `implementations/python/tests/test_reference_simulation_backend_registry.py` (Reference simulation backend registry tests)
