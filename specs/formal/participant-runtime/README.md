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

Enum blocks use formal names. Implementation schemas should publish a single
wire spelling and document the mapping; the intended wire spelling is lowercase
snake_case unless an existing ACES contract family requires a different style.

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
  visibility projection, conflict policy, provenance, and markings;
- no abstract state machine for action lifecycle, observation, operation, and
  shared-state commits;
- no concurrency model that prevents implicit last-writer-wins or timestamp-only
  ordering claims;
- no information-state semantics for noisy, lossy, stochastic, or redacted
  observations;
- no benchmark/runtime provenance surface sufficient for reproducibility claims;
- no per-UID design coverage for `RUN-305`, `RUN-306`, `RUN-307`, and
  `RUN-308`.

The repository is therefore at design coverage after this artifact, not
implementation coverage.

## Source Alignment And Design Constraints

This design is constrained by the primary sources listed in
`docs/explain/sdl/lineage.md`:

- Gymnasium and OpenAI Gym support an action/observation/episode boundary but
  do not require access to private policy internals. ACES follows that
  boundary, while adding multi-participant provenance and shared-state records.
- PettingZoo and OpenSpiel require per-agent observations, local histories,
  simultaneous or sequential interaction, and information-state discipline.
  ACES therefore separates hidden state, participant-visible observations,
  action-observation histories, centralized-training state, and review evidence.
- POMDP, Dec-POMDP, POSG, and Markov-game lineage means a participant's
  observation is not world truth. Strong information-state claims require a
  reconstructible observation history, not just a final state dump.
- CybORG, CyberBattleSim, CyGIL, CALDERA, OpenC2, CACAO, and ATT&CK show that
  cyber actions carry command, target, session, credential, knowledge,
  detection, foothold, and outcome semantics. ACES records those as portable
  references without adopting any one backend or playbook format as canonical.
- OCSF and STIX establish the event-schema precedent for identity, schema
  versioning, timestamps with distinct meanings, confidence, markings,
  source/raw mapping, and extension rules.
- Lamport clocks, HLA time management, Time Warp, DEVS, FMI, and related
  runtime literature require ACES to separate wall-clock timestamps, logical
  ordering, simulation time, causality, rollback, pacing, and synchronization.
- Cybench, AutoPenBench, CAIBench, AI Agents That Matter, and related agent
  benchmark critiques require run records, scaffold/tool exposure, seeds,
  repeated-run ids, resource/cost traces, baseline/evaluator disclosure, and
  holdout/canary exposure labels for auditable comparisons.

These sources do not make ACES a compatibility layer for any one project. They
define review constraints: the model must preserve the concepts needed to make
participant behavior, information boundaries, concurrency, and benchmark claims
auditable.

## Formal Methods Classification

This surface is `FM3` under ADR-007 and
`specs/formal/assurance-policy.yaml`: it defines stateful/control semantics,
lifecycle transitions, shared state, ordering, and concurrency.

Required artifacts for future implementation:

- invariant list;
- closed lifecycle, observation, operation, concurrency, marking, and
  capability vocabularies;
- unit tests;
- typed runtime contract coverage;
- property-based or differential tests where they improve coverage;
- abstract state-machine model;
- model-checkable or mechanically testable refinement target for the
  concurrency and information-state subsets.

This document supplies the invariant list, abstract state-machine model,
normalized vocabulary, conformance obligations, and concrete design examples for
the design issue. Typed contracts, tests, and executable models belong to the
spawned implementation issues.

## Terms

`Participant`
: A scenario participant identified at runtime by stable
  `participant_address`. The concrete implementation may be a human, LLM agent,
  RL policy, script, playbook, simulator, external service, or hybrid apparatus.

`Episode`
: A bounded execution instance for one participant, identified by `episode_id`.
  Each participant episode owns a monotonic behavior sequence.

`Observable lifecycle envelope`
: The runtime boundary record for proposal or intent observation, selection or
  admission, execution attempt, observation emission, and state update.

`Lifecycle phase`
: One of the portable runtime points: intent/proposal, selection/admission,
  execution attempt, observation emission, or state update commit.

`Phase realization`
: A normalized claim about how a lifecycle phase is realized: observed,
  runtime-mediated, externally supplied, opaque, unknown, not applicable, or
  unsupported.

`Admission disposition`
: A normalized claim about whether a selection/admission phase allowed the
  attempted action to proceed: admitted, rejected, withheld, unknown, or not
  applicable.

`Operation state`
: A normalized state for long-running or asynchronous execution: submitted,
  acknowledged, running, blocked, completed, partial, failed, timed out,
  cancelled, unknown, or unsupported.

`Opaque participant`
: A participant implementation that does not expose one or more internal
  decision phases. Opaqueness is permitted, but the runtime must still record
  observable attempts, observations, and state updates.

`Shared operational state`
: Portable runtime state that participant actions can read, write, disclose,
  conceal, or use as evidence. It is distinct from world truth,
  participant-visible projection, participant belief/history, and archival
  evidence.

`Action-observation history`
: The ordered participant-visible sequence of prior action attempts, emitted
  observations, and disclosed lifecycle facts for one participant episode.

`Information state`
: The participant information state ACES claims at an order point. It may be
  only the emitted observation, a history-consistent reconstruction, a
  perfect-recall history, a lossy projection, unknown, or unsupported.

`Conflict policy`
: The explicit rule or disclosure used when concurrent attempts touch the same
  shared operational state, resource, visibility surface, evidence stream, or
  action-contract interference relation.

`Capability guarantee`
: A backend's declared strength for a specific runtime concern. Capability is a
  vector over concerns, not one scalar level.

`Marking`
: A security, sensitivity, sharing, or redaction label attached to a record or
  field. Markings govern disclosure; they are not prose warnings.

`Refinement`
: A relation showing that concrete backend traces project to valid ACES traces
  while preserving required identity, order, visibility, provenance, and
  capability guarantees.

## Abstract State Machine

The participant runtime model is a transition system over append-only records.

### State Tuple

Let abstract runtime state be:

```text
RuntimeState =
  participants
  episodes
  behavior_history
  lifecycle_events
  operation_records
  observations
  action_observation_histories
  information_states
  shared_state
  joint_actions
  evidence_index
  run_context
  capability_declarations
  marking_policies
  logical_order
```

Where:

- `participants` is the set of participant addresses.
- `episodes[p]` is the ordered episode set for participant `p`.
- `behavior_history[p,e]` is the append-only behavior history for participant
  `p` in episode `e`.
- `lifecycle_events` is the append-only set of lifecycle envelopes.
- `operation_records` is the append-only set of long-running operation records.
- `observations[p,e]` is the emitted participant-visible observation stream.
- `action_observation_histories[p,e,t]` is the prefix of visible actions and
  observations available to participant `p` at order point `t`.
- `information_states[p,e,t]` is the information state ACES claims for
  participant `p` at order point `t`.
- `shared_state[address]` is the version chain for a shared operational state
  address.
- `joint_actions[id]` records coordination intervals and concurrent attempts.
- `evidence_index` maps safe evidence references to evidence contracts and
  redaction policies.
