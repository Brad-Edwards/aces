# Issue 716 / ASR-519 Realization Honesty Conformance Preflight

Date: 2026-07-14

Requirement source: Ground Control requirement ASR-519, selected by GitHub
issue #716.

This note records repository-wide guardrails for the realization-honesty
conformance work. It is guidance only: it does not implement the runner, alter
an envelope, add probes or fixtures, certify a backend, or define an
implementation plan.

No new ADR is required. ADR-021, ADR-036, ADR-066, and ADR-070 already own the
claim-evidence, package-boundary, evidence-plane, and realization-envelope
decisions. This issue must close the executable conformance gap without creating
parallel authority.

## Binding Sources And Canonical Incumbents

- ADR-070 and `specs/formal/realization/envelope-semantics.md` own the shared
  envelope language and the `member()`, `subsumes()`, `witness()`, and
  `generate_negative_probes()` relation in
  `aces_sdl.realization_envelope`. Conformance must extend that relation's
  deterministic probe coverage when necessary; it must not interpret domains,
  closure, or paths again.
- The issue #100 preflight and the published
  `BackendRealizationEnvelopeModel` own configuration/envelope identity,
  `RealizationConcern`, `ConcernDisposition`, `TransformationKind`, and
  `ObservationStrength`. The selected artifact under
  `contracts/realization-envelopes/` is the value/disclosure authority;
  `realization_support` and `ProvisionerCapabilities` remain separate coarse
  gates.
- The issue #714 and #715 preflights own exact-or-reject admission, one
  field-addressed concern inventory, daemon/guest observation, freshness,
  rollback, and cleanup. `RealizationObservation`, `DriverResult`, the TechVault
  concern validators, the guest observer, and the validated scenario-evidence
  workflow are incumbents, not examples to copy.
- `run_fixture_suite()`, `run_target_conformance()`,
  `ConformanceCaseResult`, `BackendConformanceReport`, and the existing
  `bounded-probe-success` `BehavioralClaimBindingModel` are the conformance and
  report family. Issue #716 evolves this family; it does not add an honesty-only
  runner, claim relation, report schema, profile, or exception hierarchy.
- `RuntimeManager`, `RuntimeControlPlane`, `_call_backend_diagnostics()`,
  `_call_backend_apply()`, `OperationReceipt`, `OperationStatus`, `ApplyResult`,
  `RuntimeSnapshot`, `ControlPlaneStore`, and the closed plan/snapshot models are
  the execution, validation, error, and portable persistence path.
- `interpret_provisioning_plan()`, `Realization`, `DomainSpec`, `NetworkSpec`,
  and `Realization.placement_targets` are the libvirt plan interpretation and
  aggregation seam. Conformance must account for the original plan operations;
  a domain-level spec or handle cannot erase placement/binding obligations.
- `aces_operations.libvirt_evidence_run`,
  `validate_libvirt_evidence_run_artifact()`, `redaction_violations()`,
  `cleanup_native_snapshot()`, `run_artifact_path()`, and
  `atomic_write_json_artifact()` are the native proof, redaction, cleanup, and
  explicit report-output incumbents.
- ADR-009/ADR-061, `ContractModel`, `schema_bundle()`, the packaged corpus,
  `contracts/schema-publication-manifest.json`, and
  `specs/authority/authority-boundary.yaml` govern any unavoidable published
  contract change. A local conformance report does not become a published
  contract merely because it is JSON.

## Architectural Diagnosis

The current target probe proves only that a control-plane apply returned a
successful operation, non-empty changed addresses, and a schema-valid mutated
snapshot. Its libvirt test uses a daemon-free recording driver. That is useful
**hermetic target-adapter evidence**, but it is neither native-live nor evidence
that each realization concern was observed at its declared strength.

Four existing shapes are insufficient by themselves:

1. `SnapshotEntry.payload` is planned reconciliation state and can echo a plan
   that the backend ignored.
2. `DomainHandle`, `NetworkHandle`, `changed_addresses`, and
   `realized_addresses()` are completion/accounting receipts, not concern
   observations.
3. `BackendConformanceReport` currently records a boolean per case but no
   execution basis, envelope/configuration binding, observation inventory,
   negative-probe mutation proof, or cleanup result.
