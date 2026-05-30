# SDL Semantic Validation

The semantic validator (`aces.core.sdl.validator.SemanticValidator`) runs the
named semantic pass set after Pydantic structural validation. It collects all
errors rather than failing on the first, so authors see every issue at once.

Under the repository's [coding standards](../reference/coding-standards.md),
this layer is primarily an `FM1` and `FM2` surface. It is where static semantic
invariants such as cross-reference resolution, ambiguity, uniqueness,
reachability, and fail-closed graph constraints are enforced. Those invariants
must stay aligned with the runtime compiler and planner contracts rather than
becoming a validator-only interpretation of the SDL.

## Validation Passes

### OCR SDL passes (ported from Rust `Scenario::formalize()`)

| Pass | What It Checks |
|------|----------------|
| `verify_nodes` | Features, conditions, injects, vulnerabilities referenced by nodes exist in their respective sections. Role names on feature/condition/inject assignments must match declared node `roles`. Node names ≤ 35 characters. |
| `verify_infrastructure` | Every infrastructure entry has a matching node. Links reference existing switch/network entries. Dependencies reference existing infrastructure entries. Switch nodes cannot have count > 1, and nodes with conditions cannot scale above 1. Complex property IPs must be valid IPs within the linked switch's CIDR. ACL `from_net` and `to_net` references are each checked and must resolve to switch/network entries. |
| `verify_features` | Vulnerability references exist. Dependency references exist. **Dependency cycle detection** via topological sort. |
| `verify_conditions` | (Structural: command+interval XOR source — enforced by Pydantic) |
| `verify_vulnerabilities` | (Structural: CWE format — enforced by Pydantic) |
| `verify_metrics` | Conditional metrics reference existing conditions. Each condition used by at most one metric. |
| `verify_evaluations` | Referenced metrics exist. Absolute min-score doesn't exceed sum of metric max-scores. |
| `verify_tlos` | Referenced evaluations exist. |
| `verify_goals` | Referenced TLOs exist. |
| `verify_entities` | TLO, vulnerability, and event references on entities (including nested) exist. |
| `verify_injects` | from-entity and to-entities reference existing (possibly nested) entities. TLO references exist. |
| `verify_events` | Condition and inject references exist. |
| `verify_scripts` | Event references exist. Event times within script start/end bounds. |
| `verify_stories` | Script references exist. |
| `verify_roles` | Entity references in node roles resolve to flattened entity names. |

### Extension passes