- `run_context` contains reproducibility and benchmark context.
- `capability_declarations[backend, concern]` is the backend guarantee vector.
- `marking_policies` contains field-level authorization and redaction rules.
- `logical_order` is the recorded total or partial order relation over events.

### Base Envelope

Every portable record that can support a runtime claim carries:

```text
BaseEnvelope =
  event_id
  schema_name
  schema_version
  event_type
  extension_policy
  participant_address
  episode_id
  sequence_number
  occurred_at
  recorded_at
  ingested_at
  clock_authority
  temporal_context
  ordering_basis
  logical_order_ref
  predecessor_event_refs
  actor_ref
  producer_ref
  source_system_ref
  source_record_ref
  source_raw_ref
  confidence
  provenance_refs
  evidence_refs
  markings
  granular_markings
  redaction_policy_ref
  authorization_scope
```

Rules:

- `event_id` is globally stable within the run.
- `schema_name` and `schema_version` identify the ACES contract projection, not
  the backend's native object.
- `participant_address`, `episode_id`, and `sequence_number` may be null only
  for run-scoped records, such as a joint action record, that carry
  per-participant linkage through member event references.
- `occurred_at`, `recorded_at`, and `ingested_at` must not be collapsed. If a
  backend cannot distinguish them, it must disclose that with `clock_authority`
  or capability weakening.
- `ordering_basis` and `logical_order_ref` carry ordering claims. Wall-clock
  timestamps alone do not establish causality.
- `source_raw_ref` points to controlled evidence; it does not inline raw
  sensitive data into the portable envelope.
- `markings` and `granular_markings` are enforceable field-level disclosure
  labels.

### State Sets

Participant episode state is inherited from ADR-013:

```text
EpisodeState =
  Initializing
  Running
  Terminated
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

Phase realization is:

```text
PhaseRealization =
  Observed
  RuntimeMediated
  ExternallySupplied
  Opaque
  Unknown
  NotApplicable
  Unsupported
```

Admission disposition is:

```text
AdmissionDisposition =
  Admitted
  Rejected
  Withheld
  Unknown
  NotApplicable
```

Operation state is:

```text
OperationState =
  Submitted
  Acknowledged
  Running
  Blocked
  Completed
  Partial
  Failed
  TimedOut
  Cancelled
  Unknown
  Unsupported
```

`Opaque`, `Unknown`, `NotApplicable`, and `Unsupported` are intentionally
distinct:

- `Opaque` means the participant may have an internal counterpart, but the
  apparatus boundary does not expose it.
- `Unknown` means the phase might be relevant, but the adapter cannot determine
  what happened.
- `NotApplicable` means the phase has no semantic counterpart for this action
  or participant.
- `Unsupported` means the backend or adapter cannot provide a portable
  guarantee.

`Rejected` and `Withheld` are admission dispositions, not phase realizations.
`Completed`, `Failed`, `TimedOut`, and `Cancelled` are operation states, not
episode terminal reasons.

Lifecycle envelopes carry:

```text
LifecycleEnvelope =
  BaseEnvelope
  phase
  phase_realization
  admission_disposition
  operation_ref
  action_ref
  action_contract_ref
  command_ref
  actor_provenance
  observation_refs
  shared_state_read_refs
  shared_state_write_refs
  emitted_state_update_refs
  joint_action_set_ref
  source_status_label
  mapping_loss
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

Observation envelopes carry:

```text
ObservationEnvelope =
  BaseEnvelope
  observation_ref
  phase_ref
  visibility_projection_ref
  information_guarantee
  action_observation_history_ref
  information_state_ref
  hidden_state_refs
  centralized_state_refs
  loss_descriptor
  stochastic_context
  noise_model_ref
  redacted_field_refs
```

Shared operational state records carry:

```text
SharedStateRecord =
  BaseEnvelope
  state_address
  state_scope
  state_kind
  revision
  digest
  predecessor_revision_refs
  ordering_basis
  logical_order_ref
  conflict_policy
  visibility_projection_basis
  provenance
  value_ref
  markings
  granular_markings
```

Shared-state accesses carry:

```text
SharedStateAccess =
  state_address
  access_kind
  read_revision
  write_revision
  read_digest
  write_digest
  snapshot_ref
  access_purpose
  atomic_group_ref
  evidence_refs
```

Joint action records carry:

```text
JointActionRecord =
  BaseEnvelope
  joint_action_set_id
  coordination_interval
  member_event_refs
  ordering_basis
  realized_order_relation
  clock_context
  snapshot_basis
  isolation_guarantee
  atomicity_scope
  read_set
  write_set
  exclusive_resource_claims
  conflict_class
  conflict_policy
  retry_policy_ref
  rollback_refs
  capability_guarantee_vector
  participant_observation_refs
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
  LogicalClock
  VectorClock
  WallClockOnly
  Unknown
  Unsupported
```

Isolation guarantee is normalized:

```text
IsolationGuarantee =
  Serializable
  Snapshot
  Causal
  ReadCommitted
  BestEffort
  Unknown
  Unsupported
```

Conflict policies are normalized:

```text
ConflictPolicy =
  Coordinate
  Serialize
  Reject
  Retry
  Withhold
  Merge
  Rollback
  DiscloseWeakGuarantee
  Unsupported
```

Capability concerns are:

```text
CapabilityConcern =
  lifecycle_phase
  admission_disposition
  operation_state
  observation_information_state
  shared_state_revision
  ordering
  isolation
  conflict_detection
  conflict_resolution
  provenance
  redaction
  replay
  benchmark_reproducibility
```

Guarantee strength per concern is:

```text
GuaranteeStrength =
  unsupported
  disclosed_weak
  bounded
  exact
```

`not_applicable` is outside the order and is represented by omitting the concern
from the required vector or by a concern-specific `NotApplicable` value where
that concern has one.

### Transition Relation

The abstract transition relation is:

```text
Apply(RuntimeState, RuntimeEvent) -> RuntimeState | Reject
```

A trace is valid when:

1. it starts from an initial state with declared participants, run context,
   capability declarations, and marking policies;
2. every event has a unique `event_id` and satisfies the `BaseEnvelope` rules;
3. every participant-scoped event references an existing participant and an
   existing or explicitly admitted episode; run-scoped records, such as joint
   action records, carry per-participant linkage through member event refs;
4. every event passes field-level marking and redaction policy checks before it
   enters any public runtime surface;
5. every transition preserves append-only history, monotonic participant
   sequence numbers, state revision discipline, and declared ordering;
6. every runtime claim is no stronger than the backend guarantee vector and the
   evidence actually recorded.

The state machine rejects an event when accepting it would require hidden truth
to appear as participant-visible observation, infer ordering from wall clock
alone, rewrite history, skip a required redaction, invent participant internals,
or claim a capability stronger than the declared backend support.

### Transitions

`ObserveIntent`
: Records an intent/proposal/trigger when the runtime can observe it.
  Participants that do not expose intent may enter the lifecycle at
  `SelectionOrAdmission`, `ExecutionAttempt`, or a lifecycle envelope with
  `Opaque`, `Unknown`, or `NotApplicable` phase realization.

`RecordAdmission`
: Records admission, rejection, withholding, external supply, unknown
  admission, or not-applicable admission. Rejection and withholding terminate
  the attempted action unless a later retry path is explicitly recorded.

