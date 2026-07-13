# Issue 73 / DSL-115 Specificity Preflight

Date: 2026-07-08

Requirement DSL-115 asks for author-selectable specificity across scenario,
participant, evaluation, and experiment concerns. This note is architecture
preflight only. It does not define new SDL syntax, schemas, validators,
runtime behavior, conformance behavior, or an implementation plan.

## Architecture Decisions

- Treat DSL-115 as a specificity contract over existing concern-owning
  surfaces, not as a new global abstraction level.
- Reuse the existing exact/constrained/open vocabulary from SEM-218
  (`aces_sdl.explicitness`) for authored intent. If richer machine-checkable
  domains are needed, align with ADR-070 and the realization envelope domain
  model instead of creating a second constraint language.
- Open or underspecified forms are allowed only where the owning SDL,
  contract, or semantic rule explicitly admits them. Silence remains
  fail-closed.
- Scenario specificity belongs in the SDL scenario model, variables,
  references, instantiation, explicitness metadata, and realization-envelope
  semantics. Do not move scenario meaning into experiment-core records.
- Participant specificity belongs in the participant surfaces that already own
  it: `Agent`, participant action contracts, observation boundaries, behavior
  specifications, and participant runtime contracts.
- Evaluation specificity must respect ADR-073: SDL objectives express
  observable success through `conditions`; graded scoring, reward, derived
  measures, and evaluator outputs belong in the experiment/evaluator plane.
- Experiment specificity belongs in experiment-core task, apparatus context,
  run, study, capture, evidence, and derived-measure contracts. Do not add
  tasks, runs, studies, or evaluator scoring records to SDL.
- Constraints that affect semantics must be machine-checkable: typed
  variables, `allowed_values`, governed references, domain descriptors, and
  semantic invariants. Prose-only constraints are explanatory, not normative.
- Preserve authored specificity provenance through instantiation, compilation,
  planning, runtime disclosure, and persisted snapshots. Substituting a
  variable must not falsely promote a constrained authored value to exact.
- Published schema changes must follow the contract publication path:
  `contracts/schemas/**`, `contracts/schema-publication-manifest.json`,
  generated-schema parity, and `schema_bundle()` compatibility.

## Canonical Incumbents

- Authority chain: ADR-009, ADR-061, `contracts/README.md`,
  `.gc/plan-rules.md`, `tools/check_repo_policy.py`,
  `tools/check_schema_publication.py`, `tools/check_generated_schemas.py`, and
  `tools/verify_all.py`.
- SDL parsing and model shape: `aces_sdl.parser.parse_sdl`,
  `aces_sdl.parser.parse_sdl_file`, `yaml.safe_load`, hashmap key
  preservation, variable-key rejection, and `SDLModel(extra="forbid")`.
- SDL semantic validation: `SemanticValidator`, `SDLParseError`,
  `SDLValidationError`, `SDLInstantiationError`, SDL diagnostics, references,
  variables, and instantiation specs.
- Specificity and realization: `specs/formal/realization/explicitness-and-realization.md`,
  ADR-070, `specs/formal/realization/envelope-semantics.md`,
  `aces_sdl.explicitness`, `RealizationEnvelopeModel`,
  `aces_sdl.realization_envelope`, `CompiledRealizationRequirement`,
  `realization_support_diagnostics`, `realization_disclosure`, and
  `RuntimeSnapshot.realization_provenance`.
- Participant semantics: `Agent`, `ParticipantActionContract`,
  `ParticipantObservationBoundary`, `ParticipantBehaviorSpecification`,
  participant behavior validators, and participant runtime contracts.
- Evaluation and experiment contracts: ADR-055, ADR-064, ADR-068, ADR-073,
  experiment task, apparatus context, run, study, capture spec, evidence
  record, and derived-measure contracts.
- Runtime and API cross-cutting behavior: `Diagnostic`, `OperationStatus`,
  `OperationReceipt`, `ControlPlaneSecurityConfig`, role authorization,
  request-size guards, idempotency keys, request fingerprints, audit records,
  and the redacted control-plane error handler.
