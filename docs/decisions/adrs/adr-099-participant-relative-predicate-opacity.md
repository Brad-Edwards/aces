# ADR-099: Participant-Relative Predicate Opacity

## Status

accepted

## Date

2026-07-29

## Classification

Classification: FM3

Required artifacts: primary and adjacent literature review, explicit
possible-point and observer model, a revisioned opacity profile boundary,
machine-readable relation authority, shared claim-binding validation, worked
falsification models, independent assurance states, requirement disposition,
and a dependency-ordered implementation program.

Waivers: issue #810 does not add a model checker, theorem prover, supervisor
synthesizer, runtime policy engine, world-state store, participant-history
store, backend registry, or raw-secret evidence surface. It does not claim
universal opacity, proof, runtime enforcement, backend realization, or backend
conformance.

## Context

ADR-022 separates world truth, participant-relative view, and participant
local history. ADR-054 defines participant runtime occurrences and delivery.
ADR-083 defines participant decision surfaces. ADR-085 and SEM-230 define
revisioned participant information-flow policy, exact-cut decisions,
declassification, observer memory, adaptive low strategies, and
policy-noninterference claims. ADR-095 separates decision epochs, state cuts,
projection, disclosure, delivery, observation, selection, and admission.
ADR-081 defines the shared behavioral-relation catalog and prevents bounded
evidence from being promoted to stronger relations.

Those authorities can say whether complete low-observation support is
unchanged across policy-equivalent worlds. They do not express the narrower
epistemic question: for every possible point where a selected predicate is
true, does the observer still consider a point where it is false possible?

Issue #810 also exposes a security boundary not captured by payload filtering.
A participant may learn a predicate from a supervisor's approval, denial,
withholding, omission, timing, action availability, retry, or changed external
behavior. Conversely, one pair of equal projected histories is not proof of
opacity: another secret point may occupy a secret-only information cell.

The opacity literature contains distinct current-state, initial-state,
historical, K-step, infinite-step, active-intruder, probabilistic, timed,
supervisory, and concurrent variants. Selecting one by name without fixing the
secret, observer, memory, strategy, release, supervisor, scheduler, order, and
time coordinates would create an ambiguous claim.

## Decision

### 1. Add one participant-relative predicate-opacity relation

The shared behavioral-relation taxonomy revision advances to `rev5` and adds
the unary epistemic relation `participant-predicate-opacity`.

For a revisioned profile `P`, let `Omega_P` be the closed possible-point
domain, `S_P` the selected predicate, and:

```text
I_P(x) = { y in Omega_P |
           Init_P(y) = Init_P(x) and Obs_P(y) = Obs_P(x) }.
```

The relation holds exactly when:

```text
for every x in Omega_P:
  S_P(x) implies there exists y in I_P(x) such that not S_P(y).
```

This is the ordinary one-sided, possibilistic condition. Symmetric,
probabilistic, quantitative, timed, progress-sensitive, coalition, and other
stronger variants require explicit profiles or separate relations and evidence.

### 2. Require a revisioned relation-parameter profile

Every opacity claim binding carries paired
`relation_parameter_profile_ref` and
`relation_parameter_profile_revision` coordinates. The profile closes the
observer, secret, point/cut scope, observation and delivery projection,
memory, participant strategy domain, supervisor visibility, policy and
release behavior, nondeterminism, scheduler/environment, concurrency,
partial-order, time/progress, and probability dimensions.

The baseline is possibilistic-support, untimed-progress-insensitive, and
outside probabilistic scope. Concurrency and partial order require a declared
treatment. Accidental serialization order is never the opacity order model.

Active-participant profiles quantify every allowed adaptive strategy. Actual
and alternative points use the same strategy. Coalition profiles declare how
member observations and memories are fused.

### 3. Treat supervisor behavior as a possible observation

Profiles distinguish fully known supervision, a public contract with hidden
realization, online-learned supervision, and selectively disclosed decisions.
Any observable approval, denial, edit, handoff, deferral, omission, occurrence,
order, latency, delivery, retry, action availability, rejection detail, or
external effect belongs in the participant observation.

Hiding a policy body or revision event does not make its behavior
epistemically hidden. Randomized or nondeterministic supervision changes the
possible-point domain; it is not evidence of opacity.

### 4. Preserve release and memory semantics

Authorized declassification may change the protected predicate, the observer
information cell, or both at one exact cut. After release, the new profile and
policy determine whether opacity remains required. Revocation and concealment
govern future availability but do not erase information retained by a
remembering observer.

Raw secrets, possible worlds, memory contents, policy bodies, supervisor
internals, and unsafe counterexamples cannot enter portable artifacts, logs,
command-line arguments, or error text. Evidence uses typed references, digests,
safe case labels, and redacted witness structure.

### 5. Keep adjacent relations distinct

