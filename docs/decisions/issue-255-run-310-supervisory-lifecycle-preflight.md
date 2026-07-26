# Issue #255 — RUN-310 Supervisory Lifecycle Preflight

Date: 2026-07-26

Issue: #255.

Requirement: RUN-310.

This note records architecture boundaries and implementation guardrails for the
observable mixed-control supervisory lifecycle. It is guidance only. It does
not add a route, runtime transition, store field, contract, schema, capability,
backend behavior, or conformance claim.

## Binding Authorities

- Accepted ADR-085 and
  `specs/formal/participant-semantics/information-flow-control.md` require
  authenticated caller, target authorization, participant/controller
  authority, action admission, and visibility to remain separate deny-first
  gates. They also require policy, controller, authority, marking, and order
  revisions to be evaluated at the occurrence's declared order point.
- ACT-617 is already authored and compiled through
  `ParticipantBehaviorSpecification.mixed_control` and
  `ParticipantBehaviorSpecificationRuntime.controller_states` /
  `control_transitions`. Those are permitted policy declarations, not live
  state or evidence that a transition occurred.
- API-409 already publishes `ParticipantControlOccurrenceModel` and
  `validate_participant_control_occurrence_context()`. An API-409 record is an
  immutable occurrence fact and outcome, not an untrusted command DTO.
- ADR-054 owns the append-only participant runtime lifecycle, ordering,
  markings, projections, and evidence boundary. Admission, execution,
  delivery, observation, and control remain distinct state owners.
- ADR-009, ADR-019, and ADR-061 govern closed contract models, published
  schemas, generated-bundle parity, and compatibility classification.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and
  `tools/verify_all.py` own repository workflow. RUN-310 needs no issue-local
  runner, registry, schema generator, or verification script.

These authorities already settle the cross-cutting architecture. RUN-310 does
not need a new ADR unless implementation discovers a conflict with an accepted
authority. This note specializes them at the live mediation boundary.

## Architecture Decisions And Boundaries

### The runtime mediates commands and emits occurrence facts

The HTTP/application input and the persisted API-409 occurrence have different
trust and ownership:

- a request carries only caller-supplied intent, stable client correlation,
  the target participant/episode/proposal or typed target, expected
  controller-state and policy revisions, and the references needed to evaluate
  it;
- the runtime owns event identity, recorded/ingested time, realized
  disposition and reason code, resulting controller-state revision,
  authorization and evidence bindings, and persistence status; and
- the resulting immutable fact is
  `ParticipantControlOccurrenceModel`, validated by the existing API-409
  contextual validator before commit.

Do not accept a caller-supplied API-409 record as already accepted, use its
`actor_ref` as authentication, or let it choose its realized disposition.
Conversely, do not publish a second portable supervisory occurrence schema.
If the HTTP adapter needs a request body, keep it as a closed, bounded
application DTO containing only client-owned fields; share API-409 component
types and vocabularies rather than duplicating its occurrence model.

Once a caller is authenticated and bound, stale, denied, late, conflicting,
limited, superseded, and too-late attempts are observable outcomes and must
append a bounded API-409 occurrence. Requests that fail before authenticated
subject binding are security-audit denials only: untrusted input cannot create
a participant occurrence.

### One runtime transition owner over compiled policy and recorded history

Extend the existing `RuntimeControlPlane` / `ParticipantControlMixin` boundary;
do not add a workflow engine, participant gateway, backend method, or parallel
controller service. The mediator consumes an admitted compiled
`ParticipantBehaviorSpecificationRuntime` supplied by trusted runtime setup,
not a declaration sent in the request. It indexes the existing controller
states and transitions into
`ParticipantControlDeclarationModel` inputs for the canonical API-409
validator.

The transition evaluation order is:

1. bind the authenticated control-plane identity and exact runtime target;
2. bind the path/body target to one participant and episode;
3. bind that principal to the requested participant/controller subject;
4. resolve the exact compiled ACT-617 transition, controller, authority basis,
   scope, policy revision, validity interval, and expected state revision;
