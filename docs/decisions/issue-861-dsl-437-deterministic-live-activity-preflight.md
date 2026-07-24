# Issue 861 / DSL-437 Deterministic Live Activity Preflight

Date: 2026-07-24

Issue: #861. Requirement: DSL-437.

This note records repository-wide architecture guardrails for a portable
deterministic live-activity contract. It does not add SDL syntax, schemas,
runtime DTOs, adapter protocols, scheduler behavior, persistence, APIs,
fixtures, tests, or an implementation plan.

No accepted ADR owns the combined activity-policy boundary. A follow-on ADR is
required before the feature is declared stable. It must use the next ADR number
available in landing order: the in-flight #857 branch already uses ADR-087 even
though that ADR is not yet in `dev`.

## Binding Decisions

### Keep activity intent separate from every adjacent authority

The instantiated SDL scenario remains the authored authority for ordinary
company-activity intent. The minimum coherent authoring surface has two
identity levels:

- reusable, keyed activity templates own provider-neutral action meaning,
  required protocol operations, admissible readback classes, and safe
  parameter shape; and
- keyed activity profiles own background-actor bindings, template
  instantiations, logical schedules, dependency edges, target/execution-context
  bindings, budgets, lifecycle policy, and telemetry requirements.

The final serialized names may differ, but those ownership boundaries may not.
A profile is not a workflow, scheduler queue, participant behavior, runtime
inventory record, experiment run, historical-state payload, backend manifest,
or native adapter configuration. A template is not a script, shell command,
HTTP request, product object, credential, or provider SDK call.

The contract references existing declarations rather than copying them:

- logical nodes and services remain owned by `nodes`, named `Node.services`,
  and registered runtime-family children;
- accounts, identity domains, deployment tenants/cells, shared-service state,
  and persistent volumes remain owned by their current SDL declarations;
- historical baseline content and digest identity remain owned by #859;
- participant agents, behavior specifications, action contracts, observation
  boundaries, episode lifecycle, and implementation manifests remain
  participant authorities; and
- backend and processor manifests remain apparatus capability authorities.

Do not add a second topology, service catalog, account schema, tenant registry,
reset counter, baseline snapshot, action-receipt authority, or telemetry root.

### Make background actors provably non-participants

A background actor is a typed binding from one activity profile to existing
organizational/account/tenant intent. It is not an SDL `Agent`, participant
implementation, participant controller, authenticated control-plane caller, or
objective actor merely because it uses the word “actor”.

Semantic admission must be able to prove disjointness. At minimum:

- an activity actor must not resolve to an `agents` declaration;
- an entity used by an activity actor must not also be the entity binding of an
  SDL `Agent` in the same admitted scenario;
- an activity actor must not reference participant behavior specifications,
  participant action contracts, participant observation boundaries, episode
  ids, or participant implementation identities as execution authority;
- its account, tenant, target, and operating scope must resolve explicitly; and
- unresolved, ambiguous, cross-tenant, stale-generation, or participant-bound
  actors fail closed.

The actor binding may reuse an existing entity or account identity, but it must
not mutate that declaration or infer credentials, access, tenant membership, or
authorization from names, roles, topology, reachability, or a sole candidate.
If a future use case needs an actor that can switch between participant and
background control, that requires an explicit governed handoff contract; it is
not a boolean on this model.

### Split required capability, adapter support, and execution result

Each bound activity action names one existing logical target service and one
closed execution-context variant. An execution context carries portable
references and policy only: tenant/account scope, target service, protocol
capability profile, and safe secret-reference posture when later authorized.
It carries no hostname copied from inventory, URL, port override, command,
query, body, headers, environment map, credential value, provider object id,
driver options, or opaque `config`.

Four facts remain independent:

1. the activity template requires a governed protocol-operation capability;
2. a selected apparatus manifest offers an exact compatible capability;
3. a run binds that requirement to one native adapter identity and version; and
4. an action occurrence returns a validated result/readback disposition.

SDL authoring owns only the requirement and logical target/context. The
selected native adapter belongs to apparatus/run binding and provenance, not
portable scenario meaning. Extend the existing backend-manifest capability and
supported-contract patterns when an executable consumer is added; do not hide
activity support in `constraints`, infer it from a service protocol string, or
repurpose `Provisioner`, `Orchestrator`, `Evaluator`, or `ParticipantRuntime`
as a generic activity executor.

