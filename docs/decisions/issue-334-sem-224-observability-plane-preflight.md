# Issue 334 SEM-224 Observability Plane Preflight

Date: 2026-06-23

Issue: #334.

Requirement: SEM-224.

This note records architecture preflight guardrails for implementing
observability plane separation semantics. It is implementation guidance only:
it does not add SDL syntax, schemas, validators, runtime behavior, APIs,
storage, fixtures, tests, or coverage claims.

## Binding Sources

- ADR-066 is the semantic authority for the five observability/evidence planes
  and the augmentation classification boundary.
- `specs/formal/observability-evidence-plane.md` defines the invariant set,
  source-to-contract-to-test matrix, and negative probe set for SEM-224.
- `specs/sdl/observability-and-evidence.md` defines SDL authoring rules for
  scenario-native observability systems and authored evidence requirements.
- ADR-022 and ADR-054 define participant-visible observations, visibility
  projection, markings, redaction, loss, and information guarantees.
- ADR-055, ADR-064, and ADR-065 define experiment tasks, capture specs, raw
  evidence records, derived measures, apparatus context, run traceability, and
  realized-form disclosures.
- ADR-036 defines package ownership: SDL language logic belongs in
  `aces_sdl`, runtime live control belongs in `aces_runtime`, and neutral
  boundary DTOs belong in `aces_contracts`.
- ADR-056 and ADR-057 define explicit-redaction behavior for runtime observed
  values and keep scenario credentials distinct from operator secrets.
- ADR-009, ADR-019, ADR-061, `contracts/schema-publication-manifest.json`, and
  `.gc/plan-rules.md` define schema authority and publication governance.
- ADR-012 and ADR-062 define concept-authority, controlled-vocabulary, and
  extension discipline.

## Architecture Decisions

- SEM-224 is a plane-classification and boundary-validation requirement over
  existing carriers. Do not create a generic top-level `observability` model,
  a universal evidence super-schema, or a second runtime telemetry hierarchy.
- A claim-bearing artifact has one primary plane by carrier and contract role,
  not by words such as `log`, `trace`, `telemetry`, `observation`, or
  `evidence`.
- Scenario-native observability stays in SDL authoring space. Node-scoped
  logical services must use the existing `nodes.<node>.runtime.*`
  runtime-family registry and reference model when a current family fits.
- Authored evidence requirements are declarative obligations. They may bind to
  `experiment-capture-spec-v1`, but they are not raw evidence, not participant
  objectives, and not proof that capture occurred.
- Processor/backend operational observability is apparatus data. It may support
  audit, setup evidence, or capability claims only after it is projected
  through existing manifest, diagnostics, control-plane, apparatus-context, or
  evidence contracts.
- Captured evidence is raw evidence material or an
  `experiment-evidence-record-v1` record. It must not carry metric values,
  scores, or interpreted conclusions.
- Derived analysis is interpreted output over evidence. It must cite source
  evidence and must not disclose hidden truth, prompts, private traces,
  answer keys, secrets, or adjudication assets without governed marking,
  redaction, and authorization.
- The classifier seam should be data-only and carrier-oriented. It may accept
  an extensible carrier kind or contract id plus optional source-layer/ref-kind
  parameters, but it must not import runtime internals, inspect backend-native
  DTOs, or infer plane ownership from arbitrary strings.
- Any executable validation must compose with existing validators: SDL semantic
  validation for authored surfaces, Pydantic contract validators for external
  contracts, runtime adapter diagnostics for backend-returned state, and
  control-plane API guards for HTTP exposure.

## Required Incumbents

- SDL authoring and semantic validation:
  `SDLModel`, `parse_sdl()`, `parse_sdl_file()`, `_HASHMAP_SECTIONS`,
  variable-key rejection, `SemanticValidator`, `instantiate_scenario()` full
  revalidation, `specs/sdl/sections.md`, `specs/sdl/references.md`, and
  `specs/sdl/runtime-inventory.md`.
