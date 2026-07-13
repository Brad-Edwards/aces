# Issue #763 — Authored Domain Topology Preflight

Date: 2026-07-13

Issue: #763.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This is implementation guidance only. It does not define final SDL field
spellings, publish a schema, change compilation or runtime behavior, or provide
an implementation plan.

## Architectural Boundary

Directory/domain **inventory** and authored domain **topology** are separate
contracts.

- `Node.runtime.identity_authorities` and ADR-032 describe node-scoped logical
  identity state that can be inventoried or compared after realization. It may
  contain subjects, policies, services, and observed relationships. It is not a
  provisioning instruction.
- The new surface describes the minimum desired graph a provisioner needs:
  domain identity, authority principal, controller role, member join, and the
  domain binding of a domain-scoped account feature.
- Runtime inventory may later be checked against authored topology, but it must
  not be copied into the authored model, used as dispatch input, or treated as
  proof that realization occurred.

Do not silently amend ADR-032's accepted runtime-only decision. The schema work
must publish this authored boundary in a new ADR or an amendment governed by
ADR-059, with corresponding normative SDL specifications.

## Semantic Decisions

### One scenario-scoped domain declaration

Introduce one map-keyed, scenario-scoped identity-domain declaration. The final
serialized section name is a schema-design choice; its semantic placement is
not. The map key is its portable SDL identity and belongs to the existing
`identities` concept family.

The declaration owns:

- a closed, realization-capable domain profile/kind;
- the canonical DNS domain identity;
- the NetBIOS identity required by the initial AD-compatible profile; and
- an authority-principal reference to an existing top-level `accounts`
  declaration.

The authority principal identifies *who* is authorized to register and read
back domain-scoped state. It is not a place to store a password, hash, keytab,
token, private key, environment-variable value, host path, or backend resolver
configuration. No repository-wide deploy-time secret-reference contract exists
today, so this issue must not invent a secret store or disguise an opaque
backend lookup key as a portable SDL reference. A provisioner that needs an
operator secret resolves it from target configuration, keyed by safe authored
domain/principal identities, outside the SDL and plan payload.

Use a provider-neutral base with explicit profiles, not a lowest-common-
denominator bag. The initial profile can require DNS and NetBIOS semantics;
future Kerberos, LDAP, or cloud-directory profiles add discriminated typed
members only where their realization semantics truly match. `unknown` and
`other` are useful inventory values but are not dispatchable authored topology
kinds.

### Roles and membership are typed topology edges

Represent domain-controller role and domain membership through the existing
top-level `relationships` graph:

- a controller edge has a node source and identity-domain target;
- a join edge has a member-node source and identity-domain target; and
- join detail carries the explicit controller/authority-node selection (or a
  bounded ordered candidate set), whose entries must be controller nodes for
  that same domain.

The exact relationship spellings remain schema work. Their semantics must use
new governed relationship terms and typed detail models. Do not encode these
facts in `Relationship.properties`, node tags/roles, descriptions, image names,
scenario ids, usernames, `os_family`, or duplicated node fields.

A controller edge also establishes the controller node's membership in that
domain; do not require a redundant join edge. Multiple controllers are valid.
For the initial AD-compatible profile a VM may not declare contradictory
controller/member roles or membership in multiple domains. A future profile
may relax that only through an explicit discriminated rule, not a global
special case.

### Domain-scoped account features bind explicitly

An account that exercises a domain-scoped feature must reference its authored
domain. `spn` is the initial governed domain-scoped account feature. Reuse the
existing `Account` declaration and `provisioner_account_features()` extraction;
do not create a second domain-account model or let a backend infer the domain
from account/node names, OS, a sole join, or a controller image.

Semantic validation must establish that the account's node is a controller or
member of the referenced domain and that the domain has complete dispatchable
topology. The account reference names the principal whose domain state is being
realized; it remains distinct from the authority principal used to perform the
operation.

### One authored authority, one compiled projection

The instantiated scenario remains the authority for domain declarations and
relationships. The compiler analyzes that graph once and emits a typed,
normalized per-node topology binding in the provisioning node payload. This is
an intentional compiled projection, not a second authored schema.

The projection must contain enough explicit evidence for a consumer to decide,
without heuristics:

- whether the node is a controller, member, or unrelated;
- the referenced domain id, profile, DNS identity, and NetBIOS identity;
- the safe authority-principal identity;
- the explicitly admitted controller node(s); and
- ordering dependencies needed to establish controllers before members and
  domain-scoped account placements.

Keep bootstrap ordering acyclic: establish the controller/domain, then realize
the authority account, then join members, then realize domain-scoped account
features. The authority-principal reference is logical identity for later
registration/read-back; it must not make the controller node depend on an
account placement that itself depends on that controller. Any credential needed
to bootstrap the first controller is target configuration, not a hidden SDL
account or plan dependency.

There is no `AcesPlanNode` contract in this repository. ACES owns
`NodeRuntime`, the provisioning `node`/`account-placement` payloads,
`ProvisioningPlanModel`, and `RuntimeSnapshot`. A downstream DTO must consume
the published ACES projection rather than becoming a second authority.

The compiled binding needs one typed model and one shared plan-analysis helper.
Although `PlanOperationModel.payload` is currently an open mapping, topology
inside it must be shape-checked at compiler output, planner admission, direct
HTTP/control-plane admission, and backend validation. Scan both plan resources
and non-`DELETE` operations, following the existing capability-envelope
pattern; a direct submitted plan cannot rely on compiler-private
`RuntimeModel` metadata.

Backend-returned snapshot entries preserve the realized normalized projection,
which provides the portable read-back surface. Extend SEM-218 realization
requirements/disclosure for exact authored identity and topology fields so a
backend cannot omit or silently approximate them. Do not treat a copied desired
payload as observed proof, and do not hide topology in plan metadata,
diagnostics, audit text, or backend-private DTOs.

## Semantic Invariants And Shared Gate

`SemanticValidator` owns cross-declaration checks and collects all failures in
the existing `SDLValidationError` envelope. Model validators own only local
shape/profile rules. Post-instantiation semantic validation must run the same
analysis after variables resolve.

The shared analysis must reject:

- non-portable ids, invalid DNS/NetBIOS forms, missing profile-required fields,
  or unresolved variables at the instantiated boundary;
- dangling or ambiguous domain, node, account, authority-principal, or
  controller refs;
- controller/join sources that are switches or otherwise non-realizable nodes;
- an authority principal that is not placed on a controller for the same
  domain;
- a join whose selected controller is not declared as a controller of the same
  domain;
- contradictory or duplicate controller/join facts, including a redundant
  controller join;
- a dispatchable join with no controller, authority principal, or required
  domain identity;
- a domain-scoped account feature without an explicit matching domain ref;
- dependency cycles introduced by controller, join, and account ordering; and
- any backend capability claim that cannot realize the domain profile and
  domain-scoped feature together.

Domain identity comparison rules must be explicit. Do not silently rewrite
authored DNS/NetBIOS spelling or use case-folding for SDL ids. If protocol names
have case-insensitive comparison semantics, preserve the authored spelling and
apply that comparison only in the owning typed validator.

Incomplete or inconsistent topology is a fatal semantic/admission diagnostic,
not an advisory. Use `SDLParseError`, `SDLValidationError`,
`SDLInstantiationError`, and runtime `Diagnostic` as appropriate; do not add a
domain exception hierarchy.

## Canonical Incumbents To Reuse

- **SDL authority and phases:** `ScenarioContent`, `SDLModel(extra="forbid")`,
  `load_sdl_yaml`, `instantiate_scenario`, `InstantiatedScenario`, ADR-078,
  canonical ids/addresses, and post-instantiation revalidation.
- **Declarations and refs:** `_mapping_scopes.HASHMAP_SECTIONS`,
  `_module_symbols.HASHMAP_SECTIONS`, `build_declaration_index()`, reference
  targetability, `composition._namespace_payload()`, `_language_metadata`, and
  the reference/language-service helpers. Extend these catalogs; do not build a
  domain-only resolver or registry.
- **Relationships:** `Relationship`, governed `RelationshipType` terms, the
  typed relationship-detail precedent, `_verify_relationships()`, and the
  cross-edge agreement checks in `validator/_relationships.py`. Free-form
  `properties` is not a topology contract.
