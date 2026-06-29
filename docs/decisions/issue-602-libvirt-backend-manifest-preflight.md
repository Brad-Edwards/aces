# Issue 602 Libvirt Backend Manifest Preflight

Date: 2026-06-28

Issue: #602.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records manifest-specific guardrails for publishing the libvirt/QEMU
backend's provisioning-only `backend-manifest-v2`. It is guidance only: it does
not implement the manifest, add schemas, or change runtime behavior.

## Binding Sources

- `docs/decisions/issue-601-libvirt-provisioning-backend-preflight.md` is the
  adjacent libvirt backend boundary: provisioning-only, implementation-side,
  driver-backed, and no new public DTO or schema surface.
- `contracts/schemas/backend-manifest/backend-manifest-v2.json` and
  `aces_contracts.contracts.BackendManifestV2Model` are the manifest shape
  authority.
- `contracts/profiles/backend/provisioning-only.json`,
  `aces_contracts.backend_profiles`, and `aces_conformance.conformance` are the
  profile/conformance authority.
- `aces_backend_protocols.capabilities`, `aces_backend_protocols.manifest`, and
  `aces_contracts.manifest_authority` are the incumbent Python manifest helpers.
- `aces_contracts.controlled_vocabularies` and
  `contracts/concept-authority/controlled-vocabularies-v1.json` govern
  provisioner node type, OS family, content type, and account feature terms.
- `aces_processor.planner._validate_manifest()` and
  `aces_processor.semantics.realization.realization_support_diagnostics()` are
  the planner gates that consume the manifest.
- `aces_runtime.backend_calls` is the runtime contract/error-envelope gate that
  validates backend output and SEM-218 realization honesty.

## Architecture Decisions

- Treat issue #602 as a truthful-manifest publication/tightening task, not a
  manifest-system redesign. The implementation must reuse
  `create_libvirt_manifest()`, `BackendManifest`, `BackendCapabilitySet`,
  `ProvisionerCapabilities`, `RealizationSupportDeclaration`,
  `backend_manifest_payload()`, and `BackendManifestV2Model`.
- Keep the libvirt backend provisioning-only. The manifest must leave
  orchestrator, evaluator, participant runtime, and observation capability
  blocks absent unless a later issue adds real surfaces and evidence.
- `supported_contract_versions` must cover every required contract in
  `contracts/profiles/backend/provisioning-only.json`. It may also include
  `provisioning-plan-v1` because the provisioner consumes `ProvisioningPlan`.
  It must not copy `BACKEND_SUPPORTED_CONTRACT_IDS` wholesale or claim
  orchestration, evaluation, participant, or experiment evidence contracts.
- Keep `realization_support` under the existing `runtime-realization` domain.
  Use the existing `declared-capability-match` exact-kind seam only when the
  backend snapshot preserves exact authored values for SEM-218 runtime checks.
- Do not conflate realization kinds with capability values. `realization_support`
  declares which requirement kinds the planner may check; `ProvisionerCapabilities`
  declares which concrete vocabulary terms the backend can provision.
- The current libvirt interpreter handles provisioning resource types `node` and
  `network`. A manifest that claims content or account realization must be
  backed by corresponding provisioner/driver behavior, not only by adding
  `file`, `dataset`, `directory`, or account feature strings to the manifest.
- VM image/source handling is not SDL `content` placement support. Do not use
  `DomainSpec.image_ref`, TechVault parameters, or generated initramfs contents
  as evidence that generic `provision.content.*` resources are realized.
- Account claims must pass the existing account gate:
  `supported_account_features` is valid only when `supports_accounts=True`, and
  every listed feature must be a governed term or governed extension. If libvirt
  does not actually create guest accounts and feature attributes, leave account
  support unclaimed and let account-using plans fail at the existing planner
  diagnostic.
- Concept bindings must describe every claimed governed capability surface:
  node types and OS families for the existing provisioner surface, plus content
  types or account features only if those capability fields are honestly
  non-empty. Do not add duplicate bindings or bind absent optional surfaces.

## Required Incumbents

Reuse these before adding anything new:

- Manifest model/rendering:
  `aces_backend_protocols.capabilities.BackendManifest`,
  `BackendCapabilitySet`, `ProvisionerCapabilities`, and
  `aces_backend_protocols.manifest.backend_manifest_payload()`.
- Contract validation:
  `aces_contracts.contracts.BackendManifestV2Model`,
  `RealizationSupportDeclarationModel`, and the checked-in JSON Schema.
- Manifest authority:
  `BACKEND_SUPPORTED_CONTRACT_IDS` only as the allow-list, and
  `validate_backend_supported_contract_versions()` as the validator.
- Profile/conformance:
  `contracts/profiles/backend/provisioning-only.json`,
  `load_backend_profile()`, `required_contracts()`,
  `profile_for_manifest()`, and `run_target_conformance()`.
- Vocabulary/concept authority:
  `validate_controlled_vocabulary_scope_values()` and the concept binding
  checks already run by `BackendManifestV2Model`.
