# Issue 857 / DSL-143 Enterprise Identity and Deployment-Tenancy Preflight

Date: 2026-07-24

Issue: #857. Requirement: DSL-143.

This note records repository-wide architecture guardrails for enterprise
identity and deployment-tenancy authoring. It does not implement SDL syntax,
schemas, compilation, backend realization, examples, fixtures, tests, or an
implementation plan.

A follow-on ADR is required before the feature is declared stable. ADR-082
deliberately excludes forests and trust, ADR-032 owns observed runtime identity
inventory, and no accepted decision currently owns deployment cells,
carrier/kernel boundaries, or shared-service tenant/state/reset ownership.
This note fixes the boundaries that the ADR and implementation must preserve
without prematurely fixing every serialized field name.

## Binding Decisions

### Keep one authored graph with distinct concept owners

The instantiated SDL scenario remains the sole authored authority. The new
semantics extend that graph; they do not create a deployment manifest, a second
topology document, or provider allocation records.

Each required concept has exactly one owning carrier:

- a keyed forest declaration owns forest identity, its explicit root-domain
  reference, and its complete authored domain membership;
- existing `identity_domains` remain the only authored domain declarations;
- a keyed provider-neutral identity-facade declaration identifies an authored
  IdP facade by reference to an existing logical node/service, without copying
  that service's topology or runtime inventory;
- closed typed relationship details own forest trust and
  directory/forest-to-IdP federation;
- one node-local endpoint-persona field classifies a logical endpoint;
- one typed node-to-node placement relation owns logical-node carrier
  placement and kernel/trust-boundary class;
- keyed deployment-tenant declarations own portable tenant identity;
- keyed deployment-cell declarations own cell membership, one tenant
  reference, and default isolation intent; and
- one typed shared-service binding owns the consumer tenant, the existing
  logical service reference, tenant-isolation mode, workload-authentication
  mode, mutable-state references/owner, and reset-generation owner.

Final serialized names may differ, but these ownership boundaries may not.
Maps are justified only for stable declarations that other records reference.
Directed trust, federation, placement, and service-binding facts extend the
existing typed `relationships` graph instead of creating parallel edge
sections. Logical service identity continues to come from existing node
services or registered runtime-family declarations; a shared-service binding
does not redeclare the application, listener, endpoint, account, volume, or
network.

Deployment tenant and deployment cell are separate concepts. A tenant may own
more than one cell; a cell has exactly one tenant. Cell membership is declared
once on the cell as node references so a root scenario can group exported
module nodes without mutating imported node declarations. A node may belong to
at most one cell. The absence of all new sections preserves current behavior.

### Extend authored identity without collapsing runtime inventory

A forest is not a synonym for a domain. Every forest has exactly one explicit
root domain; every listed member resolves to an existing `identity_domains`
declaration; a domain cannot belong to two forests. Existing forestless domain
documents remain valid when the new section is absent. No root is inferred from
DNS suffixes, declaration order, controller placement, or a sole domain.

Forest trust and identity federation are also different edges:

- forest trust relates two authored forests and carries a closed trust type
  and direction;
- federation relates a human authority (forest or domain) to an authored
  identity facade and carries a closed direction, protocol, mapping-intent
  profile, and claim-ownership policy.

The facade is authored identity intent, not
`Node.runtime.identity_authorities`. Runtime identity authorities, subjects,
policies, mappings, issuers, and tenants remain observed/read-back state under
ADR-032. They may later be checked against authored intent, but they are not
copied into it and cannot supply missing authored federation facts.

Federation mapping intent states only portable outcomes such as the source
group/role relationship, the target role-mapping policy, and which side owns a
tenant claim. It carries no mapper JSON, transform script, claim value,
credential, client secret, token endpoint secret, provider realm id, or
application-native object id. A server-controlled tenant claim means the
server/facade is authoritative for that claim; it does not authorize authors or
participants to supply its value.

### Keep endpoint, participant, and login roles separate

Endpoint persona is a closed provider-neutral classification of a logical node,
not a role assignment:

- `Node.roles` remains node-local login identity for entities;
- `agents` and behavior-specification role references remain participant
  identity and behavior authority; and
