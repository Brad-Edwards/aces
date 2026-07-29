# Issue 790 SCE-002 trial realization and provenance preflight

Date: 2026-07-29

Issue: #790.

Requirements: SCE-002 and SCE-006.

This note fixes the public one-entry realization and provenance boundary that
an isolated-batch scheduler may call. It is guidance only: it does not change a
schema or model, realize or execute a trial, add a scheduler, persist an
artifact, add fixtures/tests, or define an implementation plan.

ADR-065 and ADR-084 remain authoritative. The existing experiment run is the
only archival run root, the admitted trial plan is immutable execution intent,
and the existing SDL/processor/runtime path remains the only scenario
lifecycle.

## Architecture decisions and prerequisite gaps

- The public seam consumes one fully revalidated `AdmittedTrialPlanModel`, one
  `plan_entry_id`, and the exact digest-matched family, task, manifests,
  realization envelope, profiles, and associated artifacts pinned by that
  plan. It does not accept a detached entry, raw experiment authoring input,
  caller-supplied replacement bindings, or an unchecked Python object.
- Validate the complete plan and its canonical digest before resolving the
  entry. Then rerun the owning cross-artifact joins against the concrete pinned
  inputs. A structurally valid entry extracted from a stale, tampered,
  incomplete, or mismatched plan is not executable.
- `raes.select_scenario_family()` is the SDL-owned one-entry selection and
  admission gate. It already applies the complete recorded outcomes and routes
  through `instantiate_scenario()` and `admit_instantiated_scenario()`. The
  integration must call it and must not reconstruct its payload mutation,
  target resolution, relation validation, binding, or exception translation.
- Extend the existing `InstantiationProvenance` surface rather than add a
  trial-realization root. Canonical instantiated-snapshot bytes must commit to
  the exact family identity/digest, admitted plan id/digest, entry id/digest,
  preallocated `run_id`, coordinate, selections, and admitted bindings. Every
  repeated value is equality-checked against the plan entry; it is not a
  second authority.
- `canonical_instantiated_sdl_bytes()` and
  `canonical_instantiated_sdl_digest()` remain the snapshot identity
  authority. Do not hash YAML, `repr`, `model_dump_json()`, mutable validation
  flags, a filesystem path, or an unadmitted scenario.
- Continue through `compile_scenario_runtime_model()` and
  `raes_processor.planner.plan()`. Processor-plan provenance uses the existing
  `provisioning_plan_model()`, `orchestration_plan_model()`, and
  `evaluation_plan_model()` projections, their published contract versions,
  RFC 8785/JCS canonical digests, and the digest-matched
  `ProcessorManifestV2Model`. Do not claim a portable digest for the internal
  `RuntimeModel` or `ExecutionPlan` dataclass by serializing `asdict()` or
  Python object state.
- The effectful executor delegates to one existing execution transport per
  attempt. In-process execution uses a fresh per-attempt `RuntimeManager` and
  its `plan()`/`apply()`/`destroy()` lifecycle. A control-plane deployment may
  instead submit the same typed plan projections through
  `RuntimeControlPlane`; it must not also call `RuntimeManager.apply()` for the
  same work. No integration layer calls backend protocol methods directly.
- Attempt context is supplied to the one-entry executor. A started,
  effect-capable attempt receives one opaque `execution_attempt_id`, distinct
  from `run_id`, scheduler job id, operation id, workflow run id, snapshot id,
  and backend-native id. Transport replay reuses the attempt and idempotency
  identity; a policy-authorized later attempt receives a new attempt id but
  retains the admitted entry and `run_id`.
- Extend `ExperimentRunModel` minimally with a closed, typed trial-realization
  linkage rather than create a second run or provenance root. The linkage must
  bind the plan and entry identities/digests, logical coordinate
  (condition/block/replicate when present), instantiated-snapshot digest,
  processor-plan artifact refs/digests, and the attempt refs that contributed
  to the governed terminal run outcome.
- `TrialCleanupReceiptModel` remains the immutable per-attempt authority for
  primary disposition versus cleanup disposition. Failed or unverified cleanup
  remains visible even when the archival run outcome succeeded and prevents
  resource reuse. It is not collapsed into a deviation string or inferred
  from `RuntimeManager.destroy()` success.
