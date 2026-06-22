# Issue #234 EXP-708 Evidence Record Preflight Guardrails

Date: 2026-06-22

Issue: #234.

Requirement: EXP-708.

This preflight narrows the issue #88 evidence and measure boundary to raw
captured evidence records for EXP-708. ADR-064 and
`specs/formal/experiment-core/README.md` remain the normative design authority.
This note is guidance for implementation only.

## Architecture Decisions

- Treat `experiment-evidence-record-v1` as the first-class raw captured
  evidence surface for observations, traces, telemetry, artifacts, logs,
  packet captures, and other run evidence.
- Keep raw evidence records distinct from `experiment-capture-spec-v1`
  capture intent, `experiment-derived-measure-v1` interpreted outputs,
  `experiment-run-v1` evidence-artifact summaries, participant-runtime
  observation envelopes, backend-private logs, and backend observation
  capability claims.
- Every evidence record must cite a capture specification, a capture
  requirement, a run, source references, evidence kind, capture timestamp,
  capture window, raw content, sensitivity, redaction state, and provenance.
- Raw content must use the existing `raw_content` choices: an artifact
  reference, a content URI with checksum, or a bounded payload summary. Do not
  add backend-specific inline payload shapes or opaque result blobs.
- EXP-708 does not implement capture execution, storage, retention, redaction
  execution, APIs, schedulers, workers, statistical analysis, or evaluator
  behavior. Later work may publish or retrieve evidence records, but must do so
  through the existing contract and control-plane gates.

## Required Incumbents

- Contract source:
  `implementations/python/packages/aces_contracts/contracts.py`, especially
  `ContractModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentRawEvidenceContentModel`, `ExperimentCaptureSpecReferenceModel`,
  `ExperimentEvidenceRecordReferenceModel`, `ExperimentReferenceModel`,
  `ExperimentArtifactRefModel`, `ExperimentChecksumModel`, RFC 3339 date-time
  parsing, and `schema_bundle()`.
- Published contract surface:
  `contracts/schemas/experiment-core/experiment-evidence-record-v1.json`,
  `contracts/fixtures/experiment-core/experiment-evidence-record-v1/`,
  `contracts/schema-publication-manifest.json`, and
  `tools/generate_contract_schemas.py`.
