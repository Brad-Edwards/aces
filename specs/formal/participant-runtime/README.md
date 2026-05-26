# Participant Runtime Formal Design

This document is the issue #74 formal design artifact for:

- `RUN-305` - Participant Runtime State And History
- `RUN-306` - Participant Decision And Execution Lifecycle
- `RUN-307` - Shared Operational State Model
- `RUN-308` - Concurrent Participant Execution

It is a design artifact, not an implementation artifact. It establishes the
runtime model that later per-UID implementation issues must realize in
contracts, processor/runtime helpers, backend capability declarations,
conformance checks, and tests.

## Current Sufficiency Finding

The existing implementation is not sufficient for `RUN-305` through `RUN-308`.

What exists:

- ADR-013 and the participant episode contracts define episode identity,
  initialize, reset, restart, terminate, terminal reason, and append-only
  episode history.
- ADR-022 and `specs/formal/participant-semantics/` define participant action,
  observation, visibility, failure, temporal, attribution, interaction, and
  outcome semantics.
- `ParticipantBehaviorHistoryEvent` records action attempts, state
  transitions, observations, joint action set ids, realized order,
  interaction class, shared-state refs, temporal contexts, attribution edges,
  and outcome interpretations.
- `RuntimeSnapshot` carries participant episode state/history and behavior
  history as plain-data runtime surfaces.
- Backend manifests can declare participant runtime roles, behavior features,
  interaction features, and required evidence contracts.

What is missing:

- no joint participant runtime model that binds episode state, behavior
  history, shared operational state, and concurrent execution;
- no formal statement that the `RUN-306` lifecycle is observable boundary
  semantics rather than a participant-internal planner loop;
- no versioned shared operational state envelope with revision, digest,
  visibility projection, conflict policy, and provenance fields;
- no abstract state machine for action lifecycle and shared-state commits;
- no concurrency model that prevents implicit last-writer-wins or timestamp-only
  ordering claims;
- no per-UID design coverage for `RUN-305`, `RUN-306`, `RUN-307`, and
  `RUN-308`.

The repository is therefore at design coverage after this artifact, not
implementation coverage.

## Formal Methods Classification

This surface is `FM3` under ADR-007 and
`specs/formal/assurance-policy.yaml`: it defines stateful/control semantics,
lifecycle transitions, shared state, ordering, and concurrency.

Required artifacts for future implementation:

- invariant list;
- closed lifecycle, observation, concurrency, and capability vocabularies;
- unit tests;
- typed runtime contract coverage;
- property-based or differential tests where they improve coverage;
- abstract state-machine model.

This document supplies the invariant list, abstract state-machine model,
normalized vocabulary, conformance obligations, and concrete design examples for
the design issue. Typed contracts and tests belong to the spawned implementation
issues.

## Terms

`Participant`
: A scenario participant identified at runtime by stable
  `participant_address`. The concrete implementation may be a human, LLM
  agent, RL policy, script, playbook, simulator, external service, or hybrid
  apparatus.

`Episode`
: A bounded execution instance for one participant, identified by
  `episode_id` and `sequence_number`.

`Observable lifecycle envelope`
: The runtime boundary record for proposal or intent observation, selection or
  admission, execution attempt, observation emission, and state update.

`Lifecycle phase`
: One of the portable runtime points: intent/proposal, selection/admission,
  execution attempt, observation emission, or state update commit.

`Lifecycle status`
: A normalized claim about how a lifecycle phase is realized: observed,
  runtime-mediated, externally supplied, opaque, unknown, not applicable, or
  unsupported.

`Opaque participant`
: A participant implementation that does not expose one or more internal
  decision phases. Opaqueness is permitted, but the runtime must still record
  observable attempts, observations, and state updates.

`Shared operational state`
: Portable runtime state that participant actions can read, write, disclose,
  conceal, or use as evidence. It is distinct from world truth,
  participant-visible projection, participant belief/history, and archival
  evidence.

`Conflict policy`
: The explicit rule or disclosure used when concurrent attempts touch the same
  shared operational state.

`Information-state guarantee`
: A claim about whether the participant-visible observation can reconstruct, or
  is consistent with, the portable information state ACES claims for the
  participant.

`Capability guarantee`
: A backend's declared strength for lifecycle, observation, shared-state,
  ordering, conflict, provenance, or replay support.

## Abstract State Machine

Let:

