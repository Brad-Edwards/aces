# Issue 715 / ASR-519 Guest-Observed Libvirt Probes Preflight

Date: 2026-07-12

Requirement: ASR-519.

This note records architecture guardrails for proving selected libvirt
realization concerns from inside a booted guest. It is guidance only: it does
not add a probe, image, envelope, schema, test, command, or evidence report, and
it is not an implementation plan.

No new ADR is required. ADR-021, ADR-066, ADR-070, and the issue #100 and #714
preflights already own the claim, evidence-plane, realization-envelope, and
configuration-identity boundaries. This note applies them to issue #715.

## Binding Sources

- ADR-021 requires falsification evidence before a realization claim is
  demonstrated. ADR-066 separates operational observation, captured evidence,
  and derived analysis.
- ADR-070, `specs/formal/realization/envelope-semantics.md`, the published
  `realization-envelope-v1` schema, and issue #100 own configuration-specific
  envelope identity and the closed concern/observation-strength taxonomy.
- `specs/formal/realization/explicitness-and-realization.md` and the issue #491
  preflight own SEM-218 exactness and origin provenance. Backend origin is not
  guest observation.
- The issue #603, #604, #606, #714, and #615 preflights own production apply,
  ownership-safe teardown, target conformance, TechVault honesty, and evidence
  boundaries.
- `ProvisioningPlan`, `Realization`, `DomainSpec`, `NetworkSpec`,
  `RealizationObservation`, `DriverResult`, `Diagnostic`, `ApplyResult`,
  `OperationStatus`, and `RuntimeSnapshot` are the incumbent execution and
  error surfaces.
- `aces_operations.libvirt_evidence_run`, `_evidence_run_artifact`,
  `_evidence_run_validation`, `_techvault_cleanup`, `run_artifacts`, and the
  existing libvirt CLI commands are the incumbent proof workflow, validation,
  redaction, cleanup, and persistence surfaces.

## Architecture Decisions And Guardrails

### Select a truthful material configuration

The current `techvault-appliance-v1` configuration deliberately boots a
generated initramfs and rejects concrete images, cloud-init placements,
services, and ACLs. Keep that configuration and its weaker daemon-only claims
intact. It cannot become guest-certified merely by attaching a probe.

A canonical image/appliance proof must select a separately constructible,
versioned material configuration and realization envelope. Its secret-free
configuration identity must cover at least the image/appliance content digest,
architecture, boot/firmware and seed policy, network policy, supported concern
set, guest-observation transport and probe-policy version, and any injected
environment-visible attestation mechanism. Host paths, connection handles,
credentials, and raw probe configuration are not digest input.

Image resolution is target configuration, not new SDL syntax. An authored
source reference must resolve through one closed, configuration-selected image
policy to bytes whose digest is verified before libvirt mutation. A missing,
mutable, mismatched, or unverified image fails before define/create. Do not
overwrite the existing published envelope while retaining its id/digest, and do
not reuse the generic envelope's driver-reported cloud-init claims as
guest-observed proof.

Manifest capability projection, selected envelope, provisioner identity, driver
mode, and evidence binding must all name the same normalized configuration.
Unknown or inconsistent target config continues to fail through
`_validate_config_keys()`, `_selected_driver_mode()`,
`_validate_manifest_mode()`, the envelope loader, and the provisioner's
identity gate.

### Keep one concern inventory and layered observation

Derive the field-addressed concern inventory from the existing
`ProvisioningPlan` -> `Realization` -> `DomainSpec`/`NetworkSpec` path. Probe
selection, comparison, artifact assembly, and mutation tests consume that
inventory; they must not reparse SDL, inspect YAML dictionaries, or maintain a
TechVault-only list of authored fields.

The maximum claim is determined per field, not per domain:

| Claim | Required observation |
| --- | --- |
| Native domain identity/state and attachment | ownership-checked libvirt daemon readback |
| Requested vCPU/memory | exact daemon definition plus bounded guest-visible CPU/memory corroboration |
| Guest network attachment/addressing | daemon attachment correlated with guest link/MAC/IP readback |
| Boot readiness | fresh guest transport response; domain `active` is insufficient |
| Initialization completion | guest-reported completion for the selected initialization mechanism, with no failure state |
| File/directory/dataset content | guest-side type, mode, bounded membership, and expected content digest/value comparison |
| Account properties | guest-side identity, groups, home, shell, disabled/credential posture without returning credential material |
| Feature/service state | concern-specific installed/configured identity and active behavior; a listener alone is insufficient |
| ACL behavior | positive and negative behavior at the declared enforcement boundary, correlated to the affected addresses |

