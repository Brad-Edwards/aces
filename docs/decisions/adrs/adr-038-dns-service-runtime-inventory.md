# ADR-038: DNS Service Runtime Inventory

## Status

accepted

## Date

2026-05-28

## Context

Issue #426 identifies an SDL expressivity gap for observed DNS service state.
The current model can record a DNS listener in `Node.services` and container
resolver knobs in `runtime.container`, but it cannot represent authoritative
zones, RRsets, resolver policy, DNSSEC posture, forwarders, dynamic-update
policy, logging posture, or evidence refs without collapsing those facts into
prose or backend-specific config text.

Adjacent ACES surfaces already have narrower jobs:

- `Node.services` records transport bindings such as UDP/TCP 53.
- `runtime.network` records realized container network attachment and observed
  endpoint names, not authoritative zone contents.
- `runtime.container` records per-container resolver configuration.
- `runtime.applications` records HTTP route/API/UI surfaces only.
- `runtime.database_services`, `runtime.identity_authorities`,
  `runtime.file_services`, and `runtime.ssh_servers` each record their own
  protocol/runtime domains.
- `runtime.filesystem_inventory` records evidence paths, not parsed DNS state.
- top-level `relationships` records scenario graph edges.

The design risk is to make transport ports, resolver client settings,
authoritative zone data, BIND/CoreDNS/PowerDNS syntax, raw zone files,
DNSSEC validation posture, and relationships all mean the same thing.

DNS has strong protocol precedents: RFC 1034/1035 define the domain concepts
and resource records, RFC 2181 clarifies RRset semantics, RFC 5936 and RFC
1995 describe zone transfer behavior, RFC 4033/4034/4035 define DNSSEC, RFC
2782 defines SRV RDATA, RFC 2136 defines dynamic updates, and IANA maintains
the DNS parameters registry. Implementation references such as BIND, NSD,
Knot DNS, PowerDNS, CoreDNS, Terraform DNS providers, DNSControl, octoDNS,
Kubernetes DNS, Consul DNS, Zeek DNS logs, ECS DNS fields, and STIX domain
objects are useful lineage and evidence sources. None of them should become
the ACES portable schema or force a server-specific configuration grammar into
SDL.

## Decision

### 1. Model DNS services under node runtime

Add `Node.runtime.dns_services` as optional observed runtime inventory. The
surface represents DNS logical and protocol state hosted by the node, with a
stable `dns_service_id`, an optional same-node `Node.services[].name` owner
reference, implementation family, version, role list, configuration/log file
refs, resolver policy, dynamic-update policy, authoritative/forwarding zones,
bounded settings, and descriptions.

The owning node is implicit from the enclosing node. The transport service
remains explicit through the existing same-node service-ref pattern. DNS facts
must not be placed under `runtime.applications`, `runtime.container`,
`runtime.network`, generic `content`, or prose-only relationships.

### 2. Use RRsets, not raw zone files, as the portable record model

Zones contain stable `zone_id` values and observed zone names. `rrsets` group
records by owner, class, type, and TTL, matching DNS RRset semantics rather
than treating each line in a zone file as a separate portable object.

The model has first-class typed payloads for common operational record shapes:
SOA, NS/PTR/CNAME target-style records, MX, SRV, TXT, A, and AAAA. Additional
IANA RR types use `record_type: other` plus `type_code` and bounded `rdata`,
so the schema can preserve extension records such as SVCB/HTTPS data without
pretending to fully parse every current or future RR type.

Observed DNS names are data and must not be case-folded. Stable ACES ids are
the reference surface.

### 3. Keep resolver policy, zone transfer, dynamic update, logging, and
evidence distinct

Recursive or forwarding behavior belongs in `resolver_policy`: recursion
enabled, allowed recursion clients/selectors, forwarders, forwarding policy,
DNSSEC validation mode, and logging booleans. Zone-transfer posture belongs on
the zone transfer policy. Dynamic updates belong in a separate
dynamic-update policy with allowed clients, key names, and bounded policy text.
Configuration files, zone files, and log files remain evidence refs that can be
cross-checked against `runtime.filesystem_inventory` when that inventory is
present.

Raw BIND, CoreDNS, PowerDNS, NSD, Knot, AXFR, IXFR, `rndc`, query logs,
packet captures, provider API payloads, Terraform plans, DNSControl files,
and octoDNS YAML are evidence inputs. They are not the portable ACES model.

### 4. Publish DNS runtime refs only with matching validation and module
composition

DNS services, zones, and RRsets may be referenced from top-level relationships
using qualified refs:

- `nodes.<node>.runtime.dns_services.<dns_service_id>`
- `nodes.<node>.runtime.dns_services.<dns_service_id>.zones.<zone_id>`
- `nodes.<node>.runtime.dns_services.<dns_service_id>.zones.<zone_id>.rrsets.<rrset_id>`