- Planner/runtime gates:
  `_validate_manifest()`, `realization_support_diagnostics()`,
  `realization_disclosure()`, `RuntimeManager`, `RuntimeControlPlane`, and the
  existing `Diagnostic`, `OperationReceipt`, `OperationStatus`, and
  `RuntimeSnapshot` envelopes.
- Libvirt boundary:
  `aces_backend_libvirt.realization.interpret_provisioning_plan()`,
  `LibvirtProvisioner`, `LibvirtDriver`, `LibvirtDeploymentDriver`, and the
  registry/config seam in `create_libvirt_target(**config)`.

## Cross-Cutting Layers

- Contract shape layer: payloads must render through
  `backend_manifest_payload()` and validate with `BackendManifestV2Model` /
  `backend-manifest-v2.json`; do not hand-build parallel JSON.
- Manifest authority layer: `supported_contract_versions` must pass
  `validate_backend_supported_contract_versions()` and remain within the
  backend/runtime contract allow-list.
- Backend profile layer: the manifest must satisfy the published
  provisioning-only profile contract set through `run_target_conformance()`;
  profile requirements must be loaded from `contracts/profiles/backend/`, not
  copied into a local list.
- Controlled-vocabulary layer: `supported_node_types`, `supported_os_families`,
  `supported_content_types`, and `supported_account_features` must pass the
  governed vocabulary checks. Use governed extensions only when the backend
  owns and documents the extension semantics.
- Concept-binding layer: claimed capability fields must have canonical concept
  bindings; duplicate scopes and bindings to fields not present in the manifest
  must continue to fail validation.
- Planner layer: `_validate_manifest()` already rejects unsupported node, OS,
  content, ACL, and account requirements. Manifest changes must make those
  diagnostics more truthful, not bypass or duplicate them.
- SEM-218 layer: `realization_support_diagnostics()` gates compiled exact and
  constrained realization requirements; `realization_disclosure()` later rejects
  backend snapshots that omit or silently change exact authored values. Current
  compiled SEM-218 requirements cover node type, OS family, and content type;
  account-feature support remains a provisioner capability check today.
- Runtime target layer: `profile_for_manifest()` must still infer
  `provisioning-only`, and `RuntimeTarget` must continue to have only a
  provisioner component.
- Error-envelope and observability layer: failures remain `Diagnostic`,
  `OperationReceipt`, `OperationStatus`, and conformance-report fields. Do not
  introduce libvirt-specific public exceptions or leak native object reprs,
  XML, host paths, connection URIs, credentials, or argv into diagnostics.
- Secret and OS-exposure layer: the manifest is portable capability data only.
  Connection URI, storage pool, bridge policy, base image path, cloud-init
  content, SSH material, and guest credentials belong in target/driver config
  or private driver state, not in manifest constraints or snapshot metadata.
- Import/dependency layer: normal manifest import must not import `libvirt` or
  require a daemon. Keep native libvirt access lazy and behind the existing
  driver adapter.
- Persistence layer: publishing this manifest must not add a repository,
  operation store, cache, or native-state ledger. Existing snapshots and
  operation envelopes are the only portable persistence surface.

## Extensibility Boundary

The seam for future substrate variation is the libvirt target/driver boundary:
`create_libvirt_target(**config)`, `_driver_config()`, `LibvirtDriver`, and the
portable driver specs. Remote libvirt URIs, alternate storage pools, bridge
policy, image/template policy, cloud-init/content injection, account creation,
and resource limits belong there.

If capabilities become configuration-dependent, make that a deterministic
manifest-factory parameter and test the rendered payload for each supported
configuration. Do not hard-code one host's libvirt state into the canonical
manifest or add a new published schema/profile for a host-local variation.

## Gotchas And Anti-Patterns

Avoid:

- copying the stub or reference backend's full manifest into libvirt;
- adding `content-type` or `account-feature` claims without actual generic
  `ProvisioningPlan` resource handling and snapshot evidence;
- treating VM disk images, initramfs generation, or TechVault-specific
  parameters as generic `content` placement support;
- listing `supported_account_features` while `supports_accounts=False`;
- adding local JSON Schema, local profile maps, local vocabulary validators, or
  a libvirt-specific manifest DTO;
- changing `contracts/schemas/` or `contracts/profiles/` for this issue unless
  the contract authority itself is intentionally changing;
- hiding unsupported dimensions in `constraints` prose while capability fields
  overclaim support;
- exposing native libvirt IDs, XML, disk paths, bridge names, MAC addresses, or
  credentials in manifest constraints, diagnostics, snapshots, or tests;
- using `RuntimeSnapshot.metadata` or `ApplyResult.details` as a private
  libvirt state dump.

## Non-Goals

- Implementing content placement, account creation, orchestration, evaluation,
  participant runtime, observation, or experiment evidence capture.
- Publishing new contracts, backend profiles, schemas, vocabularies, concept
  families, or SDL authoring fields.
- Redesigning `BackendManifest`, `ProvisioningPlan`, `RuntimeSnapshot`,
  SEM-218 realization gates, conformance, registry, or control-plane envelopes.
- Making default verification require libvirt, QEMU, KVM, privileged host
  access, or a running daemon.
