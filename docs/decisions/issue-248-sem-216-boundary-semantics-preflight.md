# Issue 248 SEM-216 Boundary Semantics Preflight

Date: 2026-06-23

Issue: #248.

Requirement: SEM-216.

This note records architecture preflight guardrails for distinguishing
runtime-observable state, captured evidence, derived evaluations, analysis
outputs, and audience-specific views. It is implementation guidance only: it
does not add schemas, validators, runtime behavior, APIs, storage, or coverage
claims.

## Binding Sources

- ADR-016 and `docs/explain/reference/shared-semantic-integrity.md` define the
  SEM lifecycle model and list SEM-216 as planned coverage.
- ADR-054 defines runtime-observable participant lifecycle and observation
  boundaries.
- ADR-060 and `specs/formal/runtime-contracts/participant-backend-contracts.md`
  define participant carriers and retrieval projections.
- ADR-055, ADR-064, ADR-065, and `specs/formal/experiment-core/README.md`
  define experiment tasks, archival runs, capture specs, evidence records,
  derived measures, run traceability, and realized-form disclosures.
- ADR-009, ADR-019, ADR-061, `contracts/schema-publication-manifest.json`, and
  `.gc/plan-rules.md` define schema authority and publication governance.
- ADR-012 and ADR-062 define concept-authority, controlled-vocabulary, and
  extension discipline.
- ADR-021 defines falsification-first evidence expectations for architecture
  and maturity claims.

## Architecture Decisions

- Do not create a universal "state/evidence/result/view" super-schema. SEM-216
  is a boundary-semantics requirement over existing contract families.
- Runtime-observable state is live control-plane/runtime material:
  `RuntimeSnapshot`, snapshot entries, workflow/evaluation results and history,
  participant episode/behavior/shared-state/joint-action records, operation
  status, and audit metadata. It is operational and mutable until captured or
  sealed; it is not archival run provenance by itself.
- Captured evidence is the EXP-708 evidence surface:
  `experiment-evidence-record-v1`, run evidence artifacts, content URI plus
  checksum, bounded payload summary, sensitivity, redaction state, loss
  disclosure, and provenance. A capture spec declares intent; it is not proof
  that evidence exists.
- Derived evaluations and interpreted outputs are distinct from raw evidence.
  Live evaluator state uses compiled evaluation result/history contracts;
  archival interpreted measures use `experiment-derived-measure-v1`; run result
  summaries are compact run-local summaries, not the canonical derivation
  record when a first-class derived measure is needed.
- Analysis outputs are study/report/analysis artifacts or derived measures with
  `measure_kind: analysis-output`. Claim-bearing analysis must remain grounded
  through run traceability and at least one derived-measure reference; it must
  not float from raw runtime state or evaluator `detail`.
- Audience-specific views are projections over recorded carriers, not sources
  of truth. Reuse `participant-status-view-v1`,
  `participant-history-view-v1`, and `participant-context-view-v1` patterns:
  source refs, source layers, transformation refs, evidence/provenance refs,
  audience scope, visibility projection, markings, redaction policy,
  completeness, comparability, limitations, and optional payload refs.
- Cross-boundary movement must be by typed references, source layers,
  traceability blocks, checksums, and provenance refs. Do not copy backend
  payloads into `metadata`, `detail`, `details`, audit details, or view payloads
  to avoid modeling the boundary.

## Required Incumbents

- Runtime and backend boundary:
  `aces_contracts.runtime_state.RuntimeSnapshot`,
  `RuntimeSnapshotEnvelopeModel`, `ApplyResult`, `_call_backend_apply()`,
  `_snapshot_contract_diagnostics()`,
  `workflow_result_contract_diagnostics()`,
  `evaluation_result_contract_diagnostics()`,
  `participant_runtime_state_contract_diagnostics()`, and
  `participant_runtime_history_transition_diagnostics()`.
- Control-plane security, API, and persistence:
  `RuntimeControlPlane`, `ControlPlaneStore`, `ControlPlaneSecurityConfig`,
  `ControlPlaneIdentity`, `ControlPlaneRole`, request-size guards,
  idempotency keys, request fingerprints, audit events, response models, and
  redacted FastAPI 500 envelopes.
- View contracts and retrieval:
  `ParticipantStatusViewModel`, `ParticipantHistoryViewModel`,
  `ParticipantContextViewModel`, `ParticipantContextSourceLayerModel`,
  `ParticipantContextTransformationModel`,
  `ParticipantContextComparabilityModel`, and
  `aces_runtime.participant_retrieval`.
- Experiment contracts:
  `ExperimentCaptureSpecModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentRawEvidenceContentModel`, `ExperimentDerivedMeasureModel`,
  `ExperimentRunModel`, `ExperimentRunTraceabilityModel`,
  `ExperimentResultSummaryModel`, `ExperimentStudyModel`, constrained
  `ExperimentReferenceModel` subclasses, and
  `validate_experiment_run_against_task()`.
- Manifest/capability authority:
  `BackendManifestV2Model`, `ObservationCapabilitiesModel`,
  backend observation capability gap checks, supported-contract allowlists, and
  governed observation vocabulary scopes.
- Schema and concept authority:
  `ContractModel`, `schema_bundle()`, `tools/generate_contract_schemas.py`,
  `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/schema-publication-manifest.json`,
  `contracts/concept-authority/`, controlled-vocabulary validators, reference
  models, and semantic profiles.
