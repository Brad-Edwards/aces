# Lineage and Prior Work

ACES is not designed as a clean-room language. It is a consolidation layer over
cyber range SDLs, adversary emulation formats, agent-evaluation environments,
runtime architectures, and security event schemas that solve adjacent parts of
the same problem.

This page is a short map of the main influences. It is not a provenance or
compatibility claim, and it is not an exhaustive bibliography. For design
rationale, see [Design Precedents](precedents.md). For a dimension-by-dimension
comparison against precedent systems, including where those systems lead ACES, see
[Related-Work Comparison](related-work-comparison.md).

The normative audit record is
[`contracts/provenance/sdl-lineage-ledger-v1.json`](../../../contracts/provenance/sdl-lineage-ledger-v1.json).
It distinguishes intellectual lineage from artifact/code derivation and from
implementation examples, pins source revisions and bibliographic identities,
and records directional compatibility and notice disposition. An influence
listed on this page is not, by itself, a claim that ACES adopted syntax,
semantics, examples, or code from that source.

## Specification Surface

- [Open Cyber Range SDL](https://documentation.opencyberrange.ee/docs/sdl/reference/)
  is the closest direct SDL precedent. ACES starts from its author-facing
  section surface, including logical nodes, infrastructure, features,
  conditions, entities, injects, events, scripts, and stories. ACES keeps the
  logical scenario surface separate from backend realization instead of
  treating the SDL as a deployment format, and per
  [ADR-073](../../decisions/adrs/adr-073-scoring-reward-language-scope.md) it
  dropped OCR's scoring concepts (metrics/evaluations/TLOs/goals) — graded
  scoring/reward lives in the experiment/evaluator plane.
- [Open Cybersecurity Schema Framework](https://ocsf.io/) influences the event
  and schema side of the architecture. Its schema, profile, extension, and
  attribute-dictionary model is the main precedent for portable telemetry and
  disciplined schema evolution.
- Domain-specific language work, especially the classic DSL literature and
  formal cyber-range DSLs such as VSDL and CRACK, informs the separation
  between concrete YAML syntax, semantic models, validation, compilation, and
  runtime contracts.

## Scenario Concepts

- [CACAO Security Playbooks v2.0](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.pdf)
  informs variables, objective composition, workflow graph structure, and the
  distinction between authored playbook intent and concrete execution.
- [STIX 2.1](https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html)
  informs typed directed relationships and cross-object references. ACES adapts
  that pattern for scenario elements rather than threat-intelligence objects.
- CyRIS, KYPO, OCR, VSDL, and CRACK are prior scenario-definition systems.
  Their strongest shared lesson is that scenario meaning must be more than a
  deployment script.
- SBOM standards such as [CycloneDX](https://cyclonedx.org/specification/overview/)
  and [SPDX](https://spdx.dev/use/specifications/) inform the runtime software
  component identity vocabulary: component type, version, purl/CPE, hashes, and
  package or manifest lineage are useful portable facts. ACES adapts those
  identity concepts under `Node.runtime.software_components`; it does not import
  raw SBOM documents, scanner output, or invocation/capability semantics into
  the SDL schema.

## Directory, Domain, And Identity Authority Semantics

The `runtime.identity_authorities` surface is issue #401's response to an
observed gap in APTL's TechVault AD inventory. It is not a clean-room
invention, but it also is not a clone of any one directory or attack-graph
format.

ACES relies on prior work in four different ways:

- **Scenario-language precedents:** top-level `accounts` keeps the CyRIS account
  placement lineage. CyRIS implements `add_account`/`modify_account` as
  host/user management operations in code
  ([modules.py](https://github.com/crond-jaist/cyris/blob/8b65a30581cdd8e126c7b1fa26db2a4b770b7f17/main/modules.py)),
  so ACES continues to treat `accounts` as curated scenario/provisioning
  resources. ACES does not infer a full directory service from those accounts.
- **Primary industry standards:** LDAP/X.500 ([RFC 4510](https://www.rfc-editor.org/rfc/rfc4510),
  [RFC 4512](https://www.rfc-editor.org/rfc/rfc4512)), Kerberos
  ([RFC 4120](https://www.rfc-editor.org/rfc/rfc4120)), SCIM
  ([RFC 7643](https://www.rfc-editor.org/rfc/rfc7643),
  [RFC 7644](https://www.rfc-editor.org/rfc/rfc7644)),
  [SAML V2.0 Assertions and Protocols](http://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf),
  OAuth 2.0 ([RFC 6749](https://www.rfc-editor.org/rfc/rfc6749)),
  [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0-18.html),
  [NIST SP 800-63C-4](https://doi.org/10.6028/NIST.SP.800-63C-4),
  [NIST SP 800-162](https://doi.org/10.6028/NIST.SP.800-162), and
  [NIST SP 800-207](https://doi.org/10.6028/NIST.SP.800-207) supply
  terminology for authorities, naming contexts, realms, issuers, tenants,
  subjects, groups, attributes, policy inputs, federation boundaries,
  attribute-based authorization, and zero-trust identity/resource boundaries.
  ACES adapts their shared concepts, not their full protocol objects.
- **Primary access-control literature:** Lampson's
  [access matrix](https://doi.org/10.1145/775265.775268), Saltzer and
  Schroeder's [protection principles](https://doi.org/10.1109/PROC.1975.9939),
  Ferraiolo/Kuhn [RBAC](https://www.nist.gov/publications/role-based-access-controls),
  Sandhu et al.'s [RBAC96 model](https://doi.org/10.1109/2.485845), and NIST
  ABAC support the separation among subject, attribute, policy, relationship,
  and authority boundary. That is why ACES models policies and
  membership/trust/federation edges as first-class records instead of storing
  them only as prose or untyped relationship properties.
- **Downstream/evidence precedents:** BloodHound/OpenGraph validates the
  usefulness of node/edge identity graphs for attack-path analysis, while OCSF,
  UCO, and CASE are evidence and concept-authority influences. ACES does not
  make any of them the canonical runtime inventory schema: BloodHound graphs
  are downstream analysis overlays, OCSF is telemetry/event-oriented, and
  UCO/CASE are concept/evidence vocabularies broader than the SDL authoring
  surface.

Reference status is explicit. The identity and access-control authorities above
are primary standards, government reports, or peer-reviewed access-control
literature. The cyber-range and V&V sources are adjacent methodological support:
Russo/Costa/Armando, Swiler, Oberkampf/Roy, and Sargent are citable proceedings,
technical-report, or book sources; Garg et al. is used as a current survey
preprint rather than as settled normative authority. The working Zotero library
tracks these identity-authority references under `aces-sdl-identity-authority`
and the adjacent V&V subset under `adjacent-vv-lineage`; because that library is
private, the Garg et al. preprint citation is also snapshotted in-repo under
[`docs/research/primary/`](../../research/primary/literature/cyber-range-scenario-survey.md)
so the reference is verifiable from the repository alone.

The design deliberately keeps provider-stable identifiers as data rather than
as ACES reference identity. AD SIDs/objectGUIDs, LDAP DNs/entryUUIDs, SCIM
`id`/`externalId`, SAML NameIDs, and OIDC `iss` + `sub` values are preserved in
specific fields or bounded attributes when needed for translation/evidence, but
the portable ACES references are stable `*_id` symbols scoped by the scenario
and authority. Within one authority those ids share a single local namespace,
so an id cannot be reused across service, subject, policy, relationship, and
authority records. This matches the verification/validation posture in the
cyber-range literature (for example Russo, Costa, and Armando's
[Scenario Design and Validation for Next Generation Cyber Ranges](https://doi.org/10.1109/NCA.2018.8548324)
(IEEE NCA 2018), and Garg, Boualouache, Imeri, and Roth's
[A Survey of Cyber Range Training Exercise Scenario Description, Generation, and Execution](https://doi.org/10.36227/techrxiv.175942879.94813577/v1)
(TechRxiv preprint, 2025 — snapshotted in-repo at
[docs/research/primary](../../research/primary/literature/cyber-range-scenario-survey.md)),
and Swiler plus Oberkampf/Roy/Sargent on
[cyber-emulation V&V](https://doi.org/10.2172/1897016),
[scientific-computing V&V](https://doi.org/10.1017/CBO9780511760396), and
[simulation-model V&V](https://doi.org/10.1109/WSC.2010.5679166)): a model
should state what it can preserve and compare rather than smuggle
backend/vendor assumptions into an ambiguous field.

## DNS Service Runtime Semantics

The `runtime.dns_services` surface is issue #426's response to an observed
gap for DNS authoritative and recursive runtime inventory. It is not a clone
of any one DNS server configuration language, provider API, or DNS telemetry
format.

ACES relies on prior work in four ways:

- **Scenario-language precedents:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
  model scenario topology, deployable services/features, and validation or
  deployment concerns. They do not expose a portable first-class DNS zone,
  RRset, resolver-policy, or DNSSEC-posture inventory that ACES could reuse
  directly, so ACES introduces a typed node-scoped runtime surface rather than
  encoding the state inside `Node.services`, `runtime.applications`,
  `runtime.network`, or raw content files.
- **Primary DNS standards:** DNS concepts and record wire semantics come from
  [RFC 1035](https://www.rfc-editor.org/rfc/rfc1035). RRset grouping follows
  [RFC 2181](https://www.rfc-editor.org/rfc/rfc2181). Zone transfer and
  incremental transfer posture are informed by
  [RFC 5936](https://www.rfc-editor.org/rfc/rfc5936) and
  [RFC 1995](https://www.rfc-editor.org/rfc/rfc1995). DNSSEC posture follows
  [RFC 4033](https://www.rfc-editor.org/rfc/rfc4033),
  [RFC 4034](https://www.rfc-editor.org/rfc/rfc4034), and
  [RFC 4035](https://www.rfc-editor.org/rfc/rfc4035). SRV RDATA follows
  [RFC 2782](https://www.rfc-editor.org/rfc/rfc2782), dynamic update posture
  follows [RFC 2136](https://www.rfc-editor.org/rfc/rfc2136), and extension
  types are bounded by the
  [IANA DNS Parameters](https://www.iana.org/assignments/dns-parameters/dns-parameters.xhtml)
  registry. ACES adapts shared protocol concepts rather than importing raw
  zone-file syntax.
- **Server and configuration precedents:** BIND, NSD, Knot DNS, PowerDNS,
  CoreDNS, Terraform DNS providers, DNSControl, octoDNS, Kubernetes DNS, and
  Consul DNS show the recurring implementation facts ACES must preserve:
  authoritative zones, RRsets, forwarders, recursion controls, transfer policy,
  dynamic updates, DNSSEC validation/signing posture, and evidence sources.
  These references are implementation lineage, not schema authority.
- **Evidence and downstream consumers:** OCSF/ECS DNS fields, Zeek DNS logs,
  STIX domain-name objects, passive DNS, provider APIs, AXFR/IXFR captures,
  and backend inspect payloads remain evidence or downstream translation
  concerns. ACES records bounded runtime inventory and evidence refs; it does
  not make query telemetry or raw server config the SDL model.

Observed DNS names are preserved as data and are not case-folded. Portable
ACES references are stable `dns_service_id`, `zone_id`, and `rrset_id` symbols.
This follows the same validation posture used elsewhere in SDL: the model
states which protocol facts it can preserve, and it leaves server-specific
syntax as evidence rather than smuggling that syntax into untyped fields.

## Security-Monitoring Manager Runtime Semantics

The `runtime.security_monitoring_managers` surface is issue #428's response to
an observed gap for SIEM and security-monitoring manager inventory. It is not a
clone of Wazuh, Splunk, Elastic Security, Security Onion, Microsoft Sentinel,
or any one event schema. It is a portable node-scoped runtime inventory for the
manager facts that surrounding ACES surfaces cannot own.

ACES relies on prior work in four ways:

- **Scenario-language precedents:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
  model topology, deployable services/features, tasks, validation, and
  deployment concerns. None expose a portable first-class security-monitoring
  manager inventory. ACES therefore adds a typed `Node.runtime` surface rather
  than encoding manager state inside `Node.services`, `runtime.processes`,
  `runtime.service_manager_units`, `runtime.filesystem_inventory`, or raw
  content files.
- **Log-management and security-monitoring literature:** NIST SP 800-92 frames
  computer security log management as infrastructure and processes for
  collection, analysis, storage, maintenance, and operational use. ACES adapts
  that infrastructure/process split by recording manager identity, listeners,
  modules, agents, groups, content corpora, settings, and evidence refs without
  making log telemetry itself the SDL runtime inventory.
- **Implementation precedents:** Wazuh demonstrates the recurring manager
  concepts ACES must preserve: a central manager/server, agent connection and
  enrollment services, an analysis engine, manager API, agent groups and shared
  configuration, rules, decoders, queues, integrations, and manager components.
  These are implementation lineage and evidence sources, not schema authority.
- **Event and detection-content precedents:** OCSF is vendor-neutral event
  schema lineage, and Sigma is portable detection-rule lineage. They justify a
  product-neutral posture for content and telemetry vocabulary. ACES records a
  bounded parsed detection-definition manifest for loaded definitions, but it
  does not import OCSF events, raw Sigma rule bodies, Wazuh XML, SIEM queries,
  or alert records into SDL as first-class runtime records.

Portable ACES references are stable `security_monitoring_manager_id`, `listener_id`,
`component_id`, `agent_id`, `group_id`, `content_id`, `definition_id`, and
`setting_id` symbols. Native manager identifiers, daemon names, file names,
ruleset ids, rule ids, decoder names, agent labels, and API ids are preserved
as observed data or evidence when needed, but they are not automatically ACES
reference identity. Manager settings such as passwords, enrollment secrets, API
tokens, shared keys, keytabs, or private keys may be scenario values; explicit
`redacted`/`operator_secret` classifications omit raw values when the author
marks a value withheld.

The resulting model follows the same V&V posture as the DNS, mail, database,
file-service, and identity-authority surfaces: state which manager concepts
are stable enough to compare, target, and validate; keep vendor-specific
configuration, telemetry, rule-engine execution, and raw rule syntax as
evidence or downstream translation concerns.

## Generic Runtime Service Listener Semantics

The `runtime.service_listeners` surface is issue #431's response to an
observed gap in APTL's MISP container inventory. It is not a replacement for
authored services, host-published port bindings, protocol-specific runtime
inventories, or scanner output. It is the bounded node-scoped place for generic
observed listener facts: bind endpoint, port, transport, address family,
listener scope, owner, readiness evidence, and provenance.

ACES relies on prior work in four ways:

- **Scenario-language precedents:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
  model topology, deployable services/features, tasks, validation, and
  deployment concerns. They do not expose a portable first-class observed
  listener inventory with bind-address/interface semantics. ACES therefore
  adds a typed `Node.runtime` surface instead of hiding bind state in
  `Node.services`, `runtime.network.published_ports`, `runtime.applications`,
  or free-text descriptions.
- **Host and process-inventory precedents:** osquery's
  [`listening_ports`](https://fleetdm.com/tables/listening_ports) table keeps
  address, port, protocol, and owning PID as separate facts. systemd socket
  units such as
  [`ListenStream=` and `ListenDatagram=`](https://www.freedesktop.org/software/systemd/man/latest/systemd.socket.html)
  show the operational split between a socket endpoint and the service it can
  activate. ACES adapts that separation through `service`, `process_ref`, and
  listener endpoint fields without importing systemd unit syntax.
- **Container and orchestrator precedents:** Docker
  [port publishing](https://docs.docker.com/get-started/docker-concepts/running-containers/publishing-ports/)
  separates a container-side listener from a host-side published binding.
  Kubernetes distinguishes container ports, Services,
  [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/),
  and readiness/liveness/startup
  [probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/).
  ACES keeps in-node listener state, host publication, and readiness evidence
  as adjacent but distinct runtime facts.
- **Evidence and telemetry precedents:** Nmap
  [XML output](https://nmap.org/book/output-formats-xml-output.html) can
  report remotely observed port state and service hints, but it cannot prove a
  local bind address or owning process by itself. OpenTelemetry server
  [address and port attributes](https://opentelemetry.io/docs/specs/semconv/attributes-registry/server/)
  and OCSF [network endpoint](https://schema.ocsf.io/) vocabulary are useful
  product-neutral checks for endpoint terminology. They remain evidence and
  downstream translation lineage rather than SDL schema authority.

Portable ACES references are stable listener ids under
`nodes.<node>.runtime.service_listeners.<listener_id>`. Native process names,
PIDs, scanner table names, service-manager unit names, and probe strings remain
observed data or evidence unless the author explicitly uses them in bounded ref
fields. A wildcard bind address inside a container or node namespace is not
automatically host-public; host exposure remains `runtime.network.published_ports`.

## Network Detection Engine Runtime Semantics

The `runtime.network_detection_engines` surface is issue #430's response to an
observed gap for IDS/NDR engine inventory. It is not a Suricata clone and does
not interpret rule languages or alert telemetry. It records portable,
node-scoped facts about a detection engine that adjacent surfaces cannot own:
enabled app-layer parser families, loaded rule-source inventories, network
zoning/address-set variables, bounded output streams, reload/control channels,
and evidence refs.

ACES relies on prior work in four ways:

- **Scenario-language precedents:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
  model topology, deployable services/features, tasks, validation, and
  deployment concerns. None expose a portable first-class detection-engine
  inventory. ACES therefore adds a typed `Node.runtime` surface rather than
  encoding engine state inside `Node.services`, `runtime.network_sensors`,
  `runtime.filesystem_inventory`, `runtime.software_components`, or prose
  relationships.
- **IDS/NDR tooling:** Suricata, Snort, Zeek, Security Onion, and NDR products
  show recurring engine facts ACES must preserve: parser coverage, rule or IOC
  sources, address sets, output streams, reload controls, and evidence refs.
  These references are implementation lineage, not schema authority.
- **Telemetry and rule-content precedents:** OCSF, ECS, STIX, Sigma, YARA, and
  vendor rule formats inform vocabulary boundaries. ACES does not replace
  those schemas or inline their events, rules, packets, or IOC payloads.
- **Evidence discipline:** raw rules, alerts, packet captures, IOC exports,
  config files, and backend inspect payloads remain evidence artifacts or
  downstream translation inputs. The SDL stores bounded inventory and refs.

## Application-Internal Authorization Semantics

The `runtime.app_authorizations` surface is the SCN-010 response to the
most-replicated expressivity gap in the corpus: application-internal RBAC that
recurs across search clusters, key-value stores, dashboards, threat-intel
platforms, and case-management systems. It is deliberately not a wire-protocol
directory (that stays `runtime.identity_authorities`) and not a database engine
GRANT surface (that stays `runtime.database_services`). Its defining addition is
the resource-scoped permission grant — role → actions → resource pattern — that
neither adjacent surface can own.

ACES relies on prior work in four ways:

- **Scenario-language precedents:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
  model topology, deployable services/features, and validation/deployment
  concerns. None expose a portable first-class application-internal RBAC store,
  so ACES adds a typed node-scoped seam rather than overloading
  `runtime.identity_authorities`, `runtime.database_services`, or
  `runtime.applications`.
- **Primary RBAC and ABAC standards:** Ferraiolo and Kuhn's
  [Role-Based Access Controls](https://www.nist.gov/publications/role-based-access-controls),
  Sandhu et al.'s [RBAC96 model](https://doi.org/10.1109/2.485845),
  [ANSI INCITS 359](https://webstore.ansi.org/standards/incits/ansiincits3592004)
  (the RBAC standard), and NIST
  [SP 800-162](https://csrc.nist.gov/publications/detail/sp/800-162/final) ABAC
  supply the model's spine: principals, roles, role-permission assignment,
  user-role assignment, and resource-scoping. The resource-scoped
  `permission_grant` is anchored by RBAC96 / ANSI INCITS 359
  permission-assignment and SP 800-162 resource-scoping; tier placement
  (storage RBAC versus presentation RBAC) is derived from which spine references
  the authorization, not declared on the model.
- **Product RBAC precedents:** OpenSearch Security, Elasticsearch security,
  Cassandra `system_auth`, Redis ACLs, Kibana/OpenSearch Dashboards roles,
  MISP/TheHive/Cortex role catalogs, and Shuffle RBAC show recurring facts ACES
  must preserve: principals with reserved/hidden flags, named roles,
  resource-scoped grants, role mappings, and tenants. These are implementation
  lineage, not schema authority.
- **Credential discipline:** raw bcrypt hashes, API keys, and passwords are
  never stored. A principal records only a `credential_classification`
  (`none` / `redacted` / `operator_secret`), and the model has no field that can
  hold a raw secret.

## Scheduled-Job Cadence Semantics

The `runtime.scheduled_jobs` surface is the SCN-010 response to the gap for
recurring node-scoped work (gap IDs MISP-DSS-02 / TIP-004) that
`runtime.service_manager_units` cannot express: a bare-container ENTRYPOINT
cadence loop has no systemd unit. The surface is deliberately hollowed to
cadence plus run-state only; inputs, outputs, and trigger targets belong to the
referencing forwarding agent, and an event-triggered task is a trigger
relationship rather than a recurrence.

ACES relies on prior work in four ways:

- **Scenario-language precedents:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
  model topology, deployable services/features, and validation/deployment
  concerns. None expose a portable first-class product-neutral scheduled-job
  cadence, so ACES adds a typed node-scoped seam rather than overloading
  `runtime.service_manager_units` (systemd-scoped) or the forwarding agent.
- **Primary recurrence standards:** POSIX.1-2017
  [crontab](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/crontab.html)
  and RFC 5545 [iCalendar RRULE](https://www.rfc-editor.org/rfc/rfc5545) supply
  the product-neutral recurrence vocabulary that the closed `schedule.kind`
  (`interval` / `cron` / `calendar`) abstracts.
- **Scheduler precedents:** systemd
  [`systemd.timer`](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)
  and Kubernetes
  [CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
  show recurring scheduler facts ACES must preserve as cadence and run-state.
  These are implementation lineage, not schema authority.
- **Run-state observability:** NIST
  [SP 800-92](https://csrc.nist.gov/publications/detail/sp/800-92/final)
  (log management) and
  [SP 800-137](https://csrc.nist.gov/publications/detail/sp/800-137/final)
  (continuous monitoring) frame the observed `run_state`
  (`last_run` / `next_run` / `last_result`) as monitoring evidence rather than
  control intent.

## Non-Relational Datastore Semantics

The `runtime.datastore_services` surface is the SCN-010 (DSL-132) response to a
gap for the participant-observable logical state of *non-relational* datastores
— the search cluster, wide-column store, and key-value store that the
irreducibly-relational `runtime.database_services` cannot shape. Its defining
addition is the open `data_model` discriminator paired with a
`require_profile_for_data_model` guard that makes each data model's defining
geometry (search shard/replica counts, wide-column replication, key-value
persistence, and bounded search-index mapping manifests) executable rather than
optional. Search-index mappings and templates are captured as bounded manifests
with counts, summaries, digests, refs, and evidence pointers rather than as raw
backend JSON bodies.

ACES relies on prior work in four ways:

- **Scenario-language precedents:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
  model topology, deployable services/features, and validation/deployment
  concerns. None expose a portable first-class non-relational datastore logical
  state, so ACES adds a typed node-scoped seam rather than overloading
  `runtime.database_services` (irreducibly relational), `Node.services`
  (transport), or `runtime.software_components` (component identity).
- **Primary data-model and consensus standards:** Codd's relational model
  ([CACM 13(6)](https://doi.org/10.1145/362384.362685)) and
  [ISO/IEC 9075](https://www.iso.org/standard/76583.html) (SQL) bound what stays
  relational; Zobel and Moffat's
  [inverted-index survey](https://doi.org/10.1145/1132956.1132959) anchors the
  search-index shard/replica geometry; Ongaro and Ousterhout's
  [Raft](https://raft.github.io/raft.pdf) and Gilbert and Lynch's
  [CAP proof](https://doi.org/10.1145/564585.564601) anchor cluster/replication
  posture.
- **Engine precedents:** Lakshman and Malik's
  [Cassandra](https://doi.org/10.1145/1773912.1773922), DeCandia et al.'s
  [Dynamo](https://doi.org/10.1145/1323293.1294281), Chang et al.'s
  [Bigtable](https://research.google/pubs/pub27898/), and Redis
  [RESP3](https://github.com/redis/redis-specifications/blob/master/protocol/RESP3.md)
  / [ACL](https://redis.io/docs/management/security/acl/) /
  [persistence](https://redis.io/docs/management/persistence/) show recurring
  facts ACES must preserve: keyspaces with replication strategy/factor, search
  shard/replica geometry, and RDB/AOF/eviction persistence. These are
  implementation lineage, not schema authority.
- **Hardening and transport discipline:** NIST
  [SP 800-92](https://csrc.nist.gov/publications/detail/sp/800-92/final),
  [SP 800-53](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final),
  and [SP 800-209](https://csrc.nist.gov/publications/detail/sp/800-209/final)
  (storage security), with [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446)
  (TLS 1.3) and [RFC 5280](https://www.rfc-editor.org/rfc/rfc5280) (PKIX), frame
  the transport-security posture and explicit redaction classifications. Raw
  key material and credentials may be scenario-realization facts when they
  belong to the synthetic range; out-of-scenario operator secrets remain
  outside SDL inventory.

The node-scoped extension (SCN-010 DSL-141,
[ADR-058](../../decisions/adrs/adr-058-datastore-node-engine-provenance-and-endpoints.md))
closes the `wazuh.indexer` parity gap (Brad-Edwards/aptl#341) that ADR-048 left
at the node level: typed engine provenance (version, build hash, build type),
JVM/process memory posture (initial/maximum heap bytes, `mlockall`), a per-node
engine-plugin inventory with per-plugin version, and a product-neutral
client/peer endpoint inventory. The Elasticsearch/OpenSearch
[Nodes Info API](https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-nodes-info.html)
reports each of these per node; the client/peer listener split is structural
across the search-cluster tech class (OpenSearch http/transport, Cassandra
native/internode, Redis client/cluster-bus), which is why ACES types an
engine-neutral `role` taxonomy rather than engine-named address fields.

## Security-Platform Application Semantics

The `runtime.platform_applications` surface is the SCN-010 (DSL-133) response to
a gap for the participant-observable runtime state of security platform
applications — threat-intelligence platforms, SOAR, analyzer engines, case
management, and analytics dashboards. Its defining addition is the open
`platform_kind` discriminator paired with a `require_profile_for_platform_kind`
guard, plus content objects modeled as bounded parsed manifests (typed kind +
bounded attributes + typed references) rather than raw object bodies.

ACES relies on prior work in four ways:

- **Scenario-language precedents:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
  model topology, deployable services/features, and validation/deployment
  concerns. None expose a portable first-class security-platform application
  inventory, so ACES adds a typed node-scoped seam rather than overloading
  `runtime.applications` (HTTP routes) or `runtime.software_components`
  (component identity).
- **Primary content and intelligence-sharing standards:** RDF 1.1
  ([concepts](https://www.w3.org/TR/rdf11-concepts/)) with Angles and Gutierrez's
  [graph-database survey](https://doi.org/10.1145/1322432.1322433) frame typed
  references over raw bodies;
  [STIX 2.1](https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html) /
  [TAXII 2.1](https://docs.oasis-open.org/cti/taxii/v2.1/taxii-v2.1.html), the
  [MISP data model](https://www.misp-project.org/datamodels/), FIRST
  [TLP 2.0](https://www.first.org/tlp/), MITRE
  [ATT&CK](https://attack.mitre.org/), NIST
  [SP 800-150](https://csrc.nist.gov/publications/detail/sp/800-150/final), and
  [ISO/IEC 27010](https://www.iso.org/standard/68427.html) anchor the
  threat-intel content profile and releasability markings; NIST
  [SP 800-61r2](https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final)
  / [r3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) anchors
  the case-management incident-handling profile.
- **Automation and observability precedents:** OASIS
  [CACAO v2.0](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)
  and [OpenC2](https://docs.oasis-open.org/openc2/oc2ls/v1.0/oc2ls-v1.0.html)
  frame the SOAR/analyzer execution profile with the boundary stated explicitly:
  ACES records the workflow/analyzer *inventory* and execution policy, not
  playbook execution semantics. NIST
  [SP 800-92](https://csrc.nist.gov/publications/detail/sp/800-92/final) and
  [ISO/IEC/IEEE 42010](https://www.iso.org/standard/74393.html) frame the
  dashboard saved-object and upstream-binding posture as architecture/monitoring
  evidence. These are implementation lineage, not schema authority.
- **Transport and federation discipline:** [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110)
  (HTTP semantics), [RFC 7239](https://www.rfc-editor.org/rfc/rfc7239)
  (forwarded), and [RFC 6749](https://www.rfc-editor.org/rfc/rfc6749) (OAuth 2.0)
  bound the connector/binding posture; raw bodies, credentials, and key material
  are never stored — the surface records bounded manifests and classifications.

## Forwarding And Intel-Sync Agent Semantics

The `runtime.forwarding_agents` surface is the SCN-010 (DSL-136) response to a
gap for the participant-observable agent-side shipping state — the
`(source, transform, ship-target, buffer)` spine of a log-forwarding sidecar and
the intel-sync co-process — that the SIEM/security-monitoring *manager*
(`runtime.security_monitoring_managers`) and the detection-engine *consumer*
(`runtime.network_detection_engines`) provably cannot shape. Its defining
addition is the open `agent_kind` discriminator paired with a
`require_profile_for_agent_kind` guard that makes each member's defining shipping
profile executable rather than optional.

ACES relies on prior work in four ways:

- **Scenario-language precedents:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
  model topology, deployable services/features, and validation/deployment
  concerns. None expose a portable first-class forwarding-agent shipping
  inventory, so ACES adds typed node-scoped and scenario-level seams rather than
  overloading the manager surface, the detection-engine surface, or
  `runtime.scheduled_jobs` (cadence-only).
- **Primary log-transport standards:** The syslog family —
  [RFC 5424](https://www.rfc-editor.org/rfc/rfc5424) (syslog protocol),
  [RFC 5425](https://www.rfc-editor.org/rfc/rfc5425) (TLS transport),
  [RFC 6587](https://www.rfc-editor.org/rfc/rfc6587) (TCP framing), and
  [RFC 3164](https://www.rfc-editor.org/rfc/rfc3164) (BSD syslog) — bound the
  ship-target protocol/endpoint posture, while NIST
  [SP 800-92](https://csrc.nist.gov/publications/detail/sp/800-92/final) anchors
  the source → collector → aggregator pipeline shape and NIST
  [SP 800-137](https://csrc.nist.gov/publications/detail/sp/800-137/final) (ISCM)
  frames continuous-monitoring collection as a defining concern.
- **Intel-to-content precedents:**
  [STIX 2.1](https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html) /
  [TAXII 2.1](https://docs.oasis-open.org/cti/taxii/v2.1/taxii-v2.1.html), NIST
  [SP 800-150](https://csrc.nist.gov/publications/detail/sp/800-150/final), Bianco's
  [Pyramid of Pain](https://detect-respond.blogspot.com/2013/03/the-pyramid-of-pain.html),
  and MITRE [ATT&CK](https://attack.mitre.org/) frame the `ioc_to_rule`
  intel-sync transform — the API-pull-to-rule-reload shape — that the
  `content_sync` profile makes executable.
- **Forwarder implementation lineage:** Elastic
  [Beats](https://www.elastic.co/beats/) and the
  [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/) show the
  recurring source/transform/ship/buffer facts ACES preserves (tailed inputs,
  pipelines, exporters, back-pressure queues). These are implementation lineage,
  not schema authority; enrollment identities carry only their closed
  classification lattice, while forwarding settings use explicit redaction
  classifications rather than name-derived omission.

## Container-Spawn Orchestration-Authority Semantics

The `runtime.orchestration_authorities` surface is the SCN-010 (DSL-137) response
to a gap for the participant-observable authority to *spawn* containers/workloads
through a control interface — a SOAR orchestrator or analyzer engine holding
`docker.sock` read-write. `RuntimeControlInterface` types the docker.sock *shell*
but carries no field for what the holder is authorized to *do*; this surface adds
the spawn contract (engine, scope, spawn templates, lifecycle policy, realized
children) referencing that shell, paired with a `require_profile_for_privilege_class`
guard that makes the host-root privilege-escalation fact executable.

ACES relies on prior work in four ways:

- **Scenario-language precedents:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
  model topology, deployable services/features, and validation/deployment
  concerns. None expose a portable first-class container-spawn authority
  inventory, so ACES adds a typed node-scoped seam referencing the existing
  `runtime.local_control_interfaces` shell rather than duplicating it.
- **Primary runtime and orchestration standards:** The OCI
  [Runtime Spec](https://github.com/opencontainers/runtime-spec) and
  [Image Spec](https://github.com/opencontainers/image-spec) bound the engine /
  spawn-template posture, and the Kubernetes
  [controller pattern](https://kubernetes.io/docs/concepts/architecture/controller/)
  anchors the desired-state spawn-template / realized-children reconciliation
  shape this surface records as observed state.
- **Privilege and hardening precedents:** NIST
  [SP 800-190](https://csrc.nist.gov/publications/detail/sp/800-190/final)
  (container security) and the
  [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker) 5.x control
  family frame the read-write `docker.sock` exposure as a host-root-equivalent
  privilege escalation, and MITRE ATT&CK
  [T1610](https://attack.mitre.org/techniques/T1610/) (Deploy Container) and
  [T1611](https://attack.mitre.org/techniques/T1611/) (Escape to Host) anchor the
  adversary relevance the `host_root_equivalent` profile makes executable.
- **Engine API lineage:** The
  [Docker Engine API](https://docs.docker.com/engine/api/) shows the spawn /
  lifecycle surface (container create/start/stop, image references) ACES records
  as inventory. This is implementation lineage, not schema authority; the spawn
  contract is referenced through `control_interface_ref`, never duplicating the
  control-interface shell.

## File-Sharing And Resource-Access Semantics

The `runtime.file_services` surface is issue #421's response to a gap
observed while encoding the APTL TechVault fileshare container. It is not
a clone of any one file-sharing protocol or ACL vocabulary, and the
expected-but-absent extension to `runtime.filesystem_inventory` follows
the same posture.

ACES relies on prior work in four ways:

- **Scenario-language precedents:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and
  CRACK model scenario topology, deployable services/features, and
  validation/deployment concerns. None expose a portable first-class
  share-permission/passdb inventory that ACES could reuse directly, which
  is why ACES introduces a typed node-scoped seam rather than encoding the
  state inside `Node.services` or `runtime.applications`.
- **Primary protocol and filesystem-permission standards:** Microsoft's
  [MS-SMB2](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-smb2/5606ad47-5ee0-437a-817e-70c366052962),
  [SMB/CIFS overview](https://learn.microsoft.com/en-us/windows/win32/fileio/microsoft-smb-protocol-and-cifs-protocol-overview),
  the Samba [`smb.conf`](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html)
  and [`pdbedit`](https://www.samba.org/samba/docs/current/man-html/pdbedit.8.html)
  references, the Linux [ACL man page](https://man7.org/linux/man-pages/man5/acl.5.html),
  POSIX.1e ACL semantics (Grünbacher,
  [POSIX Access Control Lists on Linux](https://www.usenix.org/legacy/event/usenix03/tech/freenix03/full_papers/gruenbacher/gruenbacher.pdf),
  USENIX ATC 2003), Microsoft's
  [Windows ACL documentation](https://learn.microsoft.com/en-us/windows/win32/secauthz/access-control-lists)
  and [security descriptor string format](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-descriptor-string-format),
  and [NFSv4.1 (RFC 8881)](https://www.rfc-editor.org/rfc/rfc8881) supply
  terminology for shares/exports, share-level access modes, passdb
  semantics, anonymous and guest subjects, POSIX vs. Windows ACL
  families, and NFSv4 ACEs. ACES adapts their shared concepts (subject, resource,
  action, effect, basis) rather than importing any single vendor ACL
  algebra. The access-control literature already cited above
  (Lampson, Saltzer/Schroeder, RBAC96, NIST ABAC) justifies that
  subject/resource/action/policy/observation split.
- **Resource-relation modeling:** Pang et al.'s
  [Zanzibar: Google's Consistent, Global Authorization System](https://research.google/pubs/zanzibar-googles-consistent-global-authorization-system/)
  (USENIX ATC 2019) is design input for portable relationship-tuple
  authorization. ACES uses it as a cross-check that bounded
  subject/relation/resource records are workable at scale; it is not
  forced into the SDL as a global authorization framework, and ACES does
  not encode share access only as relationship edges.
- **Evidence and downstream consumers:** OCSF, UCO, CASE, STIX, and SBOM
  standards remain evidence/event/concept influences (already discussed
  above). Per-share probe outcomes are recorded as evidence-bearing
  observations under the file-service inventory; they support but do not
  silently replace authored share policy.

`RuntimeFilesystemEntry.presence` is grounded in the same V&V posture as
the identity-authority surface: an inventory model should preserve the
distinction between present-observed state and expected-but-absent state
rather than collapsing both into a single field. Russo/Costa/Armando,
Oberkampf/Roy, and Sargent's V&V sources cited above are the methodological
backing — what a model can or cannot represent must be explicit so
downstream completeness/conformance checks can act on it.

## Mail-Service Logical State Semantics

The `runtime.mail_services` surface is issue #420's response to a gap observed
while encoding the APTL TechVault mailserver container. It is not a clone of
Postfix, Dovecot, Docker Mailserver, or an RFC object tree. It is a portable
node-scoped runtime inventory for mail-service logical facts that surrounding
ACES surfaces cannot own.

ACES relies on prior work in four ways:

- **Scenario-language precedents:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
  model topology, deployable services/features, accounts, tasks, and
  validation/deployment concerns. None expose a portable first-class
  mail-server logical-state inventory, which is why ACES adds a typed
  `Node.runtime` surface rather than encoding SMTP/IMAP state inside
  `Node.services`, `runtime.applications`, filesystem entries, content, or
  generic accounts.
- **Protocol and service concepts:** SMTP transport/delivery, message
  submission, IMAP access, POP3/LMTP/Sieve extension points, TLS/STARTTLS
  posture, mailboxes, aliases, domains, queues, and MTA/MDA configuration
  supply terminology. ACES adapts these as provider-neutral fields for
  listeners, capabilities, auth mechanisms, mailbox state, routing, queues, and
  settings.
- **Evidence and redaction lineage:** Mailserver discovery output, `postconf`
  and `doveconf` command output, compose files, setup scripts, filesystem
  inventory, and participant probes are evidence/provenance sources. They do
  not become raw config dumps in SDL. Secret-bearing settings must omit values,
  and mailbox records carry credential-strength classification rather than
  passwords or hashes.
- **Relationship semantics:** STIX-style typed edges
  ([OASIS STIX 2.1](https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html)
  SRO) remain the top-level relationship surface. `RelationshipMailAccess` adds
  mail-specific protocol/auth/TLS/mailbox/domain/listener details to those edges
  without promoting mail relationships into a new root section. Three further
  typed subtypes follow the same discipline (SCN-010 §5.7, ADR-052):
  `RelationshipForwardingEdge` carries a forwarding / intel-sync agent's
  inter-node trust edge (anchored in RFC 5424 / 5425 / 6587 / 3164 syslog
  transport and NIST SP 800-92 source -> collector tiering, reusing the
  manager-side `RuntimeSecurityMonitoringListenerRole` lattice rather than
  forking one); `RelationshipServiceIntegration` carries a platform
  consumer-to-engine integration (anchored in NIST SP 800-92 and RFC 6749
  OAuth 2.0 for the API-key auth principal); and `RelationshipProxyUpstream`
  carries a reverse-proxy / gateway route-to-origin hop (anchored in RFC 9110 /
  RFC 7239, NIST SP 800-44, and the Kubernetes Ingress / Gateway API origin
  model). None of the three promotes its edge into a new root section; cross-ref
  resolution and the two cross-scope agreement guards live in the semantic
  validator (see validation.md).

The result preserves the same V&V posture as database and file-service runtime
surfaces: ACES states which mail concepts are stable enough to compare and
which dynamic queue/log/config details remain evidence or bounded settings.

## Participant Semantics

- [OpenAI Gym](https://arxiv.org/abs/1606.01540),
  [Gymnasium](https://arxiv.org/abs/2407.17032),
  [PettingZoo](https://arxiv.org/abs/2009.14471),
  and [OpenSpiel](https://arxiv.org/abs/1908.09453) inform the agent-facing
  interface vocabulary: actions, observations, rewards, resets, local histories,
  imperfect information, and multi-agent interaction.
- POMDP, Dec-POMDP, POSG, and Markov-game literature — with
  [Bernstein, Givan, Immerman, and Zilberstein's complexity result](https://doi.org/10.1287/moor.27.4.819.297)
  and [Oliehoek and Amato's Dec-POMDP monograph](https://doi.org/10.1007/978-3-319-28929-8)
  as anchors — is the theoretical lineage behind ACES's insistence that
  participant-visible observations are not world truth, and that
  multi-participant behavior cannot be reduced to a single centralized state
  stream. [Mean-field game theory](https://doi.org/10.1007/s11537-007-0657-8)
  covers the population-limit regime ACES records as mean-field nodes.
- Interpreted systems
  ([Fagin, Halpern, Moses, Vardi](https://mitpress.mit.edu/9780262562003/reasoning-about-knowledge/)),
  [dynamic epistemic logic](https://doi.org/10.1007/978-1-4020-5839-4), and
  [Kuhn's extensive-form information sets](https://doi.org/10.1515/9781400881970-012)
  are the formal lineage for participant information states, view transitions,
  and perfect-recall claims.
  [Goguen-Meseguer noninterference](https://doi.org/10.1109/SP.1982.10014) and
  [Sabelfeld-Sands declassification](https://doi.org/10.3233/JCS-2009-0352)
  ground the hidden-truth boundary and disclosure-rule semantics.
- [STRIPS](https://doi.org/10.1016/0004-3702(71)90010-5),
  [PDDL](https://doi.org/10.2200/S00900ED2V01Y201902AIM042),
  [PDDL2.1](https://doi.org/10.1613/jair.1129), and the probabilistic planning
  languages ([PPDDL](https://doi.org/10.1613/jair.1880),
  [RDDL](https://users.cecs.anu.edu.au/~ssanner/IPPC_2011/RDDL.pdf)) are the
  action-language lineage behind participant precondition/effect contracts.
- [CybORG](https://arxiv.org/abs/2108.09118),
  [CyberBattleSim](https://www.microsoft.com/en-us/research/project/cyberbattlesim/),
  [CyGIL](https://arxiv.org/abs/2109.03331), and CyGIL's
  [unified emulation-simulation training environment](https://arxiv.org/abs/2304.01244)
  are the cyber-agent environment precedents. They show the value of explicit
  action/observation/reward/episode interfaces, and also expose the
  sim-to-emulation gap that ACES must record through realization disclosure and
  evidence provenance.
- CALDERA adversary-emulation research informs the action semantics: cyber
  actions can change foothold, knowledge, observations, detection surface, and
  downstream outcomes under uncertainty.
- RUN-305's runtime snapshot design follows that lineage by making participant
  episode state and behavior history first-class portable records rather than
  backend logs or `metadata`: action attempts, observations, state-transition
  records, and outcome interpretations need stable participant/episode/action
  identity to support review across RL agents, LLM agents, humans, scripts, and
  cyber-range backends. OpenSpiel's information-state separation and the
  cyber-agent sim-to-emulation sources above are the reason the snapshot
  preserves behavior history without claiming hidden world truth, private
  participant internals, benchmark validity, or full replay guarantees from that
  history alone.

## Benchmark And Experiment Lineage

- [Cybench](https://arxiv.org/abs/2408.08926) and
  [AutoPenBench](https://arxiv.org/abs/2410.03225) inform ACES's treatment of
  task descriptions, starter files, evaluators, subtasks, gold steps,
  milestones, human assistance, and repeated runs as experiment artifacts.
  ACES does not adopt flag capture or milestone completion as the complete
  outcome model; those are inputs to explicit interpretation rules.
- [CAIBench](https://arxiv.org/abs/2510.24317) motivates integrated offensive,
  defensive, privacy, and cyber-physical evaluation surfaces. ACES adapts this
  as role-neutral multi-participant semantics and privacy/redaction disclosure,
  not as a bundled meta-benchmark score.
- General agent-evaluation critiques such as
  [AI Agents That Matter](https://arxiv.org/abs/2407.01502) and
  [Benchmarking Practices in LLM-driven Offensive Security](https://arxiv.org/abs/2504.10112)
  motivate holdout discipline, anti-contamination controls, scaffold
  disclosure, baseline disclosure, cost/resource traces, and standardized run
  records. ACES records these as provenance and information-boundary concerns
  so downstream studies can audit what a participant actually could observe.

## DSL Evaluation Lineage

- [Do Software Languages Engineers Evaluate their Languages?](https://arxiv.org/abs/1109.6794),
  Mernik, Heering, and Sloane's
  ["When and How to Develop Domain-Specific Languages"](https://doi.org/10.1145/1118890.1118892),
  and Kosar, Bohra, and Mernik's
  ["Domain-Specific Languages: A Systematic Mapping Study"](https://doi.org/10.1016/j.infsof.2015.11.001)
  inform ACES's treatment of language adequacy as an evidence claim. A language
  can be domain-aware and formally specified while still failing on ambiguity,
  usability, effectiveness, maintainability, or domain-expert reviewability.
- Issue #346 tracks this as a dedicated evidence gate. It is related to
  authoring accessibility, formal validation, and participant semantics, but it
  is not discharged by any of those alone.

## Runtime, Time, And Causality

- [TENA](https://www.trmc.osd.mil/tena-about.html) and the
  [IEEE High Level Architecture (IEEE Std 1516-2010)](https://standards.ieee.org/ieee/1516/3744/)
  are the main runtime/federation precedents for distributed exercise services,
  time management, and object publication.
- [SISO Cyber DEM](https://cdn.ymaws.com/www.sisostandards.org/resource/resmgr/standards_products/siso-std-025-2023_cyberdem.pdf)
  and Cyber FOM are cyber-specific simulation-interoperability precedents.
- Lamport logical clocks, HLA time management, Time Warp, DEVS, SimPy, ROS 2
  time, ns-3 realtime mode, and FMI inform ACES's separation of timestamp,
  ordering, clock authority, pacing, synchronization, and causality.
- [Fidge](https://doi.org/10.1109/ICDCS.1988.12501)/[Mattern](https://www.vs.inf.ethz.ch/publ/papers/VirtTimeGlobStates.pdf)
  vector time and the
  [Schwarz-Mattern causality survey](https://doi.org/10.1007/BF02277859) are
  the basis for vector-clock ordering claims: scalar Lamport clocks respect
  causality one way, vector clocks characterize it.
  [Winskel's event structures](https://doi.org/10.1007/3-540-17906-2_31) and
  [Mazurkiewicz's trace theory](https://doi.org/10.1007/3-540-17906-2_30)
  ground partial-order realized ordering with simultaneity groups.
- [Allen's interval algebra](https://doi.org/10.1145/182.358434),
  [Koymans' metric temporal logic](https://doi.org/10.1007/BF01995674), and
  [Alur-Dill timed automata](https://doi.org/10.1016/0304-3975(94)90010-8)
  are the formal temporal-contract lineage for schedules, deadlines, dwell,
  and windows.
- [Berenson et al.'s ANSI SQL isolation critique](https://doi.org/10.1145/223784.223785)
  and [Adya's generalized isolation theory](https://hdl.handle.net/1721.1/8703)
  anchor the shared-state isolation-guarantee vocabulary.
- Halpern-Pearl structural causality informs ACES's treatment of attribution:
  a participant action followed by an alert is not automatically a causal
  explanation without an evidence basis.
  [Chockler-Halpern responsibility and blame](https://doi.org/10.1613/jair.1391)
  extends this to graded multi-cause attribution.

### Cyber DEM And Cyber FOM: Adopted And Out Of Scope

[SISO Cyber DEM](https://cdn.ymaws.com/www.sisostandards.org/resource/resmgr/standards_products/siso-std-025-2023_cyberdem.pdf)
(SISO-STD-025-2023) and the
[Cyber FOM](https://www.sisostandards.org/news/690125/Publication-of-Cyber-FOM-and-SIRL-Users-Guide.htm)
(SISO-STD-025.3-2024) are distinct artifacts and are treated as distinct here.
Cyber DEM is a runtime data-exchange model: a shared ontology of cyber objects
(Device, System, Service, Network, Data) and typed effect/event types for
exchanging cyber conditions between simulators. The Cyber FOM is the HLA
federation object model derived from it.

- **Adopted as precedent.** Cyber DEM's typed cyber-object and directed
  relationship vocabulary, and its attack/defend/recon effect taxonomy, are
  precedent for ACES treating typed relationships
  ([ADR-052](../../decisions/adrs/adr-052-typed-runtime-relationship-subtypes.md))
  and observed runtime objects as first-class. ACES adopts the *concept* of a
  typed cyber-object vocabulary, not the Cyber DEM object set or its identifiers.
- **Out of scope.** ACES does not adopt Cyber DEM as its scenario model or the
  Cyber FOM as its backend contract. Cyber DEM is consumed at runtime by
  federates; ACES keeps an authored scenario surface separate from any runtime
  exchange model, and does not treat HLA federation conformance as equivalent to
  ACES backend conformance.
- **Where it leads ACES.** Because the Cyber FOM inherits IEEE 1516 HLA time
  management and multi-vendor federation, it is more mature than ACES on
  federated time and standardized interoperability. ACES's time-authoring
  surface is partial and explicitly incomplete. This is detailed in the
  [Related-Work Comparison](related-work-comparison.md).

## Adversary Emulation And Security Knowledge

- [MITRE ATT&CK](https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy),
  MITRE CALDERA, Atomic Red Team, and OpenC2 are adversary-emulation and
  command/response precedents. ACES treats them as behavior and execution
  sources that scenarios may bind to, not as replacements for the SDL.
  From OpenC2 specifically, ACES borrows the command/response principle — an
  action requested against a target with a status-bearing response — but does
  not adopt OpenC2's action/target/argument payload structures as SDL or
  runtime-contract schema.
- OCSF is the preferred lineage for normalized security event and finding
  structure. ACES uses that style for observations and evidence without making
  raw telemetry equal to participant-visible state.

## What ACES Adds

ACES separates authored scenario meaning, processor/runtime contracts, backend
realization, participant implementations, live state, and archival
evidence/provenance. The participant-semantics design extends that separation:
actions, observations, visibility, causality, temporal behavior, and outcomes
must be portable across human, AI-agent, scripted, simulated, and hybrid
participants without collapsing into any one backend or learning API.
