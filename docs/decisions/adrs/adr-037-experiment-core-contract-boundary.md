# ADR-037: Experiment Core Contract Boundary

## Status

accepted

## Date

2026-05-26

## Context

Issue #87 covers the joint design for EXP-701 through EXP-705:
experiment tasks, task/scenario separation, archival runs, execution apparatus
context, and studies/collections. ACES needs these concepts because a cyber
range is intended to operate as a scientific instrument, not only as a runtime
that provisions scenarios.

The design review started with published academic literature rather than local
field naming. The supporting notes are in
`docs/research/experiment-core/`. The central findings are:

- ML reproducibility and reporting work requires explicit tasks, protocols,
  metric definitions, leakage controls, stochastic controls, and analysis plans.
- OpenML and experiment-database work separates data/scenario-like inputs,
  tasks, executable flows, runs, and evaluations.
- PROV, FAIR, RO-Crate, and workflow-provenance work require stable identifiers,
  artifact roles, lineage links, and packaged evidence.
- Cyber range and DETER/CSET work treat testbeds and emulation ranges as
  scientific apparatus whose configuration, fidelity, host load, and measurement
  channels affect results.
- Empirical software-engineering and simulation V&V work require validity
  framing, variables, controls, repeated runs, apparatus variation, and
  uncertainty/replication support.

Existing ACES artifacts already establish adjacent boundaries:

- SDL `Scenario` records authored cyber range meaning.
- SDL `Objective` records scenario-local actor/target/success declarations.
- Runtime snapshots, workflow/evaluation envelopes, operation statuses, and
  participant episode records model live or lifecycle state.
- Backend and processor manifests model apparatus identity and capability.
- Concept authority already includes `tasks-runs-studies`,
  `apparatus-declarations`, `provenance-and-evidence`, and
  `time-and-apparatus`.

Reusing any of those as the whole experiment model would blur scientific
claims. A scenario is not an experiment task, a workflow operation is not an
archival run, and a study is not a tag list.

## Decision

Publish an experiment-core contract family with four first-class contracts:

- `experiment-task-v1`
- `experiment-apparatus-context-v1`
- `experiment-run-v1`
- `experiment-study-v1`

The contracts are machine-readable ACES artifacts under `contracts/schemas/`,
generated from closed-world `ContractModel` sources. The normative semantic
rules live in `specs/formal/experiment-core/`. Published JSON Schemas are the
portable structural contract and declare draft 2020-12 schema identity. They
also include an ACES semantic-invariant profile for constraints that require
ACES model validation, such as task/run protocol binding, cross-object
reference resolution, manifest identity/digest binding, study metric/result
grounding, and temporal ordering. The annotation profile shape is published as
`aces-semantic-invariants-v1` and checked during schema generation.

Identifier-bearing repeated children are represented as keyed object maps
rather than arrays when uniqueness is part of the contract: metric definitions
are keyed by metric id, apparatus components by component id, run result
summaries by result id, study membership entries by member id, and study
factors by factor id. This keeps the published JSON Schemas authoritative for
portable structural consumers instead of leaving uniqueness only to Python
validators. Cross-map semantic constraints that standard JSON Schema cannot
portably enforce, including metric-key equality, result-to-evidence resolution,
component manifest selection, task/run protocol binding, study metric/result
grounding, manifest payload binding, and run time ordering, are declared as
`x-aces-invariants` with validator and input metadata, and are enforced by the
ACES contract models and semantic validator functions. Manifest-specific fields use
manifest-constrained references so apparatus context cannot silently point to
runs, studies, or other artifact kinds where a manifest boundary is required.
Processor and backend constraint fields use processor- and backend-constrained
references with manifest `subject_ref` metadata for the same reason: role names
and manifest subject identity must be enforceable by semantic validators, not
only by convention.

### 1. Task Is Scenario Plus Protocol Plus Intent

An experiment task references a scenario or scenario snapshot and binds it to an
evaluation protocol, intent, unit of analysis, metric definitions, population or
construct, leakage/split controls when relevant, apparatus constraints, validity
notes, and supporting artifacts.

Tasks do not own scenario meaning and do not become an SDL root section in this
decision. One scenario may support multiple tasks, and one task may be executed
many times.

### 2. Apparatus Context Is Run-Scoped Instrument Context

Execution apparatus context records the instrument conditions under which a run
is executed: canonical processor and backend components with identity and
manifests, participant implementation identity where relevant, selected
manifests, compatibility declarations, setup context, configuration parameters,
stochastic controls, clocks, measurement channels, observed setup evidence, and
known limitations.

Apparatus context is not SDL scenario meaning, task intent, runtime snapshot
metadata, or run result value. It may be embedded in an archival run record so a
run carries the exact context used.

The v1 contract intentionally rejects apparatus records that omit the primary
processor, primary backend, selected manifests, clocks, measurement channels, or
observed setup evidence. That strictness follows the cyber-range and simulation
V&V literature: apparatus conditions are part of the evidence, not optional log
metadata.

### 3. Run Is Archival Provenance, Not Live State

An experiment run is a durable record of executing one declared task. It records
the task reference, scenario snapshot reference, apparatus context, parameters,
stochastic controls, timestamps, clock context, status, outcome status, evidence
artifacts, result summaries, deviations, invalidation details, and lineage
references.

