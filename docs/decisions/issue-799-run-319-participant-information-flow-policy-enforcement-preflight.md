# Issue 799 RUN-319 Participant Information-Flow Policy Enforcement Preflight

Date: 2026-07-27

Issue: #799.

Requirement: RUN-319.

This note records repository-wide architecture boundaries for reference-runtime
participant crossing enforcement and evidence. It is guidance only. It does not
implement a policy decision, transform content, change a backend claim, add a
route, publish or revise a schema, migrate legacy records, or claim runtime
realization or information-flow assurance.

## Decisive Current-State Findings

RUN-319 is an integration requirement over delivered incumbents, not a new
policy-engine or carrier project:

- ADR-085, as amended by ADR-095, and
  `specs/formal/participant-semantics/information-flow-control.md` own the
  deny-first semantics, distinct operations, exact-cut policy resolution,
  participant-relative projection, ordering, and nonclaims.
- API-423 already publishes the closed
  `participant-crossing-occurrence-v1` relation and
  `validate_participant_crossing_occurrence_context()`. It separates requested,
  decided, transformed, disclosed, delivery-attempted, delivered, observed, and
  audited facts.
- API-407 already owns participant policy feature strength, limitations,
  disclosure, evidence, required-contract mapping, and
  `resolve_participant_feature_support()`.
- SEM-226 already supplies deny-first exposure selection through the v2
  exact-cut decision-surface/exposure resolvers. RUN-319 must invoke that logic
  for applicable egress; it must not create another visibility selector.
- RUN-310 already demonstrates authenticated participant/controller binding,
  semantic fingerprints, scoped idempotency, immutable API-409 occurrences,
  append-only snapshot history, expected-head atomic commit, safe diagnostics,
  and audit correlation.
- `RuntimeSnapshot`, its serializers, participant snapshot/transition
  diagnostics, `ControlPlaneStore`, and `AuditEvent` do not yet carry a
  first-class crossing history or a general atomic participant transition.
- API-408 retrieval currently synthesizes visibility refs, empty markings, and
  no redaction policy from the current snapshot. Its backend/operator/auditor
  read authorization is not participant or audience authorization. It is not a
  participant-safe egress path and cannot be grandfathered into one.
- The reference-emulation manifest currently declares every participant-policy
  feature `unsupported`. Contract publication and pure runtime logic cannot
  silently upgrade that declaration.

One dependency discrepancy must be resolved deliberately. SEM-230 revision 2
and ADR-095 require the exact policy-decision identity and state-cut identity.
The current API-423 `ParticipantCrossingPolicyReferenceModel` carries policy
identity, revision, digest, effective order, and validity interval, but no
general `decision_cut_ref` or exact policy-decision ref. Decision epoch,
effective order, receipt order, timestamp, and state-cut identity are not
interchangeable. RUN-319 must therefore either consume an existing exact-cut
owning relation where one exists, such as SEM-226 v2, or evolve API-423 through
its normal compatibility/publication process before claiming general SEM-230
revision-2 enforcement. A runtime-only field, `RuntimeSnapshot.metadata`, or an
audit detail is not an acceptable compatibility shim.

Accepted ADRs and existing issue preflights settle the overall architecture. A
new ADR is not warranted unless the exact-cut discrepancy requires a normative
decision that cannot be resolved by compatible contract composition.

## Architecture Decisions And Guardrails

### Enforce at the existing runtime service boundary

The enforcement owner remains `RuntimeControlPlane` through
`ParticipantControlMixin`, `ParticipantRetrievalMixin`, and the existing
participant action/lifecycle methods. HTTP handlers, in-process callers, and
backend adapters must reach the same mediation path. Route-only middleware,
response filtering, a participant gateway, or a backend-local check would
leave bypasses.

The runtime owns crossing event ids, decision and realization dispositions,
effective policy/cut coordinates, safe reason codes, backend posture,
predecessor links, evidence/provenance, and persistence status. A caller may
provide a closed, bounded intent and typed subject reference; it must never
submit a completed API-423 occurrence, choose its gates or disposition, assert
declassification, or claim delivery/observation/audit.