- endpoint persona describes the endpoint's scenario function.

Persona is never inferred from operating system, image, domain-controller
status, service ports, accounts, participant roles, carrier placement, or
runtime inventory. It must not use the field name `role`, reuse participant
role vocabularies, or create implicit access or authorization.

### Preserve logical identity across carrier placement

A carrier placement is an asymmetric relation from one logical VM node to one
carrier VM node. The source remains a distinct node, declaration address,
objective target, account/content target, participant scope, and compiled
identity. Placement does not merge node specs, copy carrier facts, or turn the
logical node into a nested anonymous service.

The typed detail carries a closed kernel/trust-boundary class. That class is
authoring intent, not a Docker mode, hypervisor name, PID, container id, host
path, Kubernetes pod, cloud instance, or proof of realized isolation.

Semantic admission rejects self-placement, cycles, multiple carriers for one
logical node, non-VM endpoints, a carrier without the carrier persona, and
source/carrier membership in different deployment cells. If either node is
replicated, the first contract must reject ambiguity unless the dependency
contract supplies a governed stable instance selector.

Carrier placement does not imply shared network, PID, mount, IPC, UTS, user, or
cgroup namespaces. Conversely, issue #849's
`runtime.container.namespaces.network.target_node_ref` does not imply carrier
placement or a kernel boundary. The two relations may coexist only when their
independent invariants agree.

### Make cells deny-first and shared services explicit

Deployment cells express portable isolation intent, not allocation. Cell
membership and tenant ownership are explicit. Cross-cell placement, mutable
state, and ordinary service consumption are denied unless the owning typed
shared-service semantic explicitly permits the service edge. Forest trust and
identity federation may relate logical authorities in different cells, but
those identity edges never waive cell isolation or authorize network access.
Generic relationships, infrastructure links/dependencies, descriptions, tags,
network reachability, and a shared carrier never grant cross-cell access.

A shared-service binding references an already declared logical service and one
consumer tenant. It declares four independent axes:

1. tenant-isolation mode;
2. workload-authentication mode;
3. mutable-state resources and their tenant/service owner; and
4. reset-generation owner.

These axes must not be collapsed into a single `shared`, `multi_tenant`, or
`isolated` boolean. Mutable state reuses existing `persistent_volumes` (and
other governed stateful-resource references if later authorized); the binding
does not introduce storage classes, mount copies, or a second state-resource
schema. Reset generation is the authority to advance or replace the shared
service's state generation at a scenario reset boundary. It is not participant
episode reset, process restart, volume retention, snapshot version, or a
mutable counter embedded in SDL.

The semantic analyzer owns a closed compatibility matrix. It must reject, at a
minimum, dangling/ambiguous refs, a service not owned by a declared node,
unknown tenant/cell membership, cross-cell use without an explicit binding,
multiple mutable-state owners, a reset owner outside the declared ownership
set, and any unauthenticated or shared-credential posture that contradicts the
selected tenant-isolation/state mode. Missing ownership is not inferred from a
sole tenant, service location, volume consumer, declaration order, or default
provider behavior.

## Canonical Incumbents to Reuse

- **SDL phases and shapes:** `SDLModel(extra="forbid")`,
  `ScenarioContent`, `Scenario`, `ExpandedScenario`,
  `InstantiatedScenario`, `parse_sdl()`, `instantiate_scenario()`,
  `admit_instantiated_scenario()`, ADR-078, and post-instantiation semantic
  revalidation.
- **Identifiers, declarations, and references:**
  `PortableIdentifier`, `QualifiedName`,
  `_mapping_scopes.HASHMAP_SECTIONS`,
  `_module_symbols.HASHMAP_SECTIONS`, `symbol_index()`,
  `build_declaration_index()`, reference targetability, canonical-address
  collision checks, and ADR-076. Extend these catalogs; do not add a
  DSL-143-only registry or resolver.
- **Composition:** `composition._namespace_payload()`,
  `_rewrite_section_ref()`, section-specific symbol maps, module
  export/private-symbol rules, collision checks, aggregate composition budgets,
  and ADR-053. Every new reference must have an explicit namespace rewrite.
