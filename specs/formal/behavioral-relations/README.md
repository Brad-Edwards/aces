# Behavioral-Relation Taxonomy And Claim Discipline

Classification: FM2, relation and assurance semantics.

## Scope And Authority

This specification governs the meaning of ACES claims about validation,
conformance, realization, comparison, refinement, equivalence, participant
visibility, multi-agent interaction, and empirical adequacy. It prevents a
weaker observation from being reported as a stronger behavioral result.

The machine-readable authority is
`contracts/concept-authority/behavioral-relations-v1.json`, contract
`behavioral-relations/v1`, taxonomy `aces-behavioral-relations`, revision
`rev2`. Relation identifiers, formal dimensions, claim-surface defaults,
bibliography coordinates, assurance status, and worked transition systems are
normative there. ADR-081 governs the architecture. This document is the
normative reader-facing formalization of that catalog.

Revision `rev2` adds the SEM-230 `policy-noninterference` relation and its
dedicated participant-information-flow claim surface. The JSON contract remains
`behavioral-relations/v1` because its closed shape is unchanged. Revision `rev1`
is historical taxonomy identity; current in-repository producers bind `rev2`.

The taxonomy defines claim vocabulary and proof obligations. It does not add a
model checker, theorem prover, stochastic simulator, game solver, scheduler,
or runtime engine. A relation whose definition is present but whose assurance
record is `future` or `deliberately-unproved` remains unproved.

## Core Objects

Let a labelled transition system be

```text
L = (S, A, H, ->, I)
```

where `S` is a state set, `A` is the action-label set, `H` is the set of hidden
actions, `->` is a labelled transition relation, and `I` is an initial-state
set. A relation definition MUST say when this signature is applicable. A
non-transition predicate MUST explicitly record why the signature is not
applicable rather than silently borrowing transition-system language.

An observation projection is a revisioned function

```text
pi[p, policy, revision] : concrete history -> participant-visible history
```

with an identified subject, redaction scope, order treatment, and simultaneity
treatment. Two histories are never compared “from the participant view” unless
all of those coordinates are fixed. Projection equality is not access to
hidden global state and does not imply future knowledge or strategic power.

A claim quantifies separately over states, traces, schedulers, strategies,
environments, and observations. “All” on one axis says nothing about an omitted
axis. A finite case set therefore cannot satisfy a universal quantifier merely
because every executed case passed.

## Relation Families

The following identifiers are distinct. A consumer MUST use the exact catalog
identifier rather than an artifact-local synonym.

| Relation id | Class | What it establishes |
| --- | --- | --- |
| `structural-validity` | predicate | Closed-shape and field-constraint admission under a named schema revision. |
| `semantic-validity` | predicate | Cross-reference and semantic-invariant admission under a named semantic profile. |
| `capability-declaration` | predicate | What an apparatus declares, without proving that declaration true. |
| `profile-satisfaction` | predicate | Satisfaction of every obligation in one named profile. |
| `bounded-probe-success` | predicate | Expected results for an enumerated finite case set. |
| `canonical-artifact-identity` | predicate | Equality of canonical bytes or digest under one canonicalization profile. |
| `realization-envelope-membership` | set relation | A request lies inside one backend realization envelope. |
| `realization-envelope-subsumption` | set relation | Every request admitted by one envelope is admitted by another. |
| `trace-inclusion` | behavioral | Every projected trace on the left is admitted on the right. |
| `trace-equivalence` | behavioral | Mutual projected trace inclusion. |
| `forward-simulation` | behavioral | Each left step is matched by the right under a state relation. |
| `backward-simulation` | behavioral | The reverse directional simulation obligation. |
| `data-refinement` | behavioral | Concrete operations preserve an abstract data-type relation and observations. |
| `strong-bisimulation` | behavioral | Every labelled step is matched in both directions without hiding actions. |
| `weak-bisimulation` | behavioral | Both directions match visible steps while admitting governed hidden-action closure. |
| `participant-projected-history-equivalence` | behavioral | Two histories are equal after the same named participant projection. |
| `policy-noninterference` | behavioral | Unauthorized high-input variation preserves the support set of participant-visible histories under fixed low-equivalence, dynamic purge, declassification, policy, scheduler/environment, and order assumptions. |
| `epistemic-indistinguishability` | epistemic | Two worlds are indistinguishable to a named participant under an information model. |
| `alternating-strategic-equivalence` | strategic | Named coalitions preserve abilities against quantified opponent choices. |
| `probabilistic-bisimulation` | behavioral | Related states assign equal probability mass to related equivalence classes. |
| `statistical-similarity` | empirical | A declared sample-level similarity result under a named metric and uncertainty procedure. |
| `statistical-equivalence` | empirical | A declared equivalence-test result inside a predeclared margin. |
| `empirical-adequacy` | empirical | Evidence satisfies a preregistered adequacy criterion for a bounded population and purpose. |

