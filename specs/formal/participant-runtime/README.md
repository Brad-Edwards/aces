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

- Gymnasium and OpenAI Gym support an action/observation/reward/episode
  boundary with action spaces, observation spaces, termination, truncation,
  reset, and seeding. ACES follows that boundary, while adding
  multi-participant provenance and shared-state records and without requiring
  access to private policy internals.
- PettingZoo and OpenSpiel require per-agent observations, local histories,
  action masks or legal-action surfaces, rewards, termination/truncation,
  simultaneous or sequential interaction, current-actor/active-agent semantics,
  chance-node disclosure, mean-field update disclosure, and information-state
  discipline. ACES therefore separates hidden state, participant-visible
  observations, action-observation histories, centralized-training state,
  reward/return signals, interaction context, and review evidence.
- POMDP, Dec-POMDP, POSG, and Markov-game lineage means a participant's
  observation is not world truth. Strong information-state claims require a
  reconstructible observation history, not just a final state dump.
- CybORG, CyberBattleSim, CyGIL, CALDERA, OpenC2, CACAO, and ATT&CK show that
  cyber actions carry command, target, session, credential, knowledge,
  detection, foothold, and outcome semantics. ACES records those as portable
  references without adopting any one backend or playbook format as canonical.
- OCSF and STIX establish the event-schema precedent for identity, schema
  versioning, classification, timestamps with distinct meanings, normalized
  status/severity, confidence, source/raw mapping, raw-data integrity,
  markings, granular selectors, and extension rules.
- Lamport clocks, HLA time management, Time Warp, DEVS, FMI, and related
  runtime literature require ACES to separate wall-clock timestamps, logical
  ordering, simulation time, time-advance grants, lookahead, message
  send/receive causality, rollback/anti-message handling, pacing, and
  synchronization.
- Cybench, AutoPenBench, CAIBench, AI Agents That Matter, and related agent
  benchmark critiques require run records, scaffold/tool exposure, seeds,
  repeated-run ids, statistical repetition plans, resource/cost traces,
  baseline/evaluator disclosure, metric aggregation and uncertainty procedures,
  cost normalization, evaluator leakage controls, contamination audits,
  immutable artifact evidence, and holdout/canary exposure evidence for
  auditable comparisons.

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

`Step signal`
: A participant-visible or evaluator-visible signal produced at an action step:
  observation, reward, return, action mask, termination, truncation, or
  auxiliary info. Step signals are runtime records, not participant internals.

`Action mask`
: A participant-scoped legal-action projection at an order point. It is valid
  only for the declared action space, visibility projection, and state revision
  context that produced it.

`Active agent set`
: The participant addresses that may legally choose an action at a game or
  environment order point. Sequential/AEC surfaces have one current actor;
  simultaneous and parallel surfaces may have more than one; chance and
  mean-field nodes have no participant action unless explicitly wrapped by a
  scenario participant.

`Chance node`
: A runtime order point where stochastic environment/nature behavior, not a
  participant decision, selects an outcome. Portable claims require the chance
  mode, distribution or sampled-outcome disclosure, seed/randomization context,
  and ordering basis.

`Mean-field node`
: A runtime order point where the environment updates or consumes a population
  distribution rather than accepting an ordinary participant action. Portable
  claims require the distribution reference, update rule, and affected
  participant population scope.

`Conflict policy`
: The explicit rule or disclosure used when concurrent attempts touch the same
  shared operational state, resource, visibility surface, evidence stream, or
  action-contract interference relation.

`Capability guarantee`
: A backend's declared strength for a specific runtime concern. Capability is a
  vector over concerns and runtime components, not one scalar level.

`Time-management context`
: The declared time domain, clock authority, advancement, lookahead,
  message-causality, pacing, rollback, or step-negotiation basis for a
  distributed or simulated runtime claim.

`Benchmark validity claim`
: A bounded claim that a runtime record supports reproducibility, comparison,
  non-contamination, or cost-normalized evaluation. It is separate from the raw
  run context and must cite a statistical/evaluation procedure when used for
  comparative conclusions.

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
  participant_interfaces
  interaction_contexts
  step_signals
  action_observation_histories
  information_states
  shared_state
  joint_actions
  time_management_contexts
  evidence_index
  run_context
  benchmark_claims
  capability_declarations
  capability_components
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
- `participant_interfaces[p,e,t]` records action/observation spaces and
  legal-action or mask surfaces visible at order point `t`.
- `interaction_contexts[t]` records active-agent, chance, simultaneous, and
  mean-field node semantics for game/RL/MARL surfaces.
- `step_signals[p,e,t]` records reward, return, termination, truncation,
  action-mask, observation, and auxiliary-info signals when exposed.
- `action_observation_histories[p,e,t]` is the prefix of visible actions and
  observations available to participant `p` at order point `t`.
- `information_states[p,e,t]` is the information state ACES claims for
  participant `p` at order point `t`.
- `shared_state[address]` is the version chain for a shared operational state
  address.
- `joint_actions[id]` records coordination intervals and concurrent attempts.
- `time_management_contexts[id]` records simulation/distributed time semantics
  used by joint action, operation, or state-update records.
- `evidence_index` maps safe evidence references to evidence contracts and
  redaction policies.
- `run_context` contains reproducibility and benchmark context.
- `benchmark_claims[id]` records the explicit validity procedure for any
  reproducibility, comparison, non-contamination, or cost-normalized claim.
- `capability_declarations[backend, concern]` is the backend's declared
  contribution to the effective guarantee vector.
- `capability_components[component, concern]` records adapter, backend,
  evidence-store, redaction, clock, observer, and coordinator contributions to
  the effective guarantee vector.
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
  event_classification
  source_status
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
  source_pipeline
  raw_data_integrity
  confidence
  provenance_refs
  evidence_refs
  marking_definition_refs
  object_marking_refs
  markings
  granular_markings
  redaction_policy_ref
  authorization_scope
```

Rules:

- `event_id` is globally stable within the run.
- `schema_name` and `schema_version` identify the ACES contract projection, not
  the backend's native object.
- `event_classification` and `source_status` are nullable only when the record
  makes no normalized event-status, severity, or security-telemetry claim.
  When populated they use the structures below.
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
- `raw_data_integrity` records hash, size, truncation, and untruncated-size
  facts for raw data that supports a runtime claim.
- `source_pipeline` records source product/version, original event identity,
  processed/logged/transmitted times, correlation, and sequence information
  when a source telemetry or command system is mapped into ACES.
- `markings` and `granular_markings` are enforceable field-level disclosure
  labels.

Event classification, source status, source pipeline metadata, raw-data
integrity, and marking selectors follow the OCSF/STIX design pattern while
remaining ACES-native:

```text
EventClassification =
  category_uid
  category_name
  class_uid
  class_name
  activity_id
  activity_name
  type_uid
  type_name
  severity_id
  severity
```

```text
SourceStatus =
  status_id
  status
  status_code
  status_detail
  source_status_label
  source_status_mapping
```

```text
SourcePipeline =
  product_ref
  product_version
  log_provider
  log_source
  log_name
  original_event_uid
  original_time
  processed_time
  logged_time
  transmit_time
  correlation_uid
  sequence
```

```text
RawDataIntegrity =
  raw_data_hash
  raw_data_hash_algorithm
  raw_data_size
  raw_data_is_truncated
  raw_data_untruncated_size
```

```text
GranularMarking =
  selectors
  marking_ref
  marking_scope
```

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

Interaction mode is:

```text
InteractionMode =
  SingleAgent
  SequentialTurn
  AgentEnvironmentCycle
  Parallel
  Simultaneous
  Chance
  MeanField
  BackendSerialized
  Terminal
  Unknown
  Unsupported
```

Chance mode is:

```text
ChanceMode =
  NotApplicable
  Deterministic
  ExplicitStochastic
  SampledStochastic
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
  reconstruction_algorithm_ref
  reconstruction_proof_ref
  belief_support_ref
  redacted_field_refs
```

Participant interface and step-signal records carry the RL/MARL-facing pieces
that Gymnasium, PettingZoo, and OpenSpiel make first-class, without making them
the ACES protocol:

```text
ParticipantInterface =
  BaseEnvelope
  participant_address
  episode_id
  interaction_mode
  possible_agent_set_ref
  active_agent_set_ref
  current_actor_ref
  action_space_ref
  action_space_schema_ref
  observation_space_ref
  observation_space_schema_ref
  legal_action_policy_ref
  action_mask_policy_ref
  action_mask_location
  null_action_policy_ref
  chance_policy_ref
  mean_field_policy_ref
  space_version
  applicability
```

```text
InteractionContextEnvelope =
  BaseEnvelope
  interaction_context_id
  interaction_mode
  order_point
  possible_agent_set_ref
  active_agent_set
  current_actor_ref
  simultaneous_group_ref
  nonacting_agent_policy_ref
  legal_action_snapshot_refs
  chance_mode
  chance_distribution_ref
  chance_distribution_digest
  sampled_chance_outcome_ref
  chance_seed_ref
  chance_visibility
  mean_field_population_ref
  mean_field_distribution_ref
  mean_field_distribution_digest
  mean_field_update_rule_ref
  mean_field_update_ref
  terminal_node
  unsupported_interaction_disclosure
