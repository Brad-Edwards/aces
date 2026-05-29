# ADR-044: Security-Monitoring Detection Definition Semantics

## Status

accepted

## Date

2026-05-29

## Context

ADR-040 added `runtime.security_monitoring_managers` so ACES can represent a
SIEM or security-monitoring manager as observed runtime inventory. That surface
records manager identity, listeners, components, enrolled agents, groups,
content corpora, settings, and evidence refs.

Issue #434 identifies a stronger downstream claim that ADR-040 intentionally
did not cover:

> Range A and Range B loaded the same set of detection definitions.

Equal corpus paths, file counts, or file hashes can support "the same files
were present". They do not tell a downstream consumer which individual Wazuh
rules, decoders, parent/correlation links, predicates, thresholds, groups,
MITRE mappings, or parser-accepted definitions were loaded. Encoding those
facts as generic files, settings, relationships, or content-set descriptions
would make cross-range semantic comparison ambiguous.

The design risk is to turn ACES into a Wazuh XML interpreter or SIEM rule
engine. The SDL needs a portable manifest for parsed loaded definitions, not a
raw vendor payload or alert telemetry model.

## Decision

### 1. Add parsed detection definitions beneath the manager

Add `RuntimeSecurityMonitoringManager.detection_definitions` as a manager-owned
child collection. The owning manager and node remain implicit from the
enclosing `runtime.security_monitoring_managers` record.

`content_sets` continues to represent loaded corpora and file references.
`detection_definitions` represents parsed definitions from those corpora. A
definition can point back to `content_set_ref`, `source_file_ref`,
`source_artifact_ref`, and `evidence_refs`.

### 2. Preserve portable definition identity and semantics

Each definition has:

- stable ACES `definition_id`;
- portable `engine` and `definition_kind`;
- native definition identity through `native_id` and `name`;
- source file/span and canonical digest data;
- enabled, loaded, and parser-accepted state;
- severity/level and human-readable description;
- match strings, regex patterns, field predicates, decoder constraints, and
  decoder fields;
- correlation refs such as `if_sid_refs`, `if_matched_sid_refs`,
  `parent_definition_refs`, `frequency`, `timeframe_seconds`, and same-source
  constraints;
- groups, MITRE ATT&CK ids, compliance tags, tactic/technique labels, and
  generic tags;
- optional target refs for the node/service/runtime object the definition is
  intended to observe.

The model is Wazuh-capable first, but the bounded `engine` and
`definition_kind` vocabulary leaves room for Sigma, YARA, Suricata, and SIEM
analytics without making any one product the ACES schema authority.

### 3. Validate local ambiguity and provenance

Detection definitions participate in the manager-local stable-id namespace.
Duplicate `definition_id` values, or collisions with listeners, components,
agents, groups, content sets, settings, or the manager id, are rejected.

Semantic validation also checks:

- `content_set_ref` resolves to a manager-local content set;
- source and evidence file refs resolve to `runtime.filesystem_inventory` when
  the node has filesystem inventory;
- `if_sid_refs`, `if_matched_sid_refs`, and `parent_definition_refs` resolve to
  manager-local detection definitions;
- `source_artifact_ref` resolves through the generic named-ref index when set;
- `target_refs` resolve to targetable SDL elements.

### 4. Publish qualified refs and composition aliases

Detection definitions may be referenced as:

`nodes.<node>.runtime.security_monitoring_managers.<manager_id>.detection_definitions.<definition_id>`

Named-reference validation and module-import alias rewriting recognize the
same shape so composed scenarios do not retain stale un-namespaced refs.

## Security and Validation Gates

- Parser/model gate: `definition_id` is a concrete stable symbol, not a
  mapping key or `${var}` placeholder.
- SDL model gate: duplicate manager-local stable ids are rejected, including
  detection definitions.
- Canonical digest gate: `canonical_digest` and `digest_algorithm` must be
  supplied as a pair.
- Source-span gate: concrete line spans must be positive and ordered.
- Semantic validation gate: content-set refs, source/evidence file refs,
  correlation refs, source artifact refs, and target refs resolve.
- Secret-handling gate: raw manager secrets, tokens, private keys, enrollment
  secrets, and credential payloads are not detection-definition data.
- Contract/schema gate: JSON Schemas are generated from Python model sources.

## Guardrails

- Do not use `content_sets` to mean individual parsed rule/decoder semantics.
- Do not rely on file count or corpus hash alone to claim definition-level
  equivalence.
- Do not store raw Wazuh XML, SIEM query payloads, event logs, alert telemetry,
  or rule-engine execution output in the portable schema.
- Do not make XML formatting part of definition identity; use a canonical
  parsed projection and digest when identity must survive formatting changes.
- Do not accept parser failures silently: `parser_accepted` is explicit.

## Non-Goals

- Building a Wazuh capture client, XML parser, API client, or detection-rule
  interpreter.
- Modeling alert events, detection firing proof, dashboards, or logs as SDL
  runtime records.
- Replacing Sigma, YARA, Suricata, OCSF, ECS, STIX, Wazuh XML, or SIEM-native
  rule schemas.
- Redesigning manager inventory, network sensors, runtime snapshots,
  control-plane APIs, persistence, logging, or workflow semantics.

## Consequences

### Positive

- ACES can support the claim that two ranges loaded the same detection
  definition set when capture workflows provide parsed manifests.
- Wazuh rules and decoders can be represented without overloading content-set
  inventory or raw filesystem evidence.
- Definition refs are targetable and survive SDL module composition.

### Negative

- Security-monitoring manager records gain another optional child collection.
- Capture workflows that need definition-level comparison must parse vendor
  content into the portable shape.

### Risks

- Consumers may overread a canonical digest as proof that a detection fired;
  this surface only records loaded definition semantics.
- A Wazuh-only field dictionary would reduce portability. The enum and generic
  predicate/ref fields keep the boundary product-neutral.

## References

- [Security-Monitoring Manager Runtime Inventory](adr-040-security-monitoring-manager-runtime-inventory.md).
- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md).
