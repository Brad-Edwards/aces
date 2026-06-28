# Issue 208 ACT-608 Participant Behavior Modes Preflight

Date: 2026-06-28

Issue: #208.

Requirement: ACT-608, `6c45384a-1a4b-4f5a-a2e6-a5bdc4c4a832`.

This note records architecture preflight guardrails for participant behavior
modes. It is guidance for implementation only: it does not add SDL fields,
schemas, fixtures, validators, runtime emission, control-plane routes, or
conformance behavior.

## Binding Sources

- ADR-067 and `specs/formal/participant-behavior-model/README.md` are the
  joint design authority for ACT-608. Behavior mode declares how decisions are
  selected or controlled at the participant decision-surface boundary.
- ADR-020 keeps authored participant framing in SDL `agents.*` and separates
  participant role, identity, authority anchors, and operating scope from
  runtime and apparatus concerns.
- ADR-022, ADR-054, and ADR-060 keep participant actions, observations,
  shared state, behavior history, lifecycle, retrieval views, and backend
  carriers on their existing semantic/runtime contract surfaces.
- ADR-041 owns participant implementation manifests and run-level provenance:
  supported decision-surface modes and selected decision-surface mode are
  apparatus/provenance claims, not authored participant semantics.
- ADR-009, ADR-012, ADR-019, ADR-061, and ADR-062 define contract authority,
  generated schema discipline, concept-authority governance, and governed
  vocabulary extension rules.

## Architecture Decisions

- Reuse the existing `participant-decision-surface-modes` controlled
  vocabulary. Do not create a local ACT-608 enum, mode alias table, duplicate
  schema enum, or backend-specific taxonomy.
- The ACT-608 wording `supervised` maps to the governed term
  `human-supervised`. Do not accept a casual `supervised` alias unless the
  concept-authority catalog is changed through the governed vocabulary process.
- Treat behavior mode as decision-surface selection semantics. It is distinct
  from participant role, implementation kind, backend support strength,
  participant-runtime feature support, control-plane authorization,
  authority/scope, interaction class, replay corpus semantics, and evidence
  retention policy.
- Use the existing authored aggregate seam when a scenario declares behavior
  mode: `ParticipantBehaviorSpecification.behavior_mode`, semantic validation,
  compiler address projection, and
  `ParticipantBehaviorSpecificationRuntime.behavior_mode`.
  Do not add a parallel mode field under `agents`, action contracts, runtime
  history, backend manifests, or metadata.
- Use the participant implementation manifest/provenance contracts for
  apparatus capability and run selection: `supported_decision_surface_modes`
  and `selected_decision_surface_mode`. Authored desired mode and run-selected
  apparatus mode may be compared, but neither replaces the other.
- If ACT-608 publishes or changes an external contract, it must use the
  existing closed `ContractModel` and generated-schema path. Schema presence is
  not conformance; semantic diagnostics, fixtures, and evidence are required.

## Required Incumbents

- SDL ingress and model gates: `aces_sdl.parser.parse_sdl()`,
  `parse_sdl_file()`, `SDLModel(extra="forbid")`, key normalization,
  shorthand expansion, `_HASHMAP_SECTIONS`, stable mapping-key preservation,
  and variable-created key rejection.
- Authored behavior aggregate: `Scenario.behavior_specifications`,
  `ParticipantBehaviorSpecification`,
  `ParticipantBehaviorSpecificationRuntime`, and `aces_processor.compiler`
  address projection for behavior specifications.
- Semantic validation: `SemanticValidator`,
  `aces_sdl.semantics.participant_behavior.analyze_participant_behavior()`,
  `_behavior_mode_issue()`, `_validate_named_ref()`, and the central issue
  renderer in `aces_sdl.validator._content_objectives`.
- Vocabulary authority:
  `contracts/concept-authority/controlled-vocabularies-v1.json`,
  `aces_contracts.controlled_vocabularies.validate_controlled_vocabulary_value()`,
  `validate_controlled_vocabulary_scope_values()`, and governed
  `x-<owner>:<term>` extension syntax.
- Apparatus/provenance contracts:
  `ParticipantImplementationManifestModel`,
  `ParticipantImplementationCapabilitiesModel`,
  `ParticipantImplementationProvenanceModel`, and
  `ParticipantImplementationSelectionModel`.
- Backend and profile declarations:
  `BackendManifestV2Model`, `ParticipantRuntimeCapabilities`,
  `ParticipantFeatureSupportModel`, backend profile contracts, support-level
  vocabulary, disclosure refs, and conformance diagnostics.
- Runtime and conformance evidence:
  `RuntimeSnapshot.participant_behavior_history`,
  `iter_participant_behavior_history_violations()`,
  participant episode/shared-state/concurrency validators,
  participant retrieval views, and the participant-runtime fixture families.
- Contract publication machinery: `ContractModel`, `schema_bundle()`,
  `contracts/schema-publication-manifest.json`, `contracts/schemas/`,
  `contracts/fixtures/`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, and `tools/check_json_artifacts.py`.
- Error and observability surfaces: `SDLParseError`, `SDLValidationError`,
  `SDLInstantiationError`, `Diagnostic`, `Severity`, conformance
  `semantic-invalid` diagnostics, API `HTTPException` mappings, control-plane
  audit events, and the redacted FastAPI internal-error handler.

