# Issue #238 EXP-720 Run Provenance Preflight Guardrails

Date: 2026-06-22

Issue: #238.

Requirement: EXP-720.

This preflight narrows ADR-065 to the canonical run provenance record for
EXP-720. ADR-065 and `specs/formal/experiment-core/README.md` remain the
design authority. This note is implementation guidance only.

## Architecture Decisions

- Treat `experiment-run-v1` as the only canonical archival run provenance
  record. Do not add `experiment-run-provenance-v1` or a second run root.
- Keep archival run provenance distinct from live execution state:
  `RuntimeSnapshot`, `ControlPlaneStore`, operation status, workflow/evaluation
  histories, participant episode state, audit events, and backend-private logs
  are evidence inputs or operational views, not the authoritative run record.
- Preserve the existing run record split: task and scenario references,
  apparatus context, participant implementation provenance, parameter set,
  stochastic controls, timestamps, result summaries, evidence artifacts,
  traceability, realized-form disclosures, and lineage references each keep
  their current meanings.
- Manifest references and digests must use `ExperimentManifestReferenceModel`
  and apparatus-context manifest validation. Digest-bound manifest refs are
  limited to processor/backend manifests whose payloads can be checked.
- Configuration, parameter, and stochastic-control fields are bounded archival
  declarations. They must not serialize raw environments, process argv,
  backend-native config objects, bearer tokens, credentials, private keys, or
  unredacted secret material.
- EXP-720 does not implement capture execution, storage, HTTP APIs, schedulers,
  runtime state reconstruction, replay, statistical analysis, or a provenance
  graph service. Later producer or API work must emit the existing
  `ExperimentRunModel` shape through the existing gates.

## Required Incumbents

- Contract source:
  `implementations/python/packages/aces_contracts/contracts.py`, especially
  `ContractModel`, `ExperimentRunModel`, `ExperimentRunTraceabilityModel`,
  `ExperimentRealizedFormDisclosureModel`, `ExperimentApparatusContextModel`,
  `ParticipantImplementationProvenanceModel`, `ExperimentReferenceModel`,
  constrained reference models, artifact refs, checksums, parameters,
  stochastic controls, clock context, RFC 3339 parsing, and
  `validate_experiment_run_against_task()`.
- Published contract surface:
  `contracts/schemas/experiment-core/experiment-run-v1.json`,
  `contracts/fixtures/experiment-core/experiment-run-v1/`,
  `contracts/schema-publication-manifest.json`,
  `implementations/python/packages/aces_contracts/versions.py`, and
  `tools/generate_contract_schemas.py`.
- Adjacent experiment artifacts:
  `experiment-task-v1`, `experiment-apparatus-context-v1`,
  `experiment-capture-spec-v1`, `experiment-evidence-record-v1`,
  `experiment-derived-measure-v1`, `experiment-study-v1`, and
  participant implementation manifest/provenance contracts.
- Manifest and concept authority:
  `aces_contracts.manifest_authority`, processor/backend manifest models,
  backend observation capability declarations, controlled vocabularies,
  concept families `tasks-runs-studies`, `apparatus-declarations`,
  `provenance-and-evidence`, `realization-and-disclosure`, and
  `time-and-apparatus`.
