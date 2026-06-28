# Issue #342 EXP-732 Evidence Source And Augmentation Provenance Preflight Guardrails

Date: 2026-06-28

Issue: #342.

Requirement: EXP-732.

This preflight narrows issue #128 to preserving authored evidence
requirements, the realized evidence sources that satisfied them, and
processor/backend augmentation added for capture, evaluation, or operation.
It is implementation guidance only: it does not add schemas, fields,
validators, storage, APIs, fixtures, tests, or coverage claims.

## Architecture Decisions

- Treat `experiment-run-v1` as the canonical archival join point. Do not add an
  `experiment-evidence-provenance-v1`, `run-evidence-satisfaction-v1`, or
  parallel apparatus-provenance root.
- Preserve the distinction between authored requirement, executable capture
  specification, raw evidence record, run evidence artifact, derived measure,
  realized-form disclosure, and augmentation disclosure. None is a synonym for
  another.
- Preserve authored evidence requirements by reference to their authored SDL
  carrier and generated `experiment-capture-spec-v1` / capture requirement
  binding. A capture specification or authored requirement remains intent; it
  is not proof that capture occurred.
- Preserve realized evidence sources through `experiment-evidence-record-v1`
  `source_refs`, `capture_spec_ref`, `capture_requirement_ref`, raw-content
  metadata, redaction/loss state, and run `traceability.evidence_record_refs`.
  Do not treat backend logs, operation records, or audit events as realized
  evidence unless they are projected through evidence records or artifact refs.
- Preserve augmentation through existing run-level
  `augmentation_disclosures`. Environment-visible, participant-visible, or
  comparability-relevant augmentation must have evidence refs traced through
  the run; apparatus-only augmentation may remain apparatus/control-plane data
  only when no claim depends on it.
- Apparatus provenance remains `experiment-apparatus-context-v1` plus manifest
  identity, selected manifests, measurement channels, observed setup evidence,
  backend observation capability declarations, and run-level augmentation or
  realized-form disclosures. Apparatus context alone must not become a hidden
  satisfaction ledger.

## Required Incumbents

- SDL authored requirement surface: `aces_sdl.evidence_requirements`,
  `Scenario.evidence_requirements`, `SemanticValidator._verify_evidence_requirements`,
  `parse_sdl()`, `instantiate_scenario()`, fail-closed targetable refs, and
  `aces_sdl.observability_plane_semantics`.
- Experiment contracts:
  `ContractModel`, `ExperimentCaptureSpecModel`,
  `ExperimentCaptureRequirementModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentRunTraceabilityModel`, `ExperimentRealizedFormDisclosureModel`,
  `ExperimentAugmentationDisclosureModel`, `ExperimentRunModel`,
  `ExperimentApparatusContextModel`, `ExperimentArtifactRefModel`,
  `ExperimentReferenceModel`, `schema_bundle()`, and
  `validate_experiment_run_against_task()`.
- Apparatus and capability authority:
  processor/backend manifest models, `ObservationCapabilitiesModel`,
  `ObservationCapabilities`, `OBSERVATION_CAPABILITY_REQUIRED_CONTRACTS`,
  `observation_capability_contract_gaps()`, manifest-authority helpers,
  concept-authority catalogs, and governed observation vocabularies.
- Runtime/API incumbents for any future producer or publication path:
  `RuntimeControlPlane`, `ControlPlaneStore`, `ControlPlaneSecurityConfig`,
  `ControlPlaneIdentity`, `ControlPlaneRole`, request-size guards,
  idempotency keys, request fingerprints, audit events, closed FastAPI DTOs,
  `Diagnostic`, and the redacted HTTP 500 envelope.
- Backend/OS boundary incumbents:
  `DeploymentDriver`, fixed-argv OCI driver patterns, bounded timeouts,
  image trust policy, portable handles, and sanitized diagnostics.
- Governance:
  `contracts/schemas/`, `contracts/fixtures/`, `contracts/schema-publication-manifest.json`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, `tools/check_json_artifacts.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/verify_all.py`, `.ground-control.yaml`, and `.gc/plan-rules.md`.

## Cross-Cutting Layers

- SDL/config layer: authored evidence requirements must pass safe parsing,
  closed `SDLModel` shapes, no variable placeholders in symbol keys,
  fail-closed reference resolution, and instantiated semantic revalidation.
- Plane-classifier layer: source and carrier meaning must come from
  `ObservabilityEvidencePlane` and carrier-role classifiers, not words such as
  `log`, `trace`, `telemetry`, `observation`, or `evidence`.
