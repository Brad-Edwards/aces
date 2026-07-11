# Issue 714 / ASR-519 TechVault Realization Disclosure Preflight

Date: 2026-07-11

Requirement: ASR-519.

This note records architecture guardrails for making the generated TechVault
libvirt appliance path truthful at validation, execution, observation, and
evidence boundaries. It is guidance only: it does not implement issue #714,
change a schema, alter an envelope, add a probe, or define an implementation
plan.

## Binding Sources

- ADR-070, `specs/formal/realization/envelope-semantics.md`, and the issue #100
  preflight own configuration-bound realization-envelope identity, the shared
  concern/disposition/observation vocabulary, and exact/constrained/open set
  semantics.
- `specs/formal/realization/explicitness-and-realization.md` and the issue #491
  preflight own SEM-218 non-approximation and author/processor/backend origin
  provenance. Origin provenance is not observation strength.
- ADR-066 and `specs/formal/observability-evidence-plane.md` separate authored,
  operational-observability, captured-evidence, and derived-analysis facts.
- ADR-021 forbids promoting an internally coherent or positive-path result into
  a demonstrated realization claim without falsification evidence.
- ADR-004 and ADR-036 keep planning, runtime execution/persistence, portable
  contracts, concrete backend IO, and operational artifact production in their
  existing packages.
- The issue #603, #604, and #606 preflights own libvirt interpretation,
  reconciliation/teardown, and backend-neutral conformance boundaries.
- `BackendRealizationEnvelopeModel`, `RealizationEnvelopeIdentityModel`,
  `ProvisioningPlan`, `Realization`, `DomainSpec`, `NetworkSpec`, `DriverResult`,
  `ApplyResult`, `RuntimeSnapshot`, `Diagnostic`, and `OperationStatus` are the
  incumbent contract and error surfaces.

## Architectural Diagnosis

The current path has two independent truth gaps that must not be confused.

1. `LibvirtProvisioner._reconcile_snapshot()` copies plan payloads into
   `SnapshotEntry`. `realization_disclosure()` can therefore compare an authored
   value with a planned payload echo even when the native driver ignored that
   value. The snapshot is reconciliation state; payload equality is not native
   observation.
2. `TechVaultNativeLibvirtDriver.last_snapshot` is derived from
   `_native_matrix()`, not from libvirt or guest readback. `expected_surface()`
   and `native_soc_readback()` then derive claims from that matrix. A non-empty
   domain list proves, at most, that the driver reported substrate handles; it
   does not prove the requested image, resources, services, accounts, content,
   features, ACLs, or guest network state.

Concrete known relaxations include resource clamping, generated-appliance image
substitution, invalid/missing network defaults, synthesized health services,
discarded `cloud_init` and ACL intent, and domain-level handles standing in for
placement-level realization. The static TechVault envelope discloses several of
these limitations, but a transformation label such as `bounded-normalization`
is disclosure, not executable authorization to weaken an exact plan value.

Material target identity is also incomplete if behavior-changing injected
values such as the initramfs builder, kernel/image policy, `define_only`, or a
resource override can vary while only `driver_mode=techvault-appliance` selects
the fixed configuration digest. A live claim must bind the actual material
configuration, not merely the driver class name.

## Architecture Decisions And Guardrails

### Keep fact classes separate

Every claim-bearing artifact must preserve these classes explicitly:

| Fact class | Canonical source | Maximum claim without another source |
| --- | --- | --- |
| Authored | parsed and validated SDL | author requested it |
| Planned | `ProvisioningPlan`, `Realization`, `DomainSpec`, `NetworkSpec` | processor/backend intends to apply it |
| Driver-reported | `DriverResult` and bounded driver receipts | driver says an operation completed |
| Daemon-observed | post-mutation libvirt readback | libvirt reports a native definition/state |
| Guest-observed | concern-specific guest probe | guest reports the concern inside the VM |
| Derived analysis | evidence/artifact computation over named inputs | stated inference only |

No presence test, success flag, handle, snapshot entry, compiled model, or
planned matrix may promote a fact to a stronger class. In particular,
`ExplicitnessProvenance.BACKEND_REALIZED` says who chose a value; it does not mean
`daemon-observed` or `guest-observed`.

### Account for every non-UNCHANGED operation

- Derive one canonical, field-addressed concern inventory from the existing
  `ProvisioningPlan` -> `Realization` interpretation. Validation, driver
  accounting, evidence assembly, and mutation tests must consume that inventory;
  they must not maintain separate lists of fields.
