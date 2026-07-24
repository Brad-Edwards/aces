# Issue 859 / DSL-436 Authored Historical State Preflight

Date: 2026-07-24

Issue: #859. Requirement: DSL-436.

This note records repository-wide architecture guardrails for authored
historical scenario state and native materialization semantics. It does not
implement SDL syntax, schemas, compiler resources, adapters, persistence,
fixtures, tests, or an implementation plan.

A follow-on ADR is required before this contract is declared stable. Existing
decisions deliberately separate authored desired state, observed runtime
inventory, participant history, experiment baselines, runtime snapshots, and
backend realization, but none owns a versioned historical-state authority or
the semantic-object-to-product-object materialization relation. The ADR must
preserve the boundaries below and compose with ADR-087 / issue #857 after that
work reaches `dev`.

## Binding Decisions

### Establish one historical-baseline authority

Add one keyed, closed historical-baseline declaration family to the instantiated
SDL graph. A baseline key and explicit baseline version identify authored
meaning; the enclosing baseline owns its semantic objects, historical events,
actor bindings, materialization bindings, and readback requirements. Do not add
separate pack manifests, bootstrap documents, product exports, or runtime
inventories that can independently claim the same history.

The baseline is authored desired state. It is not:

- the experiment comparison baselines in ADR-054/068;
- the pre-apply `RuntimeSnapshot` called a baseline in backend reconciliation;
- participant behavior or episode history;
- `Node.runtime` observed inventory;
- a generated artifact, persistent-volume snapshot, or content package;
- a scheduler job, reset workflow, or product adapter result; or
- proof that any product accepted or exposed the state.

Each organization actor is a typed binding to an incumbent declaration. Human,
team, and organization identity comes from `entities`; participant identity
comes from `agents`; system login identity comes from `accounts`; service
actors come from existing node/service declarations. The historical contract
may classify an actor's role in one baseline, but it must not copy those
declarations, reinterpret exercise role as product authorization, or use
observed platform `organizations` as authored authority.

Each semantic object has one baseline-local portable id and kind. Product
objects, runtime inventory children, files, messages, cases, alerts, tickets,
dashboard objects, and other native records may realize that object, but they
do not supply its identity. Mutable labels, bodies, timestamps, product names,
native ids, adapter selections, and materialization order never enter semantic
object identity.

Historical object links follow the existing `Relationship` discipline:
stable edge identity, explicit endpoints, a governed relationship type, and a
closed typed detail. Extend that typed-detail seam and the central declaration
index; do not use free-form `Relationship.properties`, a second generic edge
model, or object-kind-specific reference resolvers. Event causality is owned by
the historical event graph because it also carries event order and state
transition meaning; it is not inferred from an ordinary object relationship.

### Keep history time, causality, and product time separate

Every historical event has an explicit coordinate in one baseline-declared
history time domain and a deterministic tie/order rule. The initial profile
should be finite and logical: a canonical order coordinate plus an optional
authored display instant or relative offset. The profile must not depend on
parse order, map iteration, wall time, scheduler time, product timestamps, or
materialization completion order.

History order and causal support are separate:

- predecessor/causal references resolve to events in the same baseline;
- causal and transition graphs are acyclic;
- causes precede effects under the declared history order;
- object creation precedes mutation, linkage, or deletion;
- deletion/tombstone prevents later use unless a governed restoration event
  explicitly permits it;
- one event/object authority is explicit where conflicting writers would
  otherwise make state ambiguous; and
- timestamp adjacency, equal display time, shared actor, or declaration order
  never establishes causality.

Product-native event time, creation time, update time, ingestion time, and the
time at which a materializer ran are observed mapping facts. Reuse the
ADR-054 distinction among occurred/recorded/ingested and source-pipeline times
where runtime evidence needs those values. Never copy them into the authored
history coordinate or silently shift authored time to satisfy a product API.

Historical events are not `aces_sdl.events` orchestration triggers and are not
`ParticipantBehaviorHistoryEvent` records. Those incumbents have different
lifecycle, participant, evidence, and execution authority.

### Derive semantic addresses from a versioned, closed context

A materialized semantic object address is a typed value, not a concatenated
string, provider id, compiled runtime address, JSON Pointer, or hash of a
display label. Its complete v1 context consists only of:

- an exact address-profile id;
- a portable range-instance identity;
- the deployment-tenant identity from DSL-143 / ADR-087;
- an explicit reset-generation identity governed by that tenant/service
  ownership contract;
- baseline id and baseline version; and
- the baseline-local semantic object id.

