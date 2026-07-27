# Issue #798 — API-423 Participant Crossing Contract Preflight

Date: 2026-07-26

Issue: #798.

Requirement: API-423.

This note records architecture boundaries and implementation guardrails for
portable participant-crossing policy, transformation, disclosure, realization,
evidence, and provenance contracts. It is guidance only. It does not publish a
model or schema, add runtime enforcement or persistence, change backend
capabilities, or claim that a crossing was authorized, delivered, observed, or
audited.

## Binding Authorities

- Accepted ADR-085 and
  `specs/formal/participant-semantics/information-flow-control.md` define the
  common crossing coordinates, deny-first decision composition, order and
  policy-revision semantics, information-flow operations, and claim limits.
- ADR-054 and ADR-060 define the participant-runtime carrier discipline.
  `ParticipantRuntimeBaseEnvelopeModel` already owns event/schema identity,
  participant and episode scope, timestamps and order, actor/producer/source
  identity, evidence/provenance, markings, redaction, and authorization scope.
- API-406 carriers remain authoritative for lifecycle, observation,
  participant history, shared state, and outcome facts. API-409
  `ParticipantControlOccurrenceModel` remains authoritative for proposal,
  approval/denial, direction, intervention, handoff, override, and cancellation
  occurrences.
- SEM-226 exposure selectors and occurrence/realization records own governed
  participant projection and exposure agreement. DSL-142 participant inject
  delivery bindings retain the original DSL-111 inject and narrative occurrence
  identity. API-423 composes these artifacts by reference; it does not replace
  them.
- ADR-009 and ADR-061 make schemas under `contracts/schemas/` the
  hand-governed normative authority and `schema_bundle()` output compatibility
  evidence. Publication entries, fixtures, reference parity, and compatibility
  classification move together.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and the existing
  policy/verification scripts own workflow. The implementation branch does not
  contain a requirement UID, so implementation work must set
  `ACES_REQUIREMENT_UID=API-423`.

These authorities settle the architecture. API-423 needs no new ADR unless
implementation discovers a conflict that cannot be resolved by composition.

## Architecture Decisions And Boundaries

### Publish relation records, not another participant carrier

API-423 belongs to the existing `participant-runtime` contract family. A
top-level crossing occurrence must reuse `ParticipantRuntimeBaseEnvelopeModel`
unchanged and exactly once. API-423-specific coordinates belong on focused
records or shared components private to this contract family; adding them to
the base would tighten or expand every API-406/API-409 carrier.

The contract family must preserve independently addressable facts for:

- a crossing request or produced egress candidate;
- the policy decision at one effective order point;
- each transformation, projection, redaction, or marking result;
- each declassification or disclosure authorization where applicable;
- attempted or realized delivery;
- participant observation; and
- audit/evidence retention.

These facts may share closed components and may be published as separate
schemas or a closed discriminated family, but each fact needs its own stable
identity and typed predecessor/subject references. A nullable object whose
meaning depends on whichever optional fields happen to be present is not
acceptable. Requested, decided, transformed, delivered, observed, and audited
must never be inferred from one another.

### Reference the semantic subject without copying its payload

Every crossing binds one closed direction and interaction kind to one typed
existing subject, such as:

- an API-409 proposal/control occurrence;
- a SEM-211 action contract, admission, attempt, or result;
- an API-406 observation, lifecycle, context/history/status projection, or
  outcome carrier;
- a SEM-220/226 decision-surface or exposure item;
- a DSL-142 participant-directed inject delivery binding; or
- a governed intervention/control target.

The subject relation must carry enough identity to reject a kind/contract/ref,
revision, participant, or episode mismatch. It must not contain an arbitrary
`payload`, `message`, `metadata`, `details`, or `extensions` map. Existing
payloads, hidden values, policy bodies, backend objects, and evidence content
remain out of line. A digest may supplement identity or integrity; it is not a
replacement for the typed carrier reference when that carrier must resolve.

Do not reuse `ParticipantControlTargetKind` as a universal crossing vocabulary:
it intentionally describes API-409 control targets and does not own
observations, projections, inject deliveries, or evidence. Define any genuinely
new crossing direction/kind vocabulary once, keep it closed, and bind it to the
concept-authority surface rather than copying local enums across packages.

