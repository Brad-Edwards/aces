# Issue 340 ASR-525 Observability Conformance Preflight

Date: 2026-06-28

Issue: #340.

Requirement: ASR-525.

This note records architecture preflight guardrails for conformance fixtures
and checks that distinguish scenario-native observability, authored evidence
requirements, processor/backend augmentation, and required augmentation
disclosure. It is implementation guidance only: it does not add fixtures,
tests, schemas, validators, runtime behavior, APIs, storage, or coverage
claims.

## Binding Sources

- ADR-066 is the semantic authority for observability/evidence plane
  separation and augmentation classification.
- `specs/formal/observability-evidence-plane.md` defines OE invariants, the
  source-to-contract-to-test matrix, negative probes, and implemented coverage
  for SEM-224, SEM-225, DSL-123, and DSL-124.
- `specs/sdl/observability-and-evidence.md` defines the SDL authoring rules
  for scenario-native observability, authored evidence requirements, and
  augmentation disclosure boundaries.
- `docs/decisions/issue-334-sem-224-observability-plane-preflight.md`,
  `docs/decisions/issue-336-dsl-123-scenario-native-observability-preflight.md`,
  and
  `docs/decisions/issue-337-dsl-124-authored-evidence-requirements-preflight.md`
  define the adjacent implementation guardrails ASR-525 must bind together.
- `aces_sdl.observability_plane_semantics` is the carrier-oriented plane
  classifier. ASR-525 conformance checks must consume it, not replace it.
- `experiment-run-v1` `augmentation_disclosures` and
  `ExperimentAugmentationDisclosureModel` are the SEM-225 disclosure carrier
  and validator.
- `aces_conformance.conformance`, `contracts/fixtures/`,
  `contracts/profiles/backend/`, and `schema_bundle()` are the existing
  conformance, fixture, profile, and contract-validation surfaces.
- ADR-009, ADR-019, ADR-061, `contracts/schema-publication-manifest.json`, and
  `.gc/plan-rules.md` govern published schema authority and workflow gates.

## Architecture Decisions

- ASR-525 is an executable conformance requirement over existing semantics and
  carriers. It should prove the distinction and disclosure rules are enforced;
  it should not invent a new observability, evidence, or augmentation model.
- Plane ownership must remain carrier-oriented. Use
  `classify_contract_plane()`, `classify_runtime_family()`,
  `classify_sdl_section_plane()`, and existing validators rather than
  classifying strings such as `log`, `trace`, `telemetry`, `observation`, or
  `evidence`.
- Conformance fixtures should reuse the canonical fixture corpus shape:
  `contracts/fixtures/<family>/<contract-id>/valid/*.json` and
  `invalid/*.json`, with schema validation first and semantic diagnostics only
  after schema-valid payloads.
- Backend/profile fixture conformance must remain profile-artifact driven.
  `contracts/profiles/backend/*.json` is the authority for profile contract
  sets; do not reintroduce an in-code profile requirements table.
- SDL conformance checks must route through `parse_sdl()`,
  `SemanticValidator`, fail-closed reference resolution, and instantiated
  revalidation where applicable. Do not add a second SDL fixture loader,
  reference resolver, or exception hierarchy.
- Augmentation disclosure checks must exercise `experiment-run-v1`
  `augmentation_disclosures`, including environment-visible,
  participant-visible, and comparability-relevant cases. Do not hide
  augmentation claims in backend logs, diagnostics, metadata, operation
  details, or free-form tags.
- Conformance failures exposed through the runner or CLI must use the existing
  `Diagnostic` envelope and sanitized messages. Do not leak rejected payload
  contents, fixture secrets, hidden truth, backend-private ids, or tracebacks.
- If implementation changes a published schema to make a conformance case
  expressible, the published schema remains the authority and the change must
  update the reference implementation, fixtures, and
  `contracts/schema-publication-manifest.json` ledger together.

## Required Incumbents

- Plane classifier and SDL seams: `ObservabilityEvidencePlane`,
  `PLANE_BY_CONTRACT_ID`, `PLANE_BY_SDL_SECTION`,
  `SCENARIO_NATIVE_OBSERVABILITY_FAMILIES`, `token_decides_plane()`,
  `collect_scenario_native_observability_refs()`, `RUNTIME_SERVICE_FAMILIES`,
  `collect_qualified_runtime_family_refs()`, `parse_sdl()`, `SDLModel`,
  `SemanticValidator`, and `SDLParseError` / `SDLValidationError`.
- Experiment-core carriers: `ExperimentCaptureSpecModel`,
  `ExperimentEvidenceRecordModel`, `ExperimentDerivedMeasureModel`,
  `ExperimentRunTraceabilityModel`, `ExperimentRealizedFormDisclosureModel`,
  `ExperimentAugmentationDisclosureModel`, `ExperimentRunModel`, and
  `validate_experiment_run_against_task()`.
- Participant visibility and audience-view contracts:
  `ParticipantObservationEnvelopeModel`, `ParticipantContextViewModel`,
  `ParticipantHistoryViewModel`, `ParticipantStatusViewModel`, source-layer,
  transformation, marking, redaction, loss, and comparability validators.
- Apparatus and operational observability contracts:
  `BackendManifestV2Model`, `ProcessorManifestV2Model`,
  `ExperimentApparatusContextModel`, backend observation capabilities,
  measurement-channel refs, selected-manifest validation, `Diagnostic`, and
  `Severity`.
- Conformance runner and CLI: `fixtures_root()`, `profiles_root()`,
  `required_contracts()`, `run_fixture_suite()`, `run_target_conformance()`,
  `_fixture_case_diagnostics()`, `_semantic_diagnostics()`,
  `aces conformance backend`, and the legacy `aces_conformance.runner`
  delegate.