For every authenticated and subject-bound attempt, the runtime emits the
minimum applicable API-423 stage facts. A request and deny/withhold/unsupported
decision remain append-only evidence. Delivery, observation, and audit stages
are appended only when their owning occurrence resolves; none is inferred from
another. Failures before authenticated target/subject binding remain security
audit denials and must not let untrusted input manufacture a participant fact.

### Compose the existing gates deny-first

The crossing mediator resolves one immutable state cut and evaluates:

1. closed input shape and bounded transport values;
2. authenticated caller and exact runtime target;
3. trusted principal-to-participant/controller binding;
4. participant authority, controller state, scope, and applicable policy;
5. typed subject, interaction semantics, episode, markings, and order;
6. SEM-211 applicability/admission for actionable ingress;
7. SEM-226 audience, visibility, projection, marking, redaction, and
   declassification for participant egress;
8. API-407 required feature strength, contracts, evidence, and any explicitly
   authorized downgrade;
9. governed transformation result validity and fresh admission where
   actionable; and
10. append-only decision/realization/evidence commit before dispatch or
    serialization.

These are independent owners whose results populate the API-423 decision
gates. A permit from one owner cannot widen a deny, unknown, unsupported, or
unresolved result from another. Planner admission, a manifest declaration, a
role, a visibility ref, a redaction, or a passing schema is never a substitute
for the complete decision.

Policy and subject resolution must occur while the relevant snapshot/history
head is stable. The semantic fingerprint and commit precondition bind the same
state cut; resolving policy before a concurrent handoff, policy change, reset,
or prior crossing and committing afterward is a time-of-check/time-of-use
bypass.

### Keep ingress, egress, control, inject, and transformation owners distinct

- Ordinary action ingress still terminates in
  `ParticipantActionAdmissionRequest`,
  `participant_action_admission_request_violations()`, and the existing
  participant runtime apply/result-history checks.
- Approval, denial, direction, intervention, handoff, override, and
  cancellation still terminate in RUN-310/API-409 mediation. RUN-319 adds the
  crossing decision relation around the attempt; it does not replace the
  control state machine or dispatch directly from approval.
- Decision-surface/context/history/status egress still uses the SEM-226
  exact-cut exposure selector and existing typed views. RUN-319 records the
  crossing decision and realization, then serializes only the governed result.
- A participant-directed inject retains its compiled DSL-142 binding and
  original DSL-111 occurrence identity. Schedule, attempted delivery,
  delivery, observation, external direction, and action remain separate.
- A transformation is non-mutating and creates a typed result identity with
  rule/revision, source/result markings, authority, evidence, provenance, and
  loss. Existing pure projection/exposure functions are the first incumbents.
  Any additional operation must be a trusted, resolver-supplied, closed
  operation keyed by governed rule identity/revision—not an executable policy
  body, expression language, arbitrary callable from a request, or open plugin
  bag.

A transformed proposal re-enters the same ingress boundary as a new attempt.
It receives a new subject identity, decision, semantic fingerprint, and full
structural, semantic, capability, authority, and admission validation. Source
approval, admission, execution, delivery, and idempotency state do not carry
forward. API-423's transformation graph and contextual validator remain the
cycle/source-mutation guard.

### Project before serialization, never after

Participant-facing views are constructed from authorized projected result
carriers and validated as their existing closed response models before any
serialization. The implementation must not serialize a snapshot/raw carrier
and remove fields afterward, call `_project_scope()` as an authorization
operation, or expose a response while decision persistence is still pending.

The existing `/snapshot` route is an administrative control-plane view, not a
participant view. Adding crossing history to snapshot state must not cause raw
crossing history to appear in API-408 participant views. Any participant-facing
status, context, history, result, inject, or error passes the same
participant/audience projection. Operator/auditor access to an administrative
surface does not make its contents participant-visible.

### Make crossing history first-class and append-only

