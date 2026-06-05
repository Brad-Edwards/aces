# ADR-042: Network Sensor Runtime Monitoring Posture

## Status

accepted

## Date

2026-05-29

## Context

Issue #429 identifies an SDL expressivity gap for an in-range NSM/IDS node
whose defining behavior is passive observation of network traffic. The
TechVault Suricata node runs Suricata 7.0.15 in `--pcap` mode with
`pcap.interface: any`, is attached to `dmz-net`, `internal-net`, and
`security-net`, and has raw-capture Linux capabilities. It has no listening
transport service of its own; its participant-relevant behavior is that it
observes the networks it is attached to.

Adjacent ACES surfaces each own narrower meaning:

- `infrastructure` and `Node.runtime.network.endpoints` record declared and
  observed network attachment, not monitoring.
- `Node.services` records listeners; a passive sensor may expose none.
- top-level `relationships` records directed scenario graph edges such as
  connectivity, dependency, management, trust, and replication, not passive
  traffic observation.
- `Node.roles` is login/role occupancy, not sensor function.
- `runtime.security_monitoring_managers` records manager/SIEM state such as
  Wazuh-style enrolled agents, groups, components, and content sets, not the
  posture of a node tapping network traffic.

The design risk is to smuggle "observes traffic on these networks" into
connectivity, node roles, free-form relationship properties, manager inventory,
or Docker/Suricata-specific fields.

## Decision

### 1. Add node-scoped network sensors under runtime

Add `Node.runtime.network_sensors` as an observed runtime inventory surface.
Each sensor has a stable `sensor_id`, implementation family, sensor kind,
monitoring posture, capture mode, capture interfaces, monitored network refs,
process/config/log/evidence refs, version/revision/name data, and description.

The owning node is implicit from the enclosing node. Network attachment remains
separate in `infrastructure` and `runtime.network.endpoints`; a multi-homed
node is not a network sensor unless it declares `network_sensors`.

### 2. Make monitored network scope the portable semantic axis

`monitored_network_refs` is the load-bearing portable field. Each ref resolves
to a declared switch-backed infrastructure network. When
`runtime.network.endpoints` is present on the same node, each monitored network
must also be one of that node's runtime endpoint attachments.

Capture implementation details such as `pcap`, `af_packet`, `nfqueue`, an
interface value such as `any`, or Linux capabilities are evidence and bounded
runtime data. They do not replace the scenario-level statement of which network
resources the sensor observes.

### 3. Keep sensors targetable without making them relationships

Network sensors may be referenced through qualified refs:

- `nodes.<node>.runtime.network_sensors.<sensor_id>`

Generic relationship, objective, and module-composition reference machinery
must recognize the same shape. A relationship may depend on or manage the
sensor record, but the sensor's passive monitoring scope stays on the sensor
model rather than being encoded as a `connects_to` edge.

## Security and Validation Gates

- Parser/model gate: sensor ids are stable concrete symbols, not variables.
  Model fields are closed and typed; duplicate sensor ids and duplicate
  monitored network refs are rejected.
- Semantic validation gate: monitored networks resolve to switch-backed
  infrastructure and, when endpoint inventory exists, to a same-node endpoint
  attachment.
- Evidence gate: configuration, log, and evidence refs are absolute paths and
  resolve against `runtime.filesystem_inventory` when present.
- Contract/schema gate: published schemas are regenerated from Python model
  sources; generated JSON schemas are not edited by hand.
- Secret/packet-content gate: raw packet payloads, alert streams, capture
  files, credentials, and backend inspect payloads are evidence artifacts, not
  inline SDL model data.

## Guardrails

- Do not model passive monitoring as `connects_to` or as free-form
  relationship properties.
- Do not infer monitoring from multi-homing, capabilities, command argv, or
  `pcap.interface` alone.
- Do not use `Node.roles`, `agents`, or `objectives` as sensor-role surfaces.
- Do not make Suricata, Docker, or packet-capture configuration the schema
  authority.
- Do not parse alerts, packets, rules, or telemetry as part of this runtime
  posture surface.

## Non-Goals

- Implementing packet capture, Suricata configuration parsing, alert parsing,
  rule semantics, evidence-bundle ingestion, or telemetry retention policy.
- Modeling SIEM/security-monitoring manager inventory; ADR-040 owns that
  adjacent surface.
- Changing backend provisioning behavior or Docker capability handling.

## Consequences

### Positive

- Passive NSM/IDS nodes become representable without corrupting connectivity,
  roles, services, manager inventory, or topology attachment.
- Consumers can distinguish an ordinary multi-homed node from a node that
  observes traffic on specific networks.
- Qualified refs let scenarios target the sensor record while preserving the
  sensor's own monitoring scope.

### Negative

- Node runtime gains another optional inventory surface.
- Consumers that need raw packet or alert evidence must retain separate
  evidence artifacts instead of embedding those payloads in SDL.

### Risks

- Over-expanding the model into alert telemetry or vendor-specific rule
  semantics would recreate the original ambiguity under a new name.
- Treating capture mode or Linux capabilities as sufficient proof of monitoring
  would make the portable scenario meaning depend on backend-local evidence.

## References

- [Scenario/Delivery Boundary for Runtime Node State](adr-033-scenario-delivery-boundary-for-runtime-node-state.md)
- [Container Network Realization Surface](adr-025-container-network-realization-surface.md)
- [Security-Monitoring Manager Runtime Inventory](adr-040-security-monitoring-manager-runtime-inventory.md)
- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md)
