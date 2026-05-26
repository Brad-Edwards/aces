# Design Criteria For EXP-701 Through EXP-705

These criteria distill the research notes into actionable design obligations
for issue #87. They are not the final ADR; they are the pre-design rubric used
before architecture pre-flight and implementation planning.

## Scope

Issue #87 covers five related requirements:

- EXP-701: Experiment Task Model.
- EXP-702: Task And Scenario Separation.
- EXP-703: Experiment Run Model.
- EXP-704: Execution Apparatus Context.
- EXP-705: Study And Collection Model.

The issue states that this is a design issue: produce a joint ADR and formal
specification with a schema set for tasks, runs, studies, and apparatus context.

## Design Principle 1: Separate Meaning, Protocol, Execution, And Analysis

Evidence base:

- OpenML and experiment databases separate data, tasks, flows, runs, and
  evaluations.
- ML reproducibility literature treats evaluation protocols and data splits as
  essential context.
- Cyber-range literature treats scenarios as environment/exercise models, not
  full experiment protocols.
- PROV treats entities, activities, and agents as distinct provenance roles.

Criteria:

- Scenario is authored environment meaning.
- Task is evaluation protocol over a scenario or scenario snapshot.
- Apparatus is execution instrument context.
- Run is archival execution activity and result anchor.
- Study/collection is analysis and comparison context.

Failure mode to avoid:

- A single `experiment` object that means scenario, task, run, and study
  depending on which fields are present.

## Design Principle 2: Treat Cyber Range Apparatus As Instrument Context

Evidence base:

- DETER and CSET literature frame cyber-security testbeds as experiment
  instruments.
- Simulation V&V literature requires verification, validation, calibration, and
  uncertainty context.
- Cross-testbed reproduction papers show apparatus differences can change
  results.

Criteria:

- Apparatus context must include processor identity, backend identity,
  compatibility declarations, selected manifests, configuration, parameters,
  stochastic controls, host/environment observations, measurement channels, and
  known limitations.
- Planned apparatus and observed apparatus evidence must both be representable.
- Apparatus variation must be available as a planned study factor.

Failure mode to avoid:

- Treating backend identity and host details as optional log metadata outside
  the archival run record.

## Design Principle 3: Make Tasks Evaluation-Ready

Evidence base:

- REFORMS, DOME, leakage literature, Model Cards, and Datasheets require clear
  data, protocol, metrics, intended use, and limitations.
- Statistical-comparison literature requires explicit unit of analysis and
  comparison plan.

Criteria:

- Task records should include task identifier/version, scenario reference,
  protocol identifier/version, evaluation intent, unit of analysis, metric
  definitions, split/leakage controls when relevant, admissible apparatus
  constraints, and validity notes.
- Task should be reusable across multiple runs and studies.
- One scenario should support multiple tasks without copying scenario meaning.

Failure mode to avoid:

- Defining task as only `scenario_id` plus a metric list.

## Design Principle 4: Make Runs Archival And Immutable In Meaning

Evidence base:

- Provenance and computational reproducibility literature require durable
  execution records.
- ACES already distinguishes control-plane state from declarative SDL surfaces.
- MLflow/Sumatra/ReproZip/noWorkflow-like tools preserve run context for later
  reproducibility.

Criteria:

- Run records should identify the executed task version, scenario snapshot,
  apparatus context, processor/backend, parameter set, stochastic controls,
  start/end times, outcome state, evidence artifacts, result summaries, and
  deviations.
- Live lifecycle state and mutable observation streams should remain separate
  from the archival run record.
- Run invalidation/retraction/supersession should be explicit.

Failure mode to avoid:

- Reusing operation status envelopes as experiment runs.

## Design Principle 5: Make Studies And Collections Analysis-Carrying

Evidence base:

- Empirical software engineering defines studies around research questions,
  variables, treatments, controls, validity, and analysis.
- ML comparison literature requires repeated tasks/runs and statistical
  methods.
- OpenML-like benchmark suites require structured task and evaluation grouping.

