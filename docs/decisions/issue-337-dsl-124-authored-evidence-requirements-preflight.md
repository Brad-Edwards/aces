# Issue 337 DSL-124 Authored Evidence Requirements Preflight

Date: 2026-06-24

Issue: #337.

Requirement: DSL-124.

This note records architecture preflight guardrails for implementing authored
requirements for data, evidence, and output capture. It is implementation
guidance only: it does not add SDL syntax, schemas, validators, runtime
behavior, APIs, storage, fixtures, tests, or coverage claims.

## Binding Sources

- ADR-066 is the semantic authority for observability/evidence plane
  separation.
- `specs/formal/observability-evidence-plane.md` defines the DSL-124 matrix
  rows and negative probes.
- `specs/sdl/observability-and-evidence.md` defines the SDL authoring rules for
  authored evidence requirements.
- `docs/decisions/issue-334-sem-224-observability-plane-preflight.md` and
  `aces_sdl.observability_plane_semantics` define the carrier-oriented plane
  classifier that DSL-124 must extend rather than replace.
- `docs/decisions/issue-336-dsl-123-scenario-native-observability-preflight.md`
  defines the adjacent scenario-native observability source boundary.
- `specs/sdl/sections.md`, `specs/sdl/references.md`, and
  `specs/sdl/runtime-inventory.md` define the section, reference-resolution,
  and runtime-family extension boundaries.
- ADR-022 and ADR-054 define participant-visible observation projection,
  markings, redaction, loss, and information guarantees.
- ADR-055, ADR-064, and ADR-065 define experiment-core task, capture, raw
  evidence, derived measure, run traceability, realized-form, and augmentation
  carriers.
- ADR-036 defines package ownership: SDL language logic belongs in `aces_sdl`,
  runtime live control belongs in `aces_runtime`, and neutral boundary DTOs
  belong in `aces_contracts`.
- ADR-056 and ADR-057 define observed-value and secret-handling boundaries.
- ADR-009, ADR-019, ADR-061, ADR-062,
  `contracts/schema-publication-manifest.json`, and `.gc/plan-rules.md` define
  schema authority, publication governance, concept authority, and workflow
  gates.

## Architecture Decisions

- DSL-124 is an SDL authoring requirement. It records a capture obligation, not
  proof that capture occurred and not a raw captured payload.
- The authored requirement plane maps to `experiment-capture-spec-v1` concepts
  when executable capture contracts are generated. It must not duplicate
  `ExperimentCaptureSpecModel`, `ExperimentCaptureRequirementModel`, or their
  validators.
- Authored evidence requirements must stay independent of participant
  objectives, metrics, evaluations, TLOs, goals, participant observation
  envelopes, and outcome reports. A participant objective can reference the
  same scenario target, but it must not imply a capture obligation.
- A scenario-native observability system may be a source for an authored
  evidence requirement. Its existence does not satisfy the requirement and does
  not prove that evidence was captured.
- The carrier decides plane ownership. Do not classify a requirement by words
  such as `log`, `trace`, `telemetry`, `observation`, `output`, or `evidence`.
- Source, scope, window, channel, boundary, sensitivity, integrity, retention,
  and loss-disclosure dimensions must be explicit. Missing or ambiguous
  dimensions should fail closed in semantic validation.
- Captured evidence belongs to `experiment-evidence-record-v1`. Derived
  analysis belongs to `experiment-derived-measure-v1`. Run-level provenance,
  realized-form, and augmentation links belong to `experiment-run-v1`.
- Processor/backend operational telemetry may support an authored requirement
  only after projection through existing manifests, apparatus context,
  diagnostics, capture specs, evidence records, run traceability, or
  augmentation disclosures.
- If a later API publishes or retrieves authored requirements or generated
  capture specs, it must reuse the existing control-plane auth, request-size,
  idempotency, audit, closed DTO, and redacted-error patterns.

## Required Incumbents

- SDL parser/model closure: `parse_sdl()`, `parse_sdl_file()`, `SDLModel`,
  `_HASHMAP_SECTIONS`, variable-key rejection, `SemanticValidator`,
  `SDLValidationError`, `instantiate_scenario()`, and post-instantiation
  semantic revalidation.
- SDL catalogs: `specs/sdl/sections.md`, `specs/sdl/references.md`,
  `specs/sdl/runtime-inventory.md`, and
  `specs/sdl/observability-and-evidence.md`.
