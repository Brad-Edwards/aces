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
rules live in `specs/formal/experiment-core/`.

Identifier-bearing repeated children are represented as keyed object maps
rather than arrays when uniqueness is part of the contract: metric definitions
are keyed by metric id, apparatus components by component id, run result
summaries by result id, study membership entries by member id, and study
factors by factor id. This keeps the published JSON Schemas authoritative for
portable consumers instead of leaving uniqueness only to Python validators.
Manifest-specific fields use manifest-constrained references so apparatus
context cannot silently point to runs, studies, or other artifact kinds where a
manifest boundary is required.

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
is executed: processor/backend/participant implementation identity, selected
manifests, compatibility declarations, setup context, configuration parameters,
stochastic controls, clocks, measurement channels, observed setup evidence, and
known limitations.

Apparatus context is not SDL scenario meaning, task intent, runtime snapshot
metadata, or run result value. It may be embedded in an archival run record so a
run carries the exact context used.

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

### 4. Study And Collection Share One Contract

`experiment-study-v1` is the first-class analysis and grouping artifact. It
groups typed references to tasks, runs, results, evidence, analysis artifacts,
or reports with a purpose, inclusion criteria, factors, analysis plan, validity
notes, and export/report artifacts.

If users need the word "collection", it is represented by `study_kind:
collection` within the same contract. ACES does not create a parallel
collection schema or service.

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
  lineage links to map from.
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