```

```text
ActionMaskEnvelope =
  BaseEnvelope
  participant_address
  episode_id
  interaction_context_ref
  action_space_ref
  mask_ref
  legal_action_refs
  illegal_action_refs
  mask_encoding
  valid_for_order_point
  valid_for_state_revision_refs
  visibility_projection_ref
  stochastic_context
```

```text
RewardEnvelope =
  BaseEnvelope
  participant_address
  episode_id
  reward_ref
  reward_value_ref
  reward_units
  reward_range_ref
  reward_model
  reward_visibility
  reward_timing
  source_outcome_refs
  scoring_refs
```

```text
ReturnEnvelope =
  BaseEnvelope
  participant_address
  episode_id
  return_ref
  cumulative_return_value_ref
  return_horizon
  return_discount_ref
  reward_ref_prefix
  terminal_basis_ref
```

```text
TerminationEnvelope =
  BaseEnvelope
  participant_address
  episode_id
  terminated
  truncated
  termination_reason_ref
  truncation_reason_ref
  terminal_observation_ref
  episode_terminal_reason_ref
  local_only
```

```text
StepSignalEnvelope =
  BaseEnvelope
  participant_address
  episode_id
  interaction_context_ref
  active_agent_set_ref
  current_actor_ref
  action_ref
  observation_ref
  action_mask_ref
  reward_ref
  return_ref
  termination_ref
  info_refs
  centralized_state_refs
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
  time_management_context_ref
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

Time-management contexts carry:

```text
TimeManagementContext =
  BaseEnvelope
  time_context_id
  time_domain
  time_management_mode
  logical_time
  simulation_time
  wall_clock_interval
  lookahead
  time_regulating
  time_constrained
  time_advance_request_ref
  time_advance_grant_ref
  next_event_request_ref
  message_send_refs
  message_receive_refs
  pacing_policy_ref
  step_size_ref
  rollback_window_ref
  rollback_refs
  anti_message_refs
  compensation_refs
  superseded_event_refs
  transition_basis
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

Time-management mode is normalized:

```text
TimeManagementMode =
  None
  WallClockRealtime
  ConservativeLogicalTime
  HlaTimeManaged
  OptimisticRollback
  DevsDiscreteEvent
  FmiCoSimulation
  BackendSerialized
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
  participant_interface
  interaction_context
  action_mask
  reward_signal
  return_signal
  termination_signal
  shared_state_revision
  ordering
  time_management
  rollback
  isolation
  conflict_detection
  conflict_resolution
  provenance
  redaction
  replay
  benchmark_reproducibility
  benchmark_validity
```

Guarantee strength per concern is:

```text
GuaranteeStrength =
  unsupported
  disclosed_weak
  bounded
  exact
```

Capability applicability is explicit:

```text
CapabilityApplicability =
  required
  optional
  not_applicable
```

```text
CapabilityValue =
  not_applicable
  unsupported
  disclosed_weak
  bounded
  exact
```

`not_applicable` is outside the guarantee-strength order. It may appear only
when the contract and claim both state that the concern has no semantic role.
Omitting a required concern is not equivalent to `not_applicable`; it is a
capability validation failure.

## Normative Core Model

This section is the reviewable abstract model. Concrete schemas and backend
adapters refine it by mapping native records to these domains and predicates.

### Domains

Let:

```text
P  = participant addresses
E  = episode ids
A  = action attempt ids
Op = operation ids
Obs = observation ids
S  = shared-state addresses
R  = shared-state revisions
J  = joint-action ids
Ev = runtime event ids
T  = logical order points
C  = capability concerns
M  = markings and marking definitions
K  = interaction-context ids
BC = benchmark-claim ids
```

The model uses these additional carrier sets. They are explicit so that the
abstract model is not relying on implicit prose symbols:

```text
Component =
  participant_adapter
  runtime_coordinator
  backend_engine
  observation_apparatus
  evidence_store
  redaction_policy
  clock_authority
  replay_engine
  benchmark_harness

Consumer =
  participant
  runtime_operator
  evaluator
  auditor
  backend_adapter
  public_artifact

Digest       = algorithm-tagged immutable digest values
StateSpace   = abstract runtime states reachable by valid traces
VisibleEvent = participant-visible projected event records
InformationState = governed information-state records or digests
ObservationValue = governed observation values or references
Probability = real values in [0, 1]
Distribution[X] = finite-support probability distribution over X
Maybe[X] = X union {none}
Result[X] = X union {Unknown, Unsupported, Lossy}
```

Only symbols defined in this document are normative. A future executable model
may refine the carrier sets, but it must preserve the predicates and downgrade
rules below.

The abstract functions are partial unless stated otherwise:

```text
episode_state: P x E -> EpisodeState
seq: P x E -> Nat
event: Ev -> BaseEnvelope
phase: Ev -> LifecyclePhase
realization: Ev -> PhaseRealization
admission: Ev -> AdmissionDisposition
operation_state: Op x T -> OperationState
visible_history: P x E x T -> Seq(VisibleEvent)
observation: Obs -> ObservationEnvelope
information_claim: P x E x T -> InformationGuarantee
state_revision: S x T -> R
state_digest: S x R -> Digest
order_relation: T -> Relation(Ev, Ev)
capability: Component x C -> CapabilityValue
effective_capability: C -> CapabilityValue
authorized: Consumer x BaseEnvelope -> Bool
interaction_context: K -> InteractionContextEnvelope
interaction_context_at: T -> Maybe[K]
active_agents: K -> Set(P)
current_actor: K -> Maybe[P]
chance_distribution: K -> Result[Distribution[ObservationValue]]
mean_field_distribution: K -> Result[Digest]
benchmark_claim: BC -> BenchmarkValidityClaim
```

Trace helpers are defined as follows:

```text
prefix(tr, i) =
  <ev_1, ..., ev_i> when tr = <ev_1, ..., ev_n> and 0 <= i <= n

prefix_state(tr, i) =
  fold_apply(initial_state(tr), prefix(tr, i))

fold_apply(s, <>) = s
fold_apply(s, <ev_1, ..., ev_n>) =
  Reject if Apply(s, ev_1) = Reject
  else fold_apply(Apply(s, ev_1), <ev_2, ..., ev_n>)
```

`initial_state(tr)` is the declared run initialization state containing
participants, admitted episodes, run context, capability components, marking
policies, and controlled vocabulary versions. If that declaration is missing,
`InitOK` is false.

`CapabilityValue` is `not_applicable` or a `GuaranteeStrength`. The strength
order is:

```text
unsupported < disclosed_weak < bounded < exact
```

### Valid Trace Predicate

A trace `tr = <ev_1, ..., ev_n>` is valid iff all of the following hold:

```text
ValidTrace(tr) =
  Unique(event_id, tr)
  /\ InitOK(tr[1])
  /\ forall i in 1..n:
       BaseOK(ev_i)
       /\ MarkingOK(ev_i)
       /\ CapabilityOK(ev_i)
       /\ RefOK(ev_i, prefix(tr, i - 1))
       /\ Apply(prefix_state(tr, i - 1), ev_i) != Reject
  /\ AppendOnly(tr)
  /\ MonotoneSequence(tr)
  /\ RevisionDiscipline(tr)
  /\ OrderDiscipline(tr)
```

Where:

- `BaseOK` checks envelope identity, schema version, timestamps, source/raw
  references, classification/status requiredness, and extension policy.
- `MarkingOK` checks record-level and granular marking selectors before a
  record is published to any consumer.
- `CapabilityOK` checks every claim against the effective capability vector.
- `RefOK` checks referenced participants, episodes, actions, operations,
  observations, state revisions, joint actions, evidence, and source mappings.
- `AppendOnly` forbids deletion or mutation of prior history records; rollback
  creates superseding records.
- `MonotoneSequence` requires participant-scoped `sequence_number` to increase
  within each `(participant_address, episode_id)` stream.
- `RevisionDiscipline` requires every shared-state write to cite known prior
  revisions or disclose unknown/unsupported revision support.
- `OrderDiscipline` requires every ordering claim to be backed by a declared
  order basis stronger than wall-clock-only display order.

### Transition Schema

Each transition is a predicate over pre-state `s`, event `ev`, and post-state
`s'`:

```text
Transition_k(s, ev, s') =
  Pre_k(s, ev)
  /\ s' = Update_k(s, ev)
  /\ Post_k(s, ev, s')
```

`Apply(s, ev)` returns `Reject` unless exactly one transition predicate matches
the event type and all shared invariants hold. If multiple transitions could
match, the event is invalid because its portable semantics are ambiguous.

Shared transition obligations:

```text
HistoryAppend(s, ev, s')
OrderAppend(s, ev, s')
NoHiddenDisclosure(s, ev, s')
NoCapabilityUpgrade(s, ev, s')
NoUnauthorizedField(s, ev, s')
```

These obligations are part of every transition, including records that are
externally supplied or opaque.

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
6. every runtime claim is no stronger than the effective component-wise
   capability vector and the evidence actually recorded.

The state machine rejects an event when accepting it would require hidden truth
to appear as participant-visible observation, infer ordering from wall clock
alone, rewrite history, skip a required redaction, invent participant internals,
or claim a capability stronger than the effective declared support.

### Transitions

`ObserveIntent`
: Records an intent/proposal/trigger when the runtime can observe it.
  Participants that do not expose intent may enter the lifecycle at
  `SelectionOrAdmission`, `ExecutionAttempt`, or a lifecycle envelope with
  `Opaque`, `Unknown`, `NotApplicable`, or `Unsupported` phase realization.

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

