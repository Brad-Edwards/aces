# Issue #233 EXP-707 Capture Specification Preflight Guardrails

Date: 2026-06-22

Issue: #233.

Requirement: EXP-707.

This preflight narrows the issue #88 evidence and measure boundary to the
capture-specification work for EXP-707. ADR-064 and
`specs/formal/experiment-core/README.md` remain the normative design authority.
This note is guidance for implementation only.

## Architecture Decisions

- Treat `experiment-capture-spec-v1` as declarative intent: it records what
  evidence should be captured, over what scope and window, with sensitivity,
  integrity, retention, redaction, and loss-disclosure expectations.
- Keep capture specifications distinct from scenario-internal logging,
  monitoring setup, raw evidence records, derived measures, run summaries, and
  backend observation capability claims.
- Reuse the existing schema-first contract surface in
  `aces_contracts.contracts`; do not add a second capture-spec schema, parser,
  registry, or validation stack.
- Keep EXP-707 out of live runtime state. A capture spec may reference a task,
  run, apparatus context, participant, backend, processor, network, or service
  scope, but it must not mutate `RuntimeSnapshot`, `ControlPlaneStore`, or
  scenario runtime configuration.
- Future capture backends, retention stores, APIs, and capture success records
  are separate work. EXP-707 is only the specification surface.

## Required Incumbents

- Contract source:
  `implementations/python/packages/aces_contracts/contracts.py`, especially
  `ContractModel`, `ExperimentCaptureSpecModel`,
  `ExperimentCaptureRequirementModel`, `ExperimentCaptureWindowModel`,
  `ExperimentMeasurementChannelReferenceModel`, and
  `ExperimentReferenceModel`.
- Published schemas:
  `schema_bundle()`, `tools/generate_contract_schemas.py`,
  `contracts/schemas/experiment-core/experiment-capture-spec-v1.json`, and
  `contracts/schema-publication-manifest.json`.
- Fixture and conformance corpus:
  `contracts/fixtures/experiment-core/experiment-capture-spec-v1/` and the
  experiment-core schema tests in `implementations/python/tests/`.
- Semantic invariants:
  `x-aces-invariants` entries for capture requirement key equality, capture
  window resolution, and capture window time ordering.
- Adjacent concept boundaries:
  `experiment-evidence-record-v1` for raw captured evidence,
  `experiment-derived-measure-v1` for interpreted outputs,
  `experiment-run-v1` evidence artifacts for archival run summaries, and
  `backend-manifest-v2` `capabilities.observation` for backend support claims.
- If any API surface is added later:
  `aces_runtime.control_plane_api`, `control_plane_api_guards`,
  `control_plane_security`, request fingerprints, audit events, response
  models, and redacted error handling.

## Cross-Cutting Layers

- Structural validation: every external payload must pass closed-world
  Pydantic `ContractModel` validation and the generated draft 2020-12 JSON
  Schema. Unknown fields remain errors.
- Semantic validation: capture requirement map keys must match embedded
  `requirement_id` values; every `window_refs` value must resolve to a
  declared capture window; each window must declare a start, end, or trigger;
  and windows with both timestamps must not end before they start.
- Reference shape: use typed `ExperimentReferenceModel` variants and existing
  reference-kind constraints. Do not encode scope or channel meaning in
  free-form strings when a typed reference already exists.
- Security and redaction: capture specs may declare sensitivity, redaction
  policy, retention policy, and loss-disclosure expectations, but must not
  carry real credentials, bearer tokens, private keys, environment dumps, raw
  process argv, backend-private payloads, or full tracebacks in fields,
  fixtures, diagnostics, logs, or examples.
- API/auth surface: if a capture-spec endpoint is later introduced, mutating
  requests must use the existing control-plane identity and role checks,
  request-size guard, idempotency fingerprint, audit logging, closed DTOs, and
  redacted FastAPI error envelope. Do not create a capture-specific auth or
  error stack.
- Persistence: do not put capture specs in `RuntimeSnapshot.metadata`, operation
  records, participant histories, or backend-private logs. Any future durable
  store must preserve schema-versioned artifacts and avoid treating the current
  in-memory control-plane store as archival experiment persistence.
- OS-level exposure: command-line helpers and examples must not pass secrets or
  captured raw payloads through process arguments. Use checked-in fixtures with
  synthetic data and content references with checksums.
- Governance: schema changes must update the contract source, regenerate
  schemas through `schema_bundle()`, preserve fixture coverage, and update the
  schema publication manifest when published schema hashes change.

## Extensibility Guardrail

The extension point belongs in declared capture dimensions, not in new
parallel surfaces. Preserve and extend the existing parameters:
`capture_kind`, `capture_scope`, `channel_ref`, `window_refs`,
`expected_media_types`, `required_artifact_roles`, `sensitivity`,
`redaction_policy`, `integrity_requirements`, `retention_policy`, and
`loss_disclosure_required`. New portable vocabulary should go through concept
authority only when comparison or backend capability claims depend on bounded
terms.

## Gotchas And Anti-Patterns

- Do not treat a capture spec as proof that evidence was captured.
- Do not put metric values, scores, evaluation decisions, or derived summaries
  in a capture spec.
- Do not collapse capture specs, evidence records, and derived measures into a
  single blob.
- Do not duplicate task observation requirements or run evidence artifacts as a
  second source of truth. Capture specs may reference those artifacts or
  requirements but must not redefine their contracts.
- Do not infer capture scope from scenario logging configuration, monitoring
  declarations, backend defaults, or participant observation history.
- Do not add new SDL root sections or scenario syntax for EXP-707 without a new
  ADR.
- Do not hand-edit `contracts/schemas/`.
- Do not create new exception hierarchies, logging stacks, audit formats,
  schema registries, persistence stores, or workflow logic for this issue.

## Non-Goals

- Runtime evidence capture, packet/log collection, telemetry streaming, and
  storage retention implementation.
- HTTP APIs, schedulers, workers, or background capture orchestration.
- Raw evidence publication, redaction execution, loss accounting, chain of
  custody, and derived-measure computation.
- Statistical analysis, evaluator behavior, score calculation, or study
  comparison logic.
- Scenario-internal monitoring or logging configuration.
- Backend capability declaration beyond consuming the existing
  `capabilities.observation` boundary where relevant.
