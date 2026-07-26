# ADR-092: Autonomous Benign Participants Under Shared Time

## Status

accepted

## Date

2026-07-24

## Classification

Classification: FM3

Required artifacts: authority-boundary decision, formal invariants, authored
schema, semantic validation, canonical compilation, capability admission,
runtime execution/readback, negative tests, lineage, and traceability.

Waivers: none.

## Context

Scenarios need ordinary user and automation activity to interact with real
services while evaluated participants operate. Deterministic activity is still
participant behavior: its implementation may be a script, agent, simulator, or
external service, but determinism does not create a new actor ontology.

The prior live-activity prototype introduced parallel actor, scheduler, and
historical-data concepts. That would duplicate participant semantics, bypass
the shared time authority, and make scenario-pack control conventions part of
the language. It would also let a capability declaration stand in for evidence
that a native service action actually ran.

## Decision

### 1. Reuse ordinary participant semantics

Autonomous benign activity is authored under
`ParticipantBehaviorSpecification.autonomous_execution`. It resolves existing
agents, participant action contracts, observation boundaries, implementation
selection, and behavior history. Non-evaluated autonomous participants must
have the existing `green` role.

### 2. Separate evaluation authority

Every autonomous execution policy declares evaluation authority. Mode `none`
forbids objective assignment, outcome-interpretation bindings, authority scope,
and score, proof, or receipt authority. Evaluated participants use `declared`
authority and resolved evaluator-plane references. The initial contract
resolves objective authority; proof, score, and receipt authority fail closed
until ACES defines declaration namespaces for them. Action execution never
implies evaluation authority.

### 3. Use the shared time model

Policies resolve one shared clock and progression policy plus exactly one
cadence constraint and any additional temporal constraints. Pause, resume, and
reset follow the shared clock lifecycle. Reset starts a new participant episode
and clears scheduler counters at the new time segment. Cadence starts must be
non-negative, and stepped cadence points must be reachable from `step_ticks`.
RuntimeManager owns automatic wall pacing for real-time and dilated policies
only when the clock declares runtime authority. It rechecks clock state after
every wait and does not relinquish an active driver thread during lifecycle
replacement. Externally paced autonomous policies fail closed until ACES
defines a portable backend transition-notification contract.

The scheduler adds no private clock, timestamp authority, or causality claim.
Every admitted action carries all bound temporal contexts into append-only
participant behavior history.

### 4. Require native execution and typed readback

The reference runtime selects actions deterministically using `ordered_cycle`
when the shared clock reaches each due tick. The backend participant runtime
must resolve the run-selected implementation and native target binding before
the native action hook operates on real services. Native action outcome is
distinct from control-plane operation success and precedes portable behavior
history. Scheduler state carries the exact policy digest and time segment,
persists through durable and conformance snapshots, preserves only unchanged
resolved policy and time declarations, and resets only through governed
lifecycle control. Scheduler checks govern direct protocol implementations as
well as reference-base subclasses. Invalid or contradictory native outcomes,
wrong result types, and missing matching terminal history do not commit the
native snapshot or portable history and consume their action-instance attempt
so they cannot be replayed. Durable state must agree with the bound clock
segment/lifecycle and live participant episode on save, load, API conversion,
and conformance assessment. One participant has exactly one autonomous
scheduler owner.
Each accepted action must append exactly one ordered
`action_attempted`/`state_transition_recorded`/`observation_emitted` sequence
whose actor provenance matches the selected participant implementation.

### 5. Admit capability fail closed

Backend manifests must declare autonomous execution, supported selection
strategies, exact action contracts, observation boundaries, target addresses,
required participant features, and finite participant, action-attempt, and
in-flight limits. Reset-capable policies additionally require
`supports_coordinated_participant_reset`; runtime-target registration requires
the time authority's atomic `reset_with_participants` method and the participant
runtime's atomic `reset_many` method. These operations are represented by
capability-specific protocols rather than imposed on every time or participant
runtime. A failed method must leave the clock and participant backends
unchanged; replacing a local snapshot is not rollback evidence. Runtime-target
registration also requires the native autonomous binding method. Planning
rejects a model outside those claims. A
declaration permits admission; only native execution plus typed outcome,
history, scheduler state, and backend evidence supports a realization claim.
Participant runtimes that add native reset behavior must implement their own
atomic batch operation; they cannot inherit the reference in-memory
transaction as evidence that their additional native state rolls back.

