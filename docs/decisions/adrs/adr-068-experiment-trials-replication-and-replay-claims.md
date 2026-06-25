# ADR-068: Experiment Trials, Replication, and Replay Claims

## Status

accepted

## Date

2026-06-25

## Classification

Classification: FM2
Required artifacts: ADR, formal spec, preflight guardrails, clause matrix
Waivers: No new schema, fixture, contract-source, or runtime artifacts are
required because the existing experiment-core contracts already carry the
trial, replication, reproducibility, and replay-claim support surfaces. This
ADR fixes the interpretation boundary and leaves future producer, storage,
API, and replay-execution work to spawned implementation issues.

## Context

Issue #105 is the joint design surface for:

- EXP-706: repeated runs, replications, and controlled variation across runs of
  the same task or study.
- EXP-712: reproducibility and replay claims through preserved run context,
  evidence, provenance, and derived-result lineage.

ADR-055 established experiment tasks, runs, studies, and apparatus context.
ADR-064 separated capture specifications, raw evidence records, derived
measures, and backend observation capability. ADR-065 made
`experiment-run-v1` the canonical archival run provenance record with
traceability and realized-form disclosures. ADR-066 separated authored,
operational, captured-evidence, and derived-analysis planes.

Those decisions intentionally avoid a parallel run or provenance stack. The
remaining issue is how to name trials, replications, controlled variation,
reproducibility support, and replay support without adding duplicate root
schemas for facts already carried by task, run, study, evidence, derived
measure, apparatus, and traceability contracts.

## Decision

### 1. A trial is one archival run

For the current experiment-core model, one trial is one archival
`experiment-run-v1` record. The run is the record that binds the task reference,
scenario snapshot, apparatus context, participant implementation provenance,
parameters, stochastic controls, clocks, timestamps, evidence artifacts, result
summaries, traceability, disclosures, and lineage refs for a specific
execution.

ACES does not add `experiment-trial-v1`, a trial root schema, or a trial
service for the same execution facts. Future terminology may call a run a
trial in user-facing research workflows, but the portable artifact remains the
run contract.

### 2. Repeated runs are multiple run records

Repeated runs of the same task are represented by multiple
`experiment-run-v1` records with distinct `run_id` values, a shared `task_ref`,
and a compatible `scenario_snapshot_ref`. A repeated run must not be modeled as
a mutable status update, tag, operation id, workflow id, runtime snapshot id,
participant episode id, or backend-native execution id.

The existing task/run validator remains the semantic gate for task identity,
scenario snapshot compatibility, apparatus constraints, declared metrics, and
evidence requirements.

### 3. Replication and controlled variation are study allocation semantics

Replication, cohort, benchmark, comparison, and controlled-variation claims
belong in `experiment-study-v1`, especially:

- study membership entries with `evaluation-run` roles and condition
  groupings;
- declared factors, factor levels, blocking factors, and analysis plans;
- `run_allocation.compared_conditions`;
- condition assignments with auditable run-level criteria;
- `target_runs_per_condition`;
- `replication_policy`; and
- `stopping_rule`.

Condition-assignment evidence must be grounded in inspectable run-level facts
such as participant implementation provenance, processor or backend identity,
apparatus context, selected manifests, capability declarations, measurement
channels, task or scenario snapshot identity, non-opaque parameters, and
stochastic controls. It must not depend on free-form tags, opaque `other`
parameters, runtime metadata, audit blobs, or backend-private logs.

### 4. Replay support is claim support, not replay execution

ACES supports reproducibility and replay claims by preserving enough context,
evidence, provenance, and lineage to inspect the claim. It does not claim that
the current contracts can execute a replay workflow, fetch external artifacts,
recreate hidden backend state, or recompute every derived result.

Replay and reproducibility support use the existing claim-support chain:

1. `experiment-run-v1` binds the task, scenario snapshot, apparatus,
   participant implementation, parameters, stochastic controls, timestamps,
   evidence artifacts, result summaries, realized-form disclosures,
   augmentation disclosures, and lineage refs.
2. `experiment-run-v1.traceability` links capture specifications, raw evidence
   records, derived measures, and claim/report/analysis refs.
3. `experiment-evidence-record-v1` records raw captured observations and the
   capture requirement they claim to satisfy.
4. `experiment-derived-measure-v1` records interpreted outputs and cites source
   evidence records.
5. Claim refs in run traceability are valid only when grounded by
   derived-measure refs.