| Pass | What It Checks |
|------|----------------|
| `verify_content` | Content targets reference existing VM nodes. |
| `verify_accounts` | Account nodes reference existing VM nodes. |
| `verify_relationships` | Source and target resolve to any named element in any section, including variables, relationships, content item names, named service bindings, runtime service listener refs, runtime identity-authority refs, runtime DNS refs, runtime network-sensor refs, runtime network detection-engine refs, runtime security-monitoring manager refs, and named ACL rules. Ambiguous bare refs are rejected with qualified alternatives. |
| `verify_runtime_service_listeners` | Runtime service listeners resolve optional same-node service refs, process refs, and host-published port correlations. Concrete service/listener port+protocol values must match. |
| `verify_runtime_identity_authorities` | Runtime identity-authority services resolve to same-node service bindings. Local relationship and policy refs resolve within the owning authority across authority, service, subject, policy, and relationship stable ids. |
| `verify_runtime_dns_services` | Runtime DNS services resolve to same-node service bindings. Configuration, log, and zone-file refs resolve to observed runtime filesystem entries when the node has file inventory. |
| `verify_runtime_network_sensors` | Runtime network sensors name monitored networks that resolve to switch-backed infrastructure entries and, when runtime endpoint inventory exists on the node, to same-node network endpoint attachments. Configuration, log, and evidence refs resolve to observed runtime filesystem entries when the node has file inventory. |
| `verify_runtime_network_detection_engines` | Runtime network detection engines resolve optional same-node sensor refs, network-set refs, control-channel service refs, and filesystem-backed configuration/log/evidence/rule/output/control paths. |
| `verify_runtime_security_monitoring_managers` | Runtime security-monitoring managers and listeners resolve to same-node service bindings. Manager/group/content/detection/setting file refs resolve to observed runtime filesystem entries when the node has file inventory. Agent group member refs, agent group refs, setting component refs, detection content-set refs, and detection correlation refs resolve inside the owning manager. Detection source artifact refs and target refs resolve through the generic named-ref index. |
| `verify_agents` | Entity references resolve. Starting accounts and initial-knowledge accounts exist in accounts section. Allowed subnets and initial-knowledge subnets must resolve to switch-backed infrastructure entries. Initial-knowledge hosts must resolve to VM nodes. Initial-knowledge services exist in `nodes.*.services[].name`. |
| `verify_participant_behavior` | Agent action refs resolve to declared action contracts, observation-boundary refs resolve to declared boundaries, interaction refs resolve to declared actions or targetable state, and boundary view rules/transitions resolve to declared observable, hidden, or evidence refs. |
| `verify_objectives` | Objective actors resolve (`agent` or `entity`). Objective actions must be declared by the referenced agent. Targets resolve to named scenario elements, including qualified service/ACL refs and section-qualified top-level refs. Ambiguous bare refs are rejected with qualified alternatives. Success criteria resolve to declared conditions/metrics/evaluations/TLOs/goals. Optional windows resolve through one shared normalized analysis over stories/scripts/events/workflows/workflow-steps, must remain internally consistent, and fail closed on dangling or out-of-window refs. Objective dependencies must resolve and stay acyclic. |
| `verify_workflows` | Workflow `start` and every referenced step must exist. `objective`/`retry` steps must reference declared objectives. Predicate refs must resolve to declared conditions/metrics/evaluations/TLOs/goals/objectives, and step-state refs must resolve to prior executable steps whose state is guaranteed to be known before the predicate runs. Workflow graphs must be acyclic and fully reachable from `start`. Parallel joins must be explicit barriers, every explicit branch path must converge on the declared join, branch-local state remains scoped until the join, and post-join predicates may inspect only branch steps guaranteed on every path within their branch before the join. |
| `verify_participant_outcomes` | Outcome interpretation source and target refs resolve for action contracts, objectives, workflows, and evaluations. Reward-signal targets require governed assessment refs structurally, while runtime conformance grounds emitted interpretation records in action results, event evidence, and participant episode history. |
| `verify_variables` | Checks that full-value `${var}` placeholders reference declared variables. Structural validation of typed defaults and `allowed_values` still happens in the `Variable` model itself. |

Pydantic structural validation also enforces model-local node rules before
these semantic passes run. Switch nodes reject VM-only fields, including
`runtime`. Runtime mount, dependency-manifest, and software-component manifest
paths must be absolute paths or variable references. Runtime software-component
`installed_paths`, filesystem inventory paths, container masked paths,
container read-only paths, and device host/container paths must also be
absolute runtime paths or variable references. Runtime local-control interface
paths and bind sources must be absolute paths, Windows named pipe endpoints, or
variable references; Windows named pipe endpoints require `kind: named_pipe`.
Runtime software components must have stable, concrete `component_id` values
that are unique within the node runtime block.
Runtime filesystem inventory UID/GID and size fields are non-negative, mode is
stored as octal permission bits, and content digests must carry both the digest
algorithm and value. Runtime healthcheck entries marked as redacted must omit
raw output. Runtime mount sources/options and local-control bind sources
classified as `redacted` or `operator_secret` must omit the corresponding raw
value; the Python models and generated JSON Schemas both reject non-empty raw
values for redacted/operator-secret labels accepted by the parser's
normalization rules, including case-insensitive hyphen/underscore spellings.