Persist API-423 occurrences in a first-class typed
`RuntimeSnapshot` participant crossing history, keyed consistently with the
existing participant histories and retaining episode, audience, policy/cut,
order, predecessor, evidence, provenance, marking, loss, and audit links in
each record. Do not use `metadata`, generic event `details`, operation
diagnostics, audit details, logs, an exposure cache, or a gateway-local file as
the authoritative history.

The new history must participate in all existing state paths:

- `RuntimeSnapshot`, `with_entries()`, allowed update keys, and carrier-address
  accounting;
- runtime snapshot envelope/model serialization;
- `_snapshot_payload()`, `_snapshot_from_payload()`, `_snapshot_model()`, and
  local-store restart loading;
- full-snapshot validation and API-423 resolver-backed contextual validation;
- append-only transition validation on backend results and control-plane
  commits; and
- operational summaries and conformance evidence without payload disclosure.

On restart or replay, closed models first validate each stored occurrence.
Before the runtime serves or mutates participant state, the API-423 contextual
validator must resolve the history against trusted typed subject, exact policy
history/cut, authority, evidence, and predecessor indexes. Policy bodies and
hidden subjects remain out of line; absence of the trusted resolution context
fails closed rather than weakening validation.

### Generalize the existing atomic participant commit seam

`ControlPlaneStore`, `InMemoryControlPlaneStore`, and
`LocalControlPlaneStore` remain the only persistence owners.
`commit_control_transition()` is the incumbent transaction pattern. RUN-319
must reuse or carefully generalize its expected-head semantics so one durable
commit contains the applicable crossing facts, snapshot transition, operation
record/idempotency outcome, and safe audit correlation. It must not introduce a
crossing store or call `save_snapshot()`, `save_record()`, and `append_audit()`
independently.

The commit precondition covers every history head involved in the state cut,
including control or behavior history when the crossing decision depends on
it. Multi-stage writes that must be observed together use one write set; later
realization stages use new append-only commits and predecessor refs. A failed
commit returns no permitted output and performs no backend dispatch.

The current lock and atomic file replacement support a declared single-process,
single-writer reference-runtime bound only. They do not provide multi-process
compare-and-swap, distributed linearizability, or crash-safe transactions
across unrelated files. A later durable store implements the same expected-head
write-set seam; it must not replace the policy or participant lifecycle.

### Scope idempotency to policy-relevant semantics

Reuse `Idempotency-Key`, `ControlPlaneOperationRecord`, store lookup, and
semantic request fingerprints. The effective scope includes target,
authenticated principal, operation/interaction kind, participant, episode,
audience, client key, and typed subject identity.

The fingerprint additionally binds subject revision/digest, controller and
authority, exact policy decision/cut/revision, marking state, order/head,
required and effective backend strength, downgrade authorization,
transformation rule/result identity, and any owning proposal/control/inject
revision. An exact retry returns the original result without another decision
or realization. Reuse across changed semantics conflicts. A change in policy,
controller, authority, subject, marking, capability posture, or relevant state
requires a fresh decision even if raw request bytes are equal.

### Keep capability and realization claims honest

Runtime enforcement calls `resolve_participant_feature_support()` for the
specific crossing kind and policy-required minimum strength. Planning-time
feature checks are useful early rejection, not runtime authority. Method
presence, contract ids, schema validity, or a non-null participant runtime
cannot establish support.

Map `ParticipantFeatureSupportLevel` to API-423 backend posture explicitly;
do not compare incidental string spellings. A downgrade is accepted only when
the already-resolved crossing policy authorizes the effective strength and the
record carries the downgrade policy/provenance, constraints, limitations,
disclosures, and evidence. The effective record drops the stronger claim.