- Keep the existing realization-envelope concern taxonomy. Extend that taxonomy
  in place for node service declarations rather than folding services into
  `feature-binding` or adding a TechVault-local vocabulary. Cloud-init is a
  mechanism for account/content/feature delivery, not a separate authored
  concern and not proof that any of those concerns took effect.
- Every `CREATE` or `UPDATE` concern is either realized with an allowed
  transformation and a named observation source, rejected as unsupported before
  native mutation, or failed with a structured diagnostic. A resource-level
  `DomainHandle` cannot satisfy its nested concerns.
- `DELETE` is accounted for by ownership-checked, daemon-observed absence of the
  native object and cleanup of its owned artifacts. `UNCHANGED` remains a strict
  no-driver-call operation and creates no fresh observation claim.
- Descriptor production, seed attachment, and port reachability must not satisfy
  the stronger content, account, feature, service-identity, or application-state
  concern they describe or transport.

### Exact values are honored or rejected

- Treat every concrete value in a directly submitted `ProvisioningPlan` as
  binding at the backend boundary. Direct control-plane submission cannot rely
  on compiler-only explicitness metadata being present.
- SEM-218 exact values may not be clamped, rounded, defaulted, substituted,
  normalized to a different value, or omitted. The TechVault path must honor the
  exact value or reject the plan before connection, cleanup, artifact creation,
  `defineXML`, `networkDefineXML`, `create`, `destroy`, or `undefine`.
- A constrained/open concern may be transformed only when the selected envelope
  admits the input and output and names the transformation. Record
  backend-realized origin and the actual observation strength. The current
  transformation-name list is not a free-form policy language and must not be
  interpreted as permission to clamp an exact request.
- If no executable, governed transformation rule exists, use exact-or-reject.
  Issue #714 must not add an ad hoc TechVault transformation language merely to
  preserve today's positive-path demonstrations.
- Validate the whole plan before any native mutation. Unsupported account,
  content, feature, ACL, service, image, resource, or network-property concerns
  must produce addressed diagnostics together; do not mutate the supported
  subset and then discover the rest.

### Observe native state independently of planned state

- Driver handles remain completion receipts, not evidence. Successful native
  creation must be followed by typed, source-labelled readback for every concern
  the issue claims as realized.
- Libvirt readback may support substrate existence, ownership, configured
  architecture/image attachment, vCPU/memory definition, native network
  definition, and domain/network attachment claims. Record only bounded,
  portable comparisons; never publish raw XML, native object reprs, paths, UUIDs,
  or connection data.
- Guest-applied IP configuration, cloud-init execution, accounts, placed content,
  feature behavior, ACL effect inside the guest, and named service/application
  identity require concern-specific guest evidence. Until issue #715 supplies
  that evidence, issue #714 must classify them as unsupported/not observed and
  reject binding requests, or narrow the emitted claim to the weaker substrate
  fact actually observed.
- Opening a BusyBox HTTP listener on a requested port is not realization of
  Wazuh, TheHive, MISP, PostgreSQL, SSH, DNS, or another named service. Likewise,
  `native_soc_readback()` values synthesized from node names are derived test
  data, not native SOC readback.
- A synthesized health listener is environment-visible augmentation. Remove it
  or disclose it through the existing SEM-225 augmentation carrier with its
  environment/comparability effects; do not hide it as a default service.

### Commit and rollback stay fail-closed

- `LibvirtProvisioner` may return success only after complete concern accounting
  and required readback. `_call_backend_apply()` remains the runtime contract
  backstop, not the component responsible for undoing an already dishonest
  native success.
- Preserve the current deep-copied baseline snapshot on every validation,
  driver, readback, contract, or cleanup failure. Failed results carry no changed
  addresses and never attach a new envelope or provenance claim.
- The general runtime contract currently permits some non-libvirt backends to
  return partial snapshots on failure, and the control plane persists whatever
  `ApplyResult.snapshot` it receives. Issue #714 imposes a stricter TechVault
  provisioner invariant: it must return the baseline snapshot itself. Do not
  broaden or reinterpret unrelated workflow partial-failure semantics here.
- Track pre-existing owned objects separately from objects created by this call.
  Compensate in reverse dependency order and verify the result through native
  readback. A failed update must restore the prior definition or report the
  affected ACES addresses as residual native state; preserving only the portable
  snapshot is not rollback.
- Prefix-wide `clean_existing` deletion is not ownership proof and may not run as
  a preflight shortcut. Reuse deterministic ACES ownership stamps and the
  absence-vs-lookup-failure rules from `LibvirtDeploymentDriver`.