- Extend the owning experiment cross-artifact validation beside
  `validate_experiment_run_against_task()` and
  `validate_experiment_study_against_tasks_and_runs()`. Given the admitted
  plan, concrete run records, and attempt/cleanup evidence, it must reconcile
  every admitted entry with zero or more explicit attempts and no more than
  one governed terminal archival outcome. Zero-attempt entries remain visible
  through the plan; they do not require placeholder runs.
- Planned, instantiated, processor-derived, backend-realized, observed, and
  derived facts stay on their existing surfaces. The admitted plan states
  intent; the canonical scenario snapshot states instantiated meaning; typed
  processor plans state derived operations; runtime snapshots and receipts
  state live realization; evidence records state observations; derived
  measures and study analysis state interpretation.

Two repository gaps are prerequisites, not invitations for local shortcuts:

- There is no canonical bounded external loader for
  `admitted-trial-plan-v1`. Any file/API ingress must be byte-bounded,
  duplicate-key rejecting, and closed-model validating in the owning contracts
  layer before execution. It must not use an unbounded `json.load()` or add an
  APTL-only parser.
- `InstantiationProvenance` and `ExperimentRunModel` do not yet carry the
  required admitted-entry/attempt integrity spine. Until their owning,
  published contracts and cross-artifact validators carry it, an adapter must
  not encode the missing linkage in metadata, notes, tags, paths, logs, or
  generic references and claim completion.

## Canonical incumbents to reuse

- **Lifecycle and identity:** ADR-055, ADR-065, ADR-068, ADR-074, ADR-084,
  `specs/formal/scenario-variation-trial-realization/README.md`,
  `AdmittedTrialPlanModel`, `AdmittedTrialEntryModel`,
  `AdmittedInstantiationProvenanceModel`, `TrialCoordinateModel`,
  `ExperimentRunModel`, `ExperimentStudyModel`, and RFC 8785/JCS helpers in
  `raes_contracts.canonical`.
- **SDL selection and snapshot:** the exact `ExpandedScenario` family,
  `ExpandedScenarioBindingTargetResolver`, `select_scenario_family()`,
  `instantiate_scenario()`, `admit_instantiated_scenario()`,
  `InstantiationProvenance`, `InstantiatedScenarioSnapshot`,
  `canonical_instantiated_sdl_bytes()`, and
  `canonical_instantiated_sdl_digest()`.
- **Bindings and secrets:** `AdmittedBindingModel`,
  `ExperimentBindingDescriptorModel`, `RealizedBindingProvenanceModel`,
  `validate_experiment_binding_targets()`, participant/apparatus configuration
  result validators, `SecretReferenceBindingValueModel`,
  `RuntimeFactBindingPlane`, and `RuntimeEnvironmentVariable` sensitivity and
  omission rules.
- **Processor artifacts:** `compile_scenario_runtime_model()`,
  `raes_processor.planner.plan()`, `ProvisioningPlanModel`,
  `OrchestrationPlanModel`, `EvaluationPlanModel`, the three
  `raes_contracts.plan_projection` helpers, processor/backend manifest
  compatibility, realization-envelope membership, and artifact-requirement
  admission.
- **Execution and operations:** `RuntimeManager.plan()`/`apply()`/`destroy()`;
  where the deployment uses the control plane,
  `RuntimeControlPlane.submit_provisioning()`,
  `submit_orchestration()`, `submit_evaluation()`, `get_operation()`,
  workflow cancellation/timeout/compensation helpers,
  `OperationReceipt`, `OperationStatus`, and request
  idempotency/fingerprints.
- **Attempts, cleanup, and archival evidence:** `TrialCleanupPlanModel`,
  `TrialCleanupReceiptModel`, `validate_trial_cleanup_receipt()`,
  `ExperimentRunTraceabilityModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentDerivedMeasureModel`, `ExperimentInvalidationModel`,
  augmentation/realized-form disclosures, and associated-artifact refs,
  checksums, sensitivity, and redaction/loss disclosure.
- **Persistence and observability:** `ControlPlaneStore`,
  `LocalControlPlaneStore`, `ControlPlaneOperationRecord`, append-only
  `AuditEvent`, `operational_apparatus_summary()`, `is_valid_run_id_label()`,
  `run_artifact_path()`, and the existing atomic artifact writers. Live
  operation durability and archival run/evidence storage remain separate.