The shipped reference backend remains `unsupported` until actual backend or
runtime behavior and bounded conformance evidence justify a changed manifest.
RUN-319 may exercise fail-closed unsupported paths and bounded in-process
reference-runtime logic without claiming backend realization. Any positive
manifest change remains owned by API-407 manifest/conformance rules.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Normative semantics | ADR-085, ADR-095, SEM-230 revision 2, `Effective(rho,c)`, `MayCross`, and the distinct operation/claim tables. Do not add runtime-local policy meaning. |
| Crossing contract | `ParticipantCrossingOccurrenceModel`, its closed stage models/vocabularies, `ParticipantRuntimeBaseEnvelopeModel`, and `validate_participant_crossing_occurrence_context()`. Emit and validate these; add no generic I/O event. |
| Ingress/admission | `ParticipantActionAdmissionRequest`, `participant_action_admission_request_violations()`, decision-surface selection binding, `ParticipantControlMixin.admit_participant_action()`, and participant action result/history validation. |
| Control | RUN-310 mediation, API-409 `ParticipantControlOccurrenceModel`, compiled ACT-617 controller states/transitions, `ControlPlaneIdentity.participant_control_subjects`, and `participant_control_history`. |
| Egress/exposure | SEM-226 v2 projection/exposure resolvers and validators, `participant_observation_effective_relation()`, participant decision surfaces, context/history/status models, observation envelopes, and behavior histories. |
| Directed injects | Compiled DSL-142 `ParticipantInjectDelivery`, original DSL-111 inject/event/script/story refs, temporal/evidence bindings, and API-423 delivery stages. |
| Backend capability | `ParticipantFeatureSupport`, `PARTICIPANT_RUNTIME_POLICY_FEATURES`, `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`, `resolve_participant_feature_support()`, manifest round trips, and `BackendConformanceReport`. |
| Runtime owner | `RuntimeControlPlane`, `ParticipantControlMixin`, `ParticipantRetrievalMixin`, backend call/result gates, `OperationReceipt`, `OperationStatus`, and `ControlPlaneOperationRecord`. |
| State validation | `RuntimeSnapshot`, participant full-snapshot and append-only transition diagnostics, API-423 contextual validation, and `_finalize_backend_apply()` rollback-to-baseline behavior. |
| Persistence | `ControlPlaneStore`, both shipped stores, expected-head atomic control commit, atomic replacement, and existing operation/audit serializers. |
| Authentication | `create_control_plane_app()`, `ControlPlaneSecurityConfig.strict_defaults()`, `_ControlPlaneApiAuth`, `ControlPlaneIdentity`, roles, bearer/verified-proxy identity, and target binding. Add a separate closed trusted participant/audience binding where egress needs it; do not overload control-subject binding or role membership. |
| Request protection | `request_size_guard_response()`, closed Pydantic request DTOs, `_request_fingerprint()`, and idempotency headers. No unbounded policy/payload/details maps. |
| Errors/observability | `Diagnostic`, `Severity`, operation envelopes, bounded HTTP details, the redacted 500 handler, `AuditEvent`, evidence/provenance refs, and operational apparatus summaries. Add no exception family or logger. |
| Contract/lineage governance | `schema_bundle()`, hand-governed schemas/fixtures/publication entries, `x-raes-invariants`, controlled vocabularies, `docs/explain/sdl/lineage.md`, its model/checker, and source audit. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and the existing repo-policy, requirement-governance, concept, schema, JSON, lineage, semantic-coverage, conformance, and full verification gates. |

## Cross-Cutting Layers And Security Posture

1. **Transport shape and size.** Existing HTTP bodies pass the content-length
   and actual-byte guard, then closed Pydantic DTOs. The guard does not bound
   path, query, or header values; any touched participant route must either add
   no new such input or use a shared bounded-value validator for participant,
   episode, audience, refs, and idempotency values. A body-size limit alone is
   not a complete ingress bound.
2. **Authentication and target binding.** Bearer or verified trusted-proxy
   identity passes `_ControlPlaneApiAuth`, role authorization, and exact target
   binding under empty fail-closed defaults. Bearer tokens and identity headers
   never enter fingerprints, occurrence payloads, diagnostics, audit details,
   or logs.
3. **Participant/controller/audience binding.** Trusted identity configuration
   separately binds the principal to participant/controller control authority
   and, for participant-facing reads, participant/audience access. A backend,
   operator, or auditor role alone grants neither. Cross-participant existence
   must not be discoverable through differing status/detail text.
