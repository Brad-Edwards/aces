# Participant-Relative Predicate Opacity

Classification: FM3, epistemic secrecy semantics.

Requirement: `SEM-231`.

Decision: [ADR-099](../../../docs/decisions/adrs/adr-099-participant-relative-predicate-opacity.md).

Machine-readable relation authority:
`contracts/concept-authority/behavioral-relations-v1.json`,
`participant-predicate-opacity`, introduced in taxonomy revision `rev5` and
carried by current revision `rev6`.

## Scope

This specification defines when a selected predicate remains opaque to a
participant or declared coalition. It composes the incumbent participant
world, view, local-history, policy, decision-surface, exact-cut, release, and
memory authorities. It does not add a second policy engine, supervisor,
participant-history store, world-state store, or backend registry.

The baseline is:

- one-sided predicate opacity;
- possibilistic support, not probability;
- untimed and progress-insensitive;
- parameterized by an explicit concurrency and partial-order treatment; and
- relative to one revisioned relation-parameter profile.

Symmetric, probabilistic, timed, progress-sensitive, current-state,
initial-state, K-step, infinite-step, coalition, and active-participant
variants are profiles of this kernel. They are not silently implied by the
baseline.

## Possible Points And Profiles

A possible point is

```text
x = (M, r, c, p, l, m, q, u, e, o)
```

where:

- `M` is the revisioned semantic model;
- `r` is a run admitted by `M`;
- `c` is the exact state cut or declared frontier;
- `p` is the observer participant or coalition;
- `l` is the participant-local state and projected history at `c`;
- `m` is the declared memory state;
- `q` is the policy and declassification state at `c`;
- `u` is the supervisor/controller realization and public contract;
- `e` is the environment and scheduler choice; and
- `o` is the order, time, and delivery interpretation.

The possible-point domain `Omega_P` is closed by a revisioned
relation-parameter profile `P`. A claim MUST identify the profile and its
revision. The profile fixes at least:

| Coordinate | Required declaration |
| --- | --- |
| observer | one participant or a coalition with a fused-observation rule |
| secret | predicate `S_P : Omega_P -> {true,false}` |
| point scope | current, initial, historical/K-step, language, or another closed scope |
| cut | exact total-order prefix or declared partial/causal frontier |
| observation | named projection, revision, delivery basis, and omission treatment |
| memory | retained local state, reset authority, and cross-episode/retry behavior |
| participant power | passive or a closed set of allowed adaptive strategies |
| supervisor visibility | one of the declared postures below |
| policy and release | exact-cut policy, declassification, replay, and revision behavior |
| nondeterminism | possibilistic support in the baseline |
| scheduler/environment | fixed, quantified, or otherwise bounded choices |
| order/concurrency | total, one named linearization, all linearizations, partial order, or causal frontier |
| time/progress | untimed progress-insensitive in the baseline, or an explicit stronger profile |
| probability | outside the baseline; a probabilistic profile needs a separate relation |

The secret predicate labels possible points. Raw secret values, entire possible
worlds, participant memory, policy bodies, supervisor internals, and
counterexample payloads are not portable evidence. Portable artifacts carry
typed references, digests, safe labels, and redacted witness structure.

## Information Cells And Baseline Opacity

Let `Init_P(x)` be the initial public information fixed by `P`, and let
`Obs_P(x)` be the complete participant observation at the declared cut. The
observer information cell is

```text
I_P(x) = { y in Omega_P |
           Init_P(y) = Init_P(x) and Obs_P(y) = Obs_P(x) }.
```

The selected predicate is opaque under `P` exactly when:

```text
for every x in Omega_P:
  S_P(x) implies there exists y in I_P(x) such that not S_P(y).
```

Equivalently, no reachable observer information cell may be a non-empty subset
of the secret. This is the ordinary, one-sided condition: it prevents the
observer from knowing that `S_P` is true. It does not prevent learning that
`S_P` is false.

Symmetric opacity additionally requires the same condition for `not S_P`.
That stronger result MUST be named and evidenced independently.

Empty or unreachable cells do not establish opacity. A profile must say how
reachability is determined. One equal-observation pair supplies one possible
witness for one secret point; it does not discharge the universal
actual-secret-point quantifier.

## Active Participants

A passive profile fixes participant inputs independently of its observations.
An active profile declares a closed allowed-strategy set `Sigma_P`. A strategy
maps accumulated participant-local observations to admitted participant
actions.

Active opacity requires:

