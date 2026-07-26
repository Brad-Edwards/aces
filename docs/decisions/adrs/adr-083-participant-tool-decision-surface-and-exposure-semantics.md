# ADR-083: Participant Tool, Decision-Surface, and Exposure Semantics

## Status

proposed

## Date

2026-07-14

## Classification

Classification: FM2
Required artifacts: ADR, formal specification, clause-to-contract-to-test matrix
Waivers: Executable SDL fields, compiler records, runtime projections, portable
contracts, schemas, fixtures, and conformance tests are owned by implementation
issues #294, #295, and #296.

## Context

Issue #119 is the joint design surface for three requirements that describe one
participant-local boundary:

- `SEM-219` requires explicit tool and affordance availability, visibility,
  invocation, and constraint semantics;
- `SEM-220` requires explicit semantics for open-ended, constrained-form, and
  candidate-set decision surfaces; and
- `SEM-226` requires explicit visible-versus-hidden, exposure, withholding,
  augmentation, and role-scoping semantics across those surfaces.

The repository already owns the adjacent authorities. ADR-020 owns authored
participant identity, authority, and operating scope. ADR-022 and the participant
formal specification own action contracts, the time-indexed participant view
relation `V_p,t`, observation boundaries, visibility transitions, and fail-closed
action applicability. ADR-041 owns participant-implementation capability and
run-selection provenance. ADR-054 owns runtime observation and behavior history.
ADR-060 owns neutral backend-facing carriers. ADR-067 composes these surfaces
into the participant behavior model.

Those authorities do not yet define a participant's current decision surface.
Existing fields can state that an implementation supports a decision-control
mode, expects a category of tool affordance, or selected an exposure policy.
They do not by themselves say which actions or affordances were available to
one participant at one order point, why they were visible, whether they were
eligible or invocable, what constraints applied, or what was actually exposed.

Without a joint decision, implementations could collapse tool labels into
action meaning, infer participant visibility from global state, treat backend
support as authority, use decision-control modes as surface contents, or infer
selection and outcome merely because an action appeared on a surface.

## Decision

Define participant tool, decision-surface, and exposure semantics as one
time-indexed projection over the existing participant semantic model. The
projection is semantic authority; a UI, prompt, API payload, backend object, or
participant implementation is only a realization of it.

### 1. Keep seven authority layers distinct

The design separates seven independently reviewable facts:

1. **Action meaning** is carried by governed participant action contracts.
2. **Authored availability** binds a participant or behavior specification to
   action contracts, observation boundaries, authority, and operating scope.
3. **Apparatus support** declares what a participant implementation and backend
   claim they can realize.
4. **Run selection** records the implementation, control mode, configuration,
   and exposure policy selected for a run.
5. **Current decision surface** projects visible context, action-contract
   candidates, affordances, eligibility state, constraints, and limitations for
   one participant and episode at one observation/order point.
6. **Realized exposure** records what the apparatus actually made available,
   with evidence, provenance, redaction, weakening, and loss disclosures.
7. **Decision and outcome** record the selected attempt and its result.

No field may implicitly carry more than one of these authorities. An apparatus
expectation is not an authored grant, a grant is not proof of delivery,
visibility is not eligibility, eligibility is not admission, and presentation
is not selection or successful execution.

### 2. Define a participant-local decision-surface projection

For participant `p`, episode `e`, and observation/order point `o`, define:

```text
D(p, e, o) = Project(
  behavior and action-contract refs,
  V(p, o) and the observation boundary,
  participant context and audience scope,
  implementation selection and control mode,
  exposure policy,
  SEM-211 eligibility state,
  realized affordance and support disclosures,
  evidence, provenance, marking, redaction, and limitations
)
```

`D(p,e,o)` contains stable references and disclosed relations, not duplicated
world truth, raw policies, hidden prompts, evaluator state, or backend-native
objects. It is scoped to one participant and episode and anchored to a specific
observation/order point. A cumulative or final surface cannot substitute for
the sequence of surfaces when exposure changed during the episode.

