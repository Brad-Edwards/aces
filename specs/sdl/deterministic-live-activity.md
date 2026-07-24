# Deterministic Live Activity

This specification is the normative SDL authority for provider-neutral,
range-bound live activity. It implements
[ADR-089](../../docs/decisions/adrs/adr-089-deterministic-range-bound-live-activity-policy.md)
and reuses the deployment identity, reset ownership, and historical-baseline
authorities established by ADR-087 and ADR-088.

## Authoring authority

`activity_templates` and `activity_profiles` are optional, separate maps keyed
by stable SDL identities. A template is reusable action meaning: a versioned
protocol-operation capability, a closed map of safe reference parameter kinds,
and a readback class. It contains no target, account, schedule, endpoint,
request payload, credential, command, provider option, or execution state.

Every profile MUST reference one existing `historical_baselines` declaration.
The profile derives its range instance, deployment tenant, deployment cell,
reset generation, range-level reset owner, binding-level native reset owners,
and exact
`aces-historical-baseline-digest/v1` value from that baseline. A profile MUST
NOT redeclare or override those authorities.

## Actors, contexts, and targets

A profile actor MUST name an existing entity, account, deployment tenant, and
one or more existing operating scopes. Its entity and account MUST be disjoint
from participant `agents` and participant entity/account bindings. Activity
actors are not participants, control-plane callers, receipt issuers, or
objective actors.

An execution context MUST name the same tenant, one actor-owned account, and
one existing `nodes.<node>.services.<service>` target in the baseline's
deployment cell. The target MUST be the exact service named by one of the
baseline's native materialization bindings, which carries that product's
ADR-087 reset-owner relationship. Its protocol MUST agree with the bound
template capability.

Actions bind one template, actor, context, schedule, safe parameter references,
and bounded retry policy. Parameter values MUST resolve in the domain declared
by the template parameter kind. Portable declarations MUST NOT contain native
endpoints, URLs, commands, request bodies, queries, headers, environment maps,
credentials, product ids, scheduler options, worker ids, client settings,
broker settings, store settings, or receipt authority.

## Finite schedules and dependencies

Every schedule uses `finite-logical-schedule/v1`, the `logical` time domain, a
non-negative integer anchor, a positive integer duration interval, and a
positive bounded `max_occurrences`. An optional positive horizon can further
reduce the occurrence count. The count is:

```text
min(max_occurrences, ceil(horizon_seconds / interval_seconds))
```

when a horizon exists, and `max_occurrences` otherwise. Wall time, cron syntax,
unbounded recurrence, and scheduler order have no authored meaning.

Dependencies are explicit `ordering` or `refresh` edges between profile-local
actions. All endpoints MUST resolve, self-edges and duplicate typed edges MUST
fail, and the combined graph MUST be acyclic. Compiled forward and reverse
orders use the shared dependency-graph semantics. References alone create no
hidden ordering edge.

Retries have a positive interval and `max_attempts` in the closed range 1
through 64. Retry number, queue order, and runtime availability do not enter
occurrence identity.

## Exact budget envelopes

Each budget has one closed resource dimension and matching unit, a positive
integer window, per-action demand, range capacity, fleet capacity, and
participant reservation. Every quantity is an exact non-negative rational in
lowest terms.

Every action MUST have exactly one positive demand in every declared dimension.
Range capacity MUST fit fleet capacity, and participant reservation MUST fit
range capacity. Each demand and their aggregate MUST fit
`range_capacity - participant_reservation`. These values are immutable
ceilings, not runtime counters. Multi-range fleet admission MUST additionally
prove that selected range capacities fit fleet capacity.

## Deterministic identities

The compiled profile digest is the RFC 8785/JCS serialization of a closed
record containing the profile id, full typed profile, and exact ADR-088
historical-baseline digest. SHA-256 is applied after the domain bytes
`aces-live-activity|profile-digest|v1` followed by a zero byte.

Each occurrence identity contains:

- deployment tenant id, range instance id, and reset generation id;
- compiled activity digest and ADR-088 historical-baseline digest;
- logical time and stable occurrence ordinal;
- canonical action, template, execution-context, and target-service ids;
- either the public seed identity or governed entropy-reference identity; and
- random-stream, schedule, transform, and activity-address profile versions.

The closed occurrence record is serialized with RFC 8785/JCS. SHA-256 is
applied after `aces-live-activity|occurrence-identity|v1` followed by a zero
byte, and the published value uses the `lao1:` prefix. Declaration order,
wall time, backend identity, process or worker identity, retry count, queue
position, native ids, and readback values MUST NOT enter either digest.
Duplicate canonical coordinates or digest collisions MUST fail atomically.
The historical `hsa1:` address profile MUST NOT be reused for activity.

Random choices use `blake3-xof-v1`,
`activity-random-address/v1`, and `bounded-integer/v1` with either a fixed-width
public seed or a versioned governed entropy reference. No mutable cursor RNG is
part of this contract.

## Lifecycle and evidence

Profiles use existing range lifecycle and reset-generation semantics:
start/resume admit new work, pause suspends new work, drain is finite, reset
advance discards stale work, and teardown discards pending work. Pause/resume
does not mint a generation. An occurrence or readback from a prior generation
MUST be rejected as stale.

Readback and telemetry bind existing scenario-native observability and evidence
requirements. They carry target, tenant, generation, occurrence, adapter,
source, transform/loss/redaction, activity digest, and baseline digest
provenance. They are evidence only: `participant_proof`,
`emits_participant_receipts`, and `establishes_objective_truth` are fixed false.

## Compilation and backend admission

`RuntimeModel` carries only compiled profiles, profile digests, exact reused
baseline digests, action ordering, and typed identity coordinates. Compilation
MUST NOT enumerate occurrences or scheduler jobs and MUST NOT create planned
resources.

A backend that supports live activity MUST publish an optional
`capabilities.live_activity` block. Admission requires exact support for the
contract, protocol-operation, schedule, readback, lifecycle, resource
dimension, dependency, bounded retry, generation lifecycle, participant
reservation, and readback provenance surfaces used by the scenario. Missing or
partial support fails closed. Realization lowers every action target to an
exact SEM-218 service requirement; capability support alone is not realization.

Module composition namespaces both top-level maps and all nested declaration
addresses, rewrites external references through canonical symbol maps, and
keeps profile-local ids local. Instantiation may defer permitted scalar or
reference values but MUST re-run every invariant after substitution.

Documents that omit both sections retain empty maps and unchanged behavior.
