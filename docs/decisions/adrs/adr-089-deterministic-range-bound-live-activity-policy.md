# ADR-089: Deterministic Range-Bound Live Activity Policy

## Status

accepted

## Date

2026-07-24

## Classification

Classification: FM2

Required artifacts: an explicit invariant list, pure finite-graph analyzers,
composition and instantiation differential tests, deterministic occurrence
identity vectors, bounded-schedule and budget tests, published schema parity,
and negative participant-proof tests.

Waivers: no model checker is required. Activity dependency graphs, schedules,
budget envelopes, and target bindings are finite and scenario-local;
exhaustive graph passes and property-oriented tests cover their invariants.

## Context

Ranges need authentic ordinary enterprise activity against real services.
Participant behaviors, exercise events, workflows, runtime scheduled-job
inventory, and backend orchestration have different owners and cannot serve as
a portable background-activity authority.

Activity must be deterministic enough to reproduce and audit, bounded enough
to preserve participant capacity, and isolated enough that background actions
cannot satisfy participant objectives or create participant receipts. It must
also compose with ADR-087 deployment tenancy and reset ownership and ADR-088
historical baseline identity rather than introduce parallel tenant, baseline,
or lifecycle state.

Provider commands, request bodies, credentials, endpoints, native object ids,
adapter options, wall time, and worker state would make authored meaning
provider-specific, unsafe, or nondeterministic.

## Decision

1. SDL adds separate keyed reusable activity templates and bound activity
   profiles. Templates own provider-neutral action meaning, required
   protocol-operation capability, admissible parameter shape, and readback
   class. Profiles own actors, template actions, logical schedules,
   dependencies, targets, execution contexts, budgets, lifecycle policy, and
   telemetry requirements.
2. A background actor explicitly references existing organizational, account,
   and deployment-tenant intent. It is not an SDL `Agent`, participant
   implementation, authenticated control-plane caller, or objective actor.
   Admission proves that background actors and their entity bindings are
   disjoint from participant agents and participant execution authorities.
3. Each action references one existing named service and one closed execution
   context. The target must be governed by a native materialization binding in
   the referenced ADR-088 baseline, including that product's ADR-087 reset
   owner. Portable context contains tenant/account scope, target, governed
   protocol capability, and safe reference policy only. Commands, URLs,
   headers, bodies, queries, credentials, environment maps, provider ids,
   native handles, and opaque options are unrepresentable.
4. Template capability requirement, backend-manifest support, selected native
   adapter, execution result, normalized readback, and evidence remain
   separate facts. Portable authoring owns only the requirement and logical
   target/context. Support defaults to false and exact incompatible or
   unsupported capability agreement fails admission.
5. An authored action has its normal ADR-076 declaration address. A realized
   occurrence has a separate versioned deterministic identity over a closed
   canonical record containing deployment tenant, reset generation, activity
   contract/profile digest, ADR-088 historical baseline digest, logical time
   and stable ordinal, action and target/context identities, public seed or
   governed entropy-reference identity, and every behavior-affecting profile
   version.
6. Occurrence identity uses RFC 8785/JCS and a profile-specific
   domain-separated digest. Wall time, process/worker identity, retry count,
   queue order, backend availability, native ids, and readback values are
   forbidden inputs. Stochastic choices use the accepted stateless governed
   random-stream profile through an activity-specific versioned address, not a
   cursor RNG or the trial-specific `StreamAddressModel`.
7. Logical schedules declare an explicit time domain, anchor, finite horizon
   or occurrence bound, stable recurrence/ordinal rule, and intensity
   envelope. Open-ended recurrence, unbounded fan-out or retry, non-positive
   intervals, and rates without exact integer/rational units and windows fail
   admission.
8. Action dependencies are explicit typed edges. One pure semantic analyzer
   owns resolution and acyclicity using the central declaration index and
   shared graph helpers. Compiled ordering must agree with existing planner
   dependency, refresh, and reverse-teardown semantics; consumer references do
   not imply hidden ordering edges.
9. Budgets are closed hierarchical ceilings, not mutable counters. Per-action
   demand, per-range capacity, fleet capacity, and participant-reserved
   capacity have explicit scope, dimension, unit, and window. Participant
   reserve is deducted before background capacity. Scenario admission proves
   local consistency; fleet admission proves selected-range aggregate
   feasibility.
10. Activity lifecycle policy reacts to existing range start/resume, pause,
    drain, reset-generation advance, and teardown events. It defines new-work,
    in-flight, finite-drain, and pending-work dispositions without creating a
    second scheduler or lifecycle state machine. Advancing generation
    invalidates stale occurrences and readbacks; pause/resume does not mint a
    generation.
11. Readback and telemetry are provenance-bearing observations, never authored
    truth or participant proof. Correlation includes target, tenant, reset
    generation, occurrence identity, adapter identity/version, observation
    source, transformation/loss/redaction, and activity/baseline digests.
    Activity state cannot create participant receipts, objective truth,
    scores, or behavior history without a separate explicit governed
    projection.
12. Module composition rewrites every new declaration and reference through
    the canonical catalogs. Instantiation removes every permitted variable and
    reruns the complete semantic pass. Published scenario schemas, fixtures,
    invariant disclosures, language metadata, catalogs, and lineage move
    together.
13. This decision adds portable authoring, deterministic identity, and pure
    validation only. It adds no scheduler, worker pool, fleet orchestrator,
    product client, credential broker, direct database mutator, PCAP replayer,
    health-check generator, durable occurrence store, listener, or participant
    receipt authority.

## Alternatives Considered

### Reuse participant behaviors or exercise events

Rejected. Those contracts own participant and exercise truth. Reuse would let
ordinary background actions enter scoring, receipt, and objective authority.

### Treat runtime scheduled jobs as authored activity

Rejected. Scheduled-job inventory is observed native state and cannot own
portable intent, deterministic generation, tenant isolation, or budgets.

### Put native requests in provider options

Rejected. Commands, URLs, payloads, credentials, and opaque maps bypass
portable capability and safety policy and make semantic identity
provider-specific.

### Use wall-clock cron and mutable token buckets

Rejected. Scheduler order and mutable global counters cannot provide stable
occurrence identity, bounded replay, generation isolation, or participant
capacity guarantees.

### Add a second reset or telemetry authority

Rejected. ADR-087 already owns deployment reset generation, and existing
runtime/evidence contracts already own observation and provenance.

## Consequences

### Positive

- Ordinary enterprise activity has one portable, composition-safe authority.
- Occurrences are reproducible, baseline-bound, tenant/generation isolated,
  and capability-governed.
- Finite schedules and participant reservations prevent background load from
  consuming the range without an explicit budget.
- Background telemetry cannot silently become participant proof.

### Negative

- Authors must provide explicit actors, finite schedules, dependencies,
  capability requirements, target contexts, lifecycle policy, readback, and
  budget envelopes.
- New protocols, schedule forms, resource dimensions, readback projections,
  or adapters require coordinated versioned profile work.
- Operational scheduling and native execution remain separate implementation
  work.

### Limits

An admitted activity profile proves portable intent, boundedness, deterministic
identity material, and semantic consistency only. It does not prove that a
scheduler ran, a native action succeeded, product state matches authored
intent, telemetry is complete, participant capacity was available at runtime,
or two adapters are behaviorally equivalent.

## Amendments

| Date | Commit/PR | Summary |
| --- | --- | --- |
| 2026-07-24 | #861 | Clarified that each execution context may target any native materialization binding in its causal baseline and inherits that binding's product-specific reset ownership. |