`RealizationObservation` remains the bounded fact carrier and must use
`ObservationStrength.GUEST_OBSERVED` only for a fact actually read at that
boundary. `Diagnostic` remains the failure carrier. Evolve the existing
`NativeLibvirtProbe` injection seam to return typed observations and diagnostics;
do not add a public probe DTO, exception hierarchy, logging-only result, or a
second concern enum. The current boolean/`detail` `ProbeResult` is not an
evidence or error envelope and raw detail must not escape the probe boundary.

Observation proceeds through explicit stages: daemon state, guest transport,
initialization, concern probes, and cleanup. A later stage cannot repair or
upgrade a failed earlier stage. Each stage has a bounded timeout under one
overall deadline. Timeout, partial boot, unavailable transport, initialization
failure, missing/malformed/duplicate observation, unexpected type, and value
mismatch are distinct stable diagnostic codes that name the safe ACES address
and observation level.

### Prove freshness and bind the evidence

A fresh per-run, non-secret challenge must enter the guest through the selected
configuration's disclosed initialization/attestation mechanism and be read back
by the guest observer. The challenge is operational augmentation, not authored
scenario meaning; classify it through the existing SEM-225 augmentation carrier
as environment-visible and comparability-relevant. A prior boot, cached
cloud-init result, old driver snapshot, or response without the current
challenge cannot pass.

Clear run-local observation state before every apply attempt and publish it only
after complete validation. Evidence assembly binds each normalized observation
to the control-plane operation id, ACES operation/address and field path,
concern, selected envelope/configuration digests, image/appliance digest,
observation source and level, UTC observation timestamp, and a `sha256:`
correlation derived from the ownership-verified native identity. Raw UUIDs,
MACs used only for correlation, instance ids, and native names are not portable
identity and do not enter the artifact.

The operation id is joined at the operations/control-plane boundary after
`submit_provisioning()`; do not widen `LibvirtDriver.realize()` merely to pass
control-plane metadata into backend IO. The driver supplies fresh addressed
observations and bounded native correlation material, while the evidence
producer supplies run/operation identity and timestamp. Validation must reject
unjoined, stale, cross-operation, cross-envelope, or duplicate evidence.

### Fail and clean up closed

Production realization still enters through
`RuntimeManager.plan()` -> `RuntimeControlPlane.submit_provisioning()` ->
`LibvirtProvisioner.apply()` -> the injected native driver. A direct driver
call, hand-built `DomainSpec`, pre-existing VM, or fake connection can test a
leaf but cannot satisfy the native-proof gate.

Guest proof is part of commit eligibility for the selected guest-certified
configuration. The provisioner cannot return success, changed addresses, a new
envelope/provenance claim, or a committed snapshot until all required daemon
and guest observations pass. Every failure preserves the baseline portable
snapshot. Unexpected backend output still passes through `_call_backend_apply()`
and the existing result/snapshot/SEM-218 gates.

Cleanup runs in a `finally`-equivalent path after every attempt, including
planning-after-construction errors, timeout, partial boot, guest-probe failure,
artifact-validation failure, and interrupted evidence production. The current
live/evidence flows clean only after a successful captured snapshot; issue #715
must not retain that limitation. Reuse deterministic ACES ownership stamps and
verified absence rules. Verify domains, networks, owned filters, disks/overlays,
seed media, and probe/attestation artifacts. Missing private driver inventory or
lookup uncertainty is not absence. Any residual or unverifiable category makes
the run fail and is reported only as a safe category/count plus ACES address.

### Keep one claim-bearing evidence workflow

Extend the existing `aces.libvirt.scenario-evidence-run/v1` local artifact and
`validate_libvirt_evidence_run_artifact()` source/redaction/binding gates; do not
create a guest-proof schema or a third report assembler. The TechVault live-gate
manifest may remain a bounded operator summary, but it must delegate to or
reference the same validated run result rather than independently decide guest
success. It may never upgrade or omit the canonical artifact's source labels,
failures, binding, or cleanup outcome.

Continue using `run_artifact_path()`, safe run-id validation, canonical JSON,
full pre-write validation, and `atomic_write_json_artifact()`. A failed run may
emit a redacted failure artifact only when the validator admits that shape; it
cannot set `passed=true` or publish realized facts after failed cleanup. The
operator/self-hosted entry point remains under `aces libvirt`; it must retain an
explicit destructive confirmation and return non-zero on any failed stage.

