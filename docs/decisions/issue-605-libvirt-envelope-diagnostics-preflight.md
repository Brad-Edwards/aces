# Issue 605 Libvirt Envelope Diagnostics Preflight

Date: 2026-07-01

Issue: #605.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records guardrails for surfacing typed diagnostics when a
`ProvisioningPlan` asks the libvirt/QEMU backend to realize capability terms
outside the selected backend manifest envelope. It is guidance only: it does
not implement diagnostics, change manifests, add schemas, or alter runtime
behavior.

## Binding Sources

- `docs/decisions/issue-602-libvirt-backend-manifest-preflight.md` owns the
  truthful libvirt manifest boundary: realization-support kinds are not the
  same thing as concrete capability values.
- `docs/decisions/issue-603-libvirt-apply-realization-preflight.md` owns
  fail-closed libvirt plan interpretation and apply behavior.
- `docs/decisions/issue-604-libvirt-reconciliation-teardown-preflight.md` owns
  snapshot reconciliation, teardown, and no-driver-call behavior for invalid or
  unchanged operations.
- `aces_backend_libvirt.manifest.create_libvirt_manifest()` is the libvirt
  capability envelope authority.
- `aces_backend_protocols.capabilities.BackendManifest` and
  `ProvisionerCapabilities` are the Python manifest models.
- `aces_contracts.contracts.BackendManifestV2Model`,
  `contracts/schemas/backend-manifest/backend-manifest-v2.json`, and
  `aces_contracts.controlled_vocabularies` are the manifest shape and
  vocabulary gates.
- `aces_processor.planner._validate_manifest()` and
  `aces_processor.semantics.realization.realization_support_diagnostics()` are
  the processor-side support checks the backend diagnostics must stay
  conceptually aligned with.
- `aces_backend_libvirt.realization.interpret_provisioning_plan()` and
  `LibvirtProvisioner.validate()` / `apply()` are the backend-side plan gates.
- `RuntimeManager`, `RuntimeControlPlane`, and
  `aces_runtime.backend_calls._call_backend_apply()` are the runtime execution,
  error-envelope, and snapshot-acceptance gates.

## Architecture Decisions

- Treat issue #605 as a backend plan-envelope validation task, not a manifest,
  schema, profile, SDL, or control-plane redesign.
- The selected `BackendManifest` must remain the single source of truth for
  libvirt's realizable node types, OS families, content types, and account
  features. Do not add a second hard-coded list of supported terms in the
  provisioner or driver.
- The libvirt provisioner/interpreter should validate plan terms against the
  manifest selected by `create_libvirt_components(manifest=...)`. A narrow local
  adapter that maps a plan dimension to a manifest capability surface is
  acceptable; a parallel capability schema is not.
- Governed extension syntax such as `x-owner:term` means "valid vocabulary
  shape", not "this backend realizes it". A term that passes concept-authority
  validation but is absent from `manifest.provisioner.*` must produce a blocking
  typed `Diagnostic`.
- Keep diagnostics typed by dimension: unsupported node type, OS family,
  content type, account feature, and unsupported provisioning resource type
  should be machine-distinguishable stable codes. Do not collapse them into a
  generic libvirt failure or a native driver error.
- Use the same validation helper from both `validate()` and `apply()`. The
  control plane records validation diagnostics but still calls `apply()`, so
  `apply()` must independently fail before snapshot reconciliation or driver IO
  whenever the envelope helper reports an error.
- Validate the same materialization surface the provisioner can persist or
  drive. Do not inspect only `plan.resources` if `plan.operations` can still
  create snapshot entries or request driver work from divergent payloads.
- Do not reject in-envelope governed terms that issue #603 already realizes:
  content types `file`, `dataset`, and `directory`, and the governed account
  feature terms declared by the libvirt manifest.
- Keep SEM-218 realization-support diagnostics distinct from concrete term
  envelope diagnostics. `realization_support_diagnostics()` answers "does the
  backend declare this requirement kind?"; #605 answers "is this concrete plan
  term inside this backend's declared capability envelope?"

## Required Incumbents

Reuse these before adding anything new:

- Manifest and rendering: `create_libvirt_manifest()`, `BackendManifest`,
  `BackendCapabilitySet`, `ProvisionerCapabilities`,
  `RealizationSupportDeclaration`, and `backend_manifest_payload()`.
- Contract and vocabulary validation: `BackendManifestV2Model`,
  `ProvisionerCapabilitiesModel`,
  `validate_controlled_vocabulary_scope_values()`, and the checked-in
  controlled-vocabulary catalog.
- Processor-side semantics: `_validate_manifest()` for concrete provisioner
  capability checks, `_account_features()` for the existing account-feature
  extraction rules, and `realization_support_diagnostics()` for SEM-218
  requirement-kind checks. If those extraction rules must be shared, extract the
  minimal neutral helper rather than copying divergent logic.
