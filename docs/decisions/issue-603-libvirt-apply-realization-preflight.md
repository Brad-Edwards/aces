# Issue 603 Libvirt Apply Realization Preflight

Date: 2026-06-29

Issue: #603.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records guardrails for materializing `ProvisioningPlan` operations
with libvirt/QEMU. It is guidance only: it does not implement `apply()`, add
schemas, change manifests, or alter runtime behavior.

## Binding Sources

- `docs/decisions/issue-601-libvirt-provisioning-backend-preflight.md` defines
  the libvirt backend boundary: provisioning-only, implementation-side, pure
  plan interpretation plus injected host driver.
- `docs/decisions/issue-602-libvirt-backend-manifest-preflight.md` defines the
  truthful capability and manifest boundary for libvirt.
- `docs/decisions/issue-491-sem-218-runtime-realization-preflight.md` defines
  the backend apply gate and runtime realization disclosure boundary.
- ADR-004, ADR-036, and ADR-063 keep runtime orchestration, package ownership,
  and concrete backend side effects separate from portable contracts.
- ADR-025, ADR-030, ADR-056, and ADR-057 are relevant to network realization,
  process/host exposure, observed values, and secret-shaped runtime values.
- `aces_contracts.planning.ProvisioningPlan`, `ProvisionOp`, `ChangeAction`,
  `PlannedResource`, and `RuntimeDomain` are the plan authority.
- `aces_contracts.runtime_state.RuntimeSnapshot`, `SnapshotEntry`, and
  `ApplyResult` are the returned-state authority.
- `aces_processor.planner` owns snapshot-based reconciliation,
  `UNCHANGED`/`CREATE`/`UPDATE`/`DELETE` action selection, delete ordering, and
  provisioner capability diagnostics.
- `aces_runtime.backend_calls._call_backend_apply()` is the runtime
  fail-closed adapter for backend output and SEM-218 disclosure.
- `aces_backend_libvirt.realization`, `driver`, `drivers.libvirt`,
  `provisioner`, `manifest`, and `target` are the incumbent libvirt seams.
- `aces_backend_libvirt.techvault_native` is a scenario-specific live-gate
  implementation; it is useful evidence for host IO and libvirt caution, not a
  generic provisioning contract to copy wholesale.

## Architecture Decisions

- Implement issue #603 by tightening the existing libvirt provisioner,
  interpreter, and driver seams. Do not add implementation logic under
  `implementations/python/src/aces/`, do not make core packages import
  `aces_backend_libvirt`, and do not add a libvirt-specific public DTO,
  schema, profile, exception hierarchy, operation store, or persistence layer.
- Treat `RuntimeSnapshot` as the portable source for idempotent reconciliation.
  `UNCHANGED` operations must not call the driver or define native resources;
  they may only preserve or refresh the corresponding portable `SnapshotEntry`
  with an unchanged status. `CREATE`, `UPDATE`, and `DELETE` are the only
  operations that may cause libvirt side effects.
- The native driver must also be duplicate-resistant for crash/retry and
  partial-host-state cases. Use deterministic runtime names from ACES address,
  name prefix, and safe-name normalization. Because only `CREATE`/`UPDATE`
  operations reach the driver, an existing native object at that name is
  *converged*, not skipped: it is stopped and undefined, then the desired
  XML/seed/nwfilter is redefined, so a tightened ACL or disabled account is
  genuinely enforced and exactly one object survives. Convergence is destructive,
  so it is ownership-checked: each domain, network, and nwfilter carries a
  deterministic per-address libvirt UUID, and a name hit whose UUID is not that of
  the ACES object for this address is refused — for convergence, for deletion, and
  for the host-global nwfilter redefine/undefine — so apply fails closed rather
  than replacing or removing a foreign or another-address object that merely
  normalizes to the same name. If
  convergence cannot be completed the operation fails closed with a redacted
  `Diagnostic` rather than redefining over stale, still-active config, replacing
  an object it does not own, or defining a duplicate.