4. The three published libvirt envelopes currently contain empty/open
   expressions. `witness()` cannot derive a complete valid scenario from those
   expressions. Conformance must fail visibly until an authoritative envelope
   is sufficiently constructive; it must not fall back to
   `_DEFAULT_CONFORMANCE_SCENARIO`, a caller-selected happy path, or a
   libvirt-specific witness table.

The existing `reference_scenario` bridge is therefore not an acceptable ASR-519
certification path. It may remain for legacy adapter conformance, but its result
must be labelled `hermetic-live` and bounded to that supplied scenario, never
promoted to realization-envelope or native conformance.

## Architecture Decisions And Guardrails

### Keep one conformance runner and one report family

- Extend `run_target_conformance()` (or a narrowly named helper it owns) and
  `BackendConformanceReport`; keep fixture, target, realization, and cleanup
  cases in one machine-readable report. Do not create `HonestyReport`, a
  libvirt report DTO, or a second serializer.
- Keep `aces_conformance` backend-neutral. It may depend on neutral contracts,
  SDL relations, processor planning, and runtime control, but it must not import
  `aces_backend_libvirt`, `aces_operations`, or inspect driver classes.
- Native/backend-specific construction and observation remain behind an
  injected, conformance-only harness assembled by operations code (and by test
  fixtures for hermetic runs). The minimal harness supplies an already validated
  `RuntimeTarget`, execution basis, addressed observations, an independent
  mutation/state ledger, and cleanup/residual results. It is not a new runtime
  role, manifest capability, `RuntimeTarget` component, control-plane endpoint,
  or general backend protocol.
- `aces_backend_libvirt.driver.RealizationObservation` is a backend-local
  readback DTO, not the backend-neutral evidence contract: it lacks probe,
  operation, envelope/configuration, freshness, and cleanup binding.
  `RealizationProvenanceEntry` is also not that contract; it records SEM-218
  origin without observed values or observation strength. Keep both meanings
  intact. If the injected harness must pass evidence between
  `aces_operations` and `aces_conformance`, ADR-036 puts the minimum neutral,
  typed observation-evidence DTO in `aces_contracts`; the backend/operations
  adapter maps its local readback into that DTO and the existing
  `BackendConformanceReport` projects it. Do not copy the libvirt dataclass into
  each backend, re-export it as if backend-local fields were neutral, or overload
  runtime provenance. A neutral internal DTO does not by itself authorize a
  published JSON Schema.
- Preserve the enforced import graph. `aces_conformance` must not import
  `aces_operations` or `aces_backend_libvirt`, and `aces_operations` must not
  import `aces_conformance`. The `aces_cli` composition root may wire the
  structurally compatible operations harness into the conformance runner while
  both sides exchange only `aces_contracts` DTOs. Any new public module prefix
  must be added narrowly to `tools/policy/adr_policy.yaml`; do not evade the
  policy with private-module imports or `Any` payloads.

### Derive the probe set from the selected envelope

- Load and validate the configuration-selected
  `BackendRealizationEnvelopeModel` through the packaged corpus loader. Require
  exact equality among manifest identity, offered artifact identity, plan
  identity, target configuration, observer binding, and report binding before
  any probe executes.
- Generate positive witnesses and negative variants through the shared envelope
  relation. If one deterministic base witness does not cover a finite enum,
  boolean, bounded interval boundary, governed reference, exact omission, or
  closed child dimension, extend the shared generator over the same
  `effective_constraints()`/domain engine. Do not put sampling logic in
  `aces_conformance` or a backend.
- Every positive candidate must pass the normal closed SDL model,
  instantiation, `SemanticValidator`, and `member()` checks before planning.
  Every negative candidate must remain structurally/semantically safe and be
  proven outside the offered envelope for exactly one reported variation. A
  malformed request rejected by Pydantic is not evidence that the backend
  enforces its envelope.
- Probe generation is deterministic and reportable: policy/seed, dimension,
  path, variation, and a secret-free canonical probe digest are recorded. Raw
  secret-capable values are not report identity.
