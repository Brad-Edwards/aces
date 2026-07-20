# Issue 119 Participant Tool, Decision-Surface, And Exposure Preflight

Date: 2026-07-14

Issue: #119.

Requirements: none. The GitHub issue title, body, and acceptance criteria are
the contract. `SEM-219` is the branch-CI anchor for the joint `SEM-219`,
`SEM-220`, and `SEM-226` design.

This note records architecture guardrails for the joint ADR and formal-spec
work. It is non-normative preflight guidance only: it does not publish that ADR
or specification, add SDL syntax or contracts, implement spawned issues #294,
#295, or #296, or claim semantic coverage.

## Binding Sources

- ADR-020 owns authored participant identity, role, starting conditions,
  authority anchors, and operating scope on `agents.*`. Scenario authority and
  scope are not control-plane authorization, OS identity, or apparatus
  capability.
- ADR-022 and `specs/formal/participant-semantics/README.md` own participant
  action contracts, the time-indexed view relation `V_p,t`, observation
  boundaries, visibility transitions, hidden-truth separation, fail-closed
  applicability, and evidence-labeled runtime meaning. The joint design extends
  that semantic model; it must not create a second action or visibility model.
- ADR-041 owns participant-implementation manifests and run-level selection
  provenance. `supported_decision_surface_modes` and
  `tool_affordance_expectations` are apparatus capability declarations;
  `selected_decision_surface_mode` and `ParticipantExposurePolicyModel` record
  run selection. None is authored participant meaning or proof of realized
  exposure by itself.
- ADR-054 and `specs/formal/participant-runtime/` own participant runtime
  lifecycle, observation envelopes, behavior history, shared state, concurrency,
  markings, redaction, loss, and information guarantees.
- ADR-060 and
  `specs/formal/runtime-contracts/participant-backend-contracts.md` own neutral
  backend-facing carriers, feature-support disclosures, retrieval projections,
  and outcome reports.
- ADR-067 and `specs/formal/participant-behavior-model/README.md` own behavior
  specifications as aggregates over the existing participant surfaces. The
  current `behavior_mode` uses `participant-decision-surface-modes`; it is a
  control/selection mode, not the content of a decision surface.
- SEM-214 and SEM-216 already define participant context views and the boundary
  among live state, archival evidence, derived results, analysis, and
  audience-specific views. A decision surface is not a new source-of-truth
  stratum.
- ADR-066 and the SEM-224 observability-plane design keep backend logs,
  telemetry, diagnostics, evidence, derived analysis, and participant-visible
  observations in separate carriers.
- ADR-009, ADR-012, ADR-036, ADR-061, and the authority-boundary manifest govern
  normative artifact authority, shared concepts, package ownership, and schema
  evolution.

## Architecture Decisions And Guardrails

### Keep the semantic axes separate

The joint design must distinguish these independently reviewable facts:

1. **Action meaning** is owned by governed participant action contracts.
2. **Authored availability** binds a participant or behavior specification to
   action contracts, observation boundaries, authority, and operating scope.
3. **Apparatus support** declares which control modes, participant contracts,
   and tool-affordance categories an implementation supports or expects.
4. **Run selection** records the selected implementation, control mode,
   configuration reference/digest, and exposure policy.
5. **Current decision surface** is a participant- and episode-local projection
   at an explicit observation/order point over visible context, candidate
   action-contract references with explicit eligibility/admission state,
   exposed affordance references, and declared limitations.
6. **Realized exposure** records what the runtime actually projected or made
   available, with visibility, policy, evidence, provenance, and weakening
   disclosures.
7. **Decision and outcome** are the selected action attempt and its result;
   neither may be inferred merely because an item appeared on a surface.

No field or schema should carry more than one of those authorities implicitly.
In particular, an implementation expectation is not an exposure grant, an
exposure grant is not proof of delivery, and visibility is not action
applicability.

### Extend the existing participant semantic model