- `P` be the set of participant addresses.
- `E_p` be the ordered episodes for participant `p`.
- `B_p,e` be behavior-history events for participant `p` in episode `e`.
- `S` be shared operational state records.
- `V_p,e,t` be the participant-visible projection for participant `p` in
  episode `e` at runtime order point `t`.
- `I_p,e,t` be the participant information state ACES claims for participant
  `p` in episode `e` at runtime order point `t`.
- `J_i` be a joint action set or coordination interval.
- `R_i` be the realized ordering relation for `J_i`.
- `G_b,k` be backend `b`'s declared guarantee level for contract concern `k`.

### State Sets

Participant episode state is inherited from ADR-013:

```text
EpisodeState = Initializing | Running | Terminated
```

Observable action lifecycle phase is:

```text
LifecyclePhase =
  IntentOrProposal
  SelectionOrAdmission
  ExecutionAttempt
  ObservationEmission
  StateUpdateCommit
```

Lifecycle phase realization status is:

```text
LifecycleStatus =
  Observed
  RuntimeMediated
  ExternallySupplied
  Opaque
  Unknown
  NotApplicable
  Unsupported
  Rejected
  Withheld
```

`Rejected` and `Withheld` are terminal dispositions for an attempted phase.
`Opaque`, `Unknown`, `NotApplicable`, and `Unsupported` are intentionally
distinct:

- `Opaque` means the participant may have an internal counterpart, but the
  apparatus boundary does not expose it.
- `Unknown` means the phase might be relevant, but the adapter cannot determine
  what happened.
- `NotApplicable` means the phase has no semantic counterpart for this action or
  participant.
- `Unsupported` means the backend or adapter cannot provide a portable
  guarantee.

Lifecycle envelopes carry:

```text
LifecycleEnvelope =
  event_id
  participant_address
  episode_id
  sequence_number
  phase
  status
  action_ref
  action_contract_ref
  actor_provenance
  temporal_context
  ordering_basis
  predecessor_event_refs
  observation_refs
  shared_state_read_refs
  shared_state_write_refs
  evidence_refs
  redaction_policy
  source_status_label
```

Observation information guarantees are:

```text
InformationGuarantee =
  ObservationOnly
  HistoryConsistent
  PerfectRecall
  LossyProjection
  Unknown
  Unsupported
```

Shared operational state records carry:

```text
SharedStateRecord =
  state_address
  state_scope
  state_kind
  revision
  digest
  ordering_basis
  conflict_policy
  visibility_projection_basis
  provenance
  evidence_refs
```

Shared-state accesses carry:

```text
SharedStateAccess =
  state_address
  access_kind     // read | write | read_write
  read_revision
  write_revision
  read_digest
  write_digest
  access_purpose
  evidence_refs
```

Joint action records carry:

```text
JointActionRecord =
  joint_action_set_id
  coordination_interval
  member_event_refs
  ordering_basis
  realized_order_relation
  read_set
  write_set
  conflict_class
  conflict_policy
  capability_guarantee
  evidence_refs
```

Ordering basis is normalized:

```text
OrderingBasis =
  TotalOrder
  PartialOrder
  Simultaneous
  SerializedBackendOrder
  SimulationTick
  ControlPlaneOrder
  WallClockOnly
  Unknown
  Unsupported
```

Capability guarantee strength is ordered:

```text
unsupported < disclosed_weak < bounded < exact
```

`not_applicable` is outside the order. A requirement that demands `bounded`
support is not satisfied by `disclosed_weak` support, even if the backend emits
a record.

### Transitions

`ObserveIntent`
: Records an intent/proposal/trigger when the runtime can observe it.
  Participants that do not expose intent may enter the lifecycle at
  `SelectionOrAdmission`, `ExecutionAttempt`, or a lifecycle envelope with
  status `Opaque`, `Unknown`, or `NotApplicable`.

`RecordSelection`
: Records admission, selection, rejection, withholding, external selection,
  unknown selection, or not-applicable selection.

`RecordExecutionAttempt`
: Records the action attempt, action contract, actor provenance, temporal
  context, precondition/failure basis, and optional joint action set.

`EmitObservation`
: Emits a participant-visible observation through an observation boundary.
  This transition may update `V_p,e,t` but does not expose hidden truth unless
  an explicit visibility rule permits it.

