# Participant Information-Flow And Control Adoption Design

This is the detailed design behind
[ADR-085](../../decisions/adrs/adr-085-participant-information-flow-and-control.md).
It is normative only through accepted ADRs, future requirement implementation,
and published contract/formal authorities. Issue #794 itself adds no runtime,
schema, backend, conformance, or proof implementation.

## Design objective

ACES will have one coherent participant-control policy and evidence boundary
across existing ingress and egress carriers. The boundary answers, for every
participant-directed crossing:

1. what semantic kind of crossing was requested or produced;
2. which participant, episode, actor, controller, authority, policy revision,
   and order point apply;
3. which action, observation, context, intervention, inject, or output carrier
   is referenced;
4. why it was admitted, rejected, withheld, transformed, disclosed, redacted,
   lost, or weakened;
5. what was attempted, delivered, observed, persisted, and audited; and
6. what backend capability, evidence, assurance, and explicit nonclaims support
   the record.

It does not route all traffic through one service or serialize all payloads as
one object.

## Formal objects

For participant `p`, episode `e`, and order point `o`, reuse:

- `W_o`: world/backend/evaluator truth needed to execute and assess;
- `V[p,e,o,r]`: the participant-visible projection under policy revision `r`;
- `H[p,e,o]`: the participant-local delivered action/observation/control
  history, including staleness, deception, uncertainty, and prior disclosure;
- `X_o`: archival evidence, provenance, and authorized audit state;
- `A[p,e,o]`: action contracts authored and available before eligibility;
- `D[p,e,o]`: the ADR-083 decision-surface projection; and
- `K[p,e,o]`: the information state ACES is entitled to claim from recorded
  history and reconstruction evidence.

The policy state is:

```text
Q[p,e,o] = (
  policy_id, revision, effective_order,
  subject_binding, controller_state, authority_rules,
  ingress_rules, egress_rules, marking_rules,
  declassification_rules, transformation_rules,
  backend_requirements, assurance_profile
)
```

Policy bodies are governed referenced artifacts. Runtime records carry safe
identity, revision/digest, decision, reason code, and evidence references, not
arbitrary executable expressions or policy text.

A crossing request is:

```text
R = (crossing_id, participant, episode, direction, interaction_kind,
     source_ref, payload_ref, actor, controller, authority_basis,
     action_or_projection_ref, submitted_order, policy_ref,
     markings, requested_transformation, provenance)
```

A decision and realization are separate:

```text
Decide(Q, R, state_at_o, backend_posture)
  -> (admit | reject | withhold | not_applicable | unknown | unsupported,
      reason, effective_order, transformation_or_projection,
      marking_and_declassification_result, required_evidence, limitations)

Realize(decision)
  -> (attempted | delivered | observed | failed | partial | timed_out |
      cancelled | unknown | unsupported,
      source_and_result_refs, realized_order, evidence, provenance, loss)
```

An admitted decision is not evidence of realization. A delivery record is not
evidence that the participant observed or retained the content. An audit record
is not participant disclosure.

## Crossing kinds and carriers

| Direction/audience | Interaction kind | Existing semantic carrier | Additional binding |
| --- | --- | --- | --- |
| ingress | open proposal | action contract + proposal refs | policy, actor/controller/authority, fresh admission |
| ingress | constrained form | action contract + governed mapping | defaults/normalization/loss and result identity |
| ingress | candidate selection | decision-surface entry | membership, eligibility, arguments, selection order |
| ingress | approval/denial | API-409 control record | target proposal, authority, validity/staleness |
| ingress | external direction | API-409 control record | action/control meaning and participant scope |
| ingress | intervention/handoff/override/cancel | ACT-617/RUN-310 transition | prior/new controller, conflict/order, evidence |
| ingress/egress | participant-directed inject | DSL-111 inject ref | addressee, disclosure/delivery policy and receipt |
| egress | observation | API-406 observation envelope | `V[p,e,o,r]`, markings, policy decision, loss |
| egress | context/decision surface | API-408/context refs | audience, order, exposure policy, realization evidence |
| egress | masked/redacted output | typed source/result refs | projection/transformation and inherited markings |
| egress | action result/status/history | lifecycle/history refs | audience projection and bounded evidence |
| audit/evidence | decision and realization | existing audit/evidence refs | authorized audience, policy revision, controlled source mapping |

