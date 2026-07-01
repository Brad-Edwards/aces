# Issue 209 ACT-609 Offensive Behavior Vocabularies Preflight

Date: 2026-07-01

Issue: #209.

Requirement: ACT-609, `214e3bf5-24bb-4388-8340-d7ce9bcadd31`.

This note records architecture guardrails for supporting offensive behavior
vocabularies for attack-oriented participant tasks, goals, or activities. It is
guidance for implementation only: it does not add SDL fields, vocabulary terms,
schemas, fixtures, validators, compiler output, runtime emission, control-plane
routes, or conformance behavior.

## Binding Sources

- ADR-067 and `specs/formal/participant-behavior-model/README.md` are the
  behavior-model authority. ACT-609 must extend the composed participant
  behavior model rather than create a new offensive stack.
- ADR-020 keeps authored participant framing in SDL `agents.*` and separates
  participant role, identity, authority anchors, and operating scope from
  runtime apparatus and control-plane concerns.
- ADR-022 owns portable participant action, observation, interaction, failure,
  attribution, temporal, and outcome semantics. Offensive terms classify
  participant behavior intent or activity; they do not replace action contracts
  or interaction semantics.
- ADR-041, ADR-054, and ADR-060 own participant implementation manifests,
  runtime evidence, behavior history, retrieval views, and backend-facing
  carriers. Backend capability or runtime evidence may support a claim, but it
  is not the authored offensive vocabulary itself.
- ADR-009, ADR-012, ADR-019, ADR-061, and ADR-062 define normative artifact
  authority, controlled vocabulary governance, schema publication discipline,
  and concept-authority catalog gates.

## Architecture Decisions

- Treat ACT-609 as a governed participant behavior vocabulary addition, not as
  a new task model, goal model, participant role taxonomy, backend feature flag,
  ATT&CK wrapper, or runtime history type.
- The authoring seam should be the existing behavior specification aggregate.
  A first-class ACT-609 field belongs on
  `ParticipantBehaviorSpecification`/`behavior_specifications.*`, with values
  validated by `controlled-vocabularies-v1`. Do not bury offensive terms only
  inside free-form `extensions`, action names, objective metadata, backend
  manifests, or runtime logs.
- Offensive vocabulary terms must be references or governed values that attach
  to behavior specifications and their existing action, observation, outcome,
  authority/scope, realization, and evidence refs. They must not inline a
  duplicate action contract, evaluation goal, experiment task, workflow
  activity, or backend implementation DTO.
- Use governed-extension vocabulary discipline unless the term set is proven
  closed. Local extension terms must use the existing `x-<owner>:<term>`
  pattern and the shared controlled-vocabulary helpers.
- Map to external cyber-domain vocabularies, including ATT&CK-like technique
  labels, through explicit mapping/loss fields or concept bindings where the
  owning surface already supports them. Do not make an external label the
  portable ACES semantic value unless it is governed by the catalog.
- Schema validity is necessary but insufficient. If ACT-609 publishes a new
  field or contract surface, it needs semantic validation, positive/negative
  fixtures, generated-schema parity, and conformance evidence at the owning
  implementation issue.

## Required Incumbents

- SDL ingress and model gates: `aces_sdl.parser.parse_sdl()`,
  `parse_sdl_file()`, `_HASHMAP_SECTIONS`, key normalization, shorthand
  expansion, variable-created key rejection, `SDLModel(extra="forbid")`, and
  `Scenario.behavior_specifications`.
- Authored behavior aggregate:
  `ParticipantBehaviorSpecification`,
  `ParticipantBehaviorSpecificationRuntime`,
  `aces_processor.compiler._compile_behavior_specifications()`, and the
  canonical `participant.behavior-specification.*` address projection.
- Participant behavior semantics:
  `ParticipantActionContract`, typed preconditions, effects, failure classes,
  observation boundaries, outcome interpretation rules, authority/scope refs,
  and `aces_sdl.semantics.participant_behavior.analyze_participant_behavior()`.
