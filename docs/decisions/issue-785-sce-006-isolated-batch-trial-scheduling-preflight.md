# Issue 785 SCE-006 isolated batch trial scheduling preflight

Date: 2026-07-30

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

The prerequisite repository surfaces from #788, #789, and #790 are now
present: bounded admitted-plan ingress and reconstruction, exact executable
compiler/identity profiles, full-plan isolation joins, one-entry realization
through the public SDL/processor path, and run/attempt/cleanup reconciliation.
SCE-006 must consume those surfaces as shipped; their arrival closes earlier
interface gaps but does not authorize scheduler-local copies.

Two acceptance-critical contract gaps remain. First,
`scheduler-isolation-proof-v1` has no `secret-scope` dimension even though
#785 requires secret-scope isolation. The closed v1 union cannot express that
claim, and a generic evidence ref or cleanup boundary is not an equivalent
typed proof. Non-serial execution must remain disabled until the owning
versioned isolation profile/contract, schema, validator, fixtures, manifest
claims, and conformance evidence can carry it. Second, existing
`OperationReceipt` values acknowledge individual control-plane operations and
`TrialCleanupReceiptModel` reports cleanup; neither is an immutable receipt for
the scheduling decision and complete execution attempt. SCE-006 needs one
portable attempt-evidence authority, not a scheduler-job schema and not an
overload of either incumbent receipt.

The existing execution APIs also do not by themselves prove a bounded
whole-trial timeout. `RuntimeManager.apply()` and the control-plane submission
methods are synchronous at important effect boundaries, and workflow
cancellation covers workflow state rather than every provisioning,
participant, evaluation, and cleanup effect. Abandoning a timed-out thread or
future would let it continue mutating resources while cleanup or another trial
starts. An attempt may claim a bounded timeout only when its selected transport
can fence further effects, reach a known quiescent/terminated state, and then
run cleanup; otherwise admission fails rather than fabricating a timed-out
receipt.

## Architecture decisions and dependency gates

- Every external plan first passes
  `parse_admitted_trial_plan_json()`; every already-typed caller value passes
  `revalidate_admitted_trial_plan()`. The scheduler then calls
  `realize_admitted_trial_entry()` with `TrialRealizationInputs` for one entry.
  Scheduling behavior must not parse experiment authoring input, accept a
  detached entry, or copy private compiler/runtime steps. The #790 boundary is
  fixed in `issue-790-sce-002-trial-realization-provenance-preflight.md`.
- APTL is an outer coordinator over that one-entry path. It may choose when and
  where an already admitted entry runs, but it does not compose SDL, select a
  variation, draw randomness, bind a scenario through a private path, allocate
  `run_id`, interpret experiment factors, aggregate comparisons, or score.
- `realize_admitted_trial_entry()` is the pure entry-to-existing-plans seam,
  not an effectful scheduler or a second lifecycle. One attempt uses either a
  fresh `RuntimeManager.apply()`/`destroy()` path or the existing typed
  `RuntimeControlPlane` submission/status/cancellation path, never both for the
  same effects. Any thin attempt wrapper added for SCE-006 centralizes that
  existing sequence, attempt context, timeout, and cleanup-receipt production;
  worker and scheduling branches must not each reconstruct the lifecycle.
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
  recorded; the scheduler must not silently reinterpret the request. Because
  the current proof contract cannot express secret-scope isolation, its
  effective bound is one for #785 conformance even when its
  `requested_parallelism` is greater.
- The isolation proof is necessary but not a substitute for live allocation.
  Before admitting a concurrent set, the scheduler must hold non-overlapping
  range-instance, host-capacity, port, storage, control-plane-lock, and cleanup
  ownership plus isolated secret-resolution scope for that set. It must recheck
  lease ownership/currentness under the allocator's lock immediately before
  launch and quarantine resources after failed or unverified cleanup.
- Deterministic logical order comes from the admitted
  `trial-coordinate-v1` profile: simple allocations order by numeric replicate
  ordinal; structured allocations order by portable `condition_id`, then
  numeric replicate ordinal. That is the stable baseline, not a mandate that
  every scheduler use one order. A scheduler may apply an explicit,
  deterministic order policy and record the policy plus resulting dispatch
  ordinal without mutating plan identity or entry content. Order does not come
  from plan-entry map iteration, JCS map-key order, `plan_entry_id`, queue
  insertion time, worker availability, completion order, or a random UUID.
  The accepted coordinate profile is implemented by the compiler's
  coordinate/profile helpers but no public post-serialization ordering helper
  currently exists. Before dispatch code lands, promote or extract that owning
  helper once; do not duplicate the baseline sort in APTL. An
  experiment-owned `scheduler-tiebreak` draw may be consumed only when it was
  already admitted and recorded; the scheduler never draws it.