The optional `runtime.local_identity` inventory carries its own model-local
rules. Local user `username` and local group `name` must be non-empty; user
`uid`/`primary_gid` and group `gid` are non-negative; user `home` and `shell`,
when set, must be absolute paths or variable references. Local users are unique
by `username`, local groups are unique by both `name` and `gid`, and sudo rules
are unique by principal plus command scope. A sudo rule with
`command_redacted: true` must omit its `commands` list, keeping a withheld
command scope distinct from a genuinely empty one.

The optional `runtime.identity_authorities` inventory also has model-local and
semantic rules. Authorities, services, subjects, policies, relationships,
attributes, and settings use stable non-empty ids or names. Stable ids must be
unique across the authority-local reference namespace, not just within each
child collection. The model also rejects duplicate attribute and setting names,
normalizes bounded kind/protocol/provenance/value classifications, and keeps
raw values out of secret-bearing attributes or settings. Authority services may
reference only services declared on the same node. Authority-local refs resolve
against all stable ids in the authority:
`authority_id`, `service_id`, `subject_id`, `policy_id`, and
`relationship_id`. Provider names and external object identifiers are data, not
reference keys.

The optional `runtime.dns_services` inventory has model-local and semantic
rules. DNS services, zones, and RRsets use stable ids, while observed DNS names
remain data and are not case-folded. DNS service ids are unique within a node
runtime block; zone ids are unique within a DNS service; RRset ids and
owner/class/type bindings are unique within a zone. RRsets must have at least
one record, TTL and type-code fields are bounded integer-or-variable values,
`record_type: other` requires `type_code`, and typed RDATA must match the
owning RRset type. A/AAAA typed address payloads are validated as IPv4/IPv6
respectively. Secret-bearing DNS settings such as TSIG, RNDC, password, token,
or private-key settings must omit raw values and use redacted/operator-secret
classifications. DNS services may reference only services declared on the same
node. File refs under the DNS service and its zones are checked against
`runtime.filesystem_inventory` when that inventory is non-empty.

The optional `runtime.network_sensors` inventory has model-local and semantic
rules. Network sensors use stable `sensor_id` values that are unique within the
node runtime block. Implementations, sensor kinds, monitoring postures, and
capture modes are normalized from bounded enums while allowing full-value
variables where the model permits. `capture_interfaces` and
`monitored_network_refs` reject duplicates. Each monitored network ref must
resolve to a declared switch-backed infrastructure entry; when the same node
records `runtime.network.endpoints`, the monitored network must also be one of
that node's observed endpoint attachments. Configuration, log, and evidence
refs are absolute paths and are checked against `runtime.filesystem_inventory`
when that inventory is non-empty.

The optional `runtime.service_listeners` inventory has model-local and
semantic rules. Listener ids are stable concrete symbols and are unique within
a node runtime block. Network listeners require a port and a bind address or
interface; Unix socket listeners require `socket_path` and must not set a port
or address. Concrete address-family and scope fields must not contradict the
bind endpoint: wildcard addresses use `scope: wildcard`, loopback addresses
cannot be `network_facing`, non-loopback IP addresses cannot be
`loopback_only`, and Unix socket listeners use `local_socket` or `unknown`.
Optional same-node `service` refs must resolve to `Node.services[].name`, and
concrete listener port/protocol values must match the service. Optional
`process_ref` values resolve to `runtime.process` or `runtime.processes` by
process name or PID. Optional `published_port_refs` entries resolve to
`runtime.network.published_ports` by host IP, host port, container port, and
protocol and must match the listener's container-side port/protocol.

The optional `runtime.network_detection_engines` inventory has model-local and
semantic rules. Engine ids are stable concrete symbols and are unique within
one node runtime block; engine-local rule-source, network-set, output-stream,
and control-channel ids are unique inside the owning engine. Optional
`sensor_ref` values resolve to same-node `runtime.network_sensors` ids.
Network-set refs resolve to switch-backed infrastructure entries.
Configuration, log, evidence, rule-source, output-stream, and control-channel
paths are absolute and are checked against `runtime.filesystem_inventory` when
that inventory is non-empty. Control-channel `service` refs resolve to
same-node `Node.services` bindings.