- Contract structural layer: external artifacts must pass generated draft
  2020-12 schemas and closed-world `ContractModel` validation. Unknown fields
  remain errors.
- Contract semantic layer: run traceability, evidence-record content/loss
  disclosure, augmentation disclosure semantics, realized-form evidence refs,
  apparatus manifest binding, task/run protocol binding, and task evidence
  satisfaction must use existing validators and `x-aces-invariants`.
- Auth surface: any future HTTP create/read path must use existing
  control-plane identity and role checks. Publishing provenance is a mutating
  operation; dereferencing evidence content is a separate authorized read.
- Request/idempotency surface: future HTTP paths must keep request-size guards,
  idempotency keys, request fingerprints, audit recording, and closed DTOs.
  Do not add a provenance-specific request pipeline.
- Secret-handling surface: provenance may carry sensitivity-aware refs,
  checksums, bounded summaries, redaction state, loss disclosures, and
  non-secret provenance refs. It must not carry credentials, bearer tokens,
  private keys, hidden answer keys, prompts, raw trace payloads, environment
  dumps, backend-private object reprs, full tracebacks, process argv, or raw
  captured payloads.
- Config/env-binding surface: do not introduce a new environment, token, or
  secret-binding shape. If runtime values contribute evidence, use existing
  runtime sensitivity classifications and observed-value redaction helpers.
- OS-level exposure: producers, fixtures, and CLIs must not pass tokens,
  credentials, backend-private payloads, or large raw evidence content through
  process arguments. Use content files, URIs, checksums, bounded summaries, and
  synthetic fixtures.
- Error-envelope surface: validation failures should surface as Pydantic
  errors or existing `Diagnostic` values; HTTP failures use the existing
  redacted error envelope. Do not echo full run records, evidence payloads,
  stderr, tracebacks, argv, secrets, or backend internals.
- Persistence surface: do not store the only copy of authored requirements,
  realized source satisfaction, evidence records, or augmentation provenance in
  `RuntimeSnapshot.metadata`, operation records, participant histories, audit
  details, backend DTOs, raw logs, or free-form tags. Durable persistence, if
  added later, must preserve schema-versioned experiment artifacts and refs.

## Extension Boundary

The extensibility seam is a typed run-level relationship over existing
experiment references, not a new provenance stack. If existing traceability,
evidence records, and augmentation disclosures are insufficient, extend the
existing run contract with a typed satisfaction relation that links:

- authored requirement or capture-spec requirement identity;
- realized evidence-record refs;
- realized source refs;
- relevant evidence artifact refs;
- augmentation disclosure ids or refs; and
- loss/redaction/observer-effect notes when the satisfaction claim depends on
  them.

Producer code should parameterize the authored-requirement source, capture-spec
binding, artifact locator/sealing policy, redaction policy, and augmentation
source. Future backend, processor, storage, or analysis variants should emit
the same canonical contract shape rather than changing the authority surface.

## Gotchas And Anti-Patterns

- Do not treat authored evidence requirements, capture specs, backend
  capability claims, traceability refs, or scenario-native observability
  declarations as proof of capture.
- Do not treat an evidence artifact id as equivalent to an evidence record,
  capture requirement, source ref, derived measure, or augmentation disclosure.
- Do not let backend logs, operation statuses, audit records, diagnostics,
  participant histories, runtime snapshot metadata, or backend-native DTOs be
  the only portable satisfaction carrier.
- Do not use `augmentation_disclosures` or `realized_form_disclosures` as
  unstructured log lists.
- Do not duplicate schema registries, validators, reference resolvers,
  exception hierarchies, persistence stacks, manifest renderers, logging/audit
  pipelines, or workflow logic.
- Do not hand-edit `contracts/schemas/`; update contract source, regenerate
  schemas, keep `schema_bundle()` parity, update fixtures/tests, and record
  schema-publication manifest ledger entries when published hashes change.

## Non-Goals

- Implementing EXP-732 behavior, schema fields, validators, producers,
  storage, APIs, fixtures, tests, or status changes in this preflight.
- Implementing runtime evidence capture, packet/log/trace collection,
  retention, sealing, redaction execution, retrieval, schedulers, workers, or
  background capture orchestration.
- Implementing derived-measure computation, evaluator behavior, statistical
  analysis, study comparison, replay, or artifact dereference authorization.
- Replacing DSL-124, SEM-224, SEM-225, experiment-core contracts, apparatus
  context, participant visibility contracts, control-plane security,
  diagnostics, schema authority, concept authority, or Ground Control policy.
