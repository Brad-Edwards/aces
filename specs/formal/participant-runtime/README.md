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
- unit tests;
- typed runtime contract coverage;
- property-based or differential tests where they improve coverage;
- abstract state-machine model.

This document supplies the invariant list and abstract state-machine model for
the design issue. Typed contracts and tests belong to the spawned
implementation issues.

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

## Abstract State Machine

Let:

- `P` be the set of participant addresses.
- `E_p` be the ordered episodes for participant `p`.
- `B_p,e` be behavior-history events for participant `p` in episode `e`.
- `S` be shared operational state records.
- `V_p,e,t` be the participant-visible projection for participant `p` in
  episode `e` at runtime order point `t`.
- `J_i` be a joint action set or coordination interval.
- `R_i` be the realized ordering relation for `J_i`.

### State Sets

Participant episode state is inherited from ADR-013:

```text
EpisodeState = Initializing | Running | Terminated
```

Observable action lifecycle state is:

```text
ActionState =
  IntentObserved
  SelectionRecorded
  ExecutionAttempted
  ObservationEmitted
  StateUpdateCommitted
  Rejected
  Withheld
  Unsupported
  Unknown
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

### Transitions

`ObserveIntent`
: Records an intent/proposal/trigger when the runtime can observe it.
  Participants that do not expose intent may enter the lifecycle at
  `SelectionRecorded`, `ExecutionAttempted`, or `Unknown`.

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
values such as `unknown`, `externally_selected`, `not_applicable`, or
`opaque`, not by inventing evidence.

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
changelog fragments unless a future explicit evidence contract defines a safe
redacted representation.

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
- opaque participant phases are recorded honestly as unknown or not exposed
  rather than fabricated.

Future implementation artifacts:

- versioned participant runtime state/history envelopes;
- schema publication through `aces_contracts`;
- validation that history references known participant, episode, action,
  observation, and shared-state addresses;
- tests proving reset/restart do not rewrite history;
- fixtures for opaque participants that expose attempts and observations
  without internal planning traces.

## RUN-306 - Participant Decision And Execution Lifecycle

`RUN-306` requires a portable lifecycle for action proposal, selection,
execution, observation, and state update.

Design commitments:

- lifecycle phases are observable runtime event points;
- proposal and selection may be opaque, external, unknown, or not applicable;
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
- tests for revision, digest, and visibility-projection rules.

## RUN-308 - Concurrent Participant Execution

`RUN-308` requires concurrent participant execution and interaction over shared
scenario state.

Design commitments:

- concurrency is modeled through joint action sets, ordering, revisions, and
  conflict policy;
- coordination, contention, interference, and shared-state change remain
  explicit interaction classes;
- concurrent state updates record read/write revisions and realized ordering;
- participant-local observations may differ even when they refer to the same
  shared event;
- backends that serialize, reject, drop, or weaken concurrency guarantees must
  disclose that realization.

Future implementation artifacts:

- joint action / shared-state conflict validation;
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
- Redesigning archival study provenance, benchmark asset lifecycle, or full
  observation apparatus beyond the fields needed to preserve runtime history.
