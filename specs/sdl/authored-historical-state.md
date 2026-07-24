# Authored Historical State

This specification is the normative SDL authority for versioned historical
baselines and provider-neutral native materialization intent. It implements
[ADR-088](../../docs/decisions/adrs/adr-088-authored-historical-state-and-native-materialization.md)
and is subordinate to ADR-087 for tenant, shared-service state, and reset
ownership.

## Historical baseline authority

`historical_baselines` is an optional map keyed by stable SDL identity. Each
baseline MUST declare an explicit semantic version, the fixed
`aces-historical-semantic-address/v1` address profile, the fixed
`logical-order/v1` history-time profile, a portable range-instance id, one
deployment tenant and cell, one reset-generation id, and one ADR-087
shared-service relationship that owns that reset generation.

The baseline is authored desired state. It is not an experiment comparison
baseline, runtime reconciliation snapshot, participant history, runtime
inventory, product export, persistent-volume snapshot, materialization result,
or evidence that a product accepted the state.

Baseline-local `actors` bind a role to exactly one incumbent `entities`,
`agents`, `accounts`, or named `nodes.*.services.*` declaration. The binding
MUST NOT copy identity data or imply exercise, product, or control-plane
authorization.

## Objects and relationships

`objects` is a non-empty map of portable local ids. Each object declares one
closed kind, one baseline-local writer actor, bounded display metadata, an
optional `content_ref`, and a non-secret sensitivity. The local id is the
semantic identity. Native ids, product names, labels, bodies, timestamps,
adapter options, and declaration order MUST NOT supply identity.

Historical object links MUST use the existing top-level `relationships`
section with:

- `type: historical_object_link`;
- source and target set to distinct canonical
  `historical_baselines.<baseline>.objects.<object>` addresses;
- one closed `historical_object_link.kind`; and
- no free-form `properties`.

Each such relationship MUST be listed by exactly one baseline. Ordinary object
relationships do not establish event causality.

## Logical history

`events` is a finite non-empty map. Every event has a unique non-negative
logical `order`, an operation, one local actor, one or more local object refs,
and optional predecessor and causal refs. Display instants and relative offsets
are presentation facts only.

The predecessor and causal graphs MUST resolve inside one baseline, MUST be
acyclic, and MUST point to strictly earlier logical coordinates. Parse order,
map iteration, display time, wall time, product time, materialization order,
and shared actors MUST NOT establish order or causality.

Every object MUST have exactly one create event. Mutation, linkage, unlinkage,
and deletion require a live object. Deletion prevents later use until an
explicit restore. Every event touching an object MUST agree with its declared
single writer. Every owned relationship MUST have exactly one link event, whose
object refs exactly match the relationship endpoints.

## Materialization and ownership

`materialization_bindings` maps one or more objects to:

- one exact existing `nodes.<node>.services.<service>` target;
- one closed versioned provider-neutral interface profile;
- the same deployment tenant and cell as the baseline;
- one ADR-087 reset-owner relationship from that tenant to the binding's exact
  native target service;
- explicit binding-order dependencies; and
- one or more local readback requirement refs.

Every object MUST have exactly one binding. The interface profile MUST support
the object's closed kind. Binding dependencies MUST be acyclic. The baseline
reset owner governs range-level lifecycle; each binding reset owner MUST be
`uses_shared_service`, MUST originate at the baseline tenant, MUST declare a
non-`none` reset-generation owner, and MUST target that binding's exact service.
This permits one causal baseline to span multiple real product services.

A backend claiming authored historical-state support MUST publish a
`capabilities.historical_state` block in its backend manifest with the exact
closed interface profiles and object kinds it supports. This declaration does
not establish SEM-218 exact realization support by itself.

Bindings describe portable operation classes only. Provider ids, endpoints,
queries, SDK types, tables, commands, credentials, option maps, product-native
ids, and adapter selection are forbidden. A binding is not a plan resource or
realization claim.

## Readback

`readback_requirements` names one local object, one or more existing
`assertions`, one participant `observation_boundary`, a closed projection
profile, and an observation point. Every referenced assertion MUST be an
invariant or postcondition over an observed-state proposition whose subject
set contains the exact canonical semantic object address. Existing proposition
evidence requirements and participant projection/redaction semantics apply.

Unsupported product semantics remain unsupported. Missing, stale, conflicting,
redacted, or inadequate evidence remains unknown. A passed readback is not a
claim of native equality, history equivalence, backend equivalence, or
bisimulation.

## Semantic addresses

For address profile `aces-historical-semantic-address/v1`, the complete typed
coordinate is:

```text
(profile,
 range_instance_id,
 deployment_tenant_id,
 reset_generation_id,
 baseline_id,
 baseline_version,
 object_id)
```

The coordinate is serialized with RFC 8785/JCS and hashed with SHA-256 after
the exact domain bytes
`aces-authored-historical-state|semantic-address|v1` plus a zero byte. The
canonical result is `hsa1:` followed by 64 lowercase hexadecimal characters.

All coordinate members are mandatory. Provider, backend, host, worker, process,
thread, retry, wall-time, queue, random-seed, declaration-index, native-id,
label, and timestamp values MUST NOT enter the derivation. Reusing one reset
generation preserves addresses; advancing it domain-separates the replacement
corpus. Duplicate coordinates, duplicate canonical bytes, or digest collisions
MUST fail atomically.

The complete admitted baseline has a separate
`aces-historical-baseline-digest/v1` identity. Its RFC 8785/JCS input contains
that profile, the baseline id, and the full typed baseline payload. SHA-256 is
applied after the exact domain bytes
`aces-authored-historical-state|baseline-digest|v1` plus a zero byte. This
digest is the portable carrier for downstream contracts that must bind to the
exact baseline rather than only its id/version or the containing scenario.

## Corpus safety and realization boundary

Historical object metadata is bounded and inert. An object MAY reference
ordinary SDL `Content`, but an admitted historical baseline MUST NOT absorb or
reference inline historical corpus bodies, raw exports, MIME archives,
database dumps, executable scripts or macros, private keys, credential
material, credential-bearing URLs, backend payloads, or unbounded binary/text
bodies.

Compilation MUST preserve the admitted instantiated graph, baseline digest,
and derived semantic addresses. It MUST NOT create plan resources merely to
carry metadata.
Product-assigned ids and native readback results remain tenant/reset/profile
scoped observed evidence outside the authored authority.

## Composition and compatibility

Module composition namespaces baseline keys and therefore every nested actor,
object, event, binding, and readback declaration address. It rewrites all
external refs and canonical nested object refs through the canonical symbol
maps. Local nested ids remain local to their baseline. Instantiation substitutes
permitted scalar and reference values, never declaration keys or address-profile
identity, then reruns all semantic invariants.

Documents that omit `historical_baselines` retain an empty map and unchanged
behavior.