- Scenario-native runtime families:
  `RuntimeConfiguration`, `RUNTIME_SERVICE_FAMILIES`,
  `RuntimeServiceFamily`, `collect_qualified_runtime_family_refs()`, and
  current families such as network sensors, network detection engines,
  security monitoring managers, forwarding agents, service listeners,
  platform applications, and datastore services.
- Experiment evidence and analysis contracts:
  `ExperimentReferenceModel` and constrained subclasses,
  `ExperimentCaptureSpecModel`, `ExperimentCaptureRequirementModel`,
  `ExperimentCaptureWindowModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentRawEvidenceContentModel`, `ExperimentDerivedMeasureModel`,
  `ExperimentRunTraceabilityModel`, `ExperimentRealizedFormDisclosureModel`,
  `ExperimentRunModel`, `ExperimentStudyModel`, and
  `validate_experiment_run_against_task()`.
- Participant-visible observation and audience-view contracts:
  `ParticipantObservationEnvelopeModel`,
  `ParticipantContextViewModel`, `ParticipantHistoryViewModel`,
  `ParticipantStatusViewModel`, participant runtime base-envelope fields,
  visibility projection, source-layer, transformation, marking, redaction, and
  comparability validation.
- Apparatus and operational observability:
  `BackendManifestV2Model`, `ProcessorManifestV2Model`,
  backend observation capabilities, `ExperimentApparatusContextModel`,
  selected manifest validation, `Diagnostic`, `Severity`,
  `RuntimeSnapshot`, `OperationReceipt`, `OperationStatus`, and audit records.
- Control-plane security and exposure:
  `ControlPlaneSecurityConfig`, `ControlPlaneIdentity`, `ControlPlaneRole`,
  bearer/proxy authentication, backend/operator/auditor role gates,
  request-size guards, idempotency keys, request fingerprints, audit events,
  response models, and redacted FastAPI 500 envelopes.
- Schema and concept authority:
  `ContractModel`, `schema_bundle()`, `tools/generate_contract_schemas.py`,
  `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/schema-publication-manifest.json`,
  `contracts/concept-authority/`, controlled-vocabulary validators, reference
  models, semantic profiles, and `tools/check_generated_schemas.py`.