Support defaults to false. Unsupported, partial, approximate, or
version-incompatible capability agreement is an admission failure unless the
portable contract explicitly defines and discloses that weaker posture.
Successful support negotiation is not execution success.

### Use two identities: authored action and realized occurrence

An authored template/action binding has a normal ADR-076 declaration address.
A realized action occurrence has a separate deterministic semantic identity.
Do not make mutable occurrence coordinates part of an SDL declaration address,
and do not treat an ADR-076 compiled resource address or a random-stream draw
address as the occurrence id.

The occurrence identity is a versioned canonical function over a closed typed
record containing, at minimum:

- deployment-tenant canonical identity;
- reset-generation identity from the owning lifecycle contract;
- activity contract/profile digest;
- historical baseline digest from #859;
- logical-time anchor and stable action ordinal;
- template/action and target/execution-context canonical identities;
- public root seed, or governed entropy reference identity and version rather
  than secret entropy bytes; and
- every generator, address-encoding, derivation, and transformation profile
  version that can affect the occurrence.

Use the existing RFC 8785/JCS canonicalization and profile-labelled digest
patterns (`canonical_sdl_*`, `SemanticDigest`, `PrefixedDigestString`) over the
typed record. Never concatenate strings, hash `repr()`, include map iteration
order, or omit a behavior-affecting profile version. Wall time, worker/process
identity, host, retry count, queue order, backend availability, native object
ids, and readback values are forbidden identity inputs.

The accepted `blake3-xof-v1` random-stream profile,
`RandomStreamControlBindingModel`, stateless engine, governed entropy posture,
and draw provenance remain the only executable randomness incumbent. A seed
alone is not sufficient. The current `StreamAddressModel` is trial-selection
specific and must not be overloaded with tenant/generation/activity meanings.
If live activity needs stochastic jitter or weighted choice that cannot be
represented without lying about those fields, introduce a separately versioned
activity address/profile through the same governed profile process; do not call
`random`, use a cursor RNG, or silently broaden `StreamAddressModel`.

### Keep logical scheduling deterministic and bounded

Schedules express logical intent: an explicit time domain, logical anchor,
finite horizon or occurrence bound, stable recurrence/ordinal rule, and
intensity envelope. They do not contain wall-clock start times selected by a
scheduler, cron daemon state, retries, backoff, worker placement, or a native
job definition.

`parse_duration()` is the incumbent lexical duration parser where its existing
seconds semantics fit. `RuntimeScheduledJobSchedule` is observed runtime
inventory and must not become the authored live-activity scheduler schema.
Workflow timers and participant temporal contracts retain their own meanings.

Every admitted profile must have a statically demonstrable finite bound. An
open-ended recurrence, zero/negative interval, unbounded fan-out, unbounded
retry, rate without a window/unit, or schedule whose maximum occurrence count
cannot be derived fails semantic admission. Use exact integer or rational
quantity/unit/window forms for rates; do not let binary floating-point rounding
decide occurrence identity or budget admission.

Action dependencies are typed authored edges between stable action identities.
The SDL semantic analyzer owns name-level resolution and acyclicity, using the
existing central declaration index and SDL graph helper rather than a
validator-local graph. Compiled ordering uses the existing
`aces_processor.semantics.planner` dependency semantics, stable topological
ordering, refresh rules, and reverse teardown ordering. Agreement between the
authored and compiled graphs is required; a consumer reference does not
silently create an ordering edge.

### Model budgets as envelopes, not counters

Rate and resource budgets are closed typed ceilings with explicit scope, unit,
window, and resource dimension. Per-action demand, per-range capacity, and
fleet capacity are different levels of one hierarchy. Participant-reserved
capacity is a separate explicit reservation deducted before background
capacity; it is never inferred from observed load or treated as optional
headroom.

Static scenario admission validates local consistency: positive finite bounds,
known units/dimensions, action demand within range allowance, reserve not above
capacity, compatible windows, and no contradictory duplicate owner. Fleet
admission validates the selected set of ranges against the selected fleet
envelope. The SDL validator must not claim current-fleet feasibility from one
scenario in isolation.

