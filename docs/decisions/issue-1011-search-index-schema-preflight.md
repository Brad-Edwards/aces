# Issue 1011 Search-Index Field-Schema Preflight

Date: 2026-07-31

Issue: #1011.

Requirement: none. The GitHub issue is the delivery contract.

This note fixes the architecture boundary for a provider-neutral exact
search-index field schema. It is guidance only: it does not add the profile,
change an SDL model or published schema, claim backend support, or implement a
native materializer.

## Decision Boundary

Add a second closed service-materialization profile for search-index schema
state. Do not reinterpret or mutate `service-content` v1, whose operation and
readback concern owned documents or records. The new profile remains a variant
of `content.<id>.service_materialization` and compiles through the existing
`content-placement` lifecycle; it is not a top-level schema resource, datastore
inventory entry, plan, repository, controller, or lifecycle engine.

The profile identity and capability term are versioned independently:

- interface profile `service-search-index-schema`, version `"1"`; and
- provisioner capability `service-search-index-schema-v1`.

These spellings are contract authority and must stay identical across the SDL
model, controlled vocabulary, manifest fixture, specification, schemas,
examples, and tests. Do not use `service-content-v2` merely to avoid a second
discriminated variant: document reconciliation and schema reconciliation have
different operations, desired-state payloads, collision behavior, and readback
projections.

The closed v1 requirements are:

- `operation: ensure-search-index-field-schema`;
- `conflict_policy: reject-unowned-collision`;
- `readback: canonical-portable-field-schema-digest`; and
- `field_semantics`: one non-empty mapping from portable top-level field names
  to this closed portable semantic set:

  - `exact-token`: equality/term matching without analysis or tokenization;
  - `full-text`: analyzed/tokenized text search;
  - `integer`: integral numeric comparison;
  - `temporal`: date/time comparison under the backend's documented portable
    projection; and
  - `boolean`: two-valued boolean comparison.

Vendor literals such as `keyword`, `text`, `long`, or product-native mapping
bodies are invalid authoring input. V1 proves the exact semantic of every
declared field. Undeclared native fields are outside the claim: native readback
projects exactly the declared field names, fails if one is absent, ambiguous,
or not projectable, and compares that portable projection. A native multi-field
or analyzer fallback does not satisfy `exact-token` for the exactly named
field.

The operation must establish the index and declared field semantics before the
provisioning apply succeeds. An incompatible existing mapping is a failed
reconciliation, not permission to delete/recreate an index, adopt an unowned
index, enable dynamic auto-creation, or silently weaken a field. Reset and
destructive recreation remain governed by the existing ownership contract.

Schema-only initial state must be authorable without a dummy `ContentItem`,
fake source payload, or vendor bootstrap bytes. Any narrow relaxation of the
ordinary dataset payload rule must be discriminated by this profile; it must
not make empty ordinary datasets generally valid or silently combine document
insertion with schema reconciliation. Initial items remain a separate
`service-content` concern unless a later version defines and proves a combined
operation. V1 reuses `ContentType.DATASET` and the existing dataset capability
check; it adds no `schema` content type and accepts no `source` or `items`
payload for this schema-only operation.

The portable logical store identity is the canonical `content.<id>` address
bound to the exact `target_service_ref`. A product-native index id such as
`cortex_6` stays in the backend adapter/configuration boundary. A backend may
claim that concrete result only when its operational conformance evidence binds
that native store to the admitted content address and observes it freshly.

## Desired State, Support, And Proof

Keep these three claims separate:

1. The authored field map plus its RFC 8785/JCS SHA-256 digest is exact desired
   state. Compilation retains the portable map and a derived schema digest in
   the profile-specific compiled binding, the `content-placement` payload, plan
   operation, and snapshot transition. The existing content payload digest
   remains a different digest and must not stand in for the field-schema
   digest. Digest the closed portable projection containing profile id, version,
   projection scope, and field map, not the bare map or native response.
2. `supported_service_materialization_profiles` plus SEM-218 exact support and
   the realization envelope admit the operation. A v1 profile claim means the
   backend supports the complete closed v1 semantic set; partial support must
   not advertise the profile.
3. Only fresh native readback projected to the same portable field map proves
   success. Use `RealizationObservation` with
   `RealizationConcern.CONTENT_PLACEMENT`, the existing strength, binding, and
   freshness checks, and the bound assertion/evidence/observation-boundary
   path. A mutation response, returned desired-state snapshot, manifest claim,
   cached mapping, or planned digest is not proof.