`CommitStateUpdate`
: Writes participant-local, shared operational, visibility, evidence-facing, or
  outcome-facing state records with revision, digest, ordering, provenance, and
  conflict semantics.

`ResolveConflict`
: Applies a declared conflict policy for a joint action set. The policy may
  serialize, reject, retry, withhold, mark unsupported, or record a disclosed
  weaker guarantee.

`CloseEpisode`
: Uses ADR-013 terminal semantics. It does not rewrite behavior history or
  shared-state history.

### Opaque Participant Rule

For any participant implementation `p`, ACES does not require a transition for
internal cognition, planning, prompting, policy evaluation, reward update, or
tool reasoning. Missing internal phases are represented by lifecycle status
values such as `Unknown`, `ExternallySupplied`, `NotApplicable`, or `Opaque`,
not by inventing evidence.

### Transition Preconditions And Postconditions

`ObserveIntent`
: Precondition: episode state is `Running`, or the event is explicitly attached
  to an external trigger admitted before episode start. Postcondition: an
  `IntentOrProposal` envelope exists with status in
  `{Observed, ExternallySupplied, Opaque, Unknown, NotApplicable}` and a
  provenance basis.

`RecordSelection`
: Precondition: an intent/proposal envelope exists, or selection is the first
  observable boundary for this participant. Postcondition: a
  `SelectionOrAdmission` envelope records admission, rejection, withholding,
  external selection, unknown selection, or not-applicable selection. Rejection
  and withholding terminate the attempted action unless the contract declares a
  retry path.

`RecordExecutionAttempt`
: Precondition: the action contract exists or the attempt is labeled as an
  external or unsupported action. Postcondition: an `ExecutionAttempt` envelope
  records action reference, actor provenance, temporal context, read set,
  possible write set, and failure/support basis. An attempt may be recorded even
  when proposal or selection is opaque.

`EmitObservation`
: Precondition: an execution attempt, state update, external event, or scenario
  rule produces participant-visible information. Postcondition:
  `V_p,e,t` is updated only through a declared visibility projection, and the
  envelope declares an `InformationGuarantee`.

`CommitStateUpdate`
: Precondition: the update has a stable state address and declared state kind.
  Postcondition: the written state has a new revision or digest, the read/write
  access record references prior revisions when known, and the event is linked
  to behavior history.

`ResolveConflict`
: Precondition: two or more attempts in the same joint action set have
  intersecting semantic read/write sets, exclusive resource claims, visibility
  effects, evidence streams, or declared interference. Postcondition: the joint
  action record contains conflict class, conflict policy, realized order or
  unsupported ordering, and per-participant observations.

`CloseEpisode`
: Precondition: ADR-013 terminal criteria are met. Postcondition: episode state
  is terminal, behavior history remains append-only, and shared-state history is
  not rewritten.

### Observation And Information-State Guarantees

The runtime may emit an observation without claiming a complete information
state. Stronger claims require stronger records:

- `ObservationOnly`: only the emitted observation is portable.
- `HistoryConsistent`: the participant's portable action-observation history is
  sufficient to reconstruct the information state ACES claims.
- `PerfectRecall`: the runtime preserves every prior action and observation
  needed for a perfect-recall information state.
- `LossyProjection`: the projection is sampled, aggregated, delayed, redacted,
  or otherwise incomplete; loss is recorded.
- `Unknown` or `Unsupported`: the adapter cannot determine or provide the
  information-state guarantee.

The participant-visible projection `V_p,e,t` must never be replaced by hidden
world truth, centralized-training state, scoring state, or backend debug state.
Those may be evidence or apparatus records, but they are not participant-visible
observations unless explicitly projected.

### Concurrency And Conflict Semantics

For attempts `a` and `b` in joint action set `J_i`, ACES records a conflict when
any of the following hold:

- `write_set(a)` intersects `read_set(b)` or `write_set(b)`;
- `write_set(b)` intersects `read_set(a)` or `write_set(a)`;
- the attempts claim the same exclusive resource, account, channel, tool,
  budget, route, or authority;
- one action contract declares that it can affect the other's preconditions,
  observations, effects, visibility, evidence stream, or outcome;
- the backend reports contention, dropped work, serialization, retry, rejection,
  throttling, or unsupported simultaneity.

Conflict policies are normalized:

```text
ConflictPolicy =
  Coordinate
  Serialize
  Reject
  Retry
  Withhold
  Merge
  DiscloseWeakGuarantee
  Unsupported
```