Budget declarations are intent, not mutable token buckets, utilization
telemetry, billing quotas, participant action budgets, VM `Resources`, or
backend `max_total_nodes`. Reuse shared positive/non-negative primitives and
governed units, but do not reuse a DTO whose authority is participant
concurrency or node provisioning. Runtime consumption, if later added, needs
append-only occurrence/accounting evidence rather than a counter in SDL,
snapshot metadata, or audit details.

### Reference lifecycle and reset authority; do not add a reset machine

The activity policy states dispositions at existing range lifecycle boundaries:
start/resume, pause, drain, reset-generation advance, and teardown. It must
define whether new occurrences are admitted, whether in-flight work may
finish, the finite drain bound, and how pending work is discarded. These are
policy reactions to an external lifecycle event, not a new scheduler or
authoritative range-state machine.

Participant episode reset/restart under ADR-013/054 is unrelated. Workflow
compensation, process restart, persistent-volume retention, backend
reconciliation, experiment re-execution, and historical baseline versioning are
also distinct.

The in-flight #857 contract owns deployment tenant/cell identity,
shared-service mutable-state ownership, and `reset_generation_owner`. Live
activity references and obeys that ownership; it does not redeclare the owner
or increment a mutable counter in SDL. A generation transition invalidates all
older-generation occurrence submissions and readbacks. Pause/resume does not
mint a generation. Teardown uses existing reverse dependency and
ownership-safe reconciliation semantics and never deletes state owned by
another tenant/service.

### Keep authored policy, readback, telemetry, and proof separate

The authored template states intended effects and the required readback policy.
Native product state and normalized readback are observations. They can support
execution evidence only after target, tenant, reset generation, action
occurrence, adapter identity/version, observation source, time, transformation,
loss/redaction, and contract/baseline digests are correlated.

Trusted telemetry provenance must use the existing plane separation:

- apparatus diagnostics/audit remain operational observability;
- raw action/readback material uses experiment evidence/artifact carriers when
  it becomes run evidence;
- normalized or derived interpretations cite their source evidence;
- realized adapter/readback choices use realized-form disclosure and
  realization-observation/provenance patterns; and
- participant-visible projection still passes participant observation,
  marking, redaction, and information-flow policy.

An authored readback requirement is not proof of execution. A native success
response is not authoritative readback. Normalized readback is not authored
truth. Activity telemetry, product state, control-plane audit, and backend logs
must never create participant action receipts, behavior-history events,
objective truth, scores, or non-participant proof merely by sharing an actor,
target, timestamp, or label. Proof safety requires an explicit carrier and
complete provenance join; missing, stale, cross-tenant, cross-generation,
ambiguous, lossy-without-disclosure, or untrusted provenance fails closed.

## Canonical Incumbents To Reuse

- **SDL ingress and phases:** `load_sdl_yaml()`, parser source/alias/size
  limits, duplicate-key and JSON-domain checks, `SDLModel(extra="forbid")`,
  `ScenarioContent`, `Scenario`, `ExpandedScenario`,
  `InstantiatedScenario`, `parse_sdl()`, `instantiate_scenario()`,
  `admit_instantiated_scenario()`, and concrete semantic revalidation.
- **Identity, composition, and references:** `PortableIdentifier`,
  `QualifiedName`, `DeclarationIndex`, `build_declaration_index()`,
  `_mapping_scopes.HASHMAP_SECTIONS`,
  `_module_symbols.HASHMAP_SECTIONS`, `symbol_index()`, composition rewrite
  maps/budgets, `specs/sdl/sections.md`, `specs/sdl/references.md`,
  `_language_metadata`, and `tools/check_sdl_catalog_parity.py`.
- **Targets and state:** named `Node.services`,
  `RUNTIME_SERVICE_FAMILIES`, runtime child-reference metadata,
  `PersistentVolume`, stateful-resource reference analysis, ADR-082, and the
  #857 deployment-tenant/cell/shared-service contract. Runtime inventory is
  referenced but not copied.