- Cleanup failure is a failed operation, not a warning. Diagnostics may name
  safe ACES addresses and whether residual state remains; they must not dump the
  residual XML or host paths.

### Publish truthful evidence, not a renamed plan

- Keep the local `aces.libvirt.scenario-evidence-run/v1` artifact and its
  validator as the issue's evidence carrier; do not invent a second report
  schema. Separate authored, planned, driver-reported, daemon-observed,
  guest-observed, and derived sections in that artifact.
- A `native-live` basis requires the corresponding observed facts. A non-empty
  `last_snapshot`, `realized_addresses`, domain list, or `expected_surface()` is
  insufficient. Compiled node/service/network fields remain `planned` even when
  some native substrate exists.
- Embed the canonical backend manifest identity and selected realization-envelope
  identity, including configuration and envelope digests. Bind observations to
  the concrete driver/backend version and secret-free material configuration.
- Keep the deterministic participant runtime explicitly labelled as deterministic
  control-plane execution with no live guest execution. Native provisioning does
  not upgrade its participant proof.
- The TechVault live-gate manifest and downstream cross-backend corpus must
  preserve the same source labels. No downstream summary may upgrade a weaker
  source discarded by its input artifact.
- Continue validating the full artifact before atomic write. Failed or residual
  runs may be retained as failed evidence, but never with `passed=true` or a
  realized basis.

## Required Cross-Cutting Reuse

- SDL ingress and semantic validation: `parse_sdl()` / `parse_sdl_file()`, closed
  SDL models, `instantiate_scenario()`, `SemanticValidator`, and existing parse,
  instantiation, and semantic error types.
- Planning and exactness: `CompiledRealizationRequirement`,
  `realization_support_diagnostics()`, `realization_disclosure()`,
  `ProvisioningPlan`, `ChangeAction`, and processor dependency/delete ordering.
- Envelope authority: `BackendRealizationEnvelopeModel`,
  `RealizationConcern`, `ConcernDisposition`, `TransformationKind`,
  `ObservationStrength`, `load_libvirt_realization_envelope()`, and the canonical
  digest helpers. Keep coarse `ProvisionerCapabilities` and
  `capability_envelope_diagnostics()` as separate necessary gates.
- Libvirt interpretation and IO: `interpret_provisioning_plan()`, `Realization`,
  `DomainSpec`, `NetworkSpec`, `LibvirtDriver`, `DriverResult`, the structured XML
  builders, deterministic ownership UUIDs, safe absence detection, and rollback
  precedents in `LibvirtDeploymentDriver`.
- Runtime execution and persistence: `RuntimeManager`, `RuntimeControlPlane`,
  `_call_backend_diagnostics()`, `_call_backend_apply()`, `ApplyResult`,
  `RuntimeSnapshot`, `realization_provenance`, `realization_envelope`,
  `ControlPlaneStore`, and atomic local-store writes.
- Error and operational observability: `Diagnostic`, `Severity`,
  `OperationReceipt`, `OperationStatus`, control-plane audit events, and stable
  package-local diagnostic codes. There is no need for a TechVault exception
  hierarchy or logging-only result channel.
- Evidence and conformance: `BackendManifestV2Model`,
  `ExperimentRealizedFormDisclosureModel`, SEM-225 augmentation disclosures,
  `run_target_conformance()`, `BackendConformanceReport`,
  `validate_libvirt_evidence_run_artifact()`, `redaction_violations()`,
  `run_artifact_path()`, and `atomic_write_json_artifact()`.
- Schema authority, if the existing envelope concern taxonomy or runtime carrier
  changes: the hand-governed schema, `schema_bundle()`, valid/invalid fixtures,
  `contracts/schema-publication-manifest.json`, ADR-061 compatibility evidence,
  packaged corpus, and `specs/authority/authority-boundary.yaml`. Evolve the
  existing contract; do not publish a libvirt-only duplicate.

## Security And Whole-Path Gates

- **SDL/plan shape:** authored input passes the existing parser, closed models,
  semantic validator, compiler/planner checks, closed `ProvisioningPlanModel`,
  envelope identity validation, and libvirt capability/value gates. Unknown or
  unsupported fields fail before IO; no backend-local SDL parser is added.
- **Target/config shape:** reuse `_validate_config_keys()`,
  `_selected_driver_mode()`, `_validate_manifest_mode()`, the envelope loader,
  and canonical configuration digest. Replace clamping/coercion in direct Python
  entry points with validation; Typer option bounds alone do not protect library
  callers. Material builder/kernel/image/resource/define mode affects identity or
  is rejected in claim-bearing mode. Operational handles and secrets stay out of
  the digest.