The SEM-218 snapshot comparison remains necessary to reject an omitted or
changed exact requirement, but it is not independent readback. The
`RuntimeDatastoreMapping` family remains observed runtime inventory: its
type-count census and schema digest must not become the authored field map or a
second desired-schema DTO. A backend observer may inspect native mapping data
privately, but only the bounded portable projection and safe evidence reference
cross the portable boundary.

## Canonical Incumbents

The implementation must build on:

- authoring and closed shape: `raes.content`, `SDLModel(extra="forbid")`,
  `PortableIdentifier`, and a closed discriminated
  `ServiceMaterialization` profile union;
- composition and semantic validation: `raes.composition` and
  `SemanticValidator._verify_service_materialization()`, including target,
  ordering, assertion, evidence, observation-boundary, tenancy, and reset
  ownership checks;
- compilation and phase flow:
  `raes_processor.compiler.placement`,
  `ServiceContentMaterializationBinding` as the unchanged v1 variant,
  `ContentPlacement.service_materialization` as the typed variant carrier,
  `resource_payload()`, and the existing `content-placement` operations;
- exact realization:
  `_append_service_materialization_requirements()`,
  `CONCERN_PAYLOAD_PATH`, `realization_support_diagnostics()`,
  `realization_disclosure()`, and runtime snapshot sanitization. Preserve
  `service-content-materialization` for v1 and use the distinct
  `service-search-index-schema-materialization` requirement kind for the new
  profile; both use the same machinery and payload path;
- planner and direct-submission admission:
  `service_materialization_plan_diagnostics()` as the shared closed-contract
  gate, called by both the planner and
  `raes_runtime.control_plane_submission`;
- capability and concept authority:
  `ProvisionerCapabilities`,
  `ProvisionerCapabilitiesModel`,
  `backend_manifest_payload()`, manifest parsing, and
  `contracts/concept-authority/controlled-vocabularies-v1.json`;
- canonicalization:
  `raes_contracts.canonical.canonical_json_digest()` rather than a new digest
  serializer;
- proof and conformance:
  `RealizationObservation`, `ExpectedRealizationObservation`,
  `operation_inventory_diagnostics()`, `observation_diagnostics()`, and the
  existing content-placement concern/strength mapping;
- errors and persistence:
  `Diagnostic`, `ApplyResult`, `RuntimeSnapshot`, realization provenance,
  `experiment-evidence-record-v1`, and `experiment-run-v1`; and
- contract publication:
  `schema_bundle()`, the four scenario-containing published schemas, their
  publication entries and `last_change` hashes, fixtures, SDL lineage,
  `specs/sdl/initial-service-state.md`, the public section reference, example,
  and `test_initial_service_state.py`; ADR-061 remains the schema-evolution
  policy; and
- repository workflow: `.ground-control.yaml`, `.gc/plan-rules.md`, the
  canonical nox graph, `check_repo_policy.py`,
  `check_requirement_governance.py`, `check_generated_schemas.py`,
  `check_schema_publication.py`, concept-authority checks, SDL-lineage checks,
  and `verify_all.py`. Release Please owns `CHANGELOG.md`.

Keep one profile dispatch inside the existing service-materialization model,
compiler, and admission module. Do not copy profile literals, allowed fields,
or semantic mappings into unrelated planner, runtime, backend, and test-local
tables.

## Cross-Cutting And Security Gates

- **Parse and shape:** strict SDL/YAML parsing and `SDLModel` reject unknown
  fields, empty schemas, invalid field names, and unknown or vendor semantic
  literals. The profile contains no endpoint, URL, query, command, header,
  credential, environment variable, host path, native id, or arbitrary options
  map.
- **Composition and instantiation:** existing reference rewriting applies only
  to actual SDL refs. Field names and semantics are values, not references.
  Every instantiated field semantic must be concrete before compilation; no
  backend selection or defaulting may resolve it.
- **Semantic admission:** the incumbent validator continues to prove exact
  target-service ownership, dependency references, observed-state assertions,
  evidence requirements, participant projection, shared-service tenancy, and
  reset ownership. Profile-specific payload rules are added there, not repeated
  as an unrelated whole-scenario validator.
- **Planner and direct submission:** the shared backend-protocol admission gate
  validates the closed compiled binding, profile/version, non-empty field map,
  recomputed canonical digest, content type, target address, ownership, bound
  readback refs, capability term, SEM-218 support, and observation strength
  before backend I/O. Unknown profiles and semantic values fail; there is no
  profile fallback or first-supported selection.