- Reference resolution: `SemanticValidator._named_ref_index()`,
  `_validate_named_ref()`, `collect_qualified_runtime_family_refs()`,
  `collect_scenario_native_observability_refs()`, and the fail-closed
  ambiguity semantics in `references.md`.
- Plane classifier: `ObservabilityEvidencePlane`,
  `classify_contract_plane()`, `classify_runtime_family()`,
  `assert_single_primary_plane()`, `token_decides_plane()`,
  `PLANE_BY_CONTRACT_ID`, and `SCENARIO_NATIVE_OBSERVABILITY_FAMILIES`.
- Experiment capture intent: `ExperimentReferenceModel`,
  `ExperimentCaptureSpecModel`, `ExperimentCaptureRequirementModel`,
  `ExperimentCaptureWindowModel`,
  `ExperimentMeasurementChannelReferenceModel`, `ExperimentArtifactRefModel`,
  `ExperimentChecksumModel`, and `schema_bundle()`.
- Adjacent experiment carriers: `ExperimentEvidenceRecordModel`,
  `ExperimentDerivedMeasureModel`, `ExperimentRunTraceabilityModel`,
  `ExperimentRealizedFormDisclosureModel`,
  `ExperimentAugmentationDisclosureModel`, `ExperimentRunModel`, and
  `validate_experiment_run_against_task()`.
- Backend capability authority: `ObservationCapabilitiesModel`,
  `ObservationCapabilities`, `OBSERVATION_CAPABILITY_REQUIRED_CONTRACTS`,
  `BACKEND_SUPPORTED_CONTRACT_IDS`, `backend_manifest_payload()`,
  `observation_capability_contract_gaps()`, and governed observation
  vocabulary scopes.
- Participant-visible contracts: `ParticipantObservationEnvelopeModel`,
  `ParticipantContextViewModel`, `ParticipantHistoryViewModel`,
  `ParticipantStatusViewModel`, source-layer, transformation, marking,
  redaction, loss, and comparability validators.
- Runtime/API surfaces for future exposure: `ControlPlaneSecurityConfig`,
  `ControlPlaneIdentity`, `ControlPlaneRole`, `ControlPlaneStore`,
  `Diagnostic`, `Severity`, request-size guards, request fingerprints,
  idempotency keys, audit events, response models, and redacted FastAPI 500
  envelopes.