- Semantic validation and diagnostics: `SemanticValidator`,
  `ParticipantBehaviorIssue`,
  `_behavior_specification_vocabulary_issues()`,
  `_validate_named_ref()`-style reference checks, and the central participant
  behavior issue renderer in `aces_sdl.validator._content_objectives`.
- Vocabulary authority:
  `contracts/concept-authority/controlled-vocabularies-v1.json`,
  `aces_contracts.controlled_vocabularies.validate_controlled_vocabulary_value()`,
  `validate_controlled_vocabulary_scope_values()`,
  `ControlledVocabularyCatalogModel`, and the central
  `_CONTROLLED_VOCABULARY_GOVERNED_SCOPES` allowlist.
- Concept and schema authority:
  `contracts/concept-authority/concept-families-v1.json`,
  concept bindings, `ContractModel`, `schema_bundle()`,
  `contracts/schemas/`, `contracts/schema-publication-manifest.json`,
  `contracts/fixtures/`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, and `tools/check_json_artifacts.py`.
- Runtime and conformance evidence:
  `RuntimeSnapshot.participant_behavior_history`,
  `iter_participant_behavior_history_violations()`,
  participant episode/shared-state/concurrency validators, participant
  retrieval views, and `aces_conformance` semantic diagnostics.
- Error and observability surfaces: `SDLParseError`, `SDLValidationError`,
  `SDLInstantiationError`, `aces_processor.models.Diagnostic`, `Severity`,
  API `HTTPException` mappings, control-plane audit events, and the redacted
  FastAPI internal-error handler.

## Whole-Repo View

In-scope repository surfaces are:

- design authority under `docs/decisions/adrs/`, `docs/decisions/`, and
  `specs/formal/participant-behavior-model/`;
- concept authority under `contracts/concept-authority/`;
- published schemas, fixtures, profiles, and publication manifest under
  `contracts/`;
- SDL, compiler, contracts, runtime, backend protocol, and conformance
  packages under `implementations/python/packages/`;
- policy and verification tooling in `.ground-control.yaml`,
  `.gc/plan-rules.md`, `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`,
  `tools/check_concept_authority_governance.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_json_artifacts.py`, and `tools/verify_all.py`;
- tests under `implementations/python/tests/`; and
- examples and public docs under `examples/`, `docs/api/`, and `docs/explain/`
  if ACT-609 changes user-visible SDL or contract usage.

## Cross-Cutting Layers

The intended design must pass every layer it touches:

- SDL/YAML ingress: offensive vocabulary values must enter through safe SDL
  parsing, normalized field keys, stable symbol-defining map keys, and closed
  Pydantic models. Offensive terms are values on a governed field, not new
  user-created map keys or variable-created authority surfaces.
- SDL semantic validation: unknown terms, ungoverned extensions, unresolved
  behavior-spec refs, and ambiguous references fail through collected
  `SDLValidationError` diagnostics using the existing participant behavior
  issue path. Diagnostics may name the invalid term and vocabulary; they must
  not include raw scenario dumps, credentials, prompts, backend config, hidden
  truth, raw command output, or tracebacks.
- Controlled-vocabulary validation: the new scope must be declared in
  `controlled-vocabularies-v1`, added to the central governed-scope allowlist,
  and validated through `validate_controlled_vocabulary_scope_values()` or
  `validate_controlled_vocabulary_value()`. A catalog-only edit is not enough.
- Contract/schema validation: if a portable field or contract changes, update
  the normative schema, `schema_bundle()` parity, publication manifest
  `last_change`, valid and invalid fixtures, and JSON artifact checks. Do not
  hand-edit a schema enum or add a second schema ledger.
- Concept-authority validation: offensive behavior vocabulary should bind to
  existing families before inventing a family. Most ACT-609 terms should bind
  to `actions-and-events`, `tasks-runs-studies`, `apparatus-declarations`, or
  `realization-and-disclosure` depending on the owning claim. A new family
  requires ADR linkage and catalog governance.
