# Issue #105 EXP-706/EXP-712 Reproducibility And Replay Preflight Guardrails

Date: 2026-06-25

Issue: #105.

Requirements: EXP-706, EXP-712.

This preflight narrows the joint trial/replication and reproducibility/replay
design issue to the architecture boundary implementation must preserve. ADR-055,
ADR-064, ADR-065, ADR-066, and `specs/formal/experiment-core/README.md` remain
the design authority. This note is implementation guidance only.

## Architecture Decisions

- Treat reproducibility and replay as claim disciplines over preserved
  experiment context, evidence, provenance, and lineage. Do not add a parallel
  replay-run, replay-claim, or provenance-graph root schema unless a later ADR
  deliberately supersedes the current run-provenance boundary.
- Keep `experiment-run-v1` as the canonical archival join point for one task
  execution. It already carries task/scenario snapshot refs, apparatus context,
  participant implementation provenance, parameters, stochastic controls,
  clocks, timestamps, evidence artifacts, result summaries, run traceability,
  realized-form disclosures, augmentation disclosures, and generic lineage refs.
- Keep replay distinct from re-execution. A preserved run record can support a
  replay claim only by naming what context and evidence were sealed, what
  lineage was preserved, and what limitations, redactions, observer effects, or
  unsupported surfaces weaken the claim. It must not imply that ACES can execute
  a replay workflow, fetch external artifacts, or reproduce hidden backend state.
- Keep raw evidence, derived measures, and claims separate:
  `experiment-evidence-record-v1` is captured evidence,
  `experiment-derived-measure-v1` is interpreted output, and
  `experiment-run-v1.traceability.claim_refs` is a pointer to claim/report
  artifacts grounded by derived-measure refs.
- Treat trial, replication, cohort, and benchmark grouping as study/allocation
  concerns in `experiment-study-v1`, not as tags or duplicated run fields.
  Where grouped claims depend on repeated executions, use study membership,
  run allocation, factors, analysis plans, validity notes, and explicit
  inclusion criteria.
- EXP-712 does not implement runtime replay, capture storage, artifact
  dereference APIs, schedulers, statistical analysis, or a new persistence
  service. Later producers or APIs must emit and validate the existing
  contracts through the existing control-plane, diagnostics, redaction, audit,
  and idempotency gates.

## Required Incumbents

- Contract source:
  `implementations/python/packages/aces_contracts/contracts.py`, especially
  `ContractModel`, `ExperimentRunModel`, `ExperimentRunTraceabilityModel`,
  `ExperimentTaskModel`, `ExperimentStudyModel`, `ExperimentCaptureSpecModel`,
  `ExperimentEvidenceRecordModel`, `ExperimentDerivedMeasureModel`,
  `ExperimentApparatusContextModel`,
  `ExperimentRealizedFormDisclosureModel`,
  `ExperimentAugmentationDisclosureModel`, constrained experiment references,
  artifact refs, checksums, redaction-aware `ExperimentParameterModel`,
  stochastic controls, clock context, RFC 3339 parsing,
  `validate_experiment_run_against_task()`,
  `validate_experiment_apparatus_context_against_manifests()`, and
  `validate_experiment_study_against_tasks_and_runs()`.
- Published contract surface:
  `contracts/schemas/experiment-core/`, `contracts/fixtures/experiment-core/`,
  `contracts/schema-publication-manifest.json`,
  `implementations/python/packages/aces_contracts/versions.py`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, and `tools/check_json_artifacts.py`.
- Adjacent runtime and participant evidence surfaces:
  participant implementation manifest/provenance contracts, participant
  runtime history and observation contracts, runtime snapshot
  `realization_provenance`, workflow/evaluation result envelopes, structured
  `Diagnostic` values, and control-plane operation records. These are inputs or
  observation surfaces; they are not replacement archival run records.
- Manifest, capability, and vocabulary authority:
  `aces_contracts.manifest_authority`, processor/backend manifest models,
  backend observation capability declarations, controlled vocabularies, concept
  families such as `tasks-runs-studies`, `apparatus-declarations`,
  `provenance-and-evidence`, `realization-and-disclosure`, and
  `time-and-apparatus`.
- Runtime/API incumbents for future producer or retrieval work:
  `aces_runtime.control_plane_api`, `control_plane_api_guards`,
  `control_plane_security`, `control_plane_store`, request fingerprints,
  idempotency keys, audit events, response models, redacted FastAPI error
  handling, and runtime redaction/config validators.

## Whole-Repo Scope

- Repo workflow policy: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, and
  `tools/verify_all.py`.
- Design authority: ADR-055, ADR-064, ADR-065, ADR-066,
  `specs/formal/experiment-core/README.md`, and
  `specs/formal/observability-evidence-plane.md`.
- Contract publication authority: Pydantic contract source, generated schemas,
  fixtures, schema publication manifest, semantic invariant annotations, and
  schema drift checks.
- Concept and capability authority: concept-authority catalogs, manifest
  authority lists, backend/processor manifest payloads, backend protocol
  capability dataclasses, and observation capability gap checks.
- Runtime/API boundary for future work: control-plane auth, request-size guard,
  idempotency, audit store, diagnostics, redacted error envelopes, runtime
  redaction/config validators, and OS-level command exposure rules.

## Cross-Cutting Layers

