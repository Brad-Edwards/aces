# Issue 294 SEM-219 Participant Tool And Affordance Preflight

Date: 2026-07-18

Issue: #294. Requirement: SEM-219.

This note fixes the repository-wide implementation boundary for governed
participant tool-affordance bindings. It is guidance only: it does not add SDL
fields, schemas, compiler records, runtime admission, exposure enforcement, or
an implementation plan.

ADR-083 and the SEM-219 section of the participant formal specification are
already sufficient design authority. No new ADR or parallel formal model is
needed for this issue.

## Binding Decision

The authored home is the existing first-class
`ParticipantBehaviorSpecification`, because it already binds participant or
role scope, action contracts, observation boundaries, authority/scope,
realization expectations, and evidence contracts. Extend that aggregate with
a keyed, closed `tool_affordances` mapping. Do not add a global `tools` list, a
second participant section, or a free-form behavior-specification extension.

Each mapping key is a stable local affordance-binding id. Each closed value has
only the minimum relations that are not already owned elsewhere:

- optional `tool_ref`, resolving to an existing governed tool/artifact identity
  when ACES has one;
- non-empty `action_contract_refs`; and
- non-empty `observation_boundary_refs`.

The containing behavior specification supplies participant/role scope,
authority/scope refs, lifecycle/version, realization refs, and evidence-
contract refs. Referenced action contracts supply all parameter, authority,
capability, target, knowledge, resource, temporal, interaction, and realization
preconditions; effects; failure classes; observation effects; and evidence
expectations. A binding cannot select only convenient preconditions or override
their state. Referenced observation boundaries supply visibility state and
ordered transitions. The binding carries no duplicate constraints, effects,
evidence, visibility, support, or policy body.

`tool_ref` is an identity reference, not a label, executable, command, URL,
package coordinate, ATT&CK id, UI control, or implementation expectation. It
must resolve unambiguously through the existing declaration/concept-authority
path to a declaration governed as `tools-and-artifacts`. The current reusable
portable reference-model anchor is scenario content. Do not accept every
generic named or targetable declaration merely because `_validate_named_ref()`
can resolve it. If the repository cannot prove a declaration belongs to the
tool/artifact family, omit the optional identity or extend the canonical
concept/reference authority; never add a validator-local kind list or accept a
raw `shell`/`browser` label as identity.

The binding refs are refinements of their containing specification: action and
observation refs must be subsets of the parent specification's corresponding
refs. For every explicitly or role-resolved participant, they must also agree
with the existing `Agent.actions` and `Agent.observation_boundaries` bindings;
the tool-affordance layer cannot widen participant action or view authority.
Parent authority/scope and participant authority/scope compose deny-first; the
effective scope is never their union by convenience.

Visibility remains explicit. Each applicable observation boundary must classify
the affordance binding's authored reference through its existing declared refs,
view rule, and transition model. Presence in `tool_affordances` means authored
availability only. It does not mean observable, supported, eligible, admitted,
selected, invoked, realized, or evidenced.

Exact duplicate relations within one behavior specification are invalid;
mapping order has no priority or fallback meaning. One governed tool identity
may participate in several distinct bindings, and one action contract may be
bound to different tool identities, provided each binding retains its own
identity and visibility relation.

## Compilation Boundary

Compilation must assign each binding a canonical address under its owning
behavior specification, for example:

```text
participant.behavior-specification.<spec>.tool-affordance.<binding-id>
```

The typed compiler record preserves its raw authored refs and resolved
canonical addresses: its own identity, owning behavior specification, tool
identity when present, action contracts, and observation boundaries. Participant
or role scope, authority/scope, lifecycle, and evidence-contract refs remain on
the owning `ParticipantBehaviorSpecificationRuntime` and are reached through
that address rather than copied into every affordance. Downstream code likewise
joins to existing action-contract and observation-boundary records rather than
receiving copied preconditions, effects, constraints, or visibility state.

This is semantic compiler IR only. It is not a provisioning resource, planner
operation, backend payload, runtime tool instance, or proof of support. Do not
place it in opaque `agent_specs`, backend metadata, or `resource_payload()` as
the only consumer contract.

`ParticipantExposurePolicyModel.tool_affordance_refs` may later name the
canonical binding address, but its current validator accepts non-empty strings
and does not resolve them. It is not a substitute for SDL reference validation
or proof of exposure. Likewise, `ParticipantActionAdmissionRequest` and
`participant_action_admission_request_violations()` validate the existing
participant/action binding, manifest/selection, exposure-ref, and result
consistency; they are not by themselves proof that every SEM-211 precondition
was evaluated. Issue #294 must preserve complete constraint meaning for later
admission without claiming the runtime enforcement owned by #296/#799.

## Canonical Incumbents To Reuse

- **SDL shape and ingress:** `SDLModel(extra="forbid")`,
  `ParticipantBehaviorSpecification`, `Scenario`/`ScenarioContent`,
  `InstantiatedScenario`, `parse_sdl()`, `parse_sdl_file()`, the safe YAML
  loader/source limits, normalized structural keys, portable identifiers,
  variable-key rejection, and declared whole-field variable substitution.
