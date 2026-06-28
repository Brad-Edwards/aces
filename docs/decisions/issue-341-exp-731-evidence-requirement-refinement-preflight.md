# Issue 341 EXP-731 Evidence Requirement Refinement Preflight

Date: 2026-06-28

Issue: #341.

Requirement: EXP-731.

This note records architecture preflight guardrails for supporting task-, run-,
or study-level refinement and extension of authored data and evidence
requirements without silently rewriting authored scenario meaning. It is
implementation guidance only: it does not add schemas, validators, SDL syntax,
runtime behavior, APIs, storage, fixtures, tests, or coverage claims.

## Binding Sources

- ADR-066 is the semantic authority for observability/evidence plane
  separation.
- `docs/decisions/issue-337-dsl-124-authored-evidence-requirements-preflight.md`
  is the base authored evidence-requirement guardrail.
- `specs/sdl/observability-and-evidence.md`,
  `specs/sdl/references.md`, and `specs/sdl/sections.md` define the SDL
  authoring, reference-resolution, and section boundaries.
- ADR-055, ADR-064, and ADR-065 define experiment task, capture spec, evidence
  record, derived measure, run traceability, realized-form, augmentation, and
  study boundaries.
- ADR-012, ADR-061, ADR-062, ADR-009, `contracts/schema-publication-manifest.json`,
  and `.gc/plan-rules.md` define concept authority, schema governance,
  authority boundaries, and workflow gates.
- ADR-056 and ADR-057 define explicit redaction and secret-handling boundaries.

## Architecture Decisions

- EXP-731 is a scoped overlay problem, not a new authored-scenario meaning
  root. A refinement or extension must point back to the authored requirement,
  task/capture requirement, run, or study scope it constrains.
- The authored SDL `evidence_requirements` map remains the base capture-intent
  declaration. Task-, run-, and study-level changes must not mutate that map or
  reuse the same requirement id with changed meaning.
- Refinement means a stricter or more specific obligation over an existing
  requirement dimension such as scope, window, channel, media type, integrity,
  sensitivity, redaction, retention, loss disclosure, or satisfaction evidence.
  Extension means an explicitly additional obligation in a scoped context.
- Weakening a base requirement is not refinement. If a later context cannot
  satisfy the base requirement, represent that as a new task/study version,
  explicit supersedure, run deviation, loss disclosure, invalidation, or
  exclusion criterion.
- Task-level refinements belong with experiment task/capture intent:
  `ExperimentTaskModel.evaluation_protocol`, metric evidence requirements,
  observation requirements, and `experiment-capture-spec-v1` concepts. They
  must preserve the scenario/snapshot reference chain.
- Run-level refinements belong with run provenance: selected capture specs,
  evidence records, run `traceability`, `realized_form_disclosures`, and
  `augmentation_disclosures`. They must not rewrite the referenced task.
- Study-level refinements belong with study inclusion criteria, run allocation,
  analysis plans, validity notes, and membership constraints. They must cite
  task/run/evidence/analysis refs rather than changing the task protocol by
  implication.
- Existing satisfaction validation remains authoritative. New refinement checks
  must compose with `validate_experiment_run_against_task()` and the
  experiment-core model validators instead of adding a parallel evidence
  satisfaction algorithm.
- Reference identity must be explicit. Use constrained `ExperimentReferenceModel`
  subclasses and existing digest/path qualifier rules; do not identify
  requirements by title text, tag strings, fixture paths, backend ids, or log
  messages.

## Required Incumbents

- SDL base authoring: `EvidenceRequirement`, `Scenario.evidence_requirements`,
  `parse_sdl()`, `parse_sdl_file()`, `SDLModel`, `_HASHMAP_SECTIONS`,
  `SemanticValidator`, `_verify_evidence_requirements()`,
  `_named_ref_index()`, `_validate_named_ref()`, and post-instantiation
  semantic revalidation.
- Plane ownership: `ObservabilityEvidencePlane`, `PLANE_BY_SDL_SECTION`,
  `PLANE_BY_CONTRACT_ID`, `classify_sdl_section_plane()`,
  `classify_contract_plane()`, `assert_single_primary_plane()`, and
  `token_decides_plane()`.
- Experiment-core contracts: `ExperimentReferenceModel` and constrained
  reference subclasses, `ExperimentTaskModel`,
  `ExperimentEvaluationProtocolModel`, `ExperimentCaptureSpecModel`,
  `ExperimentCaptureRequirementModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentDerivedMeasureModel`, `ExperimentRunTraceabilityModel`,
  `ExperimentRunModel`, `ExperimentStudyModel`, and
  `validate_experiment_run_against_task()`.
- Schema authority: `ContractModel`, `schema_bundle()`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `contracts/schemas/`, `contracts/fixtures/`, and
  `contracts/schema-publication-manifest.json`.