`SubmitOperation`
: Creates an operation record for asynchronous or long-running execution.
  Synchronous attempts may skip this transition when the execution attempt and
  result are recorded atomically.

`RecordExecutionAttempt`
: Records the action attempt, action contract, command mapping, actor
  provenance, temporal context, precondition/failure basis, shared-state access
  plan, and optional joint action set.

`AdvanceOperation`
: Advances a long-running operation through submitted, acknowledged, running,
  blocked, partial, completed, failed, timed out, cancelled, unknown, or
  unsupported states. Each advancement is append-only and references the
  predecessor operation record.

`EmitObservation`
: Emits a participant-visible observation through an observation boundary. This
  transition may update the participant-visible projection, but it does not
  expose hidden truth unless an explicit visibility rule permits it.

`CommitStateUpdate`
: Writes participant-local, shared operational, visibility, evidence-facing, or
  outcome-facing state records with revision, digest, ordering, provenance,
  markings, and conflict semantics.

`ResolveConflict`
: Applies a declared conflict policy for a joint action set. The policy may
  coordinate, serialize, reject, retry, withhold, merge, roll back, mark
  unsupported, or record a disclosed weaker guarantee.

`CloseEpisode`
: Uses ADR-013 terminal semantics. It does not rewrite behavior history,
  operation history, observation history, or shared-state history.

### Transition Preconditions And Postconditions

  `ObserveIntent`
: Precondition: episode state is `Running`, or the event is explicitly attached
  to an external trigger admitted before episode start. Postcondition: an
  `IntentOrProposal` envelope exists with phase realization in
  `{Observed, ExternallySupplied, Opaque, Unknown, NotApplicable, Unsupported}`
  and a provenance basis.

`RecordAdmission`
: Precondition: an intent/proposal envelope exists, or admission is the first
  observable boundary for this participant. Postcondition: a
  `SelectionOrAdmission` envelope records phase realization and, when
  applicable, `AdmissionDisposition`. Rejection and withholding prevent an
  execution attempt unless the action contract declares retry, override, or
  deferred-release semantics.

`SubmitOperation`
: Precondition: an admitted action attempt exists, or the operation is an
  externally supplied backend operation with an explicit action contract or
  unsupported-action disclosure. Postcondition: an operation record exists with
  `Submitted` or `Acknowledged` state, idempotency or correlation reference when
  available, timeout policy, cancellation policy, and evidence/provenance basis.

`RecordExecutionAttempt`
: Precondition: the action contract exists or the attempt is labeled as an
  external or unsupported action. Postcondition: an `ExecutionAttempt` envelope
  records action reference, command mapping when available, actor provenance,
  temporal context, read set, possible write set, failure/support basis, and
  operation reference when execution is asynchronous. An attempt may be recorded
  even when proposal or selection is opaque.

`AdvanceOperation`
: Precondition: an operation record exists. Postcondition: the new operation
  state references its predecessor and records progress, partial outputs,
  terminal result, timeout, cancellation, retry, unsupported-state disclosure, or
  error evidence without rewriting earlier operation records.

`EmitObservation`
: Precondition: an execution attempt, operation advancement, state update,
  external event, or scenario rule produces participant-visible information.
  Postcondition: the participant-visible projection is updated only through a
  declared visibility projection, and the envelope declares an
  `InformationGuarantee`.

`CommitStateUpdate`
: Precondition: the update has a stable state address, declared state kind,
  marking policy, and conflict policy or unsupported-concurrency disclosure.
  Postcondition: the written state has a new revision or digest, the read/write
  access record references prior revisions when known, and the event is linked
  to behavior history.

`ResolveConflict`
: Precondition: two or more attempts in the same joint action set have
  intersecting semantic read/write sets, exclusive resource claims, visibility
  effects, evidence streams, or declared interference. Postcondition: the joint
  action record contains conflict class, conflict policy, realized order or
  unsupported ordering, isolation guarantee, atomicity scope, and
  per-participant observations.

`CloseEpisode`
: Precondition: ADR-013 terminal criteria are met. Postcondition: episode state
  is terminal, behavior history remains append-only, shared-state history is not
  rewritten, and unfinished operations are completed, cancelled, timed out, or
  explicitly marked unsupported/unknown.

## Observation And Information-State Semantics

The runtime may emit an observation without claiming a complete information
state. Stronger claims require stronger records.

Let:

- `H(p,e,t)` be the participant-visible action-observation history for
  participant `p`, episode `e`, through order point `t`.
- `O(p,e,t,projection)` be the observation function that maps abstract runtime
  state through a visibility projection to an observation envelope.
- `I(p,e,t)` be the information state ACES claims for participant `p` at order
  point `t`.
- `h1 ~p h2` mean two histories are indistinguishable to participant `p` under
  the declared visibility projection, markings, timing, noise, and redaction
  rules.

Guarantee meanings:

- `ObservationOnly`: only the emitted observation envelope is portable. ACES
  does not claim that `I(p,e,t)` is reconstructible from history.
- `HistoryConsistent`: `H(p,e,t)`, projection version, redaction markings, and
  stochastic/noise disclosures are sufficient to reconstruct the information
  state ACES claims.
- `PerfectRecall`: `H(p,e,t)` contains every prior participant-visible action,
  observation, and disclosed lifecycle fact needed for a perfect-recall
  information state; no prior visible fact is forgotten, overwritten, or hidden
  by later compaction.
- `LossyProjection`: the observation is sampled, aggregated, delayed, noisy,
  redacted, filtered, or partially unavailable. The envelope records the loss
  descriptor and the claim cannot be stronger than that descriptor supports.
- `Unknown`: the adapter cannot determine the guarantee.
- `Unsupported`: the backend cannot provide the guarantee.

Rules:

- Hidden world truth, scoring state, centralized-training state, backend debug
  state, and archival evidence are not participant-visible observations unless
  an explicit visibility rule projects them to `p`.
- Redacted fields remain part of the record shape as redacted tokens or omitted
  marked fields; the raw hidden value is not part of `H(p,e,t)`.
- Stochastic or noisy observations must either disclose a reproducible generator
  reference, seed/randomization context, or noise model reference, or downgrade
  to `LossyProjection`, `Unknown`, or `Unsupported`.
- A history-consistent or perfect-recall claim is invalid if the action,
  observation, projection version, redaction policy, or order context needed to
  reconstruct the information state is missing.
- A centralized-training/global-state view may be recorded as evidence or
  apparatus state, but it must use a distinct scope and marking from
  participant-visible observation.

## Concurrency And Conflict Semantics

For attempts `a` and `b` in joint action set `J`, ACES records a conflict when
any of the following hold:

- `write_set(a)` intersects `read_set(b)` or `write_set(b)`;
- `write_set(b)` intersects `read_set(a)` or `write_set(a)`;
- the attempts claim the same exclusive resource, account, channel, tool,
  budget, route, authority, session, or actuator;
- one action contract declares that it can affect the other's preconditions,
  observations, effects, visibility, evidence stream, outcome, or provenance;
- the backend reports contention, dropped work, serialization, rollback, retry,
  rejection, throttling, starvation, or unsupported simultaneity.

### Ordering

The realized order relation is a directed acyclic relation over event ids plus
optional simultaneity groups. It may be total, partial, or explicitly
unsupported.

