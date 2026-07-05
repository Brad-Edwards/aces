# Issue 339 API-419 Observation Augmentation Disclosure Contracts Preflight

Date: 2026-06-28

Issue: #339.

Requirement: API-419.

This note records architecture preflight guardrails for portable declaration
and reporting contracts for processor or backend observation augmentation. It
is implementation guidance only: it does not add schemas, validators, runtime
behavior, APIs, storage, fixtures, tests, or coverage claims.

## Binding Sources

- ADR-066 is the semantic authority for observability/evidence plane
  separation and augmentation classifications.
- `specs/formal/observability-evidence-plane.md` records the SEM-225
  augmentation invariant set and realized implementation coverage.
- `specs/sdl/observability-and-evidence.md` states that run-level
  processor/backend augmentation disclosures are carried by
  `experiment-run-v1` `augmentation_disclosures`.
- `aces_conformance.conformance` records the executable conformance surface
  that checks augmentation disclosures name portable affected carriers and
  supporting evidence where the purpose requires it.
- ADR-055, ADR-064, and ADR-065 define experiment-core task, apparatus
  context, capture, raw evidence, derived measure, run traceability,
  realized-form, and augmentation boundaries.
- ADR-060, ADR-022, and ADR-054 define participant-visible observations,
  participant context views, visibility projection, markings, redaction, loss,
  and comparability disclosure.
- ADR-036 defines package ownership: SDL language logic belongs in `aces_sdl`,
  live runtime control in `aces_runtime`, and neutral boundary DTOs in
  `aces_contracts`.
- ADR-056 and ADR-057 define observed-value and secret-handling boundaries.
- ADR-009, ADR-061, ADR-062, `contracts/schema-publication-manifest.json`,
  and `.gc/plan-rules.md` define schema authority, publication governance,
  concept authority, and workflow gates.

## Architecture Decisions

- API-419 is a portable contract-boundary requirement. Do not create a
  backend-local augmentation model, raw telemetry endpoint, or generic
  observability bag.
- Keep declaration-time capability/support separate from run-time reporting:
  manifest declarations say what an apparatus can support; run disclosures say
  what augmentation was actually used for a run.
- Reuse existing report carriers. Actual processor/backend augmentation is
  reported through `ExperimentRunModel.augmentation_disclosures` and
  `ExperimentAugmentationDisclosureModel`, not a second run-provenance root.
- Reuse existing declaration carriers. Backend observation capability claims
  belong under `BackendManifestV2Model.capabilities.observation` and the
  backend manifest authority/conformance helpers. If processor-side
  declarations are needed, extend `ProcessorManifestV2Model` through its
  manifest authority surface deliberately; do not model them as backend-only
  constraints or free-form processor metadata.
- Added capture surfaces and apparatus must be first-class references:
  measurement channels, apparatus context components, capture specs, evidence
  records, manifests, profiles, scenario snapshots, or run refs. Backend logs,
  raw DTOs, and diagnostic text are not portable carriers.
- Constraints, side effects, observer effects, participant visibility, and
  comparability implications must remain separate fields. Do not collapse them
  into a prose note, tag list, or `metadata` object.
- Participant-visible augmentation must route through participant visibility
  projection and participant observation/context carriers. A backend observing
  something is not the same as a participant observing it.
- Comparability-relevant augmentation must have explicit observer-effect and
  comparability-effect disclosure, evidence refs, and run traceability.
- Any new portable term must be governed by concept authority or controlled
  vocabularies only when cross-implementation comparison needs a bounded
  shared term.

## Required Incumbents

- Plane classifier: `ObservabilityEvidencePlane`,
  `classify_contract_plane()`, `classify_runtime_family()`,
  `assert_single_primary_plane()`, `token_decides_plane()`,
  `PLANE_BY_CONTRACT_ID`, and
  `SCENARIO_NATIVE_OBSERVABILITY_FAMILIES`.