- **Determinism and identity:** ADR-076, ADR-084,
  `canonical_sdl_digest()`, `canonical_instantiated_sdl_digest()`,
  `SemanticDigest`, `PrefixedDigestString`,
  `RandomStreamControlBindingModel`, `StreamAddressModel` only for its declared
  trial purpose, `blake3-xof-v1`, the stateless random-stream engine, and random
  draw records.
- **Graphs, planning, and lifecycle:** the shared SDL topological helper,
  `aces_processor.semantics.planner`, `RuntimeModel` address invariants,
  `PlannedResource`/`PlanOperation`, direct plan admission,
  `RuntimeSnapshot`, backend reconciliation, and reverse delete ordering.
- **Capabilities and realization:** `BackendManifest`,
  `BackendCapabilitySet`, supported-contract validation, governed concept
  bindings/vocabularies, `RealizationSupportDeclaration`,
  `realization_support_diagnostics()`, realization envelopes, and backend
  conformance. Activity capability must extend these authorities rather than
  create a pack-local registry.
- **Errors and runtime envelopes:** bounded source-anchored
  `SDLParseDiagnostic`/`SDLParseError`, collect-all `SDLValidationError`,
  `SDLInstantiationError`, `Diagnostic`/`Severity`, `ApplyResult`,
  `OperationReceipt`, `OperationStatus`, `_call_backend_diagnostics()`, and
  `_call_backend_apply()`. No new exception hierarchy is warranted.
- **Security, persistence, and API:** `ControlPlaneSecurityConfig`,
  strict bearer/verified-proxy identity, `ControlPlaneRole`, target binding,
  request-size guards, idempotency keys/fingerprints, `AuditEvent`,
  `ControlPlaneStore`, atomic snapshot persistence, response models, and the
  redacted FastAPI internal-error envelope.
- **Evidence and provenance:** ADR-056/057/064/065/066,
  `ExperimentEvidenceRecordModel`, `ExperimentRunModel` traceability,
  `ExperimentRealizedFormDisclosureModel`,
  `RealizationProvenanceEntry`, realization-observation contracts, participant
  observation/context views, markings, redaction, loss, and augmentation
  disclosures.