Under exactly matching carriers, observation relations, strategies, memory,
release, scheduler/environment, time, and order assumptions, SEM-230
policy-noninterference implies opacity for every eligible predicate. Opacity of
one predicate does not imply policy noninterference.

Participant-projected-history equivalence may witness one alternative but
does not discharge the universal opacity condition. Epistemic
indistinguishability defines information-cell membership; opacity constrains
the secret labels in the cell. Trace equivalence and bisimulation imply
opacity only through an independently justified secret- and
observation-preserving theorem. No such theorem is claimed here.

### 6. Represent assurance axes independently

The shared relation assurance record separately represents:

- definition;
- checker implementation;
- bounded tests;
- model checking;
- mathematical proof;
- runtime enforcement;
- backend declaration;
- backend realization; and
- bounded backend conformance.

Each claim binding names one `assurance_axis`. A definition is not a proof;
bounded tests are not model checking; a runtime gate is not a backend-native
realization; a declaration is not conformance.

Positive bindings use axis-native status and evidence pairs:
`definition/defined/structural`, `checker/implemented`,
`bounded-test/tested/finite`, `model-check/model-checked/model-check`,
`proof/proved/proof`, `runtime-enforcement/enforced`,
`backend-declaration/declared/structural`,
`backend-realization/realized`, and
`backend-conformance/conformant`. Checker, runtime-enforcement, and
backend-realization evidence may be structural or finite; backend conformance
may be finite or statistical. A future axis, and a deliberately unproved proof
axis, carries structural evidence only.

The legacy `implementation_status` aggregate is consistent with the explicit
checker, runtime-enforcement, and backend-realization axes. A legacy
`proof_status` of `model-checked` is consistent with the explicit model-check
axis. Positive backend conformance requires at least partial backend
realization. Contract validation rejects every contradictory combination.

This revision records the relation as defined and bounded-tested, with no
checker, model check, proof, runtime enforcement, backend declaration,
realization, or backend conformance.

### 7. Allocate implementation without parallel authority

`SEM-231` owns the opacity relation and remains `DRAFT` while issue #810
establishes its formal design. Existing `SEM-230`, `ASR-535`, `RUN-319`, and
`API-407` continue to govern their existing noninterference, assurance,
reference-runtime, and backend scopes. This ADR contributes no satisfaction
evidence for those scopes.

The downstream program is dependency ordered:

- #961 — closed profiles and bounded falsification;
- #962 — finite-state model checking after #961;
- #963 — mathematical proof after #961 and #962;
- #964 — reference-runtime enforcement after #961; and
- #965 — backend realization and bounded conformance after #961, #962, and
  #964.

## Alternatives Considered

Treat opacity as a synonym for SEM-230 policy noninterference. Rejected:
noninterference is a stronger symmetric support-set hyperproperty, while
selected-predicate opacity is one-sided and existential within each secret
information cell.

Accept one equal projected-history pair as opacity. Rejected: it can witness
one secret point while another secret point has no nonsecret alternative.

Model only participant payloads. Rejected: supervisor decisions, omissions,
timing, delivery, action availability, and changed behavior can disclose the
predicate.

Create separate relations for every DES opacity name. Rejected: current,
initial, K-step, historical, active, and supervisory variants share the same
kernel and should be selected by a closed profile. Probability changes the
mathematical relation and remains separate.

Add an opacity-specific runtime engine, store, or backend registry. Rejected:
future realization composes the incumbent SEM-230/RUN-319/API-407 authorities.

Report every assurance result in one status field. Rejected: definition,
testing, model checking, proof, enforcement, declaration, realization, and
conformance are not interchangeable.

## Consequences

RAES gains an exact vocabulary for claims that a chosen predicate remains
unknown to a named participant under declared assumptions. Claims become
longer because the observer and threat-model coordinates are mandatory; this
is intentional.

The shared claim-binding model and every schema embedding it evolve together.
Existing relations remain compatible because the profile and assurance-axis
coordinates are optional except when a relation declares them mandatory.

The current delivery is architecture and bounded falsification evidence only.
The child issues must produce their own evidence before any model-check,
proof, runtime, backend, or conformance state can advance.

## References

- [ADR-022](adr-022-participant-behavior-and-interaction-semantics.md)
- [ADR-054](adr-054-participant-runtime-observable-lifecycle.md)
- [ADR-081](adr-081-behavioral-relation-taxonomy-and-claim-discipline.md)
- [ADR-083](adr-083-participant-tool-decision-surface-and-exposure-semantics.md)
- [ADR-085](adr-085-participant-information-flow-and-control.md)
- [ADR-095](adr-095-participant-decision-epoch-state-cut-and-delivery-semantics.md)
- [Participant-relative opacity formal authority](../../../specs/formal/participant-semantics/participant-predicate-opacity.md)
- [Research and design criteria](../../research/participant-opacity/prior-art-and-design-criteria.md)
- [Implementation program](../../research/participant-opacity/implementation-program.md)