- **Compilation and planning:** `_compile_node_runtimes()`, `NodeRuntime`,
  `resource_payload()`, `AccountPlacement`, `_collect_resources()`, canonical
  dependency addressing, and `ProvisioningPlan`. Preserve closed SDL phase
  boundaries rather than passing an authoring model to a backend.
- **Feature/capability gates:** `provisioner_account_features()`,
  `ProvisionerCapabilities`, controlled-vocabulary validation,
  `planner._validate_manifest()`, and the table-driven libvirt
  `capability_envelope_diagnostics()` pattern. Add one governed provisioner
  domain-topology capability dimension; do not bury support in free-form
  `constraints` or equate `supports_accounts` with domain support.
- **Realization fidelity:** `aces_sdl.explicitness`, realization-envelope
  membership, `CompiledRealizationRequirement`,
  `realization_support_diagnostics()`, and `realization_disclosure()`. Domain
  topology is realization-relevant authored intent, not provenance metadata or
  an open backend choice.
- **Runtime admission and read-back:** `_submitted_plan_diagnostics()`,
  `Provisioner.validate()`, `backend_calls`, `RuntimeSnapshot`, `SnapshotEntry`,
  and `ControlPlaneStore`. Extend the existing admission path and snapshot
  payload; do not create a topology service, repository, or persistence file.
- **Authority/publication:** ADR-009/019/061/076,
  `specs/authority/authority-boundary.yaml`, `specs/sdl/sections.md`,
  `specs/sdl/references.md`, published SDL/plan schemas,
  `schema_bundle()`, `contracts/schema-publication-manifest.json`, and the
  schema/catalog parity tools. Generated schemas prove Python parity but do not
  replace hand-governed contract review.
- **Concept authority:** the existing `identities` and `relationships` concept
  families, reference-model catalog, semantic profiles, and controlled
  vocabularies. Add an authored domain reference model if needed; do not create
  a competing identity concept family.
- **Diagnostics and observability:** bounded parser diagnostics,
  collect-all semantic errors, runtime `Diagnostic`, operation receipts/status,
  control-plane audit summaries, and redacted API/backend exception handling.
  No new logger or error envelope is needed.

## Security And Cross-Cutting Layers

The design passes every layer below and must satisfy each one.

1. **Source/parser gate.** Domain topology is inert data processed by
   `load_sdl_yaml`; existing source-size, safe-YAML, duplicate-key, key
   normalization, variable mapping-key, and bounded Pydantic-diagnostic rules
   remain in force. No name or field triggers network, LDAP, Kerberos, shell, or
   filesystem activity.
2. **Closed shape/reference gate.** `SDLModel(extra="forbid")`, published
   schemas, profile validators, portable ids, the declaration index, typed
   relationships, and `SemanticValidator` reject unknown fields and invalid or
   inconsistent refs. The same pure analysis is reused by compiler agreement
   tests; validation is not duplicated in a backend.
3. **Instantiation/config gate.** Existing typed variables, allowed-value
   constraints, substitution, unresolved-token rejection, and semantic
   revalidation apply. Domain ids remain literal map keys. Do not add an SDL
   environment binding, `.env` reader, CLI secret flag, or target-config parser.
4. **Plan-shape/admission gate.** A typed compiled topology binding validates
   every materialized `node`/domain-scoped `account-placement` payload. The
   shared gate handles in-process resources and non-`DELETE` operations, and is
   invoked before `Provisioner.validate()` for direct API submissions. Missing
   evidence fails before realization dispatch.
5. **Capability/non-approximation gate.** Provisioner capabilities declare the
   governed domain profile/kind and account-feature support independently.
   Planner and backend use the same payload extractor. SEM-218 support and
   disclosure reject unsupported or silently changed exact topology and record
   bounded realization provenance.
6. **API/auth gate.** Submission continues through
   `ControlPlaneSecurityConfig.strict_defaults()`, verified bearer/proxy
   identity, target-bound operator/backend roles, request-size limits,
   idempotency fingerprints, and audit summaries. Control-plane bearer identity
   is not a domain authority credential. Audit records must not copy plan
   payloads or authority-resolution details.
7. **Secret and OS/process gate.** SDL, plan operations, snapshots, diagnostics,
   logs, fixtures, process argv, command strings, and environment dumps carry no
   operator credential material. Backend adapters resolve credentials at the
   target boundary and use fixed argv/no shell, least privilege, and redacted
   output where an OS command is eventually required. This issue itself adds no
   subprocess or environment-variable surface.
