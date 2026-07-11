# Issue 100 / ASR-519 Libvirt Realization Envelope Preflight

Date: 2026-07-11

Requirement: ASR-519.

This note records architecture guardrails for publishing configuration-bound
libvirt realization envelopes. It is guidance only: it does not publish an
envelope, change a contract, select a target, alter planning/apply behavior, or
define an implementation plan.

## Binding Sources

- ADR-070 and `specs/formal/realization/envelope-semantics.md` own the
  `RealizationEnvelopeModel` language and the shared `member()`, `subsumes()`,
  `witness()`, and `generate_negative_probes()` semantics.
- `docs/decisions/issue-667-realization-envelope-preflight.md` and
  `docs/decisions/issue-668-envelope-relation-preflight.md` prohibit a second
  capability language or backend-local set relation.
- `docs/decisions/issue-602-libvirt-backend-manifest-preflight.md` and
  `docs/decisions/issue-605-libvirt-envelope-diagnostics-preflight.md` own the
  coarse manifest-capability and concrete plan-term gates. Those gates remain
  necessary but are not value-level realization envelopes.
- `create_libvirt_manifest()`, `create_libvirt_components()`,
  `create_libvirt_target()`, `_driver_config()`, `LibvirtProvisioner`,
  `LibvirtDeploymentDriver`, and `TechVaultNativeLibvirtDriver` are the current
  configuration and execution seams.
- `BackendManifest`, `backend_manifest_payload()`, `ExecutionPlan`,
  `ProvisioningPlan`, `RuntimeSnapshot`, `RuntimeManager`,
  `RuntimeControlPlane`, and `_call_backend_apply()` are the existing carriage,
  provenance, persistence, and fail-closed execution path.
- ADR-009, ADR-019, ADR-061, `ContractModel`, `schema_bundle()`,
  `contracts/schema-publication-manifest.json`, and `aces_contracts.corpus` own
  publication and packaged-corpus authority.

## Architecture Decisions And Guardrails

- Publish exactly one authoritative `realization-envelope/v1` artifact for
  each constructible **material** libvirt configuration. The initial modes are
  generic qcow2/cloud-init and the generated TechVault appliance. They must not
  share an envelope where their behavior differs.
- Keep `RealizationEnvelopeModel` as the denotational scenario-set expression
  inside the published artifact. Planning must call the shared relation:
  concrete instantiated scenarios use `member()`; a future requested envelope
  uses `subsumes(offered, requested)`. Do not duplicate path/domain logic in the
  libvirt package, planner, manifest validator, or conformance runner.
- The issue's required realization and observation disclosures are not all SDL
  value domains. Architecture, placement mechanism, transformation policy, ACL
  enforcement, and observation strength are backend-behavior claims. The
  published envelope artifact must be one closed carrier containing the
  existing set expression plus closed, typed per-concern disclosures under the
  same identity. This is the schema-governed carrier anticipated by ADR-070 R7,
  not a second set language. Do not misrepresent disclosures as navigable SDL
  paths or create a libvirt-only envelope schema.
- Keep three taxonomies distinct: envelope posture (`open`, `constrained`,
  `exact`), SEM-218 authored explicitness/provenance, and evidence source or
  observation strength (`authored`, `planned`, `driver-reported`,
  `daemon-observed`, `guest-observed`). The last is not
  `ExplicitnessProvenance` and must not be inferred from snapshot presence.
- Give the selected envelope one immutable identity value containing contract
  id, envelope id, envelope schema version, and canonical `sha256:` content
  digest. Bind it to the normalized material configuration identity: driver
  mode plus a digest of an allowlisted, secret-free semantic configuration
  projection. Reuse the repository's existing ref/digest validation conventions;
  do not compare mutable object identity, paths, summaries, or prose.
- Canonical digest input is the closed JSON contract payload with stable key
  ordering and the self-digest field excluded. The implementation must have one
  digest helper and one identity validator. A digest of raw configuration is
  forbidden: credentials and other low-entropy secrets remain vulnerable to
  offline guessing even when hashed.