Payloads are not copied into a universal crossing object. API-423 records the
relation between stable typed refs.

## Labelled transitions

SEM-230 owns a governed label alphabet with at least:

```text
propose, approve, deny, direct, intervene, handoff, override, cancel,
admit, reject, withhold, attempt, result,
transform, declassify, disclose, conceal, revoke,
deliver, observe, policy_change, weaken,
persist_evidence, audit
```

The transition relation changes only the state surfaces owned by the label.
For example:

- `approve` records an authority decision; it does not perform `attempt`;
- `declassify` changes a governed release basis; it does not prove `deliver`;
- `deliver` may extend participant history; it does not mutate world truth;
- `revoke` changes future authority/visibility; it does not rewrite `H`;
- `transform` creates a new result identity; it does not mutate its source; and
- `weaken` changes the supported guarantee and removes stronger claims.

The observable label function is `ObsLabel(p, audience, r, o, label)`. A label
can project to its full form, a redacted form, a stable visible occurrence, or
`tau`. Hiding is therefore participant-, audience-, policy-, and order-relative.
Global event ids remain controlled runtime/audit identities unless the policy
projects them. Repeated equal/redacted events retain distinct visible
occurrence ids.

## Ordering and policy change

Every decision and realization names its order basis and effective order. The
model supports:

- participant-local sequence;
- causal/happens-before partial order;
- declared simultaneity groups;
- scheduler or backend serialization;
- logical/simulation time; and
- wall-clock occurrence/record/ingest time as evidence, not implicit order.

Policy revisions are ordered state transitions. The revision effective at the
decision order governs the decision. A later policy cannot authorize an
earlier crossing. A decision with a validity interval cannot be applied after
expiry, supersession, controller handoff, subject reset, or conflicting state
change. Retries preserve idempotency identity but receive a new decision when
policy or relevant state changed.

Concurrent control decisions use declared conflict rules. At minimum, the
implementation distinguishes duplicate, compatible, stale, conflicting,
superseded, and unauthorized decisions. Last-writer-wins or timestamp order is
not a portable rule unless explicitly declared as a weakened realization.

## Deny-first decision composition

The boundary evaluates independent gates in this order without allowing one
success to override another failure:

1. validate closed request/carrier shape and bounded size;
2. authenticate the caller and bind the control-plane target;
3. bind the principal to the participant subject or authorized controller;
4. resolve participant authority, operating scope, and controller state;
5. resolve action/projection/inject/intervention semantics and policy revision;
6. evaluate SEM-211 eligibility/admission for actionable ingress;
7. evaluate audience, visibility, markings, and declassification for egress;
8. validate required backend feature support and permitted weakening;
9. apply governed transformation/projection and revalidate its result;
10. persist decision, realization expectation, evidence, provenance, and audit;
11. serialize only the governed result through the bounded error/output
    envelope.

Unknown or unresolved required facts reject or report unsupported according to
the owning contract; they never default to permit. Operator authorization
cannot impersonate the participant. Backend capability cannot grant semantic
authority. Visibility cannot imply action eligibility.

## Information-flow operations

The operations in
[`adoption-program.json`](adoption-program.json) are distinct contract states.
Important composition rules are:

- authorization precedes disclosure and admission;
- redaction follows authorization and does not widen it;
- declassification supplies a governed release basis, but participant/audience
  scope and observation policy still apply;
- masking/projection can reduce content but is not evidence that the source was
  authorized;
- withholding records non-delivery and does not erase the request;
- concealment/revocation affect future projections, not prior knowledge;
- loss/weakening must be visible to the claim consumer and cannot be labelled
  successful protection; and
- transformed actions are validated/admitted as new proposals.

Derived content inherits source classification, field markings, provenance,
and disclosure restrictions. Only an explicit declassification rule may
weaken markings; a generic transformation or summary does not.

