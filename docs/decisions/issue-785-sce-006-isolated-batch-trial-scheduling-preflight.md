# Issue 785 SCE-006 isolated batch trial scheduling preflight

Date: 2026-07-28

Issue: #785.

Requirement: SCE-006.

This note fixes the scheduler boundary before implementation. It is guidance
only: it does not add an admitted-plan contract, scheduler, queue, worker pool,
lock manager, backend adapter, API, persistence service, fixture, or
implementation plan.

ADR-084 already decides the lifecycle and authority boundaries. The portable
clean-state, cleanup, retry, and parallel-isolation contracts are already
defined by
`specs/formal/scenario-variation-trial-realization/cleanup-contracts.md` and
issue #658. No new ADR is required.

## Architecture decisions and dependency gates

- #788 must first publish the closed, integrity-bound admitted trial-plan
  contract. #790 must identify the public one-entry realization/execution path
  that preserves SDL instantiation and existing run provenance. Scheduling
  behavior must not land by guessing those interfaces, parsing experiment
  authoring input, or copying private compiler/runtime steps.
- APTL is an outer coordinator over that one-entry path. It may choose when and
  where an already admitted entry runs, but it does not compose SDL, select a
  variation, draw randomness, bind a scenario through a private path, allocate
  `run_id`, interpret experiment factors, aggregate comparisons, or score.
- Validate and integrity-check the complete admitted plan before dispatching
  any entry. Per-entry consumption is allowed only after that whole-plan gate;
  extracting one structurally valid entry from an invalid, incomplete, stale,
  duplicate, or tampered plan is forbidden.
- Serial execution is the default and needs no parallel-isolation evidence.
  A requested bound greater than one may dispatch only entries named by one
  valid `SchedulerIsolationProofModel`, after the proof is joined to the exact
  admitted plan and its evidence is still valid at dispatch. Missing,
  non-independent, stale, conflicting, or unavailable evidence means no
  parallel dispatch. Any declared serial fallback must be explicit and
  recorded; the scheduler must not silently reinterpret the request.
- The isolation proof is necessary but not a substitute for live allocation.
  Before admitting a concurrent set, the scheduler must hold non-overlapping
  range-instance, host-capacity, port, storage, control-plane-lock, and cleanup
  ownership for that set. It must recheck lease ownership/currentness under the
  allocator's lock immediately before launch and quarantine resources after
  failed or unverified cleanup.
- Deterministic logical order comes from the admitted plan's canonical logical
  coordinate/order key, not serialized list position, queue insertion time,
  worker availability, completion order, or a random UUID. If #788 does not
  publish an unambiguous canonical order key, that contract gap must be fixed
  there before scheduling. An experiment-owned `scheduler-tiebreak` draw may be
  consumed only when it was already admitted and recorded; the scheduler never
  draws it.
- Actual dispatch and completion events are apparatus evidence, not experiment
  identity. One serialized coordinator commits dispatch decisions in canonical
  order, even when workers execute concurrently. Worker, process, thread, host,
  lease, operation, workflow, and completion-order identifiers never enter plan
  entry identity, `run_id`, selected scenario meaning, or random-stream
  addresses.
- `plan_entry_id`, preallocated archival `run_id`, execution-attempt id,
  scheduler job id, control-plane `operation_id`, workflow run id, cleanup
  receipt id, and backend-native id remain distinct. A transport replay with
  the same idempotency key/fingerprint returns the original operation. A later
  effect-capable attempt has a new execution-attempt id and must satisfy the
  admitted retry/reset/compensation policy. It is not an experimental
  replicate; a genuine new trial observation requires a newly admitted
  coordinate and `run_id`.
- Trial-attempt timeout, workflow timeout, participant deadline, scenario
  logical time, control-plane request timeout, cleanup-obligation timeout, and
  lease expiry are separate concepts. Attempt timeout uses the admitted entry's
  execution control, drives the existing cancellation/timeout path, then
  triggers cleanup and a `timed-out` receipt. Cleanup keeps its own bounded
  timeout and cannot be hidden by the primary outcome.
- Queue/worker status is operational APTL state. Existing
  `OperationReceipt`/`OperationStatus` and `ControlPlaneStore` remain the live
  RAES operation carriers; `TrialCleanupReceiptModel` remains immutable cleanup
  evidence; `ExperimentRunModel` remains the archival record if execution
  starts. Do not put scheduler state or receipts in `RuntimeSnapshot.metadata`,
  operation `details`, audit text, tags, or a new RAES run repository.

## Canonical incumbents to reuse

