---
id: RUN-314
title: "Reference Emulation Backend"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T01:46:39.033909Z
updated_at: 2026-06-20T18:06:59.002481Z
---

# RUN-314 — Reference Emulation Backend

## Statement

The ecosystem shall provide a reference emulation backend that realizes scenarios against emulated infrastructure such as virtual machines, virtual networks, containers, or equivalent infrastructure surfaces while publishing manifest, conformance, and provenance data through the ecosystem's standard contracts.

## Rationale

The ecosystem needs at least one concrete infrastructure-backed backend so its portability claims are exercised against real realization surfaces rather than only abstract contracts, fixtures, or in-memory stand-ins.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#75` (Reference processor & backend implementations (RUN-313, RUN-314, RUN-315))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#197` (Reference Emulation Backend (RUN-314))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_backend/target.py` (Reference backend target + registry registration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_backend/provisioner.py` (Reference provisioner (driver-backed realization))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_backend/drivers/oci.py` (OCI deployment driver (real container realization))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_backend/manifest.py` (Reference backend manifest (backend-manifest-v2))
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-063-reference-emulation-backend.md` (ADR-063 Reference Emulation Backend)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_backend/orchestrator.py` (Reference orchestrator)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_backend/evaluator.py` (Reference evaluator)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_backend/participant_runtime.py` (Reference participant runtime (RUN-311 lifecycle))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_backend/realization.py` (Provisioning-plan interpretation)
- TESTS → TEST `implementations/python/tests/test_reference_backend_conformance.py` (Full-profile conformance + stub parity)
- TESTS → TEST `implementations/python/tests/test_reference_backend_provenance.py` (SEM-218 realization provenance)
- TESTS → TEST `implementations/python/tests/test_reference_backend_oci_driver.py` (OCI driver security + realization)
- TESTS → TEST `implementations/python/tests/test_reference_backend_registry.py` (Target shape/contract + registry registration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/participant_runtime_base.py` (BaseParticipantRuntime — shared RUN-311 episode lifecycle (extracted from the reference backend; reused by reference/stub/libvirt runtimes))
