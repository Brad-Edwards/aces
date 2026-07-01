# Issue 604 Libvirt Reconciliation And Teardown Preflight

Date: 2026-07-01

Issue: #604.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records architecture guardrails for honoring processor-computed
`create`/`update`/`delete`/`unchanged` reconciliation actions on the
libvirt/QEMU backend and for making teardown clean and idempotent. It is
guidance only: it does not implement reconciliation or teardown behavior, add
schemas, change manifests, or alter runtime behavior.

## Binding Sources

- ADR-004 owns compile/plan/execute, `ChangeAction`, and snapshot-based
  reconciliation semantics.
- ADR-036 owns package boundaries: `aces_processor` computes plans,
  `aces_runtime` invokes backends and persists operation/snapshot state,
  `aces_contracts` owns neutral DTOs, and concrete backends stay
  implementation-side.
- ADR-063 and the issue #197 preflight note define the concrete-backend
  portable-fact boundary and driver side-effect pattern.
- The issue #601, #602, and #603 libvirt preflight notes define the existing
  provisioning-only backend boundary, manifest truthfulness, driver/config seam,
  host artifact rules, ownership-stamped convergence, and redacted diagnostics.
- ADR-025, ADR-030, ADR-056, and ADR-057 remain relevant to network
  realization, host/process exposure, observed values, and explicit redaction.
- `aces_contracts.planning.ProvisioningPlan`, `ProvisionOp`,
  `ChangeAction`, `PlannedResource`, and `RuntimeDomain` are the action and
  plan-shape authority.
- `aces_contracts.runtime_state.RuntimeSnapshot`, `SnapshotEntry`, and
  `ApplyResult` are the portable state/result authority.
- `aces_processor.planner` owns action computation, payload equality,
  dependency ordering, and delete-plan construction. The backend consumes these
  decisions; it does not recompute them from libvirt daemon state.
- `aces_runtime.backend_calls._call_backend_apply()`, `RuntimeManager`,
  `RuntimeControlPlane`, and `ControlPlaneStore` are the execution, error
  envelope, snapshot validation, idempotency, audit, and persistence authority.

## Architecture Decisions

- Treat issue #604 as backend conformance to existing reconciliation semantics,
  not a redesign of planning, snapshots, manifests, profiles, or control-plane
  operation envelopes. No new libvirt-specific public DTO, schema, repository,
  exception hierarchy, operation store, or workflow API is justified.
- `CREATE`, `UPDATE`, `DELETE`, and `UNCHANGED` must be honored exactly as
  `ProvisionOp.action` states. `CREATE` provisions; `UPDATE` re-converges the
  owned native object to desired state; `DELETE` tears down the corresponding
  owned native object when the resource type has one; `UNCHANGED` is a backend
  no-op and must not call libvirt for realization, destruction, or readback.
- The backend must not use native libvirt state as a second planner. Native
  lookups may prove ownership and perform cleanup, but they must not rewrite
  `ChangeAction`, synthesize new portable resources, mark missing desired
  resources as deleted, or hide snapshot/host drift behind fabricated
  `SnapshotEntry` values.
- Snapshot updates commit only after the driver has confirmed the requested
  native side effect or the requested teardown is already true. On driver error,
  ownership conflict, malformed result, or unconfirmed side effect, the returned
  `ApplyResult` must fail closed with the baseline snapshot and redacted
  diagnostics so `_call_backend_apply()` and the control plane do not persist
  impossible state.
- Teardown idempotence means that a `DELETE` for an address whose corresponding
  native object and private host artifacts are already absent succeeds as
  "not realized" and removes the portable snapshot entry. Connection failures,
  permission failures, ambiguous lookup failures, and ownership conflicts are
  not idempotent success; they remain diagnostics and preserve the snapshot for
  retry.
- Native teardown is resource-type aware. `node` resources map to libvirt
  domains plus private seed media and owned nwfilters; `network` resources map
  to libvirt networks; `account-placement`, `content-placement`, and
  `feature-binding` have no standalone libvirt object and delete only their
  portable snapshot entries. If a placement changes or is removed while its
  target node remains desired, the planner's refresh/update of that target
  domain is the mechanism that re-renders cloud-init; placement deletion must
  not destroy the domain directly.