- Schema and concept authority: `ContractModel`, `schema_bundle()`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/schema-publication-manifest.json`, concept-authority catalogs, and
  controlled-vocabulary validators.

## Cross-Cutting Layers

- SDL/config layer: authored evidence fields must pass safe YAML loading,
  normalized field keys, closed `SDLModel` shapes, symbol-key variable
  rejection, semantic validation, and instantiated revalidation. New top-level
  fields must be represented in `sections.md`, `references.md`, published SDL
  schemas, and the reference implementation together.
- Reference layer: source, scope, trigger, window, channel, participant,
  apparatus, processor/backend, and scenario-native observability refs must
  resolve through existing fail-closed reference machinery. Ambiguous bare refs
  must require qualified refs; dangling refs are fatal.
- Plane-classifier layer: authored evidence requirements must register as the
  authored-evidence-requirement plane by carrier role, not token matching. Any
  new carrier must extend `PLANE_BY_CONTRACT_ID` or the SDL-side classifier
  seam deliberately.
- Experiment-core layer: generated or exported capture intent must use
  `experiment-capture-spec-v1` with existing key equality, window resolution,
  timestamp, sensitivity, integrity, retention, and loss-disclosure validators.
- Participant visibility layer: any participant-visible output, dashboard,
  alert, log, or evidence disclosure must route through participant
  observation/context/history/status contracts with source layer,
  transformation, marking, redaction, loss, and comparability metadata.
- Apparatus/control-plane layer: backend logs, health checks, diagnostics,
  traces, setup evidence, and measurement channels remain operational until a
  governed projection maps them into capture specs, evidence records, run
  traceability, apparatus context, or participant-visible contracts.
- Secret-handling layer: authored requirements, generated capture specs,
  diagnostics, audit details, fixtures, and examples must not carry bearer
  tokens, private keys, credentials, hidden truth, prompts, raw trace payloads,
  raw evidence payloads, environment dumps, process argv, or full tracebacks.
  Use existing sensitivity/redaction fields and observed-value helpers.
- Config/env-binding layer: DSL-124 must not introduce a new environment,
  config, or secret-binding shape. Runtime configuration and experiment
  parameters must use the existing redaction-aware models.
- OS-exposure layer: CLI examples, tools, and future producers must not pass
  secrets, tokens, backend-private payloads, or large raw capture payloads
  through command-line arguments. Use synthetic fixtures, content refs, URIs,
  and checksums.
- Error-envelope layer: parser and semantic failures use `SDLParseError` and
  `SDLValidationError`; runtime and HTTP failures use existing `Diagnostic`
  values or the redacted FastAPI error envelope. Error text must not echo
  captured payloads, secrets, tracebacks, or backend internals.
- Persistence layer: authored requirements are portable SDL/capture-intent
  data, not live runtime state. Do not store them only in
  `RuntimeSnapshot.metadata`, operation records, participant histories, audit
  blobs, backend DTOs, raw logs, or free-form tags.
- Policy layer: implementation must satisfy Ground Control policy checks,
  module-boundary policy, concept-authority governance, generated-schema
  parity, schema-publication governance, semantic coverage, and requirement
  traceability.

## Extension Boundary

The extensibility seam is declared capture dimensions plus typed references:

- requirement identity and title;
- source refs and source class;
- scope refs and capture scope;
- capture window, trigger, or comparable boundary;
- channel or modality reference;
- expected media types and artifact roles;
- sensitivity, redaction policy, integrity requirements, retention policy, and
  loss-disclosure expectation;
- optional binding to `ExperimentCaptureSpecModel` and
  `ExperimentCaptureRequirementModel`; and
- optional source refs to scenario-native observability runtime-family paths.

Future output kinds, telemetry/log/trace variants, evidence channels,
retention modes, or sealing modes should be parameterized through those fields
and governed vocabularies. Add concept-authority or controlled-vocabulary terms
only when portable comparison or capability claims need bounded shared terms.

## Gotchas And Anti-Patterns

Avoid:

- adding a generic top-level `observability`, `telemetry`, `logs`, `evidence`,
  or `outputs` bag;
- adding a second evidence-requirement schema, parser, registry, validator,
  reference resolver, exception hierarchy, logging stack, audit stack,
  persistence store, fixture loader, manifest renderer, or workflow pipeline;
- classifying plane ownership by string labels instead of carrier role and
  resolved refs;
- treating objectives, metrics, evaluations, TLOs, goals, participant
  observation boundaries, or outcome reports as implicit capture requirements;
- treating a scenario-native observability declaration, capture spec, backend
  capability claim, backend log, audit event, or run traceability ref as proof
  that evidence was captured;
- collapsing authored requirements, capture specs, raw evidence records,
  derived measures, run result summaries, realized-form disclosures, and
  augmentation disclosures into one blob;
- resolving ambiguous sources, scopes, or runtime-family refs by first match;
- storing portable meaning only in metadata, diagnostics, audit details,
  backend-native DTOs, raw logs, or free-form tags;
- leaking hidden truth, answer keys, evaluator state, prompts, private traces,
  bearer tokens, credentials, operator secrets, environment dumps, process
  argv, full tracebacks, or raw captured payloads through SDL, schemas,
  fixtures, diagnostics, audit records, logs, or examples;
- hand-editing published schemas without updating contract source,
  `schema_bundle()` parity, fixtures, and the schema publication manifest.

## Non-Goals

- Implementing DSL-124 behavior, SDL syntax, schemas, validators, compiler
  addresses, endpoints, storage, generated capture specs, fixtures, or tests in
  this preflight note.
- Updating DSL-124 status or claiming implementation coverage.
- Implementing runtime evidence capture, packet/log/trace collection,
  retention, sealing, retrieval, redaction execution, schedulers, workers, or
  background capture orchestration.
- Implementing raw evidence records, derived measures, run-level satisfaction
  logic, analysis engines, evaluator behavior, score calculation, or study
  comparison logic.
- Replacing DSL-123 scenario-native observability surfaces, participant
  visibility semantics, experiment-core contracts, runtime-family schemas,
  control-plane security, schema authority, concept authority, diagnostics,
  audit, persistence, or workflow policy.
