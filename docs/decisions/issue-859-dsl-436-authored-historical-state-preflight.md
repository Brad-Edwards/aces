# Issue 859 / DSL-436 Initial Service State Preflight

Date: 2026-07-24

This note records architecture guardrails only. It does not implement the
issue or prescribe an implementation sequence.

## Preflight Finding

The current draft is not a viable base for incremental completion. It adds a
parallel `historical_baselines` ontology across SDL, schemas, compiler models,
backend capabilities, lineage, examples, and tests. That conflicts with the
authoritative issue boundary: age and narrative history are not a distinct
semantic object class, and initial scenario data must reuse top-level
`content`. The draft also declares backend support without an executable native
service materializer or participant-equivalent readback path, so it cannot
satisfy the operational acceptance criterion.

The demonstrated repository gap is precise:

- `Content` already owns files, directories, datasets, item identities,
  sources, sensitivity, and node targets.
- `_compile_content_placements()` already lowers each entry to a canonical
  `ContentPlacement`.
- planner admission already checks `supported_content_types`.
- the libvirt reference backend already realizes node content through
  cloud-init and has guest-observation infrastructure.
- none of those contracts can request or prove exact materialization into a
  named service-owned store through a provider-neutral native interface.

The intended design therefore extends content placement in place. It does not
add a historical topology.

## Architecture Decisions and Guardrails

### Keep one content authority

The stable authored identity is the existing `content.<id>` address within an
immutable instantiated-scenario snapshot. The content payload digest identifies
the revision. A staged payload also retains its existing immutable
`Source`/associated-artifact identity, version, checksum, size, sensitivity, and
trust result. Do not mint historical-object ids, semantic-address profiles,
baseline digests, or native-id aliases.

Ordinary node placement stays unchanged. The optional extension is used only
when a concrete gap case proves that node placement cannot establish the
required service state. It must bind:

- one existing content identity;
- one existing named `nodes.<node>.services.<service>` target;
- one versioned, provider-neutral materialization-interface profile;
- closed exact requirements for that profile;
- the applicable ADR-087 `uses_shared_service` relationship and reset owner
  when the target owns shared mutable state;
- existing ordering/refresh dependencies; and
- existing observed-state assertions, evidence requirements, and participant
  observation-boundary refs.

The service profile owns only operation semantics and readback mapping. Content
payload structure stays in `content`; corpus bytes stay in content or an
associated artifact. Product exports and runtime inventory remain observed
state.

### Evidence-gate standardized profiles

Do not add speculative standard profiles. For every profile admitted to the
controlled vocabulary, the same change must provide:

1. an operational adapter reached through the production
   compile/plan/validate/apply path;
2. ownership-safe native create/update/reset behavior;
3. fresh, independently bound `RealizationObservation` readback from the native
   service;
4. projection through the declared participant observation boundary;
5. proposition/assertion evaluation with evidence; and
6. negative conformance cases proving unsupported, stale, echoed, partial,
   cross-tenant, and mismatched results fail.

A fake adapter can test orchestration but cannot be the acceptance proof. A
backend manifest flag, realization envelope, successful API status, planned
payload echo, or native id is not evidence that materialization occurred.

### Reuse the existing execution and persistence path

Service-target content remains a `content-placement` resolved resource unless
an operational adapter demonstrates that the existing resource lifecycle
cannot represent it. Preserve its identity and exact requirement through
`RuntimeModel`, `resource_payload()`, `PlannedResource`, `PlanOperation`,
`ProvisioningPlanModel`, direct-submission validation, backend `validate()`,
`apply()`, `SnapshotEntry`, and control-plane persistence.

Admission is conjunctive:

- `supported_content_types` admits the content kind;
- the profile-specific provisioner capability admits the exact interface
  profile/version and content kind;
- SEM-218 admits the complete exact requirement;
- the selected realization envelope admits the required observation strength;
  and
- ADR-087 tenancy/reset ownership agrees with the exact target service.

Any missing term produces a blocking `Diagnostic` before I/O. There is no
downgrade, approximation, fallback profile, first-success routing, or implicit
adapter selection.

Successful apply preserves the normalized admitted content identity and reset
correlation in the existing snapshot/provenance carrier, with a safe reference
to fresh observed evidence. Raw native payloads do not enter snapshots,
operation details, audit details, or logs. The observed result is an
`experiment-evidence-record-v1`; `experiment-run-v1` remains the archival join
point through its scenario snapshot ref, apparatus context, realized-form
disclosures, evidence traceability, and stochastic controls. Do not add a
materialization-result database or a second run-provenance schema.

### Reuse reset and deterministic-generation authority

ADR-087 owns shared-service state and reset-generation ownership. The new
contract references that authority; it does not create a reset controller or
generation lifecycle. A reset must use the same content identity and exact
profile, bind the new run/reset correlation, produce fresh readback, and retain
prior archival evidence. Native cleanup/adoption requires ownership proof for
the exact tenant, service, content identity, profile/version, and reset
correlation; name matching is insufficient.

