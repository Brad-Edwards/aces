# Issue #1003 — SEM-233 Final Runtime Sink Enforcement Preflight

Date: 2026-08-02

Issue: #1003.

Requirements: SEM-233, RUN-319, RUN-310, API-423, and API-407.

This note fixes the integration boundary for final-sink enforcement after
#1002. It is guidance only. It does not add a sink, policy, route, profile,
backend capability, store field, or enforcement claim.

## Decisive Boundaries

- ADR-101 defines the final RAES-controlled boundary: after the exact policy,
  authority, destination, capability, and state-cut resolution, but before a
  `RuntimeTarget` component performs an external action or any participant or
  external value is serialized, streamed, persisted, returned in an error,
  callback, or handoff.
- #1002 owns the closed SEM-233 profile and
  `ParticipantFlowControlRelationModel`, including its final-sink decision and
  resolver-backed contextual validation. It is portable evidence of a trusted
  decision, not a live enforcement mechanism.
- API-423 owns crossing stages and their policy/cut, transformation,
  disclosure, marking, loss, evidence, provenance, and realization links.
  `ParticipantCrossingOccurrenceModel` must be referenced by SEM-233; neither
  model absorbs the other.
- RUN-319 already owns operation-bound crossing mediation,
  `participant_crossing_history`, expected participant-history heads, scoped
  idempotency, atomic `commit_participant_transition()`, restart validation,
  and the existing ingress and governed-egress paths. #1003 extends these
  incumbents; it does not introduce a generic message bus, crossing store, or
  parallel transaction/audit path.

The current `RuntimeTarget` is component-specific, not one generic dispatch
method. The final-sink guard must therefore be applied at every actual target
component call and every participant/external serialization boundary reached
by `RuntimeControlPlane`; adding a nominal gateway that those calls can bypass
is insufficient.

## Required Design Guardrails

### One final decision, bound to the committed state cut

Immediately before each effect, resolve the exact SEM-233 sink decision from
trusted runtime state and call the existing
`validate_participant_flow_control_resolved_context()` with its
`ParticipantFlowControlValidationContext`. The context must contain the
already-validated API-423 occurrence, exact profile/policy/cut, source label
and provenance/influence records, sink/destination/audience, release
authority, action-admission, API-407 capability, and expected history-head
resolution. Do not accept a completed relation, labels, profile selection,
authority, sink, or permit disposition from an HTTP body, header, query
parameter, backend dictionary, snapshot metadata, or caller-provided
callback.

The sink is permitted only if the SEM-233 final disposition is `permit` *and*
the referenced API-423 decision, SEM-211 admission where applicable,
SEM-226 projection where applicable, API-407 capability result, authenticated
principal/target/participant/controller/audience bindings, and current history
heads all agree. Missing, stale, ambiguous, unresolved, unsupported, denied,
or mismatched inputs produce a non-permit decision. Preserve those safe reason
classes; never collapse them into an implicit permit or an unbounded error.

The operation fingerprint and expected heads must bind the same semantic cut
used by the flow decision. On replay, only an exact semantic match may return
the stored receipt; a profile, policy, label, provenance, release, sink,
audience, capability, controller, target, or head change conflicts and must
not reuse a prior permit.

### Commit before effect; model later facts separately

Use `ControlPlaneStore.commit_participant_transition()` as the sole durable
pre-effect transaction. Its one write set contains the API-423 decision,
SEM-233 final-sink evidence/reference, operation/idempotency record, safe
audit correlation, and snapshot/history transition. Both
`InMemoryControlPlaneStore` and `LocalControlPlaneStore` must preserve the
same expected-head behavior. A commit failure, conflict, or restart-validation
failure permits neither target invocation nor disclosure.

After a successful commit, invoke only the authorized target component or
serialize only the governed projected value. Backend failure, delivery,
observation, callback completion, and audit retention are later append-only
facts with predecessor references. They must not be pre-committed as delivery
or inferred from authorization. A target call after the authorization commit
may fail; that is not a rollback authorization to expose an alternate value.

### Reuse owners; do not duplicate their meaning