Hermetic fake-driver/probe tests validate orchestration and falsification but
cannot satisfy the native-proof gate. Committed proof must be generated by the
same operator command against a real libvirt/QEMU daemon through the production
apply path, validate before commit, identify the selected envelope/image by
digest, and contain no host-specific or secret material.

## Required Cross-Cutting Reuse

- **SDL and planning:** `parse_sdl_file()`, closed SDL models,
  `instantiate_scenario()`, `SemanticValidator`, `RuntimeManager.plan()`,
  `CompiledRealizationRequirement`, `realization_support_diagnostics()`,
  `realization_disclosure()`, `ProvisioningPlan`, and processor dependency and
  delete ordering.
- **Envelope and manifest:** `BackendRealizationEnvelopeModel`,
  `RealizationConcern`, `ConcernDisposition`, `ObservationStrength`, canonical
  digest helpers, `load_libvirt_realization_envelope()`,
  `backend_manifest_payload()`, `BackendManifestV2Model`, and existing
  capability/manifest consistency checks.
- **Libvirt:** `interpret_provisioning_plan()`, `Realization`, `DomainSpec`,
  `NetworkSpec`, `RealizationObservation`, `DriverResult`,
  `TechVaultNativeLibvirtDriver`, structured XML builders, private seed
  workspace safeguards, deterministic ownership UUIDs, safe absence detection,
  and current rollback/cleanup helpers.
- **Runtime, errors, and persistence:** `RuntimeControlPlane`,
  `_call_backend_diagnostics()`, `_call_backend_apply()`, `Diagnostic`,
  `Severity`, `OperationReceipt`, `OperationStatus`, `ApplyResult`,
  `RuntimeSnapshot`, realization provenance/envelope carriers,
  `ControlPlaneStore`, atomic store writes, and audit events.
- **Evidence and workflow:** `libvirt_evidence_run`,
  `validate_libvirt_evidence_run_artifact()`, `redaction_violations()`,
  `cleanup_native_snapshot()`, `run_artifact_path()`,
  `atomic_write_json_artifact()`, the existing libvirt CLI group, and
  `run_target_conformance()` for backend-neutral conformance.
- **Contract governance:** if the published envelope carrier changes, update
  the hand-governed schema, model/generator parity, valid/invalid fixtures,
  `contracts/schema-publication-manifest.json`, packaged corpus, and
  `specs/authority/authority-boundary.yaml`. Evolve the shared contract only
  when its current closed fields cannot express a portable fact.

## Security And Whole-Path Gates

- **Input and shape:** scenario input passes the parser, closed Pydantic shapes,
  semantic validator, compiler/planner, plan model, envelope relation/identity,
  provisioner capability and concern gates, then observation completeness/value
  validation. Unknown input or unsupported concerns fail before IO; probes do
  not parse authored SDL.
- **Target/config:** all driver mode, image policy, probe transport/policy,
  timeouts, and augmentation choices pass one extended `_validate_config_keys()`
  and normalized target configuration before manifest construction. Library
  callers receive the same validation as Typer callers. Image bytes and probe
  policy are digest-bound; paths, handles, and credentials are not serialized.
- **Authentication/authorization:** no new HTTP route is required. In-process
  operator execution retains explicit confirmation. If provisioning is exposed
  through HTTP, it keeps `ControlPlaneSecurityConfig.strict_defaults()`, verified
  bearer/proxy identity, backend/operator roles, target scope after either auth
  mechanism, request-size limits, idempotency fingerprints, and audit events.
  Guest-probe capability does not grant a caller general guest command execution.
- **Secrets:** connection URIs with user information, passwords, tokens, private
  keys, cloud-init bodies, account material, probe credentials, environment
  dumps, and connector/transport reprs never enter CLI argv, digests,
  diagnostics, audit details, snapshots, fixtures, artifacts, or command output.
  Prefer a libvirt guest-agent or equivalent injected transport that needs no
  guest credential. Any later SSH transport must use an injected credential
  handle, strict host identity verification, and bounded allowlisted operations;
  accepting a password/key CLI option is forbidden.