- Destroy order must preserve dependency safety: domains before networks, and
  owned per-domain artifacts before considering the domain fully torn down.
  Within a delete plan, preserve the processor's
  `snapshot_delete_order()` / `resource_delete_order()` semantics rather than
  sorting by libvirt-native name or iterating daemon inventory.
- Ownership remains fail-closed. Deterministic ACES names/UUIDs prove that an
  existing domain, network, or nwfilter belongs to the exact ACES address before
  convergence or teardown may destroy or undefine it. A name collision with a
  foreign or different-address object is an error, never a best-effort cleanup.
- Public snapshots and operation records carry portable ACES facts only:
  address, domain, resource type, planned payload, dependencies, and status.
  Libvirt UUIDs, XML, bridge names, MAC addresses, disk/seed paths, connection
  URIs, native exception text, daemon output, credentials, and private
  generated content stay behind the driver boundary.

## Required Incumbents

Reuse these existing surfaces before adding anything new:

- Plan and snapshot contracts:
  `ProvisioningPlan`, `ProvisionOp`, `ChangeAction`, `PlannedResource`,
  `RuntimeDomain`, `RuntimeSnapshot`, `SnapshotEntry`, and `ApplyResult`.
- Processor reconciliation:
  `aces_processor.planner._collect_resources()`,
  `_entry_matches_resource()`, `_build_provisioning_plan()`,
  `snapshot_delete_order()`, and the dependency helpers in
  `aces_processor.semantics.planner`.
- Runtime execution and persistence:
  `RuntimeManager.apply()`, `RuntimeManager.destroy()`,
  `RuntimeControlPlane.submit_provisioning()`, `_call_backend_diagnostics()`,
  `_call_backend_apply()`, `_snapshot_contract_diagnostics()`,
  `ControlPlaneStore`, `InMemoryControlPlaneStore`, and
  `LocalControlPlaneStore`.
- Runtime/API security and error envelopes:
  `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneIdentity`,
  `ControlPlaneRole`, request-size guards, idempotency keys, request
  fingerprints, audit records, `Diagnostic`, `OperationReceipt`, and
  `OperationStatus`.
- Libvirt package seams:
  `interpret_provisioning_plan()`, `Realization`, `DomainSpec`,
  `NetworkSpec`, `DriverResult`, `LibvirtDriver`,
  `LibvirtDeploymentDriver`, `LibvirtProvisioner`, `_driver_config()`,
  `create_libvirt_components()`, and `create_libvirt_target()`.
- Libvirt host-artifact helpers and precedents:
  deterministic runtime-name/UUID ownership stamps, `write_seed_files()`,
  `SeedBuilder`, `GenisoimageSeedBuilder`, nwfilter ownership checks, and the
  TechVault host-artifact helpers only as cautionary IO precedent, not as a
  generic provisioning contract.
- Manifest and conformance:
  `create_libvirt_manifest()`, `BackendManifest`,
  `ProvisionerCapabilities`, `backend_manifest_payload()`,
  `BackendManifestV2Model`, `contracts/profiles/backend/provisioning-only.json`,
  `profile_for_manifest()`, and `run_target_conformance()`.