`Serialize` is portable only with realized order and read/write revisions.
`Merge` is portable only when the action contract declares commutativity or an
explicit merge rule. Last-writer-wins is not portable unless represented as a
`Serialize` policy with evidence.

### Capability Guarantee Lattice

Every backend capability claim is made per contract concern:

```text
CapabilityConcern =
  lifecycle_phase
  observation_information_state
  shared_state_revision
  ordering
  conflict_resolution
  provenance
  replay
```

Guarantee strength is:

```text
unsupported < disclosed_weak < bounded < exact
```

Meaning:

- `unsupported`: the backend cannot provide the concern.
- `disclosed_weak`: the backend can emit a record but loses at least one
  contract guarantee.
- `bounded`: the backend supports the concern within declared limits.
- `exact`: the backend supports the concern as stated by the ACES contract.

The effective guarantee for a runtime claim is the minimum guarantee across the
concerns required by that claim. A comparison, replay, attribution, or
concurrency claim cannot be stronger than its weakest required concern.

## Invariants

### I1 - Role-Neutral Runtime Boundary

The runtime lifecycle applies to humans, LLM agents, RL policies, scripts,
playbooks, simulators, and external services. Participant implementation type
is apparatus metadata, not a different runtime semantics.

### I2 - Observable, Not Internal, Lifecycle

`RUN-306` phases are runtime-observable or runtime-mediated boundary events.
They must not be interpreted as a requirement to expose participant internal
plans, chain-of-thought, prompt content, model activations, reward traces, or
workflow steps.

### I3 - Episode Identity Preservation

Every participant runtime record that belongs to an episode carries stable
`participant_address`, per-episode `episode_id`, and the relevant
`sequence_number`. Reset and restart create new episode instances; they do not
mutate prior histories.

### I4 - Episode Lifecycle Separation

Episode status, control actions, and terminal reasons remain separate from
action lifecycle phases, action outcomes, objective outcomes, evaluator
results, and workflow state.

### I5 - Plain-Data Contract Boundary

Portable participant runtime state and history are JSON-like, schema-shaped,
versioned contract records. Backend-native objects, logs, DB rows, cache keys,
process ids, raw tool output, and private participant memory are not portable
state unless projected into a governed contract.

### I6 - No Metadata State Model

`RuntimeSnapshot.metadata`, history `details`, and diagnostic details are not
the shared operational state model. They may carry auxiliary information only
when no portable claim depends on it.

### I7 - Shared-State Addressability

Every shared operational state record has a stable address and state kind.
Behavior events that read or write shared state reference those addresses,
rather than relying on prose or backend-local names.

### I8 - Revision And Digest Discipline

State updates that affect shared operational state carry a revision, digest, or
equivalent version marker. Consumers must not infer equality, conflict, or
ordering from timestamps alone.

### I9 - Explicit Ordering Basis

Every action attempt or state update that participates in a joint action set
declares an ordering basis: total order, partial order, serialized backend
order, simulation order, control-plane order, or unsupported/unknown ordering.

### I10 - Conflict Policy Disclosure

Concurrent attempts that touch the same shared operational state declare their
conflict class and policy. Implicit last-writer-wins is not a valid portable
semantics.

### I11 - Observation Projection Boundary

Observation emission may update participant-visible state, but it must not
collapse world truth, shared operational state, participant belief/history, and
archival evidence.

### I12 - Provenance Preservation

State and history records distinguish author-declared, processor-derived,
backend-realized, participant-observed, and externally supplied values when
that distinction affects interpretation.

### I13 - Secrets And Internal Traces Stay Out

Credentials, bearer tokens, hidden answer keys, prompts, private model traces,
raw backend exceptions, and sensitive state values must not appear in public
runtime envelopes, diagnostics, audit details, snapshots, fixtures, or
changelog fragments unless an explicit evidence contract defines a safe redacted
representation.

### I14 - Backend Capability Honesty

Backends claim participant runtime support through manifest capabilities and
published evidence contracts. A backend that cannot preserve a lifecycle,
shared-state, ordering, or conflict guarantee must reject or disclose the
weaker realization.

### I15 - Replay Compatibility

Behavior history, shared-state revisions, ordering, observations, and evidence
references must be sufficient to explain what the runtime claimed happened.
Replay may be approximate, but the lost or unsupported guarantees must be
visible.