8. **Persistence/read API gate.** `LocalControlPlaneStore` persists snapshot
   payloads and exposes them to authorized readers, so only safe domain,
   principal, and controller identities may enter the compiled projection.
   Preserve atomic snapshot writes and existing authorization. Never persist a
   resolved password, keytab, token, secret URI, host path, backend-native
   object, traceback, stdout, or stderr.
9. **Error-envelope gate.** Parser and semantic errors name safe field paths and
   stable ids, not raw values or documents. Runtime failures use bounded
   `Diagnostic` codes. Backend exceptions remain type-only at the adapter, and
   the API's generic internal-error envelope must not be bypassed by embedding
   secret-bearing values in `ValueError` text.

## Extensibility Seam

The seam is a pure domain-topology analysis and projection parameterized by:

- a governed, discriminated domain profile/kind;
- profile-specific identity validation (DNS/NetBIOS initially);
- controller-selection policy over an explicit authored candidate set;
- the governed set of account features that require a domain binding; and
- provisioner-supported domain-profile terms.

The same analysis feeds semantic validation, compiled node/account bindings,
ordering dependencies, capability extraction, direct-plan admission, and
snapshot non-approximation. Adding one future join-capable directory profile,
controller failover policy, or domain-scoped account feature should add a
profile/term and adapter support, not another top-level schema, backend DTO,
validator, or inference rule.

Do not claim LDAP bind, Kerberos service use, federation, cloud tenancy, or IAM
trust is a machine domain join merely to reuse the initial shape. Extend the
profile union only when controller, membership, authority, and read-back
semantics align; otherwise use the existing relationship vocabulary or a
separate deliberately governed semantic.

## Required Contract And Test Evidence

The implementation must follow the repository's existing schema/fixture and
agreement patterns. At minimum, evidence must cover:

- valid single/multi-controller topology and explicit member/account bindings;
- invalid local profile shapes, dangling/ambiguous refs, switch roles,
  cross-domain authority selections, duplicate/conflicting roles, missing
  controllers, dependency cycles, and SPN without a matching domain ref;
- variable substitution followed by the same semantic decisions;
- module namespacing and canonical reference/language-service behavior;
- authoring, instantiated-scenario, and instantiated-scenario-snapshot
  schema/catalog parity;
- compiler projection and validator agreement, including explicitness and
  exact-value realization disclosure;
- in-process and direct-HTTP plan admission, non-`DELETE` operation coverage,
  capability rejection, and backend validation agreement;
- runtime-snapshot contract round-trip/read-back without secret material; and
- bounded diagnostics/API errors that do not echo domain credentials or raw
  payloads.

Use the existing SDL model/parser/validator/phase/composition/catalog tests,
contract fixture corpus, runtime compiler/planner tests,
`test_backend_protocols_account_features.py`, control-plane/API tests, and
backend conformance patterns. Do not make a single downstream Shifter example
the contract proof.

## Non-Goals And Anti-Patterns

- Do not provision AD, LDAP, Kerberos, DNS, or cloud directories in this issue's
  ACES implementation; SDL and plan contracts describe portable intent and
  evidence, while provisioners realize it.
- Do not redesign runtime identity inventory, local identity, accounts,
  control-plane authentication, secret storage, persistence, or logging.
- Do not copy runtime subjects/policies/services into authored topology or
  synthesize runtime inventory from desired topology and call it observation.
- Do not import legacy `dc`, `join_domain`, or `dc_config` shorthands silently.
  Any compatibility migration follows ADR-075 with explicit, loss-aware
  diagnostics.
- Do not introduce a universal directory schema, an AD-only top-level section,
  a free-form topology bag, raw plan dictionaries without shape admission, or a
  backend-owned bridge as the canonical contract.
- Do not infer topology from ids, names, images, accounts, OS families, service
  ports, runtime inventory, or the fact that only one candidate exists.
- Do not add implementation logic under `implementations/python/src/aces/` or
  create duplicate schema generators, reference registries, validation passes,
  exception classes, logging stacks, capability maps, or persistence stores.
- Do not edit changelogs or package versions as part of the implementation.