- Repository policy:
  `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL/config ingress: scenario input still flows through the existing parser,
  validator, compiler, and planner. Libvirt URI, workspace, name prefix,
  storage/image policy, bridge policy, cleanup policy, and timeouts remain
  backend target/driver config, not SDL keys.
- Planner/capability layer: the planner already computes `ChangeAction`,
  delete ordering, refresh propagation, and capability diagnostics. The libvirt
  backend must not duplicate capability validation with local allowlists or
  bypass planner diagnostics with native daemon inspection.
- Plan-shape gate: the provisioner accepts only `ProvisioningPlan`, operates
  only on `RuntimeDomain.PROVISIONING`, and maps unsupported resource types to
  package-local `Diagnostic` values without echoing raw payloads.
- Runtime target gate: component presence continues to match the manifest
  through `_validate_runtime_target_shape()`. Teardown support does not imply
  orchestrator, evaluator, observation, or participant-runtime capability.
- Backend apply gate: all manager/control-plane execution passes through
  `_call_backend_apply()`, which deep-copies the baseline snapshot, wraps
  unexpected exceptions, validates `ApplyResult`, validates snapshot contracts,
  applies SEM-218 disclosure checks when present, and rejects invalid backend
  output without accepting mutated state.
- Control-plane/API/security gate: HTTP exposure must reuse
  `create_control_plane_app()`, fail-closed auth defaults, role checks,
  request-size limits, idempotency fingerprints, audit records, Pydantic plan
  and snapshot models, and redacted error responses. Do not add a separate
  libvirt teardown endpoint or unauthenticated readback channel.
- Error-envelope layer: public failures remain `Diagnostic`,
  `OperationReceipt`, and `OperationStatus`. Diagnostics may name ACES
  addresses and stable package-local codes; they must not leak libvirt XML,
  host paths, connection URIs, generated seed content, native reprs, stderr,
  stdout, environment variables, credentials, tokens, private keys, or stack
  traces.
- Host/OS exposure layer: prefer libvirt Python APIs and structured XML
  builders. If a subprocess leaf is unavoidable, use fixed argv, no
  `shell=True`, bounded timeouts, controlled working directories, and no
  secrets in argv or environment.
- Persistence layer: `RuntimeSnapshot` and control-plane operation records are
  the portable persistence surfaces. Native address/name caches, seed paths,
  nwfilter names, live daemon lookups, and cleanup scratch state stay private to
  the driver and must not be serialized through `RuntimeSnapshot.metadata` or
  `ApplyResult.details`.

## Extensibility Boundary

The seam for future variation remains `create_libvirt_target(**config)` /
`_driver_config()` plus the package-private `LibvirtDriver` adapter. Remote
libvirt URIs, alternate storage pools, image resolution, bridge/network attach
policy, firmware/UEFI settings, seed builder choice, teardown timeout,
cleanup/retention policy, and ownership lookup strategy belong there.

Future resource types should extend the pure `Realization`/driver-spec mapping
or the existing placement-to-domain refresh relationship. They should not add
new snapshot metadata ledgers, libvirt-specific plan actions, duplicate
published schemas, or control-plane endpoints.

## Gotchas And Anti-Patterns

Avoid:

- re-planning actions from libvirt's current domain/network inventory;
- treating `UNCHANGED` as permission to refresh, redefine, destroy/recreate, or
  read back native state;
- considering a teardown complete before owned domains, networks, seed media,
  and owned nwfilters have either been removed or proven already absent;
- treating every libvirt lookup exception as "not found"; absence is
  idempotent, but connection/permission/ambiguous lookup failures are not;
- deleting a foreign object because its normalized libvirt name matches an ACES
  address;
- destroying a node domain because a placement resource was deleted while the
  node remains desired;
- preserving a snapshot entry after confirmed teardown, or removing a snapshot
  entry after unconfirmed teardown;
- using `driver.realized_addresses()`, `RuntimeSnapshot.metadata`, or
  `ApplyResult.details` as a private libvirt state ledger;
- adding local schema/profile/vocabulary validators, libvirt-specific
  exceptions, a teardown store, or a separate workflow API;
- copying TechVault-specific matrix, probe, initramfs, or live-gate semantics
  into generic libvirt reconciliation;
- making default verification depend on a real libvirt daemon, QEMU/KVM,
  privileged host access, or host-local images.

## Non-Goals

- Implementing issue #604.
- Redesigning `ProvisioningPlan`, `RuntimeSnapshot`, planner reconciliation,
  `RuntimeManager.destroy()`, backend manifests, backend profiles,
  conformance, control-plane operation envelopes, or SEM-218 realization gates.
- Publishing new SDL authoring fields, contracts, schemas, backend profiles,
  concept families, manifest capability terms, or libvirt-specific public DTOs.
- Adding orchestrator, evaluator, observation, experiment-evidence, or
  participant-runtime behavior.
- Building native drift detection or a daemon inventory reconciler beyond
  honoring explicit processor-computed actions for the current snapshot/plan.
- Certifying live-host behavior in the default hermetic verification graph.