## Information-flow and behavioral relations

### Policy noninterference

Let `~[p,r]` be low equivalence for participant `p` and policy revision sequence
`r`. Let `purge[p,r](alpha)` remove unauthorized high actions while retaining
the low inputs and explicitly permitted declassification events. Let
`Pi[p,r]` project a run to the participant-visible ordered history.

For a declared model `M`, environment class `E`, scheduler class `S`, and order
model `O`, the intended obligation is:

```text
s1 ~[p,r] s2
and purge[p,r](alpha1) = purge[p,r](alpha2)
and equal permitted declassification schedules
implies
{Pi[p,r](run(M, s1, alpha1, E, S, O))}
  =
{Pi[p,r](run(M, s2, alpha2, E, S, O))}
```

Braces denote sets when the selected model is nondeterministic. A probabilistic
claim compares measures rather than support sets and needs a separate governed
relation. A partial-order claim compares the declared visible order relation,
not an arbitrary linearization.

The baseline claim is termination- and progress-insensitive and excludes
wall-clock timing. A stronger termination-, progress-, timing-, probabilistic-,
or scheduler-sensitive claim must select those dimensions explicitly. Dynamic
policy and declassification are part of `r`; they are not exceptions described
only in prose.

No current artifact proves this obligation. SEM-230 defines the final governed
relation; ASR-535 owns negative cases and any bounded model-check or proof
progression.

### Relation selection

| Claim question | Relation | Current permitted assurance |
| --- | --- | --- |
| Did this named payload satisfy a schema? | structural validity | implemented/tested |
| Did these finite cases behave as expected? | bounded probe success | bounded |
| Are two recorded participant histories equal under one policy projection? | participant projected-history equivalence | bounded comparison |
| Does every implementation trace fit the abstract model? | trace inclusion | future proof; probes are not proof |
| Can every step be matched directionally? | forward/backward simulation | future |
| Does concrete state preserve abstract operations/observations? | data refinement | future |
| Are branching systems mutually step-matching without/with hidden closure? | strong/weak bisimulation | deliberately unproved |
| Are unauthorized high variations invisible under declared policy? | policy noninterference | deliberately unproved until model/evidence exists |
| Can the participant distinguish two worlds? | epistemic indistinguishability | future governed information model |

Bisimulation may support a noninterference proof for a specific labelled model;
it is not the definition of every information-flow claim. Projected-history
equality can falsify or support a bounded case; it does not quantify over
unseen states, inputs, branches, schedulers, or futures.

## Mixed control

Controller state includes controller identity, authority basis/scope, policy
revision, effective order, validity/lease, predecessor, and evidence. The model
records separate transitions for proposal, approval/denial, direction,
intervention, controller handoff, override, cancellation, admission, attempt,
result, observation, and handoff completion.

Approval targets one proposal/revision and expires or becomes stale under its
declared rules. A handoff changes controller state; it does not change
participant identity or rewrite prior provenance. An override/cancellation is
an ordered event and may race with admission or execution, producing an
explicit conflict/partial outcome rather than retroactive fiction.

Control-plane authentication, operator/auditor role, participant subject,
controller authority, action authority, and participant visibility remain
separate. Issue #251 owns authored semantics, #252 contracts, and #255 runtime.

## Participant-directed injects

A participant-directed inject has:

- its original DSL-111 inject id and schedule/order;
- participant addressee and episode/selection rule;
- typed content/payload ref and markings;
- observation/disclosure policy ref and revision;
- delivery deadline/order and failure behavior;
- optional external-direction/intervention ref;
- decision, receipt, observation/history, evidence, and provenance refs; and
- backend support and loss/weakening disclosure.

Scheduling does not imply delivery; delivery does not imply observation;
observation does not imply action. Environment injects keep no participant
addressee and influence participants only through ordinary world-to-view
projection.

## Portable contract design

API-423 adds closed relation records, not payload carriers. The minimum
contract family is expected to include:

- crossing request/decision record;
- transformation/projection record;
- disclosure/declassification record or typed subrecord;
- delivery/realization link; and
- policy/backend/evidence disclosure references.

