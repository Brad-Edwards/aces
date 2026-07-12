# ADR-078: Backend-Neutral Proposition and Truth Semantics

## Status

accepted

## Date

2026-07-12

## Classification

Classification: FM2

Required artifacts: closed authoring models, pure truth tables, semantic
validation, compiled resources, capability declarations, portable result
contracts, published schemas and fixtures, cross-backend fixtures, and explicit
migration diagnostics.

Waivers: ACES does not claim a complete temporal logic, a theorem-proved
evaluator, or behavioral equivalence between backends. Runtime checks exercise
the finite algebra and contract invariants implemented here.

## Context

ACES inherited `Condition` as an executable command-plus-schedule or package
source. ADR-002 and ADR-073 later described conditions as observable state and
made `objectives.*.success.conditions` the meaning of success. Those statements
were inconsistent with the actual model: command text, exit status, polling
interval, and package identity specify a probe implementation, not a
proposition about the scenario world.

That conflation prevents independent review and reproducible comparison. Two
backends can run different probes under the same condition name without a
shared statement of what is expected, and a successful process can be mistaken
for a true world-state claim. It also collapses false, insufficient evidence,
probe failure, and absent backend capability.

## Decision

### 1. Separate four contracts

ACES separates:

1. A **proposition**: a named, inert claim over a finite set of canonical SDL
   subjects. It declares whether its facts come from admitted declared state or
   observed state, a closed typed predicate, explicit quantification, and any
   authored evidence requirements.
2. An **assertion**: one use of a proposition as a precondition, invariant, or
   postcondition, with positive or negative polarity.
3. A **probe binding**: a capability-bound realization of a proposition. A
   legacy `Condition.command` or `Condition.source` may supply implementation
   mechanics only when it explicitly names the proposition it realizes.
4. A **truth result**: an evidence-bearing evaluation record that preserves
   proposition and assertion identity, polarity, realization provenance,
   governed boundary/clock context, evidence references, and loss disclosure.

None of these is a score, reward, participant perception, evaluator lifecycle
status, or command result. `EvaluationResultState.passed` remains a lifecycle
surface and cannot substitute for a proposition truth result.

### 2. Use a closed typed predicate language

The initial predicate families are presence, Boolean, string/membership, and
numeric comparison. Each family admits only operators meaningful for its
operand type. Numeric predicates name a unit and its semantic reference.

Every predicate carries both a readable local property name and a stable HTTPS
or URN semantic reference. The reference is the cross-system identity; prose
description is explanatory, not a substitute for it. The language admits no
shell, Python, callback, regular-expression policy, JSONPath, JMESPath, or
backend-native query expression.

Subjects are explicit canonical SDL references and therefore form a finite set
after instantiation. Quantification is `all`, `any`, or `at_least`; an
`at_least` threshold cannot exceed the subject count. This issue does not add
unbounded domain quantification or dynamic discovery semantics.
Numeric operands must be finite; NaN and infinities are not portable comparison
values.

### 3. Define the portable outcome algebra precisely

The semantic truth values are `true`, `false`, and `unknown`. This is consistent
with finite-observation runtime-verification practice in which a partial trace
may be inconclusive. `unsupported` is not a fourth logical truth value: it is a
realization disposition stating that the selected apparatus cannot evaluate
the proposition with the required predicate, evidence, or time guarantees.
ACES includes it in the portable outcome enum so an adapter cannot collapse
capability absence into unknown or false.

Negation swaps only true and false. It preserves unknown and unsupported.

For `all_of`, false is decisive; all true yields true; otherwise unsupported
dominates unknown. For `any_of`, true is decisive; all false yields false;
otherwise unsupported dominates unknown. For `at_least(k)`, at least `k` true
values yields true; fewer than `k` possible true values after counting unknown
and unsupported yields false; otherwise the result is unsupported when any
required undecided operand is unsupported, and unknown otherwise. Empty
composition and invalid thresholds are rejected.

The same tables aggregate per-subject predicate outcomes: proposition `all`
maps to `all_of`, `any` maps to `any_of`, and `at_least(k)` maps directly to
`at_least(k)`.

Conflicting evidence is `unknown` with a typed reason. ACES does not claim to
implement Belnap's four-valued paraconsistent logic. Partial, redacted, or lossy
evidence may decide true or false only when every disclosed loss remains within
an admitted bound. Ordinary absence of an observation is unknown; it is not
evidence of falsity.

### 4. Keep time and evidence claims governed

Preconditions apply at a governed start boundary, postconditions at a governed
completion boundary, and invariants over the owning governed window. Objective
window references determine orchestration scope and refresh dependencies; they
do not establish a clock.

An observed decided result must name a boundary, time domain, and clock
authority. This decision does not promote participant-specific time carriers
into a general SDL clock or invent backend-local wall-clock semantics. A
backend unable to supply the required governed temporal context reports
unsupported. A sampled observation does not prove an interval invariant unless
a later governed observation contract defines and satisfies that coverage
claim.

Authored evidence requirements remain capture intent. A decided observed result
must cite captured evidence and a digest-identified probe binding. Provenance
supports audit and replay; it does not prove that the referenced process ran or
that its evidence is truthful.

Runtime admission also requires each result to reference the admitted
proposition and assertion entries whose basis, proposition link, and polarity
match the result. Envelope validity alone cannot authorize a detached truth
claim.

### 5. Replace ambiguous consumers and fail migration closed

Objective success composes invariant and postcondition assertion references.
Event triggers, workflow predicates, and participant starting state consume
precondition assertion references. `nodes.*.conditions` remains probe
placement; it does not become a state claim.

The removed `success.conditions`, event/workflow condition predicates, and
`starting_conditions` fields receive bounded migration errors. A migrator may
carry command/source mechanics into a probe binding, but it cannot infer a
property, expected value, polarity, quantifier, evidence adequacy, or temporal
meaning from command text or package identity. Existing identifiers may be
retained only when the author supplies the missing proposition/assertion
meaning explicitly.

### 6. Bound equivalence claims

Two results from different probe bindings are **semantically claim-equivalent**
when their proposition, assertion, polarity, outcome, basis, governed temporal
context, loss disclosure, and unsupported capability set agree. Their evidence
and binding provenance remain distinct.

This equality is not observational equivalence of the backends. ACES does not
claim Park-Milner bisimulation without a declared labelled transition system,
observable and hidden actions, and a bisimulation relation. Result equality is
also not evidence equality, replay equivalence, or apparatus equivalence.

## Consequences

Authors can review objective truth from SDL without executing arbitrary code,
and backends can disclose inability to realize a claim without falsifying it.
The cost is a deliberately breaking migration from ambiguous condition
references and more explicit evidence/capability metadata.

The initial property vocabulary remains extensible through stable semantic
references. ACES does not yet publish a complete cyber-observable ontology;
semantic references make that limitation visible and permit later governed
profiles without changing the predicate algebra.

## References

- Andreas Bauer, Martin Leucker, and Christian Schallhart, "Runtime
  Verification for LTL and TLTL," *ACM Transactions on Software Engineering and
  Methodology* 20(4), 2011. <https://doi.org/10.1145/2000799.2000800>
- Ron Koymans, "Specifying Real-Time Properties with Metric Temporal Logic,"
  *Real-Time Systems* 2, 1990. <https://doi.org/10.1007/BF01995674>
- David Park, "Concurrency and Automata on Infinite Sequences," LNCS 104,
  1981. <https://doi.org/10.1007/BFb0017309>
- W3C, *PROV-DM: The PROV Data Model*, Recommendation, 2013.
  <https://www.w3.org/TR/prov-dm/>