The optional `runtime.security_monitoring_managers` inventory has model-local
and semantic rules. Managers, listeners, components, agents, agent groups,
content sets, detection definitions, and settings use stable ids. Manager ids
are unique within a node runtime block, and every manager-local stable id is
unique across the manager itself plus its child collections. Implementations,
manager kinds, listener roles, component kinds/statuses, agent statuses,
content kinds/formats, detection engines/kinds, field-predicate operators,
setting provenance, and value classifications are normalized from bounded
enums while allowing full-value variables where the model permits.
Secret-bearing settings such as passwords, API tokens, credentials, shared
keys, keytabs, or private keys must omit raw values and use
redacted/operator-secret classifications. Managers and listeners may reference
only services declared on the same node. Manager configuration/log/evidence
refs, agent-group configuration refs, content-set file refs,
detection-definition source/evidence refs, and setting source paths are checked
against `runtime.filesystem_inventory` when that inventory is non-empty. Group
`member_refs` must resolve to manager-local agents, agent `group_refs` must
resolve to manager-local groups, setting `component_ref` values must resolve to
manager-local components, detection `content_set_ref` values must resolve to
manager-local content sets, and detection `if_sid_refs`,
`if_matched_sid_refs`, and `parent_definition_refs` must resolve to
manager-local detection definitions. Detection `source_artifact_ref` and
`target_refs` resolve through the generic named-ref index.

The optional `source.build` container image provenance block carries its own
model-local rules. Build-argument and image-default-environment names must be
non-empty and free of `=`, and values classified as redacted must omit the raw
value. Copied-source and source-input destination paths, and image-config
working directories, must be absolute paths or variable references. Source-input
checksums must carry both the checksum and its algorithm. Build-argument names
and source-input identifiers must be unique within a build block, and
image-default environment names must be unique within an image config. An
attestation with `status: absent` cannot also report `verification: verified`,
keeping "no registry-visible attestation" distinct from a failed verification.

When a field contains an unresolved `${var}` placeholder, reference-oriented
passes treat it as deferred rather than as a broken concrete reference. The
validator still does not substitute values; the repo-owned instantiation
phase performs substitution, type-checking, and concrete revalidation before
runtime compilation.

The SDL validator is intentionally structural/semantic. The SDL-native runtime
compiler and runtime conformance helpers perform additional fail-closed binding
checks, including node-local feature dependency enforcement, bound-resource
reference resolution, and SEM-215 outcome-record grounding. A participant outcome
interpretation emitted at runtime must preserve declared source/target bindings
and must ground participant-action outcome sources in the event action result,
evidence refs in event evidence, and participant-episode status sources in
terminal participant-episode history for the same participant and episode.

This also means the validator only enforces what the current SDL syntax can
actually express. Node `runtime` metadata covers observed VM configuration
facts such as mounts, path-local control interfaces, process identity, runtime
filesystem inventory, container host/security configuration, health observations,
package inventory, software component identity, dependency manifests, and
scanner-derived package findings.
The `source.build` block covers observed container image build provenance:
base image and digest, layer chain, structured build-recipe instructions, build
arguments, copied sources, image-default configuration, source-input mapping,
and attestation status.
Broader ecosystem concerns such as participant-implementation manifests,
decision-surface exposure policy contracts, augmentation disclosure, and full
evidence-capture contract surfaces are separate validation domains.
They should not be retrofitted into validator-only behavior before the authored
surface or external contracts exist.

## Static Semantic Invariants

The validator is the main enforcement point for static SDL semantics, but not
the only source of truth. The same rules must remain consistent with compiled
runtime models and downstream runtime contracts.

Typical invariant categories in this layer include:

- cross-reference existence and disambiguation
- uniqueness rules for names and bindings
- acyclic dependency and workflow graphs
- fail-closed resolution for ambiguous or missing references
- reachability and convergence constraints
- “guaranteed to be known before evaluation” visibility rules