- Validation and conformance:
  `implementations/python/tests/test_runtime_contracts.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_json_artifacts.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, and `tools/verify_all.py`.
- If a future producer reads live runtime surfaces:
  `aces_runtime.control_plane`, `control_plane_store`, result/history models,
  structured `Diagnostic` values, and the runtime snapshot
  `realization_provenance` ledger are inputs only. They do not become archival
  persistence or schema authority.
- If a future API publishes or retrieves run records:
  `aces_runtime.control_plane_api`, `control_plane_api_guards`,
  `control_plane_security`, request fingerprints, idempotency keys, audit
  events, response models, and redacted FastAPI error handling must be reused.
- If run records are derived from runtime configuration:
  `RuntimeEnvironmentVariable`, runtime sensitivity classifications, and the
  observed-value redaction helpers in `aces_sdl.runtime_values` remain the
  secret-handling gate.

## Whole-Repo Scope

- Repo workflow policy: `.ground-control.yaml`, `.gc/plan-rules.md`, and the
  repo policy and verification scripts.
- Normative design authority: ADR-055, ADR-064, ADR-065, ADR-008, and
  `specs/formal/experiment-core/README.md`.
- Contract publication authority: contract source, generated schemas, fixtures,
  schema publication manifest, semantic invariant annotations, and schema drift
  checks.
- Concept and capability authority: concept-authority catalogs, manifest
  authority lists, backend/processor manifest payloads, backend protocol
  capability dataclasses, and observation capability gap checks.
- Runtime/API boundary for future work: control-plane auth, request-size guard,
  idempotency, audit store, diagnostics, redacted error envelopes, and existing
  runtime redaction/config validators.

## Cross-Cutting Layers

- Structural validation: external run payloads must pass closed-world
  `ContractModel` validation and the generated draft 2020-12 JSON Schema.
  Unknown fields remain errors.
- Semantic validation: `ExperimentRunModel._validate_archival_run()` enforces
  time ordering, invalidation details, succeeded-result reporting, participant
  implementation provenance resolution, result evidence resolution, and
  realized-form evidence tracing.
- Cross-artifact validation: `validate_experiment_run_against_task()` checks
  task identity/version, scenario snapshot compatibility, apparatus
  constraints, task-declared metric ids, and task/metric evidence requirements.
- Traceability validation: `ExperimentRunTraceabilityModel` requires
  duplicate-free capture-spec, evidence-record, derived-measure, and claim
  refs; claim refs must be grounded by at least one derived-measure ref.
- Realized-form validation: `ExperimentRealizedFormDisclosureModel` requires a
  realized reference or value summary, enforces processor/backend realization
  authority for matching bases, and keeps disclosure evidence refs unique.
- Manifest and digest validation: `ExperimentManifestReferenceModel` constrains
  digest-bound manifest refs to processor/backend subject refs with supported
  manifest schema versions. Apparatus context validators must bind selected
  manifests to concrete processor/backend payloads.
- Concept and vocabulary validation: portable comparison terms must come from
  existing concept-authority and manifest-authority helpers, not ad hoc local
  strings.
- API/auth surface: any future HTTP mutation or read path must use existing
  control-plane identity and role checks. Mutating requests require backend or
  operator authority; read requests require backend, operator, or auditor
  authority.
- Request and idempotency surface: future HTTP paths must keep request-size
  guards, closed DTOs, idempotency keys, request fingerprints, and audit
  recording. Do not create a run-provenance-specific request pipeline.
- Secret-handling surface: run records may carry sensitivity-aware artifact
  references, checksums, bounded summaries, and redaction disclosures. They must
  not carry credentials, bearer tokens, private keys, hidden answer keys, raw
  prompt contents, environment dumps, backend-private object reprs, full
  tracebacks, raw process argv, or raw backend payloads.
- Config/env-binding surface: configuration provenance must use existing
  runtime configuration and observed-value redaction shapes. Never serialize
  raw `os.environ`, CLI argv, process tables, or backend-local config objects
  into `parameter_set`, `apparatus_context`, evidence artifacts, diagnostics,
  audit details, fixtures, or examples.
- OS-level exposure: collection and publication helpers must not pass tokens,
  credentials, or large raw capture payloads through command-line arguments.
  Use content files or synthetic fixtures referenced by URI and checksum.
- Error-envelope surface: validation and runtime failures must use existing
  `Diagnostic` values, Pydantic validation errors, or the existing redacted HTTP
  error pattern. Error details must not echo record payloads, secrets,
  tracebacks, or backend internals.
- Persistence surface: archival run records must not be stored in
  `RuntimeSnapshot.metadata`, operation records, participant histories, audit
  details, or backend-private logs. Any future durable store must persist
  schema-versioned `experiment-run-v1` records with their evidence and
  traceability references intact.

## Extensibility Guardrail

The extension seam is inside the existing run contract and adjacent evidence
contracts, not in a parallel provenance schema. Future variation should extend
governed dimensions such as `traceability`, `realized_form_disclosures`,
`ExperimentReferenceModel.ref_kind`, `ExperimentArtifactRefModel.role`,
manifest/capability vocabularies, or capture/evidence/derived-measure
contracts. Publication or retrieval code should parameterize the producer
source and artifact locator/sealing policy that produce refs, URIs, checksums,
and redaction disclosures; storage or backend details must not leak into the
canonical run record.

## Gotchas And Anti-Patterns

- Do not reconstruct the archival run lazily from mutable control-plane state.
- Do not treat `run_id`, operation id, workflow run id, participant episode id,
  snapshot address, or backend-native execution id as interchangeable.
- Do not put archival run provenance into `RuntimeSnapshot.metadata`,
  operation status, workflow history, participant history, audit logs, or
  backend-private logs.
- Do not create duplicate provenance schemas, schema registries, validators,
  exception hierarchies, workflow logic, manifest renderers, storage stacks,
  logging stacks, or audit stacks.
- Do not use `realized_form_disclosures` as an unstructured log field.
- Do not treat traceability refs as proof that external artifacts exist or are
  authorized for dereference. Dereference belongs to future storage/API work
  using existing auth, redaction, request-size, audit, and idempotency gates.
- Do not hand-edit `contracts/schemas/`; update contract sources, regenerate,
  update the schema publication manifest when hashes change, and keep fixtures
  and tests aligned.
- Do not make processor identity explicit while backend or participant
  implementation identity stays implicit.
- Do not store secrets or backend-private payloads in parameters,
  configuration, evidence summaries, diagnostics, logs, fixtures, or examples.

## Non-Goals

- New root schema or alternative canonical provenance artifact.
- Runtime capture, replay, storage, retention, API, or query implementation.
- Live-state store changes, control-plane workflow changes, schedulers, workers,
  or background capture orchestration.
- Statistical analysis, derived-measure computation, evaluator behavior, or
  study comparison logic.
- Scenario syntax, SDL root sections, or task model changes.
- New exception hierarchy, logging/audit pipeline, persistence stack, manifest
  renderer, or validation stack.
