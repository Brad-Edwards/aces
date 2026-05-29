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

Published JSON Schemas are the portable structural contract. They declare draft
2020-12 schema identity explicitly. Semantic graph constraints that standard
JSON Schema cannot portably enforce are declared under the ACES semantic-
invariant profile through `x-aces-semantic-profile` and `x-aces-invariants`
metadata. Each invariant records a stable id, severity, validator, and input
contract/path set; the annotation shape is published as
`aces-semantic-invariants-v1` and is validated during schema generation.
Examples include metric key equality, task/run protocol binding, run time
ordering, result-evidence reference resolution, study metric grounding, and
manifest-selection and manifest-payload consistency.

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
- metric definitions keyed by metric id, with the same metric id and a metric
  version embedded in each definition;
- population or construct;
- split/leakage controls when relevant;
- apparatus constraints;
- validity notes and supporting artifacts.

One scenario may be used by many tasks. One task may be executed by many runs.

### Apparatus Context

Execution apparatus context is the instrument setup for a run. It captures or
references:

- a canonical `processor` component with processor identity and manifest;
- a canonical `backend` component with backend identity and manifest;
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

Apparatus components are keyed by component id so duplicate component keys
cannot be represented in conforming JSON records. Component identity remains an
explicit field. Claim-bearing apparatus records reserve the `processor` and
`backend` component keys for the primary processor and backend used to
interpret the run.

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

Archival run records require a completed time interval, clock context, at least
one evidence artifact, and at least one result summary. Reported result
summaries must identify the metric, carry a value, and link to evidence. Every
result-summary evidence reference must resolve to an artifact id in the same
run's `evidence_artifacts` set. Cross-artifact task/run validation also checks
that run apparatus satisfies task apparatus constraints, that run result metric
ids are declared by the task evaluation protocol, and that concrete run
evidence artifacts satisfy the task and metric evidence requirements, either by
artifact id or by an artifact `satisfies_refs` entry. If a task or metric
evidence requirement carries digest or path metadata, the matching run artifact
MUST satisfy those fields with its concrete checksum and URI/path.

### Study Or Collection

A study groups tasks, runs, results, evidence, reports, and analysis artifacts
for comparison, benchmarking, replication, or collection management. A
collection is represented by `study_kind: collection` in the same contract.

Studies carry accountable analysis context:

- owner;
- purpose and research questions;
- inclusion criteria;
- membership roles keyed by member id;
- factors and treatments keyed by factor id;
- structured run allocation plan;
- analysis plan with metric, primary metric, statistical-method,
  uncertainty-method, multiple-comparison, and missing-data policy records;
- validity notes;
- report and export artifact refs.

## Invariants

### Separation

1. A task reference to scenario material MUST use `scenario` or
   `scenario-snapshot` as the reference kind.
2. A run MUST reference exactly one task and one scenario snapshot. If the task
   references a generic scenario rather than a snapshot, the run snapshot MUST
   still use the same scenario identity.
3. A run MUST carry apparatus context; apparatus context MUST NOT be represented
   only by free-form metadata or backend-private logs.
4. A study MUST group typed artifact references; it MUST NOT redefine the task,
   run, apparatus, result, or evidence payloads it references.
5. SDL objectives MUST remain scenario-local objectives and MUST NOT be treated
   as EXP task records.
6. Metric definitions, apparatus components, run result summaries, study
   memberships, and study factors MUST use object keys as their stable local
   identifiers when uniqueness is a contract invariant. Metric definition keys
   MUST match their embedded `metric_id` values.
7. Manifest-specific fields, including required task manifests, component
   manifests, and selected apparatus manifests, MUST use `manifest` as their
   reference kind.
8. Processor and backend constraint fields MUST use processor- and
   backend-constrained references rather than generic artifact references.
9. Study membership roles MUST constrain the referenced artifact kind: task
   roles reference tasks, run roles reference runs, result roles reference
   results, evidence roles reference evidence, and analysis roles reference
   analysis artifacts.
10. Processor and backend identity constraints MUST resolve to required
    manifest references with matching identity ids and manifest schema
    versions. Manifest references for apparatus identity MUST carry a
    `subject_ref` that identifies the processor or backend identity and version
    described by the manifest.