Criteria:

- Study records should include research question/claim, task and run selection,
  compared systems or treatments, factors, blocking/randomization, analysis
  plan, validity threats, result inclusion policy, and reporting artifacts.
- Collections may provide reusable task/run/result groupings but should still
  have purpose, scope, ownership, version, and inclusion criteria.
- Studies should be able to reference collections while applying a study-
  specific analysis plan.

Failure mode to avoid:

- Treating a study as a directory or tag list without analysis semantics.

## Design Principle 6: Provide Schema And Export Support

Evidence base:

- FAIR, RO-Crate, PROV, and experiment-database literature require
  machine-readable, identifiable, reusable records.
- ACES already publishes contract schemas.

Criteria:

- Publish ACES-owned schemas for task, run, apparatus context, study, and
  collection records.
- Include artifact-reference structures with role, type, checksum, media type,
  and access/redaction metadata.
- Use controlled vocabularies for roles and statuses where comparison depends
  on them.
- Keep semantic export mappings possible for PROV/RO-Crate/OpenML-like tooling,
  but do not import their payloads as the normative ACES core.

Failure mode to avoid:

- JSON blobs that can only be interpreted by one backend or notebook.

## Minimum Fields By Requirement

### EXP-701 Task

- `task_id`, `schema_version`, `version`, `title`, `description`.
- `scenario_ref` with identity, version/snapshot, and selection scope.
- `evaluation_protocol` with protocol id/version, metric definitions,
  observations required, unit of analysis, and acceptance/aggregation policy.
- `intended_use`, `non_use`, `population_or_construct`, and `validity_notes`.
- `split_and_leakage_controls` when data, learning, replay, adaptive agents, or
  repeated exposure are relevant.
- `apparatus_constraints` for compatible processors/backends/profiles.
- `artifact_refs` for supporting protocol docs, scoring code, and evidence
  templates.

### EXP-702 Task/Scenario Separation

- A task references but does not own scenario meaning.
- A scenario can be reused by many tasks.
- A task can bind a scenario snapshot to one protocol.
- Scenario realization details remain outside task except as constraints.
- A study may include tasks derived from the same scenario to compare protocols.

### EXP-703 Run

- `run_id`, `schema_version`, `task_ref`, `scenario_snapshot_ref`.
- `apparatus_context_ref` or embedded frozen apparatus context.
- `processor_ref`, `backend_ref`, `parameter_set`, `stochastic_controls`.
- `started_at`, `ended_at`, `clock`, `run_status`, `outcome_status`.
- `evidence_artifacts`, `result_summaries`, `deviations`, `invalidation`.
- `lineage` fields for generated-by, used, derived-from, supersedes.

### EXP-704 Apparatus Context

- processor identity/version/manifest.
- backend identity/version/profile.
- selected SDL/manifests/images/datasets/dependencies.
- compatibility declarations and conformance profiles.
- host/VM/container/device context where relevant.
- configuration, parameters, stochastic controls, clocks, and resource limits.
- measurement channels and observed setup evidence.
- known limitations, drift observations, and redaction/access constraints.

### EXP-705 Study And Collection

- `study_id` or `collection_id`, `schema_version`, version, title, owner.
- research question, claim, or benchmark purpose.
- task/run/result membership and inclusion criteria.
- factors/treatments/comparators.
- run allocation, blocking, randomization, replication plan.
- metrics and statistical/estimation analysis plan.
- validity threats and limitations.
- report and export artifact references.

## Questions For Architecture Pre-Flight

- Does ACES already have a normative concept authority location that should own
  experiment-core vocabularies?
- Should task/run/study schemas live as independent contracts or under a shared
  experiment-core contract family?
- Should run records embed apparatus context immutably or reference an apparatus
  context artifact with a frozen digest?
- How should these design schemas avoid conflicting with existing control-plane
  envelopes and processor/backend manifests?
- What formal specification classification applies: FM1 for static semantic
  separation, FM2 for cross-reference/lineage constraints, or a staged approach?
