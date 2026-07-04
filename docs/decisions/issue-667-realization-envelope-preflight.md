# Issue 667 Realization Envelope Preflight

Date: 2026-07-04

Issue: #667.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records architecture guardrails for the realization-envelope design
work. It is guidance only: it does not publish the prior-art pass, formal
semantics, ADR, schema, conformance relation, or implementation.

## Architecture Decisions

- Treat the realization envelope as one SDL semantics extension, not as a
  second manifest capability language. Authored scenario families and backend
  realizability declarations must reference the same typed envelope expression
  model.
- Keep an envelope distinct from a concrete scenario, experiment run set,
  backend profile, semantic profile, `ProvisionerCapabilities`,
  `ParticipantRuntimeCapabilities.feature_support`, and today's
  `realization_support` declarations. Those surfaces may carry or consume an
  envelope, but none is the envelope semantics authority.
- Build the typed-variable substrate by extending the existing SDL variable and
  instantiation model. Do not create a parallel parameter system inside backend
  manifests, conformance, or `constraints` strings.
- Model open, constrained, and exact posture as a scope overlay from field to
  node, topology, app, and scenario. The design must define most-specific-wins
  override behavior and explicit closed-world "and nothing else" semantics.
  Absence of a bound is not universal realizability.
- Membership, subsumption, and witness generation are semantic services over
  the typed envelope expression. They must be decidable in the admitted fragment
  and shared by validation, planning, runtime/conformance checks, and tests.
  Avoid backend-local implementations of the relation.
- The manifest carriage decision should be made as a `backend-manifest` schema
  evolution question: embed an envelope expression or reference one by governed
  contract id/digest. Reusing today's coarse capability fields alone is not
  sufficient because they have no values, no scoped closed-world posture, and
  no set relation.
- Closed envelopes require negative conformance. A backend that declares "only
  this set" must be shown to refuse out-of-envelope requests, not merely accept
  one generated witness inside the envelope.

## Required Incumbents

Reuse these repo surfaces before adding anything new:

- SDL language and instantiation: ADR-001, ADR-003,
  `specs/sdl/variables-and-instantiation.md`, `aces_sdl.variables`,
  `instantiate_scenario()`, `SDLInstantiationError`, closed SDL models,
  variable-key rejection, and post-instantiation semantic revalidation.
- Shared semantic lifecycle: ADR-007, ADR-016,
  `docs/explain/reference/shared-semantic-integrity.md`, `SemanticValidator`,
  `SDLValidationError`, `compile_runtime_model()`, `plan()`, and shared
  `aces_sdl.semantics.*` / `aces_processor.semantics.*` helpers.
- Existing realization seam: `specs/formal/realization/explicitness-and-realization.md`,
  `docs/explain/reference/explicitness-realization-semantics.md`,
  `RealizationSupportMode`, `RealizationSupportDeclaration`,
  `CompiledRealizationRequirement`, `realization_support_diagnostics()`,
  `realization_disclosure()`, and `RuntimeSnapshot.realization_provenance`.
- Contract authority: ADR-009, ADR-019, ADR-061, `ContractModel`,
  `schema_bundle()`, `contracts/schema-publication-manifest.json`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, and `x-aces-invariants` annotations for
  semantic rules JSON Schema cannot express.
- Concept authority: ADR-012, ADR-062,
  `contracts/concept-authority/concept-families-v1.json`,
  `contracts/concept-authority/controlled-vocabularies-v1.json`,
  `contracts/concept-authority/reference-models-v1.json`,
  `validate_controlled_vocabulary_scope_values()`, and canonical
  `concept_bindings`. The `realization-and-disclosure` concept family governs
  realization semantics, not the cyber objects being realized.
- Backend declarations: `BackendManifest`, `BackendManifestV2Model`,
  `BackendCapabilitySet`, `ProvisionerCapabilities`,
  `ParticipantRuntimeCapabilities`, `backend_manifest_payload()`,
  `BACKEND_SUPPORTED_CONTRACT_IDS`, and existing capability-gap helpers.
- Conformance: `run_target_conformance()`, `run_fixture_suite()`,
  backend profile loading from `contracts/profiles/backend/`,
  `_validate_payload()`, semantic diagnostics, and `ConformanceCaseResult`.
  The #663 `reference_scenario` parameter is a temporary bridge to replace with
  envelope witness generation.
- Runtime and API security: `RuntimeControlPlane`, `ControlPlaneStore`,
  `ControlPlaneSecurityConfig`, `ControlPlaneIdentity`, `ControlPlaneRole`,
  request-size guard, idempotency fingerprints, audit events, redacted FastAPI
  error handling, `Diagnostic`, `OperationReceipt`, and `OperationStatus`.
- Experiment/evidence boundaries: ADR-055, ADR-066, ADR-068 and the
  experiment-core contracts. A realizable set is not an executed run set,
  replication study, raw evidence record, or replay claim.