- Run-level reporting: `ExperimentAugmentationDisclosureModel`,
  `_SEM_225_PORTABLE_CARRIER_KINDS`, `ExperimentRunModel`,
  `ExperimentRunTraceabilityModel`, and `validate_experiment_run_against_task()`.
- Experiment-core carriers: `ExperimentReferenceModel`,
  `ExperimentApparatusContextModel`, `ExperimentCaptureSpecModel`,
  `ExperimentCaptureRequirementModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentDerivedMeasureModel`, and `ExperimentRealizedFormDisclosureModel`.
- Declaration-time apparatus contracts: `BackendManifestV2Model`,
  `ProcessorManifestV2Model`, `ObservationCapabilitiesModel`,
  `ObservationCapabilities`, `OBSERVATION_CAPABILITY_REQUIRED_CONTRACTS`,
  `BACKEND_SUPPORTED_CONTRACT_IDS`, `PROCESSOR_SUPPORTED_CONTRACT_IDS`,
  `backend_manifest_payload()`, and `observation_capability_contract_gaps()`.
- Participant-visible contracts: `ParticipantObservationEnvelopeModel`,
  `ParticipantContextViewModel`, `ParticipantContextComparabilityModel`,
  `ParticipantHistoryViewModel`, `ParticipantStatusViewModel`, markings,
  redaction-policy refs, source-layer validation, and comparability disclosure
  validation.
- Schema authority: `ContractModel`, `schema_bundle()`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `contracts/schemas/`, `contracts/fixtures/`, and
  `contracts/schema-publication-manifest.json`.
- Runtime/API surfaces for any future exposure:
  `ControlPlaneSecurityConfig`, `ControlPlaneIdentity`, `ControlPlaneRole`,
  request-size guards, request fingerprints, idempotency keys, audit events,
  response models, `ControlPlaneStore`, `Diagnostic`, `Severity`, and the
  redacted FastAPI error envelope.
- Conformance diagnostics: `observability_evidence_conformance_diagnostics()`,
  `_augmentation_conformance_diagnostics()`, `run_fixture_suite()`,
  `run_target_conformance()`, and the canonical
  `conformance.observability-evidence-invalid` diagnostic code.

## Cross-Cutting Layers

- Contract shape layer: external payloads must be closed-world
  `ContractModel` descendants. Published JSON Schemas must stay in parity with
  `schema_bundle()` and must update the schema publication manifest when
  changed.
- Manifest authority layer: declaration-time support must pass supported
  contract allowlists, concept bindings, controlled vocabulary validation,
  duplicate checks, and conformance gap helpers. New processor declaration
  fields must update the same authority sets rather than bypassing them.
- Experiment-run layer: report-time disclosures must pass SEM-225
  classification validation, processor/backend `augmented_by_ref` authority,
  portable `carrier_refs`, unique ids/refs, required evidence refs, and run
  traceability binding.
- Participant visibility layer: participant-visible output must pass
  participant observation/context/history/status contracts, visibility
  projection, source-layer mediation, markings, redaction, loss, authorization
  scope, and comparability disclosure.
- Conformance layer: API-419 examples and producers must satisfy
  `observability_evidence_conformance_diagnostics()` in addition to model and
  schema validation; in particular, augmentation disclosures need
  `affected_refs`, portable `carrier_refs`, and purpose-appropriate
  `evidence_refs`.
- Apparatus/control-plane layer: operational telemetry remains apparatus data
  until projected through manifests, apparatus context, diagnostics, evidence
  records, run traceability, or participant-visible contracts.
- Auth/API layer: any future HTTP route must reuse fail-closed bearer/proxy
  auth, backend/operator/auditor role checks, request-size limits, idempotency,
  request fingerprints, audit events, response models, and redacted 500
  envelopes.
- Config/env-binding layer: API-419 must not add a new environment-variable,
  token-binding, or secret-binding shape. Workflow inputs such as
  `ACES_REQUIREMENT_UID` remain policy inputs, not contract fields, and any
  runtime configuration evidence must use existing sensitivity/redaction
  helpers before it is referenced by a portable disclosure.