### Keep decision, operation, and realization coordinates independent

A decision binds the request/candidate identity, participant and episode,
direction and interaction kind, actor/controller/authority basis, exact policy
identity/revision/digest, effective order and order model, markings,
backend-support posture, disposition and safe reason code, required evidence,
limitations, and predecessor references.

The following remain different claims:

- caller authorization, participant/controller authority, action admission,
  audience visibility, marking authorization, and declassification authority;
- withholding, projection/masking, redaction, transformation,
  declassification, disclosure, concealment/revocation, loss, and weakening;
- admitted, attempted, delivered, observed, persisted, and audited; and
- schema-valid, supported, implemented, tested, runtime-realized, and proved.

Decision composition is deny-first. Missing or unresolved required coordinates
reject or report unsupported/unknown under the owning vocabulary; they never
default to permit. A later policy revision, controller state, or
declassification cannot authorize an earlier crossing.

A transformation records source and result identity/digest, rule identity and
revision, actor/authority, source and result markings, evidence/provenance, and
loss. It never mutates its source. A transformed action or proposal receives a
new identity and fresh structural, semantic, and admission validation; it does
not inherit approval, admission, execution, delivery, or idempotency state.

### Link realization to existing occurrence evidence

An API-423 realization relation may record a bounded realization disposition
and link decision, attempt, delivery, observation, audit, evidence, and
provenance identities. It must not recreate the state machines or payloads of:

- `ParticipantLifecycleEventModel`,
  `ParticipantBehaviorHistoryEventModel`, or
  `ParticipantActionResultModel`;
- `ParticipantObservationEnvelopeModel`;
- `ParticipantControlOccurrenceModel`;
- SEM-226 exposure occurrence/realization records;
- experiment evidence records; or
- downstream `AuditEvent` and append-only runtime history.

Scheduling is not attempted delivery; attempted delivery is not delivery;
delivery is not observation; observation is not action; and audit retention is
not participant egress. A realization status that claims one of these facts
must cite the owning record and pass participant/episode, policy/order,
marking, and subject agreement checks.

### Validate each invariant at one owning layer

Closed shape, bounded scalar/list constraints, unique references,
branch-specific requiredness, and single-record cross-field rules belong in
`ContractModel` descendants and equivalent JSON Schema constraints.

Cross-record agreement belongs in one contract-level semantic validator
following `validate_participant_control_occurrence_context()` and
`validate_participant_decision_surface_context()`. Its resolution context is
the seam for known typed subjects, policy revisions, control occurrences,
transformations, lifecycle/delivery/observation facts, evidence, and audit
references. Do not repeat those joins in model validators, API handlers,
runtime services, repositories, backends, and conformance runners.

