# Issue 606 Libvirt Backend Conformance Preflight

Date: 2026-07-03

Issue: #606.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records architecture guardrails for making the libvirt backend pass
fixture-level and target-level backend conformance. It is guidance only: it
does not implement the conformance probe, change manifests, add schemas, or add
live-daemon behavior.

Correction for issue #663: this note's backend-neutral live provisioning probe
guardrail applies only when the selected probe scenario is within the target's
declared or supplied realization envelope. Backend conformance must not treat a
fixed hard-coded VM scenario as universal proof material for scenario-scoped,
fixed-topology, or simulation backends. See
`docs/decisions/issue-663-target-conformance-provisioning-scope-preflight.md`
for the contract-conformance versus scenario-realizability boundary.

## Binding Sources

- `docs/explain/reference/backend-conformance.md` owns the backend conformance
  architecture: published fixtures and profiles are the authority, and the
  runner lives in `aces_conformance`.
- `docs/decisions/issue-601-libvirt-provisioning-backend-preflight.md`,
  `issue-602-libvirt-backend-manifest-preflight.md`,
  `issue-603-libvirt-apply-realization-preflight.md`,
  `issue-604-libvirt-reconciliation-teardown-preflight.md`, and
  `issue-605-libvirt-envelope-diagnostics-preflight.md` define the libvirt
  provisioning-only, manifest, apply, reconciliation, and capability-envelope
  boundaries.
- `contracts/profiles/backend/provisioning-only.json` and
  `aces_contracts.backend_profiles` are the profile contract-set authority.
- `contracts/fixtures/**`, `schema_bundle()`, and the existing
  `ContractModel` validators are the fixture contract authority.
- `aces_conformance.conformance.run_fixture_suite()`,
  `run_target_conformance()`, `profile_for_manifest()`, and `_live_target_cases`
  are the incumbent conformance seams.
- `RuntimeControlPlane`, `_call_backend_apply()`, `OperationReceipt`,
  `OperationStatus`, `RuntimeSnapshotEnvelope`, and `Diagnostic` are the runtime
  probe and error-envelope authority.
- `create_libvirt_target()`, `create_libvirt_components()`,
  `create_libvirt_manifest()`, `LibvirtProvisioner`, `interpret_provisioning_plan()`,
  `LibvirtDriver`, and `DriverResult` are the libvirt seams the target probe
  must exercise.
- `aces_operations.run_artifacts` owns safe run-id validation and atomic JSON
  artifact writing for durable proof artifacts.

## Architecture Decisions

- Treat issue #606 as conformance closure, not a new backend feature. The
  implementation should make the existing libvirt target satisfy the existing
  published provisioning-only contract set and the existing runtime apply
  envelopes.
- Fixture-level acceptance remains `aces conformance backend --profile
  provisioning-only`; it must keep reading `contracts/profiles/backend` and
  `contracts/fixtures` through the existing corpus loaders. Do not add a
  libvirt-specific fixture runner, schema table, or profile map.
- Target-level acceptance belongs in `run_target_conformance()` as a
  backend-neutral provisioning live probe. A provisioning-only profile must not
  stop at `live-manifest`; it must submit a minimal provisioning plan through
  `RuntimeControlPlane.submit_provisioning()`, inspect the resulting
  `OperationStatus`, and validate the resulting `runtime-snapshot-v1` payload.
- The live provisioning probe must assert observable mutation, not just a valid
  manifest or accepted receipt. Passing evidence should include a succeeded
  provisioning operation, non-empty `changed_addresses`, at least one
  provisioning `SnapshotEntry`, and snapshot contract/semantic validation. A
  success-returning no-op provisioner must fail conformance.
- The probe must remain backend-neutral and profile-driven. Libvirt-specific
  tests may construct the libvirt target with an injected recording driver, but
  conformance code must not import or special-case `aces_backend_libvirt`.
