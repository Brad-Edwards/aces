# ADR-058: Datastore Node Engine Provenance and Endpoints

## Status

accepted

## Date

2026-06-07

## Context

DSL-141 extends the datastore spine introduced by
[ADR-048](adr-048-datastore-service-runtime-inventory.md). The APTL SCN-010
capture of `wazuh.indexer` observes per-node OpenSearch facts that ADR-048
cannot type without forcing description prose or losing detail:

- engine build identity (`version`, `build_hash`, `build_type`);
- JVM heap lower/upper byte bounds and `mlockall` posture;
- installed engine plugins with per-plugin versions;
- separate client-facing and inter-node publish endpoints.

The existing `RuntimeDatastoreService.engine_plugins: list[str]` is too shallow:
it is service-scoped, name-only, and drops plugin versions. The existing
`RuntimeDatastoreNode.address` is too ambiguous: it cannot distinguish a REST
client listener from a cluster peer listener, and it combines endpoint role,
address, and port into one string. Adjacent surfaces still own narrower
meanings: `runtime.service_listeners` records in-node OS/process listener state,
`Node.services` records authored service identity, `runtime.network` records
network realization and host publication, and `runtime.software_components`
records package/component identity.

The design risk is to patch the search-cluster example locally by adding
OpenSearch-specific fields such as `http_publish_address` and
`transport_publish_address`, or by copying service-listener semantics into the
datastore model. That would make one engine the schema authority and blur the
boundary between datastore node inventory, process listeners, transport
exposure, and software inventory.

## Decision

Amend ADR-048 by extending the existing `RuntimeDatastoreNode` child inventory.
Do not add a new runtime family and do not move these facts to the datastore
service spine.

Each datastore node may carry product-neutral engine provenance and runtime
posture: engine version, build hash, build type, initial and maximum heap byte
bounds, and `mlockall` state. These are node-scoped observed runtime facts, not
software-component identities, package records, or host policy declarations.

Remove the service-level name-only `engine_plugins` list and replace it with
typed node-local engine plugin records. Each plugin record carries a stable ACES
id, observed name, and observed version. Plugin ids participate in the same
datastore service-wide stable-id namespace as the service, cluster, persistence
posture, transport-security posture, nodes, partitions, and settings.

Replace the single ambiguous node address as the authoritative endpoint surface
with typed node endpoint records. Each endpoint record carries a stable ACES id,
an open product-neutral role taxonomy, split address, and split port. The role
taxonomy must include both `unknown` and `other`; the initial portable roles
distinguish client-facing endpoints from inter-node or peer endpoints without
encoding engine-native names such as `http` or `transport`.

Datastore node plugins and endpoints are targetable child records below the
datastore node ref, for example:

- `nodes.<node>.runtime.datastore_services.<datastore_service_id>.nodes.<node_id>.plugins.<plugin_id>`
- `nodes.<node>.runtime.datastore_services.<datastore_service_id>.nodes.<node_id>.endpoints.<endpoint_id>`

The service-level `engine_plugins` list is removed rather than retained as a
shallow compatibility surface: it had no consumers outside the datastore family
and ACES is pre-production, so keeping a version-dropping parallel surface would
violate the no-duplicate-surface gate. (The architecture preflight's
keep-as-compat option was considered and superseded by these verified facts.)
All plugin capture uses the node-scoped typed inventory.

## Security and Validation Gates

- Parser/model gate: all new stable ids are concrete symbols validated through
  the shared runtime id helper; enum fields use the shared runtime enum parser;
  byte and port values use the shared integer-or-variable parsing discipline.
- Shape gate: heap byte bounds are non-negative concrete-or-variable values,
  and concrete `heap_init_bytes` must not exceed concrete `heap_max_bytes`.
  Concrete endpoint ports are in the TCP/UDP port range. Endpoint address and
  port stay split.
- Service-wide id gate: datastore service-local duplicate-id rejection includes
  plugin and endpoint ids, including nested ids under nodes.
