# Issue 601 Libvirt Provisioning Backend Preflight

Date: 2026-06-25

Issue: #601.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records architecture guardrails for scaffolding a libvirt/QEMU
provisioning backend. It is guidance only: it does not implement the backend,
add schemas, change profiles, or alter runtime behavior.

## Binding Sources

- ADR-004 defines the compile, plan, execute runtime and requires explicit
  backend protocols plus a `BackendManifest`.
- ADR-036 defines package ownership: `aces_runtime` owns live control,
  `aces_backend_protocols` owns backend declarations, `aces_backend_stubs` owns
  non-normative in-memory stubs, and `aces_contracts` owns neutral DTOs.
- ADR-063 and the issue #197 preflight note define the concrete-backend
  portable-fact boundary: real realization is a backend side effect, while
  manifests, snapshots, diagnostics, and conformance reports carry only ACES
  contract data.
- The issue #491 SEM-218 preflight note defines the runtime realization gate
  and the `runtime.backend-contract-invalid` adapter boundary.
- `docs/explain/reference/backend-conformance.md` and
  `contracts/profiles/backend/provisioning-only.json` define the conformance
  surface for a provisioner-only target.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and
  `tools/policy/adr_policy.yaml` define the repository workflow and policy
  gates.

## Architecture Decisions

- Add libvirt as an implementation-side backend package, expected to live under
  `implementations/python/packages/aces_backend_libvirt/`. Core packages must
  not import it, and no implementation logic belongs in
  `implementations/python/src/aces/`.
- Implement only the `Provisioner` protocol. The manifest must omit
  orchestrator, evaluator, participant runtime, and observation capability
  blocks unless a later issue adds those surfaces with evidence and
  conformance. The inferred target profile should remain `provisioning-only`.
- Expose constructor helpers that mirror existing backend shape:
  `create_libvirt_manifest(**config)`, `create_libvirt_components(manifest=...,
  **config)`, `create_libvirt_target(**config)`, and a registry helper. Config
  flows through the existing `BackendRegistry` descriptor seam.
- Reuse the existing manifest, registry, runtime, conformance, diagnostic, and
  snapshot contracts. Do not add a libvirt-specific manifest schema, profile,
  vocabulary table, exception hierarchy, operation store, or public DTO layer.
- Keep plan interpretation pure and host-side realization behind an injected
  package-private driver or connection adapter. The pure layer consumes
  `ProvisioningPlan` and returns portable libvirt-intent specs plus
  `Diagnostic` values; the impure layer owns libvirt/QEMU calls and native
  bookkeeping privately.
- `validate()` and `apply()` must fail closed when `plan` is not an
  `aces_contracts.planning.ProvisioningPlan`. Use one stable package-local
  diagnostic code ending in `.invalid-plan`; `apply()` returns
  `ApplyResult(success=False, snapshot=<input snapshot>, diagnostics=[...])`.
  Do not rely on an `AttributeError` being wrapped later as
  `runtime.backend-call-failed`.
- The manifest should declare only evidence-backed contract ids. For this
  issue that means the provisioning-only runtime/control-plane contracts and
  `provisioning-plan-v1`; do not copy the stub's full
  `BACKEND_SUPPORTED_CONTRACT_IDS` set and accidentally claim orchestration,
  evaluation, participant, or experiment evidence surfaces.

## Required Incumbents

Reuse these existing surfaces before adding anything new:

- Protocols and capability declarations:
  `aces_backend_protocols.protocols.Provisioner`,
  `BackendManifest`, `BackendCapabilitySet`, `ProvisionerCapabilities`,
  `RealizationSupportDeclaration`, `RealizationSupportMode`, and
  `backend_manifest_payload()`.
- Neutral contracts: `ProvisioningPlan`, `ProvisionOp`, `ChangeAction`,
  `RuntimeDomain`, `Diagnostic`, `Severity`, `ApplyResult`,
  `RuntimeSnapshot`, and `SnapshotEntry`.
- Runtime construction and guards: `BackendRegistry`, `RuntimeTarget`,
  `RuntimeTargetComponents`, `_validate_runtime_target_shape`,
  `RuntimeManager`, `RuntimeControlPlane`, `_call_backend_diagnostics()`, and
  `_call_backend_apply()`.
- Manifest/profile authority: `BackendManifestV2Model`,
  `BACKEND_SUPPORTED_CONTRACT_IDS`,
  `validate_backend_supported_contract_versions()`,
  `contracts/profiles/backend/provisioning-only.json`, and
  `run_target_conformance()`.
- Existing concrete-backend patterns: the stub constructor shape in
  `aces_backend_stubs.stubs` and the reference backend's separation between
  pure interpretation, provisioner snapshot reconciliation, and injected driver
  IO.