- The issue should publish a new ADR for the joint decision and extend
  `specs/formal/participant-semantics/README.md` with the `SEM-219`, `SEM-220`,
  and `SEM-226` sections. Do not fork a parallel participant-semantics formal
  tree or revise the accepted ADR-022 decision in place.
- The formal design should define the surface as a projection relation over the
  existing sets and histories, not as a UI/widget tree or backend DTO. At
  minimum, the relation must be parameterized by participant, episode,
  observation/order point, behavior/action-contract set, observation boundary
  or view relation, implementation selection, exposure policy, and realization
  disclosures.
- The design must distinguish declared actions, currently eligible actions,
  admitted attempts, selected actions, and completed outcomes. Eligibility is
  fail-closed over authority, target, knowledge, resource, temporal,
  interaction, and realization preconditions from SEM-211; the design must not
  reimplement those predicates.
- `SEM-226` must compose or refine the existing `V_p,t`, view-rule,
  view-transition, observation-boundary, and audience-view rules. If it adds a
  cross-participant or surface-specific boundary, that boundary must be stated
  as an additional projection/constraint over those incumbents, not a second
  `visible/hidden` taxonomy.
- The current `### I1` through `### I18` headings are executable-test inputs to
  `test_participant_semantics_invariant_oracle.py`. Design-only changes may
  state new obligations and map them to existing invariants, but must not add a
  new `### I*` heading without intentionally extending that executable oracle in
  a spawned implementation issue.

### Preserve the three distinct tool concepts

- A **tool or artifact identity** names the thing and belongs to the existing
  concept-authority/reference surfaces.
- A **tool affordance** states a participant-meaningful operation or interaction
  opportunity. It must bind to action contracts, authority/scope, and
  observation effects; a label such as `shell`, `browser`, or `http-api` is not
  an executable action contract.
- A **tool-affordance expectation** is an apparatus manifest claim from
  `participant-tool-affordance-expectations`. It states what an implementation
  expects, not what the scenario author grants or what the runtime exposed.

`ParticipantExposurePolicyModel.tool_affordance_refs` may record selected
run-level references, but its free-form `constraints` map must not become the
normative affordance language. Realized availability needs explicit evidence or
provenance rather than inference from the manifest or policy alone.

### Preserve the two distinct decision-surface concepts

- `participant-decision-surface-modes` governs how an implementation makes or
  relays decisions (`autonomous`, `human-supervised`, `scripted`, and related
  terms). Reuse it for mode support and selection.
- The decision surface's **content and exposure** are a participant-visible
  projection. They require stable refs to existing contracts and view/policy
  bases; they are not another mode enum.

Do not rename or overload `behavior_mode`,
`supported_decision_surface_modes`, or `selected_decision_surface_mode` to carry
action lists, tool instances, prompts, instructions, observations, or policy
bodies.

### Issue #295 reuse verdict: keep the envelope, not the generic producer

The current `ParticipantContextViewModel` passes the ADR-083 reuse-first test as
the outer portable envelope. It already owns participant/episode scope,
observation point, governed source layers, transformation, `payload_ref`,
visibility projection, markings, redaction policy, evidence, provenance,
limitations, and comparability. Issue #295 must reuse those fields rather than
publish a second context/audience envelope.

The existing `ParticipantRetrievalMixin.get_participant_context_view()` producer
does **not** pass the semantic-projection test for `D(p,e,o)`. It accepts
caller-supplied `view_ref`, `derivation_basis_ref`, and `payload_ref`; permits
an absent episode; substitutes an episode id or `runtime.snapshot.current` for an
observation point; and projects the current snapshot without proving the
effective view relation at an order/event anchor. It remains a valid generic
API-408 reference-view producer, but issue #295 must not reuse it as proof of a
time-indexed decision surface or allow query parameters to manufacture semantic
refs.

