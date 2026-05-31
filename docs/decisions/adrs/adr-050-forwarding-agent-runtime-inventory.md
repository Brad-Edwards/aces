# ADR-050: Forwarding Agent Runtime Inventory

## Status

accepted

## Date

2026-05-30

## Context

SCN-010 (DSL-136) identifies an SDL expressivity gap for the agent-side
shipping state of a node: the log-forwarding sidecar (e.g. a Wazuh agent
tailing Suricata's `eve.json` and shipping to a manager) and the intel-sync
co-process (e.g. a MISP-to-Suricata feed that pulls IOCs, transforms them into
rules, and drives a downstream reload socket). Both share one shape —
`source -> transform -> ship-target` — that the existing runtime surfaces
provably cannot express.

Adjacent surfaces each own narrower meaning:

- `runtime.security_monitoring_managers` records the SIEM/monitoring *manager*
  half (the ingest destination), not the agent-side source/transform/ship
  spine.
- `runtime.network_detection_engines` records the detection-engine *consumer*
  of generated content, not the producer that ships it.
- `runtime.scheduled_jobs` records recurrence cadence and run-state only; it
  carries no job inputs, transforms, or ship targets.
- `runtime.service_manager_units` records systemd-scoped unit lifecycle, not
  what a forwarder ships.
- `Node.services` and `runtime.network` record transport/host exposure.

The design risk is to force shipping semantics into a manager content set, a
fake scheduled-job payload, a fake listener, or free-form relationship
properties.

## Decision

### 1. Add node-scoped and scenario-level forwarding agents

Add `Node.runtime.forwarding_agents` as an observed runtime inventory surface.
Each entry is a `RuntimeForwardingAgent` with a stable `forwarding_agent_id`,
product-neutral implementation and version fields, and an OPEN `agent_kind`
discriminator (`log_forwarder`, `content_sync`, plus the permissive
`unknown`/`other` tail) that selects the family member.

Also add top-level `Scenario.forwarding_agents` for off-node infrastructure
forwarders that are part of the scenario's runtime realization but are not
inventoried scenario nodes. These records reuse the same
`RuntimeForwardingAgent` model; there is no sidecar-specific or edge-inline
schema. This covers, for example, a Compose service that tails a database log
volume and ships to a manager while the database node itself hosts no forwarding
daemon.

### 2. Preserve typed child inventories

The agent owns typed child collections for `sources` (tailed path, API pull, or
queue inputs), `transforms` (`passthrough`/`parse`/`ioc_to_rule`),
`ship_targets` (downstream event-ingest and/or enrollment endpoints), an
optional `buffer_policy` (queue/back-pressure posture), `reload_channels`
(downstream rule-reload sockets), and bounded `settings`. Each carries a stable
local id; native config stanzas, raw events, and rule bodies remain evidence.

### 3. Make the discriminator executable

A `require_profile_for_agent_kind` after-validator makes each member's defining
profile executable so an under-populated instance fails validation. A
`log_forwarder` requires a `buffer_policy` and at least one `ship_target`
carrying an ingestion endpoint and rejects any `ioc_to_rule` transform; a
`content_sync` requires at least one `api_pull` source, one `ioc_to_rule`
transform, and one `reload_channel`, and rejects a `buffer_policy` and any
`ship_target` enrollment endpoint. A `${var}` discriminator is exempt and the
`unknown`/`other` tail is permissive.

### 4. Keep forwarding inventory targetable but not executable

Node-hosted agents and child records may be referenced from relationships using
qualified refs such as
`nodes.<node>.runtime.forwarding_agents.<forwarding_agent_id>.ship_targets.<target_id>`.
A ship-target `target_node_ref` resolves to a defined node and a
`target_service_ref` to a service on that node (or, absent a node ref, on the
owning node), validated at scenario scope. These refs are inventory targets;
they do not imply shipping execution. Cadence composes a
`runtime.scheduled_jobs` entry and the inter-node trust edge composes a
relationship forwarding edge — neither is re-typed here.

Scenario-level forwarding agents have no owning node, so a concrete
`target_service_ref` must be paired with a concrete `target_node_ref`; the
service is then resolved on that node. `RelationshipForwardingEdge.forwarder_ref`
resolves across both node-hosted and scenario-level forwarding-agent registries.
`forwarding_agent_id` values must be unique across both registries.

## Security and Validation Gates

- Parser/model gate: stable agent and child ids are concrete symbols, not
  variables; duplicate agent-local child ids fail early and semantic validation
  rejects duplicate `forwarding_agent_id` values across node-hosted and
  scenario-level registries.
- Profile gate: the `require_profile_for_agent_kind` guard rejects an
  under-populated `log_forwarder`/`content_sync` instance.
- Semantic validation gate: ship-target `target_node_ref`/`target_service_ref`
  resolve at scenario scope, and scenario-level agents cannot use an implicit
  owning node for service refs.
- Secret/payload gate: ship-target enrollment identities (closed
  `none`/`redacted`/`operator_secret` lattice) and secret-bearing settings
  never carry raw values; the shared `name_indicates_secret` helper enforces
  redaction even when the submitter left the classification at its default.
- Contract/schema gate: published schemas are regenerated from Python model
  sources; generated JSON schemas are not edited by hand.

## Guardrails

- Do not model forwarders as manager content sets, fake scheduled-job
  payloads, fake listeners, generic software components, or prose-only
  relationships.
- Do not add an infrastructure-only sidecar as a scenario node merely to host a
  forwarding agent.
- Do not re-encode what a forwarder ships onto a scheduled job or service unit.
- Do not store raw events, rule bodies, MISP/API tokens, or enrollment keys.
- Do not make Wazuh, Filebeat, or MISP the schema authority; they motivate the
  surface, the model stays product-neutral.

## Non-Goals

- Implementing log shipping, IOC ingestion, rule generation, reload execution,
  or back-pressure behavior.
- Replacing OCSF, ECS, STIX/TAXII, Beats, or OpenTelemetry schemas.
- Redesigning `runtime.security_monitoring_managers`,
  `runtime.network_detection_engines`, `runtime.scheduled_jobs`, or
  `runtime.service_manager_units`.

## Consequences

### Positive

- Agent-side shipping facts become typed, targetable, and validation-backed
  without corrupting adjacent runtime surfaces.
- The single `agent_kind` spine covers both log-forwarding and intel-sync so a
  second family is never forked.

### Negative

- Node runtime gains another optional inventory surface.

### Risks

- Over-expanding the model into a shipping engine would recreate the original
  ambiguity under a new name.
- Treating a transform's presence as proof of execution would overclaim what
  the SDL can validate.

## References

- [Security-Monitoring Manager Runtime Inventory](adr-040-security-monitoring-manager-runtime-inventory.md)
- [Network Detection Engine Runtime Inventory](adr-044-network-detection-engine-runtime-inventory.md)
- [Scheduled-Job Runtime Inventory](adr-047-scheduled-job-runtime-inventory.md)
- [Scenario/Delivery Boundary for Runtime Node State](adr-033-scenario-delivery-boundary-for-runtime-node-state.md)
- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md)
