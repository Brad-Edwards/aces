# ML Experiment Rigor Notes For ACES Experiment Core

Issue #87 needs a design that can carry the evidential burden of ML-style
evaluation and comparison. These notes summarize the academic expectations that
should shape EXP-701 through EXP-705.

## Core Claim From The Literature

The ML methods literature increasingly treats experiment metadata as part of
the scientific result. Reported metrics are not interpretable without task
definition, sampling frame, data version, leakage controls, model/process
configuration, stochastic controls, evaluation protocol, and analysis plan.

Relevant sources:

- Kapoor et al. 2024, REFORMS. DOI: 10.1126/sciadv.adk3452.
- Kapoor and Narayanan 2023, leakage review. DOI:
  10.1016/j.patter.2023.100804.
- Walsh et al. 2021, DOME recommendations. DOI:
  10.1038/s41592-021-01205-4.
- Haibe-Kains et al. 2020, AI transparency/reproducibility. DOI:
  10.1038/s41586-020-2766-y.
- Gundersen and Kjensmo 2018, reproducibility in AI. DOI:
  10.1609/aaai.v32i1.11503.
- Pineau et al. JMLR reproducibility program report.

## Task Definition Must Include Evaluation Protocol

ACES should not define an experiment task as only a scenario pointer. In ML
benchmarks, the task binds data, target, evaluation procedure, and metric
semantics. OpenML and experiment-database work are especially relevant:

- OpenML separates data sets, tasks, flows, runs, and evaluations.
- Experiment databases organize repeated experiments so later meta-analysis can
  compare algorithms, data conditions, and evaluation results.
- OntoDM and MEX show that task/process/evaluation concepts are separable
  metadata entities, not just free-text annotations.

Design requirement:

- `experiment_task` must reference an authored scenario or scenario snapshot,
  but also define the evaluation protocol, metric set, population/scope, unit of
  analysis, admissible processors/backends when relevant, and intended evidence
  use.
- A scenario may participate in many tasks. A task may constrain a scenario by
  selecting an evaluation protocol, participant role, traffic profile, attack
  model, data split, measurement window, or result acceptance rule.

## Leakage Controls Are First-Class Design Inputs

Kapoor and Narayanan show that leakage is a recurring failure mode in
ML-enabled science. For ACES, leakage can occur through data, topology,
measurement, task authoring, participant context, or post-hoc protocol choices.

ACES should record:

- training/calibration/evaluation partitioning when a task uses learned
  components or adaptive agents;
- grouping constraints that prevent same-entity contamination between train and
  evaluation sets;
- temporal availability constraints for telemetry, alerts, logs, and
  participant observations;
- whether scenarios, host images, flags, task hints, solution traces, or
  generated labels are available to the system being evaluated;
- leakage checks or known unresolved leakage risks;
- protocol version and any deviations made before run execution.

Design requirement:

- Leakage and split fields belong in task/protocol and study/analysis records,
  not in mutable run status. A run records which protocol version it executed.

## Metrics Need Semantics, Not Names Alone

REFORMS, DOME, Model Cards, Datasheets, and statistical-comparison literature
all imply that a metric name alone is too weak. ACES must capture enough
semantics for later analysis.

ACES should record per metric:

- metric identifier and version;
- measured construct or outcome;
- unit of analysis;
- aggregation level;
- directionality;
- required input observations;
- missingness policy;
- confidence interval or uncertainty method when reported;
- calibration or threshold policy when binary decisions are made;
- evaluator implementation reference where applicable.

The run result should contain observed values and pointers to raw evidence, but
the task or study should define what the metric means.

## Repeated Runs And Stochastic Controls

ML and reinforcement learning reproducibility work stresses seeds, repeated
runs, stochastic policies, nondeterministic backends, and compute variance.
Cyber ranges add additional nondeterminism from scheduling, network timing,
host load, attack/defense agents, and environment provisioning.

ACES run records should preserve:

- seed set and seed roles;
- randomization unit and assignment;
- repeated-run index and replicate family;
- nondeterminism declarations that cannot be controlled;
- host/backend timing and resource context;
- processor identity and version;
- image, manifest, and dependency snapshots;
- task version and scenario snapshot;
- execution start/end times and clock source.

Design requirement:

- `experiment_run` is an archival execution record. It is not the live
  lifecycle state object and should not be overwritten as the control plane
  progresses.

## Statistical Comparison And Study Structure

Dietterich, Demsar, Nadeau and Bengio, and Arlot and Celisse show that
comparison claims require more than a table of scores. The design needs a place
for study-level comparison methods and repeated-run structure.

ACES studies should capture:

- research question or comparison claim;
- compared systems/processors/policies/configurations;
- task collection and task sampling rationale;
- run allocation plan;
- blocking, grouping, stratification, or randomization;
- cross-validation or holdout design when relevant;
- statistical test or estimation method;
- multiple-comparison handling;
- effect-size and uncertainty reporting plan;
- stopping rules or run-count rationale;
- missing-run and failed-run handling.

Design requirement:

- EXP-705 should define `study` and `collection` records that group tasks,
  runs, and result artifacts while preserving analysis intent.

## Reporting Artifacts And Transparency

Model Cards, Datasheets, DOME, REFORMS, and data-statement work push toward
structured reports that identify intended use, limitations, data provenance,
subgroup behavior, and known caveats.

ACES should support, at minimum:

- intended use and non-use statements for a task/study;
- data/scenario origin and version;
- participant or system population represented by the task;
- subgroup/slice definitions for metrics;
- ethical/safety constraints when experiments involve generated attacks,
  malware-like payloads, or participant telemetry;
- known limitations and validity threats;
- pointers to raw evidence and analysis notebooks or scripts.

Design requirement:

- Design documentation should avoid treating these as prose-only appendices.
  The core model should reserve structured extension points for validity,
  fairness/slice analysis, and reporting artifacts.

## Acceptance Criteria For The ACES Design

The experiment core design should be considered inadequate if it cannot answer
the following questions from structured records:

- What scenario or scenario snapshot was evaluated?
- What task transformed that scenario into an experiment-ready evaluation?
- What processor/backend/system under test executed it?
- What protocol, metric definitions, and analysis plan applied?
- What stochastic controls and apparatus context were in force?
- What run produced each result value?
- What evidence artifacts support the result?
- What study or benchmark collection makes the result comparable?
- What data split, grouping, leakage, and validity controls constrain the
  interpretation?
- What identifiers and versions make the record reusable outside this repo?