- **Guest/host OS exposure:** attach only the selected, disclosed guest channel;
  it is not a generic remote shell surface. Probe requests are fixed,
  concern-specific, read-only, size-bounded, and allowlisted. Parse bounded
  structured output and discard raw stdout/stderr. If a subprocess leaf is
  unavoidable, use fixed argv, no `shell=True`, bounded timeouts, controlled
  cwd/environment, and no secret argv or environment entries. Keep libvirt
  imports lazy and generated secret-bearing seed files under the existing
  ownership/symlink/mode protections.
- **Errors/logging:** public failure data is a stable package-local diagnostic
  code, safe address, observation level, and generic message. Do not propagate
  `ProbeResult.detail`, `str(exc)`, raw agent replies, XML, command output,
  paths, native ids, or tracebacks through `_backend_call_failed()`, CLI output,
  logs, audit, or evidence. Operational logging is supplemental; it cannot be
  the only failure or evidence channel.
- **Persistence/evidence:** runtime snapshots and operation records retain only
  portable ACES state and typed envelope/provenance. Guest facts belong in the
  validated evidence artifact, not `RuntimeSnapshot.metadata`,
  `ApplyResult.details`, or a private observation database. The shared redaction
  gate and artifact validator run before atomic persistence.
- **Cleanup:** the host layer verifies owned native objects and every run-local
  artifact category after success and failure. It neither scans/deletes by name
  prefix nor treats all lookup exceptions as absence. Residual state prevents a
  passing operation/report.

## Extensibility Seam

The seam is the normalized material target configuration selecting a versioned
envelope plus the existing injected `NativeLibvirtProbe`/driver boundary. The
observer is parameterized by the canonical concern inventory, safe ACES
address/field path, per-stage/overall deadlines, selected probe-policy version,
and envelope identity, and returns only `RealizationObservation` and
`Diagnostic` values.

A second image family, architecture, initialization system, libvirt guest-agent
implementation, or credential-free transport adds a configuration/envelope
variant and observer implementation. It must not require changes to SDL syntax,
the concern enum, planner actions, runtime control-plane route, error hierarchy,
store, report writer, or evidence-source taxonomy.

## Falsification Guardrails And Gotchas

- Mutations must cover false handles, inactive/wrong domains, CPU or memory
  mismatch, wrong NIC/MAC/IP, missing current challenge, stale prior snapshot,
  partial boot, guest transport timeout/unavailability, omitted or failed
  initialization, missing/duplicate/type-coerced facts, wrong content digest,
  wrong account properties, synthesized/wrong service identity, ACL positive or
  negative mismatch, envelope/image/probe-policy mismatch, and incomplete
  cleanup.
- Every failed mutation asserts a failed `OperationStatus`, empty
  `changed_addresses`, unchanged in-memory and persisted baseline snapshots, no
  new realization provenance/envelope claim, no passing evidence artifact, and
  verified cleanup or a redacted residual-state failure.
- Do not equate active domain, ping, TCP connect, guest-agent availability,
  cloud-init `done`, package presence, process presence, or a seed descriptor
  with all nested concerns. Each is evidence only for its exact named fact.
- Do not compare authored/planned data with an echo written into the guest and
  call that independent observation. The probe must read the realized system or
  exercise behavior at the enforcement boundary; the per-run challenge proves
  freshness, not concern correctness.
- Do not expose a generic command runner, accept probe commands from SDL, infer
  checks from service names, duplicate the concern inventory, or make raw probe
  output part of the evidence schema.
- Do not let a fake driver/probe, direct driver call, hand-built spec,
  pre-existing guest, skipped cleanup, or self-skipping integration test produce
  the committed native proof.
- Do not broaden the default hermetic verification graph to require libvirt,
  QEMU/KVM, privileges, a host image, network access, or credentials. The
  self-hosted proof is an explicit separate gate.

## Non-Goals And Implementation Boundaries

- No implementation of issue #715 in this preflight.
- No new SDL syntax, universal image registry, backend profile, capability
  language, public probe DTO/schema, control-plane route, exception hierarchy,
  persistence service, observation database, or parallel report format.
- No general-purpose guest management/remote-execution API and no participant
  observation capability claim. Backend guest realization evidence remains
  operational/captured evidence unless a separate governed participant boundary
  projects it.
- No claim that one canonical guest proves all images, operating systems,
  services, ACL mechanisms, TechVault applications, SOC detection quality,
  backend equivalence, or envelope subsumption.
- No issue #716 honesty-conformance runner or issue #717 final scenario
  certification. Issue #715 supplies concern-specific observations that those
  downstream gates may consume.
