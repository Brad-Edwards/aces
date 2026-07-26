# Issue 909 RUN-311 / SEM-220 Order-Zero Anchor Preflight

Date: 2026-07-26

Issue: #909.

Requirements: none. The GitHub issue is the authoritative contract.

This note records architecture guardrails for integrating RUN-311 episode
readiness with the existing SEM-210/SEM-220 projection. It is non-normative
preflight guidance. It does not implement a projector, contract, schema,
control-plane operation, persistence path, or test.

## Existing Authorities

- ADR-013 and `raes_contracts.participant_episode` own participant-episode
  identity, state, control actions, lifecycle history, reset/restart, and
  `sequence_number`.
- ADR-022 and `specs/formal/participant-semantics/README.md` own action-linked
  participant behavior history, `V_p,t`, observation boundaries, visibility
  transitions, and the separation of participant-visible state from world truth
  and archival evidence.
- ADR-054 owns the separation between episode lifecycle and observable behavior
  lifecycle. A silent episode with empty behavior history is valid; no bootstrap
  action may be invented to make a history non-empty.
- ADR-083, `ParticipantDecisionSurfaceModel`,
  `ParticipantDecisionSurfaceProjectionInput`, and
  `project_participant_decision_surface()` own `D(p,e,o)`, including its
  participant/episode scope, compiled semantic inputs, context/exposure
  projection, order/event/evidence basis, and selection meaning.
- The issue-119 preflight remains the cross-cutting authority for SEM-219,
  SEM-220, and SEM-226 reuse, security, persistence, errors, and package
  boundaries. This note narrows the unresolved initial-anchor and ordering
  relationship; it does not fork that design.

## Architecture Decision And Guardrails

### Use one typed projection anchor, not a third history

The projection boundary needs a small, closed, public projection-anchor value
or equivalent tagged contract. It references exactly one event from exactly one
of the two existing histories:

- an **episode-readiness anchor** references a RUN-311
  `ParticipantEpisodeHistoryEvent`; or
- a **behavior-event anchor** references a
  `ParticipantBehaviorHistoryEvent`.

The two histories remain separate typed inputs. Do not create a heterogeneous
event list, add episode lifecycle values to
`ParticipantBehaviorHistoryEventType`, add action fields to episode history, or
depend on Python duck typing.

The anchor must carry or resolve, without caller-authored semantic strings:

- participant address and episode id;
- per-episode decision-surface order;
- anchor kind and stable event reference;
- the anchor's order in its owning history domain;
- evidence/provenance references supporting the projection; and
- for a behavior anchor, the exact behavior-history prefix used to derive
  `V_p,o`.

Lifecycle order, decision-surface order, and behavior-history order are
different coordinates. A field may not silently change meaning by anchor kind.
If the published decision-surface v1 carrier cannot represent those coordinates
without overloading `observation_order` or encoding structure into
`observation_point`, the contract must be compatibility-classified and
versioned under ADR-061. Do not silently reinterpret an existing v1 field.

A typed event proves shape, not authority. The anchor must be resolved against
the current trusted `RuntimeSnapshot` lifecycle result/history and, for later
surfaces, the exact participant-local behavior-history prefix. A caller-created
event object, event-ref string, final snapshot, or isolated history fragment is
not sufficient.

### `episode_running` is the readiness anchor

`episode_initialized` records creation of the first episode identity and its
initialize control action. It precedes readiness and is not sufficient to expose
participant context or accept a decision.

`episode_running` is the authoritative readiness anchor for every new episode:

- for the first episode it follows `episode_initialized`;
- for reset it follows `episode_reset`; and
- for restart it follows `episode_restarted`.

The readiness resolver must require exact participant and episode agreement, a
RUNNING live result, a valid lifecycle history whose matching
`episode_running` event is in the current episode scope, and agreement between
the live result and history head under
`iter_participant_episode_snapshot_violations()`. A terminal, superseded,
cross-participant, or previous-episode running event fails closed.

RUN-311 `sequence_number` identifies the participant's episode generation. It is
not lifecycle-event order, decision-surface order, behavior-step order, an
action count, or a visibility-transition order.

### Portable ordering relationship

For a newly initialized episode, the required causal order is:

