# Issue #239 EXP-722 Realized Form Disclosure Preflight Guardrails

Date: 2026-06-22

Issue: #239.

Requirement: EXP-722.

This preflight narrows ADR-065 to realized-form disclosure. ADR-065 and
`specs/formal/experiment-core/README.md` remain the design authority. This note
is implementation guidance only.

## Architecture Decisions

- Preserve realized forms inside `experiment-run-v1`
  `realized_form_disclosures`; do not create a parallel realized-form,
  apparatus-realization, or run-provenance root schema.
- Treat each disclosure as run provenance for an underspecified concern, not as
  authored SDL meaning, apparatus context alone, raw evidence, derived measure
  output, result summary, runtime snapshot metadata, or backend-private log
  data.
- Keep the existing disclosure shape: stable concern id, governed concern kind,
  realization basis, realizing authority reference, optional authored reference,
  realized reference or bounded value summary, disclosure text, and optional
  evidence-record refs.
- Realization evidence must flow through `experiment-evidence-record-v1` and
  the run's `traceability.evidence_record_refs`; disclosure refs are not proof
  of external artifact existence or authorization to dereference content.
- Free text in `realized_value_summary` and `disclosure` is review context only.
  It must not carry secrets, backend-native object dumps, process argv,
  environment dumps, raw tracebacks, hidden answers, or unredacted capture
  payloads.

## Required Incumbents

- Contract authority:
  `implementations/python/packages/aces_contracts/contracts.py`, especially
  `ContractModel`, `ExperimentRunModel`,
  `ExperimentRealizedFormDisclosureModel`,
  `ExperimentRunTraceabilityModel`, `ExperimentReferenceModel`,
  constrained experiment references, artifact references, checksums,
  redaction-aware experiment parameters, RFC 3339 helpers, and
  `validate_experiment_run_against_task()`.
- Published schema and fixtures:
  `contracts/schemas/experiment-core/experiment-run-v1.json`,
  `contracts/fixtures/experiment-core/experiment-run-v1/`,
  `contracts/schema-publication-manifest.json`,
  `tools/generate_contract_schemas.py`, `tools/check_generated_schemas.py`,
  and `tools/check_schema_publication.py`.
- Adjacent experiment contracts:
  `experiment-task-v1`, `experiment-apparatus-context-v1`,
  `experiment-capture-spec-v1`, `experiment-evidence-record-v1`,
  `experiment-derived-measure-v1`, `experiment-study-v1`, and participant
  implementation manifest/provenance contracts.
- Realization inputs:
  runtime snapshot `realization_provenance`, backend manifest
  `realization_support`, reference backend realization checks, processor/backend
  manifest identity, and concept-authority families such as
  `realization-and-disclosure`, `apparatus-declarations`, and
  `provenance-and-evidence`. These are inputs or capability declarations, not
  replacement archival records.
- Future producer/API work must reuse existing control-plane identity,
  authorization, request-size, idempotency, audit, diagnostics, and redacted
  error-envelope patterns. Do not add a disclosure-specific API/security stack.

## Cross-Cutting Layers

- Structural validation: external payloads must pass the generated draft
  2020-12 schema and the closed-world `ContractModel` source. Unknown fields
  remain errors.
- Semantic validation: `ExperimentRealizedFormDisclosureModel` requires
  `realized_ref` or `realized_value_summary`, enforces processor/backend
  authority for matching bases, and keeps disclosure evidence refs unique.
- Run-level validation: `ExperimentRunModel._validate_archival_run()` requires
  disclosure evidence refs to be present in
  `traceability.evidence_record_refs`.
- Cross-artifact validation: `validate_experiment_run_against_task()` remains
  the task/run protocol gate. Realized forms must not bypass task apparatus,
  metric, scenario snapshot, or evidence requirements.
- Manifest and capability validation: processor/backend realization claims must
  build on existing processor/backend manifest identity, backend
  `realization_support`, manifest-authority, and concept-authority validators
  instead of local strings.
- Auth surface: any future HTTP create/read path must use control-plane roles
  and identity checks. Disclosure publication is a run-provenance mutation;
  dereference of evidence content is a separate authorized read.
- Secret-handling surface: summaries and disclosure text may describe a choice,
  but sensitive content belongs behind redacted or restricted evidence artifact
  refs with sensitivity metadata. Do not serialize raw env, argv, credentials,
  private keys, bearer tokens, prompts, or backend-private payloads.
- OS-level exposure: producers and validation helpers must not pass secrets or
  raw evidence payloads through command-line arguments. Use bounded fixture
  files, content-addressed artifacts, URIs, and checksums.
- Error-envelope surface: validation failures must use Pydantic errors,
  existing `Diagnostic` values, or existing redacted HTTP error envelopes. Do
  not echo full run records, evidence payloads, tracebacks, or backend internals.

## Extensibility Guardrail

The extension seam is the existing disclosure model and governed vocabulary,
not a new workflow or schema stack. Add future variation by extending
`concern_kind`, `basis`, `ExperimentReferenceModel.ref_kind`, evidence record
kinds, manifest capability declarations, or concept-authority terms through the
normal contract/schema publication path. Producer code should be parameterized
by realization source and artifact sealing policy so a later backend, processor,
or operator source can emit the same canonical disclosure shape.

## Gotchas And Anti-Patterns

- Do not convert runtime snapshot `realization_provenance` directly into the
  archival run record without sealing it as `experiment-run-v1` and preserving
  traceability refs.
- Do not treat backend manifest `realization_support` as evidence that a run
  disclosed all realized choices. It is a capability claim, not a run fact.
- Do not use `realized_form_disclosures` as an unstructured log list.
- Do not use authored scenario refs, apparatus component ids, operation ids,
  workflow ids, participant episode ids, or backend-native execution ids as
  interchangeable realization identities.
- Do not duplicate schema registries, validation helpers, exception
  hierarchies, logging, auditing, persistence, manifest rendering, or workflow
  code for EXP-722.
- Do not hand-edit `contracts/schemas/`; update contract sources, regenerate,
  update the publication manifest when hashes change, and keep fixtures/tests in
  sync.

## Non-Goals

- New root schema, new provenance graph service, or alternative canonical run
  record.
- Runtime capture, replay, storage, retention, query, scheduling, or HTTP API
  implementation.
- Derived-measure computation, evaluator behavior, statistical analysis, or
  study comparison logic.
- SDL syntax changes, task model changes, or apparatus-context-only
  realization records.
- New exception hierarchy, security model, persistence stack, logging stack,
  audit stack, or workflow pipeline.