`EmitStepSignal`
: Emits an RL/MARL/game-style step signal such as action mask, reward, return,
  termination, truncation, or auxiliary info. This transition is optional for
  non-RL participants and must not fabricate signals when the backend does not
  expose them.

`RecordInteractionContext`
: Records the game/environment node semantics for an order point: active agent
  set, current actor, simultaneous group, chance mode and distribution or
  sampled outcome, mean-field distribution update, terminal node, or unsupported
  disclosure. This transition is required before a runtime claim uses AEC,
  simultaneous, chance, or mean-field semantics.

`CommitStateUpdate`
: Writes participant-local, shared operational, visibility, evidence-facing, or
  outcome-facing state records with revision, digest, ordering, provenance,
  markings, and conflict semantics.

`RecordTimeAdvance`
: Records a time-management event such as lookahead declaration,
  time-advance request/grant, step negotiation, message delivery, pacing, or
  unsupported time-management disclosure.

`RecordRollbackOrCompensation`
: Records an optimistic rollback, anti-message, compensation, or supersession
  relation. It never deletes earlier records.

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

`EmitStepSignal`
: Precondition: an execution attempt, observation, operation advancement,
  scenario rule, or backend step produces a participant-visible or
  evaluator-visible action mask, reward, return, termination, truncation, or
  auxiliary info signal. Postcondition: the signal references its space,
  visibility projection, order point, state revision basis, and marking policy;
  termination and truncation are represented separately; and no hidden state is
  exposed through `info_refs` unless a visibility rule authorizes it.

`RecordInteractionContext`
: Precondition: a step, joint action, observation, reward, terminal signal, or
  state update makes a claim about turn order, active actors, simultaneous
  actors, chance, mean-field, terminal-node, or backend-serialized game
  semantics. Postcondition: an `InteractionContextEnvelope` exists for the
  order point, `active_agents`, `current_actor`, chance disclosure, and
  mean-field disclosure satisfy `InteractionClaimOK`, and related step-signal
  or joint-action records cite the context.

`CommitStateUpdate`
: Precondition: the update has a stable state address, declared state kind,
  marking policy, and conflict policy or unsupported-concurrency disclosure.
  Postcondition: the written state has a new revision or digest, the read/write
  access record references prior revisions when known, and the event is linked
  to behavior history.

`RecordTimeAdvance`
: Precondition: a joint action, operation, state update, or external
  simulation/federation event depends on time-management semantics stronger
  than wall-clock display order. Postcondition: the time-management context
  records the time domain, mode, logical/simulation time, lookahead,
  request/grant or step-negotiation refs, message send/receive refs, and any
  unsupported disclosure needed for the ordering claim.

`RecordRollbackOrCompensation`
: Precondition: a backend performs or reports optimistic rollback,
  anti-message cancellation, compensation, or supersession. Postcondition: the
  rollback or compensation record references the affected prior events,
  produces superseding records when claims change, preserves append-only
  history, and downgrades replay/order guarantees unless the rollback evidence
  supports the stronger claim.

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
- `O(p,e,t,projection)` be the observation function that maps an abstract
  runtime state through a visibility projection to an observation envelope.
- `I(p,e,t)` be the `InformationState` ACES claims for participant `p` at
  order point `t`.
- `h1 ~p h2` mean two histories are indistinguishable to participant `p` under
  the declared visibility projection, markings, timing, noise, and redaction
  rules.

The visible-history projection is typed:

```text
Project_p,policy : Ev x P -> Maybe[VisibleEvent]

For a valid trace `tr`:

H_tr(p,e,t) =
  ordered sequence of Project_p,policy(ev, p)
  for ev in tr whose declared order point is at or before t
  where Project_p,policy(ev, p) != none
```

A `VisibleEvent` contains only:

```text
VisibleEvent =
  event_id
  delivered_order
  visible_payload_ref_or_digest
  visible_field_selectors
  marking_projection_digest
  redaction_token_refs
  stochastic_disclosure_ref
  source_projection_version
```

Hidden field values are never members of `VisibleEvent`; redacted values appear
only as stable redaction tokens or omission markers governed by the referenced
redaction policy.

The indistinguishability relation is defined by visible projection, not by
backend state equality:

```text
h1 ~p h2 iff
  VisiblePayloads(p, h1) = VisiblePayloads(p, h2)
  /\ VisibleSelectors(p, h1) = VisibleSelectors(p, h2)
  /\ VisibleMarkingDigests(p, h1) = VisibleMarkingDigests(p, h2)
  /\ VisibleDeliveredOrder(p, h1) = VisibleDeliveredOrder(p, h2)
  /\ VisibleStochasticDisclosures(p, h1) =
     VisibleStochasticDisclosures(p, h2)
```

`~p` must be reflexive, symmetric, and transitive for the recorded projection
version. If redaction or lossy projection prevents stable equality, the claim
must downgrade to `LossyProjection`, `Unknown`, or `Unsupported`.

The observation kernel is:

```text
Z_p,projection,noise,t : StateSpace x Maybe[A] -> Distribution[ObservationValue]

Z_p,projection,noise,t(s, a?)(o) =
  probability that observation value o is emitted to p
  from abstract runtime state s after optional action a at order point t
```

The kernel is valid only when:

```text
KernelOK(p,e,t) =
  sum({ Z_p,projection,noise,t(s, a?)(o) | o in support }) = 1
  /\ all probabilities are in [0, 1]
  /\ support observations satisfy ObservationEnvelope schema and markings
  /\ stochastic context cites a seed/generator, probability model, or downgrade
```

Deterministic observations are the degenerate case where the support has one
observation with probability `1`. If the distribution cannot be reconstructed
or bounded, the observation may still be recorded, but the guarantee must
downgrade to `LossyProjection`, `Unknown`, or `Unsupported`.

The reconstructed information state is:

```text
Reconstruct_p :
  Seq(VisibleEvent)
  x projection_version
  x redaction_policy
  x order_relation
  x stochastic_context
  -> Result[InformationState]

Reconstruct_p(H, projection_version, redaction_policy, order_relation,
              stochastic_context) =
  fold_left(reconstruct_step_p, initial_information_state_p, H)
```

`reconstruct_step_p` is a governed algorithm referenced by
`reconstruction_algorithm_ref`; the algorithm version and test/proof artifact
must be stable for the schema version making the claim. If no governed
algorithm or proof reference exists, `Reconstruct_p` returns `Unsupported`.
If the algorithm reaches a lossy redaction, aggregation, delayed delivery, or
unknown stochastic branch that cannot prove equality with the claimed
information state, it returns `Lossy` or `Unknown`.

`HistoryConsistent` requires:

```text
Reconstruct_p(H(p,e,t), projection_version, redaction_policy,
              order_relation(t), stochastic_context) = I(p,e,t)
```

after applying the same redaction tokens and declared lossy transforms used in
the observation envelope. `PerfectRecall` additionally requires that for every
`t' < t`, the visible event prefix `H(p,e,t')` remains embedded in `H(p,e,t)`
with stable event identity and order. Compaction is allowed only when it cites
a `reconstruction_proof_ref` that can reproduce the earlier prefix or prove
that the compact representation is information-state equivalent.

For belief-state consumers, ACES may record a belief support:

```text
B_p,t = { s in StateSpace | H_s(p,e,t) ~p H_actual(p,e,t) }
```

ACES does not require a participant to maintain this belief. It only records
enough visibility, ordering, and stochastic evidence for downstream reviewers
to know whether such a belief or information-state claim is supportable.

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
- Observation emission, delivery, consumption, and acknowledgement are distinct
  when the backend can observe them. A participant-visible history may include
  an observation only after the declared delivery point, not merely because the
  backend generated the observation.
- Redacted fields remain part of the record shape as redacted tokens or omitted
  marked fields; the raw hidden value is not part of `H(p,e,t)`.
- Stochastic or noisy observations must either disclose a reproducible generator
  reference, seed/randomization context, or noise model reference, or downgrade
  to `LossyProjection`, `Unknown`, or `Unsupported`.
- A history-consistent or perfect-recall claim is invalid if the action,
  observation, projection version, redaction policy, or order context needed to
  reconstruct the information state is missing, or if
  `reconstruction_algorithm_ref` cannot be executed or audited for the relevant
  schema/projection version.
- A centralized-training/global-state view may be recorded as evidence or
  apparatus state, but it must use a distinct scope and marking from
  participant-visible observation.
- An action mask is participant-visible only when projected through the same
  information boundary as the observation or through an explicitly linked
  action-mask envelope.

## RL And Multi-Agent Step Signal Semantics

ACES does not adopt Gymnasium, PettingZoo, or OpenSpiel as wire protocols, but
it preserves the concepts that make RL/MARL results reviewable.

Rules:

- `InteractionContextEnvelope` is required whenever a step claim depends on
  turn order, an AEC current actor, simultaneous actors, a chance outcome, a
  mean-field population update, or backend serialization. Without it, ACES can
  record observations but cannot claim MARL/game-node semantics.
- In `SequentialTurn` and `AgentEnvironmentCycle` modes, `current_actor_ref`
  must be exactly one participant in `active_agent_set`. Non-acting
  participants may receive observations or reward updates only when the
  interaction context records the non-acting-agent policy.