- Repository policy: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/policy/adr_policy.yaml`, module-boundary rules, schema-publication
  checks, concept-authority gates, and `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL parser/model layer: envelope syntax must be structured model data, not
  raw strings embedded in `constraints`. Variables may parameterize values but
  must not create symbol keys or rename identities.
- Semantic validation layer: validate variable scope, domain type, domain
  boundedness, closure posture, most-specific override conflicts, and
  reference ambiguity through existing validation errors that collect all
  defects.
- Instantiation layer: parameter binding must type-check, domain-check, remove
  unresolved placeholders, preserve explicitness/envelope provenance, and rerun
  semantic validation on the concrete scenario.
- Contract/schema layer: public envelope payloads must be closed
  `ContractModel` shapes with generated schemas, fixtures, publication-manifest
  entries, and semantic-invariant annotations where relation checks are outside
  JSON Schema.
- Manifest layer: backend carriage must render through
  `backend_manifest_payload()` and validate with the manifest model. Do not add
  a second manifest renderer, schema registry, or profile map.
- Planner/runtime layer: admission failures and backend dishonesty must remain
  `Diagnostic` values on the existing plan/apply path. Diagnostics may name
  field paths, relation kinds, and envelope ids; they must not echo sensitive
  concrete values.
- Conformance layer: generated witnesses must still pass the live mutation
  guard, snapshot validation, and semantic diagnostics. Closed-envelope
  negative probes must expect refusal through the same `OperationStatus` /
  diagnostic envelope, not backend-native exceptions.
- HTTP/control-plane layer: any envelope admission or witness API must reuse
  authentication, role authorization, request-size limits, idempotency, audit,
  published response models, and redacted internal-error responses.
- Persistence/evidence layer: store envelope refs, digests, provenance,
  declarations, and bounded summaries. Do not persist credentials, bearer
  tokens, private keys, raw environment dumps, process argv, backend-native
  object representations, or full tracebacks in envelopes, snapshots,
  diagnostics, fixtures, audit details, or evidence records.
- Host/OS exposure layer: witness generation or external tooling must not put
  secrets, tokens, or sensitive realized values in command argv, logs, or
  diagnostics. If a later solver/tool is introduced, call it through a bounded,
  fixed-argv adapter and keep inputs secret-free.
- Module-boundary layer: put SDL syntax and variable typing in `aces_sdl`,
  neutral contract DTOs in `aces_contracts`, backend dataclasses/rendering in
  `aces_backend_protocols`, planning relation consumers in `aces_processor`,
  runtime admission at `aces_runtime`, and probes in `aces_conformance`.
  Respect the existing import DAG.

## Extensibility Boundary

The primary seam is a versioned envelope expression contract plus a pure
membership/subsumption/witness helper over that contract. The helper should be
parameterized by:

- governed scope/kind identifiers, so new SDL fields or runtime families add
  terms rather than editing every backend;
- domain descriptors, so finite sets, enums, numeric intervals, and future
  bounded domain kinds slot into the decidable fragment deliberately;
- carriage mode, so a backend manifest can embed a small envelope or reference
  a larger published envelope by contract id and digest; and
- witness selection policy/seed, so conformance can generate reproducible
  in-envelope scenarios without hard-coding one global reference scenario.

Adding a future domain kind, scope level, posture value, or carrier should
require changes to the formal spec, contract model/schema, fixtures, semantic
helper, and tests. It should not require per-backend relation logic or edits to
unrelated runtime/control-plane paths.

## Gotchas And Anti-Patterns

Avoid:

- preserving the current universal-realizability assumption in conformance;
- treating the #663 `reference_scenario` parameter as the final design;
- treating one successful witness as proof of subsumption or closed-world
  refusal;
- conflating exact singleton envelopes with exact realized values in SEM-218;
- merging envelope posture with `realization_support` support modes,
  participant feature support levels, backend profiles, semantic profiles, or
  experiment study membership;
- encoding domains or closure policy as prose in `constraints`;
- accepting arbitrary Python predicates, unbounded regex/SMT fragments, or
  backend-specific callbacks in portable envelopes;
- adding duplicate schemas, validators, exception hierarchies, audit logs,
  persistence stores, manifest renderers, vocabulary tables, or profile loaders;
- leaking backend-private topology, native IDs, host paths, credentials,
  process argv, hidden truth, scoring state, or sensitive concrete values
  through diagnostics, witnesses, manifests, snapshots, fixtures, or docs;
- letting most-specific-wins silently mask conflicting closures without an
  explicit diagnostic.

## Non-Goals

- Implementing the issue, publishing the formal envelope spec, publishing a new
  ADR, or changing checked-in schemas.
- Completing the issue's prior-art pass. Put that follow-on research under a
  dedicated `docs/research/realization-envelope/` note before the ADR/schema
  work lands.
- Changing runtime behavior, conformance behavior, backend manifests, or the
  #663 bridge in this preflight.
- Adding a new SDL dialect, new backend capability language, new experiment
  run-set model, solver dependency, HTTP API, persistence service, or backend
  adapter.
