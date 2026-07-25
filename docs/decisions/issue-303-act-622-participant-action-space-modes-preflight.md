# Issue 303 ACT-622 Participant Action-Space Modes Preflight

Date: 2026-07-25

Issue: #303. Requirement: ACT-622.

This note fixes the repository-wide implementation boundary for ACT-622. It is
guidance only: it adds no action-space mode, SDL syntax, contract, schema,
runtime behavior, backend branch, API, persistence, or implementation plan.

ADR-083, the SEM-220 formal specification, and the delivered SEM-220 contract,
projection, and selection binding already define the required three forms. The
issue's clause-mapping pass also confirmed a narrower missing incumbent:
`ParticipantActionContract` did not yet carry the governed argument definition
that ADR-022 and SEM-220 require. That definition belongs on the existing action
contract and its compiled runtime record; it does not require a new ADR, action
model, mode vocabulary, global action-space field, or backend contract.

## Binding Decision

ACT-622 reuses the existing participant decision-surface model:

| ACT-622 clause | Canonical incumbent |
| --- | --- |
| open-ended action generation | `ParticipantDecisionSurfaceOpenEndedFormModel` |
| constrained action forms | `ParticipantDecisionSurfaceConstrainedFormModel` |
| enumerated candidate-action sets | `ParticipantDecisionSurfaceCandidateSetFormModel` |

The three forms remain variants of the closed, discriminated
`ParticipantDecisionSurfaceFormModel` union carried by
`participant-decision-surface-v1`. They describe surface content and selection
meaning. They are not values of `participant-decision-surface-modes`, which
describes how an implementation makes or relays decisions (`autonomous`,
`human-supervised`, `scripted`, and related terms).

Keep these axes separate:

- a governed action contract defines action meaning;
- the surface form defines how a proposal or choice binds to an action;
- `decision_control_mode` and the participant implementation selection define
  how the decision is made or relayed;
- action-entry membership, visibility, eligibility, apparatus support,
  argument-shape validity, admission, execution, result, and outcome are
  independent facts; and
- human, script, LLM, and RL integrations are apparatus realizations, not new
  action-space semantics.

Backend independence comes from resolving the form above the backend boundary.
Every form must produce a governed `ParticipantDecisionSurfaceSelectionModel`,
pass `bind_participant_decision_surface_selection()`, and enter the existing
`ParticipantActionAdmissionRequest` path. Backends consume the admitted action;
they must not reinterpret open, constrained, or candidate forms into
backend-native action meaning.

The same boundary applies to concrete arguments. Authored action contracts own
their closed domains and disclosures, compilation binds those domains to the
compiled action-contract address with a canonical shape identity, the surface
must agree with that identity, and selection binding attaches one immutable
normalized carrier to the admission request. A Boolean resolver result or a
caller-selected shape ref is not sufficient semantic authority.

## Canonical Incumbents To Reuse

- **Normative authority:** ADR-083,
  `specs/formal/participant-semantics/README.md` SEM-220,
  `contracts/schemas/control-plane/participant-decision-surface-v1.json`, its
  valid/invalid fixtures, and its schema-publication entry.
- **Portable contracts:** `ContractModel(extra="forbid")`,
  `ParticipantDecisionSurfaceModel`, the three form models,
  `ParticipantDecisionSurfaceActionEntryModel`,
  `ParticipantDecisionSurfaceSelectionModel`, `schema_bundle()`, the relational
  model validators, and `x-aces-invariants`.
- **Projection and visibility:** `ParticipantDecisionSurfaceProjectionInput`,
  `project_participant_decision_surface()`,
  `participant_observation_effective_relation()`, compiled participant/action/
  affordance/observation-boundary addresses, behavior history, and the SEM-226
  exposure resolvers. There must be no second view-timeline walk.
