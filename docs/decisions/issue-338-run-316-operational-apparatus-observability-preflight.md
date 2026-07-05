# Issue 338 RUN-316 Operational Apparatus Observability Preflight

Date: 2026-06-28

Issue: #338.

Requirement: RUN-316.

This note records architecture preflight guardrails for operational
observability surfaces used by processors and backends. It is implementation
guidance only: it does not add runtime behavior, schemas, endpoints, storage,
fixtures, tests, or coverage claims.

## Binding Sources

- ADR-008 defines the processor as the semantics-bearing middle layer and
  separates live execution state from archival run provenance.
- ADR-036 defines package ownership: processor logic in `aces_processor`, live
  control in `aces_runtime`, backend protocol declarations in
  `aces_backend_protocols`, and neutral DTOs in `aces_contracts`.
- ADR-066 defines the processor/backend operational observability plane and
  requires it to remain distinct from scenario-native observability, authored
  evidence requirements, captured evidence, and derived analysis.
- `docs/decisions/issue-334-sem-224-observability-plane-preflight.md`,
  `docs/decisions/issue-336-dsl-123-scenario-native-observability-preflight.md`,
  and `aces_sdl.observability_plane_semantics` define the carrier-oriented
  classifier and forbid token-based plane decisions.
- ADR-055, ADR-064, and ADR-065 define experiment apparatus context, capture
  specs, evidence records, derived measures, run traceability, realized-form
  disclosures, and augmentation disclosures.
- ADR-054 and ADR-060 define participant-visible observations, participant
  runtime retrieval views, visibility projection, markings, redaction, loss,
  and information guarantees. Operational apparatus telemetry is not a
  participant observation unless projected through those carriers.
- ADR-063 records backend implementation guardrails: portable facts only,
  `Diagnostic`/`OperationReceipt`/`OperationStatus` public failures, no
  backend-specific exception hierarchy, no raw native output in diagnostics.
- `.ground-control.yaml`, `.gc/plan-rules.md`, ADR-009, ADR-019, ADR-061,
  `contracts/schema-publication-manifest.json`, and `tools/policy/adr_policy.yaml`
  define workflow, schema, publication, and module-boundary gates.

## Architecture Decisions

- RUN-316 is the processor/backend operational plane from ADR-066. Do not add a
  generic top-level `observability`, `telemetry`, `logs`, or `traces` model.
- Plane ownership must stay carrier-oriented. `backend-manifest-v2`,
  `processor-manifest-v2`, and `experiment-apparatus-context-v1` already map to
  `PROCESSOR_BACKEND_OPERATIONAL` through
  `classify_contract_plane()`. Do not infer the plane from words such as
  `log`, `trace`, `telemetry`, `observation`, or `evidence`.
- Static apparatus declarations belong in existing manifest surfaces:
  `ProcessorManifestV2Model`, `BackendManifestV2Model`, concept bindings,
  supported contract versions, compatibility declarations, constraints, and
  capability blocks. `ObservationCapabilities` is specifically EXP-715 evidence
  capture support, not a catch-all operational log capability.
- Live operational state belongs in existing runtime/control-plane surfaces:
  `RuntimeManager.status()`, `RuntimeControlPlane`, `RuntimeSnapshot`,
  `OperationReceipt`, `OperationStatus`, backend component
  `status()`/`results()`/`history()` methods, `ControlPlaneStore`, and
  append-only `AuditEvent` records.
- Archival or reviewable apparatus facts must be projected through experiment
  contracts: `ExperimentApparatusContextModel` for run-scoped instrument
  context, `ExperimentEvidenceRecordModel` for raw captured evidence,
  `ExperimentDerivedMeasureModel` for interpreted analysis,
  `ExperimentRunModel.traceability`, realized-form disclosures, and
  augmentation disclosures.
- Public exposure must reuse `create_control_plane_app()`,
  `ControlPlaneSecurityConfig`, control-plane role checks, request-size guards,
  idempotency keys, request fingerprints, audit events, response models, and
  redacted FastAPI error envelopes.
- Backend/public failures remain `Diagnostic`, `ApplyResult`,
  `OperationReceipt`, and `OperationStatus`. Do not introduce a new exception,
  logging, or error-envelope hierarchy for operational observability.

## Required Incumbents

- Plane classification: `ObservabilityEvidencePlane`,
  `PLANE_BY_CONTRACT_ID`, `classify_contract_plane()`,
  `assert_single_primary_plane()`, and `token_decides_plane()`.
- Manifest and capability authority: `ProcessorManifest`,
  `ProcessorCapabilitySet`, `reference_processor_manifest_payload()`,
  `BackendManifest`, `BackendCapabilitySet`, `ObservationCapabilities`,
  `backend_manifest_payload()`, supported contract validators, controlled
  vocabulary validators, and concept bindings.
- Runtime and backend boundaries: `RuntimeTarget`, `_validate_runtime_target_shape()`,
  `Provisioner`, `Orchestrator`, `Evaluator`, `ParticipantRuntime`,
  `_call_backend_diagnostics()`, `_call_backend_apply()`,
  `RuntimeManager`, and `RuntimeControlPlane`.
- Live-state DTOs and persistence: `RuntimeSnapshot`, `SnapshotEntry`,
  `ApplyResult`, `OperationReceipt`, `OperationStatus`, `ControlPlaneStore`,
  `InMemoryControlPlaneStore`, `LocalControlPlaneStore`, and `AuditEvent`.
