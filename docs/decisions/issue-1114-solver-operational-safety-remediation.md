# Issue 1114 Solver Operational-Safety Remediation

Date: 2026-08-11

Issue: #1114. Requirement: ASR-530. Related lineage: closed issue #826.

This note records the bounded operational-safety correction without modifying
the immutable issue-826 preflight. It does not change the v1 theory,
solver package pin, solver configuration contract, witness order, or
core-reduction order.

## Gap Claim

Z3 may return `unknown` under the configured per-check timeout. The witness and
core loops compared only against their desired decisive result, so `unknown`
could silently skip a canonical witness candidate or retain a removable core
clause while the emitted evidence still claimed the governed selection rule.
Duplicate clause ids also reached tracked assumptions through a collapsing
dictionary, and empty memberships relied on an implicit zero-argument `Or`.

## Existing Surface Audit

The normalized contract already requires unique clause ids and finite bounded
symbols, domains, and clauses. The service already translates adapter failure
to `SatisfiabilityOperationalError`, and the evidence contract already records
the 5000 ms per-check timeout. The shared `_check()` seam is used by the initial
decision, witness selection, and core reduction, making it the single complete
place to reject `unknown`.

## Lineage And Precedent

ADR-086 and the normative satisfiability specification distinguish completed
SAT/UNSAT outcomes from operational failure. The issue-826 preflight explicitly
forbids mapping unknown, timeout, or exhaustion to a semantic outcome and
requires bounded repeated checks for canonical witnesses and reduced cores.

## Literature And Practice

SMT solver APIs expose `sat`, `unsat`, and `unknown` as distinct results; a
resource-limited `unknown` is not evidence for either decision. Deterministic
core reduction and lexicographic witness selection therefore require every
probe to complete decisively before their stronger labels may be published.

## Alternatives Considered

1. **Retain the old branch behavior.** Rejected because it can publish an
   overclaim that appears only as later replay drift.
2. **Map unknown to `unsupported`.** Rejected because translation coverage is
   complete; solver non-completion is an operational failure.
3. **Retry unknown automatically.** Rejected because unrecorded retries change
   the operational profile and can make latency unbounded.
4. **Add a caller-configurable check limit to the v1 wire contract.** Rejected
   as an unnecessary profile/schema change.
5. **Reject unknown centrally and derive a finite check budget from the bound
   normalized model.** Chosen.

## Chosen Architecture

Before constructing tracked assumptions, the adapter defensively rejects
duplicate clause ids. Empty membership is explicitly `false`. `_check()` raises
a structured `SolverOperationalError` for `unknown`, recording phase, check
count, derived check budget, the governed 5000 ms timeout, and Z3's bounded
reason string. The service preserves those safe fields on
`SatisfiabilityOperationalError`; it emits no partial evidence.

For model symbols `S`, domains `D(s)`, and clauses `C`, the run budget is:

```text
B = 1 + max(|C|, sum(|D(s)| for s in S))
```

One check is the initial decision. Only one of the bounded branches then runs:
at most one deletion probe per clause, or at most one feasibility probe per
domain member. The budget is thus derived from digest-bound normalized input,
not a hidden configuration knob, and its maximum is bounded by the published
contract cardinalities.

## Documentation Defense

The normative solver section now states the decisive-result rule, explicit
empty-membership semantics, derived budget, and observable operational-error
fields. No schema is regenerated because completed evidence is unchanged and
an operational failure emits no evidence envelope.

## Verification Plan

- Force the first or second solver call to return unknown and prove that no
  outcome, witness, or core evidence is emitted.
- Assert phase, call count, budget, timeout, and reason survive the service
  boundary.
- Inject duplicate clause identity past model validation and require a bounded
  adapter error rather than a raw Z3 exception.
- Exercise an empty target domain as explicit unsatisfiability and exhaust a
  synthetic zero-check budget before solver construction.