- In `Parallel` and `Simultaneous` modes, `active_agent_set` is the set of
  participants whose actions are admitted for that order point. A joint action
  or step signal must cite the same set or disclose the mismatch.
- In `Chance` mode, participant `action_ref` is null unless a scenario
  explicitly models nature as a participant. The record must cite
  `chance_mode`, a distribution or sampled-outcome disclosure,
  seed/randomization context when available, and the visibility policy that
  determines which participants can observe the chance event.
- In `MeanField` mode, no ordinary participant action is consumed at the node.
  The record must cite the population scope, distribution digest, update rule,
  and affected observations/rewards or disclose unsupported mean-field
  semantics.
- `action_space_ref` and `observation_space_ref` identify governed space
  definitions. They are required for claims that an action, observation, or
  policy trace is valid relative to an RL/game environment space.
- Action masks are time- and participant-scoped. A mask emitted at `t` cannot
  justify an action at a different order point unless its validity interval,
  state revision basis, and projection rule say so.
- `RewardEnvelope` records participant-visible or evaluator-visible reward.
  Reward is not the same as local action status, objective success, scoring
  state, or episode terminal reason.
- `ReturnEnvelope` records cumulative return over an explicit reward prefix,
  horizon, and discount basis. It cannot be reconstructed from final objective
  success unless an interpretation rule defines that mapping.
- `TerminationEnvelope.terminated` means the task's MDP/game/scenario terminal
  condition has been reached for that participant or environment scope.
  `TerminationEnvelope.truncated` means an external bound, timeout, safety
  limit, or administrative condition ended the step/episode before task
  terminal semantics. These fields must remain separate.
- Per-participant termination/truncation may differ from global episode
  closure. ACES episode closure follows ADR-013 and references the local
  termination/truncation signals when they contributed to closure.
- `info_refs` may preserve auxiliary metrics or debug data, but marked hidden
  state inside an info object is not participant-visible unless a visibility
  projection explicitly exposes it.
- Single-agent, AEC/turn-based, parallel, simultaneous, mean-field, and
  backend-serialized multi-agent surfaces are valid only when their ordering
  and participant-local signal projections are recorded.

Conformance obligations:

```text
ActionValid(p,e,a,t) =>
  a in ActionSpace(p,e,t)
  /\ exists k = interaction_context_at(t):
       p in active_agents(k)
       /\ (current_actor(k) != none => current_actor(k) = p)
  /\ (MaskPresent(p,e,t) => MaskAllows(p,e,a,t))

RewardClaimOK(p,e,t) =>
  RewardEnvelope(p,e,t) has reward model, visibility, timing, and source basis

TerminationClaimOK(p,e,t) =>
  terminated and truncated are separate booleans
  /\ terminal observation, if any, is emitted through the observation boundary

InteractionClaimOK(k) =>
  (interaction_context(k).interaction_mode in
     {SequentialTurn, AgentEnvironmentCycle} =>
     current_actor(k) in active_agents(k) /\ |active_agents(k)| = 1)
  /\ (interaction_context(k).interaction_mode in {Parallel, Simultaneous} =>
     |active_agents(k)| >= 1 /\ joint action linkage cites active_agents(k))
  /\ (interaction_context(k).interaction_mode = Chance =>
     active_agents(k) = {}
     /\ ChanceDisclosureOK(k))
  /\ (interaction_context(k).interaction_mode = MeanField =>
     active_agents(k) = {}
     /\ MeanFieldDisclosureOK(k))
```

`ChanceDisclosureOK(k)` requires a chance mode and either a deterministic
outcome, an explicit probability distribution with digest, a sampled-outcome
record with seed/randomization context, or an `Unknown`/`Unsupported`
downgrade. `MeanFieldDisclosureOK(k)` requires population scope, distribution
digest, update rule, and update record, or an `Unknown`/`Unsupported`
downgrade.

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

### Time Management

Time-management claims are separate from ordering claims. A record may have
valid ordering evidence without supporting real-time pacing, HLA time
management, optimistic rollback, DEVS transition semantics, or FMI
co-simulation semantics.

Rules:

- `WallClockRealtime` supports pacing and display claims only. It does not
  prove causality or simultaneity.
- `ConservativeLogicalTime` requires a declared safe-delivery rule. If
  lookahead is used, a message with timestamp `ts` may be delivered only when
  the receiver's grant and lookahead make earlier conflicting messages
  impossible under the declared clock authority.
- `HlaTimeManaged` requires explicit time-regulating/time-constrained
  disclosure, lookahead where relevant, time-advance request/grant refs, and
  message send/receive refs for causality claims.
- `OptimisticRollback` requires rollback refs, anti-message or compensation
  refs when messages are cancelled, superseded event refs, and a disclosure of
  which prior observations or state updates remain participant-visible after
  rollback.
- `DevsDiscreteEvent` requires an internal, external, or confluent transition
  basis and a time-advance function or unsupported disclosure for the modeled
  component.
- `FmiCoSimulation` requires step-size or step-negotiation refs, exchanged
  input/output variable refs, rollback support or no-rollback disclosure, and
  clock-domain mapping.
- `BackendSerialized` is a weaker realization. It supports review of realized
  order but not a claim that participants acted simultaneously unless a
  separate simultaneity proof exists.

Append-only rollback discipline:

```text
RollbackOK(r) =
  affected_events(r) subset prior_events
  /\ superseding_events(r) are appended after r
  /\ no prior event is deleted or mutated
  /\ every downstream claim cites either prior or superseding lineage
```

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

A capability guarantee is a component-wise partial order over concern vectors.
The effective runtime capability for a claim is the meet of the declared
capabilities for every component that can weaken that claim.

Runtime components are:

```text
CapabilityComponent =
  participant_adapter
  runtime_coordinator
  backend_engine
  observation_apparatus
  evidence_store
  redaction_policy
  clock_authority
  replay_engine
  benchmark_harness
```

Let `G_component` be a component vector and `R_claim` be the required vector for
a claim. Effective guarantee is:

```text
effective_capability[concern] =
  meet({ G_component[concern] | component affects concern })
```

The meet operator uses the guarantee order:

```text
unsupported < disclosed_weak < bounded < exact
```

Rules:

- `meet(exact, bounded) = bounded`.
- `meet(x, unsupported) = unsupported`.
- `meet(x, disclosed_weak) <= disclosed_weak` unless all weakening components
  are marked `not_applicable` for that concern.
- `not_applicable` is neutral only when the contract states that the concern
  has no semantic role for the claim.
- Missing value for a required concern is `Reject`, not `not_applicable`.

`G` satisfies `R` only when every required concern appears in the effective
vector with strength greater than or equal to the required strength:

```text
satisfies(G, R) =
  for all concern in required(R):
    concern in domain(G)
    /\ G[concern] != not_applicable
    /\ G[concern] >= R[concern]
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
- A backend with exact replay but an evidence store that truncates raw
  observations without hashes has bounded or weak provenance, not exact
  provenance.
- A clock authority with unsupported lookahead makes HLA-style time-management
  claims unsupported even if the backend records event order exactly.

Every downgrade is recorded as a capability disclosure linked to the event or
joint action it affects. Diagnostics may repeat the downgrade, but diagnostics
are not the portable semantics.

Capability registries are versioned. A concern cannot be introduced by prose in
an adapter manifest; it must be added to the governed concern registry with
applicability, ordering, required evidence, and downgrade behavior.

## Security Markings And Redaction

Runtime records that can carry sensitive data must have field-level policy.

Rules:

- Markings apply to records and to individual fields through
  `granular_markings`.
- `marking_definition_refs` identify governed marking definitions. Free-text
  labels may be preserved as source labels, but they do not define disclosure
  semantics.
- `object_marking_refs` apply to the complete record; `granular_markings`
  apply to selector paths inside the record. Selectors must be stable under the
  published schema version.
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
  openc2_profile_ref
  openc2_command_id
  openc2_request_id
  openc2_action
  openc2_target_ref
  openc2_args_ref
  openc2_actuator_ref
  openc2_response_ref
  openc2_response_status
  openc2_response_status_text
  openc2_response_results_ref
  cacao_playbook_ref
  cacao_workflow_step_ref
  cacao_workflow_step_type
  cacao_command_refs
  cacao_agent_refs
  cacao_target_refs
  cacao_variable_refs
  cacao_authentication_ref
  cacao_on_completion_ref
  cacao_on_success_ref
  cacao_on_failure_ref
  cacao_external_refs
  caldera_operation_ref
  caldera_adversary_ref
  caldera_planner_ref
  caldera_ability_ref
  caldera_link_ref
  caldera_fact_refs
  caldera_agent_ref
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
- OpenC2 mappings preserve command/response correlation through
  `openc2_command_id`, `openc2_request_id`, and response refs. ACES lifecycle
  success or failure is not inferred from source response text without a
  normalized status mapping.
- CACAO mappings preserve playbook/workflow-step identity, commands,
  agents/targets, variables, authentication references, external references,
  and success/failure routing when those facts support behavior or outcome
  claims.
- CALDERA mappings preserve operation/adversary/planner/ability/link/fact/agent
  identity when those facts support behavior, knowledge, foothold, detection,
  or provenance claims.
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
  study_id
  trial_id
  repeat_id
  replicate_id
  replicate_count
  replicate_policy_ref
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
  evaluator_version_refs
  evaluator_leakage_model_ref
  scoring_refs
  result_metric_refs
  aggregation_plan_ref
  confidence_interval_policy_ref
  statistical_test_policy_ref
  effect_size_policy_ref
  power_or_precision_target_ref
  baseline_refs
  baseline_version_refs
  baseline_eligibility_policy_ref
  comparison_cohort_ref
  paired_run_group_ref
  statistical_plan_ref
  preregistration_ref
  assistance_disclosures
  scaffold_exposure_matrix_ref
  holdout_exposure_labels
  holdout_asset_digest_refs
  canary_exposure_labels
  canary_policy_ref
  contamination_audit_refs
  contamination_audit_procedure_ref
  training_corpus_disclosure_refs
  dataset_split_ref
  training_data_cutoff_ref
  participant_knowledge_cutoff_ref
  cost_trace_refs
  cost_normalization_policy_ref
  resource_trace_refs
  hardware_profile_refs
  software_profile_refs
  timeout_budget_refs
  retry_policy_ref
  exclusion_policy_ref
  exclusion_decision_refs
  artifact_immutability_refs
  environment_build_refs
```

