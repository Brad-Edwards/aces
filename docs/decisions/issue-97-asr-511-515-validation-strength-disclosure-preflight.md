# Issue 97 ASR-511/515 Validation Strength Disclosure Preflight

Date: 2026-07-05

Issue: #97.

Requirements: ASR-511 and ASR-515.

This note records architecture preflight guardrails for the joint validation
profile and validation-strength disclosure design. It is guidance only: it does
not publish the ADR, formal spec, schema changes, fixtures, validators,
runtime behavior, APIs, storage, or implementation plan.

## Binding Sources

- ASR-511 and ASR-515 are one design surface. ASR-511 defines the layered
  validation/admission profiles; ASR-515 exposes which profile, strength, and
  limitations support a scenario, task, run, or study claim.
- ADR-009, ADR-019, ADR-061,
  `contracts/schema-publication-manifest.json`, and
  `specs/authority/authority-boundary.yaml` govern normative schema/prose
  authority and schema evolution.
- ADR-012, ADR-062, `contracts/concept-authority/`,
  `specs/concept-authority/`, controlled vocabularies, reference models, and
  semantic profiles govern shared meaning and portable term sets.
- ADR-016 and `docs/explain/reference/shared-semantic-integrity.md` define the
  cross-stage semantic lifecycle and require reuse of existing parser,
  validator, instantiation, compiler, planner, runtime, and observation seams.
- ADR-021 requires claim strength to be supported by explicit evidence,
  threats/limitations, and falsification status rather than internal
  consistency.
- ADR-055, ADR-064, ADR-065, ADR-066, and ADR-068 define the experiment-core
  task/run/study, apparatus, evidence, traceability, realized-form,
  augmentation, observability-plane, replication, and replay-claim boundaries.
- ADR-054 and ADR-060 define participant action admission, participant runtime
  capability strength, participant-visible observation, retrieval, and
  comparability contracts. Those are adjacent but distinct from ASR-515
  validation-basis disclosure.
- `.ground-control.yaml`, `.gc/plan-rules.md`, ADR-014, `noxfile.py`, and
  `tools/verify_all.py` remain the workflow and verification authority.

## Architecture Decisions

- Design ASR-511 profiles and ASR-515 disclosures together. A disclosure must
  name the validation/admission profile it used, the achieved strength, the
  subject artifact, the gates actually applied, the evidence or diagnostics
  supporting the result, and the limitations or missing coverage. It must not
  let consumers infer strength from the mere existence of a schema, fixture,
  passing model validation, or successful run.
- Keep profile definition separate from profile use. ASR-511 owns the governed
  taxonomy and ordering of profile/strength terms. ASR-515 owns per-artifact
  basis records that say what happened for one scenario, task, run, study, or
  claim.
- Do not conflate ASR-511 validation profiles with GOV-920 semantic profiles,
  backend capability profiles, `scenario-instantiation-request-v1.profile`,
  SEM-218 realization support, API-407 participant feature support levels, or
  participant action `admission_disposition`. Those are existing terms with
  separate meanings.
- The reusable semantic unit is a validation-basis disclosure, not a new
  scenario/task/run/study super-model. Each carrier should bind the same
  disclosure semantics at its own authority point:
  scenario or scenario-snapshot for SDL validation/admission,
  `experiment-task-v1` for task/protocol support,
  `experiment-run-v1` for run-time and archival support, and
  `experiment-study-v1` for study/analysis support.
- Scenario disclosure must not rely on private implementation flags such as
  `Scenario._semantic_validated` or `InstantiatedScenario` private attrs as the
  portable record. Those flags can inform producers, but public support must be
  carried by a closed contract surface or by a governed reference to a
  scenario/snapshot artifact.
- Task, run, and study disclosure must extend the existing experiment-core
  chain. Tasks already carry protocol, apparatus constraints, artifact refs,
  and validity notes. Runs already carry task binding, apparatus context,
  traceability, realized-form disclosures, augmentation disclosures, evidence,
  and result summaries. Studies already carry membership, allocation, analysis
  plans, and validity notes. ASR-515 should connect to these surfaces instead
  of creating a parallel validation-report graph.
- Admission-basis disclosure for artifacts is not participant action
  admission. Reuse `ParticipantActionAdmissionRequest` and
  `participant_action_admission_request_violations()` only for participant
  action admission. Do not place scenario/task/run/study validation profile
  results in participant lifecycle `admission_disposition`.
- If a portable term needs cross-implementation comparison, put it under the
  existing concept-authority or controlled-vocabulary machinery. Do not leave
  profile ids, strength classes, gate kinds, or limitation categories as
  unrelated free strings in each carrier.