- Successful apply returns snapshot entries for realized provisioning
  resources using portable ACES facts only: address, domain, resource type,
  planned payload, dependencies, and status. `changed_addresses` contains only
  non-`UNCHANGED` operations. Do not put libvirt UUIDs, XML, bridge names, MAC
  addresses, disk paths, cloud-init content, generated file paths, connection
  URIs, or native object reprs into `SnapshotEntry.payload`,
  `RuntimeSnapshot.metadata`, `ApplyResult.details`, diagnostics, audit records,
  conformance reports, or tests.
- Base image and cloud-init handling belong behind the driver/config seam.
  `Source` remains provider-neutral; image resolution may use
  `DomainSpec.image_ref` and deterministic target config, but must not require
  new SDL syntax. Generated cloud-init or seed media are private host artifacts:
  create them under a configured workspace, with restrictive file modes,
  deterministic names, cleanup/update behavior, and redacted diagnostics.
- Content support is backed by real `content-placement` driver logic
  (cloud-init `write_files`/`runcmd`), not by VM image handling alone. A base
  image or scenario-specific TechVault initramfs is not, on its own, content
  realization; the dedicated content-placement interpretation is.
- `feature-binding`, `content-placement`, and `account-placement` are
  provisioning resources. The libvirt interpreter must either realize a
  resource type with concrete driver behavior and portable snapshot evidence,
  or return diagnostics for unsupported resource types. It must never silently
  drop placements while returning success.
- Content and account placement support is capability-honest because it is
  fully realized. This issue adds generic content placement and account
  creation via cloud-init, so `ProvisionerCapabilities`, concept bindings,
  manifest tests, planner-facing expectations, and driver behavior are updated
  together. The manifest declares the full governed content/account vocabulary
  (all content types, all account features, accounts, ACLs) because the driver
  realizes every declared term — it cannot over-claim.
- Feature binding support has no dedicated manifest field; it is realized as a
  bounded libvirt provisioner behavior: pure interpretation to a
  package/cloud-init intent, private driver IO, and a portable snapshot entry
  preserving the authored binding payload. Do not create a hidden
  feature-capability schema for this issue.
- `validate()` and `apply()` must keep the existing invalid-plan behavior:
  fail closed for non-`ProvisioningPlan` inputs with the package-local
  diagnostic and the input snapshot unchanged.
- Public errors remain `Diagnostic`, `OperationReceipt`, and
  `OperationStatus` data. Native libvirt failures, XML errors, QEMU errors,
  cloud-init generation failures, image lookup failures, and file permission
  failures must be mapped to stable package-local diagnostic codes with
  redacted messages.
- Default verification must remain hermetic. Real libvirt daemon tests are
  opt-in/self-skipping and must not be required by `nox -s verify`.

## Realization Fidelity (implemented)

The manifest declares the full governed vocabulary and the driver realizes every
declared term to the maximum the substrate allows, so the claim cannot exceed the
behavior:

- **Cross-OS account/content realization** uses cloud-init's `users` and
  `write_files` directives, which cloud-init (Linux/BSD) and cloudbase-init
  (Windows) interpret natively — these are genuinely OS-portable.
- **Service/package and mail realization is OS-family-aware** via
  `aces_backend_libvirt.dialects`: Linux `systemctl`/`apt`, FreeBSD
  `sysrc`/`pkg`, Windows `choco`/`sc.exe`, macOS `brew`. Each dialect emits the
  family's native tooling as injection-safe argv-list `runcmd`, never a Linux
  primitive applied blindly.
- **Network ACLs** (`ACLRule` is a directional firewall/NACL rule, not a POSIX
  file ACL) are realized host-side as libvirt **nwfilter** rules referenced from
  the domain interface — OS-independent enforcement that genuinely backs
  `supports_acls=True`.
- **Substrate ceilings, not stubs.** A real Kerberos SPN needs an AD/realm join
  and source-backed content needs a fetch endpoint the SDL does not carry;
  absent those, the portable maximum is a host-side descriptor the guest joins
  with or consumes. This is the ceiling the generic substrate imposes, recorded
  honestly rather than narrowed out of the manifest.