- A dimension for which no safe, ordinary-contract-valid probe can be generated
  is `unsupported`, not passed. Skipped and unsupported probes prevent the
  corresponding claim from certifying. Open or genuinely unbounded dimensions
  remain explicit nonclaims rather than silently increasing the denominator.

### Require total operation and concern accounting

- For each positive witness, derive the expected operation inventory from the
  canonical `ProvisioningPlan`, not from driver handles or the post-apply
  snapshot. Every non-`UNCHANGED` operation has exactly one terminal accounting
  result: independently observed at the envelope-required strength, rejected
  before mutation, or failed with an addressed diagnostic.
- Preserve both levels when the backend aggregates: a node/domain observation
  may account for the node operation, but account/content/feature/service/ACL
  placements and bindings require their own addressed concern observations.
  Missing aggregated placements/bindings fail even when the parent domain and
  every `changed_address` exist.
- `UNCHANGED` means no fresh mutation and supplies no fresh observation claim.
  `DELETE` requires ownership-checked observed absence and complete cleanup; a
  false absence handle is not enough.
- Compare authored/planned requirements with independently observed facts. An
  exact value is equal or rejected. A transformed value passes only when the
  selected envelope names the transformation, the input and output are both
  admitted by an executable governed rule, and the report discloses it. The
  current transformation-name enum is disclosure, not executable permission;
  absent such a rule, use exact-or-reject.
- Missing disclosure, image substitution, resource clamping/defaulting,
  descriptor substitution, synthesized services, planned-as-observed facts,
  fabricated handles, duplicate/missing observations, stale evidence, and
  unexpected augmentation are distinct failures with stable diagnostic codes.

### Observation strength is a per-concern evidence requirement

- Treat envelope observation strength as a required terminal level, not a label
  copied onto a report. Driver-reported concerns require a fresh addressed
  `RealizationObservation`, not merely a handle. Daemon-observed concerns require
  ownership-correlated post-operation readback. Guest-observed concerns require
  the issue #715 challenge-bound concern probe and its daemon correlation.
- Strength is ordered evidence, not interchangeable provenance. SEM-218
  `backend-realized`, SEM-225 augmentation, report execution basis, and
  `driver`/`daemon`/`guest` observation are four different classifications.
- A guest terminal claim does not erase its prerequisite daemon binding. Reports
  enumerate both layers and never upgrade driver/daemon evidence because the
  overall run used a guest-capable or native driver.
- Every observation is bound to the current operation/probe, safe ACES address
  and field path, concern, source, selected envelope/configuration digests,
  observer/probe-policy version, and freshness evidence. A prior driver snapshot,
  reused challenge, cross-operation fact, or unbound timestamp fails.

### Negative probes prove refusal without mutation

- Submit plan-valid negative probes through the ordinary planning/control-plane
  boundary far enough to exercise the target's envelope/admission gate. They
  must fail before `driver.realize()`, `driver.destroy()`, libvirt connection,
  artifact creation, or any native mutation.
- Prove non-mutation in both planes: byte-equivalent portable baseline snapshot
  (including envelope/provenance and persisted store round-trip where used) and
  an independent harness ledger showing no driver/native mutation call and no
  change in the owned native inventory. Backend self-report alone is not proof.
- Wrong-envelope tests pair each libvirt configuration with another published
  envelope identity and assert refusal before IO. Generic,
  `techvault-appliance`, and any selectable guest-certified configuration remain
  separate target instances and reports; success in one must not certify the
  abstract `libvirt-qemu` name or another configuration.

### Execution basis, outcome, and certification scope stay distinct

- Use exactly these execution-basis statuses in conformance results:
  `fixture-only` (published corpus only), `hermetic-live` (real
  processor/control-plane/provisioner path with injected hermetic driver and
  observer), and `native-live` (real daemon/native mutation and verified
  teardown). Only `native-live` may support a native-conformance claim.
- `guest-certified` is an observation capability/mode inside a `native-live`
  run, not a fourth conformance basis. Existing evidence-source modes such as
  `deterministic` also do not substitute for these statuses.
- Probe outcomes are `passed`, `failed`, `skipped`, or `unsupported`; only
  `passed` contributes to an overall pass. ADR-021 evidence status
  (`untested`/`partial`/`demonstrated`/`refuted`) and the behavioral relation
  claim remain separate fields.
