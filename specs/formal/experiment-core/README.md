# Experiment Core Formal Specification

This domain specifies the EXP-701 through EXP-705 experiment-core contract
boundary:

- `experiment-task-v1`
- `experiment-apparatus-context-v1`
- `experiment-run-v1`
- `experiment-study-v1`

The contracts describe cyber range experiment artifacts. They do not implement
execution, storage, scheduling, APIs, or analysis engines.

## FM Classification

Classification: FM2, Semantic Graph / Constraint.

Rationale:

- The design is not only local schema shape. It defines cross-artifact
  relationships between scenarios, tasks, apparatus contexts, runs, results, and
  studies.
- The required properties include type separation, provenance links,
  uniqueness, validity framing, apparatus/run distinction, and study membership
  constraints.
- The implementation evidence for this design is closed-world contract models,
  generated JSON Schemas, fixtures, and unit tests. It does not introduce an
  FM3 runtime state machine.

## Authoritative Artifacts

- Normative prose: this directory.
- Architecture decision: `docs/decisions/adrs/adr-037-experiment-core-contract-boundary.md`.
- Machine-readable schemas: `contracts/schemas/experiment-core/`.
- Contract source: `implementations/python/packages/aces_contracts/contracts.py`.
- Schema generation: `tools/generate_contract_schemas.py`.
- Fixture corpus: `contracts/fixtures/experiment-core/`.

## Definitions

### Scenario

An SDL scenario is the authored cyber range environment and behavior meaning.
It may include nodes, infrastructure, content, scoring, objectives, workflows,
participants, runtime declarations, and other scenario-local semantics.

A scenario is not an EXP task, run, apparatus context, or study.

### Task

An experiment task is the evaluation problem over a scenario or scenario
snapshot. It binds:

- a scenario reference;
- an evaluation protocol;
- task intent and intended use;
- metric definitions keyed by metric id and unit of analysis;
- population or construct;
- split/leakage controls when relevant;
- apparatus constraints;
- validity notes and supporting artifacts.

One scenario may be used by many tasks. One task may be executed by many runs.

### Apparatus Context

Execution apparatus context is the instrument setup for a run. It captures or
references:

- processor identity and manifest;
- backend identity and manifest;
- participant implementation identity where relevant;
- compatibility declarations;
- selected manifests and profiles;
- configuration parameters;
- stochastic controls;
- clock context;
- measurement channels;
- observed setup evidence;
- known limitations.

Apparatus context belongs with run provenance. It is not authored scenario
meaning and is not a result value.

Apparatus components are keyed by component id so duplicate component identity
cannot be represented in conforming JSON records.

### Run

An experiment run is an archival record of a specific execution of a declared
task. It binds:

- task reference;
- scenario snapshot reference;
- apparatus context;
- parameter set;
- stochastic controls;
- start/end and clock context;
- run status and outcome status;
- evidence artifacts;
- result summaries keyed by result id;
- deviations and invalidation details;
- lineage references.

A run may reference live observation artifacts captured at a seal point. It
must not be reconstructed from mutable live control-plane state.

### Study Or Collection

A study groups tasks, runs, results, evidence, reports, and analysis artifacts
for comparison, benchmarking, replication, or collection management. A
collection is represented by `study_kind: collection` in the same contract.

Studies carry analysis context:

- purpose and research questions;
- inclusion criteria;
- membership roles keyed by member id;
- factors and treatments keyed by factor id;
- run allocation;
- analysis plan;
- validity notes;
- report and export artifact refs.

## Invariants

### Separation

1. A task reference to scenario material MUST use `scenario` or
   `scenario-snapshot` as the reference kind.
2. A run MUST reference exactly one task and one scenario snapshot.
3. A run MUST carry apparatus context; apparatus context MUST NOT be represented
   only by free-form metadata or backend-private logs.
4. A study MUST group typed artifact references; it MUST NOT redefine the task,
   run, apparatus, result, or evidence payloads it references.
5. SDL objectives MUST remain scenario-local objectives and MUST NOT be treated
   as EXP task records.
6. Metric definitions, apparatus components, run result summaries, study
   memberships, and study factors MUST use object keys as their stable local
   identifiers when uniqueness is a contract invariant.
7. Manifest-specific fields, including required task manifests, component
   manifests, and selected apparatus manifests, MUST use `manifest` as their
   reference kind.

### Provenance

1. Experiment artifacts MUST have stable identifiers and schema versions.
2. Run evidence and result summaries MUST be linkable back to the run that
   generated or recorded them.
3. Invalidation MUST be explicit when a run is marked `invalidated`.
4. Apparatus context SHOULD identify selected manifests, compatibility
   declarations, stochastic controls, clocks, and observed setup evidence when
   those factors affect interpretation.

### Closed-World Contracts

1. Published contracts MUST be closed-world Pydantic `ContractModel` shapes.
2. JSON Schemas MUST be generated through `schema_bundle()` and
   `tools/generate_contract_schemas.py`.
3. `contracts/schemas/` MUST NOT be edited by hand.
4. Valid fixtures MUST validate against their published schemas. Invalid
   fixtures for schema-expressible invariants MUST fail both the published JSON
   Schema and the Python contract model.

### Security And Redaction

1. Experiment-core records MUST NOT contain bearer tokens, credentials, private
   keys, environment dumps, full tracebacks, backend-private objects, raw process
   argv, or raw backend inspect payloads.
2. Artifact references that point at restricted or redacted evidence MUST carry
   sensitivity metadata.
3. Later API exposure MUST reuse existing control-plane identity, role,
   request-size, audit, idempotency, response-model, and redacted-error
   patterns.

## Literature-Based Criteria

The research notes in `docs/research/experiment-core/` provide the evidence
base. The most load-bearing criteria are:

- ML reproducibility: task protocols, metric definitions, data/split/leakage
  controls, repeated runs, stochastic controls, and uncertainty/analysis plans.
- Experiment databases: separable task, run, evaluation, and collection
  records.
- Provenance and FAIR packaging: stable identifiers, artifact roles, lineage,
  and exportable evidence bundles.
- Cyber range/testbed research: apparatus configuration, fidelity, host/VM
  context, and cross-testbed reproduction are part of result validity.
- Empirical software engineering and simulation V&V: validity threats,
  treatments, controls, replication, calibration, and uncertainty context.

## Non-Goals

- Runtime execution.
- Run persistence.
- Study management services.
- Statistical analysis engines.
- HTTP APIs.
- New SDL authoring syntax.
- PROV, RO-Crate, OpenML, or MLflow as the internal ACES schema.