| Concern | Required incumbent |
| --- | --- |
| SEM-233 decision | `ParticipantFlowControlRelationModel`, `ParticipantFlowSinkDecisionModel`, `ParticipantFlowControlValidationContext`, and `validate_participant_flow_control_resolved_context()` |
| Crossing/policy evidence | `ParticipantCrossingOccurrenceModel`, `validate_participant_crossing_occurrence_context()`, `ParticipantCrossingPolicyResolver`, and `participant_crossing_history` |
| Ingress/control/egress | `ParticipantActionAdmissionRequest` and its violations helper; RUN-310/API-409 mediation; SEM-226 projection/exposure resolver; DSL-142 inject delivery bindings |
| Runtime transaction | `RuntimeControlPlane`, `PreparedParticipantCrossing`, expected history heads, `ControlPlaneOperationRecord`, `commit_participant_transition()`, and both shipped stores |
| Capability | `resolve_participant_feature_support()` and API-407's required contracts/evidence/downgrade rules |
| Authentication | `create_control_plane_app()`, `ControlPlaneSecurityConfig.strict_defaults()`, `_ControlPlaneApiAuth`, `ControlPlaneIdentity`, exact target binding, control-subject binding, and audience-subject binding |
| Transport/errors/audit | `request_size_guard_response()`, closed Pydantic DTOs, `_request_fingerprint()`, `Diagnostic`, operation envelopes, `AuditEvent`, and the redacted unexpected-error handler |

No new flow-control exception hierarchy, logger, policy engine, serializer,
transport envelope, store, audit channel, or generic sink abstraction is
justified. A narrow shared final-sink helper is acceptable only if every real
target invocation and disclosure writer calls it and it delegates rather than
reimplements the listed validators and transaction owner.

## Security and Whole-Repository Layers

1. **HTTP shape and authentication.** Any touched route stays behind the
   existing byte/content-length guard, closed DTO parsing, verified bearer or
   trusted-proxy identity, role check, and target binding. Bound participant,
   controller, and audience identities separately; an operator/auditor role or
   API-408 administrative read access is not participant disclosure authority.
2. **Trusted resolver and secret boundary.** The flow-context resolver is
   server-side and uses compiled policy/profile state and opaque incumbent
   identities. It never loads a caller-selected file/URL/profile or exposes
   values, prompts, raw action arguments, policy bodies, credentials, tokens,
   private state, rejected records, or backend objects. A digest is not
   automatically safe content to disclose.
3. **Validation ownership.** JSON Schema/Pydantic shape validation occurs once
   at its published model; API-409, API-423, SEM-211, SEM-226, API-407, and
   SEM-233 contextual joins retain their respective owning validators. The
   sink helper composes results, rather than copying joins into routes,
   repositories, backend adapters, and tests.
4. **Persistence/restart.** `RuntimeSnapshot` serialization and local-store
   reload must validate stored closed records and trusted contextual joins
   before serving or mutating state. The current local atomic replacement and
   process lock are single-process reference-runtime behavior, not distributed
   atomicity; do not claim otherwise.
5. **Errors, audit, logs, and OS surfaces.** Public denials use bounded,
   value-independent details; unexpected failures remain
   `{"detail":"internal server error"}`. Diagnostics, audit details, logs,
   process argv/environment, filenames, stdout/stderr, and test failures carry
   only safe ids, codes, counts, classifications, and approved opaque refs.
   No subprocess, secret/config variable, or dynamic plugin mechanism is in
   scope.

## Extensibility Seam and Evidence Standard

The seam is the existing closed SEM-233 sink coordinate
(`sink_kind`, `sink_ref`, `destination_ref`, `audience_scope_ref`) plus the
trusted non-wire flow-control validation context and RUN-319 expected-head
write set. A later sink kind, streaming chunk, callback, persistent write, or
multi-part delivery adds a closed sink variant and an explicit invocation of
the same pre-effect decision/commit boundary; it does not add an open metadata
map or a second dispatcher. Streaming requires a decision before the first
byte and retains the bound decision/cut for each chunk; an error path or
handoff is also a sink, not an exception to enforcement.

Boundary tests must drive the real `RuntimeControlPlane` with an instrumented
`RuntimeTarget` component and assert zero target calls and zero disclosures
for every non-permit class, failed expected head, failed commit, replay
mismatch, and restart failure. They must also cover successful idempotent
replay, both stores, authenticated target/participant/controller/audience
binding, transformed ingress re-admission, projected egress, injects,
callbacks, streams, and safe diagnostics/audit output. Unit tests of the
relation validator alone are not final-sink evidence.

## Non-goals and Anti-patterns

- This is reference-runtime enforcement only; it does not claim universal
  information-flow control, backend realization, noninterference, covert-
  channel control, monitor honesty, model alignment, or adversarial robustness.
- Do not treat planning validation, schema validation, proposal approval,
  action admission, gateway filtering, monitor advice, capability declaration,
  redaction, or a successful API-423 record as final-sink authorization.
- Do not dispatch or serialize before the durable permit decision, permit on a
  resolver exception, use `RuntimeSnapshot.metadata`/audit details as policy
  state, persist raw payloads in flow/crossing evidence, or independently save
  snapshot/operation/audit records.
- Do not add generic `message`, `payload`, `details`, `extensions`, `context`,
  or `security_labels` bags, duplicate carrier schemas, or a second action,
  crossing, history, idempotency, error, or audit hierarchy.