- **Authentication/authorization:** issue #714 needs no HTTP route. If a changed
  snapshot or operation field crosses HTTP, it retains
  `ControlPlaneSecurityConfig.strict_defaults()`, bearer/proxy verification,
  backend/operator role checks, target scope, request-size limits, idempotency
  fingerprints, and audit events. The current bearer-token branch returns before
  the proxy branch's `identity.target_name` check; any issue #714 HTTP exposure
  must enforce target scope after either authentication mechanism rather than
  relying on that incumbent bug. The local destructive CLI retains explicit
  operator confirmation; neither path grants host privileges.
- **Secrets:** credential-bearing libvirt URIs are forbidden in CLI argv and are
  rejected rather than logged. Use a non-secret URI plus injected connection or
  credential handle. SSH keys, account material, cloud-init bodies, generated
  initramfs contents, connector reprs, environment dumps, and raw configuration
  never enter digests, diagnostics, snapshots, audit details, fixtures, reports,
  or command output.
- **Host files/processes:** reuse the generic seed workspace's ownership,
  symlink, and permission rules if sensitive guest material is ever generated.
  Do not place it in the current world-readable appliance metadata/HTML path.
  Keep libvirt imports lazy, use structured XML, fixed argv, no `shell=True`,
  bounded timeouts, controlled working directories, and no secrets in argv or
  subprocess environments. No `sudo`, setcap, ambient capability, or daemon
  inventory requirement belongs in the hermetic suite.
- **Error envelopes:** plan/config failures use safe addressed `Diagnostic`
  values. Native exception strings, XML, stdout/stderr, probe output, paths,
  object reprs, and stack traces do not cross the boundary. The existing
  `_backend_call_failed()` and live/evidence `str(exc)` paths are unsafe for
  secret-bearing configuration errors; avoid raising such values into them and
  harden them if touched.
- **Persistence/API serialization:** the baseline snapshot remains byte-for-byte
  equivalent on failure. Existing typed realization provenance and envelope
  identity must round-trip through `ControlPlaneStore`,
  `RuntimeSnapshotEnvelopeModel`, and `_snapshot_model()`; note that the current
  HTTP serializer omits `realization_provenance`, so any claim depending on that
  ledger must close this cross-boundary loss. Do not use `RuntimeSnapshot.metadata`
  or `ApplyResult.details` as a native-state/evidence ledger.
- **Evidence output:** run ids pass the existing safe-label and root-confinement
  helpers; artifacts pass embedded-contract, source-separation, boundary, and
  redaction validation before atomic write. Host paths, connection URIs, native
  UUIDs/XML, QEMU command lines, credentials, and private keys stay forbidden.

## Whole-Repository Surfaces In Scope

- Canonical contracts and policy: the TechVault realization envelope,
  `realization-envelope-v1`, `backend-manifest-v2`, `provisioning-plan-v1`,
  `runtime-snapshot-v1`, schema publication/authority manifests, and backend
  provisioning-only profile.
- Backend/runtime path: `aces_backend_libvirt.realization`, `capability_envelope`,
  `driver`, `drivers.libvirt`, `techvault_appliance`, `techvault_native`,
  `techvault_probe`, `provisioner`, `manifest`, `target`,
  `aces_runtime.backend_calls`, control-plane execution/API serializers, and
  control-plane stores.
- Evidence path: `aces_operations.techvault_live`,
  `libvirt_evidence_run`, `_evidence_run_artifact`,
  `_evidence_run_validation`, cross-backend corpus projection/validation, and the
  libvirt CLI presentation.
- Verification path: realization-envelope, manifest, provisioner, native driver,
  evidence-run, runtime snapshot/API/store, target conformance, authority, and
  real-libvirt opt-in suites; repository policy and full verification remain the
  final mechanical gates.

## Conformance And Falsification Guardrails

- Reuse the injected/recording `LibvirtDriver` and fake-connection patterns. Do
  not certify by monkeypatching the gate under test, inspecting source strings,
  or calling `_native_matrix()` directly.
- Mutation cases must include a driver that drops cloud-init, ignores an account,
  omits content, clamps resources, substitutes an image, and fabricates a
  realized handle. Unsupported TechVault concerns should be rejected before the
  mutation driver is called; supported concerns must fail when independent
  readback does not match the request. A plausible handle alone must never pass.