None of these rows is an implication ladder. For example:

- `canonical-artifact-identity` does not establish execution equality;
- `bounded-probe-success` does not establish `trace-inclusion`;
- `trace-equivalence` does not preserve branching structure and does not
  establish `strong-bisimulation`;
- `participant-projected-history-equivalence` does not establish
  `policy-noninterference`, `epistemic-indistinguishability`, or
  `alternating-strategic-equivalence`;
- finite leakage cases or equal sampled projections do not establish
  `policy-noninterference`;
- `statistical-equivalence` does not establish any behavioral equivalence;
- `profile-satisfaction` does not establish `empirical-adequacy`.

## Required Formal Dimensions

Every relation entry MUST state all of the following, even when a dimension is
outside scope:

1. left and right carrier types and initial-state treatment;
2. labels, transition relation, observable actions, hidden actions, and
   stuttering treatment;
3. observation-projection applicability and revision;
4. direction and quantification over states, traces, schedulers, strategies,
   environments, and observations;
5. treatment of nondeterminism, concurrency, probability, time, and partial
   order;
6. the preserved property and the proof obligation;
7. evidence that may support the relation and explicit nonclaims;
8. definition, implementation, test, and proof assurance states; and
9. revision-pinned primary-source references.

Missing dimensions are not defaults. They are an incomplete claim.

## Claim Binding

A consumer claim is a `BehavioralClaimBindingModel`. It MUST carry:

```text
(taxonomy_id, taxonomy_revision, relation_id,
 subject, left_carrier_ref?, right_carrier_ref?,
 observation_projection_ref?, observation_projection_revision?,
 quantifier_scope, evidence_scope, evidence_boundary,
 assurance_status, evidence_refs[], limitations[], explicit_non_claims[])
```

The relation meaning remains in the catalog; the binding identifies the actual
subject and evidence. Projection coordinates are mandatory for a relation whose
catalog entry has `projection_required: true`. Universal scopes
`all-admitted-inputs`, `all-traces`, and `all-strategies` require model-check or
proof evidence. A finite or statistical record cannot carry one of those
universal scopes.

Assurance axes are independent:

| Axis | Question |
| --- | --- |
| definition | Is the relation defined precisely? |
| implementation | Does ACES implement a checker or realization? |
| test | What executable cases exercise it? |
| proof | Is a universal obligation proved, model-checked, deliberately unproved, or future? |

“Defined” is not “implemented”, “implemented” is not “tested”, and “tested” is
not “proved”. The report truth value or study result remains separate from the
assurance status of the mechanism producing it.

## Claim Surfaces

### SDL transformations

Parse, normalize, expand, instantiate, and canonicalize stages currently carry
`structural-validity`, `semantic-validity`, and
`canonical-artifact-identity` evidence. Their evidence boundary consists of
typed phase functions, invariants, finite round-trip/canonicalization tests, and
property tests. They do not establish `data-refinement`, simulation,
`trace-equivalence`, or bisimulation.

### Backend realization

Envelope admission establishes `realization-envelope-membership`. The intended
universal runtime obligation is projection-bound `trace-inclusion`, but it is
deliberately unproved in revision `rev2`. Current conformance reports establish
only `bounded-probe-success` for their named fixture and target-probe cases.
Provisioning success, snapshots, witnesses, and negative probes do not establish
reverse inclusion, equivalence, simulation, or bisimulation.

### Backend comparison

A backend comparison MAY report bounded invariant equality,
`canonical-artifact-identity`, `bounded-probe-success`, or a declared empirical
relation. It MUST name the compared population, metrics, case set, environment,
and uncertainty method. Shared results, digests, or finite traces are not a
universal same-behavior result.

### Participant-visible behavior

A comparison of two participant histories uses
`participant-projected-history-equivalence` only when both histories use the
same named participant and projection-policy revision. Its evidence boundary is
the compared histories, redaction policy, order policy, simultaneity policy,
and run context. A single projected history is a record, not an equivalence
comparison.

### Participant information-flow policy

The SEM-230 claim surface uses `policy-noninterference` only when participant,
episode scope, audience, policy-revision sequence, low-equivalence relation,
dynamic purge, permitted declassification schedule, scheduler/environment
classes, order model, and observation projection are fixed. The baseline is
termination- and progress-insensitive, untimed, and set-based under
nondeterminism. Partial-order claims compare the declared visible order
relation, not one linearization. Probability measures are outside the baseline.

The executable SEM-230 cases are bounded falsification evidence. They do not
establish the universal hyperproperty, runtime enforcement, backend
realization, projected trace equivalence, simulation, refinement, bisimulation,
or epistemic indistinguishability.

### Multi-agent interaction

