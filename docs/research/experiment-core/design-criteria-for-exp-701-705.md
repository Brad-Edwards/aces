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
- Task is evaluation protocol over a scenario or scenario snapshot. For composed
  SDL, snapshot identity is over the expanded canonical scenario, while module
  fragment paths, module ids/namespaces, lock records, and fragment digests are
  preserved as evidence/audit metadata.
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
- Publish both structural JSON Schema constraints and named ACES semantic
  invariants, with validator and input metadata, for cross-record checks that
  standard JSON Schema cannot enforce. The semantic-invariant annotation shape
  must be generated and checked, and ACES conformance must require the named
  semantic validators rather than relying on generic JSON Schema consumers to
  interpret custom annotations.
- Require schema-version fields in serialized experiment artifacts and publish
  named semantic validators for RFC 3339 archival timestamp semantics that
  generic JSON Schema consumers do not portably enforce, while accepting the
  standard's lower-case `t`/`z` date-time allowance.
- Include artifact-reference structures with role, type, checksum, media type,
  byte size, creation time, source, and access/redaction metadata. Evidence
  requirements that bind digest or path metadata must resolve against the
  concrete artifact checksum and URI/path, not only an artifact display id.
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
- metric definitions carry both map-key identity and embedded metric
  id/version so exported records remain self-describing outside their parent
  object.
- `intended_use`, `non_use`, `population_or_construct`, and `validity_notes`.
- `split_and_leakage_controls` when data, learning, replay, adaptive agents, or
  repeated exposure are relevant.
- `apparatus_constraints` for compatible processors/backends/profiles.
- processor and backend identity constraints must resolve to required manifest
  references for the same identity and expected manifest schema version; those
  manifest references carry a subject identity/version, not only a manifest id.
- `artifact_refs` for supporting protocol docs, scoring code, and evidence
  templates.

### EXP-702 Task/Scenario Separation

- A task references but does not own scenario meaning.
- A scenario can be reused by many tasks.
- A task can bind a scenario snapshot to one protocol.
- When a task references a scenario rather than a sealed snapshot, task/run
  validation still requires the run snapshot to preserve that scenario identity.
- Scenario realization details remain outside task except as constraints.
- A study may include tasks derived from the same scenario to compare protocols.

### EXP-703 Run

- `run_id`, `schema_version`, `task_ref`, `scenario_snapshot_ref`.
- `apparatus_context_ref` or embedded frozen apparatus context.
- `processor_ref`, `backend_ref`, `parameter_set`, `stochastic_controls`.
- `started_at`, `ended_at`, `clock`, `run_status`, `outcome_status`.
- `evidence_artifacts`, `result_summaries`, `deviations`, `invalidation`.
- `lineage` fields for generated-by, used, derived-from, supersedes.
- Archival run records require evidence artifacts and result summaries with
  metric ids and evidence links; partial/draft records need a separate
  lifecycle surface rather than weakened archival fields.
- result-summary evidence references resolve to artifact ids in the same run
  record, and digest/path-bearing evidence requirements must match the concrete
  artifact checksum and URI/path.
- task/run semantic validation checks that run result metrics are declared by
  the task protocol, that run apparatus satisfies task apparatus constraints,
  and that concrete run evidence satisfies task and metric evidence
  requirements.

### EXP-704 Apparatus Context

- processor identity/version/manifest.
- backend identity/version/profile.
- participant implementation identity/version/manifest and run-level selected
  implementation provenance when participant implementation apparatus is
  present.
- canonical processor and backend component entries that schema consumers can
  validate without out-of-band role interpretation.
- selected SDL/manifests/images/datasets/dependencies.
- canonical processor and backend manifest refs must be included in selected
  manifests, with matching optional digest metadata and subject identities.
  Manifest path qualifiers are not part of the v1 apparatus contract, and ACES
  semantic validation must resolve canonical digest-qualified references to
  concrete processor/backend manifest payloads so identity and manifest
  evidence cannot drift.
- compatibility declarations and conformance profiles as id/version
  declarations without digest or path qualifiers unless a future validator binds
  them to concrete profile/capability payloads.
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
- analysis plans name the metrics, primary metric, estimand/unit assumptions,
  uncertainty procedure, multiple-comparison policy, and missing-data policy
  before claims are drawn, and those metrics must be grounded in included task
  protocols and represented by result summaries or explicit missingness in
  included evaluation runs before study-level comparison claims are accepted.
- run-allocation claims are semantically checked: included evaluation-run
  memberships must be grouped by predeclared `compared_conditions`; each
  condition must have an explicit assignment to declared factor levels and
  auditable run-level criteria; catch-all `other` references cannot stand in
  for treatment, apparatus, task, scenario, measurement-channel, or parameter
  evidence; parameter criteria must use non-opaque kinds; compared conditions
  cannot share identical factor-level combinations or concrete criteria; one run
  cannot be counted across multiple conditions; each included run must satisfy
  exactly one assigned condition; invalidated/superseded/not-evaluated runs
  cannot satisfy allocation; and the concrete run artifacts must satisfy
  `target_runs_per_condition` for every condition before analysis or comparison
  claims are accepted.
- run-allocation `blocking_factors` reference declared study factors so the
  blocking/randomization plan is reviewable as variable metadata, not prose.
  Those factors must have declared levels and an appropriate blocking,
  stratification, apparatus, or control kind.
- validity threats and limitations.
- report and export artifact references.
- `study` and `benchmark` records require research questions, run allocation,
  an analysis plan, and validity notes; lighter collections/cohorts still
  require ownership, purpose, membership, and inclusion criteria. If lighter
  records carry an analysis plan, invalidated/superseded/not-evaluated
  evaluation runs remain ineligible for analysis.
- benchmark and agent-evaluation lineage surfaces such as starter files,
  evaluators, subtasks, gold steps, milestones, human-assistance records,
  scaffold disclosure, baseline disclosure, and cost/resource traces should be
  representable through explicit artifact roles in v1, with deeper benchmark
  semantics reserved for future contracts.

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