- Rename remaining user/report-facing “live provisioning” descriptions that
  refer to a recording/fake driver to “hermetic target provisioning” or
  equivalent. Historical function names may remain private only if they cannot
  be mistaken for real-daemon evidence.

### Claims and reports are configuration-bound

- Bind every claim to backend implementation name and version, target instance,
  profile, driver/configuration mode, envelope id/digest, configuration digest,
  probe-set digest, execution basis, observer/probe-policy version, and evidence
  artifact refs. `backend-target:libvirt-qemu` alone is too broad.
- Reuse `bounded-probe-success`; finite probes never establish universal
  realizability, backend equivalence, or a broader abstract backend name.
- Extend the existing report projection so it enumerates each envelope concern,
  generated probe, expected observation level, actual observations, operation
  accounting, outcome, stable diagnostics, pre/post state proof, cleanup, and
  residual category. Preserve failed and unsupported results; no serializer may
  filter them from the claim's evidence boundary. Keep one canonical report
  finalizer/serializer and validate its cross-field invariants before rendering;
  do not create a parallel operations-only or libvirt-only report validator.
- Durable native evidence is written only after full report validation and the
  shared redaction gate, using the existing safe run-id/root confinement and
  atomic writer. A cleanup failure may produce a failed redacted report, never a
  passing one. Fixture-only output remains stdout unless explicit output was
  requested.

## Dishonest Backend And Falsification Boundary

- Model prohibited behaviors as a table-driven dishonest **test fixture** behind
  the same `RuntimeTarget`/provisioner/harness boundary. Do not add dishonest
  modes to the production reference backend or monkeypatch the conformance gate
  under test.
- Each behavior is independently selectable and must fail for its expected
  stable reason: schema-valid no-op/snapshot echo, omitted or mutated placement,
  silent transformation, clamp/default, image substitution, missing disclosure,
  planned-as-observed evidence, fabricated handle/observation, stale evidence,
  wrong envelope/configuration, partial cleanup, and residual state.
- Assertions cover failed operation/probe outcome, empty changed addresses where
  admission failed, unchanged portable and native baselines, expected diagnostic
  code/address, no passing claim, and cleanup/residual result. A single
  multi-fault fixture cannot prove diagnostic specificity.
- Hermetic mutation tests are mandatory in the default verification graph. Real
  libvirt proof is separate and opt-in, but it is not allowed to self-skip and
  then publish a passing native report.

## Required Cross-Cutting Reuse

- **SDL and envelope validation:** `Scenario`, `parse_sdl()`/`parse_sdl_file()`,
  `instantiate_scenario()`, `SemanticValidator`, `member()`, `subsumes()`,
  `witness()`, `generate_negative_probes()`, and their existing diagnostic
  model.
- **Contract and corpus authority:** `BackendRealizationEnvelopeModel`,
  `RealizationEnvelopeIdentityModel`, closed `ContractModel` descendants,
  `schema_bundle()`, `corpus_family_root()`, schema/fixture/profile publication
  rules, and canonical digest helpers.
- **Manifest and planning:** `backend_manifest_payload()`,
  `BackendManifestV2Model`, supported-contract and controlled-vocabulary gates,
  `realization_support_diagnostics()`, `realization_disclosure()`,
  `RuntimeManager.plan()`, and the typed provisioning plan.
- **Execution and persistence:** `RuntimeControlPlane`, backend call guards,
  operation receipt/status, `ApplyResult`, snapshot transition validation,
  `RuntimeSnapshotEnvelopeModel`, `ControlPlaneStore`, and atomic store behavior.
- **Backend observation:** the existing plan interpreter, recording drivers,
  `RealizationObservation`, TechVault daemon/guest observers, operation binding,
  ownership stamps, safe absence detection, rollback, and cleanup helpers.
- **Errors and observability:** `Diagnostic`, `Severity`, audit events, stable
  package-local codes, `BehavioralClaimBindingModel`, `SessionReporter`, and the
  shared artifact redaction validator. Logs and nox stage summaries are
  supplemental and never count as probe evidence.
