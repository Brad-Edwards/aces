# ADR-085: Participant Information-Flow And Control

## Status

accepted

ADR-095 amends this decision for participant decision-surface v2: policy
resolution is relative to an exact state cut, noninterference quantifies over
adaptive low-participant strategies, and every cross-episode information-flow
claim declares participant-memory scope. Historical scalar-order contracts
retain their published meaning.

## Date

2026-07-15

## Classification

Classification: FM3

Required artifacts: revisioned formal semantics, a closed policy and relation
vocabulary, labelled transition and projection models, clause-to-contract-to-
test mapping, negative leakage and declassification cases, bounded formal
evidence where claimed, backend capability/conformance evidence, and explicit
nonclaims.

Waivers: issue #794 is design and program work only. It does not add SDL,
schemas, runtime or backend behavior, a policy evaluator, conformance code, or
proof. Universal noninterference, trace inclusion, equivalence, simulation,
refinement, epistemic, timed, probabilistic, partial-order, and bisimulation
claims remain deliberately unproved or future.

## Context

ACES already has strong adjacent authorities:

- ADR-022 separates world truth, participant-visible state, participant local
  history, and archival evidence; it also defines action, observation,
  visibility, interaction, and attribution semantics.
- ADR-054 defines the observable participant lifecycle, portable envelopes,
  information guarantees, markings, redaction, ordering, shared state,
  concurrency, and capability disclosure.
- ADR-060 proposes neutral backend-facing participant carriers and feature
  support declarations.
- ADR-083 proposes a participant-local decision surface and realized-exposure
  discipline.
- ADR-081 and the revisioned behavioral-relation catalog separate structural
  validity, bounded probes, trace relations, simulations, refinement,
  bisimulation, epistemic relations, and empirical claims.

Those authorities do not compose into one portable policy boundary today.
ACES has action admission, visibility transitions, observation projection,
retrieval shapes, lifecycle histories, mixed-control placeholders, orchestration
injects, backend manifests, and conformance reports, but no single governed
decision says why a participant-directed crossing was permitted, transformed,
withheld, disclosed, or weakened. No current authority defines an ACES
noninterference obligation or makes it executable. API-408 retrieval views are
not participant authorization, DSL-111 injects have no participant delivery
semantics, and finite projected-history or conformance cases are not
bisimulation or universal information-flow proof.

Issue #794 assessed this gap. The detailed evidence, requirement disposition,
and implementation graph are in
[`docs/research/participant-io-control/`](../../research/participant-io-control/index.md).

## Decision

### 1. Adopt one semantic policy boundary over existing carriers

ACES SHALL adopt one coherent participant information-flow and control
boundary. "One boundary" means one set of policy coordinates, decisions,
ordering rules, and evidence obligations. It does not mean one transport, one
gateway process, one API endpoint, or one generic message schema.

The boundary composes existing action, observation, lifecycle, context,
intervention, inject, history, evidence, provenance, audit, and backend
capability carriers by stable reference. It SHALL NOT introduce a second world
state, participant view, behavior history, lifecycle, visibility taxonomy,
relation registry, persistence store, or audit channel.

### 2. Evaluate every crossing against an explicit coordinate tuple

A governed crossing is evaluated at least over:

```text
C = (participant, episode, direction, interaction_kind,
     source, actor, controller, authority_basis,
     action_or_projection_ref, observation_and_order_point,
     time_and_order_model, policy_identity_and_revision,
     markings, authorization, declassification, redaction_or_transformation,
     disposition, backend_posture, evidence, provenance, loss_and_limitations)
```

The tuple is a semantic relation and evidence contract, not a payload bag.
Payloads remain typed existing carriers or controlled references. Required
coordinates fail closed when absent or unresolved; optional coordinates carry
an explicit not-applicable, unknown, unsupported, or loss state when their
owning vocabulary permits it.

### 3. Keep crossing kinds distinct

Ingress kinds include action proposal, constrained-form submission,
candidate selection, approval, denial, external direction, intervention,
handoff, override, cancellation, and participant-directed inject delivery.
Egress kinds include observation, context/decision-surface projection,
masked or redacted output, disclosure, delivery receipt, action result, and
bounded status/history projection. Audit and archival evidence are separate
audiences, not participant egress.

These kinds share policy evaluation, order, disposition, provenance, and
evidence. They do not become one object. Approval is not execution;
presentation is not selection; selection is not admission; delivery is not
observation; and audit retention is not participant disclosure.