- Conformance: `run_target_conformance(reference_scenario=...)` as the
  current #663 bridge, backend manifest validation, profile loading, and
  `schema_bundle()`.

## Cross-Cutting Layers

- Parse/model gate: continue through `yaml.safe_load`, normalized SDL models,
  closed Pydantic models, hashmap key preservation, variable-key rejection, and
  removed scoring-section rejection.
- Reference/semantic gate: preserve fail-closed reference resolution, collect
  all semantic diagnostics, and report paths and concern kinds rather than raw
  payload values.
- Instantiation/config gate: use the existing variable declaration, type,
  default, `allowed_values`, substitution, unresolved-token, and revalidation
  pipeline. Do not introduce a new env-binding path for specificity.
- Contract/schema gate: use `ContractModel`, published schemas, schema
  manifests, generated bundles, and `x-aces-invariants` for semantic rules
  that schemas cannot express directly.
- Manifest/planner gate: use backend manifest realization declarations,
  `resolve_realization_concern()`, support diagnostics, and runtime
  disclosure. Unsupported exact or constrained requirements are diagnostics,
  not silent approximation.
- Runtime/control-plane gate: keep strict default auth, bearer/proxy identity
  validation, role checks, request-size limits, idempotency, audit records, and
  redacted FastAPI exception envelopes.
- OS and secret-exposure gate: do not place credentials, tokens, private keys,
  environment dumps, process argv, backend-private state, hidden truth, host
  paths, full tracebacks, or raw logs in SDL artifacts, contracts, fixtures,
  diagnostics, audit records, persisted snapshots, or examples.
- Error-envelope gate: use SDL exceptions, `Diagnostic`, `OperationStatus`,
  and redacted API errors. Diagnostics should identify address, field path,
  domain, scope, or kind, not sensitive authored or realized values.
- Persistence/evidence gate: store provenance, digests, references, and
  explicit evidence records through the established contracts. Do not hide new
  specificity state in metadata blobs, tags, or untyped log payloads.

## Extensibility Boundary

The required seam is per-concern specificity metadata on the owning surface,
parameterized by concern kind, scope, domain, closure, carriage, and
provenance. Existing anchors are `ExplicitnessRecord`, ADR-070 realization
domains, and the planner concern-kind mapping in
`resolve_realization_concern()`.

Future variations should add governed concern kinds, domain descriptors,
semantic invariants, or schema fields at the owning boundary. They should not
require re-editing every backend, duplicating schemas, or introducing a
top-level `specificity` bag.

## Gotchas And Anti-Patterns

- Do not add a universal `specificity:` root section or a generic
  `open|constrained|exact` field disconnected from the owning concern.
- Do not treat missing data as open unless the owning rule explicitly says so.
- Do not conflate authored explicitness with backend
  `RealizationSupportMode`, participant feature support levels, semantic
  profiles, validation strength, backend profiles, or experiment study
  membership.
- Do not reintroduce SDL scoring or reward language for evaluation
  specificity.
- Do not encode normative domains in free-form `constraints`, notes, comments,
  or ungoverned extension maps.
- Do not promote variable-substituted values to exact when the authored form was
  constrained.
- Do not resolve ambiguous references by first match or by parser order.
- Do not persist new runtime state in `RuntimeSnapshot.metadata`, tags, audit
  detail blobs, or raw backend logs.
- Do not add implementation logic under `implementations/python/src/aces/**`;
  that tree is a compatibility surface.
- Do not create duplicate parsers, validators, exception hierarchies, schema
  bundles, workflow scripts, logging paths, or security gates.

## Non-Goals

- No implementation of DSL-115 in this preflight.
- No new SDL syntax, schema publication, manifest version, compiler behavior,
  planner behavior, runtime API behavior, or conformance behavior in this note.
- No change to requirement status, coverage, or traceability records.
- No relocation of experiment tasks, runs, studies, rewards, scoring, or
  evaluator results into SDL.
- No solver, backend callback language, external query language, or hidden
  policy engine for constraints.
- No implementation plan.
