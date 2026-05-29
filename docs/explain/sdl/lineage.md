# Lineage and Prior Work

ACES is not designed as a clean-room language. It is a consolidation layer over
cyber range SDLs, adversary emulation formats, agent-evaluation environments,
runtime architectures, and security event schemas that solve adjacent parts of
the same problem.

This page is a short map of the main influences. It is not a compatibility
claim, and it is not an exhaustive bibliography. For element-level provenance,
see [Design Precedents](precedents.md).

## Specification Surface

- [Open Cyber Range SDL](https://documentation.opencyberrange.ee/docs/sdl/reference/)
  is the closest direct SDL precedent. ACES starts from its author-facing
  section surface, including logical nodes, infrastructure, features,
  conditions, scoring concepts, entities, injects, events, scripts, and
  stories. ACES keeps the logical scenario surface separate from backend
  realization instead of treating the SDL as a deployment format.
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

- **Direct SDL lineage:** top-level `accounts` keeps the CyRIS account
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
and the adjacent V&V subset under `adjacent-vv-lineage`.

The design deliberately keeps provider-stable identifiers as data rather than
as ACES reference identity. AD SIDs/objectGUIDs, LDAP DNs/entryUUIDs, SCIM
`id`/`externalId`, SAML NameIDs, and OIDC `iss` + `sub` values are preserved in
specific fields or bounded attributes when needed for translation/evidence, but
the portable ACES references are stable `*_id` symbols scoped by the scenario
and authority. Within one authority those ids share a single local namespace,
so an id cannot be reused across service, subject, policy, relationship, and
authority records. This matches the verification/validation posture in the
cyber-range literature (for example Russo/Costa/Armando on
[scenario validation](https://doi.org/10.1109/NCA.2018.8548324), Garg et al.
on the TechRxiv preprint
[scenario-design/execution survey](https://doi.org/10.36227/techrxiv.175942879.94813577/v1),
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

- **Direct SDL lineage:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
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

- **Direct SDL lineage:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
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
  product-neutral posture for content and telemetry vocabulary, but ACES does
  not import OCSF events, Sigma rule semantics, Wazuh XML, SIEM queries, or
  alert records into SDL as first-class runtime records.

Portable ACES references are stable `manager_id`, `listener_id`,
`component_id`, `agent_id`, `group_id`, `content_id`, and `setting_id`
symbols. Native manager identifiers, daemon names, file names, ruleset ids,
agent labels, and API ids are preserved as observed data or evidence when
needed, but they are not automatically ACES reference identity. Secret-bearing
manager settings such as passwords, enrollment secrets, API tokens, shared
keys, keytabs, or private keys must be redacted or operator-secret classified
and must omit raw values.

The resulting model follows the same V&V posture as the DNS, mail, database,
file-service, and identity-authority surfaces: state which manager concepts
are stable enough to compare, target, and validate; keep vendor-specific
configuration, telemetry, and rule semantics as evidence or downstream
translation concerns.

## Generic Runtime Service Listener Semantics

The `runtime.service_listeners` surface is issue #431's response to an
observed gap in APTL's MISP container inventory. It is not a replacement for
authored services, host-published port bindings, protocol-specific runtime
inventories, or scanner output. It is the bounded node-scoped place for generic
observed listener facts: bind endpoint, port, transport, address family,
listener scope, owner, readiness evidence, and provenance.

ACES relies on prior work in four ways:

- **Direct SDL lineage:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
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

- **Direct SDL lineage:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
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

## File-Sharing And Resource-Access Semantics

The `runtime.file_services` surface is issue #421's response to a gap
observed while encoding the APTL TechVault fileshare container. It is not
a clone of any one file-sharing protocol or ACL vocabulary, and the
expected-but-absent extension to `runtime.filesystem_inventory` follows
the same posture.

ACES relies on prior work in four ways:

- **Direct SDL lineage:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and
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

- **Direct SDL lineage:** Open Cyber Range SDL, CyRIS, KYPO, VSDL, and CRACK
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
- **Relationship semantics:** STIX-style typed edges remain the top-level
  relationship surface. `RelationshipMailAccess` adds mail-specific
  protocol/auth/TLS/mailbox/domain/listener details to those edges without
  promoting mail relationships into a new root section.

The result preserves the same V&V posture as database and file-service runtime
surfaces: ACES states which mail concepts are stable enough to compare and
which dynamic queue/log/config details remain evidence or bounded settings.

## Participant Semantics

- [OpenAI Gym](https://arxiv.org/abs/1606.01540),
  [Gymnasium](https://arxiv.org/abs/2407.17032),
  [PettingZoo](https://papers.nips.cc/paper/2021/hash/7ed2d3454c5eea71148b11d0c25104ff-Abstract.html),
  and [OpenSpiel](https://arxiv.org/abs/1908.09453) inform the agent-facing
  interface vocabulary: actions, observations, rewards, resets, local histories,
  imperfect information, and multi-agent interaction.
- POMDP, Dec-POMDP, POSG, and Markov-game literature is the theoretical lineage
  behind ACES's insistence that participant-visible observations are not world
  truth, and that multi-participant behavior cannot be reduced to a single
  centralized state stream.
- [CybORG](https://arxiv.org/abs/2108.09118),
  [CyberBattleSim](https://www.microsoft.com/en-us/research/project/cyberbattlesim/),
  and [CyGIL](https://arxiv.org/abs/2304.01244) are the cyber-agent environment
  precedents. They show the value of explicit
  action/observation/reward/episode interfaces, and also expose the
  sim-to-emulation gap that ACES must record through realization disclosure and
  evidence provenance.
- CALDERA adversary-emulation research informs the action semantics: cyber
  actions can change foothold, knowledge, observations, detection surface, and
  downstream outcomes under uncertainty.

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
  [IEEE High Level Architecture](https://standards.ieee.org/ieee/1516/3744/)
  are the main runtime/federation precedents for distributed exercise services,
  time management, and object publication.
- [SISO Cyber DEM](https://cdn.ymaws.com/www.sisostandards.org/resource/resmgr/standards_products/siso-std-025-2023_cyberdem.pdf)
  and Cyber FOM are cyber-specific simulation-interoperability precedents.
- Lamport logical clocks, HLA time management, Time Warp, DEVS, SimPy, ROS 2
  time, ns-3 realtime mode, and FMI inform ACES's separation of timestamp,
  ordering, clock authority, pacing, synchronization, and causality.
- Halpern-Pearl structural causality informs ACES's treatment of attribution:
  a participant action followed by an alert is not automatically a causal
  explanation without an evidence basis.

## Adversary Emulation And Security Knowledge

- [MITRE ATT&CK](https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy),
  MITRE CALDERA, Atomic Red Team, and OpenC2 are adversary-emulation and
  command/response precedents. ACES treats them as behavior and execution
  sources that scenarios may bind to, not as replacements for the SDL.
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