Non-schema-expressible obligations must be published through the existing
`x-aces-invariants` / `aces-semantic-invariants-v1` mechanism. The shared
validator must fail closed on unknown or mismatched typed refs, identity reuse
with different semantics, participant/episode disagreement, stale policy or
subject revision, contradictory direction/kind/disposition, invalid order,
unauthorized marking weakening, transformation cycles or source mutation,
realization without the required owning occurrence, and required evidence that
does not resolve.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Contract closure and primitives | `ContractModel(extra="forbid")`, `NonEmptyString`, `PrefixedDigestString`, `Rfc3339DateTimeString`, non-negative/positive integer aliases, and existing participant-runtime literals. Add no DTO base or primitive package. |
| Runtime envelope | `ParticipantRuntimeBaseEnvelopeModel` and its event/source/raw-integrity components. Reuse it unchanged and do not restate evidence, provenance, marking, redaction, time, or participant/episode fields. |
| Control and action subjects | API-409 `ParticipantControlOccurrenceModel` plus its contextual validator; SEM-211 action contracts/admission; lifecycle, behavior-history, and action-result records. Link by typed ref and retain each owning lifecycle. |
| Projection and observation | `ParticipantObservationEnvelopeModel`, `ParticipantContextViewModel`, `ParticipantHistoryViewModel`, `ParticipantStatusViewModel`, `ParticipantDecisionSurfaceModel`, and SEM-226 exposure selectors/realizations. Current API-408 retrieval authorization is not participant-safe egress authority. |
| Participant injects | DSL-142 `ParticipantInjectDelivery`, its compiled stable addresses, original DSL-111 inject/event/script/story identity, temporal constraints, and evidence requirements. Required evidence is not produced evidence or a delivery receipt. |
| Evidence, provenance, and claims | Base-envelope refs, `ExperimentEvidenceRecordModel`, `BehavioralClaimBindingModel`, existing loss/limitation fields, and append-only evidence/history semantics. Reference these; do not create an API-423 evidence store or proof vocabulary. |
| Validation | Pydantic model validators, focused `validate_*_context()` helpers, `_add_aces_invariant()`, and `aces-semantic-invariants-v1`. One resolver-backed join validator owns cross-record agreement. |
| Concepts and capability | `controlled-vocabularies-v1`, `concept-families-v1`, existing concept binding validators, API-407 participant feature-support declarations, and the exact/bounded/disclosed-weak/unsupported scale. Capability does not grant authority or prove realization. |
| Publication and compatibility | `contracts/schemas/participant-runtime/`, `contracts/fixtures/participant-runtime/`, `contracts/schema-publication/entries/`, `schema_bundle()`, explicit generator routing, `tools/check_generated_schemas.py`, and `tools/check_schema_publication.py --base-rev`. |
| Diagnostics and errors | `Diagnostic`, `DiagnosticModel`, `Severity`, operation result envelopes, bounded HTTP details, and the redacted unexpected-error envelope. Add no API-423 exception hierarchy or logger. |
| Downstream persistence/audit | `RuntimeSnapshot`, `ControlPlaneStore`, and `AuditEvent`. API-423 publishes portable relations only; RUN-319 owns append-only enforcement and persistence. |
| Lineage | The participant section of `docs/explain/sdl/lineage.md`, `SDLLineageLedgerModel`, its source audit, and `tools/check_sdl_lineage.py`. Update delivery status/evidence/nonclaims; change the ledger or source audit only for a changed normative derivation or compatibility claim. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, repo/requirement policy, authority, schema, fixture, concept, lineage, compatibility, and documentation checks. Add no issue-local runner or publication ledger. |

## Cross-Cutting Layers And Security Posture

1. **Contract and published-shape gate.** Closed hand-governed schemas and
   matching `ContractModel` descendants reject unknown keys, unbounded bags,
   illegal stage combinations, malformed ids/digests/times, and missing
   security coordinates. Valid/invalid fixtures must pass both Draft 2020-12
   schema validation and Python model validation.
2. **Reference and policy gate.** The shared context validator resolves typed
   carrier, policy/revision, participant/episode, order, marking,
   transformation, realization, evidence, and audit joins. Unknown required
   refs, contradictory decisions, stale revisions, and unsupported required
   posture fail closed.
3. **Secret and hidden-content gate.** Contracts, schemas, fixtures,
   diagnostics, audit details, logs, lineage, and issue evidence carry safe
   ids, refs, digests, controlled codes, markings, classifications, and bounded
   limitations only. They exclude credentials/tokens/keys, prompts or private
   memory, hidden answers/state, raw rejected input, policy bodies, environment
   dumps, backend objects, and raw evidence/payload content.
4. **Diagnostic and error-envelope gate.** Validation messages are
   value-independent and bounded. Public code must not stringify rejected
   records or Pydantic `ValidationError` input into diagnostics, responses,
   audit, or logs. Expected failures use existing `Diagnostic`/disposition
   contracts; unexpected HTTP failures retain
   `{"detail":"internal server error"}`.
5. **Publication and compatibility gate.** Every new schema needs an explicit
   participant-runtime path, valid/invalid fixtures, a publication entry with
   current hash and `last_change`, identical `schema_bundle()` output, and
   base-revision compatibility classification. Existing carriers and
   `ParticipantRuntimeBaseEnvelopeModel` must not be tightened incidentally.
6. **Concept and claim gate.** Direction, interaction, disposition,
   transformation, disclosure, loss, weakening, and support terms have one
   authority. Structural validity is not reported as authorization,
   enforcement, backend support, delivery, observation, noninterference, or
   proof.