- **Security boundary.** Plan-derived values never reach a shell: `runcmd` is
  argv-list form and the host-side seed ISO subprocess uses fixed argv. Seed
  source files are written `O_NOFOLLOW`/`O_EXCL` at `0o600` into a freshly
  created, owner-verified directory; the directory is `0o711` (traversable, not
  listable) and the seed ISO is `0o600` (never world-readable), so the rendered
  cloud-init stays private while the libvirt/QEMU process reaches the attached
  disk through libvirt's dynamic-ownership relabel. Governed-value translation is
  fail-closed: an ACL that cannot be resolved exactly (including a port scope on a
  wildcard protocol), an unbindable placement, or a password account without
  rendered credentials is rejected/locked, never widened. Plan-controlled
  identifiers interpolated into `/etc/aces` descriptor filenames are reduced to a
  single safe path component, so a crafted name cannot become a guest root file
  write outside its descriptor directory.

## Required Incumbents

Reuse these before adding anything new:

- Plan and snapshot contracts:
  `ProvisioningPlan`, `ProvisionOp`, `ChangeAction`, `PlannedResource`,
  `RuntimeDomain`, `RuntimeSnapshot`, `SnapshotEntry`, and `ApplyResult`.
- Planner reconciliation:
  `aces_processor.planner._collect_resources()`,
  `_build_provisioning_plan()`, `_entry_matches_resource()`,
  `snapshot_delete_order()`, provisioner capability diagnostics, and the
  resource dependency helpers in `aces_processor.semantics.planner`.
- Runtime execution guards:
  `RuntimeManager`, `RuntimeControlPlane`, `_call_backend_diagnostics()`,
  `_call_backend_apply()`, `_snapshot_contract_diagnostics()`, and the
  existing operation store/idempotency fields.
- Manifest and conformance:
  `create_libvirt_manifest()`, `BackendManifest`,
  `ProvisionerCapabilities`, `backend_manifest_payload()`,
  `BackendManifestV2Model`, `contracts/profiles/backend/provisioning-only.json`,
  `profile_for_manifest()`, and `run_target_conformance()`.
- Libvirt package seams:
  `interpret_provisioning_plan()`, `Realization`, `DomainSpec`,
  `NetworkSpec`, `DriverResult`, `LibvirtDriver`, `LibvirtDeploymentDriver`,
  `LibvirtProvisioner`, `_driver_config()`, `create_libvirt_components()`, and
  `create_libvirt_target()`.
- Concrete-backend precedent:
  `aces_reference_backend.provisioner` for snapshot reconciliation and
  no-driver-call `UNCHANGED` behavior, and
  `aces_reference_backend.driver` for the portable handle boundary.
- Host/OS cautionary precedent:
  `TechVaultNativeLibvirtDriver`, `BusyboxInitramfsBuilder`,
  `copy_kernel_for_libvirt()`, and `make_libvirt_readable()` for generated
  boot artifacts, while keeping TechVault-specific matrix/probe semantics out
  of generic libvirt apply.