In coding-standards terms:

- `FM1` covers static semantic rules such as ambiguity, uniqueness, and
  fail-closed reference resolution
- `FM2` covers graph/constraint rules such as reachability, visibility, and
  consistency across validator and compiled/runtime forms

Workflows are the clearest current example. Their syntax is described in YAML,
but the important semantics live here and in the runtime architecture: which
steps are reachable, which joins are legal, and which prior step states are
knowable before a predicate executes.

Objective windows are the clearest current `FM2` example. Their authoring
surface is still simple YAML, but the semantic meaning comes from one shared
analysis pass that resolves normalized references, checks story/script/event and
workflow/step consistency, derives refresh semantics, and feeds both validator
errors and compiled runtime forms.

The same pattern applies conceptually to participant and observability
concerns: author-facing syntax, shared semantics, runtime
contracts, and provenance must stay aligned, but they do not all collapse into
the current validator surface.

## Advisories

Successful parses may still carry non-fatal advisories on `Scenario.advisories`. These are not validation errors and do not block parsing.

Current advisory coverage:

- VM nodes without `resources` are allowed, but emit an advisory because some deployment backends may not be able to instantiate them without explicit sizing defaults.

## Error Reporting

All passes run to completion. Errors are collected into a list and raised as a single `SDLValidationError`:

```python
try:
    scenario = parse_sdl(yaml_string)
except SDLValidationError as e:
    print(f"{len(e.errors)} errors found:")
    for error in e.errors:
        print(f"  - {error}")
```

## Cross-Reference Resolution

Generic refs are indexed in two forms:

- bare names like `webapp` when they are unique in the generic-ref namespace
- qualified names like `nodes.webapp`, `features.postgres`, `infrastructure.dmz-net`, or `content.mailbox.items.invoice.eml`

The index also includes nested entity dot-paths, named service bindings
(`nodes.<node>.services.<service_name>`), named ACL rules
(`infrastructure.<infra>.acls.<acl_name>`), and runtime-family refs generated
from the SDL runtime-family registry. Registered runtime refs include:

- `nodes.<node>.runtime.service_listeners.<listener_id>`
- `nodes.<node>.runtime.applications.<application_id>`
- `nodes.<node>.runtime.database_services.<database_service_id>` plus
  `.databases.<database_id>`
- `nodes.<node>.runtime.dns_services.<dns_service_id>` plus `.zones.<zone_id>`
  and `.zones.<zone_id>.rrsets.<rrset_id>`
- `nodes.<node>.runtime.identity_authorities.<authority_id>` plus nested
  service, subject, policy, and relationship refs
- `nodes.<node>.runtime.file_services.<service_id>` plus nested share,
  principal, access-rule, and access-observation refs
- `nodes.<node>.runtime.mail_services.<service_id>` plus nested component,
  listener, domain, mailbox-store, mailbox, alias, routing-rule, queue, and
  setting refs
- `nodes.<node>.runtime.network_sensors.<sensor_id>`
- `nodes.<node>.runtime.network_detection_engines.<engine_id>` plus nested
  rule-source, network-set, output-stream, and control-channel refs
- `nodes.<node>.runtime.security_monitoring_managers.<manager_id>` plus nested
  listener, component, agent, agent-group, content-set, detection-definition,
  and setting refs
- `nodes.<node>.runtime.ssh_servers.<server_id>` plus
  `.match_rules.<match_id>`

This means a relationship can reference any node, feature, condition,
vulnerability, infrastructure entry, metric, evaluation, TLO, goal, entity
(including nested), inject, event, script, story, content entry, content item,
account, agent, objective, workflow, relationship, variable, named service
binding, registered runtime-family object, registered runtime-family child
object, or named ACL rule. When a bare ref maps to multiple elements,
validation fails and asks the author to use one of the qualified alternatives.