- Normalize target configuration once at the factory boundary and pass the same
  closed value to manifest selection, component construction, and driver
  construction. Unknown fields, invalid combinations, and a driver whose
  declared mode does not match the selected envelope fail target construction.
  Do not infer mode by `isinstance`, callable name, successful driver behavior,
  or host probing; injected test/live drivers must declare the mode explicitly.
- Classify configuration fields deliberately. Driver mode, image/source policy,
  architecture, resource bounds, network policy, seed/appliance behavior, and
  any realization-affecting toggle are material. Connection handles, URI
  credentials, workspace paths, name prefixes, cleanup, timeouts, and injected
  connector objects are operational/private unless they change the claim; if
  one does change realizability, it must be represented by a safe governed ref
  or construction must fail. `participant_runtime=True` changes a separate
  runtime surface and must not silently change the provisioning envelope.
- Carry the selected identity through the existing contracts. The backend
  manifest advertises the selected envelope; the planner copies that identity
  to the provisioning plan; the libvirt provisioner is constructed with the
  same expected identity; and a successful runtime snapshot records it in a
  typed field. Do not use `constraints`, plan operation payloads,
  `RuntimeSnapshot.metadata`, `ApplyResult.details`, tags, or audit blobs.
- `ExecutionPlan.manifest` equality and `RuntimeManager._provenance_diagnostics()`
  remain a defense, but are not sufficient because published
  `ProvisioningPlan` values can enter through `RuntimeControlPlane` directly.
  `LibvirtProvisioner.validate()` and `apply()` must both reject missing, stale,
  mismatched, malformed, or unverifiable identity before interpretation,
  snapshot reconciliation, `driver.realize()`, or `driver.destroy()`.
- A non-empty baseline snapshot bound to another envelope/configuration is also
  a mismatch. Changing material target configuration requires a new plan under
  the new identity; it must not silently relabel existing state.
- Keep `ProvisionerCapabilities` and `realization_support` as coarse incumbent
  gates. Mechanically check both directions that matter: every selected
  envelope concern is permitted by the manifest's coarse kind/capability
  surface, and every governed term claimed by the coarse manifest occurs in at
  least one selectable envelope. The selected envelope, not the union
  capability set, is the value-level admission authority.
- Keep one canonical declaration of selectable envelope content and derive or
  validate manifest projections from it. Do not preserve
  `LIBVIRT_PROVISIONER_CAPABILITIES`, a new envelope allowlist, and driver-local
  term tables as three independent truths.
- Every non-`UNCHANGED` plan operation must remain accounted for by existing
  portable surfaces: its address is changed/observed-realized, or an addressed
  typed diagnostic marks it unsupported/failed. A successful operation may not
  disappear from `changed_addresses` or the snapshot merely because the driver
  aggregates work at domain level.

## Truthful Initial Mode Boundaries

- Generic qcow2/cloud-init is x86_64 in current XML. Image `Source.version` is
  currently dropped, host image existence is not proven during planning, and a
  successful libvirt call is not guest boot or guest configuration evidence.
  The envelope must narrow image/OS claims or require an explicit governed image
  policy; it must not advertise all OS families merely because dialect code can
  emit commands.
- Generic resource translation currently rounds/clamps RAM, supplies default
  RAM/CPU values, and normalizes service protocol. Those are transformations,
  not exact realization. They must be admitted and disclosed for constrained or
  open concerns, or rejected before driver IO; exact declarations may never be
  silently transformed.
- Generic `file` placement has a direct `write_files` mechanism. Dataset and
  directory placement currently write descriptors/commands rather than proving
  the named data or directory contents exist. Likewise, some OS dialects record
  feature/mail descriptors instead of realizing the native concern. Envelope
  claims must distinguish descriptor disclosure from concern realization.
- Generic ACL translation is fail-closed through `realize_node_acls()` and
  libvirt nwfilter generation, but a successful define is daemon/substrate
  evidence only. Guest-facing enforcement strength requires separate evidence.
- TechVault appliance mode always boots a generated x86_64 Linux/BusyBox
  initramfs, ignores the scenario image as the boot artifact, clamps memory to
  64-128 MiB and vCPUs to 1-2, may synthesize a health service, and does not
  consume the generic cloud-init account/content/feature or nwfilter surfaces.
  Its envelope must reject or explicitly disclose each difference. It must not
  inherit the generic mode's broad provisioner claims.