The address profile fixes the closed DTO, RFC 8785/JCS byte encoding, digest or
derivation algorithm, domain-separation label, output encoding, and collision
behavior. Follow the accepted random-stream profile discipline in
`StreamAddressModel` and `random_stream_engine`: typed canonical inputs,
versioned domain separation, stateless derivation, duplicate semantic-coordinate
and duplicate canonical-byte detection, deterministic failure, and no partial
output. Do not reuse `StreamAddressModel`, its randomness namespace, or its
derived bytes; historical identity needs a distinct profile and separation
label.

Tenant, range, reset generation, and baseline version are mandatory isolation
inputs. A native id, hostname, worker, process, thread, backend, queue, retry,
wall time, declaration index, map order, or random seed is forbidden. A reset
that intentionally creates a fresh product corpus advances the governed reset
generation; an idempotent retry of the same generation preserves every
semantic address.

The authored local id, typed address material, derived semantic address, SDL
declaration address, compiler-owned resource address, product-assigned native
id, and evidence record id remain distinct identities. Equality in one domain
does not imply equality in another.

### Bind to native interfaces without making providers authoritative

Each materialization binding references:

- one semantic object or governed object set;
- one existing logical `nodes.<node>.services.<service>` target;
- one closed, versioned provider-neutral materialization-interface profile;
- the deployment tenant/cell and reset owner supplied by ADR-087;
- any explicit ordering dependencies; and
- participant-equivalent readback assertion refs.

The interface profile describes a portable operation class and supported
object semantics, not a vendor endpoint, HTTP path, query, SDK type, database
table, shell command, credentials, or arbitrary options map. A backend manifest
must declare the exact interface profiles and object kinds it supports. The
existing SEM-218 realization-support gate separately requires exact,
non-approximating support for the complete binding. A generic "supports
history" Boolean, service presence, product name, or realization-envelope
membership cannot satisfy both obligations.

Compilation preserves the admitted baseline graph on
`RuntimeModel.realization_instance`. If executable materialization resources
are introduced, use the existing `ResolvedResource` -> `PlannedResource` ->
`PlanOperation` -> `SnapshotEntry` path, canonical address checks, dependency
ordering, capability admission, and SEM-218 provenance. Do not add plan
resources merely to carry baseline metadata, and do not create a second plan or
lifecycle engine.

Product-assigned ids are returned only as observed binding evidence after
ownership-safe creation or readback. They may be retained in a bounded,
tenant-scoped native-correlation record or as protected backend evidence, but
never become authored identity, a compiler address segment, a reference key,
an idempotency key, or a cross-reset adoption key. A native id alone is not
ownership proof. Correlation must bind semantic address, exact target service,
tenant, reset generation, interface/profile version, operation, and observation
provenance.

### Reuse proposition, participant-view, and claim semantics for readback

Do not add a second predicate language. Historical readback requirements extend
the closed typed `Proposition` / `Assertion` seam from ADR-079. They name the
semantic object, governed participant-visible property/link projection,
expected typed value or relation, quantification, temporal observation point,
and evidence requirement. Unsupported product semantics remain `unsupported`;
missing, stale, conflicting, redacted, or inadequate evidence remains
`unknown`; neither becomes success.

"Participant-equivalent" means that the native readback satisfies the same
declared participant-visible properties and links under one named observation
boundary/projection revision. It does not require native byte equality, native
id equality, hidden-state equality, identical product timestamps, or global
state equality. Reuse compiled `ParticipantObservationBoundaryRuntime`,
`view_relation_timeline`, participant context/history view contracts, markings,
redaction, and evidence/provenance boundaries.

Do not label one successful readback as backend equivalence, trace equivalence,
bisimulation, or `participant-projected-history-equivalence`. If an artifact
actually compares two projected histories, ADR-081's
`BehavioralClaimBindingModel` and relation catalog govern the claim and its
bounded evidence.

### Keep reset ownership subordinate to ADR-087

DSL-436 declares which historical baseline and object set a reset generation
governs; it does not create a reset controller or lifecycle state machine.
Reset-generation ownership must reference and agree with ADR-087's deployment
tenant, shared-service state owner, and reset-generation owner. It remains
separate from participant episode reset/restart, backend process restart,
workflow compensation, persistent-volume `retain`/`ephemeral`, runtime snapshot
version, and a product-native generation number.

Missing, conflicting, or cross-tenant ownership fails semantic admission. Do
not infer ownership from a sole tenant, service location, volume consumer,
native namespace, product account, or declaration order.

