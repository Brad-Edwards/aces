# Issue #267 EXP-706 Trial And Replication Preflight Guardrails

Date: 2026-06-25

Issue: #267.

Requirement: EXP-706.

This preflight narrows ADR-055 and the experiment-core formal specification to
repeated runs, replications, and controlled variation. ADR-055, ADR-064,
ADR-065, and `specs/formal/experiment-core/README.md` remain the normative
design authority. This note is guidance for implementation only.

## Architecture Decisions

- Treat one trial as one archival `experiment-run-v1` record unless a later ADR
  introduces a different meaning. Do not add `experiment-trial-v1` or a trial
  root schema for the same execution facts.
- Represent repeated runs of the same task by multiple `ExperimentRunModel`
  records with distinct `run_id` values and a shared `task_ref`/compatible
  `scenario_snapshot_ref`.
- Represent replication and controlled variation at the study layer through
  `ExperimentStudyModel.run_allocation`, `membership` entries with
  `evaluation-run` roles and condition groupings, study factors, blocking
  factors, condition assignments, `target_runs_per_condition`,
  `replication_policy`, and `stopping_rule`.
- Ground controlled variation in auditable run-level criteria: participant
  implementation, processor, backend, apparatus context, selected manifests,
  capabilities, measurement channels, scenario snapshots, task refs,
  non-opaque parameters, and stochastic controls.
- Preserve the current split: task defines protocol and metric requirements;
  run records a single execution; apparatus context records instrument setup;
  evidence records and derived measures carry observation and interpretation;
  study allocation defines comparison, replication, and grouping semantics.
- EXP-706 does not implement replay execution, schedulers, storage, HTTP APIs,
  statistical analysis, or a provenance graph service.

## Required Incumbents

- Contract source:
  `implementations/python/packages/aces_contracts/contracts.py`, especially
  `ContractModel`, `ExperimentTaskModel`, `ExperimentRunModel`,
  `ExperimentStudyModel`, `ExperimentRunAllocationPlanModel`,
  `ExperimentConditionAssignmentModel`, `ExperimentParameterModel`,
  `ExperimentStochasticControlModel`, `ExperimentApparatusContextModel`,
  typed experiment reference models, and `schema_bundle()`.
- Cross-artifact validators:
  `validate_experiment_run_against_task()`,
  `validate_experiment_study_against_tasks_and_runs()`, and
  `validate_experiment_apparatus_context_against_manifests()`.
- Published contract surface:
  `contracts/schemas/experiment-core/experiment-task-v1.json`,
  `contracts/schemas/experiment-core/experiment-run-v1.json`,
  `contracts/schemas/experiment-core/experiment-study-v1.json`,
  `contracts/schemas/experiment-core/experiment-apparatus-context-v1.json`,
  `contracts/schema-publication-manifest.json`, and
  `tools/generate_contract_schemas.py`.
- Fixture and conformance corpus:
  `contracts/fixtures/experiment-core/` and
  `implementations/python/tests/test_runtime_contracts.py`.
- Adjacent evidence/provenance contracts:
  `experiment-capture-spec-v1`, `experiment-evidence-record-v1`,
  `experiment-derived-measure-v1`, run `traceability`,
  `realized_form_disclosures`, `augmentation_disclosures`, and participant
  implementation manifest/provenance contracts.
- Concept and manifest authority:
  concept families `tasks-runs-studies`, `apparatus-declarations`,
  `provenance-and-evidence`, `realization-and-disclosure`, and
  `time-and-apparatus`; processor/backend/participant manifest authority; and
  governed observation capability vocabularies.

## Whole-Repo Scope

- Repo workflow policy: `.ground-control.yaml`, `.gc/plan-rules.md`, and the
  repo policy and verification scripts.
- Normative design authority: ADR-055, ADR-064, ADR-065, and
  `specs/formal/experiment-core/README.md`.
- Contract publication authority: contract source, generated schemas, fixtures,
  schema publication manifest, schema drift checks, and ACES semantic-invariant
  annotations.
- Runtime/API boundary for future work: control-plane auth, request-size
  guards, idempotency, audit store, response models, diagnostics, redacted error
  envelopes, and existing runtime redaction/config validators.

## Cross-Cutting Layers

- Structural validation: every external payload must pass the closed-world
  `ContractModel` source and the generated draft 2020-12 JSON Schema. Unknown
  fields remain errors.