- `DomainHandle`, `NetworkHandle`, and normal `RuntimeSnapshot` entries are
  driver-reported/planned substrate facts. Neither mode may label them
  `daemon-observed` without native readback or `guest-observed` without a
  concern-specific guest probe. Later issues may strengthen observation through
  the envelope's per-concern seam without changing envelope identity semantics.

## Required Cross-Cutting Reuse

- SDL ingress: `parse_sdl()` / `parse_sdl_file()`, closed `SDLModel` shapes,
  `instantiate_scenario()`, `SemanticValidator`, and existing parse,
  instantiation, and semantic errors. No libvirt-specific SDL field is needed.
- Envelope semantics: `RealizationEnvelopeModel`, `member()`, `subsumes()`,
  `witness()`, and `generate_negative_probes()` from the shared contract and SDL
  semantic packages.
- Contract publication: hand-governed schemas, `ContractModel`,
  `schema_bundle()`, valid/invalid fixtures, publication-manifest `last_change`
  hashes, `x-aces-invariants`, generated-schema parity, and the packaged corpus
  resolver. Published envelope instances are a corpus family, not backend
  profiles or fixtures. Keep `specs/authority/authority-boundary.yaml`,
  `BACKEND_SUPPORTED_CONTRACT_IDS`, schema publication, and packaged wheel/sdist
  contents synchronized; do not make the provisioning-only profile require the
  new contract unless that is intentionally a universal backend obligation.
- Manifest authority: `BackendManifest`, `BackendManifestV2Model`,
  `backend_manifest_payload()`, supported-contract validation, capability-gap
  checks, controlled vocabularies, and canonical concept bindings.
- Planning/runtime: `_validate_manifest()`,
  `realization_support_diagnostics()`, `realization_disclosure()`,
  `ExecutionPlan`, `RuntimeManager`, `RuntimeControlPlane`,
  `_call_backend_diagnostics()`, `_call_backend_apply()`, snapshot contract
  diagnostics, and target-shape validation.
- Error/observability: existing `Diagnostic`, `Severity`, `OperationReceipt`,
  `OperationStatus`, conformance case/report, audit, and `changed_addresses`
  surfaces. Do not add a libvirt exception hierarchy or a logging-only result.
- Persistence: `RuntimeSnapshot`, `RuntimeSnapshotEnvelopeModel`,
  `ControlPlaneStore`, and its established typed serialization. Existing atomic
  run-artifact writers remain the only optional report writer.
- Testing: realization relation/property tests; planner, runtime-manager,
  control-plane/API/store, manifest publication, libvirt realization,
  provisioner, registry, conformance, and recording-driver tests. Negative
  identity/config/unsupported mutations must assert the recording driver saw no
  call and the baseline snapshot stayed byte-for-byte equivalent.

## Security And Whole-Path Gates

- Config shape gate: CLI/operations inputs must become the normalized closed
  target config before any manifest or driver is built. There is no incumbent
  environment-binding path for libvirt; do not add one implicitly. A
  credential-bearing connection URI must not be accepted through a CLI option,
  because command arguments are OS-visible; use a non-secret URI plus an
  injected connection/credential handle or an explicit future secret-input
  surface.
- Secret gate: connection credentials, connector objects, SSH keys, cloud-init
  bodies, host paths, environment dumps, and raw config never enter envelope
  artifacts, digests, plans, snapshots, fixtures, diagnostics, audit details, or
  reports. Connection URIs remain private driver input and must not be logged.
- Contract/manifest gate: envelope, manifest, plan, and snapshot shapes pass
  their closed Pydantic models, published schemas, contract-id allowlists,
  vocabulary validation, concept binding validation, and semantic invariants.
- Planner gate: ordinary manifest checks, SEM-218 support checks, and shared
  envelope membership/subsumption all run before a valid execution plan exists.
  No one check substitutes for another.
- Target/apply gate: target component shape, exact envelope/config identity,
  libvirt capability diagnostics, backend `ApplyResult` shape, snapshot
  contract/transition validation, and SEM-218 runtime disclosure all remain
  fail-closed. Identity failure precedes every native side effect.