The run record may reference live observation artifacts captured at a specific
seal point, but it must not be reconstructed lazily from mutable
`RuntimeSnapshot`, `ControlPlaneStore`, operation-status, workflow-status, or
participant-episode state.

Archival run records require an end time, clock context, evidence artifacts,
result summaries, and result-to-evidence links that resolve to run evidence
artifact ids. Reported values must identify the metric they instantiate. ACES
also publishes a cross-artifact task/run validator so a run can be checked
against the referenced task protocol: run apparatus must satisfy the task
apparatus constraints, result metrics must be task-declared, and run evidence
artifacts must satisfy the task and metric observation requirements. Artifact
references include media type, URI, checksum, byte size, creation time, source,
`satisfies_refs`, explicit benchmark/agent-evaluation evidence roles, and
sensitivity so FAIR, RO-Crate, and PROV-style exports do not need to infer the
evidence surface from backend-private files. When an evidence requirement
includes digest or path metadata, the task/run validator binds those fields to
the concrete artifact checksum and URI/path rather than accepting an id-only
match.

### 4. Study And Collection Share One Contract

`experiment-study-v1` is the first-class analysis and grouping artifact. It
groups typed references to tasks, runs, results, evidence, analysis artifacts,
or reports with an owner, purpose, inclusion criteria, factors, analysis plan,
validity notes, and export/report artifacts.

If users need the word "collection", it is represented by `study_kind:
collection` within the same contract. ACES does not create a parallel
collection schema or service.

For `study` and `benchmark` records, research questions, validity notes, a
structured run allocation plan, and an analysis plan are mandatory. Run
allocation conditions
are not labels alone: each compared condition has a `condition_assignment` that
binds it to declared study factor levels and concrete run-level criteria such
as participant implementation, processor, backend, apparatus context, manifest,
capability, measurement channel, task/scenario snapshot identity, or parameter
values. Those condition criteria are restricted to auditable run-level
references and non-opaque parameters; catch-all `other` references and `other`
parameter kinds are not accepted as condition evidence, compared conditions
cannot share identical factor-level combinations or concrete criteria, and an
included run cannot satisfy more than one condition assignment. Declared
blocking factors must resolve to declared study factors with declared levels and
an appropriate blocking, stratification, apparatus, or control kind.
Analysis plans must name the analyzed metrics, primary metric, estimand/unit
assumptions, uncertainty procedure, multiple-comparison policy, and missing-data
policy. A semantic validator
grounds those metrics in the included task protocols and requires included
evaluation runs to carry result summaries, including explicit missing/withheld
statuses, for the analysis metrics before a study can support comparison
claims. The same semantic validation checks that evaluation-run membership
groupings cover the predeclared run-allocation conditions, that one run is not
counted in multiple conditions, that invalidated/superseded/not-evaluated runs
do not satisfy allocation, and that every condition meets the target run count
before analysis claims are accepted. Lighter `collection` and `cohort` records
remain available for curated grouping, but they still carry ownership, purpose,
membership, and inclusion criteria. If a collection or cohort carries an
analysis plan, the same invalidated/superseded/not-evaluated evaluation-run
exclusion applies even without run allocation.

### 5. Keep Runtime And API Work Out Of This Issue

This design publishes the contract set and formal specification. It does not
add scheduling, execution, persistence, HTTP APIs, analysis engines, or new SDL
authoring syntax. Later implementation work may consume these contracts, but
must reuse existing control-plane security, audit, idempotency, diagnostics,
and redaction patterns.

## Guardrails

- Do not put experiment tasks into SDL as a new root section without a new ADR.
- Do not treat SDL `objectives` as EXP-701 task records; they remain
  scenario-local objective declarations.
- Do not use a scenario name as task identity.
- Do not infer task identity from SDL alone.
- Do not store archival run records in `RuntimeSnapshot.metadata`.
- Do not treat operation ids, workflow run ids, participant episode ids, or
  snapshot addresses as portable experiment run ids.
- Do not use evaluator `detail` as study analysis authority.
- Do not use tags as studies.
- Do not hand-edit `contracts/schemas/`; change contract sources and regenerate.
- Do not persist credentials, bearer tokens, private keys, environment dumps,
  full tracebacks, backend-private objects, or process argv in experiment-core
  records, diagnostics, audit details, fixtures, logs, or examples.

## Consequences

### Positive

- ACES gains a publishable experiment-core schema set without changing SDL
  scenario syntax or runtime behavior.
- Scientific claims can distinguish scenario meaning, task protocol, apparatus
  context, execution provenance, result evidence, and study analysis.
- Future PROV/RO-Crate/OpenML-style exports have stable artifact roles and
  lineage links, checksums, timestamps, and evidence metadata to map from.
- Later runtime/persistence/API work has a contract boundary to consume rather
  than inventing live-state payloads first.

### Negative

- Authors must maintain both scenario artifacts and task/study artifacts when a
  scenario is used scientifically.
- The v1 contracts are intentionally conservative and do not implement
  statistics or export packaging themselves.

### Risks

- If later code treats these contracts as free-form metadata containers, the
  scientific boundary will collapse back into logs and tags.
- If apparatus fields are populated only from backend names and omit manifests,
  stochastic controls, clocks, and observed setup evidence, reproduced results
  will remain hard to interpret.
- If studies become informal folders before analysis semantics are implemented,
  benchmark comparability will be weak.
- If later APIs need draft or partial experiment records, they must introduce an
  explicit draft lifecycle surface rather than weakening these archival
  contracts.