```text
for every sigma in Sigma_P:
  for every actual x reachable under sigma:
    S_P(x) implies there exists y reachable under the same sigma
      such that y in I_P(x) and not S_P(y).
```

Actual and witness points use the same strategy. Permitting a different
strategy in the witness would conceal information exposed by adaptive probes.
“All strategies” ranges only over the capability and policy bounds recorded in
`P`; it neither invents unavailable actions nor omits permitted probes.

## Supervisor Visibility

The supervisor is distinct from the observer. A profile MUST select one of
these postures:

1. **fully known** — actual and alternative points use the same public
   supervisor and policy realization;
2. **public contract, hidden realization** — alternatives may vary over
   hidden implementations satisfying the same public contract;
3. **online learned** — declared approvals, denials, edits, choices,
   handoffs, deferrals, or omissions enter the observer history under the
   profile's issuance rule; or
4. **selectively disclosed** — decision content, occurrence, timing, order, or
   delivery is projected under an explicit SEM-226/SEM-230 decision.

Filtering a payload does not remove the information in decision occurrence,
absence, ordering, latency, delivery, retry, surface refresh, action
availability, rejection detail, or changed external behavior. If the
participant can observe any such fact, `Obs_P` includes it. A hidden policy
revision can still be learned from its effects.

Nondeterministic or randomized supervision enlarges the possible-point
carrier. Randomness is not evidence of opacity. Probabilistic opacity or
quantitative leakage requires a separate probability-bearing relation,
threshold, measure, and assurance result.

## Observation, Order, And Memory

`Obs_P` is the complete delivered participant observation, not merely a
payload field. Its alphabet may include:

- participant-visible state and behavior-history projections;
- decision surfaces and action/affordance presence or absence;
- approvals, denials, withholding, edits, deferrals, and omission;
- action admission, attempts, outcomes, errors, and terminal observations;
- delivery occurrence, acknowledgement, retry, latency, timeout, and cadence;
- policy or release announcements visible at the exact cut;
- public supervisor identity or behavior; and
- any side channel expressly retained by the selected profile.

An assurance projection, raw audit stream, verifier evidence, or backend
inspect payload is not participant-visible by default. If another observer can
read it, that observer needs its own profile; a coalition profile must declare
how member observations and memories are fused.

The baseline abstracts elapsed time and progress but not observable order.
Concurrency and partial order are never resolved by an accidental list order.
A profile declares whether it compares one named linearization, every allowed
linearization, a partial-order projection, or a causal frontier. A result for
one linearization cannot be promoted to all schedules or a partial-order
claim.

Memory is perfect only when the profile says so. Reset, restart, retry,
handoff, concealment, or policy revocation does not erase prior knowledge
unless a trusted memory-reset authority and its semantics are in the model.

## Release And Policy Change

An authorized release may:

- change which predicate remains protected;
- change the observer projection and therefore split an information cell; or
- do both at the same exact cut.

The release occurrence and its effects are observations when the profile says
the participant can detect them. After release, opacity is evaluated under the
new policy and observation state. Conformance requires either that the
predicate is no longer protected or that each remaining secret point still has
a nonsecret alternative.

Revocation governs future release. It does not reconstruct a larger
information cell for a remembering observer. Replay and time-transitive flow
must be declared; they are not inferred from a policy version number.

## Relation Boundaries

`participant-predicate-opacity` is not an alias for another catalog relation:

| Adjacent relation | Exact boundary |
| --- | --- |
| `policy-noninterference` | Symmetrically compares complete support sets across selected low-equivalent variations and all declared strategies. Under matching profiles it implies opacity for every eligible predicate; opacity of one predicate does not imply noninterference. |
| `participant-projected-history-equivalence` | Equality of two projected histories may provide one opacity witness. It lacks the quantification over every actual secret point and its whole information cell. |
| `epistemic-indistinguishability` | Defines binary membership in an information cell. Opacity constrains the secret labels represented in that cell. |
| `trace-equivalence` | Relates two trace sets. It implies opacity only under an independently justified mapping that preserves the selected secret, observer, reachability, and profile coordinates. |
| `strong-bisimulation` | Matches labelled steps bidirectionally. Its carrier and proof obligations differ; neither relation implies the other without a secret- and observation-preserving theorem. |

Simulation, refinement, weak/branching bisimulation, anonymity, plausible
deniability, differential privacy, and quantitative information flow remain
separate claims.

## Worked Falsification Models