- Runtime/conformance validation: runtime behavior history remains evidence of
  realized behavior. Offensive terms may be projected into compiled behavior
  specification records or evidence expectations, but runtime logs, backend
  tool names, ATT&CK labels, scheduler order, and raw action names are not the
  authored vocabulary.
- Control-plane security, if exposed: routes must use
  `ControlPlaneSecurityConfig.strict_defaults()`, read versus mutating identity
  dependencies, request-size guards, idempotency fingerprints for mutations,
  audit records, bounded `HTTPException` details, published response models,
  and the redacted internal-error envelope. An offensive vocabulary term must
  not grant authorization.
- Configuration and environment binding: ACT-609 should not introduce portable
  semantics through process environment variables, command-line flags, backend
  private config, or OS users. Realization details belong behind manifest,
  provenance, disclosure, redaction, digest, and evidence refs.
- Secret and host/OS exposure: credentials, bearer tokens, hidden prompts,
  answer keys, private exploit material, raw command output, and secret-bearing
  argv/env/config values must not appear in SDL diagnostics, fixtures,
  snapshots, logs, audit details, changelog fragments, or error envelopes.

## Extensibility Seam

The extension seam is the governed vocabulary field on the behavior
specification aggregate, plus optional mapping/disclosure refs:

- one field should carry offensive behavior vocabulary terms as governed
  values;
- existing refs should continue to bind those terms to participants, action
  contracts, observation boundaries, outcome interpretation rules,
  authority/scope boundaries, realization profiles, backend feature support,
  and evidence contracts; and
- external mappings should carry system, identifier, loss label, and rationale
  rather than replace the ACES term.

Future defensive or autonomous-agent vocabularies should add sibling governed
vocabulary fields or a parameterized behavior-domain vocabulary family at this
same aggregate seam. They must not require editing backend manifests,
evaluation goals, experiment tasks, or runtime history schemas just to add
another behavior-domain term set.

## Gotchas And Anti-Patterns

Avoid:

- treating `goals` in ACT-609 as SDL evaluation `goals` or experiment
  `ExperimentTaskModel` tasks;
- using offensive terms as participant roles, behavior modes, implementation
  kinds, backend support levels, workflow steps, control-plane permissions, or
  evidence-retention policy;
- accepting arbitrary ATT&CK technique ids, CVE ids, tool names, exploit names,
  command strings, or action names as portable ACES behavior semantics without
  governed vocabulary or explicit mapping-loss metadata;
- duplicating action/precondition/effect/failure/outcome schemas inside the
  offensive vocabulary surface;
- creating a second controlled-vocabulary loader, validator registry,
  exception hierarchy, schema manifest, audit log, persistence store, or
  conformance runner;
- editing compatibility-only wrappers under `implementations/python/src/aces/`;
- weakening hidden-truth, participant-visible observation, disclosure,
  redaction, evidence-only, exposure-policy, or leakage boundaries to make an
  offensive term easier to emit; and
- hardcoding only an initial offensive term list in code, tests, examples, or
  docs while rejecting governed extensions that the catalog permits.

## Non-Goals

- Implementing ACT-609 fields, parser behavior, vocabulary terms, validators,
  compiler output, schemas, fixtures, examples, runtime emission, control-plane
  routes, conformance diagnostics, or tests in this preflight.
- Redesigning participant behavior specifications, action contracts,
  observation boundaries, outcome interpretation, authority/scope semantics,
  behavior modes, participant implementation manifests, backend capabilities,
  experiment tasks, evaluation goals, or workflow activities.
- Standardizing ATT&CK, CVE, exploit-framework, malware, tool, command, or
  backend-native taxonomies as ACES semantics outside the governed vocabulary
  and mapping process.
- Publishing private backend implementation details, credentials, prompts,
  answer keys, raw exploit material, raw command output, hidden truth, or
  backend-private logs as portable offensive behavior data.