5. read and validate the current append-only control history;
6. evaluate duplicate, stale, revoked, late, ordered-concurrent, and conflict
   disposition rules;
7. when the occurrence would lead to an action, pass the separately bound
   proposal/action through the existing SEM-211
   `ParticipantActionAdmissionRequest` path; and
8. append the validated occurrence and its operation receipt atomically, then
   project only the authorized history/view.

Unknown or unresolved required coordinates fail closed. `behavior_mode`, an
operator role, bearer-token possession, implementation identity, backend
support, request arrival time, and collection order never substitute for
controller state or participant authority.

The current implementation may support ACT-617's
`total-effective-order` only. It must reject an unsupported order strategy
rather than linearize it silently.

### Control history is first-class snapshot state

The authoritative live state is an append-only
`participant_control_history`, keyed by participant in the same manner as
episode and behavior histories, with episode identity retained in every
API-409 occurrence. Current controller state and revision are a deterministic
fold of the admitted compiled initial state plus that history. Do not maintain
a second mutable controller-state truth. A derived in-memory index is
permitted only when it is rebuilt and checked against the authoritative
history after restart.

Integrate the new history into all existing snapshot carriers and validators:

- `RuntimeSnapshot`, `RuntimeSnapshot.with_entries()`, and its allowed update
  keys;
- `RuntimeSnapshotEnvelopeModel`, `_snapshot_payload()`,
  `_snapshot_from_payload()`, and `_snapshot_model()`;
- `participant_runtime_state_contract_diagnostics()` for full-snapshot
  validity; and
- `participant_runtime_history_transition_diagnostics()` for append-only
  prefix preservation and valid head transitions.

Do not use `RuntimeSnapshot.metadata`, participant behavior `details`,
`AuditEvent.details`, operation diagnostics, or a gateway-local file as
controller state or occurrence history.

API-408 history/status projections may expose control occurrences only through
an explicitly governed typed projection with participant/episode scope,
visibility, markings, redaction policy, completeness, and source-snapshot
binding. An auditor/operator read role permits control-plane retrieval; it
does not make the same event participant-visible. Participant egress still
passes SEM-226 exposure and ADR-085 visibility/marking gates.

Any change to `runtime-snapshot-v1`, `participant-history-view-v1`, or another
published schema must update its owning `ContractModel`, all serializers,
fixtures, `schema_bundle()`, publication entry/manifest hash, and ADR-061
compatibility evidence together. The published schema remains authority;
neither a Python-only field nor a hand-edited generated schema is sufficient.

### Commit transition, receipt, and idempotency outcome atomically

`ControlPlaneStore`, `InMemoryControlPlaneStore`, and
`LocalControlPlaneStore` remain the persistence owners. RUN-310 must extend
that boundary with one atomic control-transition commit that checks the
expected history head/revision and durably records:

- the appended API-409 occurrence;
- the corresponding `ControlPlaneOperationRecord`;
- its scoped idempotency key and semantic request fingerprint; and
- the safe audit correlation needed to prove who requested the operation.

Calling the existing `save_snapshot()` and `save_record()` independently is
not sufficient: a crash between them can reapply a transition after restart
or return no receipt for an already-committed event. `LocalControlPlaneStore`'s
atomic file replacement is an incumbent building block, not a transaction
across those separate files.

The in-process mediator must serialize compare/validate/append/commit for one
participant/episode/controller history. If the first realization supports only
one control-plane writer, declare and test that bound. File replacement alone
does not provide multi-process compare-and-swap. A later distributed store must
implement the same expected-head atomic commit seam; RUN-310 must not claim
distributed linearizability without that evidence.

Audit remains an append-only security/operations trail and carries safe ids,
operation ids, dispositions, and reason codes only. The API-409 occurrence and
its evidence/provenance references are the portable supervisory fact. An audit
event is not a substitute for lifecycle evidence or participant visibility.

### Idempotency is scoped and state-bound

Reuse the existing `Idempotency-Key`, request-fingerprint,
`ControlPlaneOperationRecord`, and store lookup pattern, with RUN-310's stronger
scope. The effective lookup scope is:

```text
(target, authenticated principal, operation kind,
 participant, episode, client idempotency key)
```

The semantic fingerprint covers the canonical parsed request plus the bound
declaration, controller, authority/scope, policy revision, expected state
revision, typed target revision, and order coordinates. Raw JSON byte equality
alone is insufficient, and the authenticated identity must not be omitted.

An exact retry of an already committed occurrence returns the original receipt
and never appends or applies again. Reusing a key, client correlation, proposal
identity, decision identity, or event identity with different semantics is an
explicit conflict. A request whose policy, target, proposal, or expected state
revision no longer matches is stale and performs no state change. Exact
payload equality never collapses distinct occurrence identities.

### Admission, execution, cancellation, and observation remain separate

- A proposal is not selected, approved, admitted, attempted, or executed.
- Approval or external direction targets one proposal/revision but does not
  call a backend. A mixed-control action must carry a stable reference to the
  accepted control occurrence into the existing action-admission binding; the
  admission validator must reject a missing, stale, cross-participant, or
  policy-mismatched control basis.
- Denial records a decision and leaves action admission closed.
- Intervention and override append a new fact. They never edit a proposal,
  approval, admission event, attempt, result, or observation.
- Cancellation resolves the typed target's actual stage. Before admission it
  may prevent work; after admission or attempt it records partial limitation
  or too-late effect. It cannot manufacture retroactive non-occurrence.
- Handoff completion advances controller state by exactly one declared
  revision and preserves participant identity and all prior provenance.
- Execution remains in participant lifecycle/behavior history; observation
  remains in participant observation/exposure carriers. Stable references and
  predecessor/order relations connect them to control history.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Authored/compiled policy | `MixedControlParticipantOperation`, `MixedControlControllerState`, `MixedControlTransition`, `ParticipantBehaviorSpecificationRuntime.controller_states` and `.control_transitions` | Treat these as trusted permitted-policy declarations; do not recreate or accept them from the caller. |
| Portable occurrence | `ParticipantControlOccurrenceModel`, its closed variants/vocabularies, `ParticipantRuntimeBaseEnvelopeModel`, and `validate_participant_control_occurrence_context()` | Emit one validated immutable fact per bound attempt; do not add a generic event/details bag or duplicate occurrence schema. |
| Runtime owner | `RuntimeControlPlane`, `ParticipantControlMixin`, `OperationReceipt`, `OperationStatus`, and `ControlPlaneOperationRecord` | Add mediation at the existing participant control-plane boundary and retain the common operation lifecycle. |
| Action admission | `ParticipantActionAdmissionRequest`, `participant_action_admission_request_violations()`, decision-surface binding, and `admit_participant_action()` | Link accepted control to admission; never dispatch directly from approval/direction. |
| Lifecycle/observation | `ParticipantLifecycleEventModel`, `ParticipantBehaviorHistoryEventModel`, `ParticipantActionResultModel`, `ParticipantObservationEnvelopeModel`, and API-408 projections | Link by stable refs and order; do not copy their state machines into control history. |
| State and validation | `RuntimeSnapshot`, `RuntimeSnapshotEnvelopeModel`, participant snapshot/transition invariant helpers, and backend contract diagnostics | Add a first-class typed append-only history and validate it on load, transition, backend result, serialization, and replay. |
| Persistence | `ControlPlaneStore`, `InMemoryControlPlaneStore`, `LocalControlPlaneStore`, atomic replacement, and existing record serialization | Extend this boundary with atomic expected-head occurrence/receipt commit; add no participant-control store. |
| Authentication | `create_control_plane_app()`, `ControlPlaneSecurityConfig.strict_defaults()`, `_ControlPlaneApiAuth`, `ControlPlaneIdentity`, `ControlPlaneRole`, bearer/verified-proxy identity, and target binding | Reuse auth and request guards, then perform a separate principal-to-participant/controller binding. |
| Request protection | `request_size_guard_response()`, closed Pydantic DTOs, `_request_fingerprint()` pattern, and `Idempotency-Key` | Bound size/shape before semantic work; use a canonical, identity- and state-scoped semantic fingerprint. |
| Diagnostics/errors | `Diagnostic`, `Severity`, operation receipts/statuses, bounded `HTTPException` details, and the redacted FastAPI exception handler | Return stable codes and safe identifiers only; add no RUN-310 exception hierarchy. |
| Audit/observability | `AuditEvent`, `operational_apparatus_summary()`, participant histories, evidence/provenance/marking refs | Correlate safe identities and outcomes without logging bodies, secrets, policies, or evidence content. |
| Contract governance | `ContractModel(extra="forbid")`, `schema_bundle()`, `contracts/schema-publication-manifest.json`, publication entries/fixtures, and schema compatibility checks | Keep model/schema/serializer parity and classify every published change. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, canonical `nox` sessions, repo policy, requirement governance, schema/publication, JSON, semantic coverage, and full verification checks | Extend the existing workflow only. |