| Domain | Order | Meaning |
| --- | ---: | --- |
| episode lifecycle | first event in the new scope | `episode_initialized` for the first episode, or `episode_reset` / `episode_restarted` for a successor episode |
| episode lifecycle | next event in the same scope | `episode_running`; authoritative readiness anchor |
| projection | derived from the readiness anchor | initial participant context from SEM-210 `V_p,0`, with the existing boundary, audience, exposure, marking, redaction, evidence, provenance, and apparatus gates |
| decision surface | 0 | `D(p,e,0)`, sharing the readiness/event/evidence basis with its context view; behavior history is still empty |
| decision lifecycle | after surface 0 | proposal and selection reference surface 0; neither is an action attempt |
| behavior history | 0 | the first admitted `action_attempted` event |
| behavior history | subsequent ordered events | the admitted action's state transition and terminal observation under the existing action-instance discipline |
| decision surface | 1 | the next surface, anchored to the applicable terminal observation and its behavior-history prefix |

The current canonical admission path appends
`action_attempted -> state_transition_recorded -> observation_emitted`
consecutively. The projection abstraction must nevertheless key later surfaces
to the exact behavior event reference and behavior-history order, not to
arithmetic such as `3*n+2`; that preserves the seam for long-running,
orphaned-action, partial-order, or future lifecycle variants.

Reset and restart create a new `episode_id`, increment RUN-311
`sequence_number`, and restart decision-surface order at zero with empty
behavior history for the new episode. They never reuse the prior episode's
initial anchor, surface, selection, proposal, behavior prefix, or exposure
authorization.

### Preserve the existing visibility and selection paths

The initial anchor changes only how the initial relation is grounded. `V_p,0`
continues to come from compiled `view_rules`. Later surfaces continue to use
`_participant_behavior_history_anchor_indexes()` and
`participant_observation_effective_relation()` so a visibility transition is
effective only when its declared action-linked anchor exists at or before the
selected behavior-history order.

Initial context and surface projection must still pass the same:

- compiled behavior-specification, action-contract, argument-shape,
  observation-boundary, and affordance resolution;
- audience, source-layer, transformation, marking, redaction, withholding,
  exposure-policy revision, authorization, evidence, provenance, and apparatus
  checks;
- context-view / decision-surface relational agreement; and
- SEM-220 selection-shape, surface membership, eligibility, apparatus, and
  admission checks.

`bind_participant_decision_surface_selection()` and
`RuntimeControlPlane.admit_participant_decision_surface_selection()` remain the
selection path. The live runtime must additionally reject a surface whose
participant, episode, readiness/behavior anchor, or decision order is no longer
current. A surface from a prior reset/restart must not be admitted into the
current episode merely because its action and participant addresses still
resolve.

Invalid proposal, selection, argument-shape, apparatus, exposure, or admission
inputs create no participant behavior event. Only the existing admitted-action
path may append `action_attempted`, its transition, and its observation.

## Canonical Incumbents To Reuse

- **Lifecycle contracts and validation:**
  `ParticipantEpisodeExecutionState`, `ParticipantEpisodeHistoryEvent`,
  `ParticipantEpisodeHistoryEventModel`,
  `iter_participant_episode_snapshot_violations()`, and
  `BaseParticipantRuntime.initialize()`, `reset()`, and `restart()`.
- **Runtime state and persistence:** `RuntimeSnapshot`,
  `RuntimeControlPlane`, `execute_participant_action()`, `ControlPlaneStore`,
  `InMemoryControlPlaneStore`, and `LocalControlPlaneStore`. Projection state
  must not move into a new current-surface store or snapshot `metadata`.
- **Compiled semantic scope:** `RuntimeModel`,
  `ParticipantBehaviorSpecificationRuntime`,
  `ParticipantActionContractRuntime`,
  `ParticipantObservationBoundaryRuntime`,
  `ParticipantToolAffordanceRuntime`, and the compiler-produced
  `participant.*` addresses.
- **Visibility:** `_participant_behavior_initial_view_relation()`,
  `_participant_behavior_history_anchor_indexes()`,
  `participant_observation_effective_relation()`, and the compiled
  `view_relation_timeline`. There must be one effective-relation algorithm.
