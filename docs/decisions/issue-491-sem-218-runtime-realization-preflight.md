# Issue 491 SEM-218 Runtime Realization Preflight

Date: 2026-06-15

Issue: #491.

Requirement: none. The issue title, body, and acceptance criteria are the
contract.

This note records architecture preflight guardrails for closing the last
SEM-218 realization gaps: the runtime non-approximation gate and provenance
fields on runtime envelopes. It is guidance for the implementation and does
not implement the gate, schemas, fixtures, or spec updates.

## Binding Sources

- `specs/formal/realization/explicitness-and-realization.md` is the normative
  SEM-218 authority for I1-I5.
- ADR-008 separates processor work from backend realization and live runtime
  state; the processor compiles and plans, while the backend realizes.
- ADR-009, ADR-019, ADR-061, `contracts/schema-publication-manifest.json`, and
  `contracts/README.md` define schema authority and publication review.
- ADR-012 and `contracts/concept-authority/concept-families-v1.json` define
  the `realization-and-disclosure` concept family and extension discipline.
- ADR-054 and ADR-060 define participant runtime envelope discipline and keep
  participant support strength distinct from SEM-218 realization support.
- The existing issue #76 preflight note under
  `docs/research/participant-backend-contracts/preflight-guardrails.md`
  remains the guardrail for participant backend carriers and control-plane
  security.

## Architecture Decisions

- The runtime non-approximation gate belongs at the backend adapter contract
  boundary, before a backend-returned `ApplyResult.snapshot` is accepted into
  `RuntimeManager` state or control-plane persistence.
- The gate must build on the compiled requirements already emitted by
  `RuntimeModel.realization_requirements` and matched by
  `realization_support_diagnostics()`. Do not reclassify SDL declarations,
  reinterpret authored values, or add a second exactness taxonomy at runtime.
- The gate should consume a runtime realization context passed down from the
  `ExecutionPlan`, not global state. That context should be parameterized by
  realization `domain`, `requirement_kind`, `field_path`, `address`, and
  `explicitness` so future SEM-218 concern kinds can reuse the same boundary.
- Missing runtime provenance for a compiled exact requirement is a contract
  failure, not a best-effort warning. A backend that reports a weaker
  realization for an exact declaration must fail through the existing
  `runtime.backend-contract-invalid` diagnostic surface.
- Provenance is per realized concern or value, not a scalar property of a whole
  snapshot. If multiple envelopes need the same fields, define one shared
  contract component in `aces_contracts.contracts` and reuse it instead of
  adding divergent per-envelope shapes.
- The provenance fields must distinguish SEM-218 explicitness/provenance from
  ADR-054 lifecycle `phase_realization`, API-407 participant feature support,
  actor provenance, mapping loss, evidence refs, and control-plane operation
  state. Those concepts are adjacent but not interchangeable.
- Published schemas remain the language-neutral contract. Any envelope shape
  change must update `contracts/schemas/`, `schema_bundle()`,
  fixtures, and the publication manifest through the existing schema
  authority pipeline.

## Required Incumbents

- SEM-218 classifier and compiler: `aces_sdl.explicitness`,
  `aces_processor.compiler._compile_realization_requirements`,
  `aces_processor.models.RuntimeModel.realization_requirements`, and
  `aces_processor.semantics.realization`.
- Backend manifest declaration: `RealizationSupportMode`,
  `RealizationSupportDeclaration`,
  `RealizationSupportDeclarationModel`, `BackendManifestV2Model`, and backend
  manifest fixtures.
- Runtime adapter boundary: `aces_runtime.backend_calls._call_backend_apply`,
  `_snapshot_contract_diagnostics()`, `RuntimeManager.apply()`, and
  `ApplyResult` / `RuntimeSnapshot`.
- Existing result validators:
  `workflow_result_contract_diagnostics()`,
  `evaluation_result_contract_diagnostics()`,
  `participant_runtime_state_contract_diagnostics()`, and
  `participant_runtime_history_transition_diagnostics()`.
- Published contract models and schemas:
  `ContractModel`, `RuntimeSnapshotEnvelopeModel`,
  `WorkflowExecutionStateModel`, `WorkflowHistoryEventModel`,
  `EvaluationResultStateModel`, `EvaluationHistoryEventModel`,
  participant episode/behavior history models, participant runtime base
  envelopes, `schema_bundle()`, and `tools/generate_contract_schemas.py`.