- Registry/reference gate: datastore family `child_refs` includes nested node
  plugin and endpoint refs so generic references and module-import aliases work
  through the existing runtime-family registry.
- Semantic validation gate: existing same-node `service` and
  `authorization_ref` validation remains the datastore service boundary. Node
  endpoint records do not by themselves prove an OS process bind, host
  publication, or `Node.services` match.
- Secret/payload gate: node provenance, heap posture, plugin names/versions,
  and publish endpoints are inventory facts. Raw Nodes Info payloads, curl
  credentials, bearer tokens, TLS key material, and backend-native inspect blobs
  remain evidence or capture inputs, not SDL fields.
- Contract/schema gate: published JSON Schemas are regenerated from Python model
  sources. Generated schema JSON is not edited directly.
- Error-envelope gate: validation uses the existing Pydantic
  `ValidationError` and `SDLValidationError` paths. Do not add a datastore
  exception hierarchy or messages that echo raw backend payloads.

## Guardrails

- Do not add `http_publish_address`, `transport_publish_address`, or other
  engine-named endpoint fields.
- Do not store endpoint facts only in `RuntimeDatastoreNode.address` or
  `description`.
- Do not duplicate the generic `runtime.service_listeners` surface. Datastore
  node endpoints are engine-published topology facts; service listeners remain
  OS/process bind facts.
- Do not model engine plugins as OS packages, generic software components, or
  service-wide strings when per-node plugin version is observed.
- Do not embed application RBAC users, roles, or grants in node provenance or
  plugin records. Internal datastore RBAC remains delegated to
  `runtime.app_authorizations`.
- Do not make OpenSearch, Elasticsearch, Cassandra, Redis, or any one API
  response the schema authority. They motivate examples only.

## Non-Goals

- Building datastore capture adapters or calling engine APIs.
- Proving host exposure, firewall reachability, or process bind state from a
  datastore node endpoint.
- Replacing `runtime.service_listeners`, `Node.services`,
  `runtime.network.published_ports`, `runtime.software_components`,
  `runtime.packages`, or `runtime.app_authorizations`.
- Parsing raw plugin manifests, JVM output, OpenSearch Nodes Info responses,
  Cassandra gossip output, Redis cluster output, or backend-native payloads as
  first-class SDL records.
- Redesigning the ADR-048 `data_model` discriminator or the relational
  confirmation-fold boundary.

## Consequences

### Positive

- Datastore node build identity, plugin capability versions, memory posture,
  and listener topology become typed, targetable, and validation-backed.
- The datastore spine remains product-neutral and node-scoped where the
  observations are node-scoped.
- Generic listener, software inventory, RBAC, and network surfaces keep their
  existing meanings.

### Negative

- `RuntimeDatastoreNode` becomes a larger child model, and the registry gains
  nested datastore-node child refs.
- The service-level `engine_plugins: list[str]` field is removed; callers use
  the node-scoped typed plugin inventory. No consumers existed outside the
  datastore family at removal time (ACES pre-production).

### Risks

- Downstream consumers may overread a datastore endpoint as proof of host-public
  exposure; the model and docs must keep publish topology separate from OS bind
  and host publication.
- A future datastore class may need additional endpoint roles; the role enum is
  deliberately open so new roles do not require changing the endpoint shape.

## References

- Issue #470: SDL gap: search datastore node engine provenance
- DSL-141: Datastore Node Engine Provenance and Listener Topology
- [ADR-048: Datastore Service Runtime Inventory](adr-048-datastore-service-runtime-inventory.md)
- [ADR-043: Generic Runtime Service Listener Surface](adr-043-runtime-service-listener-surface.md)
- [ADR-034: Runtime Software Component Inventory](adr-034-runtime-software-component-inventory.md)
- [ADR-056: Runtime Observed Values and Credential Posture](adr-056-runtime-observed-values-and-credential-posture.md)
