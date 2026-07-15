# ADR-074: Experiment Authoring-Input Contract Boundary

## Status

accepted

## Date

2026-07-08

## Classification

Classification: FM2
Required artifacts: ADR, formal-spec update, published schema, fixtures,
worked examples, MCP authoring tools, discovery/validation test, amendments to
ADR-055 and ADR-069
Waivers: No runtime execution, scheduling, persistence, HTTP API, or analysis
engine is introduced by this issue. The new contract is an authoring/input
surface that is consumed by later run/orchestration work, not an executor.

## Context

Issue #675 observes an asymmetry in ACES authoring surfaces. SDL scenarios are
a first-class *authoring* surface: authored `examples/scenarios/*.sdl.yaml`
files, a published `sdl-authoring-input-v1` schema, MCP `sdl_validate` /
`sdl_scaffold` tools, and a discovery test that validates every worked example
against the published schema.

The experiment-core contracts published under ADR-055, ADR-064, and ADR-065
(`experiment-run-v1`, `experiment-study-v1`, `experiment-apparatus-context-v1`,
`experiment-task-v1`, capture-spec, evidence, derived-measure) are the
opposite. Every one is framed as an **archival provenance OUTPUT emitted by a
run** — `ExperimentRunModel` is literally "Archival provenance record for one
execution." There is no authoring path — file or MCP tool — to *specify* an
experiment (run count, seeds, red-variant selection, turn order, step count,
termination, condition assignments) as an **input** artifact before execution.
The only in-repo instances are conformance fixtures.

A full CAGE-2 specification is scenario **plus** experiment. ADR-069 routes the
CAGE-2 scenario half through the existing SDL authoring surface, but the
experiment half — REP-003's "turn order, fixed step counts, episode
termination, red-agent variants, randomization, seeds, and stochastic controls"
(ADR-069 §2, and the execution-control equivalence tier in §7) — has no pre-run
authoring home. "Fully specify the CAGE-2 experiment" is therefore not a
supported workflow today.

ADR-055 anticipated this exact need but deliberately deferred it. Its §5 states
the design "does not add scheduling, execution, persistence, HTTP APIs,
analysis engines, or new SDL authoring syntax," while "later implementation
work may consume these contracts." Its Risks section is more specific: "If
later APIs need draft or partial experiment records, they must introduce an
explicit draft lifecycle surface rather than weakening these archival
contracts." The EXP design-criteria note (Principle 1) independently warns
against "a single `experiment` object that means scenario, task, run, and study
depending on which fields are present," and (Principle 2) notes that "planned
apparatus and observed apparatus evidence must both be representable."

## Decision

Publish a new, separate authoring-input contract `experiment-authoring-input-v1`
(model `ExperimentSpecModel`) that specifies an experiment before it executes.
It is the input counterpart to the archival experiment-core outputs, exactly as
`sdl-authoring-input-v1` is the authored counterpart to `instantiated-scenario-v1`.

### 1. It is a separate input contract, not a mutation of the archival family

The archival contracts (`experiment-run-v1`, `experiment-study-v1`,
`experiment-apparatus-context-v1`) are unchanged. The authoring input is a new
closed-world `ContractModel` generated into `contracts/schemas/experiment-core/`
and recorded in the schema-publication manifest, following ADR-055's directive
to introduce an explicit draft/authoring surface rather than weaken the archival
records, and ADR-061's schema-evolution discipline.

### 2. It references the separated concepts rather than re-declaring them

Per the separation principle, the spec is a lean design that binds already-
separated concepts:

- `task_ref` references a separately authored `experiment-task-v1` (which
  carries scenario + protocol + metric definitions); the spec does not
  duplicate task meaning.
- `intended_scenario_ref` optionally pins the intended scenario snapshot.
- `apparatus_intent` reuses the input-shaped `ExperimentApparatusConstraintModel`
  (allowed processors/backends, required manifests/capabilities). It is the
  *planned* apparatus, distinct from the run-scoped *observed*
  `ExperimentApparatusContextModel`.
- `capture_spec_refs` reference `experiment-capture-spec-v1` artifacts.
- `factors`, `validity_notes`, and `artifact_refs` reuse the existing
  experiment-core value models.

### 3. The run plan carries the pre-run experimental design

`run_plan` composes reuse and the genuinely-new authoring fields:

- `stochastic_controls` (reused) declare seeds and randomization.
- `allocation` (reused `ExperimentRunAllocationPlanModel`) declares
  condition-based run counts, replication, and condition assignments; or, for a
  simple design, `target_run_count` declares a flat count. Exactly one of the
  two is present.
- `episode_control` (new) declares turn order, logical step count, and episode
  termination — the execution-control facts ADR-069 §7 requires.
- `red_variant_selections` (new, keyed by variant id) select red-agent variants.
- `clock_intent` (reused) declares the intended time domain.