The portable projection has these conceptual parts:

- surface form and selection meaning;
- behavior, action-contract, observation-boundary, context-view,
  implementation-selection, and exposure-policy references;
- visible context references with source layer, transformation, marking,
  redaction, disclosure basis, evidence, provenance, and limitations;
- action entries with presentation or generation basis, visibility state,
  eligibility state, constraint references, and realization disclosures;
- affordance entries bound to action contracts and observation effects; and
- the order/event/evidence anchor used to derive the surface.

Implementation issue #295 must first test whether
`ParticipantContextViewModel` can carry the portable envelope and a stable
typed payload reference without weakening its SEM-214/216 invariants. A new
published decision-surface contract is permitted only if that reuse-first test
fails. It must still compose, rather than duplicate, the referenced contracts.

### 3. Preserve three distinct tool concepts

A **tool or artifact identity** names a thing. A **tool affordance** is a
participant-meaningful opportunity to perform an operation and is bound to an
action contract, participant authority/scope, constraint semantics, observation
effects, and evidence expectations. A **tool-affordance expectation** is an
apparatus capability declaration from
`participant-tool-affordance-expectations`.

A label such as `shell`, `browser`, `http-api`, an executable name, an ATT&CK
technique, or a UI control does not define an action contract. A flat `tools`
list cannot express availability, visibility, invocation authority, support,
constraints, side effects, or realized exposure and is therefore not a valid
portable semantic surface.

An authored interactive-access carrier is narrower than a tool affordance.
`agents.*.interactive_access` may state that one participant can be offered an
SSH or RDP carrier to a VM, but that declaration does not define a shell or
desktop action, make the carrier visible at a particular order point, prove
apparatus support, admit an invocation, or show that access was realized. The
carrier composes with action, availability, visibility, support, eligibility,
admission, and evidence predicates; it does not collapse them.

For each affordance, implementations must keep at least these predicates
separate:

- declared or authored for the participant;
- visible at the current order point;
- supported by the selected apparatus;
- eligible under the action contract and current state;
- invocable/admitted for a particular attempt; and
- realized and evidenced by the runtime.

An implementation may report `false`, `unknown`, `unsupported`, or a typed
failure at the owning predicate. It must not infer the remaining predicates.

### 4. Define the three decision-surface forms without changing action meaning

The semantic surface distinguishes these forms:

- **Open-ended generation** permits a participant implementation to propose an
  action and arguments. The proposal must resolve to a governed action contract,
  validate its argument shape, and pass SEM-211 eligibility/admission before it
  becomes an attempt. Generation authority is not execution authority.
- **Constrained form** maps a bounded form, grammar, or parameter editor to an
  action contract. Defaults, normalization, omitted values, validation, and any
  lossy mapping are part of selection meaning and must be disclosed.
- **Candidate-action set** presents a participant-local set of action-contract
  entries. Selection identifies one member and its arguments; non-members are
  invalid unless an explicit open-extension rule subsequently binds them to a
  governed contract and applies the same admission gates.

These categories describe surface content and selection meaning. They do not
replace the `participant-decision-surface-modes` vocabulary, which describes how
an implementation makes or relays decisions. Participant implementation kind
may change the realization but not the semantics of a form.

Candidate membership and action eligibility are different. A surface may
honestly show an ineligible action when it also carries the ineligibility state
and reason basis. A surface must not mark an action eligible from global or
future-visible state, or allow open-ended generation to bypass applicability.

### 5. Refine the existing visibility boundary

`SEM-226` composes the existing `V_p,t`, view-rule, view-transition,
observation-boundary, context-view, and audience-view semantics. It introduces
no second visible/hidden taxonomy.

An item may enter `D(p,e,o)` only when all applicable boundaries agree:

- the item is in `V_p,o` under the compiled observation boundary;
- the source layer and transformation are valid for the participant-facing
  view;
- audience/role scope includes `p` without relying on another participant's
  authority;