- **Relationships and topology:** `Relationship`, governed
  `RelationshipType` terms, typed detail models, `_verify_relationships()`,
  the pure `analyze_domain_topology()` precedent, and its thin
  `SemanticValidator` adapter. Free-form `Relationship.properties` is not an
  authority surface.
- **Existing identity and state:** `IdentityDomain`,
  `Node.runtime.identity_authorities` only as separate observed inventory,
  `PersistentVolume`, stateful-resource reference analysis, and ADR-032/082.
  Do not duplicate domains, runtime IdP state, services, accounts, mounts, or
  volumes.
- **Network and placement dependencies:** issue #849's typed network-namespace
  object and `_NodesInfraNetworkMixin`; issue #845's first-class compiled
  domain-controller placement contract when it lands. The new authoring
  relation must project through that placement seam rather than create another
  compiled placement resource.
- **Language tooling and catalogs:** `_language_metadata`,
  `language_completions()`, `language_references()`,
  `specs/sdl/sections.md`, `specs/sdl/references.md`, and
  `tools/check_sdl_catalog_parity.py`, including its independently maintained
  reference-edge expectations.
- **Concept authority:** existing `identities`, `assets`, `relationships`,
  `scenarios`, and `realization-and-disclosure` families;
  `controlled-vocabularies-v1`, its governed-scope checks and fixture;
  `reference-models-v1`; and the SDL lineage ledger. Do not add an
  `enterprise`, `tenancy`, or provider concept family merely to group this
  issue.
- **Schema authority:** the four published contracts that embed the scenario
  model (`sdl-authoring-input-v1`, `instantiated-scenario-v1`,
  `instantiated-scenario-snapshot-v1`, and
  `scenario-satisfiability-evidence-v1`), `schema_bundle()`,
  `contracts/schema-publication-manifest.json` plus per-schema publication
  entries, generated-schema parity, JSON-artifact checks, and ADR-009/061.
- **Errors and observability:** bounded source-anchored
  `SDLParseDiagnostic`/`SDLParseError`, collect-all `SDLValidationError`,
  `SDLInstantiationError`, language-service diagnostics, and—only if a
  compiler/runtime projection is added—the existing `Diagnostic`,
  operation-receipt/status, audit, and redacted API envelopes. No new logger or
  exception hierarchy is warranted.
