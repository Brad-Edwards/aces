# ADR-081: Behavioral-Relation Taxonomy And Claim Discipline

## Status

accepted

## Date

2026-07-13

## Classification

Classification: FM2

Required artifacts: an explicit invariant list, a revisioned formal
specification, a closed machine-readable catalog and published JSON Schema,
typed claim bindings, counterexample and property-based tests, consumer
integration, a semantic policy gate, and an auditable delivery assessment.

Waivers: universal refinement, simulation, equivalence, bisimulation,
epistemic, strategic, probabilistic, timed, and partial-order proofs are outside
this change. Their catalog assurance states remain deliberately unproved or
future. No theorem prover, model checker, game solver, probability kernel, or
new runtime engine is introduced.

## Context

ACES previously used validation, conformance, refinement, equivalence, and
behavior-history language across different artifact boundaries without one
revisioned relation authority. Schema acceptance, bounded fixture success,
digest equality, a terminal participant record, and a study result could
therefore be read as stronger statements than their evidence supported.

This was not only a vocabulary problem. Each formal relation depends on
carriers, transition labels, hidden-action treatment, observation projection,
quantifiers, nondeterminism, concurrency, probability, time, partial order,
and a preservation obligation. Each empirical relation depends on a bounded
population, metric, uncertainty procedure, and falsification criteria. A flat
word list cannot preserve those distinctions.

## Decision

1. The ACES-native concept family `behavioral-relations` owns relation and
   claim-binding discipline. It classifies claims about other artifacts; it
   does not reclassify the scenarios, actions, observations, apparatuses,
   participants, runs, studies, or evidence to which those claims refer.
2. `contracts/concept-authority/behavioral-relations-v1.json` is the single
   machine-readable catalog for taxonomy `aces-behavioral-relations`, revision
   `rev1`. `specs/formal/behavioral-relations/README.md` is its normative
   reader-facing formalization. Relation meaning must not be duplicated in
   consumer-local registries.
3. Every relation definition states carrier types, initial-state treatment,
   transition signature, observation projection, direction, quantification,
   nondeterminism, concurrency, probability, time, partial-order treatment,
   preservation and proof obligations, bounded evidence, nonclaims, assurance
   state, and revision-pinned primary sources.
4. Relation identity, report truth, and assurance are independent. Definition,
   implementation, test, and proof statuses cannot be promoted into one another.
5. Claim-bearing consumers use `BehavioralClaimBindingModel`. A binding names
   taxonomy revision, relation, subject, carriers, projection when required,
   quantifier scope, evidence scope and boundary, assurance status, evidence,
   limitations, and explicit nonclaims. Universal quantifiers require
   model-check or proof evidence.
6. Backend conformance reports bind to `bounded-probe-success` and enumerate
   their finite cases. The intended backend-realization obligation is projected
   `trace-inclusion`, but revision `rev1` does not claim its proof. Fixture,
   target-probe, snapshot, and negative-boundary success do not establish a
   reverse direction or any equivalence.
7. Participant comparisons use
   `participant-projected-history-equivalence` only when both histories share a
   named participant and observation-policy revision. A single terminal
   projected history is reported as a bounded record, not as an equivalence.
8. Study and benchmark contracts carry revisioned empirical claim bindings.
   Independent studies under issue #729 can report only the population,
   measures, uncertainty, criteria, and limitations they actually support.
9. Scientific completeness REV1 binds each profile's intended claim to the
   catalog and enumerates non-claimed relations. Profile satisfaction remains
   distinct from empirical adequacy and behavioral proof.
10. `tools/check_behavioral_relation_claims.py` validates structured bindings
    and scans live claim surfaces for high-confidence positive relation
    assertions. It permits formal definitions, explicit weaker nonclaims, and
    relation-bound claims with evidence boundaries; it is not a keyword ban.

## Invariants

- Catalog keys and embedded relation ids are identical and unique.
- Every bibliography and claim-surface reference resolves inside the catalog.
- A projection-required relation has both projection identity and revision in
  every consumer binding.
- A finite or statistical evidence scope cannot carry a universal quantifier.
- Claimed and explicitly non-claimed relation ids cannot overlap on one
  scientific completeness profile.
- Claim-bearing studies and benchmarks carry at least one resolved behavioral
  or empirical claim binding.
- Every conformance report states its finite case boundary and explicit
  equivalence/bisimulation nonclaims.
- Strong and weak hidden-action semantics remain distinct in executable
  counterexamples.
- Catalog growth preserves concept-authority, schema-publication, package-corpus,
  and SDL-lineage parity.

## Consequences

### Positive

- Reviewers can tell structural validity, bounded conformance, intended
  universal obligations, behavioral equivalence, and empirical adequacy apart.
- Participant, multi-agent, and study conclusions expose the assumptions that
  make their relation meaningful.
- Future formal work can strengthen an assurance axis without changing relation
  identity or inventing another claim vocabulary.
- High-confidence overclaims fail deterministically in repository policy.

### Negative

- Claim-bearing artifacts become more verbose because relation identity and
  evidence boundaries are explicit.
- Adding a relation or strengthening assurance requires coordinated catalog,
  schema, documentation, test, and consumer updates.
- Revision `rev1` deliberately makes several desired universal relations visible
  as unproved rather than presenting existing probes as their substitute.

### Limits

This decision establishes a taxonomy, binding contract, and enforcement seam.
It does not prove backend trace inclusion, any simulation or refinement,
trace equivalence, strong or weak bisimulation, participant knowledge,
coalitional strategic ability, probabilistic behavior, timed behavior,
partial-order behavior, statistical equivalence, or empirical adequacy. Those
claims require their own governed models and evidence.