- Control-plane serialization and exposure: `ControlPlaneStore`,
  `_snapshot_payload()`, `_snapshot_from_payload()`, `_snapshot_model()`,
  `RuntimeSnapshotEnvelopeModel`, and `aces_conformance.conformance`.
- Verification and policy: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_json_artifacts.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL validation layer: exact/constrained/open classification must come from
  the existing closed-model parser, `SemanticValidator`, and
  `aces_sdl.explicitness`. Runtime code must not infer explicitness from raw
  payload values.
- Manifest/config layer: backend realization support still passes through
  `RealizationSupportDeclaration` shape validation, controlled-vocabulary and
  concept-binding checks, manifest version allowlists, and backend profile
  conformance. Do not add backend-local realization flags outside the manifest
  contract.
- Backend adapter layer: `_call_backend_apply()` is the fail-closed point for
  invalid backend return values. New SEM-218 failures should be ordinary
  `Diagnostic` instances with code `runtime.backend-contract-invalid`, leaving
  rollback and manager behavior on the existing path.
- Persistence layer: snapshots and histories move through `ControlPlaneStore`
  JSON-like payloads and the published runtime snapshot schema. New fields must
  round-trip through those serializers; do not create a sidecar persistence
  store for realization provenance.
- HTTP/auth layer: if the fields are visible through the control-plane API,
  they inherit `ControlPlaneSecurityConfig`, role checks, request-size limits,
  audit recording, and redacted FastAPI 500 envelopes. No new unauthenticated
  read surface is part of this issue.
- Error-envelope layer: diagnostics should name addresses, field paths,
  requirement kinds, and disclosure refs. They must not echo exact authored
  values, backend-native objects, raw payload bodies, environment dumps,
  bearer tokens, private keys, or stack traces.
- Schema and fixture layer: valid fixtures must exercise the new provenance
  fields on every affected published contract; invalid fixtures must fail
  schema/model validation for missing or contradictory provenance. Use the
  existing `contracts/fixtures/<family>/<contract>/valid|invalid` layout.
- OS/process exposure layer: this work should not introduce command-line
  passing of exact values or secrets. Use fixed-argv repo tools and existing
  nox/uv commands; do not put tokens or exact declaration values in process
  argv, logs, audit details, fixtures, or publication metadata.

## Extension Boundary

The extensibility seam is the runtime realization context plus a shared
provenance entry shape keyed by contract-local field/ref paths and realization
domain/kind strings. Future exact-requirement kinds, constraint kinds, or
governed vocabularies should extend those parameters and the concept-authority
catalog, not add new adapter-specific gates or envelope-specific provenance
schemas.

If the implementation needs a temporary string field before a governed
vocabulary exists, keep it opaque, non-empty, and disclosure-focused. Do not
pretend the field is a closed portable vocabulary until the concept-authority
artifact owns it.

## Gotchas And Anti-Patterns

Avoid:

- duplicating SEM-218 classification logic in runtime code;
- treating a successful planner gate as sufficient proof that the backend
  realized exact requirements exactly;
- treating `OPEN_REALIZATION`, `CONSTRAINED`, API-407 support strength, or
  ADR-054 `phase_realization` as permission to weaken an exact declaration;
- putting provenance only in `RuntimeSnapshot.metadata` or generic `details`
  maps when a first-class envelope field is required;
- adding per-envelope field names with subtly different meanings;
- adding a second schema registry, fixture loader, conformance runner,
  exception hierarchy, audit log, or persistence store;
- hand-waving schema changes with generated Python output but no publication
  manifest `last_change` ledger;
- exposing exact values, secrets, hidden truth, backend-private object
  representations, or raw validation payloads in diagnostics or fixtures;
- rewriting accepted ADRs in place for this issue without ADR-059 amendment
  handling.

## Non-Goals

- Implementing the runtime gate, provenance contract fields, schema
  regeneration, fixtures, or tests in this preflight note.
- Adding SDL authoring syntax or new realization concern authorities beyond
  what SEM-218 and the issue require.
- Redesigning backend manifests, processor manifests, participant feature
  support, participant episode lifecycle, workflow/evaluation result
  semantics, or control-plane authentication.
- Creating new archival experiment semantics beyond carrying the SEM-218
  provenance fields on any evidence envelopes the implementation explicitly
  changes.
- Merging or closing the PR, changing `main`, or bypassing existing Ground
  Control policy gates.