### Treat corpus safety as semantic admission, not a scanner side effect

The authored baseline carries bounded semantic metadata and inert participant
content only. It must not inline raw product exports, MIME archives, database
dumps, mapper documents, executable scripts, macros, private keys, bearer
tokens, password/hash material, live credentialed URLs, backend payloads, or
unbounded binary/text bodies.

Reuse `Content` for ordinary scenario content and associated-artifact manifests
for separately staged bytes, with checksums, sizes, sensitivity, byte binding,
and ADR-071 trust policy. A historical object may reference such content; it
must not duplicate or absorb the bytes. Product-specific parsed manifests stay
observed runtime inventory and are not bootstrap input.

The requirement's forbidden-content rule needs one pure, bounded corpus-policy
analyzer at the SDL semantic layer. It should reuse shared URI secret checks,
redaction/classification vocabulary, artifact trust/integrity results, and the
repository's private-key/secret hygiene policy, while publishing its relational
limits through `x-aces-invariants`. Do not import the libvirt-specific
`redaction_violations()` helper into `aces_sdl`, copy its regex table into
models, or claim that gitleaks alone validates arbitrary user-supplied
documents. Shape validators reject unrepresentable fields; the one semantic
analyzer owns cross-field content/ref/sensitivity policy.

## Canonical Incumbents to Reuse

- **Authority and phase contracts:** ADR-009/061/075/078,
  `ScenarioContent`, `Scenario`, `ExpandedScenario`,
  `InstantiatedScenario`, `InstantiationProvenance`,
  `InstantiatedScenarioSnapshot`, `admit_instantiated_scenario()`,
  `canonical_sdl_digest()`, and `canonical_instantiated_sdl_digest()`.
- **Source admission:** `load_sdl_yaml()`, `SDLSourceParseOptions`,
  `SDLParserLimits`, duplicate-key and YAML-domain checks,
  `SDLModel(extra="forbid")`, `PortableIdentifier`, and `QualifiedName`.
- **Declarations, references, and composition:**
  `_mapping_scopes.HASHMAP_SECTIONS`,
  `_module_symbols.HASHMAP_SECTIONS`, `symbol_index()`,
  `build_declaration_index()`, `_namespace_payload()`,
  `_rewrite_section_ref()`, module export/collision checks, composition
  budgets, and post-instantiation semantic revalidation. Extend the owning
  catalogs; do not add another list or resolver.
- **Actors, services, tenancy, and state:** `Entity`, `Agent`, `Account`,
  canonical node/service refs, `IdentityDomain`, `PersistentVolume`, and
  ADR-082/087. Runtime platform organizations/tenants/content objects remain
  observed inventory under ADR-049.
- **Pure graph semantics:** `analyze_domain_topology()` and its thin
  `SemanticValidator` adapter pattern, typed `Relationship` details, stable
  issue codes, collect-all `SDLValidationError`, and instantiated differential
  admission. One historical-baseline analyzer owns actor, event, link,
  identity, target, tenant, reset, and readback agreement.
- **Time, causality, visibility, and truth:** ADR-022/054/079/081/085,
  participant attribution ordering rules, `Proposition`, `Assertion`,
  proposition truth tables/results, observation boundaries,
  `view_relation_timeline`, participant context/history views, and
  `BehavioralClaimBindingModel`.
- **Addressing and determinism:** ADR-076, `ContractModel(extra="forbid")`,
  RFC 8785/JCS canonicalization, `StreamAddressModel` and
  `random_stream_engine` as the domain-separated stateless-derivation
  precedent, `require_compiled_address()`, and `RuntimeModel.__post_init__`.
- **Compilation and realization:** ADR-004/036/070,
  `RuntimeModel.realization_instance`, `ResolvedResource`,
  `resource_payload()`, existing planner graph semantics,
  `ProvisionerCapabilities`, `BackendManifest`,
  `CompiledRealizationRequirement`, `realization_support_diagnostics()`,
  `realization_disclosure()`, `RealizationObservation`, and backend result
  admission.
- **Persistence, errors, and observability:** `RuntimeSnapshot`,
  `SnapshotEntry`, `ControlPlaneStore` atomic persistence,
  `RealizationProvenanceEntry`, `Diagnostic`, operation receipts/statuses,
  audit events, and existing SDL parse/validation/instantiation errors. Authored
  baseline content is carried by the instantiated scenario, not snapshot
  `metadata` or operation `details`.
