# Issue 336 DSL-123 Scenario-Native Observability Preflight

Date: 2026-06-24

Issue: #336.

Requirement: DSL-123.

This note records architecture preflight guardrails for implementing
scenario-native observability, telemetry, logging, tracing, monitoring, and
comparable in-world data systems. It is implementation guidance only: it does
not add SDL syntax, schemas, validators, runtime behavior, APIs, storage,
fixtures, tests, or coverage claims.

## Binding Sources

- ADR-066 is the semantic authority for observability/evidence plane
  separation.
- `specs/formal/observability-evidence-plane.md` defines the DSL-123 matrix
  rows and negative probes.
- `specs/sdl/observability-and-evidence.md` defines the SDL authoring rules for
  scenario-native observability systems.
- `docs/decisions/issue-334-sem-224-observability-plane-preflight.md` and
  `aces_sdl.observability_plane_semantics` define the carrier-oriented plane
  classifier that DSL-123 must extend rather than replace.
- `specs/sdl/runtime-inventory.md`, `specs/sdl/sections.md`, and
  `specs/sdl/references.md` define the runtime-family, top-level-section, and
  reference-resolution extension boundaries.
- ADR-022 and ADR-054 define participant-visible observation projection,
  markings, redaction, loss, and information guarantees.
- ADR-055, ADR-064, and ADR-065 define experiment-core task, capture, raw
  evidence, derived measure, run traceability, realized-form, and augmentation
  carriers.
- ADR-036 defines package ownership: SDL language logic belongs in `aces_sdl`,
  runtime live control belongs in `aces_runtime`, and neutral boundary DTOs
  belong in `aces_contracts`.
- ADR-056 and ADR-057 define redaction behavior for observed runtime values and
  the boundary between scenario values and operator secrets.
- ADR-009, ADR-019, ADR-061, ADR-062,
  `contracts/schema-publication-manifest.json`, and `.gc/plan-rules.md` define
  schema authority, publication governance, concept authority, and workflow
  gates.

## Architecture Decisions

- DSL-123 is an SDL authoring and reference-targeting requirement. First-class
  means stable SDL identity plus typed or qualified references; it does not mean
  a generic top-level `observability` bag.
- Node-scoped observability systems must use the existing
  `nodes.<node>.runtime.<collection>` runtime-family model when the service is
  logical runtime state.
- Reuse current runtime families when they fit the product-neutral service
  identity: `network_sensors`, `network_detection_engines`,
  `security_monitoring_managers`, `forwarding_agents`, `service_listeners`,
  `platform_applications`, and `datastore_services`.
- Add a new runtime family only when the modeled system has a distinct
  product-neutral logical service identity that cannot fit an existing family
  without changing that family's meaning.
- Targeting and interaction must route through fail-closed references:
  qualified runtime-family refs from `collect_qualified_runtime_family_refs()`,
  existing objective `target` resolution, and typed relationship subtypes. Bare
  ambiguous refs must never resolve by first match.
- Plane ownership remains carrier-oriented. If DSL-123 adds or reclassifies a
  scenario-native family, update `SCENARIO_NATIVE_OBSERVABILITY_FAMILIES` and
  its validation against `RUNTIME_SERVICE_FAMILIES`; do not infer from words
  such as `log`, `trace`, `telemetry`, `monitoring`, or `evidence`.
- A scenario-native observability system may be an evidence source, a
  relationship endpoint, an objective/action target, or an affected asset. Its
  existence is not an authored evidence requirement, proof of capture, raw
  evidence, derived analysis, or backend operational telemetry.
- Processor/backend logs, traces, health checks, and diagnostics stay in the
  processor/backend operational plane unless projected through an existing SDL,
  participant-runtime, apparatus, evidence, or run-provenance carrier.
- Participant-visible dashboards, alerts, logs, traces, or monitoring outputs
  must pass participant visibility projection, markings, redaction, loss, and
  authorization gates. They must not be exposed by raw backend DTOs, stack
  traces, diagnostics, or `RuntimeSnapshot.metadata`.

## Required Incumbents