- **Repository workflow:** `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/check_semantic_coverage.py`,
  `tools/check_generated_schemas.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers and Gates

1. **Source/parser gate.** All declarations remain inert `sdl-yaml/v1` data
   processed by the bounded safe loader. UTF-8, byte/scalar/alias/node/depth
   limits, duplicate-key rejection, forbidden tags/directives, JSON-domain
   checks, structural-key normalization, literal declaration keys, and bounded
   model diagnostics remain unchanged. No authored value triggers LDAP, OIDC,
   network, filesystem, process, or provider activity.
2. **Closed-shape and vocabulary gate.** Local shape/profile rules use focused
   `SDLModel` records and existing enum-or-variable parsing. Provider-neutral
   trust, protocol, persona, kernel boundary, isolation, authentication,
   ownership, and reset terms are closed governed vocabularies. Unknown fields,
   `other`/`custom` dispatch values, free-form option maps, and provider terms
   fail closed.
3. **Reference and semantic gate.** Declarations enter the central declaration
   index. Existing domain-topology analysis owns forest/domain agreement; one
   focused pure deployment-tenancy analyzer owns cell, placement, tenant, and
   shared-binding agreement. Typed relationship validation owns type/detail
   agreement. Thin validator adapters add stable issues to the existing
   collect-all error envelope. Model validators do not duplicate graph checks,
   and compiler/backend code may only replay or strengthen the owning analysis.
4. **Composition and instantiation gate.** Module expansion rewrites every new
   reference through section-specific maps before merge. Variables may occupy
   permitted scalar/reference fields but never declaration keys. Substitution
   must leave no `${...}` token and must rerun structural and semantic
   admission, catching contradictory values that were deferred while
   unresolved.
5. **Schema and artifact-admission gate.** All four scenario-containing
   published schemas move together with their publication hashes and identical
   generated bundle. JSON Schema owns closed shapes and local cardinality;
   cross-reference, uniqueness, ownership, cycle, and compatibility invariants
   are disclosed through the existing semantic-invariant mechanism and
   enforced during instantiated-artifact admission. Schema validity alone is
   not semantic admission.
6. **Compiler/plan boundary.** This requirement authorizes portable authoring
   semantics, not provider realization. The canonical instantiated scenario
   and `RuntimeModel.realization_instance` preserve the graph. Any compiled
   placement projection must wait for and reuse #845; any node payload changes
   reuse `NodeRuntime`, existing canonical addresses/dependencies, planner
   cycle/refresh rules, and typed plan admission. Do not add a new plan resource
   merely to transport forests, cells, tenants, or shared-service policy.
7. **Authentication/authorization boundary.** No HTTP route, caller role,
   bearer scope, participant permission, or control-plane privilege is added.
   If a later plan traverses the existing control plane, strict security
   defaults, target-bound operator/backend authorization, request-size limits,
   idempotency/fingerprints, and audit remain the only API authority. A tenant,
   authority, claim-owner, or carrier reference is not caller authorization.
8. **Secret/configuration boundary.** The authored contract makes credentials
   unrepresentable. It contains no passwords, hashes, keys, tokens, client
   secrets, secret URIs, raw claims, environment-variable values, `.env`
   bindings, host paths, provider config, mapper documents, or opaque lookup
   handles. Existing observed-value redaction remains relevant to runtime
   inventory; it is not a loophole for adding redacted credential fields here.
9. **OS/process exposure boundary.** Parsing, validation, composition, and
   compilation add no listener, host port, shell, subprocess, file, mount,
   kernel namespace, or process argument. Future adapters use fixed argv/no
   shell, bounded input/output/time, controlled working directories, and safe
   non-argv secret delivery, but that realization work is outside DSL-143.
10. **Error/logging boundary.** Diagnostics name safe bounded declaration
    identities, field paths, issue codes, and expected concept classes. They do
    not echo whole SDL documents, mapper content, claim values, credentials,
    provider ids, parameter maps, backend payloads, native exceptions,
    tracebacks, argv, or `str(exc)`. Unexpected HTTP errors retain the generic
    internal-error envelope.
11. **Persistence/observation boundary.** Existing canonical instantiated
    snapshots and satisfiability evidence may preserve the portable authored
    graph. No new repository, database, cache, metadata blob, audit stream, or
    runtime snapshot field is added. Carriage proves authored intent only; it
    does not prove isolation, federation, authentication, reset, placement, or
    shared-service behavior occurred.

## Dependency and Merge Guardrails

Issue #849 is implemented on `origin/849-share-network-namespace` but is not in
the current `dev` ancestry. It modifies `composition.py`, `nodes.py`,
`runtime_configuration.py`, `runtime_container.py`, node/network semantic
validation, compiler node projection, backend realization, tests, and all four
scenario-containing schemas. DSL-143 must be reconciled with the landed #849
contract and preserve its node-reference rewrite and ownership invariants; it
must not overwrite that work during schema regeneration or conflict
resolution.

The local `origin/845-domain-controller-placement` reference currently has no
delta from `dev`, so its final compiled carrier is not available to inspect.
The authoring boundary above does not depend on guessing that shape. Code that
projects carrier placement into compiler/plan resources is blocked until #845
lands or its contract is otherwise made reviewable. The implementation must
then reuse that resource/address/dependency seam and add agreement tests; it
must not ship a second temporary placement DTO.

Both dependencies are real merge inputs. Resolve overlap with a normal merge
and semantic conflict resolution, not by dropping one side, regenerating over
hand-governed schema changes, or treating passing JSON syntax as contract
agreement.

## Extensibility Seam

The seam is stable declaration identity plus discriminated typed relationship
details and closed vocabularies:

- a future forest/domain profile extends the forest/domain analyzer without
  changing reference identity;
- a future federation protocol or mapping policy adds a governed term/profile
  and profile-specific fields, not mapper blobs;
- a future endpoint persona or kernel-boundary class adds a governed term after
  compatibility review;
- replica-aware placement adds one typed stable instance selector behind the
  #845 placement seam, not a provider instance id or list position;
- a future cell-isolation or workload-authentication mode extends the one
  compatibility matrix; and
- a future state/reset policy adds a typed ownership mode while retaining
  existing tenant, service, and state-resource references.

One obvious variation must not require a new top-level topology, resolver,
exception family, compiler resource hierarchy, store, or provider extension
map. New enum terms are not silently accepted: vocabularies, models, schemas,
fixtures, semantic rules, documentation, and compatibility posture move
together.

## Gotchas and Anti-Patterns

- Do not treat a domain as a forest, infer a forest root, or encode forest trust
  as generic `trusts` plus `properties`.
- Do not treat runtime identity inventory as authored authority, or synthesize
  observed IdP subjects, policies, tenants, issuers, or mappings from authored
  federation intent.
- Do not use generic `federates_with` without a closed typed federation detail,
  and do not embed Keycloak/Entra/Okta mapper JSON, client configuration, claim
  values, credentials, or provider ids.
- Do not reuse node login roles, participant roles, account groups, behavior
  modes, or OS/image labels as endpoint persona.
- Do not collapse a logical node into its carrier, copy carrier fields onto it,
  infer a carrier from infrastructure dependencies, or interpret carrier
  placement as namespace sharing.
- Do not reinterpret #849 network sharing, `infrastructure.links`,
  `RuntimeNetworkDriver.HOST`, a common bridge, or a shared IP as proof of the
  same carrier or kernel boundary.
- Do not use deployment cells as cloud projects, regions, clusters,
  subscriptions, namespaces, quota pools, capacity bins, or scheduling hints.
- Do not conflate tenant identity, cell identity, cell membership, and
  cross-cell authorization. Reachability is not permission; shared compute is
  not shared trust.
- Do not duplicate logical service, application, listener, endpoint, account,
  volume, mount, or network declarations inside a shared-service binding.
- Do not collapse isolation, workload authentication, mutable-state ownership,
  and reset-generation ownership into one flag or infer one axis from another.
- Do not confuse reset-generation ownership with participant episode reset,
  process restart policy, persistent-volume lifecycle, snapshot identity, or
  provider generation numbers.
- Do not allow an unauthenticated/shared-credential mode to coexist with a
  stronger tenant-isolation claim without an explicit permitted matrix entry.
- Do not resolve ambiguous bare refs by first match, split qualified refs
  locally, use declaration order as priority, or omit import rewriting for a
  new field.
- Do not add schema-only, model-only, semantic-only, compiler-only, or
  backend-only enforcement. Cross-stage differential tests must show that
  composition and instantiation preserve identity and that every admitted
  reference resolves exactly once.
- Do not add a second section catalog, reference resolver, graph analyzer,
  concept family, vocabulary registry, error hierarchy, logger, persistence
  store, plan workflow, or conformance harness.
- Do not edit compatibility-only `implementations/python/src/aces/`, hand-edit
  package versions or `CHANGELOG.md`, or update only generated schemas or only
  one published phase schema.

## Non-Goals and Implementation Boundary

- No implementation of #857 or DSL-143 in this preflight.
- No provider allocation, project/account/subscription/region/zone/cluster
  identifiers, quotas, capacity numbers, placement scores, scheduler policy, or
  concrete resource names.
- No credential storage/distribution, OAuth client registration, directory
  bootstrap, trust establishment, mapper execution, claim issuance, login
  broker, secret resolver, or application configuration.
- No duplication or replacement of authored nodes, infrastructure,
  `identity_domains`, accounts, node services, runtime identity inventory,
  runtime applications, persistent volumes, domain topology, or #849 namespace
  sharing.
- No backend capability claim, realization envelope widening, provisioning
  plan resource, control-plane route, runtime status, evidence of isolation, or
  proof that federation/authentication/reset/placement worked unless a separate
  delivery requirement explicitly owns it.
- No general workload orchestrator, pod/sidecar/service-mesh abstraction,
  identity graph database, policy engine, tenant database, state store, reset
  controller, or provider-neutral scheduler.
- No new migration alias or legacy shorthand. Existing SDL remains compatible
  because every new section/field is optional and defaults to absence; presence
  opts into the complete fail-closed invariant set.
