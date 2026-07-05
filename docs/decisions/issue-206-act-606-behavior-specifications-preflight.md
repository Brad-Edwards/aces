# Issue 206 ACT-606 Behavior Specifications Preflight

Date: 2026-06-24

Issue: #206.

Requirement: ACT-606.

This note records architecture guardrails for implementing first-class
participant behavior specifications alongside declarative participant framing.
It is guidance for the implementation and does not add SDL fields, schemas,
runtime contracts, validators, fixtures, or conformance behavior.

## Binding Sources

- ADR-020 pins declarative participant framing to SDL `agents.*` and keeps
  identity, role, starting conditions, authority anchors, and operating scope
  separate from runtime identity, credentials, control-plane auth, and apparatus
  identity.
- ADR-022 and `specs/formal/participant-semantics/` define the portable
  participant behavior semantics: action contracts, observations, visibility,
  interactions, failures, attribution, temporal context, and outcome
  interpretation.
- ADR-041 owns participant implementation manifests and provenance; ACT-606
  must reference them rather than restating private implementation config.
- ADR-054 and `specs/formal/participant-runtime/` own runtime participant
  lifecycle, behavior history, shared state, observations, concurrency, and
  evidence records.
- ADR-060 and `specs/formal/runtime-contracts/participant-backend-contracts.md`
  own the backend-facing carrier and retrieval contract surface.
- ADR-067 and `specs/formal/participant-behavior-model/README.md` define the
  participant behavior model composition and the ACT-606 aggregate shape.

## Architecture Decisions

- A behavior specification is a first-class authored aggregate over existing
  participant behavior surfaces. It may be named, versioned, traced, reviewed,
  and validated, but it must not replace action contracts, observation
  boundaries, outcome interpretation rules, authority/scope refs, participant
  implementation manifests, backend capability declarations, or runtime
  behavior evidence.
- The SDL authoring home must extend the existing scenario model and parser
  pipeline. Do not introduce a parallel top-level `participants` stack unless a
  later ADR defines a distinct authored concept.
- The aggregate should store references to existing authored artifacts and
  controlled-vocabulary values. It should not inline duplicate action,
  observation, outcome, authority, implementation, backend-support, or evidence
  schemas.
- If compilation support is added, compile behavior specifications into stable
  `participant.*` addresses that depend on existing compiled action contracts,
  observation boundaries, outcome rules, participant behavior bindings, and
  framing refs. Runtime history remains evidence of realized behavior, not the
  authored behavior specification.
- If an externally visible behavior-specification contract is published, it
  must be a closed `ContractModel` payload generated through `schema_bundle()`
  and governed by `contracts/schema-publication-manifest.json`, checked
  schemas, and positive/negative fixtures. Do not hand-edit JSON schemas as the
  only change.
- Behavior mode must resolve through the existing
  `participant-decision-surface-modes` controlled vocabulary, including the
  governed extension pattern. Do not create artifact-local aliases or a second
  enum.
- Backend feature support and weakened realization claims must use existing
  participant runtime feature vocabularies, support levels, disclosure refs,
  mapping-loss labels, and conformance diagnostics. Backend support is not
  proof that a particular participant implementation ran.

## Required Incumbents

- SDL shape and parser gates: `SDLModel(extra="forbid")`,
  `aces_sdl.parser.parse_sdl()`, `_HASHMAP_SECTIONS`, key normalization,
  shorthand expansion, user-defined mapping-key preservation, and variable-key
  rejection.
- Authored participant surfaces: `aces_sdl.agents.Agent`,
  `Scenario.agents`, `Scenario.action_contracts`,
  `Scenario.observation_boundaries`, and
  `Scenario.outcome_interpretation_rules`.
- Semantic validation: `SemanticValidator`,
  `aces_sdl.semantics.participant_behavior.analyze_participant_behavior()`,
  `aces_sdl.semantics.participant_outcome.analyze_participant_outcome_interpretations()`,
  `_validate_named_ref()`, `_validate_operating_scope_ref()`, and the central
  participant issue-renderer dictionaries in `validator/_content_objectives.py`.
- Participant contract models: `ParticipantActionContract`,
  `ParticipantObservationBoundary`, `OutcomeInterpretationRule`, typed
  preconditions/effects/failure classes, temporal contracts, attribution
  semantics, and visibility transition validators.
- Compiler/runtime addresses: `aces_processor.compiler` address helpers,
  `ParticipantActionContractRuntime`, `ParticipantObservationBoundaryRuntime`,
  `ParticipantOutcomeInterpretationRuleRuntime`,
  `ParticipantBehaviorRuntime`, and `RuntimeModel.participant_behaviors`.
- Runtime evidence and conformance: `RuntimeSnapshot.participant_behavior_history`,
  `iter_participant_behavior_history_violations()`,
  `iter_participant_behavior_joint_action_violations()`,
  participant episode/shared-state/concurrency validators,
  `_participant_behavior_snapshot_diagnostics()`, and the
  `participant-behavior-history-event-stream-v1` fixture path.
- Error and diagnostic surfaces: `SDLParseError`, `SDLValidationError`,
  `SDLInstantiationError`, `Scenario.advisories`, `Diagnostic`, `Severity`,
  conformance `conformance.semantic-invalid` diagnostics, `HTTPException`
  mappings at API boundaries, and the redacted FastAPI internal-error handler.
- Contract authority: `ContractModel`, `schema_bundle()`,
  `contracts/schemas/`, `contracts/schema-publication-manifest.json`,
  `contracts/fixtures/`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, and `tools/check_json_artifacts.py`.