API-423 itself adds no HTTP route, authentication mechanism, configuration or
environment-binding shape, secret loader, CLI argument, subprocess, daemon,
socket, filesystem store, or process-argument surface. Adding one is a scope
breach. Consequently, no API-423 value belongs in environment variables,
process argv, filenames, stdout/stderr, shell strings, or host logs.

A later runtime adapter must enter through `create_control_plane_app()`,
`ControlPlaneSecurityConfig.strict_defaults()`, verified bearer/proxy identity,
role and target binding, request-size guards, request fingerprints, idempotency
keys, and `AuditEvent`. It must then separately bind the authenticated caller
to actor, controller, participant, audience, authority basis, and policy.
Operator or auditor role cannot grant participant visibility, action authority,
or declassification. Future persistence belongs in first-class append-only
`RuntimeSnapshot`/`ControlPlaneStore` fields, not snapshot `metadata`, generic
history `details`, logs, audit bodies, or a gateway-local database.

## Extensibility Seam

The stable seam is a closed stage record plus a resolver-backed typed subject
relation. It is parameterized by participant, episode, audience, direction,
interaction kind, policy identity/revision/effective order, order model,
actor/controller/authority, subject kind/ref/revision, markings,
transformation/declassification rule, backend posture, disposition,
evidence/provenance, loss/weakening, and predecessor/realization refs.

The resolution context, rather than the published payload, supplies the known
carrier indexes and policy history. This allows the next reasonable changes—a
new governed carrier kind, streaming or multi-part realization, partial-order
delivery, another audience, or RUN-319 persistence—to add a closed variant or
resolver capability without modifying existing payload carriers, the runtime
base envelope, or earlier records. New wire meaning still requires compatible
contract evolution; an open metadata extension is not the seam.

## Gotchas And Anti-Patterns

Avoid:

- a generic message, payload, policy, evidence, metadata, details, or extension
  bag, or an optional-field union that collapses all crossing stages;
- copying action, observation, lifecycle, context, inject, control,
  evidence/provenance, or audit payloads into API-423 records;
- reusing an API-409 target enum as a universal carrier registry or creating
  duplicate direction/disposition/transformation vocabularies in multiple
  packages;
- treating authenticated caller, actor, controller, authority, participant,
  producer, backend, and auditor as one identity;
- treating approval as admission, admission as attempt, schedule as delivery,
  delivery as observation, observation as action, or audit as disclosure;
- treating redaction, masking, hashing, summarization, loss, or weakening as
  authorization or declassification;
- applying current policy to past order points, using wall-clock/list/receipt
  order, last-writer-wins, mutating prior history, or retroactively revoking
  participant knowledge;
- mutating a source during transformation or carrying its approval/admission/
  realization state to the result;
- validating cross-record joins independently in schemas, model validators,
  route handlers, stores, backends, and tests;
- raw secrets, hidden payloads, policy bodies, rejected values, backend
  objects, exception text, tracebacks, or environment/process data in any
  portable or observable surface;
- modifying the shared participant envelope for convenience;
- inferring backend support or runtime realization from contract publication,
  model methods, passing fixtures, or capability booleans;
- a second schema registry, publication ledger, concept catalog, validator
  stack, fixture runner, exception hierarchy, persistence store, audit channel,
  logger, or workflow branch; and
- changing the lineage ledger/source audit solely because delivery status
  changes.

## Non-Goals And Implementation Boundaries

- No participant gateway, transport, endpoint, UI, policy engine or expression
  language, provider integration, credential broker, or human-control service.
- No generic participant message DTO or second action, observation, lifecycle,
  context, intervention, inject, evidence, provenance, or audit carrier.
- No runtime enforcement, action admission, transformation execution,
  delivery, observation, persistence, replay, backend realization, capability
  implementation, or migration logic.
- No policy body, participant prompt/chain-of-thought/private memory, hidden
  state, credential, raw rejected input, or backend-private object in portable
  records.
- No claim that schema/model/fixture validity proves authorization, delivery,
  observation, runtime realization, backend conformance, noninterference,
  trace equivalence, simulation, refinement, epistemic equivalence, or
  bisimulation.
- No lineage-ledger/source-audit change unless implementation changes a
  normative external derivation or compatibility claim.
