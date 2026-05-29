# ADR-043: Network Detection Engine Runtime Inventory

## Status

accepted

## Date

2026-05-29

## Context

Issue #430 identifies an SDL expressivity gap for an in-range Suricata
IDS/NDR node whose defining runtime behavior is the detection engine itself.
The TechVault Suricata node already fits adjacent ACES surfaces for package
identity, processes, filesystem evidence, unix sockets, network attachment,
and network-sensor monitoring posture, but those surfaces do not carry the
engine facts that matter to participants and downstream inventory consumers:
enabled app-layer parsers, loaded rule sources, network zoning/address-set
variables, alert/telemetry output streams, and reload/control posture.

Adjacent surfaces each own narrower meaning:

- `runtime.network_sensors` records passive or inline monitoring posture and
  monitored networks, not the detection engine's parser/rule/output inventory.
- `runtime.security_monitoring_managers` records SIEM or monitoring-manager
  inventory, not standalone IDS/NDR engine state.
- `runtime.software_components` records installed component identity, not
  detection content or output semantics.
- `runtime.filesystem_inventory` records config, rule, socket, and log paths
  as evidence, not typed detection-engine facts.
- `Node.services` and `runtime.network` record transport and network exposure;
  a passive IDS may expose no listener.
- `runtime.applications` remains HTTP/WS route inventory.

The design risk is to force detection semantics into a config checksum, a
fake HTTP route, a fake listening service, SIEM manager content sets, or
free-form relationship properties.

## Decision

### 1. Add node-scoped detection engines under runtime

Add `Node.runtime.network_detection_engines` as an observed runtime inventory
surface. Each engine has a stable `engine_id`, product-neutral implementation
and kind fields, version/revision/name data, optional process and same-node
network-sensor refs, configuration/log/evidence refs, and description.

The owning node is implicit from the enclosing node. Sensor posture remains in
`runtime.network_sensors`; transport exposure remains in `Node.services` and
`runtime.network`; raw files remain evidence.

### 2. Preserve typed child inventories

The engine owns typed child collections for:

- `app_layer_protocols`: enabled parser families such as HTTP, TLS, DNS, SSH,
  SMTP, FTP, and SMB.
- `rule_sources`: loaded rule, IOC, script, or managed content sources with
  source kind, format, bounded count, file refs, generator, and loaded status.
- `network_sets`: zoning or service-group address-set variables such as
  HOME_NET, EXTERNAL_NET, DMZ_NET, INTERNAL_NET, and DNS_SERVERS.
- `output_streams`: bounded alert/telemetry stream metadata such as EVE JSON
  or fast.log, emitted event families, path refs, and enabled status.
- `control_channels`: bounded reload/control-channel metadata such as a unix
  command socket, service ref, capabilities, and auth posture.

Stable ACES ids are the portable reference surface. Native rule identifiers,
raw rule bodies, alert payloads, config stanzas, and vendor API responses
remain evidence unless promoted into a bounded field above.

### 3. Keep detection inventory targetable but not executable

Detection engines and child records may be referenced from relationships using
qualified refs:

- `nodes.<node>.runtime.network_detection_engines.<engine_id>`
- `nodes.<node>.runtime.network_detection_engines.<engine_id>.rule_sources.<source_id>`
- `nodes.<node>.runtime.network_detection_engines.<engine_id>.network_sets.<set_id>`
- `nodes.<node>.runtime.network_detection_engines.<engine_id>.output_streams.<stream_id>`
- `nodes.<node>.runtime.network_detection_engines.<engine_id>.control_channels.<channel_id>`

These refs are inventory targets. They do not imply rule execution, packet
capture, reload execution, or alert parsing.

## Security and Validation Gates

- Parser/model gate: stable engine and child ids are concrete symbols, not
  variables. Fields are closed and typed. Duplicate engine ids and duplicate
  engine-local child ids fail early.
- Semantic validation gate: same-node `sensor_ref` values resolve to
  `runtime.network_sensors`; network-set refs resolve to switch-backed
  infrastructure; control-channel service refs resolve to same-node services;
  file/path refs resolve against `runtime.filesystem_inventory` when present.
- Relationship/reference gate: engine and child qualified refs resolve in
  generic relationships and survive module import namespacing.
- Secret/payload gate: raw rules, packet payloads, alert streams, MISP/API
  tokens, private keys, backend inspect payloads, and secret-bearing config
  values stay out of SDL model data.
- Contract/schema gate: published schemas are regenerated from Python model
  sources; generated JSON schemas are not edited by hand.

## Guardrails

- Do not model IDS/NDR engines as fake HTTP applications, fake transport
  services, generic software components, passive sensor posture, SIEM manager
  content sets, raw config blobs, or prose-only relationships.
- Do not infer detection-engine semantics from package names, process argv,
  Linux capabilities, capture interfaces, EVE log presence, or a unix socket
  alone.
- Do not parse Suricata/Snort/Zeek rules, alerts, packets, telemetry, MISP
  exports, or backend-native API payloads as first-class SDL records.
- Do not make Suricata the schema authority. Suricata motivates the surface;
  the SDL model remains product-neutral.

## Non-Goals

- Implementing packet capture, rule parsing, IOC ingestion, alert parsing,
  telemetry retention, reload execution, or backend provisioning behavior.
- Replacing OCSF, ECS, Sigma, YARA, STIX, Suricata, Snort, Zeek, or vendor
  schemas.
- Redesigning `runtime.network_sensors`,
  `runtime.security_monitoring_managers`, `Node.services`,
  `runtime.filesystem_inventory`, runtime snapshots, or control-plane APIs.

## Consequences

### Positive

- IDS/NDR detection-engine facts become typed, targetable, and
  validation-backed without corrupting adjacent runtime surfaces.
- Consumers can represent Suricata-style parser, rule-source, zoning, output,
  and reload posture while keeping raw evidence external.
- Future Snort, Zeek, and NDR engines can reuse the same axes without adding
  product-specific schema clones.

### Negative

- Node runtime gains another optional inventory surface.
- Consumers that need raw rule or telemetry semantics must retain separate
  evidence artifacts instead of relying on SDL to reproduce them.

### Risks

- Over-expanding the model into a rule interpreter would recreate the original
  ambiguity under a new name.
- Treating evidence presence as proof of enabled detection would overclaim
  what the SDL can validate.

## References

- [Network Sensor Runtime Monitoring Posture](adr-042-network-sensor-runtime-monitoring.md)
- [Security-Monitoring Manager Runtime Inventory](adr-040-security-monitoring-manager-runtime-inventory.md)
- [Runtime Software Component Inventory](adr-034-runtime-software-component-inventory.md)
- [Scenario/Delivery Boundary for Runtime Node State](adr-033-scenario-delivery-boundary-for-runtime-node-state.md)
- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md)