- HTTP/auth gate: no new route is needed. Provisioning submissions retain strict
  bearer/proxy identity verification, backend/operator role authorization,
  target scoping, request-size limits, idempotency fingerprints, audit events,
  and closed `ProvisioningPlanModel` parsing. The current bearer-token branch
  returns before the proxy branch's `identity.target_name` check; target scope
  must be enforced after either authentication mechanism before a
  configuration-bound plan is accepted.
- Error-envelope gate: failures use stable typed diagnostics naming ids,
  digests, relation kind, concern, and safe paths. They do not echo envelope
  values, raw plan/config payloads, native XML/object reprs, argv, stdout/stderr,
  stack traces, or credentials; unexpected HTTP failures keep the existing
  redacted 500 response. New validation failures must not reach
  `_backend_call_failed()`, whose current inclusion of `str(exc)` is not a safe
  carrier for configuration or connection errors; use typed redacted
  diagnostics, and harden that boundary if it is touched.
- Host/OS gate: envelope selection and validation are pure and hermetic. They do
  not import libvirt, query a daemon, inspect images, invoke subprocesses, or
  broaden claims from host discovery. Native access stays lazy behind the
  existing driver; fixed argv/list-form command and ownership/rollback guards
  remain intact. Envelope ids are grammar-checked before corpus path
  construction, resolve only below the packaged corpus root, and never select a
  caller-supplied or remote path.
- Persistence gate: rejected work writes no snapshot, operation success,
  realization provenance, or native-state ledger. Successful state carries the
  typed envelope/config identity; private host state remains outside portable
  persistence.

## Extensibility Seam

The required seam is one normalized material target configuration selecting one
versioned envelope artifact and immutable identity. A future remote libvirt
policy, alternate image family, architecture, storage/network policy, or new
appliance mode adds a normalized configuration variant and envelope artifact;
it does not edit the shared relation, planner rules, control-plane route,
diagnostic hierarchy, or persistence mechanism. Observation may strengthen per
concern from driver-reported to daemon- or guest-observed only when the selected
configuration wires the corresponding probe and changes the envelope digest.

## Gotchas And Anti-Patterns

Avoid:

- treating missing envelope identity as universal support or accepting a legacy
  fallback after a successful driver call;
- treating the backend name, driver class, connection URI, manifest summary, or
  a successful libvirt define as configuration-bound envelope identity;
- hashing raw secrets or serializing a callable/connection/object repr as
  configuration identity;
- passing credential-bearing libvirt URIs in process argv, diagnostics, audit,
  or report output;
- carrying identity only on `ExecutionPlan`, only in the manifest, or only in
  snapshot `metadata` while direct provisioning-plan submission remains open;
- using `realization_support.constraints` or
  `ProvisionerCapabilities.constraints` as the machine-readable envelope;
- conflating SDL membership with backend transformation or observation claims;
- copying the shared relation, plan payload extraction, manifest renderer,
  schema registry, vocabulary tables, config normalization, or digest logic;
- allowing the generic and TechVault drivers to select the same envelope by
  accident, or inferring the envelope from an injected driver;
- retaining broad OS/content/account/feature/ACL claims that only produce a
  descriptor, planned snapshot echo, or substrate handle;
- relabeling planned data as daemon- or guest-observed evidence;
- assuming bearer authentication enforces target scope before the shared
  authorization check is corrected;
- weakening the default hermetic suite by requiring libvirt/QEMU, privileges,
  host images, network access, or secrets.

## Non-Goals And Boundaries

- No implementation of issue #100 or downstream issues #714-#717.
- No new SDL syntax, backend profile, capability language, solver, HTTP route,
  persistence service, native-state repository, or libvirt-specific exception
  hierarchy.
- No guest-observed certification, real-daemon report, TechVault end-to-end
  honesty certification, or final reference-scenario certification; this issue
  may only publish the observation strength it actually proves.
- No claim that one witness proves subsumption, negative refusal, or backend
  honesty. Closed-envelope conformance still requires generated negative probes
  and unchanged native state.
- No compatibility path that treats absent, stale, mismatched, or unverifiable
  envelope/configuration identity as acceptable.