- Actual dispatch and completion events are apparatus evidence, not experiment
  identity. One serialized coordinator commits dispatch decisions in the
  selected deterministic order, even when workers execute concurrently.
  Worker, process, thread, host, lease, operation, workflow, and
  completion-order identifiers never enter plan entry identity, `run_id`,
  selected scenario meaning, or random-stream addresses.
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
  execution control, drives a transport-supported cancellation/fencing path,
  then triggers cleanup and a `timed-out` receipt. A transport without that
  bounded stop guarantee fails admission. Cleanup keeps its own bounded timeout
  and cannot be hidden by the primary outcome.
- Queue/worker status is operational APTL state. Existing
  `OperationReceipt`/`OperationStatus` and `ControlPlaneStore` remain the live
  RAES operation carriers; `TrialCleanupReceiptModel` remains immutable cleanup
  evidence; `ExperimentRunModel` remains the archival record if execution
  starts. Do not put scheduler state or receipts in `RuntimeSnapshot.metadata`,
  operation `details`, audit text, tags, or a new RAES run repository.
- One immutable attempt execution receipt must compose, rather than replace,
  those authorities. It binds the sealed plan/entry/run identities, distinct
  execution-attempt identity, canonical dispatch ordinal and selected
  scheduling policy, effective concurrency, isolation-proof and live-lease
  evidence refs, deadline and primary disposition, control-plane operation
  refs, and cleanup-receipt ref. It carries safe refs and dispositions, not
  queue snapshots, raw lease documents, secrets, backend-native state, or
  comparison results. The existing run attempt linkage references this
  evidence and remains the archival reconciliation owner.

## Canonical incumbents to reuse

- **Lifecycle, package ownership, and identity:** ADR-036, ADR-055, ADR-065,
  ADR-068, ADR-074, ADR-084,
  `specs/formal/scenario-variation-trial-realization/README.md`, the #788
  admitted-plan contract, the #790 one-entry integration, `ExperimentRunModel`,
  `ExperimentStudyModel`, `validate_admitted_trial_run()`,
  `reconcile_admitted_trial_plan()`, `validate_admitted_trial_study()`, and the
  existing task/run/study cross-artifact validators.
- **Admitted-plan ingress and ordering:**
  `parse_admitted_trial_plan_json()`,
  `revalidate_admitted_trial_plan()`,
  `AdmittedTrialPlanModel._validate_plan()`,
  `AdmittedTrialPlanModel._validate_isolation()`, the executable
  `trial-coordinate-v1` semantics in
  `specs/formal/scenario-variation-trial-realization/README.md`, and the
  compiler coordinate/profile helpers. Promote the owning order helper for
  scheduler use instead of adding an APTL ordering implementation.
- **SDL and processing path:** public SDL composition, selection,
  `instantiate_scenario()`, `admit_instantiated_scenario()`,
  `instantiate_admitted_trial_entry()`, `realize_admitted_trial_entry()`,
  `TrialRealizationInputs`, `compile_scenario_runtime_model()`,
  `raes_processor.planner.plan()`, `RuntimeManager.plan()`/`apply()`/`destroy()`,
  and the existing typed
  `ProvisioningPlan`, `OrchestrationPlan`, and `EvaluationPlan` surfaces.
  APTL must call the public one-entry seam instead of reconstructing it.
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
  in `implementations/python/tests/test_sce_006_cleanup_contracts.py`. That
  corpus proves the existing cleanup/isolation contracts, not a batch
  scheduler, and the current isolation union lacks #785's required
  `secret-scope` dimension.
- **Attempt and run evidence:** `OperationReceipt`, `OperationStatus`,
  `TrialExecutionAttemptReferenceModel`, `TrialRunProvenanceModel`,
  `TrialCleanupReceiptModel`, `ExperimentRunModel`,
  `validate_admitted_trial_run()`, and
  `reconcile_admitted_trial_plan()`. The SCE-006 attempt receipt fills only the
  missing scheduling/attempt evidence between these surfaces; it must not copy
  their operation, cleanup, or run payloads.
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
  parameter/secret-reference rules, `RuntimeFactBindingPlane`,
  `RuntimeEnvironmentVariable`, run-local sink authorization,
  `AdmittedTrialPlanIngressError`, and evidence redaction/loss disclosure.
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

