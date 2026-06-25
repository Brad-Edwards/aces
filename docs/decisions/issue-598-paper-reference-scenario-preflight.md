# Issue 598 Paper Reference Scenario Preflight

Date: 2026-06-25

Issue: #598.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records architecture guardrails for adding the canonical paper
reference scenario that demonstrates authored SDL -> processor -> runtime ->
backend handoff for an agent-driven participant loop. It is guidance only: it
does not add the scenario, README, tests, backend bindings, APTL realization,
or proof artifacts.

## Binding Sources

- ADR-020 keeps authored participant framing in SDL `agents.*` and separates
  role, authority, accounts, operating scope, runtime identity, credentials,
  and apparatus identity.
- ADR-022 and `specs/formal/participant-semantics/` define action contracts,
  observation boundaries, visibility, interaction, temporal, attribution, and
  outcome semantics. Action names alone are not portable behavior semantics.
- ADR-041 owns participant implementation manifests and provenance; a coding
  agent runner is apparatus selected by runtime/provenance, not hidden SDL
  semantics.
- ADR-060 and `docs/research/participant-backend-contracts/preflight-guardrails.md`
  govern backend-facing participant runtime declarations and retrieval
  carriers.
- ADR-063 and `docs/decisions/issue-197-run-314-reference-emulation-backend-preflight.md`
  define the reference emulation backend boundary and the registry/driver seam.
- `docs/decisions/issue-206-act-606-behavior-specifications-preflight.md`
  governs first-class authored behavior specifications over existing
  participant behavior surfaces.
- `docs/explain/sdl/testing.md`, `examples/README.md`,
  `implementations/python/tests/test_scenarios.py`, and
  `implementations/python/tests/test_example_schema_conformance.py` define the
  positive worked-scenario corpus boundary.
- `.ground-control.yaml`, `.gc/plan-rules.md`, and ADR-014 define the canonical
  verification graph and policy gates.

## Architecture Decisions

- Place the reference scenario in the existing positive corpus
  `examples/scenarios/*.sdl.yaml`. It is a worked SDL artifact, not a contract
  fixture, invalid-control specimen, backend profile, or APTL-private asset.
- Keep the SDL compact but semantically complete: small topology, explicit
  entities/roles, at least one SDL `agent`, declared `action_contracts`,
  declared `observation_boundaries`, and outcome/objective material enough to
  explain the paper handoff.
- Reuse the current participant authoring surface. Do not add a new top-level
  `participants`, `agent_runtime`, `llm_runner`, `aptl`, or benchmark-specific
  SDL section for this issue.
- Make authored meaning portable and implementation binding explicit. The SDL
  may reference a participant implementation/runtime binding by stable
  reference such as a participant implementation manifest ref, but the actual
  coding-agent runner, prompts, command wiring, sandbox, and backend action
  driver belong to downstream runtime/backend/APTL issues and the scenario
  README.
- Compile-time acceptance is a first-class proof. The implementation should add
  focused test coverage that loads the scenario through `parse_sdl_file()` or
  `load_scenario()` and compiles with `compile_runtime_model()`, asserting
  non-empty `participant_behaviors`, `action_contracts`, and
  `observation_boundaries`.
- Treat reference-backend/APTL realizability as bounded compatibility, not as
  a new backend capability claim. The scenario should fit the existing
  `reference-emulation` manifest: small VM/switch topology, supported content
  and account shapes, ordinary objective/workflow/evaluation surfaces, and
  participant runtime feature terms already declared by the backend manifest.
- The short scenario README should explain the participant, declared actions,
  observation boundary, expected evidence, limitations, downstream APTL
  realization/n=2 proof links, and the fact that this ACES issue does not close
  Brad-Edwards/aptl#554.

## Required Incumbents

Reuse these repo surfaces before adding anything new:

- Scenario corpus and docs: `examples/scenarios/*.sdl.yaml`,
  `examples/README.md`, `docs/explain/sdl/testing.md`, and
  `implementations/python/tests/paths.py` / `EXAMPLES_DIR`.
- SDL ingress: `aces_sdl.parser.parse_sdl_file`, `parse_sdl()`,
  `yaml.safe_load`, `_HASHMAP_SECTIONS`, `_NESTED_HASHMAP_FIELDS`,
  mapping-key variable rejection, shorthand expansion, `SDLModel(extra="forbid")`,
  `SemanticValidator`, and existing SDL error types.