## Cross-Cutting Layers And Security Posture

The intended design must pass these layers in order:

1. **HTTP size and closed-shape gate.** The existing middleware bounds content
   length and actual body bytes before parsing. A closed request DTO rejects
   unknown keys, inline credentials, raw policy bodies, hidden payloads,
   free-form metadata, and caller-owned result fields.
2. **Caller authentication and target gate.** Bearer or verified trusted-proxy
   identity passes `_ControlPlaneApiAuth`, role authorization, and exact
   `ControlPlaneIdentity.target_name` binding. Strict defaults remain empty and
   fail closed.
3. **Participant/controller subject gate.** Closed subject-binding fields
   supplied with the trusted `ControlPlaneIdentity` configuration map the
   authenticated principal to permitted participant/controller subject refs.
   The mediator checks those fields as a separate gate after role
   authorization. This is operational authorization, not controller state;
   role membership alone is insufficient.
4. **Compiled policy gate.** The mediator resolves the request against the
   trusted compiled ACT-617 declaration and verifies participant/episode,
   controller, authority basis, non-widening scope, policy revision, validity,
   expected state revision, order, typed target, evidence, and provenance.
5. **Admission and visibility gates.** Actionable outcomes still pass SEM-211
   action admission. Returned or participant-facing facts separately pass
   audience, visibility, marking, redaction, and completeness projection.
6. **Persistence and replay gate.** Snapshot models, API-409 contextual
   validation, append-only transition validators, expected-head atomic commit,
   restart load validation, and deterministic replay must agree before state is
   exposed.
7. **Diagnostic/error gate.** Expected denials use bounded status/disposition
   codes and value-safe diagnostics. Do not expose `ValidationError` input,
   `str(exc)` from untrusted shape/authorization failures, stack traces,
   controller inventories, policy content, or cross-participant existence.
   Unexpected failures retain exactly `{"detail":"internal server error"}`.
8. **Audit and secret gate.** Audit stores safe ids, decisions, reason codes,
   and references—not bearer tokens, headers, action bodies, rejected input,
   policy material, prompts, evidence bodies, or backend objects.
9. **Configuration/OS/process gate.** RUN-310 needs no environment variable,
   secret loader, CLI flag, subprocess, shell, socket, filesystem path, or
   process-argument surface. Security and subject bindings remain injected
   configuration. Do not put a token, policy, proposal, or participant payload
   in environment variables, argv, filenames, stdout, or stderr. Any later
   deployment adapter must use its existing secret/config mechanism and must
   not add `shell=True` or caller-derived argv.

## Extensibility Seam

Keep three explicit seams:

- the order strategy plus effective order, predecessor refs, and expected
  state revision, so a later causal/partial-order implementation can be added
  without changing existing occurrence meaning;
- the authenticated-principal-to-controller/participant binding carried
  alongside `ControlPlaneIdentity`, so a future non-participant controller is
  introduced as a closed subject-binding variant rather than an arbitrary
  string or role; and