- **Decision and exposure:** `ParticipantDecisionSurfaceProjectionInput`,
  `project_participant_decision_surface()`,
  `ParticipantExposureResolvers`, projection-policy revision selection,
  exposure authorization/occurrence validation,
  `ParticipantDecisionSurfaceModel`, `ParticipantContextViewModel`, and
  `validate_participant_decision_surface_context()`.
- **Selection and admission:** `ParticipantDecisionSurfaceSelectionModel`,
  `ParticipantValidatedActionSelection`,
  `ParticipantDecisionSurfaceBindingResolvers`,
  `bind_participant_decision_surface_selection()`,
  `ParticipantActionAdmissionRequest`,
  `participant_action_admission_request_violations()`, and
  `ParticipantControlMixin.admit_participant_action()`.
- **Backend transition gate:** `_call_backend_apply()`,
  participant runtime state/history transition diagnostics,
  `ParticipantBehaviorHistoryEventModel`, and
  `iter_participant_behavior_history_violations()`.
- **Contracts and schema governance:** `ContractModel`,
  `schema_bundle()`, `contracts/schemas/`, `contracts/fixtures/`,
  `contracts/schema-publication-manifest.json`, and
  `contracts/schema-publication/entries/`.
- **Diagnostics and observability:** `Diagnostic`, `Severity`,
  `OperationReceipt`, `OperationStatus`, `AuditEvent`, and existing
  control-plane audit recording. Audit and raw logs are operational records,
  not substitutes for the semantic lifecycle/behavior anchor.

## Cross-Cutting Layers The Design Must Pass

### Shape and semantic validation

1. Public payloads remain closed `ContractModel` shapes with
   `extra="forbid"` behavior and JSON Schema parity.
2. Lifecycle payloads normalize through the existing RUN-311 types and complete
   snapshot invariants; accepting a standalone structurally valid event is
   insufficient.
3. Participant, episode, behavior, boundary, action, affordance, argument-shape,
   and anchor refs resolve against the compiled runtime model and trusted
   snapshot.
4. Initial projection selects only compiled `V_p,0`; later projection uses the
   existing behavior-anchor indexes and effective-relation selector.
5. Exposure resolvers validate immutable policy version/digest, effective
   revision, exact participant/episode/order/apparatus coordinates,
   authorization, markings, evidence, provenance, and any realized occurrence.
6. The context-view relational validator agrees with the surface on scope,
   observation point, payload ref, projection, evidence, provenance, markings,
   redaction, and limitations.
7. Selection binding validates surface identity/order, membership, eligibility,
   support, argument shape, proposal coordinates, apparatus selection, exposure
   policy, and admission-request agreement before normal action admission.
8. Backend apply validation preserves the predecessor snapshot, append-only
   lifecycle/behavior histories, action-instance uniqueness, exact event order,
   live episode scope, and terminal observation contract.

### Authentication, authorization, secrets, and errors

- No new HTTP endpoint is required by this integration. If an HTTP surface is
  later added or an existing route is extended, it must enter through
  `create_control_plane_app()`,
  `ControlPlaneSecurityConfig.strict_defaults()`, bearer or verified-proxy
  identity, target binding, `ControlPlaneRole` read/mutation authorization,
  request-size guards, request fingerprints, idempotency, and `AuditEvent`.
- Control-plane caller authorization, scenario participant authority,
  participant visibility, exposure authorization, and action admission are five
  separate gates. Success at one does not imply another.
- Bearer tokens, credentials, hidden prompts, answer material, raw evidence,
  raw exposure/configuration bodies, backend object representations, and full
  tracebacks must not enter the anchor, surface, context view, snapshot,
  diagnostic, audit details, or public error detail. Use stable refs, digests,
  markings, redaction policies, and governed evidence/provenance.
- Expected contract and semantic failures use existing `ValueError`/`TypeError`
  normalization at library boundaries, structured `Diagnostic` values and
  operation envelopes at the control plane, or bounded existing 4xx details at
  HTTP boundaries. Unexpected HTTP failures keep the redacted
  `{"detail": "internal server error"}` envelope. Do not add an anchor-specific
  exception hierarchy.