- Libvirt must pass by using its real target/provisioner path:
  `create_libvirt_target(driver=...)` -> `LibvirtProvisioner.apply()` ->
  `interpret_provisioning_plan()` -> `LibvirtDriver.realize()` -> portable
  `RuntimeSnapshot`. Do not certify a stub, direct interpreter call, or
  contract-surface-only target as the libvirt target.
- Default verification must stay hermetic. The acceptance test can use the
  existing recording/fake driver pattern to prove driver calls and snapshot
  mutation without requiring a host libvirt daemon, KVM, privileges, local
  images, or network access. Real-daemon checks remain opt-in/self-skipping.
- The committed conformance report should be a bounded JSON artifact assembled
  from `BackendConformanceReport` fields. It should use a stable path under a
  report or run-artifact location, canonical JSON serialization, stable
  diagnostic envelopes, and no backend-native dumps. If durable run-style output
  is implemented, reuse `run_artifact_path()` and
  `atomic_write_json_artifact()` rather than inventing a writer.

## Required Incumbents

Reuse these before adding anything new:

- Conformance: `BackendCapabilityProfile.PROVISIONING_ONLY`,
  `run_fixture_suite()`, `run_target_conformance()`, `_validate_payload()`,
  `_semantic_diagnostics()`, `ConformanceCaseResult`, and
  `BackendConformanceReport`.
- Profile and fixture authority: `load_backend_profile()`,
  `required_contracts()`, `backend_profile_path()`, `fixtures_root()`,
  `corpus_family_root(FIXTURES)`, `schema_bundle()`, and
  `contracts/profiles/backend/provisioning-only.json`.
- Manifest authority: `BackendManifest`, `ProvisionerCapabilities`,
  `backend_manifest_payload()`, `BackendManifestV2Model`,
  `validate_backend_supported_contract_versions()`, and controlled vocabulary
  validators.
- Runtime execution: `RuntimeControlPlane.submit_provisioning()`,
  `_call_backend_diagnostics()`, `_call_backend_apply()`,
  `_snapshot_contract_diagnostics()`, `RuntimeSnapshotEnvelope`,
  `OperationReceipt`, `OperationStatus`, and `Diagnostic`.
- Libvirt boundary: `create_libvirt_target()`, `create_libvirt_components()`,
  `LibvirtProvisioner`, `interpret_provisioning_plan()`,
  `capability_envelope_diagnostics()`, `LibvirtDriver`, `DriverResult`,
  `NetworkHandle`, and `DomainHandle`.
- Test precedents: the recording drivers in `test_libvirt_backend_provisioner.py`
  and `test_libvirt_backend_techvault_integration.py`, existing target
  conformance tests in `test_runtime_conformance.py`, and the libvirt manifest
  publication tests.
- Artifact persistence: `serialize_run_artifact()`,
  `run_artifact_path()`, and `atomic_write_json_artifact()` for any durable
  report output.
- Repository policy: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers

- Profile/fixture ingress: profile ids must keep flowing through
  `aces_contracts.backend_profiles` grammar and root confinement. Fixture roots
  must keep flowing through `aces_contracts.corpus`; no repo-root parent
  heuristics or remote fetching.
- Contract shape layer: manifest, operation receipt/status, provisioning plan,
  and runtime snapshot payloads must validate through existing Pydantic
  contract models and closed-world schema behavior. Do not hand-roll a
  conformance-only DTO.
- Manifest/profile layer: libvirt remains `provisioning-only` unless an
  explicit later issue enables other surfaces. `supported_contract_versions`
  must cover the profile; participant/observation capability gap checks remain
  active and must not be suppressed to make the report green.
- Runtime target layer: component presence must still match the manifest via
  `_validate_runtime_target_shape()`. A provisioning live probe must use the
  target's provisioner component and must not imply orchestrator, evaluator,
  observation, or participant-runtime support.
- Backend apply layer: live provisioning must pass through
  `RuntimeControlPlane` / `_call_backend_apply()` so the baseline snapshot is
  deep-copied, malformed `ApplyResult` values are rejected, snapshot contracts
  are checked, and failed applies preserve the baseline snapshot.