ADR-036 is the overarching package gate: neutral portable contracts stay in
`raes_contracts`, pure entry realization stays in `raes_processor`, live
attempt execution stays in `raes_runtime`, backend declarations stay in
`raes_backend_protocols`, and backend mechanics stay in concrete backend
packages. APTL/orchestration code consumes those public surfaces and does not
become a new semantic owner.

1. **Plan parser, shape, and integrity gate.** Use the #788 bounded canonical
   `parse_admitted_trial_plan_json()` loader or
   `revalidate_admitted_trial_plan()` reconstruction, closed
   `ContractModel(extra="forbid")` shape, published schema,
   `x-raes-invariants`, compatibility/version checks, canonical digest, and
   owning semantic validator. Do not add an APTL-only plan DTO, permissive
   dictionary loader, alternate canonicalizer, or partial-entry validation
   shortcut. The plan loader allows at most 32 MiB while
   `ControlPlaneSecurityConfig` defaults to a 1 MiB HTTP request limit. Do not
   raise the global control-plane limit for every endpoint to pass plans
   through it. A scheduling adapter either uses an explicitly validated,
   endpoint-scoped bound no larger than the plan ingress bound, or accepts a
   safe immutable plan-artifact reference whose authorized bytes still pass
   the canonical loader.
2. **Plan-to-schedule semantic join.** Resolve every scheduled
   `plan_entry_id`, cleanup plan, `run_id`, selected apparatus reference, and
   isolation-proof entry against the exact sealed plan.
   `AdmittedTrialPlanModel._validate_isolation()` already checks proof
   membership and rejects shared declared cleanup resources, while
   `SchedulerIsolationProofModel` checks dimensions and bounds. Reuse both;
   APTL adds only the live lease/currentness join and must not duplicate their
   portable checks. The existing model does not check secret-scope isolation;
   that is a versioned portable-contract gap, not an APTL-local boolean.
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
   control-plane/store locks, non-shared secret scopes/resolution contexts, and
   cleanup/probe ownership. Release to the pool only after verified cleanup.
   Until the portable proof contract can express every one of those dimensions,
   the effective concurrency bound remains one. Distinct free-form reference
   strings are not proof of distinct physical resources: the allocator must
   canonicalize aliases, issue ownership/fencing generations, and reject a
   stale worker before launch or cleanup.
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
   Concurrent attempts require distinct authorized secret-resolution scopes;
   using one broad worker credential, resolver cache, injected environment, or
   secret mount across workers is cross-trial contamination, even when the raw
   value is never serialized.
   `requested_parallelism` comes from the validated proof; admitted attempt and
   cleanup timeouts come from the entry/cleanup plan. APTL-owned fallback and
   stop-undispatched policies, if supported, use its closed canonical config
   validator. Ambient environment, worker defaults, backend defaults, and
   mutable global configuration cannot override those values or alter plan
   meaning or identity.
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
   the declared probes and `validate_trial_cleanup_receipt()` pass. A generic
   thread/future timeout does not cancel synchronous runtime effects. Cleanup
   starts only after the attempt transport proves quiescence or fences the
   worker from further writes, and a cleanup engine must execute the admitted
   obligation/probe kinds through declared backend capabilities rather than
   synthesize a receipt from `RuntimeManager.destroy()`.
10. **Error-envelope gate.** Expected failures use bounded
    `Diagnostic`/`DiagnosticModel` codes, domains, JSON-pointer addresses, and
    safe messages. Preserve the backend adapter rule that reports exception
    type without exception text and the HTTP redacted 500 response. Do not echo
    raw Pydantic input, plans, selected values, secret refs, lease payloads,
    host paths, stderr, native ids, environment, or tracebacks through 4xx
    details, logs, receipts, or evidence. Existing operation routes render
    caught `ValueError` text in a 409 response, so scheduler/attempt adapters
    must translate failures to governed safe messages before that boundary;
    raw validator or allocator exceptions must never be forwarded unchanged.
11. **Persistence, logging, and archival gate.** Persist enough operational
    correlation to recover idempotently after coordinator/worker restart:
    safe plan/entry/attempt ids, canonical dispatch ordinal, operation ids,
    lease refs, deadlines, and cleanup disposition. Reuse APTL's canonical
    operational store; if it has none, that is a downstream durability design
    prerequisite, not a reason to overload the RAES runtime or archival stores.
    Logs and audit may carry safe ids, digests, versions, counts, stages,
    outcomes, and durations only. Actual run facts and cleanup evidence enter
    their portable run/evidence/receipt graph. Scheduling facts enter the
    immutable attempt receipt and are joined by run reconciliation; none of
    these facts are inferred from logs.

## Reliability and evidence guardrails