- **Lifecycle and identity:** ADR-055, ADR-065, ADR-068, ADR-074, ADR-084,
  `specs/formal/scenario-variation-trial-realization/README.md`, the #788
  admitted-plan contract, the #790 one-entry integration, `ExperimentRunModel`,
  `ExperimentStudyModel`, and their task/run/study cross-artifact validators.
- **SDL and processing path:** public SDL composition, selection,
  `instantiate_scenario()`, `admit_instantiated_scenario()`,
  `compile_scenario_runtime_model()`, `raes_processor.planner.plan()`,
  `RuntimeManager.plan()`/`apply()`, and the existing typed
  `ProvisioningPlan`, `OrchestrationPlan`, and `EvaluationPlan` surfaces.
  #790 must make the supported one-entry composition of these incumbents
  explicit; APTL must call that public seam instead of reconstructing it.
- **Control plane and workflow:** `RuntimeControlPlane.submit_provisioning()`,
  `submit_orchestration()`, `submit_evaluation()`, `get_operation()`,
  `cancel_workflow()`, `reconcile_workflow_timeouts()`,
  `WorkflowExecutionContract`, `WorkflowExecutionState`,
  `WorkflowHistoryEvent`, `WorkflowCancellationRequestModel`,
  `workflow_timeout_update()`, and `maybe_apply_compensation()`.
- **Isolation and cleanup:** `TrialCleanupPlanModel`,
  `TrialCleanupReceiptModel`, `SchedulerIsolationProofModel`,
  `validate_trial_cleanup_receipt()`,
  `require_cleanup_plan_capability()`, `CleanupCapabilities`,
  backend manifest contract-version checks, and the SCE-006 fixture/test corpus
  in `implementations/python/tests/test_sce_006_cleanup_contracts.py`.
- **Backend safety:** `BackendManifest`, realization-envelope admission,
  `provider_resource_name()`, ownership-safe/idempotent backend `destroy()`
  methods, `cleanup_native_snapshot()`, libvirt owner UUID checks,
  credential-free connection-URI validation, safe name/path helpers, private
  seed-file creation, fixed argv/no-shell subprocesses, bounded subprocess
  timeouts, and redacted backend diagnostics.
- **Security and delivery:** `ControlPlaneSecurityConfig.strict_defaults()`,
  `ControlPlaneIdentity`, `ControlPlaneRole`, target binding, request-size
  guards, idempotency keys and request fingerprints, append-only `AuditEvent`,
  the redacted HTTP 500 envelope, `Diagnostic`/`DiagnosticModel`, experiment
  parameter/secret-reference rules, runtime fact sink authorization, and
  evidence redaction/loss disclosure.
- **Persistence and observability:** `ControlPlaneStore`,
  `LocalControlPlaneStore`, `ControlPlaneOperationRecord`,
  `operational_apparatus_summary()`, experiment evidence/artifact/traceability
  contracts, `is_valid_run_id_label()`, `run_artifact_path()`, and atomic
  artifact writers.
