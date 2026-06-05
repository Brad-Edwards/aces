# ADR-052: Typed Runtime Relationship Subtypes

## Status

accepted

## Date

2026-05-30

## Context

SCN-010 §5.7 identifies an SDL expressivity gap for three recurring inter-node
access edges that the SCN-010 platform tier needs to express: a forwarding /
intel-sync agent's trust edge to the manager it ships to (`wazuh-sidecar-db`,
`wazuh-sidecar-suricata`, `misp-suricata-sync`), a platform consumer-to-engine
service integration (`thehive` -> `cortex`, webhook/notification/enrichment
wiring), and a reverse-proxy / gateway route-to-origin upstream hop
(`shuffle-frontend` -> `shuffle-backend`).

A generic `Relationship.properties: dict[str, str]` can assert that two
elements are linked but cannot structurally validate enrollment-identity
classification, enum sentinels, or cross-reference resolution. This is the same
reason `RelationshipDatabaseAccess` (ADR-029) and `RelationshipMailAccess`
(ADR-038) earned typed subtypes: protocol/auth/topology facts need structural
validation rather than prose, and cross-reference resolution lives in the
scenario-level semantic validator rather than in-class.

Two facts about the proxy hop can be recorded at two scopes — on the route
itself (`RuntimeApplicationRoute.upstream_target`, ADR-026) and on the
relationship edge (`RelationshipProxyUpstream`). Without an executable guard,
the same fact recorded twice can silently disagree.

## Decision

### 1. Add three typed subtypes as optional `Relationship` fields

Add three optional fields to the top-level `Relationship` model, mirroring the
existing `database_access` / `mail_access` typed exceptions:

- `forwarding_edge: RelationshipForwardingEdge | None`
  (`runtime_forwarding_agent.py`)
- `service_integration: RelationshipServiceIntegration | None`
  (`runtime_platform_application.py`)
- `proxy_upstream: RelationshipProxyUpstream | None`
  (`runtime_application.py`)

`RelationshipForwardingEdge` carries `forwarder_ref`, a `target_listener_role`
that REUSES the manager-side `RuntimeSecurityMonitoringListenerRole` lattice
rather than forking a parallel vocabulary, an `enrollment_identity_ref` with a
closed redaction lattice, `protocol`/`crypto_method` descriptors, and an open
`parse_format`. `RelationshipServiceIntegration` carries `consumer_ref` /
`engine_ref`, an open `integration_kind`, an `auth_principal_ref`, an optional
`enabled` flag, and a closed `direction`. `RelationshipProxyUpstream` carries
`route_ref`, `upstream_node_ref` / `upstream_service_ref`, the
`client_tls_terminated` / `origin_plaintext` flags, and a `body_limit`.

### 2. Keep cross-reference resolution at scenario scope

In-class validators only normalize enums and enforce single-record invariants
(such as a present enrollment identity being classified). Cross-reference
resolution lives in the semantic validator as three methods dispatched from the
relationship-verification entrypoint, mirroring
`_verify_relationship_database_access`:

- `_verify_relationship_forwarding_edges`: `forwarder_ref` resolves to a
  unique `forwarding_agent_id` either on a node's `runtime.forwarding_agents`
  list or in the scenario-level `forwarding_agents` registry for off-node
  infrastructure forwarders.
- `_verify_relationship_service_integrations`: `consumer_ref` / `engine_ref`
  resolve to `platform_application_id` values; a concrete `auth_principal_ref`
  resolves to a principal in the engine application's referenced
  `app_authorization` store when `authorization_ref` is set.
- `_verify_relationship_proxy_upstreams`: `route_ref` resolves to an
  application `route_id` on the relationship source; `upstream_node_ref`
  and `upstream_service_ref` resolve to defined upstream node/service targets.

### 3. Make "same fact, two scopes, not duplicated" executable

Add two executable agreement guards so a fact recorded at two scopes can never
silently contradict:

- A forwarding edge's `target_listener_role` and `protocol`, where both sides
  are concrete, must be consistent with at least one of the resolved agent's
  ship targets (an `agent_event_ingestion` role needs a ship target with an
  ingestion endpoint; `agent_enrollment` needs one with an enrollment endpoint;
  a concrete edge protocol must match a concrete ship-target protocol).
- When the referenced route ALSO carries an `upstream_target`, the shared facts
  (target node, target service, and the TLS-termination boolean) MUST agree
  between `route.upstream_target` and the `RelationshipProxyUpstream`.

## Security and Validation Gates

- Parser/model gate: closed taxonomies (`direction`, upstream `scheme`) carry
  neither `unknown` nor `other`; open taxonomies (`integration_kind`,
  `parse_format`) carry both. A present enrollment identity must classify
  `redacted` / `operator_secret`; a raw enrollment identity is never recorded.
- Semantic validation gate: forwarder/consumer/engine/route/node refs resolve;
  the two agreement guards reject contradictory cross-scope facts where both
  sides are concrete. Forwarding-agent IDs are unique across node-hosted and
  scenario-level registries. `${var}` placeholders defer to instantiation
  revalidation.
- Secret gate: enrollment identities and API-key principals are referenced by
  classification or stable id, never by raw value.
- Contract/schema gate: published schemas are regenerated from the Python model
  sources; generated JSON schemas are not edited by hand.

## Guardrails

- Do not express these edges as free-form `Relationship.properties` prose when
  a typed subtype carries the same fact.
- Do not fork a parallel listener-role enum for forwarding edges; reuse
  `RuntimeSecurityMonitoringListenerRole`.
- Do not duplicate the proxy upstream target/TLS facts across the route and the
  relationship without the agreement guard holding them consistent.

## Non-Goals

- Implementing forwarding, integration, or proxy behavior; these remain
  observation metadata.
- Redesigning `RuntimeForwardingAgent`, `RuntimePlatformApplication`,
  `RuntimeApplicationRoute`, or the generic relationship endpoint check.

## Consequences

### Positive

- The three inter-node access edges become typed, cross-referable, and
  validation-backed rather than prose.
- The "same fact, two scopes, not duplicated" claim becomes executable through
  the agreement guards rather than aspirational.

### Negative

- The `Relationship` model gains three more optional typed fields.

### Risks

- Over-broad agreement guards could reject legitimate partial inventories; the
  guards therefore fire only where both sides are concrete.

## References

- [Database Logical-State Runtime Surface](adr-029-database-logical-state-runtime-surface.md)
- [Runtime Mail-Service Logical State](adr-038-runtime-mail-service-logical-state.md)
- [Application HTTP Surface Inventory](adr-026-application-http-surface-inventory.md)
- [Platform Application Runtime Inventory](adr-049-platform-application-runtime-inventory.md)
- [Forwarding Agent Runtime Inventory](adr-050-forwarding-agent-runtime-inventory.md)
- OASIS STIX 2.1 (SRO); RFC 5424/5425/6587/3164 (syslog); NIST SP 800-92;
  RFC 6749 (OAuth 2.0); RFC 9110 / RFC 7239 (HTTP, Forwarded);
  NIST SP 800-44; Kubernetes Ingress / Gateway API.
- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md)