- Any published contract change must be closed-world and generated from the
  existing `ContractModel`/`schema_bundle()` path. Published JSON Schema is the
  structural authority; ACES semantic constraints that JSON Schema cannot
  express must be published through the existing `x-aces-invariants` pattern.

## Required Incumbents

Reuse these repo surfaces before adding anything new:

- SDL ingress and validation: `parse_sdl()`, `parse_sdl_file()`,
  YAML safe loading, key normalization, shorthand expansion, variable-key
  rejection, `SDLModel(extra="forbid")`, `SemanticValidator`,
  `instantiate_scenario()`, `SDLParseError`, `SDLValidationError`, and
  `SDLInstantiationError`.
- SDL contracts: `sdl-authoring-input-v1`, `instantiated-scenario-v1`,
  the generated schema bundle, and the instantiated-scenario unresolved-token
  invariant.
- Experiment-core carriers and validators:
  `ExperimentTaskModel`, `ExperimentRunModel`, `ExperimentStudyModel`,
  `ExperimentApparatusContextModel`, `ExperimentCaptureSpecModel`,
  `ExperimentEvidenceRecordModel`, `ExperimentDerivedMeasureModel`,
  `ExperimentRunTraceabilityModel`,
  `ExperimentRealizedFormDisclosureModel`,
  `ExperimentAugmentationDisclosureModel`,
  `validate_experiment_run_against_task()`, and
  `validate_experiment_study_against_tasks_and_runs()`.
- Manifest, capability, and concept authority:
  `ProcessorManifestV2Model`, `BackendManifestV2Model`,
  `ParticipantImplementationManifestModel`,
  `ParticipantImplementationProvenanceModel`,
  `manifest_authority`, `controlled_vocabularies`, `reference_models`,
  `semantic_profiles`, backend profile loading, and supported-contract
  allowlists.
- Participant/admission boundary:
  `ParticipantActionAdmissionRequest`,
  `participant_action_admission_request_violations()`,
  `RuntimeControlPlane.admit_participant_action()`,
  participant behavior history events, and participant observation/context
  contracts.
- Conformance and fixture surfaces: `run_fixture_suite()`,
  `run_target_conformance()`, `_validate_payload()`, `_semantic_diagnostics()`,
  `ConformanceCaseResult`, `BackendConformanceReport`, `contracts/fixtures/`,
  and `contracts/profiles/`.
- Control-plane and error surfaces:
  `RuntimeControlPlane`, `ControlPlaneStore`,
  `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneIdentity`,
  `ControlPlaneRole`, request-size guards, idempotency fingerprints, audit
  events, `OperationReceipt`, `OperationStatus`, `Diagnostic`, `Severity`, and
  the redacted FastAPI error envelope.