- **Repository workflow:** ADR-009, ADR-014, ADR-019, ADR-061,
  `specs/authority/authority-boundary.yaml`, `.ground-control.yaml`,
  `.gc/plan-rules.md`, `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, and `tools/verify_all.py`.

The similarly named modules under `raes_runtime.participant_scheduler*` govern
participant actions inside one scenario. They are not a batch-trial scheduler,
host-capacity allocator, range pool, or reusable worker framework. Likewise,
participant resource-budget pools do not prove host, port, storage, range, or
control-plane isolation between trials.

## Cross-cutting layers the design must pass

1. **Plan parser, shape, and integrity gate.** Use the #788 bounded canonical
   loader/model, closed `ContractModel(extra="forbid")` shape, published
   schema, `x-raes-invariants`, compatibility/version checks, canonical digest,
   and owning semantic validator. Do not add an APTL-only plan DTO, permissive
   dictionary loader, alternate canonicalizer, or partial-entry validation
   shortcut.
2. **Plan-to-schedule semantic join.** Resolve every scheduled
   `plan_entry_id`, cleanup plan, `run_id`, selected apparatus reference, and
   isolation-proof entry against the exact sealed plan. The structural
   `SchedulerIsolationProofModel` currently validates dimensions and bounds,
   but not membership in a particular plan; that cross-artifact join belongs
   beside the admitted-plan/cleanup semantic validators, following
   `validate_trial_cleanup_receipt()`, rather than as duplicated APTL-local
   checks.
3. **SDL, processor, and apparatus admission gate.** Each entry has already
   passed composition, selection, instantiation, whole-scenario semantic
   admission, manifest compatibility, realization-envelope, and cleanup
   capability checks. Dispatch rechecks version/digest/capability drift and
   fails visibly; it never substitutes a scenario, backend, configuration,
   range, or selected value.
4. **Live isolation gate.** Join the proof to current owned allocations and
   enforce the effective concurrency bound atomically. Evidence must identify
   independent range instances, sufficient reserved host capacity,
   non-overlapping port leases, distinct storage namespaces, mutually exclusive
   control-plane/store locks, and cleanup/probe ownership. Release to the pool
   only after verified cleanup.
5. **Authentication and authorization gate.** Any scheduling API reuses
   fail-closed identity, mutating-role authorization, target scoping,
   request-size limits, idempotency/fingerprint conflict handling, and audit.
   Plan visibility, evidence dereference, secret resolution, lease mutation,
   control-plane submission, cancellation, and cleanup are separate
   permissions. A broad scheduler token must not be serialized into jobs or
   shared with workers through argv.
6. **Secret and configuration gate.** Portable plans contain governed secret
   references only. Resolve them at authorized run-local sinks and exclude raw
   values and sensitive locator details from identity, proof, persistence,
   diagnostics, audit, logs, telemetry, fixtures, and cleanup receipts.
   Scheduler parallelism, ordering, timeout, and fallback policy are explicit
   validated inputs; ambient environment, worker defaults, backend defaults,
   and mutable global configuration cannot alter plan meaning or identity.
7. **OS/process exposure gate.** Use per-attempt private work/storage
   namespaces, safe bounded names, containment-validated paths, fixed argv,
   controlled working directories, no `shell=True`, bounded timeouts, captured
   redacted output, credential-free URIs, and backend ownership checks.
   Credentials, tokens, secret refs, parameter maps, raw plans, environment
   dumps, native handles, and daemon output do not appear in argv or process
   titles.
8. **Control-plane and concurrency gate.** Reuse idempotency keys/fingerprints
   for transport replay and operation status for observation. The
   `RuntimeControlPlane` participant `RLock` is process-local, and
   `LocalControlPlaneStore` atomic replacement is not a cross-process lock.
   A parallel scheduler therefore needs independent per-trial targets/store
   namespaces or APTL's canonical external lock authority; it must not cite
   those RAES implementation details as proof of cross-trial isolation. The
   APTL repository must identify that authority and its own config validators
   before coding; this repository cannot certify an unnamed downstream lock.
9. **Timeout, cancellation, retry, and cleanup gate.** A timeout or cancellation
   first records the primary disposition, uses the existing control path where
   applicable, and then runs every triggered cleanup obligation in dependency
   order. Backend `destroy()` return, workflow compensation, operation success,
   missing exceptions, or a missing resource is not clean-state evidence until
   the declared probes and `validate_trial_cleanup_receipt()` pass.
10. **Error-envelope gate.** Expected failures use bounded
    `Diagnostic`/`DiagnosticModel` codes, domains, JSON-pointer addresses, and
    safe messages. Preserve the backend adapter rule that reports exception
    type without exception text and the HTTP redacted 500 response. Do not echo
    raw Pydantic input, plans, selected values, secret refs, lease payloads,
    host paths, stderr, native ids, environment, or tracebacks through 4xx
    details, logs, receipts, or evidence.
11. **Persistence, logging, and archival gate.** Persist enough operational
    correlation to recover idempotently after coordinator/worker restart:
    safe plan/entry/attempt ids, canonical dispatch ordinal, operation ids,
    lease refs, deadlines, and cleanup disposition. Reuse APTL's canonical
    operational store; if it has none, that is a downstream durability design
    prerequisite, not a reason to overload the RAES runtime or archival stores.
    Logs and audit may carry safe ids, digests, versions, counts, stages,
    outcomes, and durations only. Actual run facts and cleanup evidence enter
    their portable run/evidence/receipt graph; they are never inferred from
    logs.

## Reliability and evidence guardrails

- A coordinator crash after dispatch but before recording completion must
  reconcile the existing idempotent operation before issuing work again.
  Unknown effect state is not permission to retry; apply the admitted
  reset/compensation rule or fail and clean up.
- Acquiring five isolation dimensions and then failing the sixth cannot leave a
  partial concurrent allocation. Release or quarantine the complete attempted
  lease set without dispatch.
- Cleanup runs after success, failure, cancellation, timeout, abort, and every
  admitted effect-capable retry trigger. Cleanup failure is preserved even when
  the trial succeeded, and it prevents reuse or release to the schedulable pool.
- One trial's failure or cleanup delay must not cancel, mutate, resample, or
  re-identify another entry unless an explicit batch cancellation policy says
  to stop undispatched work. Started entries still complete their own
  cancellation and cleanup obligations.
- Parallel workers never share a mutable `RuntimeManager`,
  `RuntimeControlPlane`, `RuntimeSnapshot`, local control-plane directory,
  backend workspace, port lease, or cleanup boundary unless the isolation proof
  and live lock authority explicitly establish an independent partition.
- Per-trial evaluation may run through the existing `EvaluationPlan` as part of
  the single-scenario lifecycle. Cross-trial comparison, aggregation, stopping
  analysis, ranking, reward, and scoring remain study/evaluator concerns and
  cannot enter scheduler dispatch policy.

## Extensibility seam

The seam is the existing one-entry executor wrapped by a bounded scheduling
policy whose authoritative inputs are:

- the admitted plan identity and its canonical entry order key;
- `SchedulerIsolationProofModel.requested_parallelism` and proof/profile
  version;
- live owned allocation/lease evidence for the proof's closed dimensions;
- admitted attempt timeout, retry, and `TrialCleanupPlanModel`; and
- an optional already-admitted deterministic tie-break value.

The effective bound is one by default. It cannot exceed the proof, live
capacity, or number of eligible entries. A future distributed worker transport,
backend, or APTL range allocator should replace only dispatch and lease
mechanics. It must not change plan identity, entry realization, run/study
provenance, cleanup semantics, or scoring boundaries.

Adding a portable isolation dimension, attempt disposition, cleanup action, or
proof profile extends the owning closed contract, validator, schema-publication
record, fixtures, manifest capability, and conformance evidence under ADR-061.
It is not added as an APTL-only string, free-form constraint, environment
variable, or backend branch.

## Gotchas and anti-patterns

Avoid:

- starting #785 against raw experiment authoring or before #788/#790 expose the
  admitted-plan and one-entry execution boundaries;
- deriving identity or logical order from array position, worker number,
  queue/completion order, wall time, retry count, process id, host, or random
  UUID;
- allowing worker threads/processes to race on a shared queue and calling the
  resulting order deterministic;
- treating a structurally valid isolation proof, capacity estimate, successful
  probe, or allocator log as a current exclusive lease;
- citing `RLock`, atomic file replacement, participant action concurrency, or
  participant resource budgets as cross-process/cross-trial isolation;
- silently raising worker count above the proof, silently falling back from an
  invalid parallel request, or letting worker availability change the admitted
  trial set;
- sharing one runtime snapshot, control-plane store directory, backend
  workspace, port set, storage namespace, or cleanup owner across concurrent
  trials without proven partitioning;
- retrying an effect-capable operation under a new request body with the same
  idempotency key, or treating repeated attempts as scientific replicates;
- using workflow compensation as resource cleanup, using backend teardown as a
  verified receipt, or returning failed-cleanup resources to the pool;
- conflating attempt timeout with logical scenario time, workflow timeout,
  cleanup timeout, lease expiry, or a study stopping rule;
- persisting scheduler truth in `RuntimeSnapshot.metadata`, operation details,
  audit text, logs, tags, backend state, or a duplicate run/trial repository;
- putting raw secrets, secret locators, tokens, plans, parameter maps, native
  handles, host paths, argv, environment dumps, stdout/stderr, or tracebacks in
  jobs, diagnostics, logs, receipts, fixtures, or evidence;
- adding duplicate plan/cleanup DTOs, schema loaders, canonicalizers, semantic
  validators, exception hierarchies, loggers, audit streams, persistence
  stores, or CI workflows; and
- making scheduler success, throughput, completion order, or cleanup outcome a
  comparison/scoring result.

## Non-goals and implementation boundaries

- This preflight does not implement #785/SCE-006 or modify #788/#790.
- It does not publish a scheduler queue/job/worker contract or make APTL
  operational state part of the RAES portable semantic model.
- It does not define a second scenario, trial, run, workflow, operation,
  cleanup, comparison, or scoring lifecycle.
- It does not compile or admit plans, instantiate scenarios, allocate archival
  run ids, select/randomize/resample entries, resolve secrets, or mutate study
  allocation.
- It does not promise universal rollback, exact replay, hidden-state recovery,
  artifact availability, backend equivalence, or that serial execution alone
  proves clean state.
- It does not certify an APTL allocator or deployment. A downstream APTL
  preflight must identify its canonical range, capacity, port, storage, lock,
  persistence, cleanup, configuration-validation, and error-envelope
  authorities. The implementation must bind the portable proof to those
  incumbents and produce evidence through the established RAES contracts.