- **Selection and admission:** compiled action argument definitions,
  `resolve_participant_action_arguments()`,
  `ParticipantValidatedActionSelection`,
  `ParticipantDecisionSurfaceArgumentShapeResolver`,
  `ParticipantDecisionSurfaceApparatusResolver`,
  `bind_participant_decision_surface_selection()`,
  `ParticipantActionAdmissionRequest`,
  `participant_action_admission_request_violations()`,
  `ParticipantControlMixin.admit_participant_decision_surface_selection()`, and
  the existing backend-neutral `ParticipantRuntime.admit_action()` protocol.
- **Context, apparatus, and provenance:** `ParticipantContextViewModel`,
  `validate_participant_decision_surface_context()`,
  `ParticipantImplementationManifestModel`,
  `ParticipantImplementationSelectionModel`,
  `ParticipantExposurePolicyModel`, participant implementation provenance,
  behavior/episode history, observation envelopes, action results, and evidence
  and provenance refs.
- **Errors, observability, and persistence:** collected SDL errors when authored
  semantics are involved, `Diagnostic`, `Severity`, `OperationReceipt`,
  `OperationStatus`, `RuntimeSnapshot`, `ControlPlaneStore`,
  `InMemoryControlPlaneStore`, `LocalControlPlaneStore`, and `AuditEvent`.