4. **Compiled and exact-cut policy resolution.** Trusted compiled behavior,
   control, inject, observation, exposure, policy-history, marking, and
   authority resolvers supply semantic state. Requests, query values, current
   wall-clock time, snapshot metadata, or backend dictionaries do not.
   Missing, ambiguous, stale, future, or incomparable resolution denies.
5. **Contract and semantic validation.** Closed API-423 models own local shape;
   one resolver-backed API-423 contextual validator owns cross-record joins.
   Existing SEM-211, SEM-226, RUN-310, lifecycle, and backend-result validators
   retain their own invariants. Do not repeat the same join in models, routes,
   mediation, stores, backends, and tests.
6. **Capability and downgrade gate.** The target's admitted manifest passes the
   canonical strength/evidence helper at the crossing state cut. Missing
   entries, insufficient strength, missing required contracts/evidence, or
   unauthorized weakening reject. Unsupported capability is an explicit
   recorded posture, not a best-effort path.
7. **Transformation and output gate.** Only governed source refs reach trusted
   operation-specific transforms. Results receive fresh identity, inherited
   markings/provenance, API-423 validation, and fresh admission where
   actionable. Only the validated projected result is serialized.
8. **Persistence, restart, and concurrency.** Full snapshot and transition
   validators, expected-head atomic write-set commit, scoped idempotency,
   restart parsing, and deterministic contextual replay must agree before
   dispatch or output. Corrupt/truncated/unresolved state fails closed.
9. **Diagnostic and error envelope.** Expected denials use stable codes and
   value-independent bounded messages. Do not expose `str(exc)`, Pydantic
   rejected input, hidden refs, policy/controller inventories, backend objects,
   or cross-participant existence. Unexpected failures retain exactly
   `{"detail":"internal server error"}`.
10. **Secret, audit, and logging surface.** Occurrences, snapshots, operation
    records, audit, diagnostics, fixtures, conformance, lineage, stdout/stderr,
    and host logs carry safe ids, refs, digests, classifications, postures,
    reason codes, and bounded limitations only. They exclude credentials,
    tokens, headers, private prompts/memory, hidden answers/world state, raw
    policy/evidence/payload bodies, environment dumps, and tracebacks.
11. **Configuration and OS/process exposure.** RUN-319 needs no new environment
    variable, secret loader, CLI policy argument, subprocess, shell, socket,
    daemon, or host file. Security/policy resolvers remain injected typed
    configuration. No token, policy body, participant payload, hidden value, or
    arbitrary ref belongs in environment variables, process argv, filenames,
    shell strings, stdout, or stderr.
12. **Package and workflow boundary.** Normative semantics stay in `specs/`;
    portable contracts in `raes_contracts`; pure compiled selectors in
    `raes_processor`; live mediation/security/state/store work in
    `raes_runtime`; declarations in `raes_backend_protocols`; and bounded
    claims in conformance. Implementation checks set
    `RAES_REQUIREMENT_UID=RUN-319` because the current branch name has no UID.

## Extensibility Seam

The stable seam is one runtime crossing transition parameterized by:

- participant, episode, audience, direction, interaction kind, and typed
  subject revision/digest;
- exact policy decision/state cut, order model/head, controller, authority,
  markings, and operation;
- trusted subject/policy/exposure/evidence resolvers;
- required backend feature/minimum strength and an already-authorized
  downgrade;
- an optional governed operation-specific transformation resolver; and
- an expected-head atomic write set for API-423 stages, operation receipt, and
  audit correlation.

The runtime supplies state and produces decisions; adapters supply only intent.
This seam permits a new governed carrier kind, audience, policy revision,
streaming/multipart realization, partial-order backend, or durable multi-writer
store by adding a closed contract variant or resolver/store capability. It does
not require re-editing existing action, observation, control, inject,
lifecycle, evidence, or audit carriers, and it is not an open metadata or
generic plugin seam.

## Assurance Guardrails

Use the existing API-423 contract tests, RUN-310 mediation/store/API-security
tests, SEM-226 projection/bypass tests, SEM-211 action admission/result tests,
DSL-142 inject tests, API-407 manifest/admission/conformance tests,
participant-runtime persistence tests, and Hypothesis patterns.

