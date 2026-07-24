# Issue 658 SCE-007 Clean-State And Cleanup Contracts Preflight

Date: 2026-07-22

Issue: #658.

Requirement: SCE-007.

This note fixes architecture guardrails for the portable clean-state and
cleanup contract work before implementation. It is guidance only: it does not
publish a schema, contract model, scheduler, worker pool, lock manager,
backend adapter, persistence service, API, fixture set, or implementation
plan.

## Architecture Decisions

- Treat clean state, reusable state, cleanup obligations, cleanup receipts, and
  residual-state disclosure as ACES portable contract semantics. They must not
  be scheduler-private flags, backend-private lifecycle methods, ad hoc
  `RuntimeSnapshot.metadata`, audit details, or free text in manifest
  `constraints`.
- Keep the admitted trial plan as execution intent. It may carry per-entry
  clean-state requirements and cleanup obligations, but it is still not a
  scheduler queue, operation record, runtime snapshot, run, study, evidence
  store, or second trial identity.
- One started trial still archives as one existing `experiment-run-v1` record.
  The plan-entry `run_id`, scheduler job id, control-plane `operation_id`,
  workflow `run_id`, participant `episode_id`, backend-native id, and cleanup
  receipt id are distinct. A retry after execution has side effects needs a
  distinct execution-attempt identity and explicit reset/cleanup/compensation
  policy before it can be admitted.
- Cleanup status is independent from primary trial outcome. A trial can fail
  while cleanup succeeds, and a trial can succeed while cleanup fails or remains
  unverified. Failed or unverified required cleanup invalidates any clean-state
  claim for reuse.
- Required cleanup cannot be silently skipped, converted to best effort, or
  hidden in a successful operation receipt. Required vs best-effort semantics,
  ordering, dependencies, triggers, idempotency, and compensation references
  belong in the portable obligation contract and must be validated before
  scheduling.
- A clean-state or reusable-state claim is scoped to declared resource
  boundaries and observable probes. It never means universal environmental
  reversal. Residual state is disclosed as bounded evidence attached to the
  owned resource boundary that could not be cleaned or verified.
- Workflow compensation remains workflow compensation. Cleanup contracts may
  reference compiled workflow compensation events or compensation targets, but
  they must not redefine the existing workflow compensation state machine as
  resource rollback.
- Backend support is a manifest claim and a conformance/evidence question. If
  existing capability blocks are insufficient, add a governed cleanup/clean-state
  capability surface through the existing `BackendManifest` and
  `BackendCapabilitySet` pattern, with supported contract versions and evidence
  criteria. Do not overload observation, provisioning, or free-form constraints
  with cleanup semantics.
- Scheduling remains subordinate to admission. The scheduler consumes sealed
  plan entries, dispatches over the existing single-scenario control-plane
  path, records attempt/order/timeout/cleanup evidence, and defaults to serial
  execution. SCE-007 owns the portable isolation-evidence contract; bounded
  parallelism execution policy remains SCE-006/#785 scheduler scope and is
  admitted only from explicit isolation evidence over independent range
  instances, capacity, ports, storage, and control-plane locks.

## Required Incumbents

Reuse these repo surfaces before adding anything new:

- **Normative and schema authority:** ADR-009, ADR-019, ADR-061,
  `specs/authority/authority-boundary.yaml`, `ContractModel(extra="forbid")`,
  `schema_bundle()`, `contracts/schemas/`,
  `contracts/schema-publication-manifest.json`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, and `x-aces-invariants` for semantic
  rules JSON Schema cannot enforce.
- **Package boundaries:** ADR-036. Portable DTOs and profile shapes belong in
  `aces_contracts`; trial-set compilation/admission and run-id preallocation in
  `aces_processor`; live execution and control-plane submission in
  `aces_runtime`; backend capability dataclasses/renderers in
  `aces_backend_protocols`; backend-specific mechanics in concrete backend
  packages; conformance probes in `aces_conformance`; operational evidence
  producers in `aces_operations`.