- SDL parser/model closure: `parse_sdl()`, `parse_sdl_file()`, `SDLModel`,
  `_HASHMAP_SECTIONS`, variable-key rejection, `SemanticValidator`,
  `instantiate_scenario()`, and post-instantiation semantic revalidation.
- Runtime-family registry and refs: `RuntimeConfiguration`,
  `RUNTIME_SERVICE_FAMILIES`, `RuntimeServiceFamily`,
  `RuntimeReferenceChild`, `collect_qualified_runtime_family_refs()`,
  `nested_node_runtime_family_aliases()`, and family-specific validators.
- Runtime-family docs and catalogs: `specs/sdl/runtime-inventory.md`,
  `specs/sdl/references.md`, `specs/sdl/sections.md`, and
  `specs/sdl/diagnostics.md`.
- Plane classifier: `ObservabilityEvidencePlane`,
  `SCENARIO_NATIVE_OBSERVABILITY_FAMILIES`, `classify_runtime_family()`,
  `classify_contract_plane()`, and `token_decides_plane()`.
- Existing runtime families likely to carry DSL-123 use cases:
  network sensors, network detection engines, security monitoring managers,
  forwarding agents, service listeners, platform applications, and datastore
  services.
- Experiment-core boundaries: `ExperimentReferenceModel`,
  `ExperimentCaptureSpecModel`, `ExperimentCaptureRequirementModel`,
  `ExperimentEvidenceRecordModel`, `ExperimentDerivedMeasureModel`,
  `ExperimentRunTraceabilityModel`, `ExperimentAugmentationDisclosureModel`,
  `ExperimentRunModel`, and `validate_experiment_run_against_task()`.
- Participant-visible contracts: `ParticipantObservationEnvelopeModel`,
  `ParticipantContextViewModel`, `ParticipantHistoryViewModel`,
  `ParticipantStatusViewModel`, source-layer, transformation, marking,
  redaction, loss, and comparability validators.
- Apparatus/control-plane surfaces: `BackendManifestV2Model`,
  `ProcessorManifestV2Model`, `ExperimentApparatusContextModel`,
  `Diagnostic`, `Severity`, `RuntimeSnapshot`, `OperationReceipt`,
  `OperationStatus`, `ControlPlaneSecurityConfig`, `ControlPlaneIdentity`,
  `ControlPlaneRole`, `ControlPlaneStore`, audit events, request-size guards,
  idempotency keys, request fingerprints, response models, and redacted FastAPI
  500 envelopes.