- HTTP exposure: `create_control_plane_app()`, `_ControlPlaneApiAuth`,
  `ControlPlaneIdentity`, `ControlPlaneRole`, `request_size_guard_response()`,
  `_request_fingerprint()`, OpenAPI response declarations, and redacted 500
  handling.
- Contract authority: `ContractModel`, `schema_bundle()`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `contracts/schemas/`, `contracts/fixtures/`, and
  `contracts/schema-publication-manifest.json`.
- Experiment projection: `ExperimentApparatusContextModel`,
  `ExperimentCaptureSpecModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentDerivedMeasureModel`, `ExperimentRunModel`,
  `ExperimentAugmentationDisclosureModel`, and
  `validate_experiment_run_against_task()`.
- Conformance and workflow: `aces_conformance.conformance`,
  `observation_capability_contract_gaps()`,
  `participant_runtime_capability_contract_gaps()`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers

- Auth and authorization: any HTTP/API surface must pass
  `ControlPlaneSecurityConfig` authentication, target scoping, and
  `BACKEND`/`OPERATOR`/`AUDITOR` role gates. Mutating observability actions are
  not auditor-readable shortcuts.
- Secret handling and redaction: diagnostics, audit details, examples,
  fixtures, status payloads, snapshots, and experiment records must not expose
  bearer tokens, private keys, credentials, operator secrets, environment
  dumps, raw evidence payloads, hidden truth, private traces, prompts, backend
  private object reprs, or full tracebacks.
- Config and manifest validation: processor/backend declarations must pass
  supported contract version checks, controlled vocabulary scopes, concept
  binding scope checks, compatibility checks, and closed `ContractModel` shapes.
- OS-level exposure: operational capture must not place secrets in process
  argv, shell command strings, environment dumps, native stdout/stderr,
  daemon inspect payloads, host paths, or backend-native handles returned to
  portable surfaces.
- Error envelopes: backend exceptions must flow through
  `_call_backend_diagnostics()` or `_call_backend_apply()` into `Diagnostic`;
  HTTP failures must use explicit 4xx responses or the existing redacted 500
  envelope; public payloads must not include stack traces.
- Runtime validation: backend apply results must pass `ApplyResult` shape
  checks, snapshot/result contract diagnostics, participant transition checks,
  and SEM-218 realization disclosure gates before becoming live state.
- Persistence: mutable operational state stays in `RuntimeSnapshot`,
  operation records, and audit logs through `ControlPlaneStore`. Archival
  evidence, run provenance, and analysis stay in experiment-core contracts.
  Do not use `RuntimeSnapshot.metadata`, operation `details`, audit blobs,
  backend DTOs, or raw logs as portable claim carriers.
- Schema publication: any published schema change must preserve
  `schema_bundle()` parity, add fixtures, and update
  `contracts/schema-publication-manifest.json` with the required ledger entry.
- Module boundaries: new code must respect ADR-036 import rules in
  `tools/policy/adr_policy.yaml`; no implementation logic belongs in
  `implementations/python/src/aces/`.

## Extension Boundary

The extensibility seam is existing carrier kind plus explicit references, not
a new observability taxonomy:

- static support claims vary by processor/backend identity, component kind,
  supported contract versions, capability block, constraint ref, and concept
  binding;
- live operational views vary by target, component role, operation id,
  domain, snapshot address, history scope, audit scope, and authorization role;
- archival projections vary by apparatus component ref, selected manifest ref,
  measurement channel ref, capture requirement ref, evidence record ref,
  provenance ref, redaction/loss disclosure, and comparability or augmentation
  classification.

Future processors, backends, probes, health checks, setup attestations, or
measurement-channel observations should add parameters on those seams. They
must not hard-code a vendor, driver, protocol, log format, or backend adapter
as the portable ACES concept boundary.

## Gotchas And Anti-Patterns

Avoid:

- treating `ObservationCapabilities` as generic operational observability
  instead of evidence-capture capability;
- making backend logs, traces, health checks, audit records, or stack traces
  participant-visible observations without a participant observation/context
  projection;
- treating control-plane audit events as captured experiment evidence unless
  projected through `experiment-evidence-record-v1` with provenance and
  sensitivity;
- treating a capture spec, measurement channel, or apparatus context as proof
  that evidence was captured;
- placing portable claims only in `metadata`, `details`, diagnostics, audit
  blobs, backend-native DTOs, raw logs, or free-form tags;
- adding duplicate schemas, validators, stores, exception hierarchies,
  observability registries, manifest renderers, conformance logic, or
  workflow logic;
- exposing operational data through a route that bypasses control-plane auth,
  request-size limits, idempotency, auditing, response models, or redacted
  error handling;
- weakening accepted ADRs in place instead of following ADR-059 amendment or
  supersedure rules.

## Non-Goals

- Implementing RUN-316 behavior, APIs, schemas, persistence, collection
  agents, exporters, fixtures, tests, or status transitions in this preflight.
- Implementing DSL-123 scenario-native observability, DSL-124 authored
  evidence requirements, SEM-225 augmentation behavior, or experiment evidence
  capture scheduling.
- Creating a generic observability bag, universal evidence taxonomy, new
  runtime telemetry store, new backend exception hierarchy, new logging
  channel, new conformance authority, or new schema authority.
- Redesigning participant visibility semantics, experiment-core contracts,
  control-plane security, backend protocols, processor manifests, concept
  authority, or Ground Control workflow policy.
