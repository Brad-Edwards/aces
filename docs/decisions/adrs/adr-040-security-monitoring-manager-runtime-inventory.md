# ADR-040: Security-Monitoring Manager Runtime Inventory

## Status

accepted

## Date

2026-05-29

## Context

Issue #428 identifies an SDL expressivity gap for observed SIEM and
security-monitoring manager state. The current model can record transport
listeners in `Node.services`, processes in `runtime.processes`, service-manager
unit state in `runtime.service_manager_units`, evidence paths in
`runtime.filesystem_inventory`, and adjacent logical runtime services such as
DNS, mail, database, identity, and file sharing. It cannot represent a manager
such as Wazuh as the runtime control point that owns enrolled agents, agent
groups, manager modules, detection/ruleset content, and bounded manager
settings.

That gap matters because SIEM and security-monitoring managers are not only
network listeners. They are also log-management and analysis infrastructure.
NIST SP 800-92 frames log management as infrastructure plus processes for
collection, analysis, storage, and maintenance. Wazuh's documentation describes
the server/manager as a central component that receives data from agents,
external APIs, and network devices, analyzes events against rulesets, and
exposes manager, agent, rule, decoder, and group management surfaces. OCSF and
Sigma are useful evidence-lineage checks for vendor-neutral security event and
detection-content vocabulary, but neither should become the ACES SDL runtime
inventory schema.

Adjacent ACES surfaces already have narrower jobs:

- `Node.services` records transport bindings such as manager API or agent
  ingestion ports.
- `runtime.service_manager_units` records service-manager lifecycle state, not
  manager-domain inventory.
- `runtime.processes` records live or supervised process identity, not
  enrolled security agents or detection content.
- `runtime.filesystem_inventory` records evidence paths, not parsed manager
  configuration or rules.
- `runtime.dns_services`, `runtime.mail_services`, `runtime.database_services`,
  `runtime.identity_authorities`, and `runtime.file_services` each record their
  own runtime domain.
- top-level `relationships` records scenario graph edges.

The design risk is to overload a port, a process, a unit, a filesystem entry,
or raw Wazuh XML/API output until all of them mean "SIEM manager".

## Decision

### 1. Model security-monitoring managers under node runtime

Add `Node.runtime.security_monitoring_managers` as optional observed runtime
inventory. Each manager has a stable `manager_id`, optional same-node
`Node.services[].name` owner reference, implementation family, manager kind,
version/revision/name data, configuration/log/evidence refs, and descriptions.

The owning node is implicit from the enclosing node. The transport service
remains explicit through the existing same-node service-ref pattern. Manager
facts must not be placed under `runtime.applications`, `runtime.processes`,
`runtime.service_manager_units`, `runtime.filesystem_inventory`, generic
`content`, or prose-only relationships.

### 2. Preserve manager-local child records with stable ids

The manager owns typed child collections for:

- `listeners`: manager-domain listeners bound to same-node services, with
  logical roles such as agent event ingestion, enrollment, API, syslog
  ingestion, alert forwarding, indexer forwarding, or dashboard.
- `components`: manager modules or daemons such as analysis engines, agent
  ingestion, enrollment, module supervision, API, clustering, vulnerability
  detection, FIM, SCA, active response, integrations, or database components.
- `agents`: enrolled agents or sensors, including status, observed name,
  version, OS/address data, optional scenario node reference, and group refs.
- `agent_groups`: manager-side groups, including member refs and group
  configuration file evidence.
- `content_sets`: detection or monitoring corpora such as rules, decoders,
  correlation rules, SCA policies, active-response content, CDB lists, threat
  intel, dashboards, or query packs, with bounded format and file-count data.
- `settings`: bounded manager settings with provenance, source path, component
  ref, and runtime sensitivity classification.

Stable ACES ids are the portable reference surface. Product identifiers such as
native Wazuh rule ids, file names, group names, API ids, and daemon names remain
observed data unless promoted into one of these stable id fields by the author
or capture workflow.

### 3. Keep detection content as inventory, not a rule interpreter

The SDL surface records which content families are present, loaded, and
evidence-backed. It does not parse Wazuh rule XML, decoder XML, Sigma rule
logic, YARA, STIX, SIEM query languages, alert telemetry, or raw event payloads
as first-class SDL runtime records.

This keeps ACES aligned with the runtime-inventory pattern used by DNS and
mail: enough structure to compare, target, and validate scenario-relevant
facts, without pretending to be a vendor-specific manager API or rules engine.

### 4. Publish qualified runtime refs with matching validation and composition

Security-monitoring managers and their stable child records may be referenced
from top-level relationships using qualified refs:

- `nodes.<node>.runtime.security_monitoring_managers.<manager_id>`
- `nodes.<node>.runtime.security_monitoring_managers.<manager_id>.listeners.<listener_id>`
- `nodes.<node>.runtime.security_monitoring_managers.<manager_id>.components.<component_id>`
- `nodes.<node>.runtime.security_monitoring_managers.<manager_id>.agents.<agent_id>`
- `nodes.<node>.runtime.security_monitoring_managers.<manager_id>.agent_groups.<group_id>`
- `nodes.<node>.runtime.security_monitoring_managers.<manager_id>.content_sets.<content_id>`
- `nodes.<node>.runtime.security_monitoring_managers.<manager_id>.settings.<setting_id>`

Named-reference validation and module-import alias rewriting must recognize
the same shapes so a composed scenario cannot silently point at an
un-namespaced or nonexistent manager record.

## Security and Validation Gates

- Parser/model gate: manager and child stable ids are concrete symbols, not
  `${var}` placeholders or mapping keys.
- SDL model gate: reject duplicate manager ids in one node runtime block and
  duplicate manager-local stable ids across manager, listener, component,
  agent, group, content, and setting records.
- Semantic validation gate: each manager and listener `service` ref resolves
  only to a same-node `Node.services[]` binding. Configuration, log, evidence,
  content, group config, and setting source paths resolve to observed runtime
  filesystem entries when such inventory exists.
- Local-reference gate: group member refs resolve to manager-local agents,
  agent group refs resolve to manager-local groups, and setting component refs
  resolve to manager-local components.
- Relationship/reference gate: manager and child qualified refs resolve in
  generic relationships and survive module import namespacing.
- Secret-handling gate: password/token/credential/private-key/keytab and
  equivalent security-monitoring settings must omit raw values and use
  `redacted` or `operator_secret` classifications.
- Contract/schema gate: schemas are generated from Python model sources through
  the repo generator; generated JSON schemas are not edited by hand.

## Guardrails

- Do not model a security-monitoring manager as only a transport service,
  process, service-manager unit, package, filesystem entry, or HTTP route.
- Do not encode raw Wazuh XML, Sigma/YARA/STIX rule bodies, SIEM queries, API
  payloads, alert telemetry, or logs as the ACES portable schema.
- Do not store manager API tokens, enrollment passwords, private keys, shared
  keys, or other secret material in settings.
- Do not make Wazuh the schema authority. Wazuh is a motivating implementation
  and evidence source; the SDL surface remains product-neutral.
- Do not publish manager refs into relationships/objectives unless validation,
  module composition aliases, docs, and tests move together.

## Non-Goals

- Building a Wazuh capture client, API client, XML parser, or detection-rule
  semantic interpreter.
- Modeling event telemetry, alert records, log lines, dashboards, or
  per-detection execution results as first-class SDL runtime records.
- Designing backend provisioning behavior for SIEM/SOC platforms.
- Replacing OCSF, ECS, Sigma, YARA, STIX, or vendor schemas.
- Redesigning `Node.services`, `runtime.processes`,
  `runtime.service_manager_units`, `runtime.filesystem_inventory`, top-level
  `relationships`, runtime snapshots, control-plane APIs, persistence,
  logging, or workflow semantics.

## Consequences

### Positive

- SIEM/security-monitoring manager inventory becomes typed, targetable, and
  validation-backed without corrupting transport services, process snapshots,
  units, filesystem evidence, or generic relationships.
- Wazuh-style managers can preserve their load-bearing facts: listeners,
  manager modules, enrolled agents, groups, content corpora, settings, and
  evidence refs.
- Secret redaction and same-node ownership checks are consistent with adjacent
  runtime surfaces.

### Negative

- Node runtime gains another optional inventory surface.
- Consumers that need full vendor-specific configuration or rule semantics must
  retain separate evidence artifacts rather than relying on SDL to reproduce
  raw manager state.

### Risks

- A Wazuh-specific field dictionary would recreate the original ambiguity under
  a new field name.
- Treating content inventory as rule semantics would overclaim what the SDL can
  validate.
- Recording API tokens, enrollment secrets, private keys, or shared credentials
  could leak sensitive data into fixtures, schemas, diagnostics, logs, or
  snapshots.

## References

- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md).
- [NIST SP 800-92: Guide to Computer Security Log Management](https://doi.org/10.6028/NIST.SP.800-92).
- [Wazuh server documentation](https://documentation.wazuh.com/current/user-manual/manager/index.html),
  [Wazuh API reference](https://documentation.wazuh.com/current/user-manual/api/reference.html),
  [Wazuh grouping agents](https://documentation.wazuh.com/current/user-manual/agent/agent-management/grouping-agents.html),
  [Wazuh rules syntax](https://documentation.wazuh.com/current/user-manual/ruleset/ruleset-xml-syntax/rules.html),
  and
  [Wazuh decoders syntax](https://documentation.wazuh.com/current/user-manual/ruleset/ruleset-xml-syntax/decoders.html).
- [Open Cybersecurity Schema Framework](https://github.com/ocsf) and
  [OCSF schema browser](https://schema.ocsf.io/).
- [Sigma detection rules documentation](https://sigmahq.io/docs/basics/rules.html).