An environment-directed inject remains an orchestration event. A
participant-directed inject preserves its DSL-111 orchestration identity and
is governed as participant disclosure/observation at delivery. If it directs
an action or changes control, it additionally binds the appropriate mixed-
control transition.

### 4. Define labelled transitions and participant-relative hiding

SEM-230 SHALL define a labelled transition system over existing participant
and runtime state. Labels identify at least proposal, approval/denial,
direction, intervention, handoff, override/cancellation, admission/rejection,
attempt/result, disclosure/withholding, transformation, delivery, observation,
policy change, and evidence/audit actions.

Observable and hidden are relative to participant, audience, policy revision,
and observation/order point. They are not intrinsic booleans on a label. A
controller change may be hidden from one participant, visible to another, and
retained for an authorized audit surface. Any `tau` treatment SHALL name the
governed label set, closure, stuttering, divergence, and projection rules.

The time/order model SHALL state whether it is sequential, total, partial,
causal, simultaneous, timed, or backend-serialized. Timestamp equality is not
an ordering rule. Stale approvals, concurrent interventions, policy changes,
and future disclosures are resolved at explicit order points.

### 5. Keep information-flow operations independent

- Authorization binds an authenticated actor to a subject and authority scope.
- Admission decides whether one action or crossing may proceed now.
- Withholding records intentional non-release.
- Projection and masking select participant-visible content.
- Redaction transforms an authorized representation; it does not grant access.
- Declassification changes release authority under an explicit what, who,
  where, when, basis, and policy revision.
- Disclosure records an authorized release and its delivery evidence.
- Concealment and revocation affect future availability; they do not erase
  prior knowledge.
- Loss and weakening describe unavailable fidelity or guarantees; neither is a
  successful security transformation.

Caller authorization, participant authority, action admission, visibility,
marking authorization, and declassification compose deny-first. No successful
gate widens a failed one.

Transformations preserve source and result identity/digest, rule and revision,
actor/authority, reason, markings, provenance, evidence, and loss. Derived
content inherits source markings unless explicit declassification changes
them. A transformed action is a new proposal and receives fresh validation and
admission; it never inherits the source admission result.

### 6. Adopt a precise noninterference claim surface, not a proof claim

SEM-230 SHALL define `policy-noninterference` using named participant/policy
low-equivalence, purge or equivalent projection, permitted declassification
events, and policy revision sequence. For a fixed declared environment and
scheduler class, two low-equivalent initial states with the same admitted low
inputs and declassification schedule must produce the same set of participant-
projected low histories under the selected order model despite variations in
unauthorized high inputs. The definition SHALL state:

- state, trace, input, environment, scheduler, and observation quantifiers;
- termination, progress, divergence, and timing sensitivity;
- nondeterministic, probabilistic, concurrent, and partial-order treatment;
- policy-change and declassification semantics; and
- the model/bound within which any executable result applies.

The baseline design is termination- and progress-insensitive and does not
include wall-clock timing unless a stronger timed claim is selected. A claim
that needs those dimensions must adopt and evidence them explicitly rather
than inheriting them silently.

`policy-noninterference` is distinct from projected-history equality, trace
inclusion/equivalence, simulation, data refinement, strong/weak bisimulation,
and epistemic indistinguishability. Those relations may be proof techniques or
separate claims only when their own carriers, projections, quantifiers,
assumptions, and evidence exist. A finite negative-leakage suite, passing
backend probes, or equal sampled histories remains bounded evidence.

The relation SHALL be published in the existing
`aces-behavioral-relations` catalog at taxonomy revision `rev3`, with a
dedicated participant-information-flow claim surface. The closed catalog
contract remains `behavioral-relations/v1`; adding the relation changes the
taxonomy contents, not the contract shape. Current in-repository claim
producers SHALL advance together to `rev2`. Historical serialized `rev1`
resolution requires the governed migration path owned by issue #802, not a
consumer-local fallback.

This ADR adopts the claim surface and assurance progression. It makes no
universal noninterference or bisimulation claim.

### 7. Reuse the existing enforcement and evidence incumbents

Future implementation SHALL reuse:

- safe SDL loading, closed models, semantic validation, instantiation, and
  post-instantiation validation;
- action contracts, observation boundaries, view timelines, compiler
  addresses, and behavior histories;