Evidence must cover positive and deny-first behavior; negative
cross-participant leakage and hidden-existence probing; stale policy/cut,
controller, subject, marking, and capability changes; unauthorized and
claim-retaining downgrades; transformed-proposal fresh admission; redacted
errors; exact retry and conflicting key reuse; crash/restart/replay,
append-only prefix integrity, and concurrent expected-head conflicts; and
serialization only after durable authorization.

Finite tests establish bounded reference-runtime behavior only. They do not
prove native backend realization, distributed ordering, noninterference, trace
equivalence/inclusion, simulation, refinement, epistemic equivalence, or
bisimulation.

## Gotchas And Anti-Patterns

Avoid:

- a new policy engine, gateway, transport, workflow engine, DTO family,
  participant lifecycle, store, audit stream, logger, exception hierarchy,
  schema registry, concept catalog, or verification runner;
- accepting caller-completed API-423 facts or policy bodies, evaluating policy
  expressions from input, or using open `payload`, `metadata`, `details`,
  `constraints`, or `extensions` bags;
- treating effective order as exact state-cut identity, a current/final
  snapshot as historical authority, or a later policy as authorization for an
  earlier crossing;
- treating caller authentication, role, target authorization, participant
  authority, controller state, admission, visibility, marking,
  declassification, backend support, and transformation validity as one gate;
- treating approval as admission, admission as dispatch, schedule as delivery,
  delivery as observation, observation as action, or audit as disclosure;
- treating masking, projection, redaction, hashing, summarization, loss, or
  weakening as authorization or declassification;
- filtering after serialization, using `_project_scope()` or synthesized
  visibility refs as policy, or returning raw crossing/control/history facts
  through participant views;
- mutating a transformation source, retaining source admission/idempotency,
  removing inherited markings without declassification, or admitting a result
  without the normal fresh path;
- treating planner success, method presence, schema validity, supported
  contract ids, a manifest claim, or finite conformance as runtime realization;
- independent snapshot/receipt/audit writes, a second crossing persistence
  file, last-writer-wins, arrival/timestamp order, or claims of multi-process
  safety from an in-process lock and file rename;
- exception text, rejected values, policy bodies, hidden refs, raw payloads,
  credentials, headers, backend objects, or environment/process data in
  responses, audit, logs, evidence, fixtures, or documentation; and
- changing the lineage ledger/source audit solely because RUN-319 delivery
  status changes.

## Publication Workflow Compatibility

The repository's configured Ground Control commands bridge the service's
legacy requirement gate variable to the repository-owned
`RAES_REQUIREMENT_UID` name without retaining the retired identity token in
repository content. This preserves server-side issue/requirement authorization
while allowing completion, policy, and pre-commit commands to evaluate RUN-319
on issue-number branches that do not contain the UID.

## Non-Goals And Implementation Boundaries

- No participant gateway, transport, endpoint family, UI, external-agent API,
  policy-expression language, credential broker, provider integration,
  arbitrary transformation runtime, or OS sandbox.
- No replacement or duplication of SEM-211 admission, SEM-226 exposure,
  RUN-310/API-409 control, DSL-142 inject bindings, API-423 crossings, API-407
  capability declarations, participant lifecycle/history, evidence/provenance,
  or audit.
- No participant prompt, chain-of-thought, private memory, hidden state, policy
  body, credential, raw rejected input, raw evidence, or backend-private object
  in portable or observable records.
- No migration or silent promotion of legacy records. Missing policy/crossing
  history remains legacy/unknown/unsupported until issue #802 supplies the
  governed compatibility path.
- No positive backend capability claim without the owning implementation and
  conformance evidence.
- No universal noninterference, timed/probabilistic security, erasure,
  trace-equivalence, simulation, refinement, epistemic, or bisimulation claim.
- No lineage-ledger/source-audit change unless implementation changes a
  normative external derivation or compatibility claim. The participant
  section of `docs/explain/sdl/lineage.md` is updated only with actual delivered
  RUN-319 mappings, evidence, status, and nonclaims.