Rules:

- `before(a,b)` means `a` is ordered before `b` by the declared order basis.
- `simultaneous(a,b)` means the contract treats `a` and `b` as the same
  coordination instant and no order is claimed between them.
- `wall_clock_only` never proves `before(a,b)` by itself. It can support
  display or weak evidence only when the capability vector discloses the weaker
  guarantee.
- Logical-clock and vector-clock contexts are evidence for happens-before
  claims only when the clock authority and update rules are declared.
- Simulation tick order, control-plane order, and serialized backend order are
  different claims and must not be collapsed.

### Isolation And Atomicity

Every joint action that reads or writes shared operational state declares:

- `snapshot_basis`: the state revisions each attempt read;
- `isolation_guarantee`: serializable, snapshot, causal, read-committed,
  best-effort, unknown, or unsupported;
- `atomicity_scope`: single-state, multi-state, per-participant, per-action,
  joint-action, backend-transaction, or unsupported;
- `rollback_refs` when the backend rolled back or compensated state.

Multi-object updates are portable only when the atomicity scope and all affected
state revisions are recorded. Snapshot claims are invalid without the read
revision set. Serializable claims are invalid without a realized order or proof
obligation showing equivalence to a serial order.

### Conflict Policy

Policy meanings:

- `Coordinate`: the runtime or backend coordinates attempts before execution.
- `Serialize`: the runtime or backend chooses a realized order. Portable only
  with realized order and read/write revisions.
- `Reject`: at least one attempt is denied and records an admission disposition
  or operation failure.
- `Retry`: at least one attempt is retried with retry bound, new predecessor
  refs, and updated read revisions.
- `Withhold`: an attempt is intentionally not released.
- `Merge`: concurrent effects are merged. Portable only when the action
  contract declares commutativity or an explicit merge rule.
- `Rollback`: an attempted effect is undone or compensated with rollback refs.
- `DiscloseWeakGuarantee`: the backend can report what happened but cannot
  satisfy the stronger required semantics.
- `Unsupported`: the backend cannot supply a portable conflict semantics.

Fairness and liveness claims are bounded claims. If ACES says a retry policy is
fair or starvation-free, the retry bound, scheduler basis, or proof obligation
must be present. Otherwise the claim must be limited to observed outcome facts.

## Capability Guarantee Vectors

A capability guarantee is a partial order over concern vectors.

Let `G` and `R` be guarantee vectors mapping concerns to strengths. `G` satisfies
`R` only when every concern required by `R` appears in `G` with strength greater
than or equal to the required strength:

```text
satisfies(G, R) =
  for all concern in required(R):
    G[concern] >= R[concern]
```

Two vectors are incomparable when each is stronger on at least one required
concern and weaker on another. Implementations must not collapse vectors to one
scalar minimum unless the claim being made explicitly requires all dimensions
and the minimum is reported as a conservative summary, not as the backend's full
capability.

Examples:

- A backend with exact ordering and weak redaction does not satisfy a claim that
  requires bounded ordering and bounded redaction.
- A backend with exact observation history and unsupported conflict resolution
  can support a single-agent information-state claim, but it cannot support a
  concurrent shared-state comparison claim.
- A backend with serialized backend order can support a review claim about the
  realized order, but it cannot claim true simultaneity.

Every downgrade is recorded as a capability disclosure linked to the event or
joint action it affects. Diagnostics may repeat the downgrade, but diagnostics
are not the portable semantics.

## Security Markings And Redaction

Runtime records that can carry sensitive data must have field-level policy.

Rules:

- Markings apply to records and to individual fields through
  `granular_markings`.
- A redaction policy states which fields are omitted, replaced by stable
  redaction tokens, summarized, hashed, or moved to controlled evidence.
- Authorization checks apply before data enters public runtime envelopes,
  diagnostics, audit details, snapshots, fixtures, generated schemas, or
  changelog fragments.
- Raw credential values, bearer tokens, hidden answer keys, private prompts,
  chain-of-thought, model activations, private memory, backend exceptions, and
  unredacted command output must not appear in portable runtime records unless a
  specific evidence contract defines a safe representation.
- Redaction must preserve enough stable identity to support provenance and
  replay claims. If it cannot, the affected claim must be downgraded.

## Asynchronous And Long-Running Operations

Cyber actions often start, block, stream observations, partially succeed, time
out, or complete after later state changes. ACES models these with operation
records rather than by inventing participant-internal lifecycle phases.

Operation records carry:

```text
OperationRecord =
  BaseEnvelope
  operation_id
  action_ref
  action_contract_ref
  command_ref
  state
  predecessor_operation_ref
  idempotency_ref
  correlation_ref
  progress_refs
  streamed_observation_refs
  partial_result_refs
  timeout_policy_ref
  cancellation_policy_ref
  retry_policy_ref
  terminal_result_ref
```

Rules:

- A long-running action starts with `SubmitOperation` or
  `RecordExecutionAttempt`.
- Each operation advancement is append-only and references its predecessor.
- Partial progress can emit observations and state updates before terminal
  completion.
- Timeout and cancellation are operation states, not episode terminal reasons.
- Retries create new lifecycle/operation records linked by predecessor refs.
- A backend that can only report start and final status must declare a weaker
  operation-state guarantee.

## Cyber Action Semantics

Portable cyber action envelopes carry:

```text
CyberActionEnvelope =
  BaseEnvelope
  action_ref
  action_contract_ref
  command_ref
  command_family
  action_verb
  target_ref
  argument_refs
  actuator_ref
  executor_ref
  session_ref
  authority_ref
  privilege_context_ref
  credential_ref
  tool_ref
  playbook_step_ref
  attack_technique_refs
  knowledge_delta_refs
  foothold_delta_refs
  visibility_delta_refs
  detection_surface_refs
  response_refs
  observation_refs
  outcome_refs
```

Rules:

- `credential_ref` points to a redacted or controlled evidence/state reference,
  never a raw credential value.
- Command mappings may cite OpenC2 actions/targets, CACAO playbook steps,
  CALDERA abilities/links/facts, ATT&CK techniques, CybORG actions, or
  backend-native commands as source mappings. Those mappings do not define ACES
  semantics by themselves.
- Knowledge, foothold, visibility, and detection deltas must be state records or
  evidence references when used to support outcome or attribution claims.
- Backend-native success or failure strings are source labels until normalized
  into ACES lifecycle, operation, observation, state, and outcome records.

## Benchmark And Reproducibility Context

Participant-runtime records are not a full experiment-management system, but
benchmark claims require an auditable runtime context:

```text
RunContext =
  run_id
  repeat_id
  scenario_ref
  scenario_version
  contract_bundle_digest
  backend_manifest_digest
  backend_version_ref
  participant_implementation_refs
  participant_adapter_refs
  participant_scaffold_refs
  model_or_policy_version_refs
  tool_version_refs
  seed_refs
  randomization_policy_ref
  run_config_digest
  evaluator_refs
  scoring_refs
  baseline_refs
  assistance_disclosures
  holdout_exposure_labels
  canary_exposure_labels
  cost_trace_refs
  resource_trace_refs
  timeout_budget_refs
  environment_build_refs
```

Rules:

- Repeated runs must have distinct `repeat_id` or equivalent identity.
- Seed/randomization claims require seed refs or an unsupported/unknown
  disclosure.
- Scaffold, tool, model, policy, and human assistance exposure must be disclosed
  when used for benchmark comparison.
- Cost/resource traces may be summarized or redacted, but the loss must be
  disclosed when it affects comparison.
- Holdout and canary labels must not reveal hidden answers to participants.

## Refinement And Conformance Obligations

An implementation refines this design when there is a projection from concrete
backend traces to valid abstract ACES traces.

Required preservation properties:

- participant, episode, action, operation, observation, state, joint-action, and
  evidence identity;
- append-only history and monotonic participant sequence numbers;
- lifecycle phase, phase realization, admission disposition, and operation
  state vocabulary;
- observation function, visibility projection, action-observation history, and
  information-state guarantee;
- shared-state address, revision/digest, marking, and provenance discipline;
- realized order, clock basis, isolation guarantee, atomicity scope, conflict
  predicate, and conflict policy;
- component-wise capability guarantee vectors and explicit downgrades;
- redaction and authorization policy before public disclosure;
- run context needed for reproducibility claims.

Safety properties:

- no hidden state as participant-visible observation without a visibility rule;
- no inference of causality from wall clock alone;
- no history rewrite after append;
- no unmarked sensitive field in public runtime records;
- no capability claim stronger than backend declaration and evidence;
- no conflation of opaque, unknown, not applicable, and unsupported.

Liveness properties are bounded and contract-specific:

- admitted synchronous attempts either record an execution result, failure,
  rejection, or unsupported disclosure within the contract's timeout bound;
- admitted long-running operations eventually record progress, terminal state,
  timeout, cancellation, unknown, or unsupported disclosure within the declared
  operation policy;
- retry, fairness, and starvation-free claims require declared scheduler,
  retry, and bound evidence.

Future implementation issues should turn the concurrency and information-state
subsets into an executable model, such as TLA+/PlusCal, Alloy, state-machine
property tests, or differential tests against backend traces.

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
results, workflow state, and operation state.

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
declares an ordering basis: total order, partial order, simultaneity,
serialized backend order, simulation order, control-plane order, logical/vector
clock order, or unsupported/unknown ordering.

### I10 - Conflict Policy Disclosure

Concurrent attempts that touch the same shared operational state, exclusive
resource, visibility surface, evidence stream, or action-contract interference
relation declare their conflict class and policy. Implicit last-writer-wins is
not a valid portable semantics.

### I11 - Observation Projection Boundary

Observation emission may update participant-visible state, but it must not
collapse world truth, shared operational state, participant belief/history,
centralized-training state, scoring state, and archival evidence.

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
admission, operation, observation, shared-state, ordering, isolation, conflict,
redaction, provenance, replay, or benchmark guarantee must reject or disclose
the weaker realization.

### I15 - Replay Compatibility

Behavior history, operation history, shared-state revisions, ordering,
observations, and evidence references must be sufficient to explain what the
runtime claimed happened. Replay may be approximate, but the lost or unsupported
guarantees must be visible.

### I16 - Closed Vocabulary Semantics

Lifecycle phase, phase realization, admission disposition, operation state,
information guarantee, ordering basis, isolation guarantee, conflict policy,
and capability strength values are closed at the portable contract layer.
Source labels may be preserved, but source labels do not define ACES semantics.

### I17 - Missingness Distinctions

`Opaque`, `Unknown`, `NotApplicable`, and `Unsupported` must remain
distinguishable. They express apparatus boundary, epistemic gap, semantic
absence, and backend capability limit respectively.

### I18 - Information-State Claim Strength

An observation may be portable without a portable information-state claim.
Whenever ACES claims history consistency or perfect recall, the
action-observation history, visibility projection, markings, stochastic/noise
context, and order relation must be sufficient for that claim.

### I19 - Semantic Conflict Detection

Conflict detection is based on semantic read/write sets, exclusive resource
claims, visibility effects, evidence streams, action-contract interference,
sessions, authorities, and actuators. It is not limited to object identity or
physical storage collisions.

### I20 - Capability Vector Monotonicity

A runtime claim cannot be stronger than the required backend guarantee vector
for lifecycle, admission, operation, observation, shared-state revision,
ordering, isolation, conflict, redaction, provenance, replay, and benchmark
concerns. Downgrades are records, not diagnostics-only warnings.

### I21 - Capability Incomparability

Guarantee vectors that are stronger on different concerns are incomparable
unless the claim explicitly ignores the weaker concern. Implementations must not
silently collapse incomparable vectors to one scalar.

### I22 - Marking And Redaction Enforcement

Security markings and redaction policies are enforced before data is published
through runtime envelopes, diagnostics, audit details, snapshots, fixtures,
schemas, or changelog fragments.

### I23 - Operation State Append-Only

Long-running operation state advances by appending operation records. Timeout,
cancellation, partial progress, and failure do not rewrite prior lifecycle,
operation, observation, or state records.

### I24 - Cyber Command Context

Cyber actions that support portable behavior or outcome claims preserve command,
target, actuator, executor, session, authority, privilege, credential reference,
knowledge delta, visibility delta, response, and evidence context as governed
references.

### I25 - Benchmark Provenance

Benchmark comparison claims require run context for scenario version, contract
bundle, backend manifest, participant implementation, adapter/scaffold/tool
exposure, seeds/randomization, evaluator/scoring, resource/cost traces, and
holdout/canary exposure labels as applicable.

### I26 - Concrete Envelope Compatibility

Every conforming implementation must be able to represent opaque LLM/RL
participants, externally supplied human actions, asynchronous cyber actions,
simultaneous joint actions, backend-serialized weak concurrency, and redacted
evidence without changing the portable semantics.

## Canonical Design Examples

The examples use snake_case wire-style values and complete abstract fields. Raw
payloads are represented by governed refs, not omitted secrets.

### Opaque LLM Agent Action