- Libvirt capability-envelope layer: plan terms used by the probe must be
  inside the selected manifest's `ProvisionerCapabilities`. Out-of-envelope
  diagnostics from `capability_envelope_diagnostics()` are legitimate failures,
  not conformance false positives to mask.
- Error-envelope layer: report failures as structured `Diagnostic` values with
  stable codes, addresses, domains, severities, and redacted messages. Do not
  serialize raw exceptions, native object reprs, libvirt XML, stdout/stderr, or
  stack traces.
- Secret and OS-exposure layer: the conformance path must not require secrets
  in CLI args or process argv, inspect local libvirt daemon state, read host
  images, or expose connection URIs, credentials, private keys, environment
  dumps, generated cloud-init, disk paths, MACs, UUIDs, or QEMU command lines in
  snapshots, diagnostics, reports, docs, or tests.
- Persistence layer: the portable state surfaces are the conformance report,
  `RuntimeSnapshot`, and operation records. Do not add a libvirt conformance
  database, native state ledger, or snapshot metadata dump.

## Extensibility Seam

The seam for future live probes is the known backend profile runtime-surface
contract in `BackendCapabilityProfile` plus the published profile artifact:
add one profile-aware probe helper per runtime surface and return
`ConformanceCaseResult` values. The provisioning probe should be parameterized
by the minimal backend-neutral scenario/plan shape and expected changed
resource addresses so another provisioning backend can reuse it without editing
libvirt code.

The seam for libvirt variation remains the target/driver factory:
`create_libvirt_target(**config)`, `_driver_config()`, and injected
`LibvirtDriver`. A future remote libvirt connection, alternate storage/image
policy, seed builder, or live-daemon integration should require only target
configuration and optional integration tests, not a conformance runner branch or
new published schema.

If the report writer becomes a CLI option later, keep the output path
parameterized and confined. Use the existing run-id label rules for run-style
archives, and keep the report schema local unless a future issue makes it a
published contract with fixtures and schema-publication governance.

## Gotchas And Anti-Patterns

Avoid:

- adding a libvirt-specific conformance runner, profile, schema, DTO, exception
  hierarchy, or fixture family for issue #606;
- changing `contracts/profiles/backend/provisioning-only.json` or published
  schemas just to make libvirt pass;
- making provisioning-only target conformance pass with only `live-manifest`;
- accepting a succeeded receipt while `OperationStatus.changed_addresses` and
  `RuntimeSnapshot.entries` remain empty;
- calling `LibvirtProvisioner.apply()` directly from conformance and bypassing
  `RuntimeControlPlane` / `_call_backend_apply()`;
- using a `_NoopDriver` for the libvirt conformance proof, because it cannot
  prove realization confirmation or snapshot mutation;
- weakening `LibvirtProvisioner` confirmation diagnostics to let a silent
  driver pass;
- copying TechVault-specific scenario, matrix, appliance, probe, or native-live
  semantics into the generic provisioning conformance probe;
- putting driver `realized_addresses()`, libvirt UUIDs, XML, seed paths,
  cloud-init content, connection URI, or native daemon inventory into
  `RuntimeSnapshot.metadata`, `ApplyResult.details`, diagnostics, or reports;
- making the default `verify` graph depend on a real libvirt daemon, QEMU/KVM,
  privileged host access, local images, private credentials, or network access.

## Non-Goals

- Implementing issue #606 in this preflight.
- Redesigning backend profiles, contract fixtures, conformance report data
  structures, the runtime control plane, `ProvisioningPlan`, `RuntimeSnapshot`,
  or the libvirt driver boundary.
- Adding orchestrator, evaluator, observation, experiment-evidence, or
  participant-runtime capability to the default libvirt target.
- Publishing a new report schema, backend profile, controlled vocabulary,
  concept family, SDL syntax, or libvirt public DTO.
- Certifying a real libvirt daemon path in the default hermetic verification
  graph; live-host certification remains opt-in and separately gated.