- the store's expected-head atomic append/receipt operation, so a later
  multi-writer store can provide compare-and-swap without replacing the
  lifecycle engine or history contract.

These are parameters and injected dependencies of the existing runtime
boundary, not new policy engines or portable schema families.

## Required Assurance Guardrails

Evidence must exercise existing test families and invariant paths, including:

- approval, denial, direction, intervention, handoff, override, cancellation,
  exact retry, conflicting reuse, stale proposal/policy/state, revoked/late
  authority, cross-participant targets, and unordered/unsupported order;
- restart and replay from the same append-only history, truncated/corrupt
  store rejection, atomic-commit failure, duplicate recovery, and history
  prefix preservation;
- unauthenticated, wrong-role, wrong-target, unbound subject, authority
  widening, hidden-target probing, oversized body, and error-leakage cases;
- the separation of approval from admission, cancellation before/after
  admission and attempt, and observation/visibility from audit retention; and
- published schema/model/fixture parity, snapshot/store round trips, API-408
  projection scoping, contract compatibility, repo policy, requirement
  governance, and full verification.

Finite behavioral tests are implementation evidence for RUN-310. They are not
a backend support claim, distributed-order proof, noninterference proof,
refinement, simulation, or bisimulation result.

## Gotchas And Anti-Patterns

Avoid:

- treating `behavior_mode`, authenticated caller, operator/auditor/backend
  role, token, OS account, backend process, participant implementation, or
  actor/producer field as controller state or participant authority;
- accepting a caller-completed API-409 fact, trusting a requested disposition,
  or using an authored transition identity as an occurrence identity;
- a generic supervisory event, nullable command/result union, free-form
  `details`/`metadata` map, duplicate control-kind enum, or second validation
  stack;
- reading declarations, authority, policy revision, or conflict rules from the
  request, environment, snapshot metadata, backend response, or current wall
  clock;
- last-writer-wins, arrival-time/list-order semantics, silently linearizing a
  partial order, or returning a cached idempotent result across a different
  identity/target/policy/controller/state binding;
- snapshot plus receipt writes with a crash window, relying on file rename as
  multi-process locking, or mutating/replacing an earlier occurrence;
- calling a backend directly from approval/direction, carrying approval across
  proposal transformation, or equating admission with execution;
- retroactive cancellation, deletion on revocation/concealment, or rewriting
  prior controller, action, observation, evidence, or provenance history;
- returning control history without visibility/marking projection or treating
  audit retention as participant disclosure;
- raw credentials, headers, tokens, prompts, action payloads, policy bodies,
  hidden content, rejected records, evidence bodies, backend objects, or
  exception text in contracts, snapshots, diagnostics, logs, audits, fixtures,
  environment, or argv;
- adding a new gateway, workflow engine, store, audit channel, logger,
  exception hierarchy, schema registry, compatibility process, or verification
  script; and
- updating the lineage ledger/source audit merely because RUN-310 delivery
  status changes.

## Non-Goals And Implementation Boundaries

- No new SDL syntax, authored controller semantics, API-409 occurrence family,
  information-flow relation, participant gateway, human-control UI, identity
  provider, event bus, workflow engine, or persistence product.
- No backend-specific supervisory method, capability declaration, universal
  backend support claim, or automatic weakening when support is absent.
- No replacement of SEM-211 admission, participant lifecycle/action results,
  SEM-226 exposure, API-408 retrieval, or evidence/provenance ownership.
- No participant-internal reasoning, prompt/answer capture, chain-of-thought,
  hidden world state, or policy body in the supervisory record.
- No distributed ordering or multi-writer guarantee unless the selected store
  proves the expected-head atomic commit contract.
- No retroactive erasure and no claim that approval proves admission,
  admission proves execution, delivery proves observation, or audit proves
  participant visibility.
- The implementation must update the participant section of
  `docs/explain/sdl/lineage.md` with actual delivery evidence and explicit
  nonclaims. `contracts/provenance/sdl-lineage-ledger-v1.json` and the source
  audit change only if normative derivation or compatibility claims change.