```yaml
lifecycle_envelope:
  event_id: evt-llm-17-exec
  schema_name: aces.participant_runtime.lifecycle
  schema_version: 1.0.0
  event_type: execution_attempt
  extension_policy: reject_unknown_required
  participant_address: participants.red.llm
  episode_id: ep-red-004
  sequence_number: 17
  occurred_at: 2026-05-26T10:15:01Z
  recorded_at: 2026-05-26T10:15:02Z
  ingested_at: 2026-05-26T10:15:03Z
  clock_authority: backend.logical_clock.red-range
  temporal_context: tick-118
  ordering_basis: logical_clock
  logical_order_ref: order.red.118.17
  predecessor_event_refs:
    - evt-llm-16-selection
  actor_ref: participants.red.llm
  producer_ref: adapters.llm-tool-runtime.v2
  source_system_ref: tool-gateway.red
  source_record_ref: gateway-call-992
  source_raw_ref: evidence.raw.tool-call-992
  confidence: 0.82
  provenance_refs:
    - provenance.participant_observed
  evidence_refs:
    - evidence.tool-call-992-redacted
  markings:
    - internal
  granular_markings:
    /source_raw_ref:
      - restricted_evidence
  redaction_policy_ref: redaction.no-prompts-or-secrets.v1
  authorization_scope: runtime_review
  phase: execution_attempt
  phase_realization: observed
  admission_disposition: admitted
  operation_ref: null
  action_ref: actions.exfiltrate_file
  action_contract_ref: contracts.file_access.v1
  command_ref: commands.tool.invoke-992
  actor_provenance: participant_observed
  observation_refs:
    - obs-red-17
  shared_state_read_refs:
    - hosts.web01.files.secret-plan@rev3
  shared_state_write_refs:
    - evidence.collection.red@rev9
  emitted_state_update_refs:
    - state-update-red-17
  joint_action_set_ref: null
  source_status_label: tool_call_completed
  mapping_loss: selection_private_to_model
selection_envelope:
  event_id: evt-llm-16-selection
  schema_name: aces.participant_runtime.lifecycle
  schema_version: 1.0.0
  event_type: selection_or_admission
  extension_policy: reject_unknown_required
  participant_address: participants.red.llm
  episode_id: ep-red-004
  sequence_number: 16
  occurred_at: 2026-05-26T10:15:00Z
  recorded_at: 2026-05-26T10:15:02Z
  ingested_at: 2026-05-26T10:15:03Z
  clock_authority: backend.logical_clock.red-range
  temporal_context: tick-118
  ordering_basis: logical_clock
  logical_order_ref: order.red.118.16
  predecessor_event_refs: []
  actor_ref: participants.red.llm
  producer_ref: adapters.llm-tool-runtime.v2
  source_system_ref: llm-agent.red
  source_record_ref: null
  source_raw_ref: null
  confidence: null
  provenance_refs:
    - provenance.apparatus_boundary
  evidence_refs: []
  markings:
    - internal
  granular_markings: {}
  redaction_policy_ref: redaction.no-prompts-or-secrets.v1
  authorization_scope: runtime_review
  phase: selection_or_admission
  phase_realization: opaque
  admission_disposition: unknown
  operation_ref: null
  action_ref: actions.exfiltrate_file
  action_contract_ref: contracts.file_access.v1
  command_ref: null
  actor_provenance: apparatus_opaque
  observation_refs: []
  shared_state_read_refs: []
  shared_state_write_refs: []
  emitted_state_update_refs: []
  joint_action_set_ref: null
  source_status_label: model_private_choice
  mapping_loss: private_policy_trace_not_exposed
```

The runtime records the observable action attempt. It does not require prompt
content, chain-of-thought, policy logits, tool reasoning, or private memory.

### RL Policy Step With Observation-Only Guarantee

```yaml
observation_envelope:
  event_id: obs-blue-43
  schema_name: aces.participant_runtime.observation
  schema_version: 1.0.0
  event_type: observation_emission
  extension_policy: reject_unknown_required
  participant_address: participants.blue.rl
  episode_id: ep-blue-002
  sequence_number: 43
  occurred_at: 2026-05-26T10:20:10Z
  recorded_at: 2026-05-26T10:20:10Z
  ingested_at: 2026-05-26T10:20:11Z
  clock_authority: sim.tick
  temporal_context: tick-42
  ordering_basis: simulation_tick
  logical_order_ref: order.sim.42.blue.obs43
  predecessor_event_refs:
    - evt-rl-42-exec
  actor_ref: participants.blue.rl
  producer_ref: adapters.cyborg-blue.v1
  source_system_ref: cyborg.sim
  source_record_ref: cyborg.obs.42.blue
  source_raw_ref: evidence.raw.cyborg.obs.42.blue
  confidence: 1.0
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.obs-blue-43-redacted
  markings:
    - participant_visible
  granular_markings:
    /hidden_state_refs:
      - restricted_evidence
  redaction_policy_ref: redaction.blue-observation.v1
  authorization_scope: participant:participants.blue.rl
  observation_ref: observations.blue.local.telemetry.43
  phase_ref: evt-rl-42-exec
  visibility_projection_ref: projections.blue.local.telemetry.v1
  information_guarantee: observation_only
  action_observation_history_ref: history.blue.ep002.prefix43
  information_state_ref: null
  hidden_state_refs:
    - evidence.hidden-world-state.tick42
  centralized_state_refs:
    - evidence.global-training-state.tick42
  loss_descriptor:
    kind: partial_projection
    fields_redacted:
      - attacker.intent
  stochastic_context:
    seed_ref: seeds.run-778-blue
    randomization_policy_ref: randomization.cyborg.default.v1
  noise_model_ref: null
  redacted_field_refs:
    - /hidden_state_refs
```

The policy update, reward update, and model state are apparatus internals unless
an explicit evidence contract exposes a redacted representation.

### Human-Supplied Action

```yaml
lifecycle_envelope:
  event_id: evt-human-09-admission
  schema_name: aces.participant_runtime.lifecycle
  schema_version: 1.0.0
  event_type: selection_or_admission
  extension_policy: reject_unknown_required
  participant_address: participants.gold.operator
  episode_id: ep-gold-001
  sequence_number: 9
  occurred_at: 2026-05-26T10:30:00Z
  recorded_at: 2026-05-26T10:30:02Z
  ingested_at: 2026-05-26T10:30:02Z
  clock_authority: control_plane.audit_clock
  temporal_context: wallclock-window-30
  ordering_basis: control_plane_order
  logical_order_ref: audit.gold.09
  predecessor_event_refs:
    - evt-human-08-observation
  actor_ref: users.operator-7
  producer_ref: control-plane.operator-console.v1
  source_system_ref: operator-console
  source_record_ref: command-form-9
  source_raw_ref: evidence.operator-command-9
  confidence: 1.0
  provenance_refs:
    - provenance.externally_supplied
  evidence_refs:
    - evidence.operator-command-9-redacted
  markings:
    - internal
  granular_markings: {}
  redaction_policy_ref: redaction.operator-command.v1
  authorization_scope: runtime_review
  phase: selection_or_admission
  phase_realization: externally_supplied
  admission_disposition: admitted
  operation_ref: null
  action_ref: actions.approve_containment
  action_contract_ref: contracts.defense.approve-containment.v1
  command_ref: null
  actor_provenance: human_operator
  observation_refs: []
  shared_state_read_refs:
    - incident.queue.web01@rev12
  shared_state_write_refs: []
  emitted_state_update_refs: []
  joint_action_set_ref: null
  source_status_label: submitted_by_operator
  mapping_loss: null
```

The human operator is represented through the same participant runtime boundary
as an automated agent; the source of selection is external, not opaque.

### Asynchronous Cyber Action