- Repository policy: `tools/policy/adr_policy.yaml` module boundaries,
  `implementations/python/pyproject.toml` package and coverage lists,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL/config ingress: scenario input still flows through the existing parser,
  compiler, and planner. Libvirt URI, workspace, storage pool, bridge/network
  policy, base image, and trust settings are backend factory config, not new
  SDL keys or hidden ambient YAML.
- Plan shape gate: the backend accepts only `ProvisioningPlan`. Resource
  interpretation must use the existing `RuntimeDomain.PROVISIONING`,
  `ChangeAction`, `PlannedResource`, and `ProvisionOp` fields; unsupported or
  malformed resource payloads become `Diagnostic` values that do not echo raw
  payloads.
- Manifest authority gate: supported contracts, concept bindings,
  realization-support declarations, compatibility, and provisioner capability
  terms must validate through `BackendManifest`, `BackendManifestV2Model`, the
  controlled vocabulary checks, and `backend_manifest_payload()`.
- Runtime target gate: component presence must match the manifest. Since this
  is provisioning-only, `RuntimeTarget` should have a provisioner and `None` for
  orchestrator, evaluator, and participant runtime.
- Backend apply gate: execution through `RuntimeManager` or
  `RuntimeControlPlane` must pass `_call_backend_apply()`, which deep-copies
  snapshots, converts unexpected exceptions to diagnostics, validates
  `ApplyResult`, validates runtime snapshot contracts, and rejects invalid
  backend output without accepting a mutated snapshot.
- Control-plane and error-envelope gate: public failures are `Diagnostic`,
  `OperationReceipt`, and `OperationStatus` values. Do not add public libvirt
  exceptions, raw tracebacks, libvirt XML dumps, QEMU command lines, native
  object reprs, or stderr/stdout payloads to diagnostics, audit records,
  snapshots, examples, or conformance reports.
- Secret and OS-exposure gate: libvirt connection URIs, TLS credentials,
  passwords, SSH keys, storage paths, cloud-init secrets, guest credentials,
  daemon inspect output, host environment, and process argv must stay out of
  portable artifacts. Prefer an injected libvirt connection adapter; if any
  subprocess leaf is unavoidable, use fixed argv, no `shell=True`, no secrets
  in argv, bounded timeouts, controlled working directories, and redacted
  diagnostics.
- Dependency/import gate: do not import concrete backends from each other. The
  libvirt package should consume `aces_backend_protocols`, `aces_contracts`,
  and the public `aces_runtime.registry` seam. Avoid importing `aces.*`
  compatibility wrappers or processor/private SDL implementation modules.
- Packaging/policy gate: adding `aces_backend_libvirt` requires updating the
  Python package list, coverage source list, module-boundary policy, and policy
  test fixtures. Default verification must not require a host libvirt daemon or
  installed libvirt Python bindings unless the package declares and gates an
  explicit optional integration path.

## Extensibility Boundary

The seam for the next variation is the registry/config and driver boundary:
`connection_uri`, workspace/name prefix, storage pool, network attachment
policy, base image/template policy, resource limits, timeout, and injected
connection/runner belong behind `create_libvirt_target(**config)` and the
package-private driver adapter. A future remote-libvirt URI, alternate storage
pool, UEFI/cloud-init support, or bridge policy should not require changes to
`RuntimeManager`, `RuntimeControlPlane`, published schemas, backend profiles, or
the manifest renderer.

## Gotchas And Anti-Patterns

Avoid:

- subclassing the stub or treating `aces_backend_stubs` as normative authority;
- copying the reference backend's full capability and contract claims into a
  provisioning-only backend;
- declaring orchestrator, evaluator, participant runtime, or observation
  capability blocks for this issue;
- adding libvirt/QEMU-specific SDL syntax, published schemas, backend profiles,
  vocabulary families, public DTOs, exception hierarchies, or persistence
  stores;
- importing `libvirt` at package import time when that would make normal builds
  fail on hosts without libvirt libraries; keep real-daemon work behind lazy,
  optional, or injected leaves;
- exposing libvirt domain UUIDs, network UUIDs, XML, disk paths, bridge names,
  MAC addresses, cloud-init content, credentials, or command output as portable
  ACES semantics;
- using `RuntimeSnapshot.metadata` or `ApplyResult.details` as a dumping ground
  for backend-native state;
- certifying the backend with local smoke tests only; use manifest validation
  and provisioning-only target conformance, with real-daemon tests opt-in and
  self-skipping.

## Non-Goals

- Implementing orchestration, evaluation, participant runtime, observation, or
  experiment evidence capture.
- Publishing new contracts, fixtures, backend profiles, or SDL authoring
  fields.
- Redesigning `ProvisioningPlan`, `RuntimeSnapshot`, `BackendManifest`, the
  registry, conformance runner, control plane, or SEM-218 adapter gate.
- Making the default hermetic verification graph depend on libvirt, QEMU, KVM,
  privileged host access, or a running system daemon.