- Libvirt plan gates: `interpret_provisioning_plan()`, `Realization`,
  `LibvirtProvisioner.validate()`, `LibvirtProvisioner.apply()`, and the
  existing package-local `Diagnostic` pattern.
- Runtime fail-closed path: `RuntimeManager._apply_precondition_failure()`,
  `RuntimeControlPlane.submit_provisioning()`, `_call_backend_diagnostics()`,
  `_call_backend_apply()`, `ApplyResult`, and `RuntimeSnapshot`.
- Verification precedents: `test_runtime_planner.py`,
  `test_libvirt_backend_manifest_publication.py`,
  `test_libvirt_backend_realization.py`, and the control-plane/runtime-manager
  tests that prove invalid plans do not persist snapshots or call drivers.

## Cross-Cutting Layers

- SDL and parser layer: no new SDL authoring fields are needed. Closed
  Pydantic SDL models, semantic validation, instantiation, and compilation
  remain the normal authoring path.
- Concept-authority layer: vocabulary validators still decide whether a term is
  governed or syntactically valid as an extension. Backend envelope validation
  decides whether the selected backend realizes that valid term.
- Manifest/config layer: `BackendManifest` construction and
  `BackendManifestV2Model` validation continue to enforce non-empty capability
  surfaces, account-support consistency, concept bindings, contract ids, and
  realization-support shape. Do not bypass these with local JSON or dict
  payloads.
- Planner layer: processor planning already emits diagnostics for normal
  compiled models that exceed a manifest. Backend envelope validation is the
  defense for direct, mutated, or third-party `ProvisioningPlan` inputs.
- Runtime target layer: component presence must still match the manifest via
  `_validate_runtime_target_shape()`. Passing a manifest into libvirt
  validation must not imply orchestrator, evaluator, observation, or
  participant-runtime support.
- Backend apply layer: all diagnostics are `Diagnostic` values. Any error from
  the envelope helper must stop before `_reconcile_snapshot()`, `driver.realize()`,
  or `driver.destroy()`, and must return the input snapshot unchanged.
- Control-plane/API layer: `RuntimeControlPlane` must keep using operation
  receipts/statuses, idempotency keys, request fingerprints, audit records, and
  existing API guards. No libvirt-specific endpoint or exception path is
  needed.
- Error-envelope layer: messages may name ACES addresses, dimensions, and
  capability terms. They must not echo raw plan payloads, content text,
  cloud-init data, credentials, SSH keys, environment variables, native libvirt
  XML, host paths, stdout/stderr, or stack traces.
- Host/OS exposure layer: envelope validation is pure. It must not import
  `libvirt`, inspect the daemon, run subprocesses, read host images, or place
  secrets in argv or environment.
- Persistence layer: rejected plans must not write `RuntimeSnapshot` entries,
  control-plane snapshot state, `ApplyResult.details`, or metadata ledgers for
  unsupported terms.

## Extensibility Boundary

The parameter for future capability variation belongs at the manifest/target
factory boundary: `create_libvirt_manifest(**config)`,
`create_libvirt_target(**config)`, and `create_libvirt_components(manifest=...)`.
If a future libvirt configuration truly realizes an extension term, the manifest
factory should declare that term for that configuration and the same envelope
validator should accept it without code changes to the term list.

If future dimensions need envelope checks, add them through one small mapping:
plan payload extractor, manifest capability surface, realization requirement
kind when one exists, and diagnostic code. Do not scatter per-dimension
allowlists through the interpreter, provisioner, driver, and tests.

## Gotchas And Anti-Patterns

Avoid:

- treating governed extension syntax as backend support;
- checking `resource.resource_type == "node"` while ignoring the payload's
  `node_type`;
- realizing an unsupported content type by falling through and emitting no
  cloud-init contribution;
- interpreting every account field as an account-feature requirement and
  accidentally rejecting descriptive fields that `_validate_manifest()` does not
  treat as features;
- silently ignoring an unsupported account feature while creating the account;
- validating only the happy-path compiler output while leaving direct
  `ProvisioningPlan` inputs unguarded;
- relying on `RuntimeControlPlane.submit_provisioning()` validation diagnostics
  to prevent side effects, because `apply()` is still invoked;
- calling the driver before all envelope diagnostics are known;
- adding libvirt-specific schemas, profiles, DTOs, exception hierarchies, or
  control-plane routes;
- changing published controlled vocabularies or manifest schemas just to test
  an out-of-envelope term.

## Non-Goals

- Implementing issue #605.
- Redesigning `BackendManifest`, `ProvisioningPlan`, `RuntimeSnapshot`,
  `RuntimeManager`, `RuntimeControlPlane`, SEM-218 realization gates, or backend
  conformance.
- Adding new SDL syntax, schemas, backend profiles, concept families,
  controlled-vocabulary terms, or public libvirt DTOs.
- Expanding libvirt beyond the issue #603 governed provisioning envelope.
- Making default verification require a real libvirt daemon, QEMU/KVM,
  privileged host access, host-local images, or network access.
