---
id: RUN-314
title: "Reference Emulation Backend"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T01:46:39.033909Z
updated_at: 2026-08-11T00:00:00Z
---

# RUN-314 — Reference Emulation Backend

## Statement

The ecosystem shall provide a reference emulation backend that realizes scenarios against emulated infrastructure such as virtual machines, virtual networks, containers, or equivalent infrastructure surfaces while publishing manifest, conformance, and provenance data through the ecosystem's standard contracts.

## Rationale

The ecosystem needs at least one concrete infrastructure-backed backend so its portability claims are exercised against real realization surfaces rather than only abstract contracts, fixtures, or in-memory stand-ins.

## Traceability

- IMPLEMENTS → ADR `docs/decisions/adrs/adr-063-reference-emulation-backend.md` (ADR-063 Reference Emulation Backend)
- TESTS → TEST `implementations/python/tests/test_reference_backend_conformance.py` (Full-profile conformance + stub parity)
- TESTS → TEST `implementations/python/tests/test_reference_backend_provenance.py` (SEM-218 realization provenance)
- TESTS → TEST `implementations/python/tests/test_reference_backend_oci_driver.py` (OCI driver security + realization)
- TESTS → TEST `implementations/python/tests/test_reference_backend_docker_integration.py` (Real Docker/Podman realization and full-profile conformance)
- TESTS → TEST `implementations/python/tests/test_reference_backend_docker_gate.py` (Optional versus release-required runtime/image admission)
- TESTS → TEST `implementations/python/tests/test_reference_backend_registry.py` (Target shape/contract + registry registration)
- DOCUMENTS → GITHUB_ISSUE `197` (RUN-314 reference-emulation backend root)
- IMPLEMENTS → GITHUB_ISSUE `1094` (Deterministic and cache-safe libvirt boot artifacts)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_backend_libvirt/_initramfs.py` (Repository-owned newc, toolchain preflight, and atomic artifact helpers)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_backend_libvirt/techvault_appliance.py` (Deterministic TechVault appliance and digest kernel cache)
- IMPLEMENTS → DOCUMENTATION `docs/decisions/issue-1094-libvirt-boot-artifact-reliability.md` (Boot-artifact reliability architecture)
- TESTS → TEST `implementations/python/tests/test_libvirt_boot_artifacts.py` (Determinism, preflight, newc, and atomic cache regressions)
- DOCUMENTS → GITHUB_ISSUE `1105` (Guest-certified service protocol binding)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-1105-libvirt-guest-service-protocol.md` (TCP-only admission and evidence decision)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_backend_libvirt/techvault_concerns.py` (Fail-closed service protocol admission)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_backend_libvirt/guest_appliance.py` (Protocol-bound guest listener and facts)
- TESTS → TEST `implementations/python/tests/test_libvirt_backend_guest_certified.py` (Service protocol certification regressions)
- IMPLEMENTS → GITHUB_ISSUE `1110` (Exact-SHA real-container release admission)
- IMPLEMENTS → CODE_FILE `.github/workflows/release-please.yml` (Required release-only Docker integration before artifact build)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-1110-required-container-release-gate.md` (Release evidence architecture and limitations)
