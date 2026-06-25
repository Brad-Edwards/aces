# EXP-706/EXP-712 Clause Matrix

Date: 2026-06-25

Issue: #105.

Requirements: EXP-706, EXP-712.

This matrix maps the joint trial/replication and reproducibility/replay design
to the documentation artifacts and incumbent executable gates. It is a
docs-only acceptance artifact for ADR-068; it does not add new contract,
schema, fixture, runtime, storage, or API behavior.

## Matrix

| Requirement | Clause | Design Artifact | Existing Gate Or Evidence |
|-------------|--------|-----------------|---------------------------|
| EXP-706 | One trial is one archival run record, not a new trial schema. | ADR-068 decision 1; experiment-core formal spec `Run` definition and separation invariants 21-22. | `ExperimentRunModel._validate_archival_run()` keeps a run archival and complete. |
| EXP-706 | Repeated runs of the same task are distinct run records with distinct `run_id` values, shared `task_ref`, and compatible scenario snapshots. | ADR-068 decision 2; formal spec separation invariant 22; EXP-706 preflight guardrails. | `validate_experiment_run_against_task()` checks task identity, scenario snapshot compatibility, apparatus constraints, declared metrics, and evidence requirements. |
| EXP-706 | Replication, cohort, benchmark, comparison, and controlled variation are study allocation semantics. | ADR-068 decision 3; formal spec `Study Or Collection` definition; provenance invariants 13-15 and 21. | `ExperimentRunAllocationPlanModel._validate_condition_assignments()` and `validate_experiment_study_against_tasks_and_runs()`. |
| EXP-706 | Controlled variation must be grounded in auditable run-level facts, not tags or opaque metadata. | ADR-068 decision 3 and required boundaries; formal spec provenance invariants 13 and 21; EXP-706 preflight guardrails. | Existing study allocation validation rejects opaque catch-all references and invalid condition assignment evidence. |
| EXP-706 | Runtime replay, schedulers, storage, HTTP APIs, statistical analysis, and provenance services remain out of scope. | ADR-068 decision 5 and alternatives; formal spec non-goals; EXP-706 preflight non-goals. | Docs-only diff confirmed; no contract source, schema, fixture, runtime, or API files changed. |
| EXP-712 | Reproducibility and replay are claim-support disciplines over preserved context, evidence, provenance, and lineage. | ADR-068 decision 4; formal spec `Run Traceability` definition; EXP-712 preflight guardrails. | Existing run traceability, evidence-record, and derived-measure models remain the claim-support graph. |
| EXP-712 | Replay support is distinct from executable replay or hidden backend-state reconstruction. | ADR-068 decision 4 and required boundaries; formal spec separation invariant 23 and provenance invariant 22. | No replay-run, replay-claim, reproducibility-claim, provenance-graph, storage, scheduler, or dereference API artifacts were added. |
| EXP-712 | Claims must follow the chain from run context to capture specs, evidence records, derived measures, and claim/report refs. | ADR-068 decision 4; formal spec separation invariant 19 and 23; EXP-712 preflight cross-cutting layers. | `ExperimentRunTraceabilityModel._validate_run_traceability()` requires capture/evidence traceability and grounded claim refs. |
| EXP-712 | Derived results must cite raw evidence records and cannot stand in for raw observations. | ADR-068 decision 4; formal spec `Evidence Record` and `Derived Measure` definitions; separation invariants 15-16. | `ExperimentDerivedMeasureModel._validate_derived_measure()` requires `source_evidence_refs`. |
| EXP-712 | Claim strength is limited by preserved artifacts, redaction, loss, observer effects, unsupported surfaces, and apparatus limitations. | ADR-068 decision 4; formal spec provenance invariant 22; EXP-712 preflight architecture decisions and cross-cutting layers. | Existing evidence-record loss/redaction validation, artifact sensitivity metadata, traceability notes, disclosures, and validity notes remain the review surface. |

## Non-Goals Checked

- No `experiment-trial-v1` root schema.
- No replay-run, reproducibility-claim, replay-claim, or provenance-graph root
  schema.
- No runtime replay execution, capture orchestration, scheduler, artifact
  dereference API, retention store, query service, statistical analysis, or
  derived-measure computation.
- No SDL syntax, participant runtime, control-plane persistence, auth, error
  envelope, exception hierarchy, or logging changes.