- Run validation: `ExperimentRunModel._validate_archival_run()` enforces run
  interval ordering, invalidation details, participant implementation
  provenance resolution, result evidence resolution, and traced disclosure
  evidence.
- Task/run validation: `validate_experiment_run_against_task()` is the gate for
  task identity/version, scenario snapshot compatibility, apparatus
  constraints, task-declared metric ids, and task/metric evidence requirements.
- Study allocation validation: `ExperimentRunAllocationPlanModel` and
  `validate_experiment_study_against_tasks_and_runs()` enforce compared
  conditions, condition assignments, blocking factors, target runs per
  condition, evaluation-run eligibility, one-condition-per-run assignment, and
  analysis metric grounding.
- Manifest and digest validation: apparatus variations must use
  `ExperimentManifestReferenceModel` and
  `validate_experiment_apparatus_context_against_manifests()` for canonical
  processor/backend manifest identity and digest binding.
- Secret-handling surface: parameters may use redaction-aware
  `ExperimentParameterModel`; condition-assignment parameters must be
  auditable and non-redacted. Do not serialize credentials, bearer tokens,
  private keys, hidden answer keys, raw prompts, environment dumps, process
  argv, backend-private payloads, or full tracebacks into task/run/study
  records, diagnostics, audit details, logs, fixtures, or examples.
- Config/env-binding surface: run variation may cite bounded configuration,
  apparatus, protocol, or analysis parameters. It must not introduce a new
  environment-binding shape or store raw `os.environ`, CLI arguments, process
  tables, or backend-local config objects.
- API/auth surface: any future create/read/update path for trial, run, or
  study records must reuse `aces_runtime.control_plane_api`,
  `control_plane_api_guards`, `control_plane_security`,
  `control_plane_store`, request fingerprints, idempotency keys, audit events,
  response models, and redacted FastAPI error handling.
- OS-level exposure: command helpers must not pass tokens, credentials, raw
  evidence payloads, or large private run artifacts through process arguments.
  Use content-addressed files, URIs, checksums, and synthetic fixtures.
- Error-envelope surface: failures must use existing Pydantic validation
  errors, structured `Diagnostic` values, or the existing redacted HTTP error
  pattern. Do not echo full experiment records, evidence payloads, secrets,
  tracebacks, or backend internals.
- Persistence surface: archival trial/run/replication records must not be
  stored in `RuntimeSnapshot.metadata`, operation records, participant
  histories, audit details, or backend-private logs. Any future durable store
  must preserve schema-versioned experiment artifacts and their refs.

## Extensibility Guardrail

The extension seam is `experiment-study-v1.run_allocation` plus existing run
provenance fields, not a parallel trial service or schema. If a future change
needs more than the current `replication_policy` string, `target_runs_per_condition`,
condition assignments, membership groupings, parameters, and stochastic controls
can express, extend the study allocation contract through the normal schema
publication path. Producer code should parameterize the run producer source and
artifact locator/sealing policy so additional replay backends, replication
types, or apparatus variations emit the same canonical task/run/study shapes.

## Gotchas And Anti-Patterns

- Do not create duplicate trial, replication, or replay schemas for facts
  already carried by task, run, apparatus, evidence, derived-measure, or study
  contracts.
- Do not treat operation ids, workflow run ids, participant episode ids,
  snapshot addresses, or backend-native execution ids as portable trial ids.
- Do not use tags, folders, evaluator `detail`, runtime metadata, or audit log
  entries as study allocation or replication authority.
- Do not make controlled variation depend on opaque `other` references,
  redacted condition parameters, or unbounded free-text criteria.
- Do not infer replication from repeated backend operations unless sealed
  `experiment-run-v1` records and study membership/allocation refs exist.
- Do not hand-edit `contracts/schemas/`; update contract sources, regenerate,
  update the publication manifest when hashes change, and keep fixtures/tests
  aligned.
- Do not duplicate schema registries, validation helpers, exception
  hierarchies, logging/audit stacks, manifest renderers, persistence stores, or
  workflow logic for EXP-706.

## Non-Goals

- New trial root schema, new run-provenance root, or new study/collection
  service.
- Replay execution, schedulers, workers, runtime orchestration, capture
  execution, retention jobs, HTTP APIs, or durable storage implementation.
- Statistical analysis engines, derived-measure computation, evaluator behavior,
  or benchmark reporting.
- SDL syntax changes, scenario root sections, objective semantics, or runtime
  snapshot changes.
- New security model, exception hierarchy, logging pipeline, audit format,
  manifest renderer, schema registry, or persistence stack.