- This design needs no new environment binding, secret provider, config file,
  subprocess, socket, filesystem path, or command-line option. A later backend
  adapter must not place tokens, credentials, proposal payloads, hidden context,
  or policy bodies in process argv, environment dumps, shell strings,
  stdout/stderr, or logs. Existing typed adapter calls and injected resolvers are
  the boundary; no `shell=True` execution is justified.

### Persistence, replay, and observability

- The current `RuntimeSnapshot` and `ControlPlaneStore` remain authoritative for
  live episode and behavior history. Local persistence keeps its atomic snapshot
  writes and append-only audit path.
- An initial anchor is valid only while it resolves to the current running
  episode. Reset, restart, termination, participant mismatch, history
  truncation, or live-result/history disagreement invalidates it.
- A later anchor must identify exactly one event in the supplied complete
  participant/episode behavior prefix. Empty behavior history is permitted only
  with a valid readiness anchor for decision order zero.
- Operation idempotency/request fingerprints and action-instance uniqueness
  remain the mutation replay guards. Semantic surface replay also requires live
  participant/episode/anchor agreement; idempotency alone does not make an old
  surface current.
- Projection failures and authorization denials use existing diagnostics and
  audit events. Do not add a decision-surface log schema, replay database,
  side-channel cache, or treat logs/audit events as participant-visible
  evidence.

## Extensibility Seam

The seam is the tagged, participant/episode-scoped projection anchor plus its
trusted resolver. Adding another truthful pre-action readiness source, partial
ordering basis, or externally realized participant must add a new governed
anchor variant/resolver rule without:

- editing the RUN-311 or behavior-history event enums;
- changing `V_p,0`;
- changing action, argument-shape, exposure, or admission meaning;
- adding another history or visibility algorithm; or
- overloading lifecycle `sequence_number`, decision-surface order, or behavior
  order.

Anchor identity/order/evidence is the parameter. Backend kind, participant kind,
UI form, prompt format, and APTL scenario are not.

## Gotchas And Anti-Patterns

Avoid:

- using `episode_initialized` as readiness;
- treating the simultaneous timestamps currently emitted for
  `episode_initialized` and `episode_running` as ordering evidence;
- using lifecycle list position or `sequence_number` as behavior order;
- inserting a fake setup action, observation, choice, or state transition to
  make behavior history non-empty;
- passing a lifecycle object through a
  `Sequence[ParticipantBehaviorHistoryEvent]` and relying on shared attributes;
- merging lifecycle and behavior events into one union history;
- allowing an arbitrary empty history without a current readiness anchor;
- accepting a final snapshot, standalone event DTO, caller-owned event ref, or
  backend-private bootstrap record as projection authority;
- encoding anchor structure in free-form `details`, snapshot `metadata`,
  `observation_point`, audit details, or a naming convention;
- copying the initial view relation or visibility-transition walk into a second
  projector;
- using future behavior, policy, authorization, or disclosure to justify the
  initial surface;
- allowing a stale surface from a terminated, reset, or restarted episode to
  bind to the current episode;
- treating presentation as proposal, selection, admission, action, result, or
  participant choice;
- weakening argument-shape, apparatus, exposure, SEM-211, or normal admission
  checks for the first selection;
- treating `AuditEvent`, `OperationReceipt`, backend logs, or timestamps alone
  as semantic evidence;
- adding a duplicate DTO family, schema registry, validator stack, exception
  hierarchy, persistence store, audit/log path, or backend-specific bootstrap
  protocol; or
- changing a published schema without generator parity, fixtures, publication
  ledger updates, and ADR-061 compatibility classification.

## Non-Goals And Implementation Boundaries

- No second participant, episode, visibility, context, decision, exposure, or
  history model.
- No arbitrary snapshot projection and no weakening of later time-indexed
  behavior-history semantics.
- No participant UI, prompt, agent framework, tool runner, backend setup action,
  credential broker, policy engine, or OS sandbox.
- No APTL-, TechVault-, coding-agent-, LLM-, RL-, human-, or backend-specific
  initialization semantics.
- No exposure of evaluator-only state, hidden truth, private answer material,
  raw evidence, credentials, or backend-private identifiers.
- No redesign of RUN-311 lifecycle, SEM-210 transitions, SEM-211 applicability,
  SEM-214/216 context/audience views, SEM-226 exposure authorization, control
  plane authentication, persistence, audit, diagnostics, or experiment
  provenance.