- Contract and corpus governance: `ContractModel`, `schema_bundle()`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `tools/check_json_artifacts.py`, `contracts/schemas/`,
  `contracts/fixtures/`, `contracts/profiles/`,
  `contracts/schema-publication-manifest.json`, controlled vocabularies, and
  concept-authority validators.
- Workflow and policy gates: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_schema_publication.py`, `tools/check_semantic_coverage.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers

- Fixture/config layer: conformance inputs must be JSON or SDL fixtures under
  canonical corpus roots, loaded through existing corpus/profile helpers or
  safe SDL parsing. Override roots must stay explicit parameters such as
  `--fixtures-root` and `--profiles-root`; do not add environment-variable
  discovery or path heuristics.
- Schema layer: valid fixtures must pass the checked-in published schema and
  matching `ContractModel`; invalid fixtures must fail schema and/or model
  validation. Published schema edits require generated-schema parity and a
  manifest ledger entry.
- Semantic layer: cross-artifact checks must reuse the SEM-224 classifier,
  DSL-123 runtime-family refs, DSL-124 evidence-requirement validation,
  SEM-225 augmentation validators, participant visibility rules, and
  experiment-core run/evidence traceability validators.
- Conformance runner layer: schema validation must run before semantic checks,
  profile load failures must become `conformance.profile-load-failed`, missing
  fixtures must become `conformance.fixture-missing`, and unknown contracts
  must fail closed as `conformance.contract-unknown`.
- Auth surface: ASR-525 should be offline fixture conformance by default and
  should not add an HTTP endpoint. If a future live-target probe is added, it
  must reuse `RuntimeControlPlane`, `ControlPlaneSecurityConfig`,
  `ControlPlaneIdentity`, `ControlPlaneRole`, request-size guards, idempotency,
  request fingerprints, audit events, response models, and redacted FastAPI
  error envelopes.
- Secret-handling layer: fixtures must be synthetic and redacted. Do not place
  bearer tokens, private keys, operator secrets, hidden answer keys, prompts,
  raw trace payloads, raw evidence payloads, backend-private ids, environment
  dumps, or full stack traces in fixtures, diagnostics, logs, CLI output, or
  assertion messages.
- Config/env-binding layer: do not introduce new runtime configuration,
  environment binding, or secret-binding shapes for conformance. Policy-only
  settings such as `ACES_REQUIREMENT_UID` remain workflow inputs, not contract
  or fixture data.
- OS-exposure layer: CLI and tool invocations should pass profile ids and
  filesystem paths only. Do not pass fixture payloads, raw evidence, tokens, or
  backend-private content through process argv.
- Error-envelope layer: runner and CLI failures must preserve structured
  diagnostic codes and sanitized messages. Parser failures should remain SDL
  errors. Pydantic validation details must not echo rejected confidential
  payloads when surfaced through public conformance reports.
- Persistence layer: ASR-525 does not add persistent state. Portable claims
  must live in SDL, contract fixtures, evidence records, run provenance, and
  schema-versioned artifacts; never only in `RuntimeSnapshot.metadata`, audit
  blobs, backend DTOs, raw logs, or operation details.
- Policy layer: changes must satisfy Ground Control policy, module-boundary
  policy, schema-publication governance, generated-schema parity, JSON artifact
  checks, semantic coverage, and requirement traceability.

## Extension Boundary

The extensibility seam is a small conformance probe catalog, not a new domain
model. Each probe should be parameterized by requirement UID or invariant id,
carrier contract id or SDL section, fixture path, expected plane or
augmentation classification, and expected diagnostic outcome.

Future probes should add rows and fixtures for new carriers, classifications,
or profile contract sets. They should not require editing every validator, a
second fixture runner, duplicate schema registries, or hard-coded string
classification.

## Gotchas And Anti-Patterns

Avoid:

- treating this issue as permission to redesign SEM-224, SEM-225, DSL-123, or
  DSL-124;
- adding a generic observability/evidence/augmentation super-schema;
- adding duplicate plane classifiers, reference resolvers, fixture loaders,
  profile requirement tables, validators, diagnostics, exception hierarchies,
  logging stacks, audit stacks, or persistence stores;
- deciding plane ownership from ambiguous tokens instead of carriers and
  registered runtime families;
- accepting backend logs, traces, health checks, diagnostics, audit records, or
  stack traces as participant observations or authored scenario meaning;
- treating scenario-native observability or authored evidence requirements as
  proof that evidence was captured;
- accepting environment-visible, participant-visible, or
  comparability-relevant augmentation without first-class disclosure,
  evidence refs, markings where required, and run traceability;
- putting portable semantics only in metadata, details, diagnostic text,
  backend DTOs, raw logs, or free-form tags;
- making conformance pass by weakening valid/invalid fixtures rather than
  exercising the existing validators;
- hand-editing published schemas without updating source models, generated
  parity, fixtures, and schema-publication manifest entries.

## Non-Goals

- Implementing ASR-525 fixtures, tests, runner changes, schemas, validators,
  CLI behavior, runtime probes, endpoints, persistence, or telemetry
  collection in this preflight note.
- Updating ASR-525 status or claiming implementation coverage.
- Changing the SEM-224 plane definitions, SEM-225 augmentation carrier,
  DSL-123 runtime-family model, or DSL-124 evidence-requirement syntax.
- Adding a new backend telemetry API, evidence capture scheduler, analysis
  engine, raw evidence storage layer, or participant visibility model.
- Replacing control-plane security, diagnostics, schema authority,
  concept-authority governance, conformance profile governance, or workflow
  policy.