A single new closed decision-surface payload contract is therefore justified.
`ParticipantContextViewModel.payload_ref` references that typed payload; it does
not embed a free-form map. The payload must be independently portable and carry
the required `D(p,e,o)` identity and surface facts, while a relational validator
or projection boundary verifies that its participant, episode, observation/order
point, derivation basis, visibility projection, evidence, and provenance agree
with the enclosing context view. Cross-contract obligations that JSON Schema
cannot express must use the existing `x-aces-invariants` convention. The payload
composes stable action-contract, affordance, observation-boundary,
implementation-selection, exposure-policy, evidence, and provenance refs; it
must not duplicate the referenced contracts.

The payload must use one discriminated surface-form union so open-ended,
constrained-form, and candidate-set selection meaning cannot be combined into an
ambiguous bag. Common surface and action-entry facts remain common; form-specific
defaults, normalization, omission, loss, membership, and open-extension meaning
live only on the applicable variant. These form values are not additions to
`participant-decision-surface-modes`.

Two current capability limits must remain explicit:

- `participant_action_admission_request_violations()` validates
  implementation selection, exposure-policy consistency, and result identity;
  it does not evaluate every SEM-211 precondition and does not validate action
  arguments. `ParticipantActionResult` and
  `validate_participant_action_result_contract()` enforce reported SEM-211
  precondition/effect/result consistency after an attempt. A surface must not
  rename either fact as pre-selection eligibility. It needs an order-scoped,
  fail-closed eligibility state with reason refs to the existing SEM-211
  precondition classes, and every selection still enters the existing admission
  path.
- No governed participant-action argument/parameter schema exists in the current
  action contract. Issue #295 must not claim argument-shape validation by using
  arbitrary dictionaries, SDL variables, experiment parameters, backend
  command shapes, or `ParticipantExposurePolicyModel.constraints`. The minimum
  missing seam is a governed selection/argument-shape reference plus a resolver
  that validates proposals before admission; unresolved shape, default,
  normalization, omission, or loss meaning fails closed or is explicitly
  `unsupported`/`unknown`. This seam maps selection to an existing action
  contract and does not redefine that contract's action meaning.

## Required Incumbents

- SDL ingress and authored semantics: `parse_sdl()`, `parse_sdl_file()`, safe
  YAML normalization, `SDLModel(extra="forbid")`, `Scenario`,
  `InstantiatedScenario`, variable-key rejection, `agents.*`,
  `action_contracts`, `observation_boundaries`, `behavior_specifications`, and
  existing authority/scope fields.
- SDL semantic validation: `SemanticValidator`,
  `analyze_participant_behavior()`, participant outcome analysis, named and
  targetable reference validation, controlled-vocabulary validation, and full
  post-instantiation revalidation.
- Compiled semantic addresses: `ParticipantBehaviorRuntime`,
  `ParticipantBehaviorSpecificationRuntime`,
  `ParticipantActionContractRuntime`,
  `ParticipantObservationBoundaryRuntime`, `ParticipantToolAffordanceRuntime`,
  and the existing `participant.*` address families produced by
  `aces_processor.compiler`.
- Visibility and audience projections: `ParticipantViewRule`,
  `ParticipantViewTransition`, `view_relation_timeline`,
  `_compile_view_relation_timeline()`,
  `_participant_behavior_observation_effective_relation()`,
  `ParticipantObservationEnvelopeModel`, `ParticipantContextViewModel`,
  `ParticipantStatusViewModel`, `ParticipantHistoryViewModel`, and the SEM-216
  audience-boundary validators. The existing effective-relation logic is the
  incumbent to expose/factor for reuse; a decision-surface projector must not
  copy its transition ordering and anchor-resolution algorithm.
- Apparatus and selection: `ParticipantImplementationManifestModel`,
  `ParticipantImplementationCapabilitiesModel`,
  `ParticipantImplementationSelectionModel`, `ParticipantExposurePolicyModel`,
  `ParticipantImplementationProvenanceModel`,
  `validate_experiment_apparatus_context_against_manifests()`, and
  `participant_action_admission_request_violations()`.
