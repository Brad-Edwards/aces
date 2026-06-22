# Issue #235 EXP-709 Derived Measure Preflight Guardrails

Date: 2026-06-22

Issue: #235.

Requirement: EXP-709.

This preflight narrows the issue #88 evidence and measure boundary to derived
measures, evaluations, scores, summaries, and comparable analysis outputs for
EXP-709. ADR-064 and `specs/formal/experiment-core/README.md` remain the
normative design authority. This note is guidance for implementation only.

## Architecture Decisions

- Treat `experiment-derived-measure-v1` as the first-class interpreted output
  surface computed from raw evidence records.
- Keep derived measures distinct from `experiment-evidence-record-v1` raw
  captured evidence, `experiment-capture-spec-v1` capture intent,
  `experiment-run-v1` result summaries, study analysis plans, live evaluation
  result envelopes, participant outcome reports, and backend-private evaluator
  details.
- Every derived measure must cite one or more evidence-record refs, a metric or
  evaluation reference, derivation method metadata, generation time, value
  status, optional reported value, uncertainty, limitations, and provenance.
- The reported value is the interpreted result, not a raw payload container. Do
  not use `value`, `limitations`, or `provenance_refs` to inline raw evidence,
  backend logs, tracebacks, hidden answer keys, or large analysis artifacts.
- EXP-709 does not implement measure computation, statistical analysis,
  evaluator behavior, storage, APIs, schedulers, workers, or study comparison
  workflows. Later work may compute or publish measures, but must use the
  existing contract and control-plane gates.

## Required Incumbents

- Contract source:
  `implementations/python/packages/aces_contracts/contracts.py`, especially
  `ContractModel`, `ExperimentDerivedMeasureModel`,
  `ExperimentDerivedMeasureMethodModel`, `ExperimentParameterModel`,
  `ExperimentEvidenceRecordReferenceModel`,
  `ExperimentDerivedMeasureReferenceModel`, `ExperimentReferenceModel`, RFC
  3339 date-time parsing, reported-value-status validation, and
  `schema_bundle()`.
- Published contract surface:
  `contracts/schemas/experiment-core/experiment-derived-measure-v1.json`,
  `contracts/fixtures/experiment-core/experiment-derived-measure-v1/`,
  `contracts/schema-publication-manifest.json`, and
  `tools/generate_contract_schemas.py`.