- markings, redaction, withholding, and loss disclosures are satisfied;
- the exposure policy authorizes the class of disclosure; and
- a visibility transition at or before `o` supplies the required event and
  evidence anchor when exposure changed over time.

Observations, control-context artifacts, truth assets, adjudication assets,
private references, scaffold guidance, and augmentation metadata remain
distinct source classes. Augmentation must name its source, transformation,
audience, visibility basis, evidence/provenance, and limitations. It cannot be
smuggled into a generic context or metadata map.

Future disclosure never justifies earlier exposure. Backend reachability,
operating scope, participant authority, control-plane authorization, and
information visibility are separate boundaries.

### 6. Preserve cross-stage meaning and evidence

Authoring declares semantic bindings; validation resolves references and fails
closed; compilation emits canonical addresses and projection inputs; planning
checks apparatus support and declared weakening; execution applies SEM-211
admission; observation records surface and visibility transitions; conformance
checks that the realized surface agrees with the authored, compiled, selected,
and evidenced facts.

Runtime evidence must preserve the participant, episode, order point, surface
derivation basis, selected implementation and exposure policy, action/affordance
references, decision, result, and any weakening. Raw logs are not semantic
evidence, and final outcome records do not reconstruct an earlier surface.

### 7. Bind the implementation issues to one matrix

The normative clause-to-contract-to-test matrix lives in
`specs/formal/participant-semantics/README.md`. Issues #294, #295, and #296 must
implement their rows through existing package ownership and must update the
matrix when a carrier or enforcement point changes. They may strengthen a row
but may not redefine the joint relations independently.

### 8. Ground the first surface in RUN-311 episode readiness

A participant episode's first decision surface is grounded by the existing
RUN-311 lifecycle rather than by a fabricated behavior event.
`episode_initialized`, `episode_reset`, and `episode_restarted` establish an
episode generation; the following `episode_running` event is the authoritative
readiness anchor. Only then may the runtime derive the initial context from
compiled `V_p,0` and project `D(p,e,0)`.

The public projection anchor is tagged as either episode readiness or a
behavior event. It references one event in one owning history and carries the
participant, episode, per-episode decision-surface order, anchor-local order,
stable event reference, evidence, and provenance. Episode lifecycle and
participant behavior remain separate histories. The tagged anchor makes the
surface `observation_order` the per-episode decision-surface coordinate, while
`anchor_order` remains the referenced lifecycle- or behavior-history
coordinate. RUN-311 `sequence_number` remains only the episode-generation
coordinate. Readiness derives decision-surface order zero. Each terminal
`observation_emitted` event advances the derived decision-surface order by one;
callers cannot choose that value independently.

The portable order is:

```text
episode_initialized | episode_reset | episode_restarted
  -> episode_running
  -> V_p,0 context
  -> D(p,e,0)
  -> proposal and selection
  -> admitted action_attempted
  -> state_transition_recorded
  -> terminal observation_emitted
  -> D(p,e,1)
```

Proposal and selection do not create participant behavior. Admission creates
the first behavior event. A reset or restart creates a new episode id and a new
order-zero surface with no behavior prefix from the new episode.

Anchor shape is not authority. Projection and admission resolve the anchor
against the current trusted runtime snapshot and complete participant-local
history. A standalone event, isolated fragment, final snapshot, prior-episode
surface, surface superseded by later behavior, or unanchored surface presented
to the runtime admission path fails closed. Initial projection continues to use
the compiled initial view relation; later projection continues to use the
existing behavior-anchor indexes and effective view-relation selector.

### 9. Classify the anchor integration as a breaking semantic change

The `participant-decision-surface-v1` schema remains in the `draft` stability
class. ADR-061 therefore permits an in-place v1 change, and adding
`projection_anchor` is structurally additive because the serialized property is
optional. That structural fact is not an end-to-end compatibility claim.

This amendment is a breaking semantic and runtime-admission change:

- surface `observation_order` is the derived per-episode decision-surface
  coordinate, not the referenced behavior-history index;