- **Trial and experiment semantics:** ADR-055, ADR-064, ADR-065, ADR-068,
  ADR-074, ADR-084,
  `ExperimentSpecModel`, `ExperimentRunPlanModel`,
  `ExperimentRunAllocationPlanModel`, `ExperimentStochasticControlModel`,
  `TrialCoordinateModel`, `ExperimentRunModel`,
  `ExperimentRunTraceabilityModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentDerivedMeasureModel`, `ExperimentArtifactRefModel`,
  `ExperimentRealizedFormDisclosureModel`,
  `validate_experiment_run_against_task()`, and
  `validate_experiment_study_against_tasks_and_runs()`. Extend these owning
  surfaces where they own the concept; do not add `experiment-trial-v1` or a
  private run/provenance stack.
- **Existing execution path:** `compile_scenario_runtime_model()`, planner
  `plan()`, `ProvisioningPlan`, `OrchestrationPlan`, `EvaluationPlan`,
  `require_plan_operation_identity()`, `RuntimeControlPlane`,
  `OperationReceipt`, `OperationStatus`, `RuntimeSnapshot`,
  `ControlPlaneStore`, and the current single-scenario
  provisioning/orchestration/evaluation submission APIs.
- **Workflow conventions:** `WorkflowExecutionContract`,
  `WorkflowExecutionState`, `WorkflowHistoryEvent`,
  `WorkflowCompensationStatus`, `maybe_apply_compensation()`,
  `workflow_timeout_update()`, and `WorkflowCancellationRequestModel`.
  Cancellation, timeout, abort, retry, and compensation references must compose
  with these surfaces rather than bypass them.
- **Backend declarations and conformance:** `BackendManifest`,
  `BackendCapabilitySet`, `ProvisionerCapabilities`,
  `OrchestratorCapabilities`, `ObservationCapabilities`,
  `backend_manifest_payload()`, `BACKEND_SUPPORTED_CONTRACT_IDS`,
  `participant_runtime_capability_contract_gaps()`,
  `observation_capability_contract_gaps()`,
  `RealizationConformanceHarness`, `RealizationProbeEvidence`,
  `RealizationProbeCase`, and conformance report fields
  `cleanup_verified` and `residual_state`.
- **Backend cleanup mechanics already in use:** `cleanup_native_snapshot()`,
  `TechVaultNativeLibvirtDriver.destroy()`,
  `LibvirtDeploymentDriver.destroy()`,
  `OciDeploymentDriver.destroy()`, deterministic `provider_resource_name()`,
  libvirt owner UUID checks, OCI workspace labels, fixed argv, bounded
  subprocess timeouts, and redacted backend diagnostics.
- **Security and fact-binding patterns:** `ControlPlaneSecurityConfig`,
  `ControlPlaneIdentity`, `ControlPlaneRole`, `request_size_guard_response()`,
  idempotency keys and request fingerprints, append-only `AuditEvent`,
  redacted FastAPI 500 envelopes, `ExperimentParameterModel` redaction,
  runtime fact secret-reference handling, artifact sensitivity, and evidence
  redaction/loss disclosure rules.
- **Verification graph:** ADR-014, `.ground-control.yaml`,
  `.gc/plan-rules.md`, `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/verify_all.py`,
  experiment contract fixtures, runtime contract tests, control-plane API
  tests, random-stream determinism tests, realization conformance tests, and
  libvirt/OCI cleanup tests.

## Cross-Cutting Layers

- **Admitted-plan and contract shape gate.** New clean-state, cleanup,
  execution-attempt, isolation-evidence, and cleanup-receipt payloads must be
  closed `ContractModel` shapes with generated schemas, fixture coverage,
  schema-publication manifest entries, and semantic validators for reference
  resolution, required-vs-best-effort semantics, trigger coverage, duplicate
  ids, cleanup ordering, and receipt-to-obligation binding.
- **SDL and trial-realization gate.** SCE-007 cleanup contracts are carried by
  admitted entries only after ordinary SDL composition, instantiation, semantic
  validation, processor planning, manifest compatibility,
  realization-envelope checks, and admitted plan sealing. The scheduler must
  not parse raw SDL, bind variables, select variation points, randomize,
  allocate `run_id`, or construct scenario snapshots.
