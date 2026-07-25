# Assessment Semantics

Implementer-facing reference for `SEM-206` (Assessment Semantics), governed by
ADR-016. The formal artifacts are
{download}`specs/formal/assessment/README.md <../../../specs/formal/assessment/README.md>`
and
{download}`specs/formal/assessment/pipeline-consistency.md <../../../specs/formal/assessment/pipeline-consistency.md>`;
this note is the working summary.

## The SDL carries no scoring/assessment pipeline

[ADR-073](../../decisions/adrs/adr-073-scoring-reward-language-scope.md) removed
the OCR-inherited scoring/assessment pipeline from the SDL authoring language.
The graded chain `conditions -> metrics -> evaluations -> tlos -> goals` and the
CybORG `agents.reward_calculator` label are no longer SDL surfaces:

- `metrics`, `evaluations`, `tlos` (Training Learning Objectives), and `goals`
  are removed. They expressed graded values, thresholds, and training-exercise
  objective/goal trees — read by a grader, not by a participant in-horizon.
- `agents.reward_calculator` is removed. It was an unbound free-text CybORG label
  with no cross-reference validator.

There is no score aggregation, no per-condition metric-exclusivity rule, and no
scoring-chain ordering/refresh derivation in authored SDL.

## What the SDL keeps

- **`conditions`** are observable state and remain a first-class SDL surface. A
  declared condition compiles onto a runtime `evaluation.condition.*` address
  (`evaluation.condition.<node>.<condition>` once bound); an unbound or ambiguous
  binding is reported at compilation as `evaluation.condition-ref-unbound` /
  `evaluation.condition-ref-ambiguous`.
- **`objectives`** are participant intent and remain first-class. An objective's
  `success` references **only** `conditions` — observable state, in-horizon and
  reproducible — never a graded score. Workflow predicates likewise reference
  `conditions`. The objective-success semantics are detailed in
  [objective-semantics.md](objective-semantics.md).

## Where graded scoring now lives

Graded scoring, cumulative reward, pass/fail evaluation, leaderboard values, and
evaluation outputs are an experiment/evaluator-plane concern, never authored SDL:

- **experiment-core contracts**
  ([ADR-055](../../decisions/adrs/adr-055-experiment-core-contract-boundary.md)):
  `experiment-task-v1` metric definitions and `experiment-study-v1` analysis
  plans;
- **evidence/measure contracts**
  ([ADR-064](../../decisions/adrs/adr-064-experiment-evidence-and-measure-contract-boundary.md)):
  `experiment-evidence-record-v1` (raw evidence) and
  `experiment-derived-measure-v1` (a derived measure or evaluation output);
- **the backend Evaluator**
  ([ADR-069](../../decisions/adrs/adr-069-cage-2-replication-architecture.md)
  §3), which projects reward, objective, terminal-condition, and scoring facts
  into RAES evaluation results, evidence records, and derived measures.

The runtime evaluator-result and execution contracts (`EvaluationResultContract`,
`EvaluationExecutionContract`, `validate_evaluation_result()`) remain the
portable, fail-closed observation boundary for evaluated success; score fields
stay confined to score-supporting evaluator resources and experiment-derived
measures, not SDL objectives or participant outcomes.

## Participant outcome interpretation

The SEM-215 participant outcome-interpretation layer keeps its
`reward_signal` / `evaluation_result` interpretation layers as a governed
interpretation relation. They no longer bind to any SDL `evaluations` section —
a governed `reward_signal` interpretation is not an authored reward calculator
and adds no score/reward field to participant outcome reports.