```yaml
operation_record:
  event_id: op-red-55-running
  schema_name: aces.participant_runtime.operation
  schema_version: 1.0.0
  event_type: operation_advance
  extension_policy: reject_unknown_required
  participant_address: participants.red.playbook
  episode_id: ep-red-006
  sequence_number: 55
  occurred_at: 2026-05-26T10:40:30Z
  recorded_at: 2026-05-26T10:40:31Z
  ingested_at: 2026-05-26T10:40:32Z
  clock_authority: backend.logical_clock.caldera
  temporal_context: operation-window-55
  ordering_basis: logical_clock
  logical_order_ref: caldera.order.55
  predecessor_event_refs:
    - op-red-55-ack
  actor_ref: participants.red.playbook
  producer_ref: adapters.caldera.v1
  source_system_ref: caldera.operation.abc
  source_record_ref: link.1234
  source_raw_ref: evidence.raw.caldera.link.1234
  confidence: 0.9
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.caldera.link.1234-redacted
  markings:
    - internal
  granular_markings:
    /source_raw_ref:
      - restricted_evidence
  redaction_policy_ref: redaction.cyber-action.v1
  authorization_scope: runtime_review
  operation_id: op-red-55
  action_ref: actions.credential_dump
  action_contract_ref: contracts.attack.credential-dump.v1
  command_ref: commands.caldera.link.1234
  state: running
  predecessor_operation_ref: op-red-55-ack
  idempotency_ref: idem.red.credential-dump.55
  correlation_ref: caldera.operation.abc.link.1234
  progress_refs:
    - progress.red.55.started
  streamed_observation_refs:
    - obs-red-55-stdout-1
  partial_result_refs: []
  timeout_policy_ref: timeout.operation.5m
  cancellation_policy_ref: cancellation.best-effort.v1
  retry_policy_ref: retry.none
  terminal_result_ref: null
cyber_action_envelope:
  event_id: cyber-red-55
  schema_name: aces.participant_runtime.cyber_action
  schema_version: 1.0.0
  event_type: cyber_action_context
  extension_policy: reject_unknown_required
  participant_address: participants.red.playbook
  episode_id: ep-red-006
  sequence_number: 55
  occurred_at: 2026-05-26T10:40:30Z
  recorded_at: 2026-05-26T10:40:31Z
  ingested_at: 2026-05-26T10:40:32Z
  clock_authority: backend.logical_clock.caldera
  temporal_context: operation-window-55
  ordering_basis: logical_clock
  logical_order_ref: caldera.order.55
  predecessor_event_refs:
    - evt-red-55-exec
  actor_ref: participants.red.playbook
  producer_ref: adapters.caldera.v1
  source_system_ref: caldera.operation.abc
  source_record_ref: ability.cred-dump.link.1234
  source_raw_ref: evidence.raw.caldera.link.1234
  confidence: 0.9
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.caldera.link.1234-redacted
  markings:
    - internal
  granular_markings:
    /credential_ref:
      - secret_ref
  redaction_policy_ref: redaction.cyber-action.v1
  authorization_scope: runtime_review
  action_ref: actions.credential_dump
  action_contract_ref: contracts.attack.credential-dump.v1
  command_ref: commands.caldera.link.1234
  command_family: caldera
  action_verb: execute
  target_ref: hosts.workstation01
  argument_refs:
    - args.cred-dump.safe-summary
  actuator_ref: agents.caldera.red.01
  executor_ref: processes.agent-01
  session_ref: sessions.red.workstation01.user
  authority_ref: authorities.domain.local
  privilege_context_ref: privileges.user
  credential_ref: credentials.redacted.cred-77
  tool_ref: tools.mimikatz.redacted-profile
  playbook_step_ref: cacao.step.credential-access.4
  attack_technique_refs:
    - attack.T1003
  knowledge_delta_refs:
    - knowledge.red.discovered-credential@rev2
  foothold_delta_refs: []
  visibility_delta_refs:
    - visibility.blue.edr-alert@rev5
  detection_surface_refs:
    - detections.edr.credential-access
  response_refs: []
  observation_refs:
    - obs-red-55-stdout-1
  outcome_refs: []
```

The action can stream observations and update state before completion. Raw
credential values and unredacted command output remain controlled evidence.

### Simultaneous Conflict Over Shared State

```yaml
joint_action_record:
  event_id: joint-13
  schema_name: aces.participant_runtime.joint_action
  schema_version: 1.0.0
  event_type: concurrent_attempt
  extension_policy: reject_unknown_required
  participant_address: null
  episode_id: null
  sequence_number: null
  occurred_at: 2026-05-26T10:50:00Z
  recorded_at: 2026-05-26T10:50:01Z
  ingested_at: 2026-05-26T10:50:01Z
  clock_authority: sim.tick
  temporal_context: tick-88
  ordering_basis: simultaneous
  logical_order_ref: sim.tick.88
  predecessor_event_refs:
    - joint-12
  actor_ref: runtime.scheduler
  producer_ref: backend.cyborg-adapter.v1
  source_system_ref: cyborg.sim
  source_record_ref: sim.tick.88.joint
  source_raw_ref: evidence.raw.sim.tick88
  confidence: 1.0
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.sim.tick88.joint
  markings:
    - internal
  granular_markings: {}
  redaction_policy_ref: redaction.shared-state.v1
  authorization_scope: runtime_review
  joint_action_set_id: joint-13
  coordination_interval: tick-88
  member_event_refs:
    - evt-red-88
    - evt-blue-88
  realized_order_relation:
    simultaneous_groups:
      - [evt-red-88, evt-blue-88]
    before: []
  clock_context:
    simulation_tick: 88
  snapshot_basis:
    hosts.web01.service.http: rev7
  isolation_guarantee: snapshot
  atomicity_scope: joint_action
  read_set:
    evt-red-88:
      - hosts.web01.service.http@rev7
    evt-blue-88:
      - hosts.web01.service.http@rev7
  write_set:
    evt-red-88:
      - hosts.web01.service.http@rev8-red
    evt-blue-88:
      - hosts.web01.service.http@rev8-blue
  exclusive_resource_claims:
    - hosts.web01.service.http
  conflict_class: interference
  conflict_policy: reject
  retry_policy_ref: retry.none
  rollback_refs: []
  capability_guarantee_vector:
    ordering: exact
    isolation: bounded
    conflict_detection: exact
    conflict_resolution: bounded
    shared_state_revision: exact
    provenance: bounded
  participant_observation_refs:
    participants.red: obs-red-88-conflict
    participants.blue: obs-blue-88-conflict
```

The conflict is portable because read/write revisions, simultaneous grouping,
isolation, conflict class, policy, and per-participant observations are
explicit.

### Backend-Serialized Weak Concurrency

```yaml
joint_action_record:
  event_id: joint-21
  schema_name: aces.participant_runtime.joint_action
  schema_version: 1.0.0
  event_type: backend_serialized_attempt
  extension_policy: reject_unknown_required
  participant_address: null
  episode_id: null
  sequence_number: null
  occurred_at: 2026-05-26T11:00:00Z
  recorded_at: 2026-05-26T11:00:02Z
  ingested_at: 2026-05-26T11:00:03Z
  clock_authority: backend.scheduler.log
  temporal_context: wallclock-window-21
  ordering_basis: serialized_backend_order
  logical_order_ref: scheduler.window.21
  predecessor_event_refs:
    - joint-20
  actor_ref: backend.scheduler
  producer_ref: backend.adapter.v1
  source_system_ref: backend.scheduler
  source_record_ref: scheduler.log.21
  source_raw_ref: evidence.raw.scheduler.log.21
  confidence: 0.7
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.backend-scheduler-log-21
  markings:
    - internal
  granular_markings: {}
  redaction_policy_ref: redaction.scheduler-log.v1
  authorization_scope: runtime_review
  joint_action_set_id: joint-21
  coordination_interval: wallclock-window-21
  member_event_refs:
    - evt-a
    - evt-b
  realized_order_relation:
    before:
      - [evt-a, evt-b]
    simultaneous_groups: []
  clock_context:
    scheduler_sequence:
      evt-a: 1201
      evt-b: 1202
  snapshot_basis:
    shared.queue: rev44
  isolation_guarantee: best_effort
  atomicity_scope: backend_transaction
  read_set:
    evt-a:
      - shared.queue@rev44
    evt-b:
      - shared.queue@rev45
  write_set:
    evt-a:
      - shared.queue@rev45
    evt-b:
      - shared.queue@rev46
  exclusive_resource_claims:
    - shared.queue
  conflict_class: serialization
  conflict_policy: disclose_weak_guarantee
  retry_policy_ref: retry.unsupported
  rollback_refs: []
  capability_guarantee_vector:
    ordering: disclosed_weak
    isolation: disclosed_weak
    conflict_detection: bounded
    conflict_resolution: disclosed_weak
    shared_state_revision: bounded
    provenance: bounded
  participant_observation_refs:
    participants.a: obs-a-21
    participants.b: obs-b-21
```