- Schema and concept authority: `ContractModel`, `schema_bundle()`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/schema-publication-manifest.json`, concept-authority catalogs, and
  controlled-vocabulary validators.

## Cross-Cutting Layers

- SDL/config layer: authored observability elements must pass safe YAML loading,
  normalized field keys, closed `SDLModel` shapes, symbol-key variable
  rejection, semantic validation, and instantiated revalidation. New fields must
  be represented in `sections.md`, `references.md`, published SDL schemas, and
  the reference implementation together.
- Runtime-family layer: node-scoped systems must have stable `<noun>_id`
  identity, duplicate-id rejection, registered child-ref metadata, and
  family-local semantic validators. A new family must register once in
  `RUNTIME_SERVICE_FAMILIES`; no second registry is allowed.
- Reference layer: objective targets, relationship endpoints, evidence sources,
  and child records must resolve fail-closed through the existing reference
  catalog and validator. Ambiguous or dangling refs are fatal.
- Plane-classifier layer: scenario-native observability families must be
  registered data, not token-matched strings. Any family change must keep
  `classify_runtime_family()` and the SEM-224 tests fail-closed.
- Contract shape layer: any external payload must remain a closed
  `ContractModel` descendant with `schema_bundle()` parity. Published schema
  changes require fixtures and a `contracts/schema-publication-manifest.json`
  last-change ledger entry.
- Experiment-core layer: capture intent, raw evidence, derived measures, run
  traceability, and augmentation disclosures must use existing experiment-core
  carriers. Observability elements can be referenced by those carriers, but
  must not replace them.
- Participant visibility layer: any participant-visible observability output
  must route through participant observation/context/history/status contracts
  with source layer, transformation, marking, redaction, loss, and comparability
  metadata.
- Apparatus/control-plane layer: backend operational telemetry remains
  apparatus data unless explicitly projected. HTTP exposure must reuse
  authentication, role checks, request-size limits, idempotency, request
  fingerprints, audit events, response models, and redacted error envelopes.
- Persistence layer: live operational state remains in `RuntimeSnapshot` and
  `ControlPlaneStore` envelopes. Portable scenario meaning, evidence, analysis,
  and augmentation claims must not live only in `RuntimeSnapshot.metadata`,
  operation details, audit blobs, backend DTOs, raw logs, or free-form tags.
- Secret and OS-exposure layer: runtime fields, examples, diagnostics, logs,
  audit details, fixtures, command examples, process argv, environment captures,
  and backend inspect payloads must not expose bearer tokens, private keys,
  operator secrets, hidden truth, raw trace payloads, raw evidence payloads,
  full stack traces, or backend-private object representations.
- Policy layer: implementation must satisfy Ground Control policy checks,
  module-boundary policy, concept-authority governance, generated-schema
  parity, schema-publication governance, semantic coverage, and requirement
  traceability.

## Extension Boundary

The extensibility seam is runtime-family identity plus typed references:

- runtime family key, collection name, primary id field, and child-ref tree
  identify targetable scenario-native observability assets;
- existing objective `target`, typed relationship refs, experiment
  `ExperimentReferenceModel.ref_kind`, capture channel refs, evidence-record
  refs, derived-measure refs, and run traceability express cross-plane links;
- participant source layers, transformations, audience scope, markings,
  redaction policy, evidence refs, provenance refs, and comparability refs
  express any participant-visible projection;
- concept-authority or controlled-vocabulary terms belong only where portable
  comparison needs a shared term, not where a family-local enum is enough.

Future telemetry, logging, tracing, metrics, or dashboard variants should be
parameterized as product-neutral runtime-family fields or children such as
source refs, output streams, control channels, collection windows, channels,
formats, transports, markings, loss/redaction expectations, and comparability
basis. Do not hard-code a vendor, protocol, or backend adapter as the DSL
concept boundary.

## Gotchas And Anti-Patterns

Avoid:

- adding a top-level `observability`, `telemetry`, `logs`, or `traces` bag;
- adding a second runtime-family registry, target resolver, or plane classifier;
- deciding plane ownership from string tokens instead of carrier role and
  registered runtime family;
- resolving ambiguous observability targets by first match;
- using backend logs, traces, health checks, diagnostics, audit records, stack
  traces, process argv, or environment dumps as participant observations or
  authored scenario meaning;
- treating an observability system declaration as an authored evidence
  requirement or proof that capture occurred;
- duplicating experiment-core capture, evidence-record, derived-measure, run,
  apparatus-context, or augmentation schemas;
- storing portable meaning only in metadata, diagnostic details, audit blobs,
  backend-native DTOs, raw logs, or free-form tags;
- leaking hidden truth, answer keys, evaluator state, prompts, private traces,
  bearer tokens, credentials, or operator secrets through SDL, contracts,
  fixtures, generated schemas, diagnostics, logs, audit details, or examples;
- weakening accepted ADRs in place instead of following ADR-059 amendment or
  supersedure rules.

## Non-Goals

- Implementing DSL-123 behavior, SDL syntax, schemas, validators, compiler
  addresses, endpoints, storage, telemetry collection, log parsing, trace
  collection, fixtures, or tests in this preflight note.
- Updating DSL-123 status or claiming implementation coverage.
- Implementing DSL-124 authored evidence requirements, evidence capture
  scheduling, raw evidence records, derived analysis, or run-level satisfaction
  logic.
- Implementing SEM-225 augmentation behavior beyond preserving the disclosure
  boundary that DSL-123 must not bypass.
- Replacing participant visibility semantics, experiment-core contracts,
  runtime-family schemas, control-plane security, schema authority, concept
  authority, diagnostics, audit, persistence, or workflow policy.