Explicit benchmark validity claims carry:

```text
BenchmarkValidityClaim =
  BaseEnvelope
  claim_id
  claim_type
  run_context_ref
  population_scope_ref
  metric_refs
  aggregation_plan_ref
  replicate_set_ref
  unit_of_analysis_ref
  confidence_interval_ref
  statistical_test_ref
  effect_size_ref
  minimum_effect_or_margin_ref
  baseline_refs
  baseline_eligibility_policy_ref
  comparison_cohort_ref
  paired_run_group_ref
  evaluator_version_refs
  evaluator_leakage_model_ref
  exclusion_policy_ref
  exclusion_decision_refs
  retry_policy_ref
  cost_normalization_policy_ref
  contamination_audit_refs
  contamination_audit_procedure_ref
  holdout_non_exposure_evidence_refs
  canary_evidence_refs
  scaffold_exposure_matrix_ref
  artifact_immutability_refs
  conclusion_scope
  unsupported_or_unknown_limits
```

Rules:

- Repeated runs must have distinct `repeat_id` or equivalent identity.
- Comparative claims require a statistical plan, replicate identity and count,
  baseline version, evaluator version, comparison cohort, retry/exclusion
  policy, and cost/resource normalization policy.
- Statistical plans must define the unit of analysis, metric aggregation,
  uncertainty interval, effect-size or equivalence margin when relevant, and
  how paired or clustered runs are handled. A final score without these fields
  is a descriptive result, not a portable comparative claim.
- Exclusions and retries must be interpreted through the preregistered or
  otherwise disclosed policy and recorded as decision refs. Dropped failed
  attempts, evaluator crashes, manual interventions, or timeout retries cannot
  be hidden inside aggregate metrics.
- Baselines are comparable only when their participant implementation,
  scaffold/tool exposure, evaluator, scenario, cost/resource normalization, and
  allowed assistance satisfy the same eligibility policy or the mismatch is
  disclosed in the claim limits.
- Evaluator leakage claims require an evaluator leakage model, evaluator
  version refs, public/private material labels, and contamination-audit
  procedure refs. Runtime records alone do not prove that an evaluator, scaffold,
  or agent could not access hidden material.
- Artifacts used in a comparative claim must cite immutable digests or
  equivalent registry/version evidence for scenario, contract bundle, evaluator,
  baseline, scaffold, participant implementation, and backend manifest.
- Seed/randomization claims require seed refs or an unsupported/unknown
  disclosure.
- Scaffold, tool, model, policy, and human assistance exposure must be disclosed
  when used for benchmark comparison.
- Cost/resource traces may be summarized or redacted, but the loss must be
  disclosed when it affects comparison.
- Holdout and canary labels must not reveal hidden answers to participants.
  Claims about non-exposure require holdout asset digests, canary policy,
  scaffold exposure matrix, and contamination-audit evidence or a disclosed
  unsupported claim.
- Runtime records alone do not prove benchmark validity. They preserve the
  evidence needed for an external study design to make a valid comparison.

Benchmark conformance predicates:

```text
BenchmarkClaimOK(claim) =
  RunContextOK(claim.run_context_ref)
  /\ MetricsOK(claim.metric_refs, claim.aggregation_plan_ref)
  /\ ReplicationOK(claim.replicate_set_ref, claim.unit_of_analysis_ref)
  /\ UncertaintyOK(claim.confidence_interval_ref,
                   claim.statistical_test_ref,
                   claim.effect_size_ref)
  /\ BaselineComparabilityOK(claim.baseline_refs,
                             claim.comparison_cohort_ref,
                             claim.baseline_eligibility_policy_ref)
  /\ ExposureOK(claim.scaffold_exposure_matrix_ref,
                claim.holdout_non_exposure_evidence_refs,
                claim.canary_evidence_refs,
                claim.contamination_audit_refs)
  /\ CostOK(claim.cost_normalization_policy_ref)
  /\ ArtifactImmutabilityOK(claim.artifact_immutability_refs)
```

If any predicate is `Unknown` or `Unsupported`, the claim must either downgrade
to the supported conclusion scope or explicitly record
`unsupported_or_unknown_limits`.

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
- action/observation space, action mask, reward, return, termination,
  truncation, and auxiliary-info boundaries when the concrete backend exposes
  RL/MARL/game step signals;
- shared-state address, revision/digest, marking, and provenance discipline;
- realized order, clock basis, isolation guarantee, atomicity scope, conflict
  predicate, and conflict policy;
- time-management mode, lookahead, time-advance request/grant, message
  causality, step negotiation, rollback, anti-message, and supersession
  discipline when the concrete backend makes such claims;
- component-wise capability guarantee vectors and explicit downgrades;
- redaction and authorization policy before public disclosure;
- run context needed for reproducibility, benchmark, and comparative claims.

Safety properties:

- no hidden state as participant-visible observation without a visibility rule;
- no inference of causality from wall clock alone;
- no history rewrite after append;
- no unmarked sensitive field in public runtime records;
- no capability claim stronger than backend declaration and evidence;
- no conflation of opaque, unknown, not applicable, and unsupported.
- no inferred reward, return, termination, truncation, or action mask from
  hidden objective/scorer/backend internals;
- no deletion or mutation of prior records during rollback or compensation;
- no benchmark comparison claim without repetition, baseline, evaluator,
  cost-normalization, and exposure evidence required by the claim.

Liveness properties are bounded and contract-specific:

- admitted synchronous attempts either record an execution result, failure,
  rejection, or unsupported disclosure within the contract's timeout bound;
- admitted long-running operations eventually record progress, terminal state,
  timeout, cancellation, unknown, or unsupported disclosure within the declared
  operation policy;
- retry, fairness, and starvation-free claims require declared scheduler,
  retry, and bound evidence.

Future implementation issues should turn the normative core above into an
executable model or mechanically checked test harness. The minimum executable
surface is: valid trace predicate, `Apply` transition predicates, observation
reconstruction, capability meet/satisfaction, shared-state revision discipline,
interaction-context validity, benchmark-validity predicates, and
concurrency/time-management rules. TLA+/PlusCal, Alloy, state-machine property
tests, or differential tests against backend traces are acceptable realizations
only if they cover those predicates rather than rechecking schema shape alone.

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
admission, operation, observation, step-signal, shared-state, ordering,
time-management, rollback, isolation, conflict, redaction, provenance, replay,
or benchmark guarantee must reject or disclose the weaker realization.

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

A runtime claim cannot be stronger than the required effective capability
vector for lifecycle, admission, operation, observation, shared-state revision,
step signals, ordering, time management, rollback, isolation, conflict,
redaction, provenance, replay, and benchmark concerns. Downgrades are records,
not diagnostics-only warnings.

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

### I27 - RL Step Signal Separation

Action spaces, observation spaces, action masks, rewards, returns,
termination, truncation, and auxiliary info are portable only when represented
as governed step signals. They must not be inferred from objective success,
scoring state, hidden world state, backend debug fields, or participant private
policy state.

### I28 - Termination And Truncation Separation

Task terminal semantics and external truncation semantics remain separate.
Neither field is equivalent to ADR-013 episode terminal reason unless an
explicit closure record relates them.

### I29 - Information-State Reconstructability

History-consistent and perfect-recall claims require a reconstructability
procedure over visible action-observation history, projection version,
redaction policy, delivery order, and stochastic context. If that procedure is
missing or lossy, the claim must be downgraded.

### I30 - Time-Management Honesty

Claims about HLA-style time management, conservative logical time, optimistic
rollback, DEVS transitions, FMI co-simulation, or true simultaneity require the
corresponding lookahead, time-advance, message-causality, rollback, transition,
or step-negotiation evidence. Otherwise the backend may claim only the weaker
realized order it can prove.

### I31 - Capability Composition

Effective capability is the meet across all components that can weaken a
claim. A strong backend engine cannot hide a weak adapter, clock authority,
redaction policy, evidence store, observation apparatus, replay engine, or
benchmark harness.

### I32 - Benchmark Comparison Evidence

Runtime provenance is necessary but not sufficient for benchmark comparison.
Comparative claims require repetition, statistical plan, baseline/evaluator
version, cost normalization, retry/exclusion policy, scaffold exposure,
holdout/canary non-exposure evidence, and contamination-audit records as
applicable.

### I33 - Active-Agent And Chance Discipline