- Structural validation: external payloads must pass closed-world
  `ContractModel` validation and the generated draft 2020-12 JSON Schemas.
  Unknown fields remain errors.
- Semantic validation: reuse the existing model validators for run time
  ordering, invalidation details, succeeded-result reporting, participant
  implementation provenance resolution, result evidence resolution,
  traceability uniqueness, realized-form evidence tracing, augmentation
  evidence tracing, derived-measure source evidence, and study allocation
  grounding.
- Cross-artifact validation: `validate_experiment_run_against_task()` remains
  the task/run gate for task identity, scenario snapshot compatibility,
  apparatus constraints, declared metrics, and evidence requirements.
  `validate_experiment_study_against_tasks_and_runs()` remains the grouped
  claim gate for membership, allocation, analysis metrics, invalidated-run
  exclusion, and condition coverage.
- Claim grounding: a run claim reference must be grounded by at least one
  derived-measure ref in `traceability`; derived measures must cite raw
  evidence-record refs; evidence records must cite capture specs and
  requirements. Do not accept claim refs that float free of this chain.
- Manifest and digest validation: use constrained experiment reference models
  and apparatus-context manifest validation. Digest-bound manifest refs are
  limited to processor/backend manifests whose payloads can be checked.
- Auth surface: future create/read/dereference APIs must use existing
  control-plane identity and role checks. Publishing replay/reproducibility
  metadata is a run-provenance mutation; dereferencing evidence content is a
  separate authorized read.
- Secret-handling surface: preserved context may include sensitivity-aware
  artifact references, checksums, redacted parameters, bounded summaries, and
  disclosure text. It must not include credentials, bearer tokens, private keys,
  hidden answers, raw prompts, environment dumps, backend-private object
  reprs, full tracebacks, raw process argv, or unredacted capture payloads.
- Config/env-binding surface: configuration provenance must use existing
  redaction-aware experiment parameters, runtime configuration shapes, and
  observed-value redaction helpers. Never serialize raw `os.environ`, CLI argv,
  process tables, or backend-local config objects into run, study, evidence,
  diagnostics, audit, fixture, or example payloads.
- OS-level exposure: producers, validation helpers, and examples must not pass
  tokens, secrets, or large raw evidence payloads through command-line
  arguments. Use content-addressed artifacts, files, URIs, checksums, and
  synthetic fixtures.
- Error-envelope surface: validation and runtime failures must use Pydantic
  validation errors, existing `Diagnostic` values, or existing redacted HTTP
  error envelopes. Do not echo full run records, evidence payloads, secrets,
  tracebacks, or backend internals.
- Persistence surface: do not store reproducibility or replay records in
  `RuntimeSnapshot.metadata`, operation status, workflow history, participant
  history, audit details, free-form tags, or backend-private logs. A future
  durable store must preserve schema-versioned experiment artifacts and their
  references intact.

## Extensibility Guardrail

The extension seam is the existing claim-support graph, not a new replay stack.
Future variation should extend governed dimensions such as study kind/allocation
metadata, `ExperimentReferenceModel.ref_kind`, run `traceability`, evidence
record kinds, derived-measure method metadata, realized-form and augmentation
classifications, artifact roles, manifest capability declarations, or
concept-authority terms. Producer code should be parameterized by source
surface, replay/claim strength, artifact locator, sealing policy, and redaction
policy so future backends can emit the same canonical contracts without leaking
backend-native state into the archival model.

## Gotchas And Anti-Patterns

- Do not introduce a generic `replay_record`, `reproducibility_claim`, or
  provenance graph schema that duplicates `experiment-run-v1`,
  `experiment-study-v1`, evidence records, or derived measures.
- Do not confuse replayability with successful re-execution. Claim strength must
  be limited by preserved context, artifact availability, redaction, loss,
  observer effects, and unsupported runtime surfaces.
- Do not reconstruct archival run or claim support lazily from mutable
  control-plane state, runtime snapshots, operation statuses, participant
  histories, audit logs, or backend-private logs.
- Do not treat capture specs, evidence-record refs, derived-measure refs, or
  claim refs as proof that external artifacts exist or are authorized for
  dereference.
- Do not use tags, free-form notes, evaluator `detail`, `RuntimeSnapshot`
  metadata, backend-native IDs, operation ids, workflow ids, participant
  episode ids, or snapshot addresses as portable trial, replication, run, or
  claim identity.
- Do not duplicate schema registries, validation helpers, exception
  hierarchies, logging stacks, audit formats, storage stacks, manifest
  renderers, or workflow logic.
- Do not hand-edit `contracts/schemas/`; update contract sources, regenerate,
  update the publication manifest when hashes change, and keep fixtures and
  tests aligned.

## Non-Goals

- Runtime replay execution, replay scheduling, capture orchestration, artifact
  retrieval, retention storage, query services, or HTTP APIs.
- New root schemas for replay, reproducibility claims, provenance graphs,
  trial records, or replication records.
- Statistical analysis, evaluator behavior, score calculation, derived-measure
  computation, or study comparison algorithms.
- SDL syntax changes, new SDL root sections, or changes to participant runtime
  semantics.
- New exception hierarchy, auth model, secret-handling surface, persistence
  stack, logging stack, audit stack, manifest renderer, or workflow pipeline.