- Authored participant surfaces: `Agent`, `Scenario.agents`,
  `Scenario.action_contracts`, `Scenario.observation_boundaries`,
  `Scenario.outcome_interpretation_rules`, and
  `Scenario.behavior_specifications`.
- Participant semantic validators:
  `analyze_participant_behavior()`,
  `analyze_participant_outcome_interpretations()`,
  `_validate_named_ref()`, `_validate_operating_scope_ref()`, and the central
  participant issue renderers in `validator/_content_objectives.py`.
- Compiler/runtime addresses: `compile_runtime_model()`,
  `compile_scenario_runtime_model()`, `ParticipantActionContractRuntime`,
  `ParticipantObservationBoundaryRuntime`,
  `ParticipantOutcomeInterpretationRuleRuntime`,
  `ParticipantBehaviorRuntime`, `ParticipantBehaviorSpecificationRuntime`, and
  `RuntimeModel.participant_behaviors`.
- Controlled vocabularies and manifests:
  `participant-decision-surface-modes`,
  `participant-runtime-behavior-features`,
  `participant-runtime-interaction-features`,
  `ParticipantRuntimeCapabilities`, `ParticipantFeatureSupportModel`,
  `BackendManifestV2Model`, `backend_manifest_payload()`, and
  `create_reference_backend_manifest()`.
- Participant implementation and apparatus contracts:
  `ParticipantImplementationManifestModel`,
  `ParticipantImplementationProvenanceModel`,
  `ExperimentApparatusContextModel`, and `ExperimentRunModel`.
- Runtime/backend boundaries, if tests go past compile:
  `BackendRegistry`, `RuntimeTarget`, `RuntimeManager`,
  `RuntimeControlPlane`, `_call_backend_apply()`, `OperationReceipt`,
  `OperationStatus`, `RuntimeSnapshot`, `Diagnostic`, and `Severity`.
- Verification and policy: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/check_example_library.py`,
  `tools/check_schema_publication.py`, `tools/check_generated_schemas.py`,
  `tools/check_json_artifacts.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL/config parsing: the scenario must pass safe YAML loading, normalized
  field keys, preserved user-defined map keys, symbol-key variable rejection,
  closed Pydantic SDL models, semantic validation, and advisory checks. Do not
  compile directly from raw dictionaries or skip validation to make the example
  pass.
- Positive corpus and schema layer: a file under `examples/scenarios/` must be
  valid reusable SDL. It is automatically enumerated by `test_scenarios.py` and
  should continue to conform to the checked-in
  `sdl-authoring-input-v1` schema through `test_example_schema_conformance.py`.
  Do not place invalid controls or partial drafts under this directory.
- Participant semantic layer: `agents.*.actions` must resolve to declared
  action contracts; agent observation boundaries must resolve to declared
  boundaries; behavior specifications must reference existing participants,
  roles, action contracts, observation boundaries, outcome rules, authority
  scope refs, governed behavior modes, governed backend feature terms, and
  published evidence contract ids.
- Observation/security layer: hidden truth, answer keys, scaffolds, task
  statements, evidence, and participant-visible observations must be separated
  with observation boundary rules. Do not expose hidden adjudication material,
  raw prompts, private runner configuration, credentials, backend inspect data,
  or evaluator state as participant-observable data.
- Outcome/evidence layer: participant-local action outcome, objective result,
  workflow result, evaluation result, reward, and evidence claim must remain
  distinct. Outcome interpretation rules should map between layers explicitly
  and include limitations rather than implying that local action success is
  objective success.
- Backend manifest/config layer: backend support must be read through
  `BackendManifestV2Model` and the governed participant runtime capability
  vocabularies. Do not add scenario-local backend feature strings, APTL-private
  support flags, or Docker/Podman/APTL SDL keys.
- Runtime apply/control-plane layer: if the proof exercises runtime/backend
  behavior, calls must flow through `RuntimeManager` or `RuntimeControlPlane`
  with a `RuntimeTarget` from `BackendRegistry`; public failures remain
  `Diagnostic`, `OperationReceipt`, and `OperationStatus` payloads.