- Verification:
  `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_schema_publication.py`, `tools/check_generated_schemas.py`,
  `tools/check_json_artifacts.py`, `tools/check_semantic_coverage.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL/config layer: if an implementation touches authoring or configuration,
  use the existing safe YAML parser, closed `SDLModel` shapes, variable-key
  rejection, `SemanticValidator`, and `instantiate_scenario()` revalidation.
  Do not infer boundary meaning from raw YAML strings.
- Contract shape layer: externally visible payloads must remain closed-world
  `ContractModel` descendants, generated/published JSON Schemas, fixtures, and
  semantic-invariant annotations. Schema changes must update the publication
  manifest and keep `schema_bundle()` byte-compatible with published schemas.
- Runtime adapter layer: backend-returned live state must fail closed through
  `_call_backend_apply()` and existing `runtime.backend-contract-invalid`
  diagnostics before entering snapshots or persistence.
- Evaluation layer: evaluator outputs must correspond to observable compiled
  evaluation entries and pass `EvaluationResultContract`,
  `EvaluationExecutionContract`, `EvaluationExecutionState`,
  `EvaluationHistoryEvent`, and `validate_evaluation_result()` semantics.
- Evidence and archival layer: evidence, derived measures, run traceability,
  and run summaries must pass the existing experiment model validators,
  timestamp parsing, reference constraints, reported-value rules, redaction/loss
  disclosure rules, and task/run cross-artifact validation.
- View layer: retrieval views must pass source binding, nested scope binding,
  completeness-basis, comparability, audience-scope, visibility-projection,
  marking, and redaction-policy validation. Views must not invent state absent
  from recorded carriers.
- Manifest/profile layer: observation capability, supported contract versions,
  concept bindings, controlled vocabulary scopes, and semantic-profile
  assumptions must resolve through existing authority helpers.
- API/auth layer: every future read or mutation surface must reuse
  control-plane authentication, backend/operator/auditor role checks,
  request-size limits, idempotency, request fingerprints, audit events, and
  redacted error envelopes.
- Persistence layer: live state remains in `ControlPlaneStore` plain-data
  envelopes; archival evidence/run/measure records require their own
  schema-versioned contract records when implemented. Do not use
  `RuntimeSnapshot.metadata`, operation records, participant histories, or audit
  details as archival storage.
- Error-envelope and OS exposure layer: diagnostics, HTTP errors, logs,
  fixtures, audit records, helper commands, and process argv must not expose
  credentials, bearer tokens, private keys, hidden truth, raw evidence payloads,
  environment dumps, backend-private object reprs, or full tracebacks.

## Extension Boundary

The extensibility seam is the existing set of typed references and governed
dimensions:

- `ParticipantContextSourceLayerModel.source_layer`, `audience_scope`,
  transformation refs, comparability refs, evidence refs, and provenance refs
  for view semantics;
- `ExperimentReferenceModel.ref_kind`, `ExperimentArtifactRefModel.role`,
  `ExperimentDerivedMeasureModel.measure_kind`, method metadata,
  `ExperimentRunTraceabilityModel`, and `ExperimentRealizedFormDisclosureModel`
  for experiment and analysis semantics;
- backend `capabilities.observation.supported_*` vocabularies for portable
  observation capability claims.

Future variation should parameterize producer source, seal point, content
locator/checksum policy, view audience, source layer, transformation, and
comparability basis through those fields. Add concept-authority or controlled
vocabulary terms only when portable comparison requires them; otherwise keep
backend- or study-specific details as refs, limitations, or method parameters.

## Gotchas And Anti-Patterns

Avoid:

- treating `RuntimeSnapshot`, operation status, workflow/evaluation history,
  participant history, or audit events as archival run provenance;
- treating capture specs as proof of capture;
- treating raw evidence records as metric values, scores, derived measures, or
  analysis outputs;
- treating derived measures, run result summaries, participant outcome reports,
  evaluator `detail`, or study analysis plans as interchangeable result blobs;
- treating views as sources of truth or letting a `payload_ref` hide a
  backend-native object model;
- exposing hidden world truth, centralized-training state, scoring state,
  private answer keys, prompts, credentials, or raw configuration in
  participant-visible or audience-specific views;
- adding duplicate schemas, reference models, validators, exception
  hierarchies, logging/audit paths, persistence stores, fixture loaders,
  manifest renderers, or workflow logic;
- hand-editing `contracts/schemas/` or skipping schema publication manifest
  updates when published schemas change;
- weakening accepted ADRs in place rather than using ADR-059 amendment or
  supersedure rules.

## Non-Goals

- Implementing SEM-216 behavior, schemas, validators, endpoints, storage,
  capture, analysis, or tests in this preflight note.
- Updating the SEM-200 coverage row or transitioning SEM-216 from DRAFT.
- Adding SDL authoring syntax, a new universal boundary taxonomy, a new
  archival provenance root, a new evidence store, a new view service, or a new
  analysis engine.
- Redesigning participant semantics, evaluator semantics, experiment-core
  contracts, backend manifests, control-plane security, schema authority, or
  concept authority.
- Publishing secrets, hidden truth, backend-private payloads, raw evidence, or
  raw process/environment state as portable contract data.