- **Content and trust:** `Content`, ADR-056/057/066/071/077,
  `AssociatedArtifactManifestModel`,
  `validate_associated_artifact_manifest()`, artifact validation limits,
  checksum/size binding, and the canonical hygiene/private-key/gitleaks graph.
- **Publication and workflow:** all scenario-containing published schemas,
  especially `sdl-authoring-input-v1`, `instantiated-scenario-v1`,
  `instantiated-scenario-snapshot-v1`, and
  `scenario-satisfiability-evidence-v1`; `schema_bundle()`;
  schema-publication entries; SDL catalog parity; controlled vocabularies;
  reference models; the SDL lineage ledger; `.ground-control.yaml`;
  `.gc/plan-rules.md`; and the canonical nox verification graph.

## Cross-Cutting Layers and Gates

1. **Source/parser gate.** Historical declarations remain inert bounded
   `sdl-yaml/v1` data. Existing UTF-8, byte/scalar/node/depth/alias/import
   budgets, duplicate-key rejection, forbidden tags/directives, key
   classification, JSON-domain checks, and source diagnostics apply before
   model construction. Parsing performs no product, filesystem, network, LDAP,
   mail, database, or provider activity.
2. **Closed-shape/config gate.** Focused closed models and controlled
   vocabularies own baseline/object/event/link/interface/readback shapes.
   Declaration ids cannot be variables. Unknown fields, provider option maps,
   native queries, environment bindings, executable templates, and
   `other`-style dispatch for security-sensitive semantics fail closed.
3. **Reference/semantic gate.** Every actor, object, event, relationship,
   service, tenant, cell, state, proposition, assertion, reset owner, and
   content/artifact ref enters the central declaration index and resolves
   exactly once. One pure analyzer owns graph and compatibility invariants;
   field validators do not duplicate graph checks.
4. **Composition/instantiation gate.** Module expansion namespaces baseline and
   nested declaration identities and rewrites every reference with the owning
   symbol map. Parameter substitution may fill permitted scalar/reference
   values but may not rename objects, change address-profile identity, inject
   native ids, or leave `${...}` unresolved. Instantiation reruns every
   invariant.
5. **Schema/publication gate.** JSON Schema owns closed shape and local
   cardinality. Cross-reference, causality, ownership, collision, tenant,
   content-safety, and compatibility rules are published as semantic
   invariants and enforced by artifact admission. All embedding phase schemas,
   generator parity, fixtures, publication hashes, lineage, concept authority,
   and catalog parity move together. Structural validity is not semantic
   validity under ADR-072.
6. **Compiler/plan/capability gate.** Compiler output preserves the canonical
   admitted graph and deterministic semantic addresses. Any executable resource
   uses existing compiled-address, unique-address, dependency-cycle, plan
   resource-type, direct-submission, interface-profile capability, SEM-218
   exactness, and backend `validate()` gates before `apply()`.
7. **Authentication/authorization gate.** Authoring adds no API privilege.
   Any later control-plane route reuses
   `ControlPlaneSecurityConfig.strict_defaults()`, bearer/proxy identity
   verification, target binding, read/mutating role separation, request-size
   limits, idempotency fingerprints, and audit. An authored actor, tenant,
   reset owner, or product principal is not a control-plane caller identity.
8. **Secret/configuration gate.** Credentials, tokens, private keys, product
   endpoints, environment values, secret URIs, client configuration, and raw
   claims are unrepresentable. Adapters resolve credentials outside portable
   contracts at an independently authorized sink. No new CLI secret option,
   environment variable, `.env` shape, ambient config, or credential resolver
   is authorized.
9. **OS/process exposure gate.** Authoring, validation, compilation, and
   address derivation require no subprocess, listener, mount, host path, or
   privilege. Future adapters use fixed argv/no shell, bounded input/output and
   time, controlled working directories, and non-argv secret delivery.
   Historical content, native ids, credentials, parameter maps, and product
   payloads never enter argv, filenames, stdout/stderr, environment captures,
   or shell interpolation.
10. **Backend-result/error/logging gate.** Expected failures use bounded SDL
    errors or structured `Diagnostic` values with safe ids, paths, codes, and
    counts. They do not echo corpus bodies, native ids, product payloads,
    credentials, rejected documents, backend exceptions, or tracebacks.
    Unexpected HTTP failures retain `{"detail":"internal server error"}`.
    `_call_backend_apply()` retains the prior snapshot on malformed,
    approximate, cross-tenant, or unverifiable results.