- Governed vocabularies and capability claims:
  `contracts/concept-authority/controlled-vocabularies-v1.json`,
  `validate_controlled_vocabulary_scope_values()`,
  `ParticipantFeatureSupportLevel`, `ParticipantRuntimeCapabilities`, and
  `ParticipantFeatureSupportModel`.
- Control-plane surfaces, if exposed: `ControlPlaneSecurityConfig`,
  read vs mutating identity dependencies, request-size guard,
  idempotency fingerprinting, audit events, redacted internal-error handler,
  participant retrieval views, `OperationReceiptModel`, and
  `OperationStatusModel`.

## Cross-Cutting Layers

- YAML/config parsing: behavior specifications must pass through safe YAML
  loading, normalized field keys, stable symbol-defining mapping keys,
  variable-reference rules, and closed Pydantic SDL models. Symbol-defining
  spec ids and map keys must not be `${var}` placeholders.
- SDL semantic validation: participant refs, role refs, action-contract refs,
  observation-boundary refs, outcome-rule refs, authority/scope refs, behavior
  mode values, backend feature-support refs, and evidence-contract refs must
  fail closed when unresolved, ambiguous, duplicated, or outside the governed
  scope.
- Controlled-vocabulary validation: behavior mode, backend behavior features,
  interaction features, and support levels must route through the existing
  controlled-vocabulary helpers and extension patterns. Local enums or loose
  strings are not enough.
- Contract/schema validation: any portable exchange payload must be a closed
  `ContractModel`, generated into `schema_bundle()`, published under
  `contracts/schemas/`, registered in the schema publication manifest, and
  covered by valid and invalid fixtures plus conformance diagnostics where
  schema validity alone cannot prove semantics.
- Runtime/conformance validation: runtime behavior claims must continue to
  validate through compiled addresses, participant behavior-history checks,
  episode history, shared state, visibility, temporal context, outcome
  grounding, attribution, and concurrency validators. Runtime history must not
  become the authored behavior specification.
- Control-plane security: any API route or retrieval view must use strict auth
  defaults, read vs mutating role dependencies, request-size limits,
  idempotency fingerprints for mutations, audit records, and the redacted
  internal-error envelope. Participant authority is scenario meaning, not
  control-plane authorization.
- Error envelopes and leakage: parser and semantic failures should stay on the
  existing SDL exception path, runtime/conformance failures should stay on
  structured `Diagnostic` payloads, and HTTP handlers should map expected
  domain conflicts to bounded `HTTPException` details. Do not add traceback,
  backend-private payload, or raw scenario dumps to error responses.
- Secret and host/OS exposure: behavior specifications, diagnostics, fixtures,
  audit events, logs, snapshots, and process argv must not carry bearer tokens,
  credentials, raw command output, private prompts, hidden answer keys,
  backend-private objects, or full tracebacks. Use refs, digests, markings,
  redaction policy refs, and disclosure refs.
- Persistence: use existing scenario artifacts, contract fixtures, runtime
  snapshot histories, control-plane stores, and audit logs. Do not create a
  participant-behavior-specific persistence path unless a later contract
  explicitly requires a new published artifact family.

## Extensibility Seam

The extension seam is a behavior specification aggregate whose fields are
references plus governed declarations:

- `spec_id`, semantic version, lifecycle state, and extension policy;
- participant and participant-role refs;
- action contract, observation boundary, outcome interpretation, authority,
  scope, backend feature-support, and evidence-contract refs;
- behavior mode from `participant-decision-surface-modes`; and
- realization/disclosure refs for weakened, backend-specific, or private
  implementation details.

Future variations should add reference slots, governed vocabulary terms, or
`x-<owner>:<term>` governed extensions at that seam. A future executable
behavior-specification contract should parameterize by behavior-spec id and
compiled address, not by backend-specific DTO fields or free-form metadata.

## Gotchas And Anti-Patterns

Avoid:

- duplicating `Agent` or existing behavior contracts under a new participant
  schema tree;
- treating raw `agents.*.actions`, tool labels, ATT&CK/CVE labels, backend
  commands, scheduler order, timestamps, rewards, or logs as portable behavior
  semantics;
- copying action-contract, observation-boundary, outcome-rule, authority,
  implementation-manifest, backend-capability, or runtime-history fields into
  the behavior specification body instead of referencing them;
- using behavior mode as participant role, implementation kind, backend support
  strength, interaction class, or control-plane authorization;
- treating credentials, bearer tokens, OS users, or backend sandboxing as
  authored participant authority or operating scope;
- using runtime behavior history, participant retrieval views, or backend logs
  as the authored behavior specification;
- adding duplicate exception hierarchies, validator registries, schema
  manifests, audit logs, persistence stores, or conformance runners;
- hand-editing generated/public schema artifacts without the manifest ledger,
  fixtures, and generated-schema parity checks;
- editing compatibility-only wrappers under `implementations/python/src/aces/`;
  and
- weakening hidden-truth, evidence-only, redaction, disclosure, or
  participant-visible observation boundaries to make the aggregate easier to
  emit.

## Non-Goals

- Implementing ACT-606 fields, parser behavior, semantic validators, compiler
  output, schemas, fixtures, conformance diagnostics, or runtime emission in
  this preflight.
- Redesigning declarative participant framing, participant episode lifecycle,
  action contracts, observation boundaries, outcome interpretation rules,
  behavior modes, authority/scope semantics, or participant implementation
  manifests.
- Adding a new control-plane authentication model, authorization role, request
  envelope, logging/audit mechanism, persistence store, backend API, or live
  participant runtime loop.
- Publishing private backend implementation configuration, prompt content,
  credentials, answer keys, raw command output, or hidden truth as portable
  behavior-specification data.