These finite models are definition examples, not model checking or proof.

### Equal Pair Does Not Prove Opacity

Let secret points be `a` and `c`, with nonsecret point `b`.
`Obs(a) = Obs(b) = 0`, while `Obs(c) = 1`. Point `a` has witness `b`, but the
information cell of `c` contains only secret points. Opacity fails at `c`.

### Supervisor Decision Leak

Two worlds deliver the same redacted participant payload. In the secret world
the supervisor denies an action; in the nonsecret world it approves it. If
decision outcome, occurrence, changed action availability, or resulting
behavior is observed, the cells split and opacity fails. Redacting the
decision body alone is insufficient.

### Opacity Without Noninterference

Every point satisfying selected predicate `S` has an observationally equal
`not S` alternative. A different unprotected low fact nevertheless varies
between two SEM-230 low-equivalent worlds and produces different projected
histories. `S` is opaque, while policy noninterference fails. This is the
required counterexample to the reverse implication.

### Declassification Changes Knowledge

Before release, a cell contains a secret and nonsecret point. An authorized
release exposes the predicate and splits the cell. Post-release opacity fails
unless the new policy stops protecting it or another nonsecret alternative
remains. Later concealment does not erase what a remembering participant
learned.

## Independent Assurance Lanes

Assurance states are independent:

| Lane | Evidence needed | This specification's status |
| --- | --- | --- |
| definition | accepted ADR, formal authority, catalog entry, sources, binding validation | defined |
| bounded testing | named finite profiles/cases, full bounds, digests, safe counterexamples | bounded |
| model checking | closed finite model, explored bounds, pinned tool/version, result or counterexample | not model checked |
| mathematical proof | theorem, assumptions, independently checkable proof, tool/digest when mechanized | deliberately unproved |
| runtime enforcement | complete supported-channel inventory, fail-closed mediation, durable decisions, security tests | not enforced |
| backend declaration | API-407 feature strength, required contracts, limitations, evidence refs | not declared |
| backend realization | native implementation, profile mapping, environment and provenance evidence | not realized |
| bounded backend conformance | adversarial cases, backend/profile/environment digests, sanitized reports | not tested |

A claim binding identifies exactly one `assurance_axis`. Finite execution
evidence cannot satisfy universal quantification. A definition does not
establish satisfaction, a declaration does not establish realization, and
realization does not establish conformance.

Each positive binding uses the axis-native status: `defined`, `implemented`,
`tested`, `model-checked`, `proved`, `enforced`, `declared`, `realized`, or
`conformant` respectively. Definition and declaration evidence is structural;
bounded tests are finite; model checking and proof use their same-named
evidence scopes; checker, runtime, and realization evidence may be structural
or finite; bounded backend conformance may be finite or statistical. A future
axis, and a deliberately unproved proof axis, has structural evidence only.

Legacy aggregates cannot contradict the explicit axes.
`implementation_status` summarizes checker, runtime-enforcement, and backend
realization; a model-checked legacy proof aggregate requires a positive
model-check axis; and positive backend conformance requires a realized or
partially realized backend. A future definition cannot carry a positive
assurance axis.

## Requirement And Delivery Mapping

- `SEM-230` continues to define `policy-noninterference`, exact-cut policy,
  adaptive low strategies, releases, memory, projection, scheduler, and order
  within its existing evidence boundary.
- `SEM-231` owns the opacity kernel, profiles, observer information cells,
  supervisor visibility, relation boundaries, and independent assurance state.
- `ASR-535` owns bounded falsification, model-check/proof evidence discipline,
  safe counterexamples, and backend conformance claims.
- `RUN-319` owns any future reference-runtime mediation and durable
  information-flow decisions.
- `API-407` owns backend feature strength, required contracts, limitations,
  realization, and evidence disclosure.

Issue #810 defines this architecture. Issues #961 through #965 separately own
bounded profiles and falsification, finite-state model checking, mathematical
proof, runtime enforcement, and backend realization/conformance.

## Explicit Nonclaims

This revision does not claim that RAES, the reference runtime, or any backend
satisfies or enforces participant predicate opacity. It provides no universal
opacity result, model-check result, mathematical proof, supervisor synthesis,
runtime mediation, backend declaration, backend realization, or backend
conformance result. It makes no probabilistic, quantitative-leakage, timed,
progress-sensitive, all-schedule, coalition, anonymity, noninterference,
trace-equivalence, simulation, refinement, or bisimulation claim.
