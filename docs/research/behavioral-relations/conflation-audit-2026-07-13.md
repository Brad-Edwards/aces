# Behavioral-Relation Conflation Audit

Date: 2026-07-13

Issue: #747

Taxonomy coordinate: `aces-behavioral-relations@rev1`

## Method

The audit inspected live claim-bearing prose, contracts, reports, examples, and
implementation strings under `docs/`, `specs/`, `examples/`,
`contracts/profiles/`, `contracts/fixtures/`, and
`implementations/python/packages/`. It searched for equivalence,
bisimulation, refinement, participant-history, conformance, identity, profile,
and empirical-adequacy language, then classified each occurrence by subject,
relation, quantifier, evidence boundary, and assurance state.

Generated schemas, tests containing seeded counterexamples, planning preflight
records, and timestamped `tools/real-daemon/evidence/` captures are not live
claim surfaces. The archived captures remain immutable evidence of what an old
run emitted; their legacy terminology is recorded below instead of rewritten.

## Results

| Surface | Previous risk | Revision-1 classification and boundary | Result |
| --- | --- | --- | --- |
| SDL schema and semantic validation | “valid” could be read as executable or conformant | `structural-validity` and `semantic-validity`; one artifact and named profile only | Bound in the taxonomy and scientific completeness REV1 |
| Normalize/expand/instantiate/canonicalize phases | Determinism and digest equality could be read as refinement or same behavior | `canonical-artifact-identity` plus phase invariants; no simulation, refinement, trace, or bisimulation proof | Existing nonclaims retained; catalog claim surface added |
| Realization envelopes | Admission could be read as successful realization | `realization-envelope-membership` or `realization-envelope-subsumption`; no execution result | Catalog separates set relations from runtime behavior |
| Backend fixture and target conformance | “conformance” did not expose finite quantification | `bounded-probe-success`; report enumerates cases, projection revision, limitations, and nonclaims | Implemented in `BackendConformanceReport` and CLI JSON |
| Backend realization obligation | “refines this design” asserted an unnamed universal relation | Intended `trace-inclusion` under a named participant projection; definition present, proof deliberately unproved | Normative participant-runtime prose corrected |
| Libvirt terminal participant record | The legacy `behavior-history-equivalent` label is not a current relation claim; it conflated one projected record with a comparison | Single `participant-projected-history` record with observation policy, redaction, ordering, simultaneity, and explicit nonclaimed relation ids | Artifact producer and example corrected |
| Cross-backend corpus coverage | Coverage note repeated the same legacy equivalence label | Bounded participant-projected record; explicitly no equivalence comparison | Producer corrected |
| Participant-history comparisons | Projection assumptions could remain implicit | `participant-projected-history-equivalence`; same participant and projection revision required | Defined and binding-enforced |
| Multi-agent records | Joint actions or shared results could be read as strategic equivalence | Current evidence is structural/finite; `alternating-strategic-equivalence` and `probabilistic-bisimulation` are future and unproved | Catalog makes the missing game/probability obligations explicit |
| Scientific completeness REV1 | The behavioral-relation concern existed but had no executable authority | Every profile binds its intended relation and enumerates nonclaimed relation ids | Concern moved from missing to implemented with executable evidence |
| Study and benchmark records | A study conclusion could omit relation and population boundary | Claim-bearing studies require revisioned claim bindings; empirical claims state population, projection/measurement plan, scope, evidence, and limitations | Implemented in `ExperimentStudyModel` |
| Independent studies under #729 | Planned results could be promoted to universal conformance or equivalence | `empirical-adequacy`, `statistical-similarity`, or `statistical-equivalence` only as preregistered and bounded | Contract seam is ready; results remain future evidence |
| Proposition/assertion result equality | Equal evaluator projections could be read as bisimulation | Explicit nonclaim already states the missing labelled-transition and matching obligations | No semantic change required |
| Historical real-daemon capture | Archived JSON contains `behavior-history-equivalent`, which is not a current relation claim | Historical, timestamped evidence; not a current authority or producer | Preserved unchanged and excluded from the live gate |

## Assurance Summary

Implemented and bounded-tested now:

- validity, declaration, profile, envelope, canonical-identity, and finite-probe
  relations;
- revisioned claim-binding validation;
- conformance-report disclosure;
- participant-projection metadata; and
- semantic policy enforcement.

Defined but deliberately unproved or future:

- universal backend `trace-inclusion`;
- trace equivalence, simulation, data refinement, and strong/weak bisimulation;
- epistemic and alternating strategic relations;
- probabilistic, timed, and partial-order relations; and
- empirical or statistical conclusions not yet supported by a completed,
  preregistered study.

## Gate Behavior

`tools/check_behavioral_relation_claims.py` is intentionally not a forbidden-word
list. Definitions and explicit nonclaims are permitted. A high-confidence
positive assertion is permitted when the surrounding claim identifies the
governed relation and an evidence boundary. Structured bindings are parsed and
validated against the canonical catalog, so unknown relation ids, revision
drift, missing projections, and finite-to-universal promotion fail directly.

The executable counterexamples demonstrate why this distinction matters: a
shared finite trace can pass while an unmatched branch refutes strong
bisimulation, and a hidden prefix can preserve one visible trace while strong
matching fails. These are evidence-boundary failures, not vocabulary failures.