- Also exercise service synthesis/omission, ACL omission, network defaulting,
  stale or mismatched envelope/configuration identity, partial create, failed
  update restoration, rollback failure, and residual-state reporting. These are
  distinct failure modes and must not collapse into one happy-path handle test.
- Every rejection asserts: no pre-admission native call; failed operation status;
  empty `changed_addresses`; prior in-memory and persisted snapshots unchanged;
  no new realization provenance/envelope claim; and either verified native
  cleanup or a safe residual-state diagnostic naming the affected ACES address.
- Artifact mutations must relabel planned or driver-reported data as
  daemon/guest-observed, infer realization from a non-empty domain list, replace
  the bound envelope/configuration identity, or inject forbidden host/secret
  material. The existing artifact validator must reject every mutation before
  atomic write.
- Keep `run_target_conformance()` as the backend-neutral target/profile runner.
  Libvirt-specific mutation coverage belongs at the existing driver,
  provisioner, evidence-validator, and target-integration seams, not in a
  libvirt branch inside `aces_conformance`.
- The default suite remains hermetic. Real-libvirt evidence is opt-in,
  reproducible, source-labelled, and must verify complete cleanup even when the
  realization or probe fails.

## Extensibility Seam

The seam is one canonical concern inventory plus a source-specific observer
passed through the existing target/driver configuration boundary. The observer
is parameterized by ACES address/field path, concern, selected envelope identity,
and observation source; it returns bounded typed facts, not raw backend objects.

Issue #714 supplies validation and daemon-level accounting for the bounded
TechVault appliance. Issue #715 can add guest observers for the same concern
inventory without changing SDL syntax, plan interpretation, diagnostic
hierarchy, control-plane workflow, or evidence taxonomy. A future appliance,
kernel/image policy, remote libvirt configuration, or stronger probe selects a
different normalized material configuration/envelope identity rather than
editing global planner or artifact rules.

## Gotchas And Anti-Patterns

Avoid:

- treating `SnapshotEntry.payload`, `status="applied"`, `changed_addresses`, a
  handle, domain existence, or a non-empty driver matrix as native observation;
- comparing an authored value with the same planned payload twice and calling
  the second copy backend evidence;
- using `last_snapshot`, `last_matrix`, `realized_addresses()`,
  `expected_surface()`, or name-derived SOC counts as the evidence authority;
- allowing `bounded-normalization`, `default-substitution`, or
  `image-substitution` to weaken an exact request;
- silently accepting accounts/content/features/ACLs/services because they were
  aggregated into a `DomainSpec` the TechVault driver then ignores;
- calling a generic HTTP listener the requested named service or calling seed
  creation guest application;
- inferring guest IP state from a planned DHCP allocation or daemon network XML;
- overloading SEM-218 origin provenance with observation strength, or using the
  SEM-225 augmentation carrier as a substitute for realization evidence;
- adding a second concern enum, plan payload extractor, schema registry,
  validation stack, exception hierarchy, store, endpoint, or report writer;
- binding claims only to a driver class/mode while injected material behavior can
  vary under the same configuration digest;
- deleting resources by prefix, treating every lookup error as absence, or
  reporting rollback success without post-cleanup readback;
- relying on the general runtime's permissive partial-failure snapshot behavior
  for the stricter issue #714 baseline-preservation contract;
- assuming bearer authentication currently enforces target scope;
- preserving the portable snapshot while hiding known residual native state;
- echoing raw exceptions, XML, stdout/stderr, host paths, connection URIs,
  account/cloud-init material, or probe details in diagnostics or artifacts;
- weakening assertions or relabelling current tests merely to keep the existing
  TechVault positive path green.

## Non-Goals And Implementation Boundaries

- No implementation of issue #714 in this preflight.
- No new SDL syntax, backend profile, control-plane route, persistence service,
  libvirt-specific public DTO, exception hierarchy, or parallel report schema.
- No implementation of real TechVault/Wazuh/TheHive/MISP/application services,
  generic cloud-init delivery, accounts, content, features, ACLs, or guest
  configuration. Unsupported concerns are rejected and disclosed honestly.
- No guest-observed certification; issue #715 owns guest probes. Issue #714 may
  only emit daemon/driver strengths it actually proves.
- No claim that the deterministic participant adapter executes inside live
  guests, and no coupling of participant-runtime success to substrate success.
- No final real-libvirt scenario certification or backend-equivalence claim;
  issues #716 and #717 own broader conformance and final evidence.
- No compatibility fallback that accepts missing concern accounting, stale or
  mismatched envelope/configuration identity, or failed cleanup as success.