11. Required task apparatus capabilities MUST resolve to capability references
    in the run apparatus compatibility declarations or component compatibility
    references.

### Provenance

1. Experiment artifacts MUST have stable identifiers and schema versions.
2. Evidence-bearing artifact references MUST include media type, URI, checksum,
   byte size, creation time, source, and sensitivity metadata.
3. RFC 3339 date-times, including the standard's lower-case `t`/`z`
   allowance and only known valid UTC leap-second instants, MUST be used for
   experiment-core archival times.
4. Checksums and reference digests MUST identify their digest algorithm and use
   algorithm-appropriate hex digest lengths.
5. Run evidence and result summaries MUST be linkable back to the run that
   generated or recorded them.
6. Invalidation MUST be explicit when a run is marked `invalidated`.
7. Apparatus context MUST identify selected manifests, compatibility
   declarations, configuration parameters, stochastic controls, clocks,
   measurement channels, observed setup evidence, and known limitations.
8. Completed run intervals MUST not end before they start.
9. Canonical apparatus processor and backend component manifests MUST appear in
   the same record's selected manifests with matching reference identity,
   digest/path metadata, and `subject_ref` values that match the component
   identities.
10. Study and benchmark records MUST carry research questions, run allocation,
    validity notes, and an analysis plan with at least one metric, a primary
    metric, and structured statistical, uncertainty, multiple-comparison, and
    missing-data policies.
11. ACES semantic validation MUST be able to resolve canonical processor and
    backend manifest references to concrete manifest payloads with matching
    identities and schema versions.
12. Study analysis metrics MUST be grounded in the metric definitions of the
    included task protocols and represented by result summaries, including
    explicit missing/withheld statuses, in included evaluation runs before the
    study can support comparison claims.
13. Study run-allocation `compared_conditions` MUST have matching
    `condition_assignments` that reference declared study factor levels and
    auditable run-level criteria such as participant implementation,
    processor, backend, apparatus context, manifest, capability, measurement
    channel, task/scenario snapshot identity, or non-opaque parameter values.
    Opaque catch-all references and `other` parameter kinds MUST NOT be used as
    condition-assignment evidence. Compared conditions MUST NOT share identical
    factor-level combinations or identical run-level criteria.
14. Included evaluation-run membership groupings MUST reference declared
    `compared_conditions`, a single run MUST NOT be counted in multiple
    conditions, each included run MUST satisfy exactly one condition
    assignment, invalidated/superseded/not-evaluated runs MUST NOT satisfy a
    declared run allocation, and every condition MUST meet the predeclared
    `target_runs_per_condition` when run allocation is declared and before the
    study can support analysis or comparison claims. Analysis-bearing
    collection/cohort records without
    `run_allocation` MUST still exclude invalidated, superseded, and
    not-evaluated evaluation runs.
15. Run-allocation `blocking_factors` MUST reference declared blocking,
    stratification, apparatus, or control study factors with declared levels.

### Closed-World Contracts

1. Published contracts MUST be closed-world Pydantic `ContractModel` shapes.
2. JSON Schemas MUST be generated through `schema_bundle()` and
   `tools/generate_contract_schemas.py`.
3. `contracts/schemas/` MUST NOT be edited by hand.
4. Valid fixtures MUST validate against their published schemas. Invalid
   fixtures for schema-expressible invariants MUST fail both the published JSON
   Schema and the Python contract model.
5. Consumers that use only generic JSON Schema can validate portable structure
   but MUST NOT claim full ACES experiment-core conformance until the ACES
   semantic validators named by `x-aces-invariants` have been applied.

### Security And Redaction

1. Experiment-core records are not a credential, traceback, process-argument, or
   raw backend-inspect transport. v1 automated enforcement covers the
   closed-world field set, checked-in artifact secret scanning, artifact
   sensitivity metadata, and redaction-aware parameter validators; it does not
   claim complete semantic detection of every sensitive string a producer could
   place in free-text fields.
2. Artifact references that point at restricted or redacted evidence MUST carry
   sensitivity metadata.
3. Structured experiment parameters marked `redacted` or `withheld` MUST NOT
   include concrete values.
4. Later API exposure MUST reuse existing control-plane identity, role,
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
