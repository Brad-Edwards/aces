---
id: DSL-141
title: "Datastore Node Engine Provenance and Listener Topology"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-06-07T08:19:30.899037Z
updated_at: 2026-06-07T09:57:52.002168Z
---

# DSL-141 — Datastore Node Engine Provenance and Listener Topology

## Statement

The language shall represent participant-observable datastore-node engine provenance and runtime posture as typed node-scoped runtime inventory under the data-model-discriminated datastore surface (extending DSL-132), including engine version, build hash, and build type; initial and maximum heap byte bounds and memory-lock (mlockall) state; a typed per-node engine-plugin inventory carrying each plugin's stable id, name, and version (replacing the name-only, version-dropping, service-level engine_plugins list); and a typed, product-neutral node-endpoint inventory distinguishing client-facing from inter-node/peer publish listeners by an open role taxonomy with split address and port (replacing the single ambiguous node address), so that build identity, installed-capability versions, memory posture, and listener topology are typed, targetable, and validation-backed without forcing description prose, overloading software-component identity or transport-listener surfaces, or making any concrete engine the schema authority. New stable ids participate in the datastore service-wide id-uniqueness namespace and the cross-family structural invariant set; the new role taxonomy is an open enum carrying both unknown and other sentinels.

## Rationale

APTL TechVault SCN-010 capture of wazuh.indexer (Brad-Edwards/aptl#341, OpenSearch 2.19.1) observes node-scoped engine provenance and posture — build_hash, build_type, 18 plugins each with its own version, JVM heap_init/heap_max bytes, mlockall state, and distinct http (REST, :9200) vs transport (inter-node, :9300) publish addresses — that the DSL-132 datastore spine cannot type at the node level. Today these facts can only be shallow-encoded in the free-text node description or the name-only service-level engine_plugins list, both of which the SCN-010 observable-parity gate (#353) forbids. The Elasticsearch/OpenSearch Nodes Info API reports all of these per node; the client/peer listener split is structural across the search-cluster tech class (OpenSearch http/transport, Cassandra native/internode, Redis client/cluster-bus), motivating an engine-neutral role taxonomy. Extends DSL-132 to close its node-level parity gap; recorded in ADR-058 amending ADR-048.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `470` (SDL gap: search datastore node engine provenance)
- TESTS → TEST `implementations/python/tests/test_runtime_datastore.py`
- DOCUMENTS → ADR `docs/decisions/adrs/adr-058-datastore-node-engine-provenance-and-endpoints.md`
- IMPLEMENTS → PULL_REQUEST `480` (added: datastore-node engine provenance and listener topology (DSL-141))