- A coordinator crash after dispatch but before recording completion must
  reconcile the existing idempotent operation before issuing work again.
  Unknown effect state is not permission to retry; apply the admitted
  reset/compensation rule or fail and clean up.
- A lease carries a fencing generation. A restarted coordinator or delayed
  worker must not launch, publish success, or clean resources after that
  generation is superseded.
- Acquiring all but one required isolation dimension cannot leave a partial
  concurrent allocation. Release or quarantine the complete attempted lease
  set without dispatch.
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
- A prior `declared-reusable` or `verified-clean` claim is evidence scoped to
  exact boundaries and probes, not a perpetual cache flag. Reuse rechecks the
  claim, lease ownership, evidence availability, and any profile freshness
  rule immediately before dispatch.
- Per-trial evaluation may run through the existing `EvaluationPlan` as part of
  the single-scenario lifecycle. Cross-trial comparison, aggregation, stopping
  analysis, ranking, reward, and scoring remain study/evaluator concerns and
  cannot enter scheduler dispatch policy.

## Conformance boundary

Use the existing contract fixtures, pytest/nox sessions, determinism/property
patterns, and repository verification graph; do not add a scheduler-specific
fixture runner or CI workflow. SCE-006 conformance must distinguish at least:

- serial default with no parallel proof, plus an explicit recorded
  fail-versus-serial-fallback decision for a rejected parallel request;
- identical plan/entry/run identity and canonical dispatch decisions under
  worker, process, partition, and completion-order permutations;
- rejection of shared or aliased range, capacity, port, storage, lock, cleanup,
  or secret scope, including proof evidence that is stale at dispatch;
- idempotent transport replay versus a policy-authorized new attempt id, with
  every attempt joined to operation, attempt, cleanup, and run evidence;
- success, primary failure, cancellation, timeout, abort, coordinator crash,
  partial allocation, cleanup failure, unverified cleanup, and quarantine; and
- contamination fixtures proving that failed/unverified cleanup, a live stale
  worker, or one shared isolation dimension can never be reported as a clean
  successful reusable trial.

## Extensibility seam

The seam is the existing pure one-entry realizer plus one centralized
effectful attempt path, wrapped by a bounded scheduling policy whose
authoritative inputs are:

- the admitted plan identity and an owning helper for the declared coordinate
  profile's canonical order;
- an explicit closed deterministic scheduler order policy and its recorded
  dispatch ordinals;
- `SchedulerIsolationProofModel.requested_parallelism` and proof/profile
  version;
- live owned allocation/lease evidence for the proof's closed dimensions;
- admitted attempt timeout, retry, and `TrialCleanupPlanModel`; and
- an optional already-admitted deterministic tie-break value; plus
- explicit APTL-owned parallel-admission fallback and batch
  stop-undispatched policy, when those behaviors are supported.

The effective bound is one by default. It cannot exceed the proof, APTL's
validated deployment ceiling, live capacity, or number of eligible entries.
A future distributed worker transport, backend, or APTL range allocator should
replace only dispatch and lease mechanics. It must not change plan identity,
entry realization, run/study provenance, cleanup semantics, or scoring
boundaries.

Adding a portable isolation dimension, attempt disposition, cleanup action, or
proof profile extends the owning closed contract, validator, schema-publication
record, fixtures, manifest capability, and conformance evidence under ADR-061.
It is not added as an APTL-only string, free-form constraint, environment
variable, or backend branch. `secret-scope` is the immediate required instance
of that rule. A future attempt-evidence revision extends the one receipt's
closed disposition/evidence vocabularies; it does not add per-transport receipt
types.

## Gotchas and anti-patterns

Avoid:

- starting #785 against raw experiment authoring or bypassing the admitted-plan
  and one-entry realization surfaces now exposed by #788/#790;
- deriving identity or logical order from array position, worker number,
  queue/completion order, wall time, retry count, process id, host, or random
  UUID;
- allowing worker threads/processes to race on a shared queue and calling the
  resulting order deterministic;
- treating a structurally valid isolation proof, capacity estimate, successful
  probe, or allocator log as a current exclusive lease;
- treating cleanup ownership, a generic evidence ref, separate worker
  processes, or non-serialization of raw secret values as proof of isolated
  secret scope;
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
- treating `OperationReceipt`, `TrialCleanupReceiptModel`, or
  `TrialExecutionAttemptReferenceModel.operation_refs` alone as the complete
  scheduling/attempt receipt;
- enforcing attempt timeout by abandoning a thread/future while it can still
  mutate state, or starting cleanup before effect quiescence/fencing;
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