- **Publication and workflow:** ADR-009, ADR-019, ADR-061,
  `specs/authority/authority-boundary.yaml`,
  `contracts/schema-publication-manifest.json`, per-contract publication
  entries and fixtures, `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/generate_contract_schemas.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, and
  `tools/verify_all.py`.

The modules under `raes_runtime.participant_scheduler*` schedule participant
actions inside one already running scenario. They are not trial-attempt
identity, batch scheduling, run provenance, or a reusable worker framework.

## Cross-cutting layers the design must pass

1. **Ingress and shape gate.** Bound bytes before parsing, reject duplicate
   JSON members, reconstruct `AdmittedTrialPlanModel`, reject extras through
   `ContractModel(extra="forbid")`, check contract/profile compatibility, and
   recompute `plan_digest` and every entry digest. Never execute a caller's
   deserialized model without reconstruction.
2. **Plan and cross-artifact gate.** Resolve the requested map key to the
   embedded `plan_entry_id`; join plan/family/task/spec/binding-set/artifact/
   manifest/envelope refs to exact concrete digest-matched inputs; resolve the
   cleanup plan and stochastic controls; and reject stale capability or
   envelope drift. No fetch, substitution, fallback, or repair occurs inside
   validation.
3. **SDL admission gate.** `select_scenario_family()` validates every complete
   outcome, target write, relation, and whole selected scenario before the
   ordinary instantiation/admission path. Entry bindings and resulting
   `InstantiationProvenance` must be equal to the admitted values, and the
   canonical snapshot digest is recomputed before processor use.
4. **Processor/backend gate.** Compile the admitted instantiated scenario,
   project all three typed plans through the existing contract models, rerun
   planner diagnostics, manifest compatibility, artifact availability,
   realization-envelope, target binding, and backend `validate()` gates.
   Backend refusal or drift is an explicit failed/deviated attempt, never
   permission to substitute bindings or apparatus.
5. **Authentication and authorization gate.** Any API reuses
   `ControlPlaneSecurityConfig.strict_defaults()`, bearer or verified-proxy
   identity, mutating/read roles, target scoping, request-size guards,
   idempotency/fingerprint conflicts, and append-only audit. Plan visibility,
   artifact dereference, secret resolution, execution, cancellation, cleanup,
   evidence publication, and run publication are separately authorized
   actions.
6. **Secret and configuration gate.** Portable plans and provenance carry
   governed secret references only. Resolve a secret at its authorized
   run-local typed sink; never turn it into a factor, parameter value, digest
   input, selection, artifact summary, diagnostic, or audit detail. Ambient
   environment, worker defaults, backend defaults, or mutable global config
   cannot change the admitted scenario or run identity.
7. **OS/process exposure gate.** Use per-attempt private work/storage
   namespaces, safe bounded names, containment-validated paths, fixed argv,
   controlled working directories, no shell interpolation, bounded
   subprocesses, private seed/material files, credential-free connection URIs,
   ownership-safe backend names, and redacted captured output. Tokens,
   credentials, secret refs, parameter maps, raw plans, environments, native
   handles, and backend output do not enter argv or process titles.
8. **Timeout, retry, cancellation, and cleanup gate.** Attempt timeout is
   supplied from `AdmittedExecutionControlModel`; workflow timeout,
   participant deadlines, logical scenario time, API timeouts, cleanup
   obligation timeouts, and lease expiry remain distinct. Unknown effect state
   reconciles the persisted attempt/operation before a retry. Every terminal
   path triggers the declared cleanup obligations and validates the resulting
   receipt independently of the primary outcome.
9. **Error-envelope gate.** Expected failures become bounded,
   canonically ordered `Diagnostic`/`DiagnosticModel` records with governed
   codes, domains, JSON-pointer addresses, and safe fixed messages. Backend
   adapters report exception type without exception text; HTTP retains the
   redacted 500 body. Raw Pydantic inputs, selected values, secret locators,
   plans, host paths, stderr, native ids, environment, and tracebacks are not
   rendered.
10. **Persistence, logging, and archival gate.** Persist operational
    correlation needed for idempotent recovery in the canonical operational
    store: safe plan/entry/run/attempt ids, operation ids, deadlines, and
    cleanup disposition. Store canonical plan/snapshot/processor/run/evidence
    artifacts through immutable, checksum-bound artifact surfaces. Logs and
    audit carry only safe ids, digests, versions, stages, counts, outcomes, and
    durations; they are not provenance authority.
11. **Run/study reconciliation gate.** Revalidate the run against its task,
    apparatus manifests, scenario snapshot, admitted entry, attempts, cleanup
    receipts, evidence, and stochastic controls. Revalidate the study against
    its tasks, admitted allocation, and runs. Condition, replicate, selected
    bindings, draw addresses, `run_id`, and terminal outcome must agree across
    every repeated surface.

## Extensibility seam

The seam is a pure entry-realization operation followed by an effectful
attempt executor. Its explicit inputs are the sealed plan identity, entry id,
exact pinned artifacts, selected runtime target, opaque caller-owned
`execution_attempt_id`, idempotency identity, and admitted deadline/cleanup
policy. Its outputs are existing typed artifacts and safe diagnostics:
admitted instantiated snapshot, canonical digests, typed processor-plan
projections, operation/attempt evidence, cleanup receipt, and the existing run
record when terminal.

A future scheduler, distributed worker transport, backend, artifact store, or
resume mechanism replaces only dispatch, transport, or storage adapters. It
must not change entry realization, snapshot identity, processor-plan
projections, attempt/run identity rules, run/study validation, cleanup
semantics, or scoring boundaries. A new processor artifact kind extends the
owning published artifact/profile registry and projection helper rather than
adding a free-form digest field to the executor.

## Gotchas and anti-patterns

Avoid:

- executing a detached entry or validating only the requested entry;
- passing raw experiment authoring input to the executor or redrawing,
  resampling, defaulting, repairing, or selecting a backend during realization;
- duplicating `select_scenario_family()`, SDL target resolution, parameter
  substitution, semantic admission, plan projection, or canonicalization;
- claiming provenance linkage through matching strings without recomputing
  canonical digests and validating the concrete referenced artifacts;
- hashing Python dataclasses, `repr`, mutable runtime snapshots, file paths,
  logs, or backend-native payloads as portable processor provenance;
- using one effectful call through `RuntimeManager` and another through
  `RuntimeControlPlane` for the same attempt;
- sharing a mutable manager, snapshot, target workspace, or control-plane store
  across independent concurrent attempts without the SCE-006 isolation proof
  and live allocator authority;
- treating an idempotent request replay as a new attempt, an attempt retry as a
  scientific replicate, or a retry count as a logical coordinate;
- conflating `run_id`, `plan_entry_id`, `execution_attempt_id`, operation id,
  workflow run id, scheduler job id, cleanup receipt id, and backend-native id;
- overwriting a successful primary result with cleanup failure, or treating
  `destroy()`, compensation, missing resources, or absence of exceptions as a
  verified clean-state receipt;
- storing pending/attempt state in `ExperimentRunModel`, storing archival
  provenance in `RuntimeSnapshot.metadata` or operation details, or storing
  allocation reconciliation in logs/tags/notes;
- using `realized_form_disclosures`, augmentation disclosures, deviations,
  generic `used_refs`, or traceability notes as an untyped substitute for the
  admitted-entry/attempt integrity spine;
- allowing planned facts to masquerade as observed facts, observations as
  selected values, cleanup status as run outcome, or derived scores as
  scheduler decisions; and
- adding a duplicate trial/run schema, loader, validator, exception hierarchy,
  persistence repository, logger, audit stream, workflow, comparison engine,
  or CI pipeline.

## Non-goals and implementation boundaries

- This preflight does not implement #790, SCE-002, or SCE-006.
- It does not add a scheduler, queue, worker pool, allocator, lock manager,
  placement policy, timeout daemon, cleanup engine, run repository, artifact
  service, API, CLI, or MCP tool.
- It does not add another scenario, instantiation, processor, runtime,
  operation, attempt, cleanup, run, study, comparison, or scoring lifecycle.
- It does not alter experiment selection, random streams, factor/condition
  allocation, run-id derivation, backend selection, study stopping rules,
  invalidation semantics, augmentation semantics, or derived-measure
  computation.
- It does not guarantee environmental replay, hidden-state recovery, artifact
  availability, backend equivalence, successful rollback, or that a cleanup
  action proves clean state without the declared probes.
- SCE-006 may call the resulting one-entry seam and supply attempt scheduling
  context. It may not bypass it, mutate its artifacts, or implement private
  comparison/scoring behavior.