- Control-plane security layer: no new HTTP or retrieval surface is required.
  If later proof work exposes one, it inherits `ControlPlaneSecurityConfig`,
  role gates, target-bound identity, request-size limits, idempotency
  fingerprints, audit records, and redacted internal error envelopes.
- Secret and OS exposure layer: scenario files, README text, tests,
  diagnostics, fixtures, logs, process argv, and command examples must not
  contain bearer tokens, API keys, private host paths, raw prompts, hidden
  answers, raw environment dumps, command stdout/stderr dumps, backend-native
  object reprs, or full tracebacks. Use refs, digests, markings, disclosure
  refs, and redaction language.
- Persistence layer: this issue should not add a new operation store, scenario
  registry, participant store, audit path, or artifact database. Live state uses
  `RuntimeSnapshot` / `ControlPlaneStore`; archival apparatus/run evidence uses
  existing experiment and participant implementation contracts.
- Error-envelope layer: SDL failures stay on `SDLParseError`,
  `SDLValidationError`, or `ScenarioValidationError`; runtime/conformance
  failures stay on `Diagnostic` and existing operation/result envelopes. Do not
  add a scenario-specific exception hierarchy or payload dump.
- Workflow/policy layer: repo policy, requirement governance, changelog,
  generated-schema parity, schema-publication, JSON artifact, and full verify
  gates remain authoritative. A user-visible scenario addition should add the
  required `changelog.d/598.<type>.md` fragment.

## Extension Boundary

The extension seam is the authored behavior specification plus a documented
runtime binding:

- SDL fields parameterize participant refs, role refs, action contract refs,
  observation boundary refs, outcome interpretation refs, authority/scope refs,
  behavior mode, backend feature-support refs, and evidence contract refs.
- The sidecar README parameterizes the participant implementation/runtime
  binding and downstream issue refs. It should name the binding without
  embedding private runner config or backend commands in the SDL body.
- Backend variation belongs on the existing backend registry descriptor seam
  (`manifest_factory(**config)` and `components_factory(manifest=..., **config)`)
  and on participant implementation manifest/provenance records, not in new SDL
  keys.

A future n=2 proof or alternate runner should add another participant
implementation/provenance selection, another participant/action/boundary ref,
or another downstream binding entry without changing the scenario corpus root,
parser, compiler address scheme, backend manifest schema, or participant
semantics vocabulary.

## Gotchas And Anti-Patterns

Avoid:

- copying the APTL #554 backend-defined action into SDL as if it were authored
  ACES behavior;
- treating `agents.*.actions` as complete semantics instead of binding each
  action name to an action contract;
- treating backend participant-runtime capability as proof that a coding-agent
  participant implementation ran;
- hiding the coding-agent runner, prompt, command, OS sandbox, or APTL action
  adapter in free-form SDL fields, runtime metadata, diagnostics, or README
  prose that implies authored semantics;
- adding a new schema, parser branch, controlled vocabulary, manifest section,
  fixture loader, exception hierarchy, persistence store, or workflow runner for
  one reference scenario;
- moving the scenario into a new corpus root or subdirectory pattern without
  updating the one existing `EXAMPLES_DIR` discovery seam;
- using backend logs, traces, timestamps, scheduler order, container IDs,
  command labels, ATT&CK/CVE labels, reward values, or final scores as portable
  participant semantics without governed mapping and limitations;
- exposing hidden truth, answer keys, prompt content, canaries, private traces,
  operator secrets, process argv, environment dumps, or backend-native object
  reprs in scenario artifacts or diagnostics;
- claiming broad purple-team benchmark capability, agent capability, or
  backend conformance from this compact reference scenario alone.

## Non-Goals

- Implementing the paper reference scenario, README, tests, backend binding,
  APTL realization, n=2 proof, runtime action runner, or participant
  implementation manifest in this preflight.
- Closing Brad-Edwards/aptl#554 or proving the downstream backend action loop.
- Adding or changing SDL syntax, published schemas, contract fixtures,
  controlled vocabularies, backend profiles, manifest authority, or reference
  backend infrastructure.
- Redesigning participant framing, action contracts, observation boundaries,
  outcome interpretation, behavior specifications, participant implementation
  provenance, control-plane security, runtime persistence, diagnostics, or
  verification workflow.
