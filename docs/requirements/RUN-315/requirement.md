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

- IMPLEMENTS → CONFIG `implementations/python/pyproject.toml` (Python package registration for the reference simulation backend)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/reference-simulation-backend.md` (Reference simulation backend operator documentation)
- TESTS → TEST `implementations/python/tests/test_reference_simulation_backend_conformance.py` (Reference simulation backend conformance tests)
- TESTS → TEST `implementations/python/tests/test_reference_simulation_backend_manifest.py` (Reference simulation backend manifest tests)
- TESTS → TEST `implementations/python/tests/test_reference_simulation_backend_provenance.py` (Reference simulation provenance tests)
- TESTS → TEST `implementations/python/tests/test_reference_simulation_backend_provisioner.py` (Reference simulation provisioner tests)
- TESTS → TEST `implementations/python/tests/test_reference_simulation_backend_realization.py` (Reference simulation realization tests)
- TESTS → TEST `implementations/python/tests/test_reference_simulation_backend_registry.py` (Reference simulation backend registry tests)