Generated content reuses scenario variables, variation points,
`InstantiationProvenance`, random-stream profiles and addresses, draw records,
and experiment-run stochastic controls. Profile requirements may reference
their resolved outputs but may not define another seed, random generator,
clock, retry-based id, timestamp-derived version, or provider-selected corpus.

## Canonical Incumbents to Reuse

- **SDL identity and phases:** `Content`, `ContentItem`, `Source`,
  `ScenarioContent`, `Scenario`, `ExpandedScenario`, `InstantiatedScenario`,
  `InstantiationProvenance`, `InstantiatedScenarioSnapshot`,
  `canonical_sdl_digest()`, `canonical_instantiated_sdl_digest()`, and
  `admit_instantiated_scenario()`.
- **Parsing and shape:** `load_sdl_yaml()`, `SDLSourceParseOptions`,
  `SDLParserLimits`, duplicate-key/YAML-domain checks,
  `SDLModel(extra="forbid")`, `PortableIdentifier`, and `QualifiedName`.
- **References and composition:** `HASHMAP_SECTIONS`,
  `NESTED_HASHMAP_FIELDS`, `symbol_index()`, `build_declaration_index()`,
  `_namespace_payload()`, `_rewrite_section_ref()`, module collision/export
  checks, composition budgets, and post-instantiation revalidation.
- **Compilation and planning:** `_compile_content_placements()`,
  `ContentPlacement`, `RuntimeModel`, `ResolvedResource`,
  `resource_payload()`, planner dependency/cycle checks,
  `PLAN_RESOURCE_TYPES_BY_DOMAIN`, `ProvisioningPlan`, and
  `ProvisioningPlanModel`.
- **Admission and realization:** `ProvisionerCapabilities`,
  `BackendManifest`, controlled capability vocabularies,
  `CompiledRealizationRequirement`, `realization_support_diagnostics()`,
  `realization_envelope_diagnostics()`, `realization_disclosure()`,
  `RealizationObservation`, backend contract validation, and conformance
  observation binding/freshness checks.
- **Tenancy, reset, and state:** ADR-087 `deployment_tenants`,
  `deployment_cells`, `RelationshipSharedService`, `PersistentVolume`, state
  owner, and reset-generation owner. Participant episode reset, volume
  lifecycle, and backend restart are not substitutes.
- **Readback and evidence:** `Proposition`, `Assertion`,
  `EvidenceRequirement`, `ParticipantObservationBoundary`,
  `ParticipantObservationBoundaryRuntime`, truth outcomes,
  `experiment-evidence-record-v1`, ADR-066 evidence-plane separation, and
  `experiment-run-v1`.
- **Determinism:** variation points, instantiation binding provenance,
  `StreamAddressModel`, `random_stream_engine`, random-stream profiles/draw
  records, and experiment stochastic controls. Reuse their discipline, not
  necessarily their byte namespace.
- **Persistence and errors:** `Diagnostic`, `Severity`, `ApplyResult`,
  `RuntimeSnapshot`, `SnapshotEntry`, `RealizationProvenanceEntry`,
  `_call_backend_diagnostics()`, `_call_backend_apply()`,
  `ControlPlaneStore`, atomic writes, operation receipts/statuses, and audit
  events. Reuse `SDLError`, `SDLParseError`, `SDLValidationError`, and
  `SDLInstantiationError`; add no parallel exception hierarchy.
- **Artifact trust and publication:** associated-artifact manifests, ADR-071
  trust/integrity rules, schema publication manifest/entries,
  `schema_bundle()`, SDL catalog parity, controlled vocabularies, concept
  authority, lineage ledger, fixtures, and the authority-boundary manifest.