- Repository policy:
  `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL/config ingress: existing SDL parser, validator, compiler, `Source`,
  `Content`, `Account`, feature, and node models remain the only authoring
  input. Libvirt URI, storage pool, image catalog, cloud-init workspace, name
  prefix, bridge policy, timeout, and cleanup policy are backend target/driver
  config, not new SDL keys.
- Planner/capability layer: the planner already emits provisioning resources
  and capability diagnostics for node type, OS family, content type, accounts,
  and account features. Libvirt apply must not duplicate that validation or
  bypass it with local allowlists.
- Plan shape gate: the backend accepts only `ProvisioningPlan`, interprets only
  `RuntimeDomain.PROVISIONING` resources, and reports unsupported resource
  types as diagnostics.
- Manifest/profile layer: any widened content or account support must pass
  `ProvisionerCapabilities`, controlled vocabulary validation, concept binding
  checks, `BackendManifestV2Model`, and provisioning-only conformance.
- Runtime target layer: `RuntimeTarget` remains provisioner-only for libvirt.
  Component presence must continue to match the manifest through
  `_validate_runtime_target_shape()`.
- Backend apply layer: execution through `RuntimeManager` or
  `RuntimeControlPlane` must pass `_call_backend_apply()`, which deep-copies
  snapshots, validates `ApplyResult`, validates snapshot contracts, applies
  SEM-218 disclosure checks when present, and rejects invalid backend output
  without accepting mutated state.
- Control-plane/API/security layer: submitted provisioning flows through
  `RuntimeControlPlane`, `ControlPlaneStore`, operation receipts/statuses,
  idempotency keys, request fingerprints, audit records, and the existing API
  guards/security config when exposed over HTTP. Do not add a separate libvirt
  endpoint or unauthenticated status/readback surface.
- Error-envelope layer: diagnostics may identify ACES addresses and stable
  package-local codes. They must not echo raw plan payloads, XML, exact
  cloud-init data, generated file contents, environment variables, native
  exception text, credentials, private keys, tokens, stdout/stderr dumps, or
  stack traces.
- OS/process exposure layer: prefer libvirt Python APIs and generated XML via
  structured XML builders. If a subprocess leaf is unavoidable, use fixed argv,
  no `shell=True`, bounded timeouts, controlled working directories, no
  secrets in argv or environment, and redacted failures.
- Persistence layer: native address-to-name maps, generated image paths,
  cloud-init paths, and live-daemon readback are private driver state. The
  portable persistence surfaces remain `RuntimeSnapshot`, control-plane
  operation records, and opt-in live-gate archives.

## Extensibility Boundary

The seam for future variation is `create_libvirt_target(**config)` /
`_driver_config()` plus the package-private driver adapter. Parameterize
connection URI, name prefix, workspace, storage pool or image catalog, base
image resolver, cloud-init renderer, network attach/bridge policy, resource
limits, cleanup mode, and timeout there. A future remote libvirt target,
alternate storage pool, UEFI/firmware mode, different cloud-init transport,
or real generic content/account support should not require changes to
`RuntimeManager`, `RuntimeControlPlane`, published schemas, backend profiles,
or processor planning contracts.

## Gotchas And Anti-Patterns

Avoid:

- driving libvirt for `UNCHANGED` operations;
- using native libvirt state as a second planner that rewrites portable
  `ChangeAction` decisions;
- calling `defineXML` unconditionally and relying on libvirt failure behavior
  for idempotence;
- hiding native drift by returning success with a fabricated snapshot entry;
- copying TechVault-specific matrix, probe, initramfs, or live-gate semantics
  into the generic libvirt provisioner;
- treating cloud-init bootstrap as generic content placement support;
- claiming content/account support in the manifest before generic placement
  behavior and snapshot evidence exist;
- putting backend-native identifiers, host paths, XML, bridge names, MACs,
  image paths, cloud-init data, credentials, or exception strings in portable
  artifacts;
- using `RuntimeSnapshot.metadata` or `ApplyResult.details` as a native-state
  ledger;
- adding local schema/profile/vocabulary validators instead of the existing
  contract and concept-authority validators;
- making normal imports require `libvirt`, QEMU, KVM, privileged host access,
  or a running daemon.

## Non-Goals

- Implementing orchestration, evaluation, participant runtime, observation, or
  experiment evidence capture.
- Publishing new SDL authoring fields, contracts, schemas, backend profiles,
  concept families, or a libvirt-specific operation API.
- Redesigning `ProvisioningPlan`, `RuntimeSnapshot`, planner reconciliation,
  `BackendManifest`, runtime target registry, control-plane operation
  envelopes, or SEM-218 realization gates.
- Making default verification depend on a real libvirt daemon, QEMU/KVM,
  privileged host access, or host-local images.
- Certifying behavior beyond the governed provisioning vocabulary. Every
  governed content-placement, account-placement, and feature-binding term is
  realized and tested; only out-of-vocabulary extensions are out of scope.