- Repo workflow and policy:
  `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_schema_publication.py`, `tools/check_json_artifacts.py`,
  `tools/check_semantic_coverage.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL/config layer: new authoring claims must pass safe YAML loading, closed
  `SDLModel` shapes, normalized keys, symbol-key variable rejection, semantic
  reference resolution, and post-instantiation revalidation. A plane decision
  must come from the carrier and resolved refs, not from raw YAML text.
- Runtime-family layer: scenario-native observability must use registered
  runtime families, stable ids, same-node service refs, child-ref catalogs, and
  family-specific validators. Add a new family only with an owning ADR,
  `runtime-inventory.md` row, schema/model updates, validators, fixtures, and
  tests.
- Contract shape layer: external payloads must remain closed-world
  `ContractModel` descendants with generated/published JSON Schemas. Published
  schema changes require `schema_bundle()` parity, fixtures, and a
  `contracts/schema-publication-manifest.json` last-change ledger entry.
- Experiment-core layer: capture intent, raw evidence, derived measures, run
  traceability, realized-form disclosure, and studies must pass the existing
  experiment model validators, timestamp parsing, reference constraints,
  reported-value rules, redaction/loss disclosure rules, and task/run
  cross-artifact validation.
- Participant visibility layer: any participant-visible projection must pass
  ADR-022/ADR-054 observation-envelope and audience-view rules for source
  layer, transformation, visibility, marking, redaction policy, delivery basis,
  information guarantee, loss, and comparability.
- Apparatus/control-plane layer: backend logs, traces, health, setup evidence,
  and diagnostics remain operational until projected through manifests,
  apparatus context, diagnostics, evidence records, or run traceability.
  Control-plane exposure must reuse auth, role checks, request-size limits,
  idempotency, request fingerprints, audit events, response models, and
  redacted error envelopes.
- Persistence layer: live state remains in `RuntimeSnapshot` and
  `ControlPlaneStore` envelopes. Archival evidence/run/measure artifacts must
  use their schema-versioned contracts. Do not use `RuntimeSnapshot.metadata`,
  operation details, audit blobs, backend DTOs, or raw logs as portable plane
  carriers.
- Error-envelope and OS exposure layer: diagnostics, HTTP errors, audit
  records, logs, fixtures, process argv, and helper command examples must not
  expose bearer tokens, private keys, operator secrets, hidden truth, raw
  evidence payloads, environment dumps, backend-private object reprs, or full
  tracebacks.
- Policy layer: implementation must satisfy Ground Control policy checks,
  module-boundary policy, concept-authority governance, generated-schema parity,
  schema-publication governance, semantic coverage, and requirement
  traceability. Do not add authority-bearing artifacts outside approved roots.

## Extension Boundary

The extensibility seam is a carrier-oriented plane classifier plus existing
typed references:

- carrier or contract id identifies the primary plane;
- `ExperimentReferenceModel.ref_kind`, capture requirement ids, measurement
  channel refs, evidence-record refs, derived-measure refs, and run
  traceability express cross-plane links;
- `ParticipantContextSourceLayerModel.source_layer`, transformation refs,
  evidence refs, provenance refs, audience scope, and comparability refs
  express audience-view projections;
- `RUNTIME_SERVICE_FAMILIES` and child-ref metadata express
  scenario-native observability targets;
- backend observation capability vocabularies express apparatus support
  claims.

Future variation should parameterize carrier kind, source ref, capture window,
channel, source layer, audience, transformation, evidence ref, provenance ref,
redaction/loss expectation, and comparability basis through those existing
fields. Add concept-authority or controlled-vocabulary terms only when portable
comparison requires them.

## Gotchas And Anti-Patterns

Avoid:

- classifying planes by string labels instead of carrier type and resolved
  contract role;
- treating backend logs, traces, health checks, audit records, or stack traces
  as participant observations or authored scenario meaning;
- treating a capture spec or authored evidence requirement as proof of capture;
- treating a scenario-native observability system as satisfying an evidence
  requirement merely because it exists;
- putting evidence, analysis, augmentation, or comparability semantics only in
  `metadata`, `details`, diagnostics, audit blobs, backend-native DTOs, raw
  logs, or free-form tags;
- mixing raw evidence with metric values, scores, evaluator decisions, result
  summaries, or claims;
- leaking hidden adjudication assets, prompts, answer keys, private traces,
  operator secrets, or backend-private ids through participant-visible
  observations or public analysis outputs;
- duplicating schemas, validation helpers, exception hierarchies, logging/audit
  paths, persistence stores, fixture loaders, manifest renderers, concept
  vocabularies, or workflow logic;
- bypassing `contracts/schema-publication-manifest.json` or hand-editing
  published schemas without reference-implementation parity;
- weakening accepted ADRs in place instead of following ADR-059 amendment or
  supersedure rules.

## Non-Goals

- Implementing SEM-224 behavior, schemas, validators, endpoints, storage,
  capture scheduling, telemetry collection, analysis engines, fixtures, or
  tests in this preflight note.
- Updating SEM-224 status or claiming implementation coverage.
- Adding SDL syntax for DSL-123 or DSL-124, which belong to their own
  implementation issues.
- Implementing SEM-225 augmentation carriers or validators beyond preserving
  the boundary needed for SEM-224.
- Creating a generic observability bag, a universal evidence taxonomy, a new
  archival provenance root, a new backend telemetry API, or a new persistence
  store.
- Redesigning participant semantics, experiment-core contracts,
  runtime-family schemas, control-plane security, schema authority, or concept
  authority.
