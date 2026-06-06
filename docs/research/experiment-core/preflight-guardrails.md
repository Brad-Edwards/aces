# Architecture Pre-Flight Guardrails

Date: 2026-05-26

Issue: #87.

Requirements: EXP-701, EXP-702, EXP-703, EXP-704, EXP-705.

The architecture pre-flight was run once per requirement after the literature
notes were committed to the branch worktree and linked from the issue thread.
All five runs completed without changing files. The guardrails below are the
binding implementation constraints extracted from those runs.

## EXP-701: Experiment Task Model

Result: no files changed.

Guardrails:

- Treat experiment tasks as experiment-level contracts, not as a new SDL root
  section by default.
- `ExperimentTask` binds a scenario/environment reference, evaluation protocol,
  and task intent.
- Do not collapse tasks into `Scenario`, `Objective`, `Evaluation`, `Workflow`,
  `Run`, or `Study`.
- Evaluation protocol should be a versioned closed-world contract or reference.
  It may reference existing SDL assessment constructs but must not embed backend
  probe code as task meaning.
- Runs are archival provenance records of task execution, not mutable
  `RuntimeSnapshot` state.
- Apparatus context must be declared from processor/backend/participant
  manifests, compatibility declarations, concept bindings, and realization
  disclosures, not inferred from backend internals.

Required incumbents:

- `aces_sdl.SDLModel`, `parser.py`, `SemanticValidator`, `instantiate_scenario()`,
  and existing SDL error classes.
- `aces_contracts.contracts.ContractModel`, `schema_bundle()`,
  `tools/generate_contract_schemas.py`, generated schemas, and
  `contracts/schema-publication-manifest.json`.
- Existing semantic authority around `tasks-runs-studies`, `scenarios`,
  `apparatus-declarations`, `realization-and-disclosure`,
  `provenance-and-evidence`, and `time-and-apparatus`.
- `Diagnostic`, canonical runtime addresses, planner dependency semantics,
  control-plane security/audit/idempotency, and redacted error handling where
  runtime/API surfaces are involved.

## EXP-702: Task And Scenario Separation

Result: no files changed.

Guardrails:

- Keep these concepts distinct:
  - `Scenario`: SDL authoring specification and instantiated derivatives.
  - `Objective`: scenario-local SDL declaration.
  - `Task`: experiment workflow object that references a scenario and binds
    protocol, intent, apparatus constraints, or study context.
  - `Run`: archival record of a task execution, not mutable live runtime state.
  - `Study`: grouping of tasks, runs, and results.
- Do not subclass `Scenario` into `Task`.
- Do not embed duplicate scenario schemas in task contracts.
- Do not use scenario name as task identity.
- Do not treat SDL `objectives` as EXP tasks.
- Do not make runs another mutable runtime snapshot.

Required doc fix:

- `docs/explain/sdl/sections.md` currently describes SDL `objectives` as
  "experiment tasks." Correct that to "scenario-local objectives; not EXP task
  records."

## EXP-703: Experiment Run Model

Result: no files changed.

Guardrails:

- EXP-703 lands as an archival experiment contract, not as an extension of live
  runtime/control-plane state.
- Keep these identities distinct:
  - task: declared execution intent binding scenario, protocol, and intent;
  - scenario: authored SDL meaning;
  - run record: durable archival record of one execution of one declared task;
  - runtime snapshots, workflow/evaluation result envelopes, participant
    episode state/history, operation receipts/statuses: live or lifecycle
    observation surfaces, not archival run records;
  - study: grouping surface over tasks, runs, and results.
- A run record may capture or reference live observation artifacts at a specific
  capture/seal point.
- A run record must not be reconstructed lazily from mutable `RuntimeSnapshot`
  or `ControlPlaneStore` state.
- Avoid treating workflow `run_id`, operation id, participant `episode_id`, or
  snapshot address as the experiment run id.
- Avoid storing archival records in `RuntimeSnapshot.metadata`.
- Avoid reusing `OperationStatus`, `WorkflowStatus`, or participant episode
  status as archival run outcome without a deliberate contract boundary.

Required contract direction:

- Design around stable `contract_id`/schema version, `run_id`, `task_ref`,
  explicit apparatus context, observation/evidence/provenance references,
  timestamps and clock context, and typed result references.

## EXP-704: Execution Apparatus Context

Result: no files changed.

Guardrails:

- Model apparatus context as run-scoped archival apparatus context.
- Keep it distinct from SDL scenario meaning, task definition, mutable live
  runtime state, and run results.
- Land it as part of the joint EXP-701 through EXP-705 task/run/study model, not
  as a standalone schema that will need reconciliation later.
- Apparatus context should reference or snapshot selected processor/backend/
  participant manifests, compatibility declarations, configuration, parameters,
  stochastic controls, and setup context explicitly.
- Do not put apparatus context in SDL scenario models, task intent,
  `RuntimeSnapshot.metadata`, run results, logs, or free-form metadata blobs.
- Do not make backend identity explicit while processor or participant
  implementation identity stays implicit.

Required incumbents:

- `ProcessorManifestV2Model`, `BackendManifestV2Model`,
  `aces_contracts.manifest_authority`, `backend_manifest_payload()`,
  `reference_processor_manifest_payload()`, controlled vocabularies, runtime
  envelopes, `Diagnostic`, and `Severity`.

## EXP-705: Study And Collection Model

Result: no files changed.

Guardrails:

- Design EXP-705 as one first-class archival/analysis artifact that groups typed
  references to tasks, runs, and results.
- Do not redefine task, run, result, evidence, or apparatus payloads.
- Use one canonical study/collection model. If both terms remain user-facing,
  make `collection` an explicit kind/alias within the same contract, not a
  parallel schema or service.
- A study consumes archival/run/result envelopes and must not change plan/apply
  semantics or live runtime state.
- Avoid tags-as-studies, `RuntimeSnapshot.metadata` blobs, evaluator `detail` as
  analysis authority, backend-native IDs as portable references, duplicated
  result schemas, duplicated validators, duplicated schema registries, and
  conflating semantic profiles with study definitions.

Required model direction:

- Use a versioned study/collection contract plus typed artifact membership:
  target kind, stable target id/ref, optional role/purpose, and optional
  analysis grouping metadata.

## Cross-Cutting Constraints

- Normative prose belongs under `specs/`.
- Machine-readable contracts belong under `contracts/`.
- Implementation consumes the normative and contract artifacts.
- Do not hand-edit `contracts/schemas/`; update generator inputs and regenerate.
- External payloads must use closed-world `ContractModel` shapes, generated JSON
  Schemas, and fixture/schema publication checks.
- If exposed over HTTP, use existing control-plane identity, authorization,
  request-size, audit, idempotency, response model, and redacted error patterns.
- Do not persist tokens, credentials, private keys, environment secrets,
  backend-private objects, full tracebacks, raw process argv, or raw backend
  payloads in task/run/study/apparatus records, diagnostics, fixtures, audit
  details, logs, or documentation examples.
- Use existing error envelopes and diagnostics; do not create a new exception
  hierarchy.
- Use existing concept authority and controlled-vocabulary machinery when
  portable comparison depends on a bounded term.
- Avoid duplicate schema registries, validation stacks, manifest renderers,
  profile loaders, persistence stacks, logging stacks, or audit stacks.
