# Assessment Pipeline Consistency (removed)

[ADR-073](../../../docs/decisions/adrs/adr-073-scoring-reward-language-scope.md)
removed the SDL scoring/assessment pipeline. This spec formerly defined the
consistency rules for the graded chain

```text
condition bindings -> metrics -> evaluations -> TLOs -> goals
```

— reference resolution along the chain, the "at most one metric per condition"
exclusivity rule, the `min-score` / metric-`max-score` aggregation rule, and the
scoring-chain ordering/refresh derivation. None of those surfaces
(`metrics`, `evaluations`, `tlos`, `goals`) exist in the SDL any longer, so none
of those consistency rules apply.

## What is left

`conditions` remain the SDL's **observable state**. A condition compiles onto a
runtime `evaluation.condition.*` address, and its consistency (a condition
binding that resolves to no bound node, or to more than one) is still enforced at
compilation as `evaluation.condition-ref-unbound` /
`evaluation.condition-ref-ambiguous` against the resolved addresses. Objective
`success` and workflow predicates reference `conditions` only; the
objective-success reference model is in
[`../objectives/declarative-objective-semantics.md`](../objectives/declarative-objective-semantics.md).

## Where graded scoring now lives

Graded scoring, reward, and evaluation outputs are an experiment/evaluator-plane
concern — experiment-core contracts
([ADR-055](../../../docs/decisions/adrs/adr-055-experiment-core-contract-boundary.md)),
the evidence/measure contracts
([ADR-064](../../../docs/decisions/adrs/adr-064-experiment-evidence-and-measure-contract-boundary.md)),
and the backend Evaluator
([ADR-069](../../../docs/decisions/adrs/adr-069-cage-2-replication-architecture.md)
§3) — never authored SDL.