- Runtime/API exposure, if later needed: `ControlPlaneSecurityConfig`,
  `ControlPlaneIdentity`, `ControlPlaneRole`, request-size guards,
  idempotency/request fingerprints, audit records, `Diagnostic`, `Severity`,
  and the redacted FastAPI error envelope.
- Secret handling: `enforce_observed_value_redaction()`, sensitivity/redaction
  fields on experiment evidence contracts, and ADR-056/057 explicit-redaction
  discipline.

## Cross-Cutting Layers

- SDL/config layer: base authored requirements must pass safe YAML loading,
  normalized keys, closed `SDLModel` shapes, symbol-key rejection, fail-closed
  reference resolution, and instantiated revalidation.
- Plane-classifier layer: refinements remain in the authored evidence,
  captured evidence, derived analysis, processor/backend operational, or
  scenario-native planes by carrier role, never by words such as `log`,
  `trace`, `telemetry`, or `evidence`.
- Contract/schema layer: any new portable carrier must be a closed
  `ContractModel` with `schema_bundle()` parity, fixtures, semantic invariant
  annotations where needed, and a schema-publication manifest ledger entry.
- Experiment-core layer: refinement satisfaction must reuse capture-spec key
  equality, window resolution, evidence-record redaction/loss, derived-measure
  source-evidence, run traceability, and task/run cross-artifact validators.
- Study layer: study-level constraints must use membership, inclusion
  criteria, run allocation, analysis plans, validity notes, and metric/run
  grounding. They must not create hidden task protocol changes.
- Auth/control-plane layer: future API exposure must reuse bearer/proxy
  authentication, backend/operator/auditor role gates, request-size limits,
  idempotency fingerprints, audit records, response DTOs, and redacted 500
  envelopes.
- Secret/env/OS exposure layer: refinement artifacts, diagnostics, fixtures,
  logs, command examples, and process argv must not carry operator secrets,
  bearer tokens, private keys, environment dumps, raw backend payloads, hidden
  answer keys, full tracebacks, or large raw evidence payloads. Use content
  refs, checksums, sensitivity, redaction state, and bounded summaries.
- Persistence layer: scoped refinements are portable contract data, not live
  runtime state. Do not store the only authoritative copy in
  `RuntimeSnapshot.metadata`, operation details, backend DTOs, audit blobs,
  raw logs, or free-form tags.
- Policy layer: implementation must satisfy Ground Control checks, module
  boundary policy, concept-authority governance, generated-schema parity,
  schema-publication governance, semantic coverage, and requirement
  traceability.

## Extension Boundary

The extension seam is a scoped refinement overlay with explicit provenance:

- stable refinement id and version;
- `scope_kind` constrained to task, run, or study;
- base requirement refs to authored SDL evidence requirements, experiment
  capture requirements, task observation requirements, or study/run refs;
- operation kind such as stricter constraint, additive requirement, or explicit
  supersedure;
- dimension-specific fields for source, scope, window, channel, media type,
  sensitivity, redaction, integrity, retention, loss disclosure, satisfaction,
  or comparability impact;
- rationale and provenance/evidence refs; and
- conflict policy that rejects silent loosening or ambiguous overlaps.

Future variations should add dimensions or governed terms through this seam.
Do not add a second evidence-requirement registry, resolver, schema family,
exception hierarchy, logging/audit path, persistence store, or workflow engine.

## Gotchas And Anti-Patterns

Avoid:

- rewriting authored SDL `evidence_requirements` during task, run, or study
  generation;
- changing a requirement's meaning while preserving its id;
- treating capture specs, backend capability claims, observability systems,
  audit records, diagnostics, or raw logs as proof of capture;
- loosening base requirements without explicit supersedure, deviation, loss,
  invalidation, or study exclusion semantics;
- resolving overlaps by first match, title text, tag strings, or backend-native
  object ids;
- putting refinement semantics only in `notes`, `metadata`, diagnostics,
  audit blobs, backend DTOs, or free-form tags;
- duplicating experiment-core capture, evidence-record, derived-measure, run,
  study, reference, or plane-classifier validators; and
- leaking secrets, hidden truth, answer keys, prompts, private traces,
  environment dumps, process argv, full tracebacks, or raw evidence payloads
  through schemas, fixtures, diagnostics, logs, examples, or comments.

## Non-Goals

- Implementing EXP-731 behavior, schemas, validators, endpoints, persistence,
  capture scheduling, fixtures, tests, or requirement status changes in this
  preflight note.
- Adding a new top-level SDL section, generic evidence bag, universal
  observability model, archival provenance root, or study protocol override
  model.
- Replacing DSL-124 authored evidence requirements, experiment-core contracts,
  run provenance, study analysis semantics, control-plane security, schema
  authority, concept authority, diagnostics, audit, persistence, or workflow
  policy.