- **Control-plane auth and API gate.** Any future scheduling or cleanup API
  must reuse `ControlPlaneSecurityConfig.strict_defaults()`, bearer or
  verified-proxy identity, backend/operator/auditor role checks,
  target scoping, request-size limits, idempotency keys/fingerprints, and audit
  events. Permission to read a schedule summary must not imply permission to
  dereference evidence, read secrets, or mutate cleanup state.
- **Secret-handling gate.** Cleanup obligations, reusable-state claims,
  isolation evidence, receipts, diagnostics, fixtures, argv, logs, and
  telemetry must not contain bearer tokens, credentials, private keys, raw
  secret values, raw environment dumps, hidden answers, backend-native objects,
  process argv, or full tracebacks. Secret material stays as governed
  references resolved only at authorized run-local sinks.
- **Environment and config binding gate.** Ambient environment variables,
  process-global locks, worker-local defaults, backend availability, host wall
  time, or mutable parameter stores cannot affect trial identity, selected
  scenario meaning, or clean-state claims. If a host resource is part of the
  proof, it must be represented as a bounded, evidence-backed lease or probe
  result with a declared owner and resource boundary.
- **OS/process exposure gate.** Backend driver calls must retain existing
  fixed-argv/no-shell discipline, bounded timeouts, image trust policy,
  credential-free libvirt URIs, safe name prefixes, ownership checks, and
  redacted stdout/stderr handling. Scheduler subprocesses or helper tools must
  expose only safe paths, ids, digests, and profile names in argv.
- **Backend capability/admission gate.** Clean-state reuse is admitted only
  when the selected backend manifest declares the required cleanup and
  verification contract versions/capabilities and conformance evidence covers
  them. Unsupported cleanup, unsupported verification, absent probes, or
  backend-private cleanup without portable outcome disclosure fails admission
  whenever clean state is required.
- **Control-plane operation and timeout gate.** Trial execution uses existing
  operation submission, status, cancellation, and timeout reconciliation. A
  timeout/cancellation/abort trigger must produce explicit cleanup disposition
  and attempt provenance rather than relying on an exception or a missing
  result.
- **Workflow compensation gate.** Existing workflow compensation validates
  workflow-visible step history and compensation events. Cleanup may depend on
  those events or cite them as evidence, but resource cleanup receipts remain a
  separate scheduler/contract surface with their own success, failure,
  partial, unsupported, and unverified states.
- **Error-envelope and diagnostics gate.** Admission, scheduling, cleanup, and
  conformance failures use `Diagnostic`/`DiagnosticModel` style codes,
  domains, safe addresses, and bounded messages. HTTP conflict and redacted
  internal-error behavior must remain intact. Diagnostics may name safe ACES
  addresses, obligation ids, resource-boundary ids, counts, statuses, and
  capability ids; they must not echo raw plans, parameter maps, secret refs,
  daemon stderr, native handles, environment, or tracebacks.
- **Persistence and evidence gate.** Mutable control-plane state remains in
  `ControlPlaneStore` operation records and `RuntimeSnapshot`. Durable
  scientific evidence remains experiment run/evidence/artifact/traceability
  contracts. Cleanup receipts and residual disclosures must be immutable
  evidence artifacts or referenced portable receipts, not hidden mutable
  metadata, audit blobs, tags, or backend log files.
- **Logging and observability gate.** Reuse audit events, operation receipts,
  operation statuses, experiment evidence records, and conformance reports.
  Logs may carry safe ids, digests, profile versions, counts, stages, outcomes,
  and durations only. The inspectable clean-state claim must be in the
  portable evidence/receipt graph, not inferred from logs.
- **Parallelism isolation gate.** Serial execution is the default. Any
  non-serial scheduler configuration must pass a closed isolation proof that
  covers independent range instance identity, host capacity, port leases,
  storage namespaces, control-plane locks, cleanup ownership, and cleanup probe
  independence. Missing proof downgrades to serial or fails admission according
  to the configured scheduling policy; it must not silently run in parallel.