- **Workflow:** the canonical Typer `aces conformance` family, explicit
  destructive confirmation and noncredential URI validation for native runs,
  the hermetic `nox verify` graph, separate real-daemon workflow, and repository
  policy/governance checks from `.ground-control.yaml` and `.gc/plan-rules.md`.

## Security And Whole-Path Gates

- **Corpus/config shape:** envelope/profile ids resolve only through grammar-
  checked, root-confined packaged corpus loaders. Payloads pass closed Pydantic
  models, canonical digest checks, manifest/config/mode consistency, and
  allowlisted `_validate_config_keys()` before target or observer construction.
  Do not accept caller-supplied envelope paths or remote envelope URLs.
- **SDL/plan shape:** generated probes pass ordinary SDL structure, semantics,
  envelope relation, compiler/planner, `ProvisioningPlanModel`, capability, and
  target identity gates. A conformance shortcut must not instantiate backend
  specs directly.
- **Authentication/authorization:** no new HTTP route is required; prefer the
  in-process runner, whose result makes no authentication claim. If conformance
  is ever driven through the existing HTTP submission route, retain
  `ControlPlaneSecurityConfig.strict_defaults()`, verified bearer/proxy identity,
  backend/operator role authorization, request-size limits, idempotency
  fingerprints, and audit events. The current
  `_ControlPlaneApiAuth._authenticate_request()` applies `identity.target_name`
  only in the proxy-header branch because a valid bearer returns early. That
  must be factored into one post-authentication scope check for both mechanisms
  before an HTTP-driven result can count; issue #716 must not add a second auth
  path or claim the current bearer path is target-scoped.
- **Secrets and environment binding:** credentials, bearer tokens, keys,
  cloud-init/account material, environment dumps, connector/transport reprs,
  host paths, native ids, and raw configuration never enter probes, digests,
  diagnostics, snapshots, reports, or logs. The CLI's
  `_noncredential_connection_uri()` check must become one shared library/config
  validator used by both `TechVaultNativeLibvirtDriver` and the generic
  `LibvirtDeploymentDriver`; Typer validation alone does not protect Python
  callers, and the generic driver currently checks only non-emptiness. The
  opt-in `ACES_REAL_LIBVIRT_URI` test input must pass that same validator before
  driver or direct `libvirt.open()` construction; unset/invalid native input is
  blocked or unsupported, never a passing `native-live` result. Do not add a
  dotenv or generic environment-to-config binder. Never hash a
  credential-bearing URI as a safe substitute and never place secrets in
  process argv. Use injected connection/credential handles if a future
  transport requires authentication.
- **Host/OS exposure:** fixture-only and hermetic-live are pure with respect to
  libvirt/QEMU. Native-live remains opt-in, uses lazy libvirt import, structured
  XML, fixed argv/no `shell=True`, bounded stage and overall deadlines,
  ownership-confined workspaces, safe file modes/symlink checks, and no ambient
  privilege escalation. Guest probing remains a fixed read-only fact channel,
  never a general command runner.
- **Error envelope:** public failures carry stable code, safe address/path,
  concern/observation level, and generic redacted message. Do not concatenate
  backend diagnostic messages or `str(exc)`. Existing conformance paths that
  render raw Pydantic/backend exception text (`_validate_payload()`, event
  validation, participant probe handling, and target provisioning status
  aggregation) must be sanitized if reused by the new report. The HTTP routes'
  `HTTPException(detail=str(exc))` conflict responses are likewise not a safe
  conformance error carrier. Apply the shared redaction gate to the complete
  report before persistence and discard raw stdout/stderr, XML, probe details,
  and tracebacks.
- **Portable persistence:** conformance does not add fields to
  `RuntimeSnapshot.metadata` or `ApplyResult.details`, and it does not add a
  native-state database. Runtime state continues through typed snapshots/store;
  captured observation and cleanup proof live in the validated report/evidence
  artifact. Rejected work writes no successful operation, snapshot mutation, or
  realization claim.

## Whole-Repository Surfaces In Scope

- Normative: realization-envelope formal semantics; published realization
  envelope, backend manifest, provisioning plan, operation status, and runtime
  snapshot schemas/artifacts; backend profile and fixture corpora; authority and
  schema-publication manifests if any published shape changes.