- an anchored projector requires the current trusted runtime snapshot; and
- runtime admission rejects an unanchored surface even though an older payload
  can still pass structural schema validation.

The Python distribution release carrying this amendment must therefore use the
repository's breaking-change release classification. The publication ledger
must describe the structural-versus-semantic distinction and must not claim
backward, forward, behavioral, or operational compatibility.

Consumers migrate by resolving a readiness or behavior anchor from the current
trusted snapshot, carrying it on the projected surface, passing that snapshot
to anchored projection, using `observation_order` for `D(p,e,o)`, and using
`anchor_order` only for the referenced lifecycle or behavior-history event.
Cached or independently constructed unanchored surfaces cannot be migrated by
copying an event ref; they must be reprojected from current authority.

## Alternatives Considered

### Add a flat participant `tools` list

Rejected. A list cannot distinguish semantic affordances from apparatus
expectations or express visibility, applicability, constraints, side effects,
realization, or evidence.

### Put decision-surface contents in the decision-control mode

Rejected. Modes describe how decisions are made or relayed. Overloading them
with actions, observations, prompts, or policy bodies would duplicate semantics
and break comparability.

### Treat backend support or participant implementation kind as semantics

Rejected. Both are apparatus facts. They may support or weaken a semantic
contract but cannot grant participant authority or change action meaning.

### Publish a new standalone visibility or persistence stack

Rejected. `V_p,t`, observation boundaries, context/audience views, runtime
snapshots, control-plane storage, behavior history, evidence, and provenance
already own those concerns.

### Require all presented actions to be eligible

Rejected. Some participant surfaces intentionally disclose unavailable choices.
The portable requirement is explicit eligibility state and fail-closed
admission, not suppression of every ineligible item.

## Consequences

### Positive

- Tool/affordance, decision-surface, and exposure implementations share one
  participant-local, time-indexed theory.
- Candidate presentation, eligibility, admission, selection, and outcome can be
  audited independently.
- Hidden truth and evaluator-only material remain behind existing view and
  audience boundaries.
- Different participant implementations and backends can realize the same
  semantic surface while disclosing support and fidelity differences.

### Negative / costs

- Implementations must carry stable references, order/event anchors, and
  evidence/provenance instead of convenient flat lists or metadata maps.
- Reviewers must distinguish several closely related predicates rather than
  accepting a single availability boolean.
- Cross-stage fixtures must cover both semantic and apparatus disagreement.

### Risks

- A future DTO may duplicate referenced action, observation, exposure, or
  implementation contracts instead of composing them.
- An implementation may compute candidate actions from hidden, global, stale,
  or future-visible state.
- A backend may treat support as permission, or a participant implementation may
  bypass SEM-211 during open-ended generation.
- A final surface snapshot may erase exposure changes and their evidence
  anchors.

## Non-Goals

- Defining a participant UI, prompt format, external-agent API, tool runner,
  shell/RPC protocol, policy engine, credential broker, or OS sandbox.
- Adding SDL fields, compiler/runtime records, contracts, schemas, fixtures,
  storage, or conformance code in this design issue.
- Replacing action contracts, SEM-210 visibility, SEM-211 applicability,
  SEM-214 context views, SEM-216 audience boundaries, or participant
  implementation provenance.
- Standardizing trajectories, demonstrations, budgets, quotas, reward, or full
  clock semantics.

## References

- `specs/formal/participant-semantics/README.md`
- [ADR-020](adr-020-declarative-participant-framing-boundaries.md)
- [ADR-022](adr-022-participant-behavior-and-interaction-semantics.md)
- [ADR-041](adr-041-participant-implementation-manifest-and-provenance.md)
- [ADR-054](adr-054-participant-runtime-observable-lifecycle.md)
- [ADR-060](adr-060-participant-backend-facing-contract-surface.md)
- [ADR-067](adr-067-participant-behavior-model.md)
- GitHub issues #119, #294, #295, and #296