- **Composition and references:** `HASHMAP_SECTIONS`, `NESTED_HASHMAP_FIELDS`,
  `_module_symbols`, the existing composition rewriters, `DeclarationIndex`,
  `specs/sdl/references.md`, `REFERENCE_COMPLETION_TARGETS`, and
  `tools/check_sdl_catalog_parity.py`. Extend these registries; do not parse
  dotted refs with `split()` or build a tool-only symbol service.
- **Semantic validation:** `SemanticValidator`,
  `analyze_participant_behavior()`, the participant issue-code/rendering path
  in `validator/_content_objectives.py`, `_validate_named_ref()`, existing
  participant/role/action/observation/authority resolution, and collected
  `SDLValidationError` reporting.
- **Action and visibility authority:** `ParticipantActionContract`, typed
  SEM-211 preconditions/effects/failures, `ParticipantObservationBoundary`,
  `ParticipantViewRule`, `ParticipantViewTransition`, and the compiled
  `view_relation_timeline`. The affordance binding references these; it does not
  reimplement them.
- **Instantiation/admission:** `instantiate_scenario()`,
  `admit_instantiated_scenario()`, closed phase contracts, portable derivation
  evidence, unresolved-token rejection, and full post-substitution semantic
  revalidation.
- **Compilation:** `aces_processor.compiler.participant_behaviors`, existing
  address builders and alias index, `ParticipantBehaviorSpecificationRuntime`,
  `ParticipantBehaviorRuntime`, `ParticipantActionContractRuntime`,
  `ParticipantObservationBoundaryRuntime`, `RuntimeModel` address uniqueness,
  and `require_compiled_address()`.
- **Concept and apparatus authority:** `tools-and-artifacts`, the existing
  reference-model/concept-binding catalogs,
  `ParticipantImplementationManifestModel`,
  `ParticipantImplementationSelectionModel`,
  `ParticipantExposurePolicyModel`, and the existing controlled-vocabulary
  helpers. `participant-tool-affordance-expectations` remains manifest-only
  apparatus metadata and must not become authored affordance meaning.
- **Contracts and publication:** the three hand-governed SDL schemas,
  `schema_bundle()`, `contracts/schema-publication-manifest.json`,
  `contracts/fixtures/`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, and `tools/check_json_artifacts.py`.
- **Errors, diagnostics, and assurance:** `SDLParseError`,
  `SDLValidationError`, `SDLInstantiationError`, `Diagnostic`, `Severity`, the
  existing participant invariant/SEM-208/SEM-211 tests, module-composition and
  phase tests, compiler model tests, schema-parity tests, and lineage/policy
  gates. Do not add an affordance exception or diagnostic hierarchy.

## Cross-Cutting Gates And Security Posture

- **Source/parser gate:** the SDL remains behind the existing UTF-8, size,
  alias/depth/node/tag/directive, safe-YAML, normalized-key, and closed-model
  checks. Binding ids are concrete portable identifiers; `${...}` cannot create
  or rename them. Reference values may use only the existing declared
  whole-field-variable rules and must be concrete after instantiation.
- **Shape/config gate:** the closed binding admits refs only. It has no command,
  arguments, executable, host, port, URL, environment, provider options,
  working directory, prompt, credential, policy text, or arbitrary
  `constraints`/`metadata` map. There is no new env var, CLI flag, config file,
  or backend configuration shape.
- **Semantic-reference gate:** dangling, ambiguous, stale, cross-family,
  out-of-parent, out-of-participant, and unclassified visibility refs fail
  closed in the collect-all semantic pass. Empty lists, duplicate refs, exact
  duplicate bindings, and an action not backed by a governed action contract
  are invalid. Apparatus support cannot repair authored invalidity.
- **Instantiation gate:** module composition rewrites all three reference
  families through the canonical symbol maps. Instantiation and direct artifact
  admission rerun structural and semantic checks; an unresolved or newly
  conflicting binding cannot reach the compiler.
- **Constraint/admission gate:** every action-contract precondition remains in
  force. Unknown, unresolved, stale, exhausted, or unsupported constraint state
  is not converted to a local default or omitted from compiled meaning. Runtime
  invocation is outside this issue and must later pass the existing participant
  address binding plus the complete SEM-211/RUN-319 decision path.
- **Concept/apparatus gate:** authored identity/meaning, manifest expectation,
  selected implementation/policy, and realized support remain independent.
  Do not add an authored enum duplicating
  `participant-tool-affordance-expectations`, infer identity from that category,
  or validate support by string equality with a tool label.
- **Contract/schema gate:** the authoring, instantiated, and instantiated-
  snapshot schemas move together, each with publication-manifest `last_change`
  and content hash, generated-bundle parity, compatibility classification, and
  valid/invalid fixture or equivalent schema coverage. The published schemas
  remain normative; Python generation alone does not authorize their change.
- **Authentication/authorization gate:** issue #294 adds no HTTP surface. Any
  later API must still use `create_control_plane_app()`,
  `ControlPlaneSecurityConfig.strict_defaults()`, bearer or verified-proxy
  identity, target-bound read/mutating roles, request-size guards, mutation
  fingerprints/idempotency, and audit recording. Scenario participant authority
  is not control-plane caller authorization.