### 6. Keep run apparatus and scenario content in their existing planes

Participant implementation identity and configuration remain run-apparatus
concerns. Stochastic implementations use the existing governed random-stream
and experiment apparatus contracts; the deterministic `ordered_cycle`
scheduler needs no seed field. Historical files remain ordinary initial service
state. Exercise injects remain orchestration, not simulated users.

### 7. Extend autonomous execution through a versioned activity policy

The fixed-cadence `participant-autonomous-execution/v1` profile remains
unchanged. Richer admitted behavior is a new profile variant under the same
`ParticipantBehaviorSpecification.autonomous_execution` authority, not
optional fields that silently change v1 meaning and not a second activity
root.

The richer profile composes:

- inclusion and pause windows that resolve existing shared-time `window`
  constraints on the policy clock;
- positive bounded logical-tick timing intervals and cooldowns;
- stable keyed action candidates with exact integer weights, explicit
  dependency guards, portable failure-class retry rules, and finite burst,
  retry, attempt, and in-flight bounds; and
- a reference to an admitted run/apparatus stochastic control whose role is
  `agent-policy`.

It reuses the governed random-stream engine and publishes a new immutable
profile/address variant when participant-runtime coordinates or transforms are
needed. A participant draw address is based on the run randomness namespace,
policy and participant addresses, shared-time segment/reset generation,
occurrence ordinal, governed draw purpose, and stable local draw coordinate.
It does not relabel experiment selection-policy or variation-point fields, use
the aggregate scenario/experiment digest, or include worker, thread, host,
wall-time, retry, or call-order coordinates. Exact weighted choice and bounded
timing reuse the admitted bounded-integer transform. Their canonical range and
prefix-interval mappings are policy semantics with conformance vectors; they
are not new random transforms or library RNG behavior.

Within-run activity draws are not scenario-family selection, factor
allocation, or trial compilation. SDL declares the activity policy and a
stochastic-control reference; admitted run apparatus supplies the exact
profile, namespace, and public seed or governed entropy reference. Raw entropy
never enters SDL, compiled addresses, snapshots, behavior history, diagnostics,
logs, argv, or telemetry.

Scheduler continuation remains typed autonomous participant state. Append-only
behavior history carries occurrence, selection, timing, dependency, attempt,
terminal outcome, and safe random-draw provenance. Reset creates a new
shared-time segment and participant episode, starts a new scheduler generation,
and preserves predecessor lineage; it does not infer rollback of service state
or causality from timestamps. Backend admission is exact for profile, policy
features, selection strategy, random-stream profile/transform support, time
constraint kinds, and finite limits.

## Consequences

- Human, AI, scripted, and benign simulated participants share one semantic and
  runtime path.
- Scenario packs state portable policy but do not define control APIs.
- Backends can implement any scheduler/worker architecture that preserves the
  declared controls and observable contracts.
- The reference implementation proves protocol behavior, not production
  backend fidelity or throughput.
- Existing v1 policies retain fixed-cadence `ordered_cycle` semantics. Consumers
  opt into the richer profile explicitly and fail closed when any activity
  feature or governed random-stream profile is unsupported.

## Rejected Alternatives

- A background-actor or live-activity ontology parallel to participants.
- A private live-activity clock or scheduler lifecycle.
- Treating deterministic user actions as injects.
- Making historical content a first-class temporal concept.
- Adding a seed field to a deterministic scheduler that performs no random
  draws.
- Inferring native execution from a backend capability boolean.
- Adding activity-policy fields to v1 and changing its existing meaning.
- Reusing experiment variation-point address fields as participant occurrence
  coordinates.
- Adding a weighted-choice random transform when the governed bounded-integer
  transform plus a canonical policy mapping already expresses the choice.
- A mutable or process-global RNG, host-local calendar, cron expression, or
  wall-clock sleep as participant semantic authority.

## Amendments

| Date | Commit/PR | Summary |
|------|-----------|---------|
| 2026-07-24 | #861 | Required exact action provenance and capability-specific atomic participant batching. |
| 2026-07-26 | #897 | Kept v1 stable and governed richer within-run timing, weighted selection, lifecycle state, and provenance as a versioned autonomous-execution profile. |