- Validation and conformance:
  `implementations/python/tests/test_runtime_contracts.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_json_artifacts.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, and `tools/verify_all.py`.
- Adjacent boundaries:
  `experiment-evidence-record-v1` for source observations,
  `experiment-capture-spec-v1` for capture requirements,
  `experiment-run-v1` traceability for capture/evidence/measure/claim links,
  `ExperimentResultSummaryModel` for compact run-level result summaries, and
  `experiment-study-v1` for analysis plans and comparison grouping.
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
- Normative design authority: ADR-064, ADR-055, ADR-065, and
  `specs/formal/experiment-core/README.md`.
- Contract publication authority: contract source, generated schemas, fixtures,
  schema publication manifest, and schema drift/publication checks.
- Concept and capability authority: concept-authority vocabularies, backend
  manifest authority lists, backend protocol capability dataclasses, manifest
  renderers, and observation capability gap checks.
- Runtime/API boundary for future work: control-plane auth, request guards,
  idempotency, audit store, diagnostics, redacted error envelopes, existing
  runtime redaction/config validators, and OS-level command exposure rules.

## Cross-Cutting Layers

- Structural validation: external derived-measure payloads must pass
  closed-world `ContractModel` validation and the generated draft 2020-12 JSON
  Schema. Unknown fields remain errors.
- Semantic validation: `source_evidence_refs` must contain at least one
  `evidence-record` ref; `generated_at` must parse as RFC 3339; reported
  measures must include `value`; missing, withheld, and not-applicable measures
  must not include `value`.
- Reference shape: use typed experiment references for metric/evaluation refs,
  source evidence refs, derived-measure refs, and provenance. Do not encode
  reference kind, source binding, or derivation identity in free-form strings
  when a typed reference or method field exists.
- Manifest and vocabulary authority: backend observation claims must remain in
  `capabilities.observation`, must use governed vocabulary scopes, and must be
  falsifiable against the published experiment capture, evidence, and derived
  measure contracts.
- API/auth surface: any future HTTP mutation or read path must use the existing
  control-plane identity and role checks. Mutating requests require backend or
  operator authority; read requests require backend, operator, or auditor
  authority.
- Request and idempotency surface: future HTTP paths must keep request-size
  guards, closed DTOs, idempotency keys, request fingerprints, and audit
  recording. Do not create a measure-specific request pipeline.
- Secret-handling surface: derived measures carry interpreted values, method
  metadata, uncertainty, limitations, source evidence refs, and provenance.
  They must not carry credentials, bearer tokens, private keys, hidden answer
  keys, environment dumps, backend-private object reprs, raw evidence payloads,
  full tracebacks, or raw process argv. If a source value is sensitive, keep it
  in the evidence-record path with sensitivity/redaction metadata and publish
  only a bounded, reviewable derived result.
- Config/env-binding surface: EXP-709 must not introduce a new environment,
  config, or secret-binding shape. Method parameters use the existing
  redaction-aware `ExperimentParameterModel`; never serialize raw `os.environ`,
  process argv, or backend-local config objects into derived measures.
- OS-level exposure: command helpers and examples must not pass secrets,
  tokens, raw evidence payloads, or large analysis outputs through process
  arguments. Use content references, checked-in synthetic fixtures, and
  checksums where artifacts are needed.
- Error-envelope surface: validation and runtime failures must use existing
  `Diagnostic` values or the existing redacted HTTP error pattern. Error
  details must not echo raw evidence, credentials, computed hidden truth,
  tracebacks, or backend internals.
- Persistence surface: do not place derived measures or raw analysis outputs in
  `RuntimeSnapshot.metadata`, operation records, participant histories, audit
  details, or backend-private logs. Any future durable store must preserve
  schema-versioned derived-measure records and their source-evidence links.

## Extensibility Guardrail

The extension seam belongs in the existing derived-measure dimensions, not in a
parallel score, evaluation, summary, or analysis-output schema. Preserve and
extend `measure_kind`, `metric_ref`, `method.method_id`,
`method.method_version`, `method.parameters`, `source_evidence_refs`,
`value_status`, `value`, `uncertainty`, `limitations`, and `provenance_refs`.
New portable measure kinds, value envelopes, sensitivity markings, or method
taxonomies require contract-source and schema-publication changes. Backend or
study-specific variation should be parameterized through method metadata and
typed refs rather than by adding ad hoc API DTO fields or evaluator-private
payloads.

## Gotchas And Anti-Patterns

- Do not treat a derived measure as raw evidence or proof of capture.
- Do not let a run result summary become the canonical derived-measure record;
  it may summarize a result, but the reviewable derivation chain belongs in
  `experiment-derived-measure-v1` plus run traceability.
- Do not put raw observations, logs, packet captures, traces, screenshots,
  backend-native evaluator payloads, or participant-private data in the
  derived-measure `value`.
- Do not collapse capture specs, evidence records, derived measures, run
  summaries, participant outcome reports, and study analysis plans into a
  single result blob.
- Do not duplicate reported-value-status validation, reference validation,
  timestamp parsing, schema generation, fixture loading, exception handling,
  logging, audit, or persistence logic.
- Do not hand-edit `contracts/schemas/`; update contract sources, regenerate,
  update the schema publication manifest when hashes change, and keep fixtures
  and tests aligned.
- Do not add new SDL root sections, evaluator APIs, analysis services, storage
  backends, or workflow steps for EXP-709 without a separate design decision.

## Non-Goals

- Measure computation, evaluator behavior, score calculation, statistical
  analysis, model evaluation engines, or study comparison logic.
- Runtime capture, packet/log collection, telemetry streaming, retention,
  redaction execution, or chain-of-custody implementation.
- HTTP APIs, CLI ingestion, schedulers, workers, background analysis jobs, or
  durable publication stores.
- Scenario-internal monitoring, logging, scoring, objective, or task syntax.
- New schemas, validators, exception hierarchies, persistence stores, or
  workflow logic beyond consuming the existing EXP-709 contract boundary.