- **Authentication and request shape:** no new HTTP or MCP route is needed.
  Remote plan submission continues through the closed
  `ProvisioningPlanModel`, request-size guard, idempotency fingerprint,
  `ControlPlaneSecurityConfig.strict_defaults()`, verified identity,
  backend/operator role authorization, target binding, and audit event path.
- **Secrets and process exposure:** adapter credentials remain in private
  backend configuration or a secret resolver. They never enter SDL, plan
  payloads, snapshots, evidence, diagnostics, logs, environment bindings, or
  process argv. Any native helper uses fixed argv/no shell and bounded timeout;
  native API authentication is not a profile field.
- **Backend result and error envelope:** backend calls continue through
  `_call_backend_apply()` and return `ApplyResult` plus bounded `Diagnostic`
  values. Preserve the baseline snapshot on malformed output or failed
  readback. Do not add a profile-specific exception hierarchy, expose rejected
  mappings, response bodies, credentials, native ids, or tracebacks, or turn a
  provider error into a public diagnostic payload. The HTTP adapter's redacted
  internal-error handler remains the outer envelope.
- **Persistence and observability:** portable persistence retains declared and
  projected field semantics, canonical digests, operation/content addresses,
  observation strength, provenance, and safe evidence refs only. Raw native
  mappings, service responses, headers, adapter configuration, and credentials
  remain out of `RuntimeSnapshot`, `ApplyResult.details`, control-plane audit
  records, experiment artifacts, logs, and telemetry.

Provisioning success is the ordering barrier for later orchestration and
participant admission. Native service readiness/retry belongs inside the
backend adapter and must be bounded and idempotent; do not reintroduce a
one-shot VM node, shell bootstrap, sidecar scheduler, or unbounded poll loop.

## Extensibility Boundary

The extension seam is the profile-versioned portable semantic projector and the
backend adapter's semantic-to-native mapping. A second Elasticsearch,
OpenSearch, or non-Elasticsearch backend implements the same portable v1
semantics without changing SDL or the canonical digest. Adapter selection,
native index identity, credentials, connection policy, timeout, and retry
policy stay backend-local.

Nested field paths, analyzers, collation, decimal/binary/geospatial types,
nullability, cardinality, dynamic-template policy, aliases, and a claim that no
additional fields exist are not implied by v1. Add only a demonstrated portable
semantic through a new profile version (or a separately named profile when the
operation/readback relation changes), with its own exact projection and
capability term. Do not add an open string or vendor extension map to v1.

## Gotchas And Anti-Patterns

Avoid:

- extending `ContentItem` with a field type or treating an index as a document;
- overloading the existing `service-content-materialization` SEM-218 kind with
  schema-reconciliation meaning;
- making `RuntimeDatastoreMapping.field_type_census` authored desired state;
- accepting `keyword`, `_mapping`, index templates, native queries, endpoints,
  or `cortex_6` in the portable profile;
- hashing the raw native mapping, dictionary insertion order, or the whole
  service response instead of the canonical portable projection;
- treating additional native fields as a mismatch while v1's claim is scoped
  to declared fields, or accepting a missing/ambiguous declared field;
- accepting dynamic auto-creation, a mutation acknowledgement, a snapshot echo,
  or a manifest declaration as readback;
- silently translating an unsupported semantic, selecting a weaker type, or
  allowing partial profile capability claims;
- deleting/recreating an incompatible index outside reset ownership or adopting
  an existing index by native name;
- duplicating the profile schema, validation rules, diagnostic hierarchy,
  observation DTO, evidence carrier, persistence store, or workflow; and
- updating only the authoring model while leaving composition, all four
  scenario schemas, schema publication records, capability/concept authority,
  phase carriers, direct-submission admission, fixtures, docs, lineage, or
  negative tests stale.

## Non-Goals

- Implementing an Elasticsearch/OpenSearch/TheHive/Cortex adapter or releasing
  a backend support claim.
- Authoring vendor-native index names, mappings, analyzers, templates, queries,
  credentials, endpoints, or bootstrap payloads.
- General datastore schema migration, destructive reindexing, document
  insertion, historical-state modeling, event replay, or runtime inventory
  redesign.
- A full portable database DDL, nested-field, analyzer, cardinality, or
  dynamic-mapping language.
- A new materialization engine, plan, controller, repository, reset authority,
  exception hierarchy, API route, secret store, logging framework, or evidence
  contract.
