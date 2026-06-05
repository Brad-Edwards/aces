# ADR-048: Datastore Service Runtime Inventory

## Status

accepted

## Date

2026-05-30

## Context

SCN-010 (DSL-132) identifies an SDL expressivity gap for the
participant-observable logical state of a node's *non-relational* datastore.
The existing `runtime.database_services` surface is irreducibly relational
(databases, schemas, tables, engine GRANTs) and cannot shape the OpenSearch /
Elasticsearch search cluster, the Cassandra wide-column store, or the Redis
key-value store that recur across the corpus. Those nodes already fit adjacent
ACES surfaces for package identity, processes, filesystem evidence, network
attachment, and transport listeners, but no surface carries the datastore facts
that matter to participants and downstream inventory consumers: search
shard/replica geometry, wide-column replication strategy/factor, and key-value
persistence posture.

Adjacent surfaces each own narrower meaning:

- `runtime.database_services` records relational logical state and engine
  GRANTs, not non-relational data models or their replication/persistence
  geometry.
- `runtime.app_authorizations` records application-internal RBAC, referenced
  here only by a string `authorization_ref`.
- `runtime.software_components` records installed component identity, not
  datastore logical state.
- `Node.services` and `runtime.network` record transport and host exposure.

The design risk is to force non-relational datastore semantics into the
relational surface, a config checksum, a fake listener, or free-form
relationship properties — silently shallow-encoding a defining fact such as a
search cluster with no shard geometry.

## Decision

### 1. Add a single discriminated datastore spine under runtime

Add `Node.runtime.datastore_services`. Each entry is a single
`RuntimeDatastoreService` spine with a stable `datastore_service_id`, an optional
same-node `service` ref, an open `engine` fact, and an OPEN `data_model`
discriminator (`search_index` / `wide_column` / `key_value` / `relational` /
`unknown` / `other`). The owning node is implicit; transport exposure stays in
`Node.services` and `runtime.network`; raw files remain evidence.

### 2. Make the discriminator executable with a required-profile guard

A model-local `require_profile_for_data_model` after-validator fails an
under-populated instance. A `${var}` placeholder discriminator is exempt and the
open `unknown` / `other` / `relational` tail imposes no profile, but each
concrete structural data model requires its defining geometry:

- `search_index` requires at least one `partition` with `kind: index` carrying
  shard/replica counts.
- `wide_column` requires at least one `keyspace` partition with a concrete
  replication strategy and a replication factor.
- `key_value` requires a `persistence` profile and rejects relational /
  wide-column (`keyspace` / `column_family`) partitions.

### 3. Preserve typed child inventories

The service owns single nested postures (`cluster`, `persistence`,
`transport_security`) and id-bearing child collections (`nodes`, `partitions`,
`settings`); `templates`, `aliases`, `mappings`, `lifecycle_policies`,
`ingest_pipelines`, `pubsub_channels`, `queues_streams`, `engine_plugins`, and
`backup_targets` are bare reference-name lists. Secret-bearing settings omit
their raw value and classify `redacted` / `operator_secret`.

### 4. Keep datastore inventory targetable but not executable

Services and id-bearing children may be referenced from relationships using
qualified refs:

- `nodes.<node>.runtime.datastore_services.<datastore_service_id>`
- `nodes.<node>.runtime.datastore_services.<datastore_service_id>.nodes.<node_id>`
- `nodes.<node>.runtime.datastore_services.<datastore_service_id>.partitions.<partition_id>`
- `nodes.<node>.runtime.datastore_services.<datastore_service_id>.settings.<setting_id>`

These refs are inventory targets. They do not imply query execution, indexing,
replication, or persistence behavior.

## Security and Validation Gates

- Parser/model gate: stable service and child ids are concrete symbols. Enum
  fields are normalized through the single runtime enum-parse helper. Duplicate
  service ids and duplicate service-local child ids fail early.
- Required-profile gate: the `require_profile_for_data_model` guard fails an
  under-populated `search_index` / `wide_column` / `key_value` instance.
- Semantic validation gate: the owning `service` ref resolves to a same-node
  binding; a non-empty, non-variable `authorization_ref` resolves to a same-node
  `app_authorization`.
- Relationship/reference gate: service and child qualified refs resolve in
  generic relationships and survive module import namespacing.
- Secret/payload gate: raw key material, credentials, and secret-bearing setting
  values stay out of SDL model data.
- Contract/schema gate: published schemas are regenerated from Python model
  sources; generated JSON schemas are not edited by hand.

## Guardrails

- Do not model non-relational datastores as relational `database_services`, fake
  HTTP applications, fake transport services, generic software components, raw
  config blobs, or prose-only relationships.
- Do not embed principals, roles, or grants here; internal RBAC is delegated to
  `runtime.app_authorizations` via `authorization_ref`.
- Do not make OpenSearch, Cassandra, or Redis the schema authority. They
  motivate the surface; the SDL model remains product-neutral.

## Non-Goals

- Implementing query execution, indexing, replication, persistence, or backend
  provisioning behavior.
- Replacing the relational `runtime.database_services` surface.
- Redesigning `runtime.app_authorizations`, `Node.services`, or
  `runtime.filesystem_inventory`.

## Consequences

### Positive

- Non-relational datastore facts become typed, targetable, and
  validation-backed without corrupting the relational surface.
- The required-profile guard makes a defining datastore fact impossible to
  silently omit.

### Negative

- Node runtime gains another optional inventory surface.
- Consumers needing raw engine internals must retain separate evidence.

### Risks

- Over-expanding the model into a query/replication engine would recreate the
  original ambiguity under a new name.
- Treating evidence presence as proof of a data-model profile would overclaim
  what the SDL can validate; the required-profile guard exists to prevent this.

## References

- [Database Logical-State Runtime Surface](adr-029-database-logical-state-runtime-surface.md)
- [App-Authorization Runtime Inventory](adr-046-app-authorization-runtime-inventory.md)
- [Runtime Software Component Inventory](adr-034-runtime-software-component-inventory.md)
- [Scenario/Delivery Boundary for Runtime Node State](adr-033-scenario-delivery-boundary-for-runtime-node-state.md)
- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md)