Claim strength is limited by preserved artifacts, redaction, loss disclosure,
observer effects, unsupported runtime surfaces, availability of external
artifacts, and disclosed apparatus limitations.

### 5. Runtime surfaces remain future work

Future producer, retrieval, storage, or replay-execution APIs must emit and
validate the same canonical task, run, study, evidence, derived-measure,
apparatus, and traceability contracts. They must reuse the existing
control-plane identity, authorization, request-size, audit, idempotency,
diagnostic, and redacted-error patterns before dereferencing or publishing
evidence content.

## Required Boundaries

- Trial identity is run identity.
- Repetition is a set of distinct run records, not a mutation of one run.
- Replication and controlled variation are study allocation facts, not tags.
- Replay support is the preserved claim-support graph, not guaranteed
  re-execution.
- Raw evidence, derived measures, run summaries, and claims remain separate.
- Capture specifications state intent; evidence records state captured raw
  observations; derived measures state interpretation.
- Live control-plane state, runtime snapshots, operation statuses, participant
  histories, workflow ids, audit logs, diagnostics, and backend-native logs are
  not canonical trial, replication, or replay-claim records.
- Secrets, hidden answers, raw prompts, bearer tokens, private keys, raw
  environment dumps, process argv, backend-private objects, and full tracebacks
  must not be serialized into portable experiment records, fixtures, logs, or
  examples.

## Implementation Mapping

Issue #105 is satisfied by this ADR, the experiment-core formal specification,
the preflight guardrail notes for EXP-706 and EXP-712, and the
EXP-706/EXP-712 clause matrix in
`docs/research/experiment-core/traceability-matrix-exp-706-712.md`.

Existing executable gates already enforce the load-bearing clauses:

- `ExperimentRunModel._validate_archival_run()` keeps one run archival and
  complete, including timestamps, evidence, result summaries, participant
  implementation provenance, and disclosure evidence.
- `validate_experiment_run_against_task()` binds runs to task identity,
  scenario snapshot compatibility, apparatus constraints, declared metrics, and
  evidence requirements.
- `ExperimentRunAllocationPlanModel._validate_condition_assignments()` and
  `validate_experiment_study_against_tasks_and_runs()` validate compared
  conditions, condition assignments, blocking factors, target runs per
  condition, evaluation-run eligibility, and analysis metric grounding.
- `ExperimentRunTraceabilityModel._validate_run_traceability()` requires run
  traceability through capture specifications and evidence records, and
  prevents claim refs from floating free of derived-measure refs.
- `ExperimentDerivedMeasureModel._validate_derived_measure()` requires derived
  measures to cite source evidence records.

The structural test coverage for those gates remains in
`implementations/python/tests/test_runtime_contracts.py`.

## Alternatives Considered

### Add `experiment-trial-v1`

Rejected. The proposed trial artifact would duplicate `experiment-run-v1`
identity, apparatus, timestamps, evidence, results, provenance, and lineage.
The run is already the archival record for one task execution.

### Add a replay or reproducibility-claim root schema

Rejected. The existing traceability chain already separates capture
specifications, raw evidence, derived measures, and claim refs. A new root
would split claim authority and make consumers reconcile parallel provenance
graphs.

### Encode replications with tags or free-form notes

Rejected. Replication and controlled variation need declared factors,
condition assignments, run allocation, target counts, stopping rules, analysis
plans, and validity notes. Tags cannot express those constraints or support
semantic validation.

### Implement runtime replay with this issue

Rejected. Issue #105 fixes the design boundary. Runtime replay, artifact
retrieval, retention storage, query APIs, scheduling, and derived-measure
recalculation require separate producer and control-plane work.

## Consequences

### Positive

- The experiment-core model has one authoritative meaning for trial,
  repetition, replication, controlled variation, reproducibility support, and
  replay support.
- Existing contract validators remain the executable authority instead of
  adding duplicate schema and runtime stacks.
- Future replay or reproducibility tooling can add producer and API behavior
  without changing the portable artifact identities.

### Negative / Costs

- User-facing tools that prefer the term "trial" must map it explicitly to a
  run record.
- Reproducibility and replay claims remain reviewable support claims, not
  guarantees of executable replay.

### Risks

- Implementers may overstate replayability by treating sealed references as
  proof that external artifacts still exist or are authorized for dereference.
- Study authors may try to infer replication from repeated operations without
  publishing run records and study allocation. Validators and review guidance
  must continue to reject those shortcuts.