- **Workflow:** `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_authority_boundary.py`, `tools/check_schema_publication.py`,
  `tools/check_generated_schemas.py`, `tools/check_sdl_catalog_parity.py`,
  `tools/check_sdl_lineage.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers the Design Must Pass

1. **Source/parser validation.** Input remains inert bounded YAML. Existing
   UTF-8, byte/scalar/node/depth/alias/import budgets, duplicate-key rejection,
   forbidden tag/directive handling, canonical key rules, and parse diagnostics
   run before model construction. Parsing performs no product or network I/O.
2. **Closed config shapes.** `Content` and a discriminated profile contract
   reject unknown fields. Profile requirements have typed bounds and no
   `options`, `properties`, `command`, `query`, `endpoint`, `env`, or `other`
   escape hatch. Provider credentials and native identifiers are
   unrepresentable.
3. **Semantic validation.** The central declaration index resolves content,
   service, relationship, state, assertion, evidence, and observation refs.
   One pure analyzer owns cross-field profile/target/tenancy/reset/readback
   agreement; field validators do not duplicate graph rules.
4. **Composition and instantiation.** Existing namespace and rewrite catalogs
   carry every new ref. Mapping keys remain non-variable; allowed variable
   values must resolve; all invariants rerun after substitution. The
   instantiated snapshot/digest freezes exact content identity and generation
   inputs.
5. **Published contract validation.** The four scenario-containing schemas,
   `x-aces-invariants`, valid/invalid fixtures, generator parity, publication
   hashes, reference catalog, concept vocabulary, and lineage must agree.
   Editing only Python or only a generated schema is invalid.
6. **Planner/backend admission.** Canonical address/resource-type checks,
   dependency ordering, content-kind capability, exact profile capability,
   SEM-218 exactness, realization-envelope observation strength, and backend
   `validate()` all pass before `apply()`. Directly submitted plans pass the
   same gates.
7. **Authentication/authorization.** No new authoring privilege is created. Any
   HTTP execution surface retains `ControlPlaneSecurityConfig.strict_defaults`,
   verified bearer/proxy identity, target binding, mutating/read role
   separation, request-size limits, idempotency fingerprints, and audit.
   Authored tenant/product principals are never control-plane identities.
8. **Secret/config handling.** Scenario fixture secrets remain subject to
   ADR-057, but real adapter credentials are external operational secrets
   resolved at an authorized sink. No new CLI credential argument, portable
   environment binding, `.env` contract, URI userinfo, raw token, or private
   key field is authorized.
9. **OS/process exposure.** SDL and plan data never becomes a shell command.
   An adapter uses an injected client or fixed allowlisted argv, no shell,
   bounded input/output/time, controlled cwd/environment, and non-argv secret
   delivery. Corpus bodies, credentials, native ids, queries, and rejected
   payloads never enter argv, filenames, stdout/stderr, or environment
   captures.
10. **Error envelopes and logging.** Expected failures are bounded
    `Diagnostic`/SDL errors with stable codes, safe ACES addresses, and generic
    messages. `_call_backend_apply()` rejects malformed results and preserves
    the prior snapshot. HTTP 500 remains `{"detail":"internal server error"}`.
    Do not expose native exception text, response bodies, queries, credentials,
    paths, ids, or tracebacks in diagnostics, audit, logs, or evidence
    summaries.
11. **Persistence and evidence.** Atomic control-plane persistence retains
    portable desired identity and safe provenance/evidence refs. Native
    readback becomes validated evidence with operation, apparatus, profile,
    target, tenant/reset, freshness, and participant-projection bindings.
    Support declarations and desired snapshots cannot satisfy observation.

## Extensibility Seam

The seam is the versioned tuple:

`(interface_profile, profile_version, content_kind, participant_projection)`

Each profile supplies a closed requirement model, capability predicate,
materializer, readback mapper, required observation strength, and conformance
cases behind the existing content-placement and backend protocol. A second
service implementation of the same profile changes the adapter and apparatus
evidence, not SDL identity. A genuinely different portable operation adds a new
evidence-backed profile without changing unrelated content kinds.

Replica selection and fan-out are not implicit. A future replica-aware profile
must add a stable instance-selection and consistency policy; it may not use
native ids, discovery/list order, first success, or provider defaults.

## Gotchas and Anti-Patterns

- Do not retain, rename, or slim `historical_baselines`; remove the concept.
- Do not create historical actors, events, relationships, address/digest
  profiles, lifecycle graphs, or object kinds for messages/records already
  represented by content.
- Do not treat old timestamps as identity, causality, generation input, or
  proof of history.
- Do not put product exports, SDK objects, commands, queries, table/mailbox
  schemas, adapter options, credentials, or native ids in SDL.
- Do not duplicate content identities inside a materialization binding.
- Do not infer target, tenant, reset owner, participant visibility, or profile
  from product/service names or a sole candidate.
- Do not adopt, update, or delete a native object by name alone.
- Do not collapse content support, profile support, exact realization,
  execution success, native readback, participant visibility, and assertion
  truth into one Boolean.
- Do not call planned data, a capability flag, a success response, or a value
  echoed by the adapter independent readback.
- Do not store native results in `RuntimeSnapshot.metadata`,
  `ApplyResult.details`, audit details, generic tags, or logs.
- Do not create duplicate schemas, validators, resolvers, exception
  hierarchies, stores, lifecycle engines, predicate languages, evidence
  formats, run-provenance roots, or CI workflows.
- Do not standardize a profile with only unit tests, a fake backend, or
  self-skipping integration evidence.
- Do not implement owning logic under compatibility-only
  `implementations/python/src/aces/`, hand-edit generated output alone, omit
  schema publication records, or update only one document phase.

## Non-Goals and Implementation Boundaries

- No general historical ontology, event-history/replay contract, age model,
  narrative reconstruction, product audit-log authoring, or trajectory model.
- No product-specific SDL schema, native inventory authority, provider id,
  endpoint, query, command, credential, or corpus export format.
- No new reset controller, scheduler, tenant database, identity service,
  materialization repository, observation database, or archival run root.
- No claim that authored initial state proves native creation time, past user
  activity, audit provenance, participant exposure, adapter correctness,
  successful reset, or backend equivalence.
- No standard interface profile without an operational adapter and
  participant-equivalent readback proof in the same supported surface.
- Event-history semantics remain a separate future contract, justified only
  when an authoritative replayable event sequence—not initial service
  state—is the requirement.