- Implementation: `aces_sdl.realization_envelope`, `aces_contracts` envelope and
  runtime DTOs, `aces_conformance`, processor planning/realization disclosure,
  runtime control plane/backend calls/store, libvirt target/provisioner/driver
  observers, operations evidence/cleanup/writer, and the canonical CLI wiring.
- Verification: relation/property tests, contract/fixture tests, target and
  control-plane tests, dishonest-backend mutation corpus, generic and TechVault
  wrong-envelope tests, libvirt daemon/guest evidence validation, report drift
  tests, redaction/security tests, and the opt-in reproducible real-daemon proof.
- Governance: repo policy, requirement governance/traceability, generated-schema
  parity, schema publication, authority boundaries, ADR-036 module-boundary
  policy, docs build, and full verify.

## Extensibility Seam

The required seam is a backend-neutral conformance engine parameterized by:

- one validated target and configuration-bound envelope;
- deterministic probe policy/seed;
- execution basis (`fixture-only`, `hermetic-live`, `native-live`);
- one source-specific addressed observer;
- one independent mutation/state ledger; and
- one cleanup/residual verifier.

A future backend, libvirt image family, remote libvirt policy, architecture,
guest transport, or stronger observation source supplies another target/harness
configuration. It must not require edits to the envelope relation, concern or
observation vocabularies, planner action model, runtime control plane, diagnostic
hierarchy, store, claim relation, or report writer. The probe policy is the seam
for future deterministic coverage strengthening; backend names and driver
classes are not dispatch keys in the conformance engine.

## Gotchas And Anti-Patterns

Avoid:

- treating the current empty/open libvirt envelope expressions as constructive,
  or silently substituting the old default/reference scenario;
- accepting one in-envelope witness as proof of a bounded dimension;
- counting a skipped, unsupported, unsafe, malformed, or unexecuted probe as
  passed;
- using schema validity, receipt acceptance, snapshot mutation, changed
  addresses, handles, or a planned payload echo as realization evidence;
- letting parent domain accounting hide aggregated placement/binding omissions;
- letting a claimed transformation name authorize clamp/default/substitution
  without a governed executable rule and explicit report record;
- treating `backend-realized`, `native-live`, `guest-certified`, and
  `guest-observed` as synonyms;
- trusting a backend's own “no mutation” or cleanup assertion without an
  independent call/native-state ledger;
- allowing a fake/recording driver report to certify native conformance;
- treating an integration-test self-skip or an unset/invalid
  `ACES_REAL_LIBVIRT_URI` as a passing native-conformance result;
- certifying `libvirt-qemu` broadly from one mode, envelope, driver,
  configuration, or witness;
- importing libvirt/operations code into `aces_conformance`, adding conformance
  to the universal runtime protocols, or duplicating the observation DTO;
- adding a conformance schema, profile, capability language, exception tree,
  logger, store, endpoint, report writer, or secret/config parser when the
  incumbents already exist;
- mutating canonical fixtures in place, monkeypatching the gate under test, or
  putting dishonest behavior in a production backend;
- exposing credential-bearing URIs in argv or accepting them through unvalidated
  library calls; and
- persisting a passing report before cleanup and full redaction/report
  validation succeed.

## Non-Goals And Implementation Boundaries

- No implementation of issue #716 in this preflight and no certification result.
- No new SDL syntax, envelope language, solver, backend profile, universal
  observation service, runtime role, HTTP route, persistence service, or public
  report schema.
- No redesign of the planner, control plane, backend protocol, runtime snapshot,
  experiment-core evidence contracts, or participant-observation semantics.
- No implementation of additional guest applications, OS/image families,
  services, ACL mechanisms, or broader libvirt realizability merely to make a
  probe pass. Unsupported concerns stay unsupported.
- No claim of universal envelope subsumption, backend equivalence, all-driver
  conformance, all-configuration conformance, or final reference-scenario
  certification (issue #717).
- No requirement that the hermetic verification graph install libvirt/QEMU,
  access a daemon, hold credentials, use network access, or gain host privileges.
- No compatibility fallback for missing/stale/mismatched identity, incomplete
  operation accounting, absent required observation, failed cleanup, or
  residual native state.