- `ParticipantActionAdmissionRequest`, `ParticipantControlMixin`, participant
  retrieval projections, `RuntimeSnapshot`, and `ControlPlaneStore`;
- strict control-plane authentication, role/target binding, request bounds,
  idempotency/fingerprints, bounded diagnostics, redacted unexpected errors,
  and `AuditEvent`;
- API-405/407 participant capability and feature-support declarations;
- `BackendConformanceReport`, existing fixture/target runners, and
  `BehavioralClaimBindingModel`; and
- existing schema publication, concept authority, controlled vocabulary, and
  compatibility gates.

Unexpected errors must retain the redacted error envelope. Contracts,
diagnostics, audit, logs, and issue evidence carry safe identifiers, references,
digests, classifications, and bounded summaries, not credentials, hidden
payloads, policy bodies, raw rejected input, or environment dumps.

### 8. Make backend support portable and fail closed

API-407 SHALL declare governed participant-control feature identifiers,
support strength, limitations, disclosure references, and evidence criteria.
Support is not inferred from method presence. Missing required semantics reject
target selection or admission. A downgrade is permitted only when policy
authorizes it, provenance records it, affected audiences receive the required
disclosure, and stronger claims are removed.

Reference runtime implementation, backend declaration, backend realization,
bounded conformance, model checking, and proof remain independent statuses.
Schema or method presence establishes none of the later statuses.

### 9. Migrate in stages

Existing scenarios and histories retain their historical meaning. Absence of a
new policy record means legacy/unknown/unsupported according to the migration
profile; it never implies exact enforcement or noninterference. ADR-061 governs
published-contract compatibility. Adoption proceeds through semantic
authority, authored bindings, contracts, runtime enforcement, backend support,
assurance, migration, and documentation in that order.

## Consequences

Positive:

- Participant ingress, egress, intervention, and directed inject delivery gain
  one reviewable policy and evidence model without forcing one transport.
- Security, realization, and behavioral claims become falsifiable and cannot
  silently borrow strength from adjacent artifacts.
- Existing participant, runtime, observability, backend, and relation
  authorities remain canonical.

Negative:

- Implementations must carry policy revisions, order coordinates, evidence,
  provenance, markings, and explicit loss instead of convenient booleans or
  metadata bags.
- Legacy records require explicit compatibility interpretation.
- Stronger relation claims remain visibly unproved until their models and
  evidence exist.

Risks:

- A generic gateway DTO could duplicate existing carriers.
- Operator authorization could be confused with participant authority.
- Redaction could be misreported as authorization or declassification.
- Backend capability declarations could be mistaken for realization.
- Finite tests or model checks could be promoted beyond their bound.

The implementation graph and structural acceptance manifest mitigate these
risks and are published with issue #794.

## Non-Goals

- Selecting or building a participant I/O gateway, transport, UI, model
  provider, human-control service, or policy engine.
- Adding production SDL, schema, runtime, backend, or conformance behavior in
  issue #794.
- Replacing accepted participant, runtime, observability, orchestration,
  apparatus, backend-contract, or behavioral-relation authority.
- Claiming universal noninterference, trace inclusion, equivalence,
  simulation, refinement, epistemic equivalence, or bisimulation.

## References

- Issue #794
- [Current-state assessment](../../research/participant-io-control/current-state-assessment.md)
- [Detailed adoption design](../../research/participant-io-control/adoption-design.md)
- [Requirement disposition](../../research/participant-io-control/requirement-disposition.md)
- [Implementation program](../../research/participant-io-control/adoption-program.md)
- [ADR-022](adr-022-participant-behavior-and-interaction-semantics.md)
- [ADR-054](adr-054-participant-runtime-observable-lifecycle.md)
- [ADR-060](adr-060-participant-backend-facing-contract-surface.md)
- [ADR-081](adr-081-behavioral-relation-taxonomy-and-claim-discipline.md)
- [ADR-083](adr-083-participant-tool-decision-surface-and-exposure-semantics.md)

## Amendments

| Date | Commit/PR | Summary |
|------|-----------|---------|
| 2026-07-17 | #831 | Recorded ADR-085 acceptance with the SEM-230 formal authority, behavioral taxonomy revision, bounded evidence, and explicit literature-derived lineage and nonclaims. |
| 2026-07-26 | #909 | Adopted ADR-095 exact-cut policy, reactive-strategy, and explicit participant-memory semantics and advanced the behavioral taxonomy to revision 3. |