Current joint-action, simultaneous-move, chance, and mean-field contracts
provide structural and finite evidence only. A future strategic claim MUST use
`alternating-strategic-equivalence` and identify agents, coalitions, action
availability, opponent quantification, information sets, schedulers, objectives,
and preserved abilities. A probabilistic claim MUST use
`probabilistic-bisimulation` and supply the probability kernel and equivalence
classes. Neither relation is implemented or proved in revision `rev2`.

### Independent adequacy studies

Study and benchmark contracts bind their conclusions to
`empirical-adequacy`, `statistical-similarity`, or
`statistical-equivalence` as appropriate. The evidence boundary includes the
preregistered population, tasks, conditions, metrics or coding scheme,
uncertainty procedure, equivalence margin when applicable, falsification
criteria, missing-data handling, and limitations. Results from issue #729 will
therefore be bounded empirical evidence, not universal behavioral proof.

## Worked Counterexamples

### A passing probe is not bisimulation

Let the left system have transitions `l0 -a-> l1` and `l0 -b-> l2`. Let the
right system have only `r0 -a-> r1`. The named probe trace `[a]` passes on both
systems, so `bounded-probe-success` may hold for that case. The unmatched `b`
branch means `strong-bisimulation` does not hold. The evidence boundary is the
single `[a]` probe; it does not quantify over the untested branch.

### Hidden actions separate strong from weak matching

Let the abstract system perform `send` directly. Let the backend perform
`tau` and then `send`, where `tau` is governed as hidden. Strong matching fails
because the abstract initial state has no `tau` step. The visible trace can
still match after hidden-action closure, which is evidence relevant to
`weak-bisimulation`. A weak relation would still require the bidirectional
state-relation obligation; matching one visible trace does not prove it.

The executable versions of both examples are embedded in the revisioned
catalog and checked by `implementations/python/tests/test_behavioral_relations.py`.

## Assurance Boundary For Revision 2

Implemented and tested now:

- structural and semantic validity;
- capability declarations and profile satisfaction;
- bounded conformance probes;
- canonical artifact identity;
- realization-envelope membership and subsumption; and
- participant projection machinery and bounded projected-history comparisons;
  and
- the SEM-230 relation definition, catalog/claim-policy validation, and bounded
  test-local counterexamples.

Defined but deliberately unproved or only partially implemented:

- universal `trace-inclusion` for backend realization;
- `trace-equivalence`, forward/backward simulation, and data refinement;
- strong and weak bisimulation; and
- universal `policy-noninterference`, production policy enforcement, and
  backend realization of the SEM-230 relation.

Defined for future governed work and inappropriate to claim from current
artifacts:

- epistemic indistinguishability without a world/information model;
- alternating strategic equivalence without a game structure;
- probabilistic bisimulation without a probability kernel;
- timed or partial-order equivalence without the corresponding semantic model;
- statistical equivalence without a predeclared margin and test; and
- empirical adequacy without a preregistered population, criteria, and evidence.

## Primary Sources

The catalog records the complete title, authors, publication year and venue,
edition/version, and immutable DOI or ISBN for each source. Revision `rev2`
uses, among others:

- Milner, *A Calculus of Communicating Systems* (1980),
  DOI `10.1007/3-540-10235-3`;
- Park, “Concurrency and Automata on Infinite Sequences” (1981),
  DOI `10.1007/BFb0017309`;
- van Glabbeek, “The Linear Time–Branching Time Spectrum” (1990),
  DOI `10.1007/BFb0039066`;
- Abadi and Lamport, “The Existence of Refinement Mappings” (1991),
  DOI `10.1016/0304-3975(91)90224-P`;
- Lynch and Vaandrager, “Forward and Backward Simulations” (1995),
  DOI `10.1006/inco.1995.1134`;
- Fagin, Halpern, Moses, and Vardi, *Reasoning About Knowledge* (1995),
  ISBN `9780262061629`;
- Alur, Henzinger, Kupferman, and Vardi, “Alternating Refinement Relations”
  (1998), DOI `10.1007/BFb0055622`;
- Alur, Henzinger, and Kupferman, “Alternating-Time Temporal Logic” (2002),
  DOI `10.1145/585265.585270`;
- Larsen and Skou, “Bisimulation Through Probabilistic Testing” (1991),
  DOI `10.1016/0890-5401(91)90030-6`; and
- Wellek, *Testing Statistical Hypotheses of Equivalence and Noninferiority*,
  second edition (2010), ISBN `9781439808184`;
- Goguen and Meseguer, “Security Policies and Security Models” (1982), DOI
  `10.1109/SP.1982.10014`; and
- Sabelfeld and Sands, “Declassification: Dimensions and Principles” (2009),
  DOI `10.3233/JCS-2009-0352`.

Bibliographic prose here is an aid. The machine-readable catalog is the
revision-pinned identity surface.