Before publishing a new carrier, each issue tests reuse of ADR-054 base
envelopes, API-406 carriers, API-409 control records, API-408 context/history
views, ADR-083 decision surfaces, and existing evidence/provenance refs.

Contracts use `ContractModel(extra="forbid")`, governed vocabularies, semantic
reference validation, generated schemas, valid/invalid fixtures, publication-
manifest change accounting, and ADR-061 compatibility classification. Secrets,
policy bodies, raw hidden payloads, backend objects, and unbounded diagnostics
are excluded.

## Runtime design

RUN-319 extends, rather than bypasses:

- `ParticipantActionAdmissionRequest` and SEM-211 validation;
- `ParticipantControlMixin` and existing lifecycle transitions;
- observation boundaries, `V[p,e,o,r]`, API-408 projections, and exposure
  evidence;
- `RuntimeSnapshot`, participant behavior/observation/control histories, and
  `ControlPlaneStore`;
- control-plane strict defaults, identities/roles, target binding, request
  limits, idempotency, fingerprints, bounded diagnostics, and redacted 500s;
  and
- `AuditEvent` plus evidence/provenance carriers.

Decision and realization records are append-only. Retrying, restarting, or
replaying does not delete or mutate earlier decisions. Policy changes,
controller changes, redactions, and declassifications are history events. Raw
backend logs are evidence inputs, not policy decisions or participant output.

## Backend obligations

API-407 feature-support entries cover admission, projection, marking,
declassification, transformation, supervisory control, directed inject
delivery, ordering, persistence, evidence, and replay guarantees. Each entry
uses governed strength, limitations, disclosures, and evidence criteria.

Effective support is the meet across backend engine, adapter, participant
apparatus, policy evaluator, clock/order source, projection/redaction stage,
evidence store, and replay/conformance path. A strong component cannot hide a
weak one. Missing required support rejects target selection/admission. A
permitted weaker realization is policy-authorized, provenance-bound, disclosed,
and stripped of the stronger claim.

`BackendConformanceReport` records finite cases and explicit nonclaims. Passing
those cases is not universal runtime realization or behavioral proof.

## Assurance progression

1. **Defined:** revisioned policy, labels, relations, clauses, and nonclaims.
2. **Structurally implemented:** closed contracts and governed vocabularies.
3. **Semantically implemented:** validators and transition/projection logic.
4. **Tested:** positive, negative, property, concurrency, replay, and leakage
   cases.
5. **Bounded model checked:** finite model, bound, tool/version, assumptions,
   state count, result/counterexample, artifact digest, and reproduction command.
6. **Proved:** theorem, quantified model, assumptions, proof artifact/checker,
   and independent reproducibility.
7. **Runtime realized:** named backend/adapter/apparatus version and evidence.

No level promotes another automatically. ASR-535 integrates with the existing
relation catalog, behavioral claim bindings, conformance runners, and
scientific-completeness assessment.

## Compatibility and staged adoption

The dependency order is:

```text
semantic authority
  -> authored affordance/control/inject bindings
  -> portable contracts
  -> backend capability declarations
  -> supervisory and policy runtime enforcement
  -> conformance/formal assurance
  -> migration
  -> explanatory documentation
```

Legacy artifacts retain their historical semantics. A missing policy/crossing
record is legacy/unknown/unsupported according to the profile, not exact
enforcement. Migration preserves source/result identity, markings, provenance,
evidence, order, and disclosed loss. Breaking published-shape changes follow
ADR-061; accepted ADRs change only through ADR-059 amendment/supersession.

## Explicit non-goals and nonclaims

- No universal participant gateway, message DTO, policy bag, store, logger,
  exception family, authentication stack, or transport.
- No participant internal prompts, chain-of-thought, private memory, policy
  state, credentials, hidden answers, or backend objects in portable records.
- No claim that current API-408 retrieval is participant-safe egress.
- No claim that current bounded probes prove trace inclusion, noninterference,
  equivalence, refinement, or bisimulation.
- No claim that issue closure, requirement activation, ADR acceptance, schema
  publication, or tests alone establish runtime realization.
