---
id: ASR-519
title: "Realization Honesty And Disclosure Conformance"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 3
created_at: 2026-04-05T00:55:45.357920Z
updated_at: 2026-06-15T02:32:29.792706Z
---

# ASR-519 — Realization Honesty And Disclosure Conformance

## Statement

The ecosystem shall provide validation and conformance artifacts that detect silent relaxation of binding declarations and missing disclosure of processor or backend realizations for underspecified concerns.

## Rationale

Current state: identified gap. Honest portability needs executable checks against silent approximation and undisclosed gap-filling, not just documentation.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#100` (Realization honesty & disclosure conformance (ASR-519))
- DOCUMENTS → CODE_FILE `implementations/python/packages/aces_processor/semantics/realization.py` (First ASR-519 conformance artifact: planner gate detecting silent relaxation of exact bindings)
- DOCUMENTS → GITHUB_ISSUE `490` (Issue #490 contributes the first ASR-519 conformance artifact (planner realization-support gate))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/semantics/realization.py` (Runtime non-approximation gate (realization_disclosure))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/runtime_state.py` (RealizationProvenanceEntry disclosure contract (I5))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/backend_calls.py` (Gate invocation at the runtime adapter boundary)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Published RealizationProvenanceEntryModel on runtime-snapshot envelope)
- TESTS → TEST `implementations/python/tests/test_sem_218_runtime_realization.py` (SEM-218 runtime gate + provenance tests)
- IMPLEMENTS → GITHUB_ISSUE `491` (SEM-218 realization enforcement 3/3 (issue #491))
- DOCUMENTS → GITHUB_ISSUE `715` (03: Add guest-observed libvirt realization probes (ASR-519))
- DOCUMENTS → GITHUB_ISSUE `717` (05: Certify the libvirt reference scenario with honest evidence (ASR-519))
- IMPLEMENTS → GITHUB_ISSUE `100` (01: Publish configuration-specific libvirt realization envelopes (ASR-519))
- IMPLEMENTS → SPEC `contracts/schemas/realization-envelope/realization-envelope-v1.json` (Published realization-envelope-v1 schema)
- IMPLEMENTS → CONFIG `contracts/realization-envelopes/libvirt-qemu/generic-v1.json` (Generic libvirt realization envelope)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-070-realization-envelope-semantics.md` (ADR-070 realization-envelope semantics)
- IMPLEMENTS → CONFIG `contracts/realization-envelopes/libvirt-qemu/techvault-appliance-v1.json` (TechVault appliance realization envelope)
- IMPLEMENTS → SPEC `specs/formal/realization/envelope-semantics.md` (Formal realization-envelope semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/envelopes.py` (Configuration-specific libvirt envelope loader)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/manifest.py` (Envelope-derived libvirt capability manifest)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/provisioner.py` (Fail-closed libvirt envelope enforcement)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/target.py` (Driver-mode and envelope target binding)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/backend_manifest.py` (Backend manifest realization-envelope contract)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/manifest.py` (Backend realization-envelope manifest rendering)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/guest_appliance.py` (Guest-observing initramfs appliance builder)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/realization_envelope.py` (Realization-envelope expression and membership contract)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/realization_envelope_carrier.py` (Configuration identity and concern-disclosure carrier)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/planning.py` (Provisioning-plan realization-envelope identity carrier)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane_api_models.py` (Control-plane envelope identity disclosure)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/control_plane_store.py` (Runtime snapshot envelope identity persistence)
- IMPLEMENTS → SPEC `specs/authority/authority-boundary.yaml` (Realization-envelope normative authority registration)
- TESTS → TEST `implementations/python/tests/test_realization_envelope_contract.py` (Realization-envelope schema and semantic invariant tests)
- TESTS → TEST `implementations/python/tests/test_libvirt_backend_envelopes.py` (Libvirt envelope disclosure and capability-boundary tests)
- TESTS → TEST `implementations/python/tests/test_libvirt_backend_provisioner.py` (Fail-closed libvirt envelope enforcement tests)
- TESTS → TEST `implementations/python/tests/test_libvirt_backend_manifest_publication.py` (Published libvirt manifest envelope tests)
- TESTS → TEST `implementations/python/tests/test_libvirt_backend_manifest.py` (Configuration-specific libvirt manifest tests)
- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (Runtime conformance envelope preservation tests)
- TESTS → TEST `implementations/python/tests/test_backend_manifest.py` (Backend envelope contract validation tests)
- TESTS → TEST `implementations/python/tests/test_authority_boundary.py` (Realization-envelope authority-boundary tests)
- IMPLEMENTS → CODE_FILE `examples/scenarios/techvault-bounded-native.sdl.yaml` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/driver.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/realization.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/techvault_concerns.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/techvault_appliance.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/techvault_observation.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/techvault_lifecycle.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/techvault_matrix.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_operations/_evidence_run_artifact.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/techvault_probe.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_cli/libvirt.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_operations/_evidence_run_types.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_operations/_techvault_cleanup.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_operations/_evidence_run_validation.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_operations/libvirt_evidence_run.py` (ASR-519 implementation artifact)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_operations/run_artifacts.py` (ASR-519 implementation artifact)
- TESTS → TEST `implementations/python/tests/test_libvirt_backend_cli.py` (ASR-519 conformance test)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_operations/techvault_live.py` (ASR-519 implementation artifact)
- TESTS → TEST `implementations/python/tests/test_libvirt_backend_techvault_honesty.py` (ASR-519 conformance test)
- TESTS → TEST `implementations/python/tests/test_libvirt_backend_techvault_real_libvirt.py` (ASR-519 conformance test)
- TESTS → TEST `implementations/python/tests/test_libvirt_backend_techvault_native.py` (ASR-519 conformance test)
- IMPLEMENTS → GITHUB_ISSUE `714` (02: Enforce honest TechVault appliance realization disclosure (ASR-519))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/guest_observation.py` (Guest-observation staging, GUEST_OBSERVED facts, and gate)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/guest_certified_driver.py` (Guest-certified libvirt driver (commit-eligibility gate))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_libvirt/guest_transport.py` (Credential-free guest fact transport + bounded parser)
- IMPLEMENTS → SPEC `contracts/realization-envelopes/libvirt-qemu/guest-certified-appliance-v1.json` (Guest-certified realization envelope (guest-observed disclosures))
- TESTS → TEST `implementations/python/tests/test_libvirt_backend_guest_certified.py` (Hermetic guest-observation orchestration + falsification + evidence tests)
- TESTS → TEST `implementations/python/tests/test_libvirt_backend_guest_certified_real_libvirt.py` (Opt-in real-daemon guest-certification (native-proof gate))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_reference_backend/manifest.py` (Fail-closed reference backend domain and SPN capability disclosure)
- TESTS → TEST `implementations/python/tests/test_authored_domain_topology.py` (Planner rejection of unrealized domain topology and SPN requests)
- TESTS → TEST `implementations/python/tests/test_reference_backend_manifest.py` (Reference manifest capability-honesty regression test)
- IMPLEMENTS → GITHUB_ISSUE `776` (Issue #776: correct unrealized domain and SPN capability claims)
- IMPLEMENTS → GITHUB_ISSUE `716` (04: Add ASR-519 realization honesty conformance (ASR-519))
- IMPLEMENTS → DOCUMENTATION `docs/decisions/issue-716-asr-519-realization-honesty-conformance-preflight.md` (ASR-519 realization honesty conformance design)
- IMPLEMENTS → DOCUMENTATION `docs/conformance/libvirt-qemu.provisioning-only.report.json` (ASR-519 machine-readable libvirt conformance report)
- IMPLEMENTS → DOCUMENTATION `docs/explain/reference/backend-conformance.md` (ASR-519 backend conformance contract)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/_realization_models.py` (ASR-519 realization conformance evidence models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/_realization_validation.py` (ASR-519 realization evidence validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/realization.py` (ASR-519 realization honesty conformance engine)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/realization_observation.py` (ASR-519 neutral realization observation contract)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_operations/realization_conformance.py` (ASR-519 realization conformance harness)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_realization_envelope_probe_payloads.py` (ASR-519 safe envelope probe payload generation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_cli/conformance.py` (ASR-519 conformance report CLI projection)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (ASR-519 backend conformance orchestration and reporting)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_realization_envelope_domains.py` (ASR-519 envelope domain falsification support)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/realization_envelope.py` (ASR-519 deterministic realization envelope probes)
- TESTS → TEST `implementations/python/tests/test_realization_honesty_conformance.py` (ASR-519 dishonest-backend conformance tests)
- TESTS → TEST `implementations/python/tests/test_libvirt_conformance.py` (ASR-519 libvirt conformance mode tests)
- TESTS → TEST `implementations/python/tests/test_libvirt_participant_runtime.py` (ASR-519 libvirt realization observation tests)
- TESTS → TEST `implementations/python/tests/test_realization_envelope_relation.py` (ASR-519 envelope probe relation tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/planner/__init__.py` (Envelope membership and plan identity enforcement)