Sequential, AEC, simultaneous, parallel, chance, and mean-field step claims
require an interaction context. Participant actions are valid only for the
recorded active agent set and current actor; chance and mean-field nodes cannot
be silently represented as participant choices.

### I34 - Benchmark Validity Procedure

Run context is evidence, not a conclusion. A comparative or
non-contamination claim must cite a benchmark validity claim with metric,
aggregation, uncertainty, baseline comparability, evaluator leakage, exposure,
exclusion, retry, cost-normalization, and artifact-immutability procedures, or
downgrade the conclusion scope.

## Canonical Design Examples

The examples use snake_case wire-style values and complete fields for the
surface being exercised. Conditional source-alignment subobjects appear when
relevant; concrete schemas may make non-applicable subobjects explicit nulls or
omit them under a published extension policy. Raw payloads are represented by
governed refs, not omitted secrets.

### Opaque LLM Agent Action

```yaml
lifecycle_envelope:
  event_id: evt-llm-17-exec
  schema_name: aces.participant_runtime.lifecycle
  schema_version: 1.0.0
  event_type: execution_attempt
  extension_policy: reject_unknown_required
  event_classification: null
  source_status:
    status_id: 1
    status: success
    status_code: tool_call_completed
    status_detail: tool gateway accepted and completed the command
    source_status_label: tool_call_completed
    source_status_mapping: aces.lifecycle.operation_state.completed
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
  source_pipeline:
    product_ref: products.tool-gateway.red
    product_version: 2.4.1
    log_provider: tool-gateway
    log_source: tool-gateway.red
    log_name: tool-invocation
    original_event_uid: gateway-call-992
    original_time: 2026-05-26T10:15:01Z
    processed_time: 2026-05-26T10:15:02Z
    logged_time: 2026-05-26T10:15:02Z
    transmit_time: 2026-05-26T10:15:03Z
    correlation_uid: corr-tool-call-992
    sequence: 992
  raw_data_integrity:
    raw_data_hash: sha256:1111111111111111111111111111111111111111111111111111111111111111
    raw_data_hash_algorithm: sha256
    raw_data_size: 4096
    raw_data_is_truncated: false
    raw_data_untruncated_size: 4096
  confidence: 0.82
  provenance_refs:
    - provenance.participant_observed
  evidence_refs:
    - evidence.tool-call-992-redacted
  marking_definition_refs:
    - markings.internal.v1
    - markings.restricted_evidence.v1
  object_marking_refs:
    - markings.internal.v1
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
  event_classification: null
  source_status:
    status_id: 0
    status: unknown
    status_code: model_private_choice
    status_detail: selection existed inside opaque model apparatus
    source_status_label: model_private_choice
    source_status_mapping: aces.lifecycle.phase_realization.opaque
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
  source_pipeline:
    product_ref: products.llm-agent.red
    product_version: 2.4.1
    log_provider: null
    log_source: null
    log_name: null
    original_event_uid: null
    original_time: null
    processed_time: null
    logged_time: null
    transmit_time: 2026-05-26T10:15:03Z
    correlation_uid: corr-tool-call-992
    sequence: 16
  raw_data_integrity:
    raw_data_hash: null
    raw_data_hash_algorithm: null
    raw_data_size: null
    raw_data_is_truncated: null
    raw_data_untruncated_size: null
  confidence: null
  provenance_refs:
    - provenance.apparatus_boundary
  evidence_refs: []
  marking_definition_refs:
    - markings.internal.v1
  object_marking_refs:
    - markings.internal.v1
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
interaction_context_envelope:
  event_id: interaction-cyborg-tick42
  schema_name: aces.participant_runtime.interaction_context
  schema_version: 1.0.0
  event_type: interaction_context
  extension_policy: reject_unknown_required
  event_classification: null
  source_status:
    status_id: 1
    status: success
    status_code: aec_current_actor
    status_detail: AEC step exposes blue as the current actor at tick 42
    source_status_label: cyborg_aec_current_actor
    source_status_mapping: aces.interaction_mode.agent_environment_cycle
  participant_address: null
  episode_id: null
  sequence_number: null
  occurred_at: 2026-05-26T10:20:10Z
  recorded_at: 2026-05-26T10:20:10Z
  ingested_at: 2026-05-26T10:20:11Z
  clock_authority: sim.tick
  temporal_context: tick-42
  ordering_basis: simulation_tick
  logical_order_ref: order.sim.42.interaction
  predecessor_event_refs:
    - interaction-cyborg-tick41
  actor_ref: runtime.scheduler
  producer_ref: adapters.cyborg-blue.v1
  source_system_ref: cyborg.sim
  source_record_ref: cyborg.interaction.42
  source_raw_ref: evidence.raw.cyborg.interaction.42
  source_pipeline:
    product_ref: products.cyborg.sim
    product_version: 1.0.0
    log_provider: cyborg
    log_source: cyborg.sim
    log_name: interaction-context
    original_event_uid: cyborg.interaction.42
    original_time: 2026-05-26T10:20:10Z
    processed_time: 2026-05-26T10:20:10Z
    logged_time: 2026-05-26T10:20:10Z
    transmit_time: 2026-05-26T10:20:11Z
    correlation_uid: cyborg.tick42
    sequence: 42
  raw_data_integrity:
    raw_data_hash: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    raw_data_hash_algorithm: sha256
    raw_data_size: 1024
    raw_data_is_truncated: false
    raw_data_untruncated_size: 1024
  confidence: 1.0
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.interaction-cyborg-tick42
  marking_definition_refs:
    - markings.internal.v1
  object_marking_refs:
    - markings.internal.v1
  markings:
    - internal
  granular_markings: {}
  redaction_policy_ref: redaction.blue-step-signal.v1
  authorization_scope: runtime_review
  interaction_context_id: interaction.cyborg.tick42
  interaction_mode: agent_environment_cycle
  order_point: order.sim.42.interaction
  possible_agent_set_ref: agents.cyborg.possible
  active_agent_set:
    - participants.blue.rl
  current_actor_ref: participants.blue.rl
  simultaneous_group_ref: null
  nonacting_agent_policy_ref: policies.cyborg.nonacting-observe-only
  legal_action_snapshot_refs:
    participants.blue.rl: masks.blue.tick42
  chance_mode: not_applicable
  chance_distribution_ref: null
  chance_distribution_digest: null
  sampled_chance_outcome_ref: null
  chance_seed_ref: seeds.run-778-blue
  chance_visibility: not_applicable
  mean_field_population_ref: null
  mean_field_distribution_ref: null
  mean_field_distribution_digest: null
  mean_field_update_rule_ref: null
  mean_field_update_ref: null
  terminal_node: false
  unsupported_interaction_disclosure: null
observation_envelope:
  event_id: obs-blue-43
  schema_name: aces.participant_runtime.observation
  schema_version: 1.0.0
  event_type: observation_emission
  extension_policy: reject_unknown_required
  event_classification:
    category_uid: 4
    category_name: findings
    class_uid: 4001
    class_name: detection_finding
    activity_id: 1
    activity_name: telemetry_observed
    type_uid: 800101
    type_name: blue telemetry observation emitted
    severity_id: 1
    severity: informational
  source_status:
    status_id: 1
    status: success
    status_code: observation_emitted
    status_detail: simulator emitted the blue local telemetry observation
    source_status_label: cyborg_observation
    source_status_mapping: aces.observation.emitted
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
  source_pipeline:
    product_ref: products.cyborg.sim
    product_version: 1.0.0
    log_provider: cyborg
    log_source: cyborg.sim
    log_name: observation-step
    original_event_uid: cyborg.obs.42.blue
    original_time: 2026-05-26T10:20:10Z
    processed_time: 2026-05-26T10:20:10Z
    logged_time: 2026-05-26T10:20:10Z
    transmit_time: 2026-05-26T10:20:11Z
    correlation_uid: cyborg.tick42.blue
    sequence: 42
  raw_data_integrity:
    raw_data_hash: sha256:2222222222222222222222222222222222222222222222222222222222222222
    raw_data_hash_algorithm: sha256
    raw_data_size: 2048
    raw_data_is_truncated: false
    raw_data_untruncated_size: 2048
  confidence: 1.0
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.obs-blue-43-redacted
  marking_definition_refs:
    - markings.participant_visible.v1
    - markings.restricted_evidence.v1
  object_marking_refs:
    - markings.participant_visible.v1
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
  reconstruction_algorithm_ref: null
  reconstruction_proof_ref: null
  belief_support_ref: null
  redacted_field_refs:
    - /hidden_state_refs
step_signal_envelope:
  event_id: step-blue-43
  schema_name: aces.participant_runtime.step_signal
  schema_version: 1.0.0
  event_type: participant_step_signal
  extension_policy: reject_unknown_required
  event_classification: null
  source_status:
    status_id: 1
    status: success
    status_code: step_signal_emitted
    status_detail: simulator exposed governed step signal refs
    source_status_label: cyborg_step
    source_status_mapping: aces.step_signal.emitted
  participant_address: participants.blue.rl
  episode_id: ep-blue-002
  sequence_number: 43
  occurred_at: 2026-05-26T10:20:10Z
  recorded_at: 2026-05-26T10:20:10Z
  ingested_at: 2026-05-26T10:20:11Z
  clock_authority: sim.tick
  temporal_context: tick-42
  ordering_basis: simulation_tick
  logical_order_ref: order.sim.42.blue.step43
  predecessor_event_refs:
    - evt-rl-42-exec
  actor_ref: participants.blue.rl
  producer_ref: adapters.cyborg-blue.v1
  source_system_ref: cyborg.sim
  source_record_ref: cyborg.step.42.blue
  source_raw_ref: evidence.raw.cyborg.step.42.blue
  source_pipeline:
    product_ref: products.cyborg.sim
    product_version: 1.0.0
    log_provider: cyborg
    log_source: cyborg.sim
    log_name: step-signal
    original_event_uid: cyborg.step.42.blue
    original_time: 2026-05-26T10:20:10Z
    processed_time: 2026-05-26T10:20:10Z
    logged_time: 2026-05-26T10:20:10Z
    transmit_time: 2026-05-26T10:20:11Z
    correlation_uid: cyborg.tick42.blue
    sequence: 42
  raw_data_integrity:
    raw_data_hash: sha256:3333333333333333333333333333333333333333333333333333333333333333
    raw_data_hash_algorithm: sha256
    raw_data_size: 1536
    raw_data_is_truncated: false
    raw_data_untruncated_size: 1536
  confidence: 1.0
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.step-blue-43-redacted
  marking_definition_refs:
    - markings.participant_visible.v1
    - markings.restricted_evidence.v1
  object_marking_refs:
    - markings.participant_visible.v1
  markings:
    - participant_visible
  granular_markings:
    /centralized_state_refs:
      - restricted_evidence
  redaction_policy_ref: redaction.blue-step-signal.v1
  authorization_scope: participant:participants.blue.rl
  interaction_context_ref: interaction.cyborg.tick42
  active_agent_set_ref: active-agents.cyborg.tick42
  current_actor_ref: participants.blue.rl
  action_ref: actions.blue.isolate_host
  observation_ref: observations.blue.local.telemetry.43
  action_mask_ref: masks.blue.tick42
  reward_ref: rewards.blue.tick42
  return_ref: returns.blue.prefix42
  termination_ref: termination.blue.tick42
  info_refs:
    - info.blue.step42.redacted
  centralized_state_refs:
    - evidence.global-training-state.tick42
```