Named-reference validation and module-import alias rewriting must recognize
the same shapes so a composed scenario cannot silently point at an
un-namespaced or nonexistent DNS object.

## Security and Validation Gates

- Parser/model gate: stable ids are concrete symbols, not `${var}` placeholders
  or mapping keys. Observed names remain data.
- SDL model gate: reject duplicate DNS services in one runtime block,
  duplicate zones in one service, duplicate RRset ids in one zone, duplicate
  RRset owner/class/type bindings, empty RRsets, malformed TTLs/type codes,
  mismatched typed RDATA, and invalid A/AAAA address payloads.
- Semantic validation gate: each DNS service's `service` ref resolves only to
  a same-node `Node.services[]` binding. Configuration, log, and zone-file refs
  resolve to observed runtime filesystem entries when such inventory exists.
- Relationship/reference gate: service, zone, and RRset qualified refs resolve
  in generic relationships and survive module import namespacing.
- Secret-handling gate: TSIG/RNDC/key/password/token/private-key settings must
  omit raw values and use `redacted` or `operator_secret` classifications.
- Contract/schema gate: schemas are generated from Python model sources through
  the repo generator; generated JSON schemas are not edited by hand.

## Guardrails

- Do not add DNS authoritative zones or resolver policy to
  `runtime.applications`.
- Do not overload `Node.services`; it remains a transport binding.
- Do not use `runtime.network` endpoint aliases or generated DNS names as an
  authoritative DNS zone model.
- Do not represent DNS logical state as generic `content` files or raw zone
  file strings.
- Do not encode BIND/CoreDNS/PowerDNS/NSD/Knot syntax as the ACES schema.
- Do not make TTL per-record when the model is RRset-oriented.
- Do not case-fold observed DNS names.
- Do not publish DNS refs into relationships/objectives unless validation,
  module composition aliases, docs, and tests move together.

## Non-Goals

- Building a DNS discovery parser or authoritative zone-file parser.
- Supporting every IANA RR type with typed RDATA in this issue.
- Modeling DNS traffic telemetry, passive DNS, packet captures, or Zeek/ECS
  event logs as first-class SDL runtime records.
- Designing backend provisioning behavior for DNS servers, zones, TSIG keys,
  dynamic updates, or provider APIs.
- Redesigning `Node.services`, `runtime.network`, `runtime.container`,
  `runtime.applications`, top-level `relationships`, runtime snapshots,
  control-plane APIs, persistence, logging, or workflow semantics.

## Consequences

### Positive

- DNS authoritative and recursive runtime state becomes typed, queryable, and
  targetable without corrupting transport services, HTTP applications,
  container resolver options, filesystem evidence, or generic relationships.
- RRset grouping and typed common RDATA preserve protocol semantics while an
  explicit extension path handles less common RR types.
- Evidence refs can be checked against node-scoped filesystem inventory when
  evidence inventory is present.

### Negative

- Node runtime gains another optional inventory surface.
- Consumers that need complete vendor-specific server configuration must retain
  separate evidence artifacts rather than relying on SDL to reproduce raw
  configuration files.

### Risks

- A server-specific configuration dictionary would recreate the original
  ambiguity under a new field name.
- A model that tries to type every RR today would likely lag IANA and become
  brittle; the bounded `other` path is therefore intentional.
- Recording raw TSIG secrets, RNDC keys, private keys, or provider credentials
  could leak sensitive data into fixtures, schemas, diagnostics, logs, or
  snapshots.

## References

- [Lineage and Prior Work](../../explain/sdl/lineage.md) and
  [Design Precedents](../../explain/sdl/precedents.md).
- [RFC 1035](https://www.rfc-editor.org/rfc/rfc1035),
  [RFC 2181](https://www.rfc-editor.org/rfc/rfc2181),
  [RFC 5936](https://www.rfc-editor.org/rfc/rfc5936),
  [RFC 1995](https://www.rfc-editor.org/rfc/rfc1995),
  [RFC 4033](https://www.rfc-editor.org/rfc/rfc4033),
  [RFC 4034](https://www.rfc-editor.org/rfc/rfc4034),
  [RFC 4035](https://www.rfc-editor.org/rfc/rfc4035),
  [RFC 2782](https://www.rfc-editor.org/rfc/rfc2782), and
  [RFC 2136](https://www.rfc-editor.org/rfc/rfc2136).
- [IANA DNS Parameters](https://www.iana.org/assignments/dns-parameters/dns-parameters.xhtml).
- [BIND documentation](https://bind9.readthedocs.io/),
  [NSD documentation](https://nsd.docs.nlnetlabs.nl/),
  [Knot DNS documentation](https://www.knot-dns.cz/documentation/),
  [PowerDNS documentation](https://doc.powerdns.com/), and
  [CoreDNS documentation](https://coredns.io/manual/toc/).
- [DNSControl](https://docs.dnscontrol.org/) and
  [octoDNS](https://github.com/octodns/octodns).