This record can support review of what happened. It cannot support a claim that
the backend executed true simultaneity or serializable isolation.

## RUN-305 - Participant Runtime State And History

`RUN-305` requires portable state and history for participants, including
actions, observations, state changes, and outcomes.

Design commitments:

- participant runtime history is append-only and keyed by participant and
  episode identity;
- behavior history links action attempts, observations, state updates,
  temporal context, attribution, and outcome interpretation;
- operation history links long-running actions, progress, partial results,
  terminal states, timeouts, and cancellation;
- shared operational state is recorded through versioned state records, not
  metadata;
- history distinguishes participant-local state, shared state, visibility,
  evidence, outcomes, scoring state, and centralized-training state;
- information-state claim strength is explicit for each participant-visible
  observation;
- opaque participant phases are recorded honestly as unknown or not exposed
  rather than fabricated;
- benchmark run context is present when runtime records support comparison or
  reproducibility claims.

Future implementation artifacts:

- versioned participant runtime state/history envelopes;
- base envelope fields for schema version, event type, source refs, markings,
  and temporal context;
- operation record model for asynchronous actions;
- schema publication through `aces_contracts`;
- validation that history references known participant, episode, action,
  operation, observation, and shared-state addresses;
- validation that hidden truth, scoring state, and centralized-training state
  are not exposed as participant-visible observations without projection rules;
- tests proving reset/restart do not rewrite history;
- fixtures for opaque participants that expose attempts and observations
  without internal planning traces;
- fixtures proving marked/redacted evidence cannot leak through public runtime
  records.

## RUN-306 - Participant Decision And Execution Lifecycle

`RUN-306` requires a portable lifecycle for action proposal, selection,
execution, observation, and state update.

Design commitments:

- lifecycle phases are observable runtime event points;
- phase realization, admission disposition, and operation state use separate
  closed vocabularies;
- proposal and selection may be opaque, externally supplied, unknown, not
  applicable, or unsupported;
- admission may be admitted, rejected, withheld, unknown, or not applicable;
- execution attempts remain tied to governed action contracts, command context,
  actor provenance, and operation records when asynchronous;
- observations are emitted through participant observation boundaries;
- state updates commit through participant-local and shared-state records;
- the lifecycle is separate from episode lifecycle, workflow state, evaluator
  state, control-plane operation status, and participant internals.

Future implementation artifacts:

- lifecycle phase, phase-realization, admission-disposition, and operation-state
  vocabulary;
- runtime event envelope linking lifecycle phase, action contract, participant,
  episode, temporal context, operation, observation, and state update;
- fixtures for `Opaque`, `Unknown`, `NotApplicable`, and `Unsupported` values
  that prove they are not collapsed;
- fixtures for `Rejected`, `Withheld`, `TimedOut`, `Cancelled`, `Partial`, and
  `Failed` values showing they are not phase-realization modes;
- validation that hidden participant internals are not required or leaked;
- negative fixtures showing LLM/RL/human/script participants can satisfy the
  boundary without exposing internal planning loops.

## RUN-307 - Shared Operational State Model

`RUN-307` requires a portable shared operational state model for evolving
participant and environment state.

Design commitments:

- shared operational state is a typed runtime contract surface;
- records carry state address, kind, revision/digest, predecessor revisions,
  ordering basis, conflict policy, visibility projection, provenance, markings,
  and evidence refs;
- read/write access records carry prior and written revisions when known;
- state updates are explicit behavior-history events;
- shared state remains separate from hidden world state, participant-visible
  projection, participant belief/history, centralized-training state, scoring
  state, and archival evidence;
- backend-native stores may realize the state internally but do not define the
  portable semantics;
- cyber action knowledge, foothold, visibility, detection, and outcome deltas
  are shared-state or evidence references when used for portable claims.

Future implementation artifacts:

- shared state record/envelope model;
- compiler/runtime address convention for state records;
- validation of state refs from action contracts and behavior history;
- conformance checks rejecting metadata-only shared state;
- tests for revision, digest, read/write access, markings, redaction, and
  visibility-projection rules;
- tests proving hidden/scoring/centralized-training state cannot be confused
  with participant-visible state.

## RUN-308 - Concurrent Participant Execution

`RUN-308` requires concurrent participant execution and interaction over shared
scenario state.

Design commitments:

- concurrency is modeled through joint action sets, realized order relations,
  logical clock context, isolation guarantees, atomicity scope, revisions, and
  conflict policy;
- coordination, contention, interference, serialization, rollback, retry,
  rejection, weak guarantee, and unsupported simultaneity remain explicit
  interaction classes;
- conflicts are detected over semantic read/write sets, exclusive resource
  claims, visibility effects, evidence streams, sessions, authorities,
  actuators, and contract interference;
- concurrent state updates record read/write revisions and realized ordering;
- participant-local observations may differ even when they refer to the same
  shared event;
- backends that serialize, reject, drop, roll back, retry, or weaken
  concurrency guarantees must disclose that realization;
- capability support is evaluated with guarantee vectors, not a scalar minimum.

Future implementation artifacts:

- joint action / shared-state conflict validation;
- capability guarantee validation across lifecycle, admission, operation,
  observation, shared-state, ordering, isolation, conflict, redaction,
  provenance, replay, and benchmark concerns;
- property or differential tests for serialized versus simultaneous conflicting
  attempts;
- model-checkable or executable state-machine tests for ordering/isolation
  claims;
- conformance checks for missing order/revision/conflict/isolation metadata;
- backend capability evidence for supported concurrency guarantees.

## Non-Goals

- Defining new SDL participant syntax.
- Implementing participant runtime contracts or backends in this issue.
- Requiring participants to reveal chain-of-thought, prompts, policy internals,
  reward updates, private memory, or tool traces.
- Treating backend-native stores, logs, timestamps, or scheduler order as the
  portable runtime semantics.
- Treating reward, policy optimizer state, centralized-training state, model
  internals, or scorer state as participant runtime semantics.
- Defining a solver, policy optimizer, reward-learning API, centralized-training
  protocol, or reward API.
- Redesigning full archival study management beyond the runtime fields needed
  to preserve participant history, shared-state evidence, and reproducibility
  claims.