The action mask, reward, return, and termination refs resolve to governed
step-signal records. Policy updates, optimizer state, and model state remain
apparatus internals unless an explicit evidence contract exposes a redacted
representation.

Chance and mean-field order points use the same interaction-context envelope
with an empty `active_agent_set`; their distribution, sampled outcome, update
rule, or unsupported disclosure is recorded there rather than represented as a
participant action.

### Human-Supplied Action

```yaml
lifecycle_envelope:
  event_id: evt-human-09-admission
  schema_name: aces.participant_runtime.lifecycle
  schema_version: 1.0.0
  event_type: selection_or_admission
  extension_policy: reject_unknown_required
  event_classification: null
  source_status:
    status_id: 1
    status: success
    status_code: submitted_by_operator
    status_detail: operator submitted an admitted containment command
    source_status_label: submitted_by_operator
    source_status_mapping: aces.lifecycle.admission.admitted
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
  source_pipeline:
    product_ref: products.operator-console
    product_version: 1.8.0
    log_provider: control-plane
    log_source: operator-console
    log_name: operator-command
    original_event_uid: command-form-9
    original_time: 2026-05-26T10:30:00Z
    processed_time: 2026-05-26T10:30:02Z
    logged_time: 2026-05-26T10:30:02Z
    transmit_time: 2026-05-26T10:30:02Z
    correlation_uid: operator-command-9
    sequence: 9
  raw_data_integrity:
    raw_data_hash: sha256:4444444444444444444444444444444444444444444444444444444444444444
    raw_data_hash_algorithm: sha256
    raw_data_size: 1024
    raw_data_is_truncated: false
    raw_data_untruncated_size: 1024
  confidence: 1.0
  provenance_refs:
    - provenance.externally_supplied
  evidence_refs:
    - evidence.operator-command-9-redacted
  marking_definition_refs:
    - markings.internal.v1
  object_marking_refs:
    - markings.internal.v1
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
  event_classification: null
  source_status:
    status_id: 2
    status: in_progress
    status_code: running
    status_detail: caldera link is running
    source_status_label: running
    source_status_mapping: aces.operation_state.running
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
  source_pipeline:
    product_ref: products.caldera
    product_version: 5.1.0
    log_provider: caldera
    log_source: caldera.operation.abc
    log_name: link-state
    original_event_uid: link.1234
    original_time: 2026-05-26T10:40:30Z
    processed_time: 2026-05-26T10:40:31Z
    logged_time: 2026-05-26T10:40:31Z
    transmit_time: 2026-05-26T10:40:32Z
    correlation_uid: caldera.operation.abc.link.1234
    sequence: 55
  raw_data_integrity:
    raw_data_hash: sha256:5555555555555555555555555555555555555555555555555555555555555555
    raw_data_hash_algorithm: sha256
    raw_data_size: 8192
    raw_data_is_truncated: true
    raw_data_untruncated_size: 23142
  confidence: 0.9
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.caldera.link.1234-redacted
  marking_definition_refs:
    - markings.internal.v1
    - markings.restricted_evidence.v1
  object_marking_refs:
    - markings.internal.v1
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
  event_classification:
    category_uid: 6
    category_name: application_activity
    class_uid: 6003
    class_name: api_activity
    activity_id: 1
    activity_name: command_execution
    type_uid: 1200301
    type_name: caldera command execution context
    severity_id: 2
    severity: low
  source_status:
    status_id: 2
    status: in_progress
    status_code: running
    status_detail: caldera command context recorded while link is running
    source_status_label: running
    source_status_mapping: aces.operation_state.running
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
  source_pipeline:
    product_ref: products.caldera
    product_version: 5.1.0
    log_provider: caldera
    log_source: caldera.operation.abc
    log_name: ability-link
    original_event_uid: ability.cred-dump.link.1234
    original_time: 2026-05-26T10:40:30Z
    processed_time: 2026-05-26T10:40:31Z
    logged_time: 2026-05-26T10:40:31Z
    transmit_time: 2026-05-26T10:40:32Z
    correlation_uid: caldera.operation.abc.link.1234
    sequence: 55
  raw_data_integrity:
    raw_data_hash: sha256:6666666666666666666666666666666666666666666666666666666666666666
    raw_data_hash_algorithm: sha256
    raw_data_size: 8192
    raw_data_is_truncated: true
    raw_data_untruncated_size: 23142
  confidence: 0.9
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.caldera.link.1234-redacted
  marking_definition_refs:
    - markings.internal.v1
    - markings.secret_ref.v1
  object_marking_refs:
    - markings.internal.v1
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
  openc2_profile_ref: null
  openc2_command_id: null
  openc2_request_id: null
  openc2_action: null
  openc2_target_ref: null
  openc2_args_ref: null
  openc2_actuator_ref: null
  openc2_response_ref: null
  openc2_response_status: null
  openc2_response_status_text: null
  openc2_response_results_ref: null
  cacao_playbook_ref: playbooks.red.credential-access
  cacao_workflow_step_ref: cacao.step.credential-access.4
  cacao_workflow_step_type: command
  cacao_command_refs:
    - commands.caldera.link.1234
  cacao_agent_refs:
    - agents.caldera.red.01
  cacao_target_refs:
    - hosts.workstation01
  cacao_variable_refs:
    - variables.target_host.redacted
  cacao_authentication_ref: auth_refs.redacted.caldera-agent
  cacao_on_completion_ref: cacao.step.credential-access.5
  cacao_on_success_ref: cacao.step.credential-access.5
  cacao_on_failure_ref: cacao.step.cleanup.1
  cacao_external_refs:
    - attack.T1003
  caldera_operation_ref: caldera.operation.abc
  caldera_adversary_ref: caldera.adversary.red
  caldera_planner_ref: caldera.planner.atomic
  caldera_ability_ref: caldera.ability.cred-dump
  caldera_link_ref: caldera.link.1234
  caldera_fact_refs:
    - caldera.fact.credential-cache
  caldera_agent_ref: agents.caldera.red.01
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
  event_classification: null
  source_status:
    status_id: 1
    status: success
    status_code: conflict_rejected
    status_detail: runtime detected simultaneous shared-state conflict
    source_status_label: conflict_rejected
    source_status_mapping: aces.conflict_policy.reject
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
  source_pipeline:
    product_ref: products.cyborg.sim
    product_version: 1.0.0
    log_provider: cyborg
    log_source: cyborg.sim
    log_name: joint-action
    original_event_uid: sim.tick.88.joint
    original_time: 2026-05-26T10:50:00Z
    processed_time: 2026-05-26T10:50:01Z
    logged_time: 2026-05-26T10:50:01Z
    transmit_time: 2026-05-26T10:50:01Z
    correlation_uid: sim.tick.88
    sequence: 88
  raw_data_integrity:
    raw_data_hash: sha256:7777777777777777777777777777777777777777777777777777777777777777
    raw_data_hash_algorithm: sha256
    raw_data_size: 3072
    raw_data_is_truncated: false
    raw_data_untruncated_size: 3072
  confidence: 1.0
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.sim.tick88.joint
  marking_definition_refs:
    - markings.internal.v1
  object_marking_refs:
    - markings.internal.v1
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
  time_management_context_ref: time.sim.tick88
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
time_management_context:
  event_id: time-sim-88
  schema_name: aces.participant_runtime.time_management
  schema_version: 1.0.0
  event_type: time_management_context
  extension_policy: reject_unknown_required
  event_classification: null
  source_status:
    status_id: 1
    status: success
    status_code: time_grant_recorded
    status_detail: logical time advance evidence recorded for tick 88
    source_status_label: time_grant_recorded
    source_status_mapping: aces.time_management.devs_discrete_event
  participant_address: null
  episode_id: null
  sequence_number: null
  occurred_at: 2026-05-26T10:50:00Z
  recorded_at: 2026-05-26T10:50:01Z
  ingested_at: 2026-05-26T10:50:01Z
  clock_authority: sim.tick
  temporal_context: tick-88
  ordering_basis: simulation_tick
  logical_order_ref: sim.tick.88
  predecessor_event_refs:
    - joint-12
  actor_ref: runtime.scheduler
  producer_ref: backend.cyborg-adapter.v1
  source_system_ref: cyborg.sim
  source_record_ref: sim.tick.88.time
  source_raw_ref: evidence.raw.sim.tick88
  source_pipeline:
    product_ref: products.cyborg.sim
    product_version: 1.0.0
    log_provider: cyborg
    log_source: cyborg.sim
    log_name: time-management
    original_event_uid: sim.tick.88.time
    original_time: 2026-05-26T10:50:00Z
    processed_time: 2026-05-26T10:50:01Z
    logged_time: 2026-05-26T10:50:01Z
    transmit_time: 2026-05-26T10:50:01Z
    correlation_uid: sim.tick.88
    sequence: 88
  raw_data_integrity:
    raw_data_hash: sha256:8888888888888888888888888888888888888888888888888888888888888888
    raw_data_hash_algorithm: sha256
    raw_data_size: 3072
    raw_data_is_truncated: false
    raw_data_untruncated_size: 3072
  confidence: 1.0
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.sim.tick88.time
  marking_definition_refs:
    - markings.internal.v1
  object_marking_refs:
    - markings.internal.v1
  markings:
    - internal
  granular_markings: {}
  redaction_policy_ref: redaction.shared-state.v1
  authorization_scope: runtime_review
  time_context_id: time.sim.tick88
  time_domain: simulation_tick
  time_management_mode: devs_discrete_event
  logical_time: 88
  simulation_time: tick-88
  wall_clock_interval: null
  lookahead: 1_tick
  time_regulating: true
  time_constrained: true
  time_advance_request_ref: time-request.tick88
  time_advance_grant_ref: time-grant.tick88
  next_event_request_ref: null
  message_send_refs:
    - msg.red.88.action
    - msg.blue.88.action
  message_receive_refs:
    - msg.runtime.88.conflict-result
  pacing_policy_ref: sim.pacing.logical
  step_size_ref: step.tick.1
  rollback_window_ref: null
  rollback_refs: []
  anti_message_refs: []
  compensation_refs: []
  superseded_event_refs: []
  transition_basis: confluent
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
  event_classification: null
  source_status:
    status_id: 2
    status: weak_guarantee
    status_code: backend_serialized
    status_detail: backend serialized the attempts and cannot prove simultaneity
    source_status_label: backend_serialized
    source_status_mapping: aces.conflict_policy.disclose_weak_guarantee
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
  source_pipeline:
    product_ref: products.backend.scheduler
    product_version: 3.2.0
    log_provider: backend
    log_source: backend.scheduler
    log_name: scheduler-order
    original_event_uid: scheduler.log.21
    original_time: 2026-05-26T11:00:00Z
    processed_time: 2026-05-26T11:00:02Z
    logged_time: 2026-05-26T11:00:02Z
    transmit_time: 2026-05-26T11:00:03Z
    correlation_uid: scheduler.window.21
    sequence: 21
  raw_data_integrity:
    raw_data_hash: sha256:9999999999999999999999999999999999999999999999999999999999999999
    raw_data_hash_algorithm: sha256
    raw_data_size: 6144
    raw_data_is_truncated: false
    raw_data_untruncated_size: 6144
  confidence: 0.7
  provenance_refs:
    - provenance.backend_realized
  evidence_refs:
    - evidence.backend-scheduler-log-21
  marking_definition_refs:
    - markings.internal.v1
  object_marking_refs:
    - markings.internal.v1
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
  time_management_context_ref: time.backend.window21
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
- RL/MARL step signals are recorded as action/observation space, action-mask,
  reward, return, termination, truncation, and auxiliary-info records when a
  backend exposes them;
- RL/MARL/game interaction context records preserve active-agent/current-actor,
  simultaneous, chance-node, and mean-field update semantics when claims depend
  on them;
- information-state claim strength is explicit for each participant-visible
  observation;
- opaque participant phases are recorded honestly as unknown or not exposed
  rather than fabricated;
- benchmark run context is present when runtime records support comparison or
  reproducibility claims;
- explicit benchmark validity claims are present when runtime records are used
  for comparative, non-contamination, or cost-normalized conclusions.

Future implementation artifacts:

- versioned participant runtime state/history envelopes;
- base envelope fields for schema version, event type, source refs, markings,
  and temporal context;
- operation record model for asynchronous actions;
- step-signal contract models for action masks, rewards, returns,
  termination/truncation, and auxiliary info;
- schema publication through `aces_contracts`;
- validation that history references known participant, episode, action,
  operation, observation, and shared-state addresses;
- validation that hidden truth, scoring state, and centralized-training state
  are not exposed as participant-visible observations without projection rules;
- validation that rewards, returns, action masks, and terminal/truncation
  signals cannot be inferred from hidden scorer/backend state;
- validation that comparative benchmark conclusions cite metric aggregation,
  uncertainty, baseline comparability, evaluator leakage, exposure, exclusion,
  retry, cost-normalization, and artifact-immutability procedures;
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
- step signals preserve RL/game-facing rewards, returns, masks,
  termination/truncation, and info without requiring participant internals;
- AEC/current-actor, simultaneous active-agent, chance, and mean-field node
  semantics are separate interaction-context records, not inferred from final
  observations or action lists;
- the lifecycle is separate from episode lifecycle, workflow state, evaluator
  state, control-plane operation status, and participant internals.

Future implementation artifacts:

- lifecycle phase, phase-realization, admission-disposition, and operation-state
  vocabulary;
- runtime event envelope linking lifecycle phase, action contract, participant,
  episode, temporal context, operation, observation, and state update;
- runtime step-signal envelope linking action attempts, observations, action
  masks, rewards, returns, termination, truncation, and info refs when present;
- interaction-context envelope for sequential/AEC, simultaneous, chance, and
  mean-field order points;
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
- distributed-simulation concurrency additionally records time-management mode,
  lookahead, time-advance grants, message causality, rollback/anti-message or
  step-negotiation semantics when those claims are made;
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
  observation, step-signal, shared-state, ordering, time-management, rollback,
  isolation, conflict, redaction, provenance, replay, and benchmark concerns;
- property or differential tests for serialized versus simultaneous conflicting
  attempts;
- model-checkable or executable state-machine tests for ordering/isolation,
  rollback, and time-management claims;
- model-checkable or property tests for active-agent/current-actor, chance, and
  mean-field claim validity where those surfaces are implemented;
- conformance checks for missing order/revision/conflict/isolation metadata;
- backend capability evidence for supported concurrency guarantees.

## Primary Reference Surface

This design should be reviewed against the source map in
`docs/explain/sdl/lineage.md` and, at minimum, these primary reference
families:

- Gymnasium/OpenAI Gym, PettingZoo, and OpenSpiel for action spaces,
  observation spaces, rewards, returns, termination/truncation, action masks,
  per-agent histories, active-agent/current-actor state, chance nodes,
  mean-field updates, simultaneous moves, and information-state discipline.
- POMDP, Dec-POMDP, POSG, and Markov-game literature for partial observability
  and multi-agent information boundaries.
- CybORG, CyberBattleSim, CyGIL, CALDERA, ATT&CK, OpenC2, and CACAO for cyber
  action, sensing, command/response, playbook, knowledge, foothold, detection,
  and sim-to-emulation realization disclosure.
- OCSF and STIX for event classification, normalized status/severity, schema
  versioning, source/raw mapping, confidence, markings, granular selectors, and
  extension discipline.
- Lamport clocks, IEEE HLA time management, Time Warp, DEVS, FMI, and related
  distributed-simulation work for order, time advance, lookahead, rollback,
  pacing, and synchronization.
- Cybench, AutoPenBench, CAIBench, AI Agents That Matter, and offensive
  security benchmark-methodology work for run records, repeated trials,
  baseline/evaluator disclosure, cost normalization, scaffold exposure,
  contamination audits, and holdout/canary discipline.

## Non-Goals

- Defining new SDL participant syntax.
- Implementing participant runtime contracts or backends in this issue.
- Requiring participants to reveal chain-of-thought, prompts, policy internals,
  reward updates, private memory, or tool traces.
- Treating backend-native stores, logs, timestamps, or scheduler order as the
  portable runtime semantics.
- Treating hidden reward calculators, policy optimizer state,
  centralized-training state, model internals, or scorer state as participant
  runtime semantics. Participant-visible reward and return signals are portable
  only through governed step-signal records.
- Defining a solver, policy optimizer, reward-learning API, centralized-training
  protocol, or training framework API.
- Redesigning full archival study management beyond the runtime fields needed
  to preserve participant history, shared-state evidence, and reproducibility
  claims.