### I16 - Closed Lifecycle Status Semantics

Lifecycle status values are closed at the portable contract layer. Source
labels may be preserved, but source labels do not define ACES semantics.
`Opaque`, `Unknown`, `NotApplicable`, and `Unsupported` must remain
distinguishable.

### I17 - Information-State Claim Strength

An observation may be portable without a portable information-state claim.
Whenever ACES claims history consistency or perfect recall, the
action-observation history must be sufficient for that claim.

### I18 - Semantic Conflict Detection

Conflict detection is based on semantic read/write sets, exclusive resource
claims, visibility effects, evidence streams, and action-contract interference.
It is not limited to object identity or physical storage collisions.

### I19 - Capability Guarantee Monotonicity

A runtime claim cannot be stronger than the weakest required backend guarantee
for lifecycle, observation, shared-state revision, ordering, conflict,
provenance, or replay. Downgrades are records, not diagnostics-only warnings.

### I20 - Concrete Envelope Compatibility

Every conforming implementation must be able to represent opaque LLM/RL
participants, externally supplied human actions, simultaneous joint actions, and
backend-serialized weak concurrency without changing the portable semantics.

## Canonical Design Examples

### Opaque LLM Agent Action

```yaml
lifecycle_envelope:
  event_id: evt-llm-17
  participant_address: participants.red.llm
  episode_id: ep-red-004
  sequence_number: 17
  phase: ExecutionAttempt
  status: Observed
  action_ref: actions.exfiltrate_file
  action_contract_ref: contracts.file_access.v1
  actor_provenance: participant_observed
  predecessor_event_refs:
    - evt-llm-16-selection
  evidence_refs:
    - evidence.tool-call-992
selection_envelope:
  event_id: evt-llm-16-selection
  phase: SelectionOrAdmission
  status: Opaque
  source_status_label: model_private_choice
```

The runtime records the observable action attempt. It does not require prompt
content, chain-of-thought, policy logits, tool reasoning, or private memory.

### RL Policy Step

```yaml
lifecycle_envelope:
  event_id: evt-rl-42
  participant_address: participants.blue.rl
  episode_id: ep-blue-002
  sequence_number: 42
  phase: ExecutionAttempt
  status: Observed
  action_ref: actions.isolate_host
  action_contract_ref: contracts.defense.isolate-host.v1
observation_envelope:
  event_id: evt-rl-43
  phase: ObservationEmission
  status: Observed
  information_guarantee: ObservationOnly
  visibility_projection_basis: blue.local.telemetry.v1
```

The policy update, reward update, and model state are apparatus internals unless
an explicit evidence contract exposes a redacted representation.

### Human-Supplied Action

```yaml
lifecycle_envelope:
  event_id: evt-human-09
  participant_address: participants.gold.operator
  episode_id: ep-gold-001
  sequence_number: 9
  phase: SelectionOrAdmission
  status: ExternallySupplied
  actor_provenance: human_operator
  evidence_refs:
    - evidence.operator-command-9
```

The human operator is represented through the same participant runtime boundary
as an automated agent; the source of selection is external, not opaque.

### Simultaneous Conflict Over Shared State

```yaml
joint_action_record:
  joint_action_set_id: joint-13
  coordination_interval: tick-88
  member_event_refs:
    - evt-red-88
    - evt-blue-88
  ordering_basis: Simultaneous
  read_set:
    - hosts.web01.service.http@rev7
  write_set:
    - hosts.web01.service.http@rev8
  conflict_class: Interference
  conflict_policy: Reject
  capability_guarantee: bounded
```

The conflict is portable because read/write revisions, conflict class, and
policy are explicit.

### Backend-Serialized Weak Concurrency

```yaml
joint_action_record:
  joint_action_set_id: joint-21
  coordination_interval: wallclock-window-21
  member_event_refs:
    - evt-a
    - evt-b
  ordering_basis: SerializedBackendOrder
  realized_order_relation:
    before:
      - [evt-a, evt-b]
  conflict_policy: DiscloseWeakGuarantee
  capability_guarantee: disclosed_weak
  evidence_refs:
    - evidence.backend-scheduler-log-21
```

This record can support review of what happened. It cannot support a claim that
the backend executed true simultaneity.

## RUN-305 - Participant Runtime State And History

`RUN-305` requires portable state and history for participants, including
actions, observations, state changes, and outcomes.

Design commitments:

- participant runtime history is append-only and keyed by participant and
  episode identity;
- behavior history links action attempts, observations, state updates,
  temporal context, attribution, and outcome interpretation;
- shared operational state is recorded through versioned state records, not
  metadata;
- history distinguishes participant-local state, shared state, visibility,
  evidence, and outcomes;
- information-state claim strength is explicit for each participant-visible
  observation;
- opaque participant phases are recorded honestly as unknown or not exposed
  rather than fabricated.

Future implementation artifacts:

- versioned participant runtime state/history envelopes;
- schema publication through `aces_contracts`;
- validation that history references known participant, episode, action,
  observation, and shared-state addresses;
- validation that hidden truth and centralized-training state are not exposed as
  participant-visible observations without an explicit projection rule;
- tests proving reset/restart do not rewrite history;
- fixtures for opaque participants that expose attempts and observations
  without internal planning traces.

## RUN-306 - Participant Decision And Execution Lifecycle

`RUN-306` requires a portable lifecycle for action proposal, selection,
execution, observation, and state update.

Design commitments:

- lifecycle phases are observable runtime event points;
- lifecycle statuses use the closed normalized vocabulary in this document;
- proposal and selection may be opaque, externally supplied, unknown, or not
  applicable;
- execution attempts remain tied to governed action contracts and actor
  provenance;
- observations are emitted through participant observation boundaries;
- state updates commit through participant-local and shared-state records;
- the lifecycle is separate from episode lifecycle, workflow state, evaluator
  state, and control-plane operation status.

Future implementation artifacts:

- lifecycle phase/status vocabulary;
- runtime event envelope linking lifecycle phase, action contract, participant,
  episode, temporal context, and state update;
- fixtures for `Opaque`, `Unknown`, `NotApplicable`, and `Unsupported` statuses
  that prove they are not collapsed;
- validation that hidden participant internals are not required or leaked;
- negative fixtures showing LLM/RL/human/script participants can satisfy the
  boundary without exposing internal planning loops.

## RUN-307 - Shared Operational State Model

`RUN-307` requires a portable shared operational state model for evolving
participant and environment state.

Design commitments:

- shared operational state is a typed runtime contract surface;
- records carry state address, kind, revision/digest, ordering basis,
  conflict policy, visibility projection, provenance, and evidence refs;
- read/write access records carry prior and written revisions when known;
- state updates are explicit behavior-history events;
- shared state remains separate from hidden world state, participant-visible
  projection, participant belief/history, and archival evidence;
- backend-native stores may realize the state internally but do not define the
  portable semantics.

Future implementation artifacts:

- shared state record/envelope model;
- compiler/runtime address convention for state records;
- validation of state refs from action contracts and behavior history;
- conformance checks rejecting metadata-only shared state;
- tests for revision, digest, read/write access, and visibility-projection
  rules.

## RUN-308 - Concurrent Participant Execution

`RUN-308` requires concurrent participant execution and interaction over shared
scenario state.

Design commitments:

- concurrency is modeled through joint action sets, ordering, revisions, and
  conflict policy;
- coordination, contention, interference, and shared-state change remain
  explicit interaction classes;
- conflicts are detected over semantic read/write sets, exclusive resource
  claims, visibility effects, evidence streams, and contract interference;
- concurrent state updates record read/write revisions and realized ordering;
- participant-local observations may differ even when they refer to the same
  shared event;
- backends that serialize, reject, drop, or weaken concurrency guarantees must
  disclose that realization.

Future implementation artifacts:

- joint action / shared-state conflict validation;
- capability guarantee validation across lifecycle, observation, shared-state,
  ordering, conflict, provenance, and replay concerns;
- property or differential tests for serialized versus conflicting attempts;
- conformance checks for missing order/revision/conflict metadata;
- backend capability evidence for supported concurrency guarantees.

## Non-Goals

- Defining new SDL participant syntax.
- Implementing participant runtime contracts or backends in this issue.
- Requiring participants to reveal chain-of-thought, prompts, policy internals,
  reward updates, private memory, or tool traces.
- Treating backend-native stores, logs, timestamps, or scheduler order as the
  portable runtime semantics.
- Treating reward, policy optimizer state, centralized-training state, or model
  internals as participant runtime semantics.
- Redesigning archival study provenance, benchmark asset lifecycle, or full
  observation apparatus beyond the fields needed to preserve runtime history.