- **Repository workflow:** `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, the schema publication/generated-schema checks, concept and
  authority governance, requirement governance, participant semantic tests, and
  `tools/verify_all.py`. Published schemas remain the hand-governed authority;
  Python generators must reproduce them exactly.

## Cross-Cutting Gates

- **Shape and semantic-source gate:** do not add a second action-space DTO or
  enum. A surface form must resolve from a governed projection/selection basis,
  not from a backend dictionary, prompt convention, UI widget, query parameter,
  environment value, or caller assertion. The current projection input accepts
  a mapping and validates the resulting closed contract; that convenience is
  not semantic authority.
- **Identity gate:** preserve the distinction between a surface-local
  `entry_id` and its canonical `action_contract_address`. Candidate and
  constrained forms reference entry ids; open-ended forms reference allowed
  action-contract addresses. Do not depend on the current fixtures' coincidence
  that entry ids equal action addresses, and do not let projector code interpret
  one identifier family as the other without an explicit index/validation rule.
- **Contract/schema gate:** reuse the form vocabulary in
  `participant-decision-surface-v1` unchanged. The bounded argument-domain
  addition belongs to `ParticipantActionContract` and therefore updates the
  affected hand-governed SDL schemas and their publication ledger. Any real
  contract change must update
  the hand-governed published schema, matching contract model and bundle,
  focused fixtures, compatibility classification, and the publication
  `last_change` hash. Do not register a backend or participant-implementation
  support claim unless that component really consumes or produces the contract.
- **Visibility and exposure gate:** every emitted context, action, and affordance
  ref must pass the participant/episode/order-scoped compiled view relation,
  audience, effective projection and exposure policies, markings, redaction,
  evidence, provenance, and limitations. Missing, stale, global, future, or
  unresolved state fails closed.
- **Selection/admission gate:** candidate membership is not eligibility.
  Open-ended generation is not execution authority. Constrained-form defaults,
  normalization, omission, and loss remain explicit refs. Every selected
  proposal resolves a governed action and argument shape before the existing
  SEM-211 admission and result/history paths.
- **Authentication/authorization gate:** ACT-622 requires no new HTTP endpoint.
  Any later endpoint must enter through `create_control_plane_app()`,
  `ControlPlaneSecurityConfig.strict_defaults()`, bearer or verified-proxy
  identity, target-bound read/mutating roles, request-size limits, mutation
  fingerprints/idempotency, and audit. Caller authorization, participant
  authority, and participant-visible exposure remain separate gates.
- **Secret and OS-exposure gate:** forms and selections carry safe refs and
  digests, not credentials, bearer tokens, private prompts, answer material,
  raw policy/configuration, raw evidence, backend object representations, or
  environment dumps. This requirement adds no env binding, listener, process,
  filesystem execution, or CLI shape. A later adapter must not place user
  proposals or secrets in argv, shell strings, stdout/stderr, or environment
  dumps; use fixed invocation shapes, injected providers, bounded timeouts, and
  no `shell=True`.
- **Error-envelope gate:** contract failures remain bounded Pydantic/relational
  validation failures converted to existing structured diagnostics at runtime.
  Expected HTTP failures use bounded existing 4xx details; unexpected failures
  retain the redacted `{"detail":"internal server error"}` envelope. Do not add
  an ACT-622 exception hierarchy or expose native resolver exceptions.
- **Persistence and observability gate:** preserve surfaces and decisions through
  existing context, behavior-history, observation, result, snapshot, evidence,
  provenance, operation, and audit carriers. Do not add an action-space store,
  current-surface cache, event stream, audit channel, logger, or metadata/details
  side channel. Audit and raw logs are not participant-visible evidence.
- **Package boundary:** neutral DTOs stay in `aces_contracts`, projection logic
  in `aces_processor`, live admission/security/persistence in `aces_runtime`,
  backend protocols in `aces_backend_protocols`, and conformance in
  `aces_conformance`. The compatibility-only `implementations/python/src/aces/`
  tree receives no new implementation logic.

## Extensibility Seam

The reusable seam is the typed surface-form discriminator plus its governed
selection-meaning, argument-shape, validation-policy, constraint, disclosure,
and extension-binding refs, evaluated for one participant, episode, and
observation order. The form is a parameter to the shared time-indexed projector;
it is not a backend class or decision-control mode.

A per-phase surface adds an explicit selection-context coordinate. A fourth
portable form extends the discriminated contract under normal schema
compatibility/versioning review. A new participant implementation or backend
changes apparatus/support/provenance inputs. None of those changes should
require another action model, visibility relation, admission workflow, or
backend-specific form branch.

## Gotchas And Anti-Patterns

Avoid:

- adding `open-ended`, `constrained`, or `enumerated` to
  `participant-decision-surface-modes`;
- adding another `action_space`, `actions`, `choices`, `tools`, or
  backend-native schema alongside `participant-decision-surface-v1`;
- treating tool identity, tool affordance, interaction channel, control mode,
  implementation kind, surface form, and action contract as synonyms;
- interpreting candidate membership or presentation as visibility,
  eligibility, support, selection, admission, execution, success, or outcome;
- allowing free-form generation to invent an action/argument schema or bypass
  argument validation and SEM-211 admission;
- hiding constrained-form defaults, normalization, omission, coercion, or loss
  in code, UI metadata, prompts, or policy `constraints`;
- computing candidates from global, hidden, stale, or future-visible state;
- treating caller-supplied form mappings or semantic refs as trusted projection
  authority;
- duplicating validators, controlled vocabularies, exception hierarchies,
  schema registries, persistence stores, log/audit paths, conformance runners,
  or backend workflows; and
- changing a published schema, capability allowlist, or traceability status
  merely to create ACT-622-specific naming when the existing SEM-220 artifact
  already carries the requirement.

## Non-Goals And Implementation Boundary

- Designing a UI, prompt format, form renderer, agent framework, RL space,
  generic tool runner, shell/RPC protocol, command grammar, credential broker,
  or OS sandbox.
- Making action-space form a global participant attribute or adding a parallel
  argument/policy language. Bounded portable argument domains remain local to
  governed action contracts; a current surface is participant-, episode-, and
  order-scoped.
- Replacing action contracts, tool-affordance bindings, visibility/exposure
  semantics, participant implementation selection, action admission, runtime
  lifecycle, outcome interpretation, backend capability declarations, or
  control-plane security.
- Defining rewards, scoring, trajectories, demonstrations, budgets, quotas, or
  complete policy/argument languages.
- Claiming that a manifest, selected mode, surface presentation, audit record,
  or backend support statement proves realized participant exposure or action
  execution.