- Schema and policy tooling: `ContractModel`, `schema_bundle()`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, `tools/check_json_artifacts.py`,
  `tools/check_authority_boundary.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/check_semantic_coverage.py`,
  and `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL parser/config layer: scenario-level disclosures must be produced from
  safe parsed/expanded/instantiated SDL artifacts. They must not use raw YAML
  dictionaries, environment-variable discovery, untyped `metadata`, or private
  source-file layout as authority.
- SDL semantic layer: a disclosure that claims semantic validation must be
  backed by the existing `SemanticValidator` path, including fail-closed
  reference resolution, ambiguity, uniqueness, acyclicity, runtime-family
  guards, and instantiated revalidation where applicable.
- Contract/schema layer: external disclosure payloads must be closed
  `ContractModel` shapes with generated schemas, schema-publication manifest
  updates, valid/invalid fixtures, JSON artifact checks, and
  `x-aces-invariants` for cross-artifact checks.
- Experiment-core layer: task/run/study disclosures must reference or embed the
  same basis semantics while preserving existing separations: task protocol is
  not run evidence, capture intent is not captured evidence, raw evidence is
  not derived analysis, and study allocation is not a tag list.
- Admission layer: artifact admission decisions must use the existing
  processor, planner, manifest, conformance, and runtime diagnostic seams for
  their domain. Participant action admission remains scoped to
  `ParticipantActionAdmissionRequest` and must not become the generic
  validation-profile carrier.
- Manifest/profile layer: processor/backend/participant capability declarations
  must continue to pass supported-contract allowlists, concept bindings,
  controlled vocabulary checks, duplicate checks, compatibility declarations,
  and capability-gap helpers. Do not add profile requirement tables beside the
  published profile artifacts.
- API/auth layer: any future HTTP exposure must reuse fail-closed control-plane
  authentication, role authorization, request-size limits, idempotency,
  request fingerprints, audit events, published response models, and redacted
  internal-error responses.
- Secret-handling layer: disclosures, fixtures, examples, diagnostics, audit
  details, logs, and command examples must not contain credentials, bearer
  tokens, private keys, hidden truth, prompts, raw trace payloads, raw evidence
  payloads, backend-native object reprs, full stack traces, environment dumps,
  or process argv.
- OS/process exposure layer: tools should pass contract ids, profile ids,
  artifact refs, and filesystem paths only. Do not pass raw scenario payloads,
  evidence content, tokens, backend-private values, or claim text through
  process argv.
- Error-envelope layer: disclosure validation failures should name contract
  paths, profile ids, gate ids, refs, and sanitized diagnostic codes. They
  should not echo rejected confidential payload content or introduce a new
  exception hierarchy beside SDL errors, `Diagnostic`, operation envelopes, or
  policy failures.
- Persistence/logging layer: live state remains in `RuntimeSnapshot` and
  `ControlPlaneStore`; archival claims remain in experiment-core contracts and
  evidence/provenance artifacts. Do not make validation strength live only in
  `RuntimeSnapshot.metadata`, operation details, audit blobs, backend DTOs, raw
  logs, free-form tags, or README prose.
- Policy layer: changes must satisfy Ground Control policy, module-boundary
  policy, generated-schema parity, schema-publication governance,
  concept-authority governance, semantic coverage where touched, and
  requirement traceability.

## Extensibility Boundary

The extension seam is a versioned validation-basis disclosure shape plus a
governed validation-profile/strength vocabulary. That seam should be
parameterized by:

- subject reference, so the same disclosure semantics can bind to a scenario,
  scenario snapshot, task, run, study, or later claim artifact without a new
  root model;
- profile id/version and strength class, so ASR-511 can add or revise profiles
  in one governed place;
- gate results, so structural, semantic, behavioral, conformance,
  falsification, or future stronger gates can be added as rows/terms rather
  than new carrier-specific fields;
- producer/validator references, evidence refs, diagnostics refs, and
  artifact refs, so consumers can inspect what actually ran;
- limitation and not-covered disclosures, so a weaker basis is explicit rather
  than inferred from omissions; and
- optional audience or publication scope if later public APIs need redacted
  views of the same basis record.

Future profiles, gate kinds, strength terms, or limitation categories should
extend the governed vocabulary/spec, fixtures, and shared validators. They
should not require per-backend relation logic, duplicate profile loaders, a
second schema registry, or edits to unrelated runtime/control-plane paths.

## Gotchas And Anti-Patterns

Avoid:

- treating JSON Schema validity, Pydantic acceptance, or `semantic_validated`
  private flags as a complete validation-strength disclosure;
- using one generic `profile` field without saying whether it is a semantic
  profile, backend profile, instantiation profile, validation profile, or
  participant support level;
- adding `validation_report`, `validation_metadata`, `admission_metadata`, or
  `claim_strength` as untyped dicts or free-form log blobs;
- duplicating experiment-core task/run/study/evidence schemas, validators,
  reference resolvers, fixture loaders, conformance runners, exception
  hierarchies, logging stacks, audit paths, or persistence stores;
- storing validation strength only in runtime snapshots, operation statuses,
  evaluator detail, backend logs, diagnostics, tags, or changelog prose;
- conflating captured evidence with derived measures, task support artifacts
  with run evidence, or study validity notes with gate outcomes;
- accepting a behavioral or stronger profile without naming the runtime,
  conformance, falsification, or evidence gates that made it stronger than
  semantic validation;
- hiding weaker, partial, not-run, redacted, lossy, or unsupported gate results
  by omission;
- making a disclosure appear stronger because sensitive evidence was withheld;
  redaction must reduce or qualify the exposed basis unless an explicit
  governed proof/attestation remains available;
- adding a new validation profile taxonomy in backend manifests,
  participant-runtime capability declarations, semantic profiles, or SDL
  authoring prose without binding it to ASR-511;
- leaking secrets, hidden answers, prompts, private traces, backend-native ids,
  environment dumps, process argv, or full tracebacks through disclosure
  records, fixtures, diagnostics, audit details, logs, examples, or HTTP
  responses.

## Non-Goals

- Implementing ASR-511 or ASR-515 in this preflight note.
- Publishing the final ADR, formal validation-profile spec, schemas, fixtures,
  validators, conformance probes, API behavior, persistence, or UI surfaces.
- Updating ASR-511 or ASR-515 requirement status or claiming implementation
  coverage.
- Redesigning SDL parsing, semantic validation, experiment-core contracts,
  participant action admission, backend profiles, semantic profiles, concept
  authority, control-plane security, diagnostics, audit, persistence, or
  workflow policy.
- Adding a generic claim graph, validation service, raw evidence store,
  analysis engine, backend telemetry API, or replay/execution scheduler.