11. **Persistence/evidence gate.** Instantiated snapshots preserve authored
    intent and derivation provenance. Runtime native bindings and readback
    results are observed evidence with tenant/reset/profile/operation
    provenance. Do not store either in `RuntimeSnapshot.metadata`,
    operation/audit `details`, generic tags, logs, or a new mutable global
    repository. A desired-state snapshot is not proof of native state.

## Dependency and Extensibility Guardrails

Issue #857 / DSL-143 is a semantic dependency, not optional nearby work. The
local `857-enterprise-deployment-tenancy` branch defines ADR-087,
`deployment_tenants`, deployment cells, typed shared-service bindings, mutable
state ownership, and reset-generation ownership, but it is not in current
`dev` ancestry. DSL-436 implementation must first reconcile with the landed
form of that contract using a normal merge and semantic conflict resolution.
It must not recreate tenant, cell, shared-service, state-owner, or reset-owner
fields as a temporary historical-state schema.

The primary extension seam is the versioned triple:

`(semantic_object_kind, materialization_interface_profile,
participant_readback_projection_profile)`.

The binding also carries the closed semantic-address profile. A new product
object family should add governed object/interface/projection profile terms,
profile-specific typed fields, capability evidence, validators, fixtures, and
readback mapping while preserving baseline and object identity. It must not
require a provider extension bag, a new top-level topology, another predicate
AST, another graph engine, or edits to unrelated object kinds.

Replica-aware targets belong behind an explicit stable instance-selector
profile. Multi-interface fan-out requires a declared authority/consistency
policy. Neither variation may use product ids, list positions, discovery order,
or first-success behavior to choose the authoritative object.

## Gotchas and Anti-Patterns

- Do not reuse the word `baseline` without its owner: historical baseline,
  experiment comparison baseline, and runtime reconciliation snapshot are
  different concepts.
- Do not treat `entities.events`, orchestration `events`, participant history,
  runtime inventory, `Content`, or a product export as historical authority.
- Do not duplicate entities, agents, accounts, nodes, services, tenants,
  cells, persistent volumes, propositions, observation boundaries, or
  associated artifacts inside a baseline.
- Do not infer organization actor, tenant, authority, reset owner, causal edge,
  object creator, or materialization target from names, DNS suffixes, native
  namespaces, product accounts, declaration order, or a sole candidate.
- Do not derive identity by delimiter concatenation, mutable labels, timestamps,
  native ids, provider names, hashes of secret material, random values,
  iteration order, retries, or worker identity.
- Do not adopt or overwrite an existing native object by name. Ownership-safe
  readback must prove the semantic-address binding for the exact tenant and
  reset generation before update or cleanup.
- Do not make product time the authored timeline, use timestamps as causality,
  or silently coerce unsupported historical timestamps into a product's range.
- Do not collapse target interface, product capability, exact realization,
  execution success, readback success, participant visibility, and equivalence
  into one `supported` or `materialized` Boolean.
- Do not treat native-id equality, payload equality, final-state equality, or
  one passed predicate as participant-history equivalence or backend
  equivalence.
- Do not place raw corpus bodies, provider exports, commands, scripts, queries,
  credentials, attachments, stdout/stderr, or native exception text in SDL,
  diagnostics, snapshots, audit, fixtures, or provenance summaries.
- Do not add duplicate section catalogs, reference resolvers, identity/hash
  helpers, graph validators, predicate languages, truth tables, exception
  hierarchies, loggers, stores, lifecycle machines, schema registries, or CI
  workflows.
- Do not implement logic under compatibility-only
  `implementations/python/src/aces/`, hand-edit only generated schemas, omit
  schema-publication ledger changes, or update only one phase schema.

## Non-Goals and Implementation Boundary

- No product adapter, product SDK/client, credential broker, product discovery,
  native object creation, database mutation, audit-history forgery, direct
  product-database writes, or management-plane proof.
- No fleet/range scheduler, placement optimizer, reset controller, parallel
  lifecycle state machine, global identity service, tenant database, event
  store, or product-object repository.
- No generated filler, stochastic corpus generation, live data import, raw
  MIME/STIX/vendor bundle authority, archive format, package layout, artifact
  registry, or acquisition workflow.
- No claim that authored history proves native creation time, audit log
  provenance, product-internal causality, participant exposure, adapter
  correctness, cross-backend equivalence, or successful reset.
- No provider ids, endpoints, database keys, host paths, cloud/project ids,
  credentials, or backend handles in authored identity.
- Runtime native ids, materialization receipts, and readback results remain
  observed evidence. They never become authored authority.