Identifier-bearing repeated children are keyed object maps (ADR-055 rule).
Cross-map constraints that portable JSON Schema cannot express — exactly-one run
count source, red-variant map-key equality, and blocking factors resolving to
declared factors — are declared as `x-aces-invariants` and enforced by the ACES
model validators, consistent with ADR-055's semantic-invariant profile.

### 3a. The authoring input is not an admitted trial plan

ADR-084 makes the downstream boundary explicit. The authoring input declares
experiment intent. A separate processor-owned operation combines an admitted
spec with the exact composed scenario family, task, apparatus
manifests/envelopes, and accepted compiler/identity/random-stream profiles to
produce an immutable admitted trial plan.

Typed selection/allocation policies may extend the run plan under ADR-061, but
existing free-text allocation/randomization fields and seeds do not become
executable by convention. The admitted plan records concrete logical
coordinates, selections, factor assignments, apparatus bindings, and
preallocated archival run ids. It is neither this authoring document nor an
`experiment-run-v1` / `experiment-study-v1` output.

### 4. Authoring surface parity with SDL

The contract ships an authored-file convention (`examples/experiments/*.exp.yaml`),
a thin Pydantic loader (`aces_contracts.experiment_spec.load_experiment_spec`;
no SDL-style parser is needed because the document has no shorthand or
cross-file resolution), MCP authoring tools (`experiment_scaffold`,
`experiment_validate`, `experiment_get_example`), and a discovery test that
validates every worked `.exp.yaml` against the published schema — mirroring the
SDL authoring surface and satisfying AUT-801's agent-facing authoring mandate.

### 5. Runtime and orchestration remain out of scope

Like ADR-055, this decision publishes a contract, a formal spec, tooling, and
examples. It does not schedule, execute, persist, or evaluate experiments. A
future orchestration surface consumes an authored spec through ADR-084's
trial-compilation/admission boundary, then produces the archival
`experiment-run-v1` / `experiment-study-v1` records from actual executions.

## Guardrails

- Do not treat the authoring input as a run, study, or apparatus-context
  record; it is pre-run design, not provenance.
- Do not weaken the archival experiment-core contracts to carry draft or
  partial data — that is exactly what this surface exists to avoid.
- Do not duplicate task, scenario, or capture-spec meaning inside the spec;
  reference the authored artifacts.
- Do not hand-edit `contracts/schemas/`; change the contract source and
  regenerate.
- Do not add a parallel experiment-authoring DSL or SDL section; the spec is a
  single nested contract document.
- Do not treat descriptive stochastic fields or a seed as an executable
  random-stream contract, and do not let a scheduler/backend create selections
  that are absent from the admitted plan.

## Consequences

### Positive

- An experiment can be authored and validated before execution, closing the
  asymmetry with SDL scenarios and giving REP-003 a home to declare CAGE-2
  execution-control facts pre-run.
- The archival contracts and their scientific boundary are untouched.
- The authoring surface reuses the existing published schema, fixture,
  conformance, and MCP machinery rather than inventing new mechanisms.

### Negative

- Authors now maintain a task artifact and an experiment-spec artifact when a
  task is used in a designed experiment.
- The spec references artifacts (task, capture-spec) by id; cross-artifact
  existence is not resolved by the loader and is left to downstream
  orchestration.

### Risks

- If later orchestration code treats the spec as free-form metadata, the
  input/output boundary could blur back into the archival records. Conformance
  and review must keep the surfaces distinct.
- The reused `ExperimentRunAllocationPlanModel` annotates its semantic
  invariant against `experiment-study-v1`; when embedded in the authoring input
  the annotation still names study. This is documented in the formal spec and is
  harmless because the model validator runs regardless.

## Alternatives Considered

### Add authoring fields to the archival run/study contracts

Rejected. ADR-055 explicitly forbids weakening the archival contracts to carry
draft/partial data and directs a separate draft lifecycle surface instead.

### Add a CAGE-specific experiment schema for REP-003

Rejected. ADR-069 rejects CAGE-specific schemas; the authoring surface is a
general experiment-core contract that REP-003 uses, not a CAGE fork.

### Author experiments as a new SDL section

Rejected. ADR-055's guardrails forbid putting experiment concepts into SDL as a
new root section, and an experiment is not scenario meaning.

### Defer authoring to a future runtime/API milestone

Rejected. The issue asks specifically for an authoring surface analogous to SDL;
the contract + tooling can and should exist independently of execution, exactly
as the SDL authoring surface predates full runtime realization.

## Amendments

| Date | Commit/PR | Summary |
|------|-----------|---------|
| 2026-07-15 | #652 | Clarified that experiment authoring input is consumed by a separate deterministic trial-compilation/admission boundary and that descriptive stochastic fields are not executable profiles. |