- **Authority and workflow:** ADR-009/019/036/061/062/072/075/080,
  `ContractModel(extra="forbid")`, `schema_bundle()`,
  `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/schema-publication-manifest.json` and per-schema entries, SDL
  lineage ledger, `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_semantic_coverage.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers And Gates

1. **Source and structural shape.** Activity input remains inert
   `sdl-yaml/v1` data. It passes bounded safe YAML construction, UTF-8 and
   byte/scalar/alias/node/depth limits, tag/directive rejection, duplicate-key
   checks, canonical structural fields, JSON-domain checks, closed models,
   identifier/cardinality bounds, and value-safe model diagnostics. No value
   triggers network, filesystem, provider, process, or credential activity.
2. **Composition and instantiation.** Every declaration and external reference
   enters the canonical section/symbol/rewrite catalogs. Variables may occupy
   authorized leaf fields but never declaration keys, profile ids, or
   identity-bearing generation coordinates. Expansion preserves provenance and
   budgets; instantiation removes every `${...}` token and reruns the complete
   semantic pass.
3. **Semantic policy.** One pure activity analyzer owns actor disjointness,
   target/context resolution, dependency acyclicity, tenant/generation
   agreement, finite schedule bounds, capability requirement coherence, budget
   hierarchy, lifecycle/reset ownership, readback policy, and proof-safety
   declarations. The `SemanticValidator` adapter only renders its stable issues.
   Model validators own local shape, not graph joins; compiler/runtime
   validators replay or strengthen the same decisions rather than restating
   them.
4. **Published contract shape.** Scenario-containing schemas, generated
   `schema_bundle()` output, positive/negative fixtures, publication hashes,
   semantic-invariant disclosures, section/reference catalogs, language
   metadata, and lineage evidence move together. JSON Schema proves structure,
   not cross-artifact semantics or runtime support.
5. **Capability and runtime admission.** A selected manifest must advertise the
   exact activity contract/profile and protocol capability before dispatch.
   Direct plan/control-plane submission repeats target, address, generation,
   dependency, budget, capability, and baseline-digest admission; backend
   `validate()` is an additional stricter gate, never the only gate. Any error
   prevents a native adapter call.
6. **Authentication and authorization.** DSL-437 adds no route or caller role.
   Any future activity submit/read route must use strict control-plane
   authentication, target-bound operator/backend authorization, request-size
   limits, idempotency/fingerprint checks, and audit. Tenant identity,
   background-actor authority, target reachability, adapter support, and caller
   authorization are independent deny-first gates.
7. **Secrets and configuration.** Credentials are unrepresentable in authored
   templates, contexts, schedules, action addresses, diagnostics, fixtures, or
   telemetry. Portable contracts may carry an existing account ref or governed
   secret-reference identity/version only. They carry no token, password, key,
   cookie, header, URI userinfo, environment value, `.env` binding, host path,
   provider config, or native handle. SDL variable binding is not a secret
   resolver.
8. **OS and process exposure.** This authoring/validation change adds no
   listener, socket, file, mount, subprocess, shell, or process argument.
   Future adapters use typed in-process calls or bounded stdin/files, fixed
   argv, no shell interpolation, controlled working directories, bounded
   input/output/time, and non-argv secret delivery. Raw actions, credentials,
   policy bodies, observations, or secret refs never enter argv, environment
   captures, stdout/stderr, filenames, or logs.
9. **Errors, logging, and API envelopes.** Expected source/semantic failures use
   existing SDL errors; runtime failures use bounded `Diagnostic` and operation
   envelopes; HTTP uses explicit bounded 4xx responses and the existing generic
   `{"detail":"internal server error"}` for unexpected failures. Logs/audit may
   contain safe ids, digests, profile/adapter versions, counts, disposition
   codes, stage outcomes, and durations only—not credentials, action bodies,
   parameter maps, native objects, readback payloads, documents, or tracebacks.
10. **Persistence and observation.** This requirement adds no live store.
    Canonical instantiated snapshots preserve authored policy. If action
    occurrences later become durable, use a first-class append-only,
    generation-scoped carrier through `RuntimeSnapshot` and
    `ControlPlaneStore`; do not use snapshot `metadata`, operation `details`,
    audit blobs, backend DTOs, raw logs, or a mutable global queue. Archival
    evidence and run provenance remain experiment-core artifacts.
11. **Package and policy boundary.** Authoring and pure semantic analysis stay
    in `aces_sdl`; neutral published DTOs/profiles in `aces_contracts`;
    compilation in `aces_processor`; live admission/security in `aces_runtime`;
    adapter capability/protocols in `aces_backend_protocols`; native behavior
    in backend packages; conformance in `aces_conformance`. Add no implementation
    logic to compatibility-only `implementations/python/src/aces/` and no
    owning package imports `aces.*`.

## Dependency And Merge Guardrails

The in-flight `origin/857-enterprise-deployment-tenancy` branch is a binding
dependency, not merely inspiration. It adds ADR-087, `deployment_tenants`,
`deployment_cells`, shared-service isolation/authentication/state/reset
ownership, pure deployment-tenancy analysis, schema/catalog/lineage changes,
and compiled placement work. DSL-437 must merge the landed contract normally
and reuse its exact tenant and reset-owner identities. It must not add temporary
`tenant_id`, cell, shared-state owner, or reset-owner fields and later try to
reconcile them.

The local `859-authored-historical-state` branch currently has no delta from
`dev`, so the historical baseline contract, digest carrier, and generation
relationship are not inspectable. DSL-437 must not guess or duplicate their
shape. The implementation may define activity-side references only after #859
is reviewable, and must bind to that contract's canonical identity/digest
instead of embedding historical state or inventing a baseline schema.

Both dependencies overlap the scenario-containing published schemas, semantic
catalogs, lineage ledger, and likely reference-resolution surfaces. Resolve
them with real merges and semantic conflict resolution. Never regenerate over
hand-governed schema changes, drop one side's publication entries, or treat
valid JSON as proof that tenant, generation, baseline, and activity identities
agree.

## Extensibility Seam

The seam is a closed discriminated activity-template kind plus versioned
protocol-capability, schedule, occurrence-identity, budget, readback, and
telemetry profiles. A bound action supplies stable references to the template,
actor, tenant/generation, target service, execution context, dependencies, and
those profile ids. A selected apparatus supplies a compatible native adapter
identity/version and exact capability declaration.

The next likely changes are another protocol operation, a new product adapter,
a new bounded recurrence/intensity policy, another resource dimension, a new
normalized readback shape, or a new telemetry sink. Each should add one
governed kind/profile term and its validator/fixture/conformance dispatch. It
must not require a new topology, scheduler language, actor hierarchy, tenant or
baseline schema, generic options map, exception family, store, or telemetry
root. A provider adapter can vary without changing authored action meaning, and
a new schedule or identity algorithm mints a new profile rather than silently
changing existing bytes.

## Gotchas And Anti-Patterns

Avoid:

- reusing `agents`, participant behaviors/action contracts, objective actor
  bindings, participant implementations, runtime scheduled jobs, workflows,
  injects/events/scripts, or runtime orchestration authorities as background
  activity merely because one field appears similar;
- letting ordinary activity emit participant receipts/history, satisfy
  participant objectives, influence scores, or become proof without an
  explicit provenance-bearing projection;
- copying nodes, services, accounts, tenants, volumes, historical state,
  endpoints, or runtime inventory into activity declarations;
- putting commands, URLs, query/body/header text, credentials, host paths,
  environment maps, provider ids, SDK types, native handles, or arbitrary
  `options`/`properties` in portable templates or execution contexts;
- conflating template requirement, manifest support, selected adapter,
  dispatch authority, execution result, normalized readback, evidence, and
  derived interpretation in one DTO;
- using a seed without exact generator/address/derivation/transform versions,
  or using wall time, UUIDs, worker order, retry count, hash iteration, native
  ids, or backend availability in action occurrence identity;
- overloading ADR-076 compiled addresses or `StreamAddressModel` with action
  occurrence identity;
- accepting open-ended schedules, unbounded fan-out/retry, floating-point
  identity/rate arithmetic, implicit dependency edges, or lexical ordering as
  execution order;
- treating budgets as observed utilization or mutable global token buckets,
  combining participant reserve with background allowance, or claiming fleet
  feasibility from scenario-local validation;
- equating pause with reset, participant reset with range generation, process
  restart with baseline restore, volume retention with reset ownership, or
  teardown with destructive deletion of unowned state;
- accepting readback from the wrong tenant, generation, target, adapter,
  baseline, or action occurrence; accepting success status as readback; or
  treating normalized state as authored authority;
- storing occurrence state, raw readback, or provenance only in `metadata`,
  `details`, audit blobs, diagnostics, tags, backend-native DTOs, or logs;
- adding duplicate section registries, reference resolvers, graph algorithms,
  schema generators, capability registries, validators, exception hierarchies,
  log formats, audit streams, persistence stores, schedulers, or CI workflows;
  and
- hand-editing one generated/published schema without the other
  scenario-containing contracts, publication entries, fixtures, catalogs,
  lineage, and generator parity.

## Non-Goals And Implementation Boundary

- This preflight does not implement DSL-437, define final serialized field
  names, update requirement status, publish an ADR, schema, model, fixture,
  adapter, runtime protocol, API, store, scheduler, or test.
- DSL-437 is portable authoring and semantic validation. It does not implement
  a scheduler, worker pool, fleet orchestrator, token bucket, native service
  client, credential broker, secret store, direct database mutation, PCAP
  replay, health-check generator, product emulator, or cleanup daemon.
- It does not add provider credentials, endpoints, commands, scripts, request
  bodies, adapter configuration, cloud allocation, or database-native mutation
  to SDL.
- It does not replace exercise events, participant behavior, participant
  lifecycle, participant action admission/receipts, runtime inventory,
  scenario variation/trial selection, workflow compensation, backend teardown,
  historical-state authority, experiment run/evidence provenance, or research
  telemetry.
- A valid policy proves authored coherence only. It does not prove target
  reachability, credentials, provider support, capacity availability,
  scheduling fairness, exact timing, execution, native state change,
  readback correctness, cleanup, participant isolation, or behavioral
  authenticity.