- **Secret-handling gate:** bearer tokens, keys, passwords, credential values,
  private prompts, answer material, raw policy/configuration bodies, backend
  objects, and evidence payloads never enter bindings, fixtures, diagnostics,
  snapshots, audit details, or lineage records. Use governed refs/digests,
  markings, redaction policies, and evidence/provenance carriers.
- **Host/OS exposure gate:** parsing and compilation create no process,
  listener, route, firewall rule, session, file execution, or shell command.
  They place no user value or secret in process argv, environment dumps,
  stdout/stderr, or command strings. A later adapter must use fixed invocation
  shapes, injected secret providers, bounded timeouts, controlled working
  directories, and no `shell=True`.
- **Error-envelope gate:** structural failures remain bounded,
  source-anchored `SDLParseError` diagnostics; semantic failures remain
  collected `SDLValidationError` values; instantiation failures remain
  `SDLInstantiationError`; processor/runtime failures use structured
  `Diagnostic` values. Expected HTTP failures use bounded existing 4xx details,
  and unexpected failures retain the redacted
  `{"detail":"internal server error"}` envelope. Do not echo full SDL,
  commands, native exceptions, or backend payloads.
- **Persistence/observability gate:** the authored binding persists through SDL
  and phase artifacts and is carried in typed compiler IR. It creates no store,
  cache, audit stream, log schema, runtime snapshot field, history event, or
  evidence claim. Later realization must reuse `RuntimeSnapshot`,
  `ControlPlaneStore`, behavior history, action results, observation envelopes,
  audit events, and evidence/provenance records; raw logs are not exposure
  evidence.
- **Package/workflow gate:** authored models and rules remain in `aces_sdl`,
  compiled IR in `aces_processor`, neutral published DTOs in `aces_contracts`,
  runtime control/security/persistence in `aces_runtime`, and conformance in
  `aces_conformance`. Do not add logic to compatibility-only
  `implementations/python/src/aces/` or import `aces.*` from owning packages.

## Extensibility Seam

The extension seam is the stable affordance-binding address plus references,
not a backend runner or category enum. The next issues can project that address
for `(participant, episode, order point, policy revision)` and independently
attach eligibility, admission, selected implementation, support, exposure, and
realization evidence without changing the authored binding's meaning.

A new tool identity kind extends the canonical `tools-and-artifacts`
reference/declaration resolver. A per-phase or conditional availability variant
adds a typed selection-context or condition reference at the binding seam. A
different backend or participant implementation changes manifest/selection
parameters. None should require another tools list, another action schema, or a
new visibility model.

## Gotchas And Anti-Patterns

Avoid:

- treating `tool_affordance_expectations`, exposure-policy refs, backend
  reachability, installed software, interactive access, or OS accounts as an
  authored participant grant;
- treating a tool label, command, ATT&CK/CVE id, package name, URL, prompt, or
  UI control as an action contract or governed tool identity;
- placing the binding on both `Agent` and `ParticipantBehaviorSpecification`,
  creating two availability authorities;
- allowing a binding to widen its parent action, observation, participant, or
  authority scope, or to discard action-contract preconditions/effects;
- adding `available`, `visible`, `supported`, `eligible`, `invocable`,
  `realized`, or `success` booleans to collapse independent predicates;
- putting normative constraints into
  `ParticipantExposurePolicyModel.constraints`, manifest `constraints`,
  behavior-specification `extensions`, snapshot `metadata`, history `details`,
  audit details, or logs;
- treating `ParticipantActionAdmissionRequest` construction, schema validity,
  policy selection, or a final action result as proof of prior visibility,
  complete constraint evaluation, invocation, or realized exposure;
- adding a new vocabulary, schema registry, resolver, validator stack,
  exception hierarchy, persistence store, logger, audit path, workflow, API,
  or backend protocol for affordances; and
- claiming SEM-219 active/complete from syntax and compilation alone without
  the required semantic/compiler/schema evidence and traceability update.

## Non-Goals And Workflow Boundary

Issue #294 does not implement a flat tools catalog, tool runner, shell/RPC
protocol, external-agent API, UI/prompt format, credential broker, OS sandbox,
participant session, command executor, decision-surface projection, realized
exposure, information-flow gateway, runtime policy enforcement, persistence,
or new control-plane route. Issues #295/#296 and the RUN-319/API-423 program own
the downstream surface, exposure, crossing, and runtime enforcement layers.

The implementation must update the participant section of
`docs/explain/sdl/lineage.md` with exact adopted source-to-ACES mappings,
delivery status, evidence, and explicit nonclaims. The lineage ledger and source
audit change only when normative derivation or compatibility claims change;
they are not edited merely to list another implementation file.

Repository completion remains subject to `.ground-control.yaml`,
`.gc/plan-rules.md`, the three SDL schema publication rules, SDL catalog parity,
concept-authority governance, lineage and semantic-coverage gates, requirement
traceability, the canonical nox verification graph, and `tools/verify_all.py`.
No changelog or version edit belongs to this issue.
