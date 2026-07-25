# Assessment Semantics (SDL scoring chain removed)

[ADR-073](../../../docs/decisions/adrs/adr-073-scoring-reward-language-scope.md)
removed the OCR-inherited SDL scoring/assessment pipeline. The graded chain that
these formal artifacts once specified —
`condition bindings -> metrics -> evaluations -> TLOs -> goals` — is no longer an
SDL authoring surface: the `metrics`, `evaluations`, `tlos` (Training Learning
Objectives), and `goals` sections and the CybORG `agents.reward_calculator`
label are gone.

## What remains in the SDL

- `conditions` are **observable state** and stay a first-class SDL surface. They
  compile onto runtime `evaluation.condition.*` addresses.
- `objectives` are participant intent and stay first-class. An objective's
  `success` references **only** `conditions` (observable state), not a graded
  score (see [`../objectives/`](../objectives/README.md) for the objective-success
  semantics under `SEM-207`).
- Workflow predicates reference `conditions`.

There is no condition→metric→evaluation→TLO→goal scoring chain, no score
aggregation rule, no per-condition metric-exclusivity rule, and no
scoring-chain ordering/refresh derivation in the SDL.

## Where graded scoring now lives

Graded scoring, cumulative reward, pass/fail evaluation, leaderboard values, and
evaluation outputs live exclusively in the experiment/evaluator plane, never as
authored SDL:

- experiment-core contracts
  ([ADR-055](../../../docs/decisions/adrs/adr-055-experiment-core-contract-boundary.md)):
  `experiment-task-v1` metric definitions, `experiment-study-v1` analysis plans;
- evidence/measure contracts
  ([ADR-064](../../../docs/decisions/adrs/adr-064-experiment-evidence-and-measure-contract-boundary.md)):
  `experiment-evidence-record-v1`, `experiment-derived-measure-v1`;
- the backend **Evaluator**
  ([ADR-069](../../../docs/decisions/adrs/adr-069-cage-2-replication-architecture.md)
  §3), which projects reward, objective, terminal-condition, and scoring facts
  into RAES evaluation results, evidence records, and derived measures.

The governing requirement remains **SEM-206 (Assessment Semantics)**;
[`../../../docs/explain/reference/assessment-semantics.md`](../../../docs/explain/reference/assessment-semantics.md)
carries the implementation-facing reference for the narrowed semantics.