## Extensibility Boundary

The required seam is a versioned clean-state/cleanup profile family carried by
admitted trial-plan entries and execution-attempt receipts:

- a closed clean-state mode/profile that distinguishes fresh state, verified
  reset/restoration, declared reusable state, and fresh-range-required
  disposition;
- typed cleanup obligations with owned resource-boundary refs, trigger sets,
  ordering dependencies, idempotency policy, compensation refs, required vs
  best-effort semantics, timeout bounds, and verification probes;
- attempt and receipt identities that bind one execution attempt to its plan
  entry and preallocated run id without becoming a second run id;
- backend capability declarations and conformance fixtures for supported
  cleanup actions, verification probes, reusable-state evidence, and residual
  disclosure; and
- a scheduler isolation-proof profile whose policy parameter is the requested
  parallelism bound. The default bound is one; increasing it requires adding
  proof evidence, not editing trial identity, scenario realization, backend
  lifecycle, or run/study contracts.

Future backend resource kinds, cleanup actions, probe channels, trigger kinds,
or isolation dimensions should extend the owning union/profile, controlled
vocabulary, validator, fixture corpus, and conformance dispatch. They should
not require scheduler branches for every backend or edits to unrelated
scenario, run, study, workflow, or scoring code.

## Gotchas And Anti-Patterns

Avoid:

- implementing a second scenario lifecycle, trial root schema, run identity,
  run repository, scheduler queue schema, comparison engine, or scoring engine;
- treating operation success, workflow success, backend `destroy()` return, or
  absence of exceptions as a clean-state proof without a required portable
  cleanup receipt and verification evidence;
- conflating workflow compensation with resource cleanup or environmental
  rollback;
- downgrading required cleanup to best effort after failure, cancellation,
  timeout, retry, or abort;
- retrying non-idempotent effects under the same attempt identity after
  execution starts;
- reusing state based on backend-private knowledge, tags, mutable snapshots,
  audit logs, or scheduler memory rather than admitted reusable-state evidence;
- using host wall time, worker id, process id, completion order, retry count,
  random UUIDs, or backend availability to derive ordering, identity, or
  clean-state claims;
- placing cleanup obligations or receipts in `RuntimeSnapshot.metadata`,
  `ControlPlaneOperationRecord.details`, raw logs, tags, or backend-native
  payloads instead of the portable contract/evidence surface;
- hiding residual state behind a passing trial outcome or treating partial
  cleanup as clean state;
- adding duplicate schema loaders, validation helpers, exception hierarchies,
  manifest renderers, persistence stores, audit streams, loggers, or CI
  workflows;
- exposing raw secrets, credential refs, environment dumps, process argv,
  daemon stderr, host paths, native handles, or full tracebacks through
  diagnostics, fixtures, evidence, receipts, or logs; and
- using `constraints` strings or prose capability notes as executable cleanup
  or isolation policy.

## Non-Goals And Implementation Boundaries

- This preflight does not implement SCE-007/#658, publish schemas, add
  contract models, mutate backend manifests, add fixtures, or change runtime
  behavior.
- #658/SCE-007 owns the portable clean-state/cleanup contract boundary consumed
  by admitted trial plans and schedulers, including the evidence shape that can
  admit reuse or bounded parallelism. #785/SCE-006 owns scheduling policy,
  placement, worker management, and bounded concurrency behavior.
- The scheduler may order, delay, pause, cancel, retry transport idempotently,
  enforce attempt timeouts, allocate isolated leases, dispatch through the
  existing control plane, and collect cleanup receipts. It must not compose,
  select, randomize, instantiate, allocate archival run ids, compare, score, or
  mutate study allocation.
- Cleanup contracts do not promise manual rollback, universal environmental
  reversal, reconstruction of hidden backend state, artifact availability, or
  exact replay.
- Backend-private cleanup may still exist as implementation detail, but it
  cannot satisfy admission or reuse unless declared through portable capability
  and outcome evidence.