- Runtime admission and evidence: `ParticipantActionAdmissionRequest`,
  `participant_action_admission_request_violations()`, `RuntimeControlPlane`,
  `ParticipantRuntime.admit_action()`, `ParticipantActionPreconditionResult`,
  `ParticipantActionResult`, `validate_participant_action_result_contract()`,
  `ParticipantBehaviorHistoryEventModel`, `ParticipantActionResultModel`,
  `RuntimeSnapshot`, participant episode/behavior/history validators,
  shared-state and concurrency validators, and runtime conformance diagnostics.
- Contract and concept authority: `ContractModel`, `schema_bundle()`,
  `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/schema-publication-manifest.json`,
  `contracts/schema-publication/entries/`,
  `controlled-vocabularies-v1`, concept bindings,
  `validate_controlled_vocabulary_scope_values()`, and governed
  `x-<owner>:<term>` extensions.
- Security, persistence, errors, and audit:
  `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneIdentity`,
  `ControlPlaneRole`, request-size guards, request fingerprints, idempotency
  keys, `AuditEvent`, `ControlPlaneStore`, `InMemoryControlPlaneStore`,
  `LocalControlPlaneStore`, `Diagnostic`, `Severity`, `OperationReceipt`,
  `OperationStatus`, and the redacted FastAPI internal-error handler.
- Verification patterns: the existing participant semantic invariant oracle,
  SEM-208/210 and SEM-216 negative leakage tests, participant-manifest fixtures,
  participant-backend contract fixtures, control-plane authorization tests,
  runtime snapshot/conformance tests, RUN-306 lifecycle separation tests, and
  controlled-vocabulary tests. Human, script, LLM, and RL fixtures reuse stable
  semantic refs: LLM/RL are realization variants of the governed `agent`
  implementation kind, not new action or surface semantics.