- Secret and OS-exposure layer: contracts, fixtures, logs, diagnostics, audit
  details, command examples, process argv, environment captures, and backend
  inspect payloads must not expose tokens, private keys, credentials, hidden
  truth, prompts, raw traces, raw evidence payloads, full stack traces, or
  backend-private object representations.
- Persistence layer: portable augmentation claims must not live only in
  `RuntimeSnapshot.metadata`, operation details, audit blobs, backend-native
  DTOs, raw logs, or free-form tags. Live state stays in `RuntimeSnapshot` and
  `ControlPlaneStore`; archival claims use experiment-core contracts.
- Error-envelope layer: contract validation errors should identify structural
  contract violations without echoing raw captured payloads or secrets. Runtime
  and HTTP failures must use existing diagnostics or redacted error envelopes.
- Policy layer: implementation must satisfy Ground Control policy checks,
  module-boundary policy, generated-schema parity, schema-publication
  governance, concept-authority governance, semantic coverage, and requirement
  traceability.

## Extension Boundary

The extensibility seam is the existing declaration/reporting split:

- declaration-time support is parameterized by apparatus identity, supported
  contract ids, observation capability terms, concept bindings, constraints,
  and conformance gap checks;
- report-time use is parameterized by augmentation id, purpose, realization
  layer, additive classifications, processor/backend authority, portable
  carrier refs, affected refs, evidence refs, disclosure policy, markings,
  environment effect, participant visibility, observer effect, and
  comparability effect; and
- participant/audience projection is parameterized by source layers,
  transformation rule, audience scope, evidence/provenance refs, redaction
  policy, and comparability backend-disclosure refs.

Future capture-surface, apparatus, channel, sealing, redaction, observer-effect,
or comparability variants should extend those parameters or their governed
vocabularies. A new root contract is appropriate only if both the manifest
declaration surface and `experiment-run-v1` reporting surface cannot represent
the boundary without concept confusion, and that decision needs an ADR update.

## Gotchas And Anti-Patterns

Avoid:

- adding `observation_augmentation`, `telemetry`, `logs`, `traces`, or
  `evidence` as a generic free-form bag;
- creating a duplicate augmentation schema, manifest renderer, plane
  classifier, reference resolver, exception hierarchy, logging/audit path,
  persistence store, fixture loader, or workflow pipeline;
- treating backend logs, health checks, stack traces, audit records, raw
  packet captures, process argv, or environment dumps as portable
  participant-visible observations;
- treating a manifest capability claim, capture spec, or run traceability ref
  as proof that evidence was captured;
- reporting environment-visible or comparability-relevant augmentation with
  only backend-local logs or diagnostics;
- omitting evidence refs for environment-visible, participant-visible, or
  comparability-relevant augmentation;
- using `apparatus_only` as the default when the augmentation changes the
  realized environment, participant-visible information, or comparison basis;
- placing constraints, side effects, redaction, loss, observer effects, or
  comparability implications only in prose notes;
- adding published schemas without fixtures, `schema_bundle()` parity, and a
  schema publication manifest ledger update;
- leaking hidden truth, answer keys, evaluator state, prompts, private traces,
  credentials, operator secrets, raw evidence payloads, environment dumps, or
  full tracebacks through SDL, contracts, schemas, fixtures, diagnostics,
  audit records, logs, examples, or HTTP responses.

## Non-Goals

- Implementing API-419 behavior, schemas, validators, endpoints, storage,
  producers, conformance checks, fixtures, or tests in this preflight note.
- Updating API-419 status or claiming implementation coverage.
- Redesigning SEM-225, experiment-core run provenance, participant visibility
  semantics, schema authority, concept authority, control-plane security,
  diagnostics, audit, persistence, or workflow policy.
- Implementing capture scheduling, telemetry collection, packet/log/trace
  parsing, retention, sealing, redaction execution, analysis engines, scoring,
  or study comparison logic.