- Validation and conformance:
  `implementations/python/tests/test_runtime_contracts.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_json_artifacts.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, and `tools/verify_all.py`.
- Adjacent evidence boundaries:
  `experiment-capture-spec-v1` for capture intent,
  `experiment-derived-measure-v1` for values and analysis outputs,
  `experiment-run-v1` for archival run summaries, and
  participant-runtime observation contracts for live participant-facing
  history.
- Backend capability declarations:
  `ObservationCapabilities`, `ObservationCapabilitiesModel`,
  `backend_manifest_payload()`, `observation_capability_contract_gaps()`,
  `BACKEND_SUPPORTED_CONTRACT_IDS`,
  `OBSERVATION_CAPABILITY_REQUIRED_CONTRACTS`, and the governed observation
  vocabularies in concept authority.
- If an API or retrieval surface is added later:
  `aces_runtime.control_plane_api`, `control_plane_api_guards`,
  `control_plane_api_models`, `control_plane_security`,
  `control_plane_store`, request fingerprints, audit events, structured
  `Diagnostic` values, and redacted FastAPI error handling.

## Whole-Repo Scope

- Repo workflow policy: `.ground-control.yaml`, `.gc/plan-rules.md`, and the
  repo policy and verification scripts.
- Normative design authority: ADR-064, ADR-055, and
  `specs/formal/experiment-core/README.md`.
- Contract publication authority: contract source, generated schemas, fixtures,
  schema publication manifest, and schema drift/publication checks.
- Concept and capability authority: concept-authority vocabularies, backend
  manifest authority lists, backend protocol capability dataclasses, manifest
  renderers, and observation capability gap checks.
- Runtime/API boundary for future work: control-plane auth, request guards,
  idempotency, audit store, diagnostics, redacted error envelopes, and existing
  runtime redaction/config validators.

## Cross-Cutting Layers

- Structural validation: external evidence payloads must pass closed-world
  `ContractModel` validation and the generated draft 2020-12 JSON Schema.
  Unknown fields remain errors.
- Semantic validation: captured timestamps must parse as RFC 3339; content URI
  evidence must include a checksum; raw evidence must carry artifact content,
  URI content, or a bounded summary; redacted or withheld records must disclose
  loss in `raw_content.loss_disclosure`.
- Reference shape: use typed experiment references for capture specs, evidence
  records, tasks, runs, apparatus context, source references, and provenance.
  Do not encode reference kind or binding semantics in free-form strings.
- Manifest and vocabulary authority: backend observation claims must remain in
  `capabilities.observation`, must use governed vocabulary scopes, and must be
  falsifiable against the published experiment evidence contracts.
- API/auth surface: any future HTTP mutation or read path must use the existing
  control-plane identity and role checks. Mutating requests require backend or
  operator authority; read requests require backend, operator, or auditor
  authority.
- Request and idempotency surface: future HTTP paths must keep request-size
  guards, closed DTOs, idempotency keys, request fingerprints, and audit
  recording. Do not create an evidence-specific request pipeline.
- Secret-handling surface: evidence records carry sensitivity, redaction state,
  loss disclosure, content references, checksums, and provenance. They must not
  carry credentials, bearer tokens, private keys, hidden answer keys,
  environment dumps, backend-private object reprs, full tracebacks, or raw
  process argv. Runtime observed-value inputs must preserve the existing
  redaction helpers instead of bypassing them.
- Config/env-binding surface: EXP-708 must not introduce a new environment,
  config, or secret-binding shape. If evidence is derived from SDL/runtime
  configuration, use the existing runtime configuration, image provenance, and
  observed-value redaction validators; never serialize raw `os.environ`,
  process argv, or backend-local config objects into evidence records.
- OS-level exposure: command helpers and examples must not pass secrets,
  tokens, or large raw capture payloads through process arguments. Use content
  files or checked-in synthetic fixtures referenced by URI and checksum.
- Error-envelope surface: validation and runtime failures must use existing
  `Diagnostic` values or the existing redacted HTTP error pattern. Error
  details must not echo captured payloads, credentials, tracebacks, or backend
  internals.
- Persistence surface: do not place evidence records or raw captured payloads
  in `RuntimeSnapshot.metadata`, operation records, participant histories,
  audit details, or backend-private logs. Any future durable store must preserve
  schema-versioned evidence records and their checksum/redaction metadata.

## Extensibility Guardrail

The extension seam belongs in the evidence record's declared dimensions and in
the adjacent capture/capability contracts, not in a parallel evidence schema.
Preserve and extend `evidence_kind`, `source_refs`, `raw_content`,
`sensitivity`, `redaction_state`, and `provenance_refs`; use capture
specifications for capture windows and requirements; use
`capabilities.observation.supported_*` vocabularies for portable backend
capability claims. New portable evidence kinds or channel kinds require
contract-source and concept-authority changes, not ad hoc strings in API DTOs.
Future publication APIs should parameterize the content locator/sealing policy
that produces `content_uri` plus `content_checksum` or an `artifact_ref`;
storage backend details must not leak into the evidence-record contract.

## Gotchas And Anti-Patterns

- Do not treat a capture specification as proof that evidence was captured.
- Do not use participant observation envelopes, workflow histories, runtime
  snapshots, audit events, or backend log entries as substitutes for
  `experiment-evidence-record-v1`.
- Do not put metric ids, computed values, scores, evaluation decisions, or
  analysis summaries in raw evidence records.
- Do not use run evidence artifacts alone as the raw-evidence authority when a
  first-class evidence record is needed.
- Do not duplicate `raw_content`, checksum, redaction, reference, schema,
  validation, exception, logging, audit, or persistence logic.
- Do not hand-edit `contracts/schemas/`; update contract sources, regenerate,
  update the schema publication manifest when hashes change, and keep fixtures
  and tests aligned.
- Do not log or audit raw evidence payloads, backend-private objects, secrets,
  full tracebacks, or command lines used to collect evidence.
- Do not add new SDL root sections or scenario syntax for EXP-708 without a
  new ADR.

## Non-Goals

- Runtime capture, packet/log collection, telemetry streaming, retention, or
  chain-of-custody implementation.
- HTTP APIs, CLI ingestion, schedulers, workers, or background capture
  orchestration.
- Redaction execution, access-control policy engines, immutable object-store
  integration, or evidence deletion workflows.
- Derived-measure computation, evaluator behavior, score calculation,
  statistical analysis, or study comparison logic.
- Scenario-internal monitoring or logging configuration.
- New schemas, validators, exception hierarchies, persistence stores, or
  workflow logic beyond consuming the existing EXP-708 contract boundary.