- Repository policy: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`,
  `tools/check_concept_authority_governance.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_json_artifacts.py`, `tools/check_semantic_coverage.py`, and
  `tools/verify_all.py`. The participant section of `docs/explain/sdl/lineage.md`
  records SEM-220's exact ACES mappings, delivery status, evidence, and
  nonclaims. `contracts/provenance/sdl-lineage-ledger-v1.json` and
  `docs/research/lineage/source-audit-2026-07-12.md` change only if implementation
  changes a normative external derivation or compatibility claim.

## Cross-Cutting Layers

- **SDL and configuration shape:** any future authored surface must pass safe
  parsing, normalized keys, closed SDL models, stable symbol keys, variable
  rules, semantic reference resolution, and instantiated-scenario revalidation.
  Do not compile a decision surface from raw YAML dictionaries or backend
  config.
- **Concept and vocabulary authority:** reuse the existing decision-mode,
  tool-affordance-expectation, and exposure-policy vocabularies only for their
  current meanings. Add a governed term or concept binding only when portable
  comparison requires it; do not create artifact-local enums or accept arbitrary
  synonyms.
- **Contract/schema shape:** portable payloads must be closed `ContractModel`
  descendants and pass model plus JSON Schema validation. Published schema
  changes require normative schema review, reference `schema_bundle()` parity,
  valid/invalid fixtures, a v2 record under
  `contracts/schema-publication/entries/` with a current `last_change` hash, and
  compatibility classification under ADR-061. Adding a contract to a backend,
  processor, or participant-implementation support allowlist is a separate
  capability claim and occurs only when that component really consumes or
  produces the contract.
- **Participant visibility:** every participant-visible item must resolve at the
  relevant observation/order point through the compiled observation boundary,
  `V_p,t` timeline, exposure policy, source-layer transformation, audience
  scope, marking, redaction policy, evidence/provenance basis, and any disclosed
  weakening. Factor/reuse the effective-relation selector already embodied by
  `_participant_behavior_observation_effective_relation()`; do not implement a
  second timeline walk. Future visibility cannot justify earlier exposure.
- **Action admission:** a visible action or affordance is not necessarily
  eligible. Any admission path must reuse compiled action-contract addresses and
  SEM-211 authority, capability, target, knowledge, resource, temporal,
  interaction, and realization checks, then emit existing behavior-history and
  action-result records. `ParticipantAdmissionDisposition` describes an
  admission decision, not candidate eligibility, and the current admission
  request helper is not an argument or full-precondition validator.
- **Apparatus and provenance:** manifest support, selected mode, configuration
  ref/digest, and exposure policy must validate through the existing participant
  implementation and experiment apparatus/run models. Capability claims do not
  prove selection or realization; actual exposure requires runtime evidence and
  provenance.
- **Authentication and authorization:** any future HTTP read or mutation must
  enter through `create_control_plane_app()`, fail-closed security defaults,
  bearer/proxy identity validation, read-versus-mutating role dependencies,
  target binding, request-size limits, idempotency/request fingerprints for
  mutations, and audit recording. Participant authority, surface visibility,
  and control-plane caller authorization remain three different checks. Issue
  #295 requires no new HTTP endpoint; if the existing context route later
  returns a decision-surface ref, authenticated caller-supplied query values
  must never become the surface's semantic or derivation authority.
- **Secret handling and error envelopes:** credentials, bearer tokens, private
  keys, hidden prompts, answer keys, canaries, raw policy/configuration bodies,
  raw evidence payloads, environment dumps, backend-native object reprs, and
  full tracebacks must not enter SDL, portable contracts, context views,
  snapshots, diagnostics, audit details, fixtures, or public HTTP details. Use
  references, digests, markings, redaction policies, disclosure bases,
  limitations, and evidence/provenance records. Expected failures use collected
  SDL validation issues, structured `Diagnostic` values and operation
  envelopes, or bounded existing HTTP 4xx details; unexpected failures use the
  redacted 500 envelope. Do not add a participant-surface exception hierarchy.
- **Environment and OS exposure:** the semantic design introduces no new env
  binding or command-line shape. A later adapter must not put credentials,
  prompts, policy bodies, hidden material, or arbitrary user values in process
  argv, environment dumps, stdout/stderr, or shell command strings; it must use
  injected providers, controlled working directories, bounded timeouts, fixed
  invocation shapes, and no `shell=True`.
- **Persistence and observability:** live state remains in first-class
  `RuntimeSnapshot` fields and `ControlPlaneStore`; run/apparatus selection and
  archival claims remain in participant implementation and experiment-run
  provenance contracts. Reuse behavior history, observation envelopes,
  diagnostics, audit events, and evidence records for observability. Do not add
  a decision-surface store, authoritative current-surface cache, audit channel,
  log schema, or metadata/details side channel, and do not treat raw logs as
  participant-visible evidence. Historical claims must remain derivable from or
  referenced by the existing time-indexed behavior/visibility history and
  evidence; a final `RuntimeSnapshot` projection alone cannot prove an earlier
  surface after exposure changed.
- **Package and policy boundary:** authored semantics stay in `aces_sdl`,
  compiled projections in `aces_processor`, neutral DTOs in `aces_contracts`,
  live control/persistence/security in `aces_runtime`, protocols in
  `aces_backend_protocols`, and conformance in `aces_conformance`. The legacy
  `implementations/python/src/aces/` tree is compatibility-only.

## Extensibility Seam

The reusable seam is a time-indexed decision-surface projection/selector, not a
backend-specific runner or UI model. Its semantic inputs are:

- participant address and episode id;
- observation/order point and time/clock basis where relevant;
- surface form, projection-policy ref/revision, and selection-meaning ref;
- behavior-specification and action-contract refs;
- governed selection/argument-shape and constraint refs;
- observation-boundary/view-relation ref;
- participant implementation selection and decision-control mode;
- exposure-policy ref/version/digest and realized affordance refs;
- evidence, provenance, marking, redaction, limitation, and comparability refs.

The next reasonable variants should fit by changing those parameters: another
participant implementation, a per-phase surface, a new governed affordance
category, a weaker backend realization, or another audience projection. A
per-phase or per-action surface should add an explicit selection-context
parameter, not overload the mode vocabulary or fork the visibility model. The
order-relative view selector must remain one shared incumbent used by behavior
history validation and surface projection, so a new clock/order basis extends
one selector rather than creating divergent visibility algorithms.

## Gotchas And Anti-Patterns

Avoid:

- treating a tool name, package, binary, browser, shell, HTTP endpoint, ATT&CK
  label, CVE, command, prompt, or UI control as an ACES action contract;
- treating tool-affordance expectation, authored grant, run selection, realized
  exposure, invocation, output observation, and evidence as one `tools` list;
- treating decision-control mode as decision-surface content, participant role,
  interaction topology, authority, or control-plane permission;
- treating a visible action as currently applicable, authorized, supported, or
  successfully admitted;
- treating `ParticipantAdmissionDisposition` or a successful historical
  `ParticipantActionResult` as the candidate's pre-selection eligibility state;
- treating `participant_action_admission_request_violations()` as argument-shape
  validation or as the complete SEM-211 applicability evaluator;
- treating caller-supplied `view_ref`, `payload_ref`, an episode id, or
  `runtime.snapshot.current` from the generic context-view producer as a proved
  decision-surface order/derivation anchor;
- treating network reachability, `operating_scope`, backend sandboxing, control
  plane authorization, and information visibility as equivalent boundaries;
- collapsing `hidden`, `withheld`, `evidence_only`, `concealed`, `unsupported`,
  `unknown`, and `not_applicable`;
- using future disclosure to justify earlier visibility or recording only the
  final aggregate surface without its observation/order point;
- exposing world truth, raw archival evidence, evaluator state, private answer
  material, hidden prompts, credentials, or backend-private ids through a
  participant decision surface;
- turning `ParticipantExposurePolicyModel.constraints`, snapshot `metadata`,
  history `details`, audit details, or logs into an untyped policy/surface bag;
- placing raw proposal arguments, JSON Schema bodies, form defaults,
  normalization rules, or lossy mappings in those bags instead of resolving a
  governed selection-shape reference;
- adding `llm`, `rl`, or UI-specific participant semantics when the existing
  `agent`, `human-control-proxy`, `script`, decision-control mode, configuration,
  provenance, and realization disclosures already express the variation;
- duplicating action, affordance, visibility, exposure, mode, failure, or
  support vocabularies in Python, schemas, docs, CLI, API, or backend code;
- adding a second DTO layer, schema registry, validator stack, exception
  hierarchy, persistence store, audit/log path, fixture loader, conformance
  runner, or workflow/admission path;
- hand-editing implementation code as semantic authority, hand-editing a schema
  without publication/generator parity, or weakening an accepted ADR in place;
- marking SEM-219, SEM-220, or SEM-226 active/complete from ADR/spec prose alone.

## Non-Goals And Implementation Boundaries

- Implementing the ADR/spec, spawned issues #294-#296, SDL fields, parsers,
  validators, compiler records, runtime projections, contracts, schemas,
  fixtures, APIs, adapters, storage, conformance, or tests in this preflight.
- Designing a participant UI, agent framework, shell/RPC protocol, generic tool
  runner, prompt format, policy engine, credential broker, or OS sandbox.
- Designing a general action-parameter language or changing governed action
  meaning. SEM-220 owns the minimum selection/argument-shape binding needed to
  map a surface choice to an existing action contract; it does not turn UI,
  prompt, command, or backend-native schemas into action authority.
- Replacing participant action contracts, SEM-210 visibility, SEM-211
  applicability/failure, SEM-214 context views, SEM-216 audience boundaries,
  participant implementation provenance, or backend feature support.
- Redesigning control-plane authentication/authorization, persistence, audit,
  diagnostics, schema publication, concept authority, observability/evidence
  planes, or experiment-run provenance.
- Defining trajectories, demonstrations, budgets, quotas, full clock semantics,
  reward/scoring, or evidence-capture adequacy beyond preserving their existing
  boundaries.
- Publishing secrets, hidden truth, raw configuration, raw evidence, or
  backend-private data as portable participant semantics.