## Whole-Repo View

In-scope repository surfaces are:

- design authority under `docs/decisions/adrs/` and `specs/formal/`;
- concept authority and published contracts under `contracts/`;
- SDL, compiler, contracts, runtime, backend protocol, and conformance packages
  under `implementations/python/packages/`;
- negative, positive, runtime, conformance, and policy tests under
  `implementations/python/tests/`;
- scenario and library examples under `examples/` when examples expose
  behavior-mode declarations;
- documentation mirrors under `docs/api/` and `docs/explain/` if public
  behavior-mode usage changes; and
- workflow and policy tooling in `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, `tools/check_json_artifacts.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers

The intended design must pass every layer it touches:

- SDL/YAML ingress: behavior-mode declarations must enter through safe SDL
  parsing, normalized field names, closed models, stable symbol-defining keys,
  and variable-key rejection. A mode value is data, not a new map key or
  template-created authority surface.
- SDL semantic validation: unknown or ungoverned mode terms must fail through
  collected `SDLValidationError` diagnostics using the existing participant
  behavior issue path. The diagnostic may name the invalid term and vocabulary;
  it must not include raw scenario dumps, credentials, prompts, backend config,
  or tracebacks.
- Controlled-vocabulary validation: SDL behavior mode should resolve by
  vocabulary id `participant-decision-surface-modes`; manifest/provenance
  supported or selected modes should resolve through the governed scope
  `capabilities.supported_decision_surface_modes`. Both paths must use the
  shared vocabulary loader and extension discipline.
- Contract/schema validation: any new portable payload must be closed,
  generated from model source into the schema bundle, registered in the
  publication manifest, and covered by valid and invalid fixtures. Do not
  hand-edit a schema enum or add a second manifest ledger.
- Apparatus/provenance validation: implementation manifests declare supported
  modes; run provenance records the selected mode for each participant address.
  Selected mode should be checked against the governed vocabulary and, when a
  manifest is available, against the declared supported set.
- Configuration and environment binding: behavior modes must not introduce new
  process environment variables, argv flags, or backend-private configuration
  shapes as portable semantics. Configuration-sensitive realization details
  belong behind manifest/provenance refs, digests, disclosure refs, and
  exposure-policy refs.
- Runtime/conformance validation: runtime behavior history remains evidence of
  realized decisions and must continue through participant behavior-history,
  episode, shared-state, temporal, visibility, attribution, outcome, and joint
  action validators. Do not store authored behavior mode as runtime history.
- Control-plane security, if exposed: routes must use
  `ControlPlaneSecurityConfig.strict_defaults()`, read versus mutating identity
  dependencies, request-size guards, idempotency fingerprints for mutations,
  audit records, bounded `HTTPException` details, and the redacted internal
  error envelope. Behavior mode does not grant control-plane permission.
- Secret and OS/process exposure: behavior-mode validation must not require
  hidden prompts, policy bodies, credentials, bearer tokens, raw command output,
  raw event logs, process argv values, or environment dumps. Use refs, digests,
  markings, redaction policies, exposure-policy refs, and disclosure refs.

## Extensibility Seam

The extension seam is the governed mode term plus explicit selection context:

- authored selection belongs on the behavior specification aggregate, keyed by
  behavior-spec id and compiled participant address;
- apparatus support belongs on participant implementation manifests; and
- run selection belongs on participant implementation provenance.

Future variants, such as a new non-human supervision term, a finer replay
selection basis, or a mode selected per decision phase, should add governed
vocabulary terms or an explicit selection-context parameter at one of those
seams. They must not overload `behavior_mode` into a backend feature flag,
role label, evidence-retention policy, or control-plane authorization claim.

## Gotchas And Anti-Patterns

Avoid:

- accepting `supervised` as a synonym for `human-supervised`;
- hardcoding only the six ACT-608 examples and rejecting other governed terms
  or governed extensions such as existing catalog terms;
- creating a second enum in Python, JSON Schema, CLI code, tests, docs, or
  backend manifests;
- treating `human-control-proxy`, `human-supervised`, and `mixed-control` as
  participant roles or interaction topologies;
- treating `replayed` as proof of replay corpus, benchmark split, evidence
  retention, or reproducibility semantics;
- treating `policy-directed` as scenario authority, credential possession, or
  control-plane permission;
- treating backend support claims as proof that a particular mode ran;
- deriving behavior mode from raw logs, scheduler order, reward values,
  action names, tool labels, ATT&CK/CVE labels, process names, or backend
  private DTOs;
- adding participant-mode-specific persistence, exception hierarchies,
  validator registries, audit channels, or schema publication paths; and
- weakening hidden-truth, redaction, evidence-only, participant-visible
  observation, or exposure-policy boundaries to make a mode easier to emit.

## Non-Goals

- Implementing ACT-608 fields, parser changes, validators, compiler output,
  schemas, fixtures, control-plane routes, runtime emission, conformance
  checks, or tests in this preflight.
- Redesigning participant behavior specifications, declarative participant
  framing, participant semantics, participant episode lifecycle, backend
  capability declarations, participant implementation manifests, run
  provenance, or control-plane authentication.
- Publishing hidden prompts, credentials, raw policy bodies, private replay
  data, answer keys, raw command output, backend-private logs, or hidden truth
  as portable behavior-mode data.
