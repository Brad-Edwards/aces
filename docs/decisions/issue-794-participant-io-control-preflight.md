# Issue 794 Participant I/O Control Adoption Preflight

Date: 2026-07-15

Issue: #794.

Requirements: none. The GitHub issue title, body, acceptance criteria, and
non-goals are the contract. Live Ground Control status was unavailable during
this preflight, so requirement state must be read from Ground Control when the
assessment is performed; it must not be inferred from this checkout.

This note records non-normative architecture guardrails for the assessment and
adoption-design work. It does not publish the adoption ADR, amend a formal
specification, create or disposition requirements, create implementation
issues, select a participant I/O gateway, or implement schemas, runtime code,
backend behavior, conformance, or migration.

## Decisive Current-State Finding

ACES currently has adjacent participant-control mechanisms, not one portable
participant ingress/egress semantic boundary or enforcement point.

- [ADR-022](adrs/adr-022-participant-behavior-and-interaction-semantics.md) and
  `specs/formal/participant-semantics/` define world/view/history separation,
  action and observation contracts, visibility transitions, and participant
  information boundaries. Noninterference and disclosure/declassification are
  rationale-level obligations, not a revisioned machine-readable IFC policy,
  relation, checker, proof, or runtime realization.
- [ADR-054](adrs/adr-054-participant-runtime-observable-lifecycle.md) and
  `specs/formal/participant-runtime/` define the observable lifecycle,
  admission dispositions, ordering, projections, markings, redaction, shared
  state, and concurrency. `ParticipantControlMixin` and
  `ParticipantActionAdmissionRequest` provide an internal Python admission
  path and binding checks, but do not constitute a transport-neutral ingress
  contract or complete SEM-211 policy evaluator.
- [ADR-060](adrs/adr-060-participant-backend-facing-contract-surface.md) is
  proposed and existing API-406/API-408 carriers provide lifecycle,
  observation, status, history, and context shapes. The reference API-408
  retrieval code synthesizes visibility references and currently supplies no
  marking or redaction policy. Its HTTP authorization is for backend,
  operator, and auditor callers, not participant-address authorization. DTO
  construction and control-plane read authorization therefore do not establish
  participant egress enforcement. Its `portable_equivalent` comparability class
  is a view-carrier classification, not behavioral equivalence or proof, and
  must be explicitly reconciled by the assessment.
- [ADR-083](adrs/adr-083-participant-tool-decision-surface-and-exposure-semantics.md)
  is proposed. It cleanly separates action meaning, authored availability,
  apparatus support, run selection, current decision surface, realized
  exposure, and outcome, but its implementation issues are not evidence of
  delivered runtime mediation.
- SDL `Inject` and compiled orchestration inject/event records model scheduled
  orchestration resources. They do not bind participant addressees,
  observation boundaries, authorization, declassification, delivery receipts,
  or participant behavior history. An environment inject is not participant
  input merely because a participant may later observe its effects.
- Participant decision modes and lifecycle values include useful adjacent
  terms such as human supervision, mixed control, external supply, admission,
  and withholding. They do not define approval, external direction,
  intervention, controller handoff, override, cancellation, or control-lease
  transitions.
- [ADR-081](adrs/adr-081-behavioral-relation-taxonomy-and-claim-discipline.md)
  and `contracts/concept-authority/behavioral-relations-v1.json` define claim
  discipline and several trace, simulation, bisimulation, projected-history,
  and epistemic relations. The catalog does not presently make an IFC
  noninterference policy authoritative. Its implemented and bounded relations
  do not prove noninterference or bisimulation.

The issue must preserve this finding. It may adopt one coherent semantic
boundary, but that means common policy coordinates, ordered decisions, and
evidence obligations across existing carriers. It does not require one generic
message schema, one transport, or routing every orchestration inject through a
participant gateway.

## Existing Threads And Required Disposition

| Thread | Preflight disposition |
| --- | --- |
| #71, SEM-208 through SEM-213, ADR-022 | Reuse as participant semantic authority. Compose or strengthen it for IFC policy, governed disclosure, and labelled control transitions; do not replace its world/view/history or action/observation model. |
| #74, RUN-305 through RUN-308, ADR-054 | Reuse the lifecycle, envelope, ordering, projection, shared-state, and concurrency model. Strengthen portable realization and evidence obligations; do not create another lifecycle or history. |
| #119, SEM-219, SEM-220, SEM-226, ADR-083, #294 through #296 | Preserve its seven authority layers and its refinement of `V_p,t`. Treat proposed design and spawned work as dependencies/evidence to inventory, never as implementation completion. |
| #747, ADR-081, behavioral-relation catalog | Reuse the catalog, claim bindings, assurance axes, and nonclaim discipline. Revise the governed catalog only if the adoption makes a new relation authoritative; do not create an IFC-local equivalence vocabulary. |
| ACT-617, RUN-310, API-409, #251, #252, #255 | Treat current modes, actors, admission dispositions, provenance, and behavior history as adjacent primitives only. The adoption authority must distinguish proposal, approval, external direction, intervention, handoff, override, cancellation, admission, execution, and observation. |
| API-406 and backend participant contracts | Reuse the common envelope, neutral carriers, backend manifest, feature-support disclosure, capability-gap diagnostics, and conformance reports. Add no backend-specific participant DTO family. |
| DSL-111 and orchestration injects | Preserve orchestration identity and scheduling. Participant-directed delivery must compose with participant observation/disclosure and record delivery evidence; environment-only injects remain orchestration concerns. |
| Scientific-completeness delivery assessment | Preserve the partial participant-relative information-flow finding as a gap signal. Reconcile it against current artifacts; do not promote a profile result to proof or runtime realization. |

The assessment ledger must record each artifact's authority and independent
states for definition, implementation, test, model-check/proof, and runtime
realization, with evidence refs and explicit nonclaims. `accepted`, `closed`,
`active`, schema-valid, fixture-passing, bounded-probe success, and backend
realization are different facts. Existing formal-spec sufficiency text and
`specs/formal/assurance-fulfillment.yaml` also require reconciliation against
newer code and tests; neither should be silently treated as the sole status
source.

## Adoption-Design Guardrails

### Compose existing authorities; publish one new composing decision

Issue #794 warrants a new ADR because no current authority owns the composition
of participant IFC, input mediation, output projection, intervention, inject
delivery, backend realization, and relation-specific assurance. The ADR must
compose ADR-022, ADR-041, ADR-054, ADR-060, ADR-066, ADR-067, ADR-079, ADR-081,
and ADR-083. Accepted ADRs are not edited into a new meaning; use the ADR-059
amendment/supersession rules and give every changed authority an explicit
migration disposition.

The formal design must use the existing participant-relative objects and add
only missing predicates, labels, transitions, policies, and evidence
obligations. It must not introduce a second world state, participant view,
history, observation boundary, action contract, exposure policy, runtime
lifecycle, relation registry, or provenance system.

### Share semantic coordinates, not object identity

Every governed crossing should be evaluable at an explicit tuple containing:

- participant and episode identity;
- ingress or egress direction and interaction kind;
- source, actor, current controller, and authority basis;
- action-contract, observation-boundary, inject, intervention, or payload ref;
- observation/order point and the declared clock, simultaneity, partial-order,
  scheduler, and nondeterminism treatment where relevant;
- policy identity, revision/digest, security markings, authorization result,
  disclosure/declassification basis, and redaction/transformation refs;
- admission/delivery disposition and reason code;
- backend capability/realization posture, weakening or rejection decision; and
- provenance, evidence, loss, limitation, and claim-binding refs.

These are parameters of the existing semantic relations and envelopes, not a
mandate for a `ParticipantIOEvent`, untyped `message`, or universal gateway
DTO. Participant action proposals, approvals, external directions,
interventions, and injects remain distinct ingress kinds. Observations,
masked/projection outputs, and inject-delivery receipts remain distinct egress
or evidence records. They share policy evaluation, temporal coordinates,
dispositions, and provenance.

Observable and hidden are participant- and policy-relative projections of
governed labels, not intrinsic booleans on an action. A controller change may
be hidden from one participant, visible to another, and always retained for an
authorized audit surface. The formal design must define the action-label
alphabet, transition and hiding/projection relations, stuttering or `tau`
treatment, and matching coordinates. It must also state when ordering is total,
partial, simultaneous, causal, or backend-observed; timestamp equality is not
an ordering rule.

### Keep information-flow operations distinct

- **Authorization/admission** decides whether a crossing is permitted now.
- **Withholding** records that content was not delivered.
- **Projection/masking** selects participant-visible content from an authorized
  source at an observation point.
- **Redaction** transforms the representation after authorization; it is not an
  authorization grant.
- **Declassification/disclosure** is a governed authority decision that may
  widen future release under an explicit what/where/when/who/basis policy.
- **Concealment/revocation** changes future availability; it cannot erase
  information already learned by a participant.
- **Loss or weakening** describes unavailable fidelity/evidence and must not be
  reported as a successful security transformation.

Visibility, marking authorization, and caller authorization compose
deny-first. No one dimension may widen another. A disclosed payload still
passes participant scope and observation policy; a visible item still requires
admission where it is actionable. Derived or transformed content inherits the
source markings and provenance by default; only an explicit governed
declassification decision may weaken them.

Input or output modulation is an auditable transformation, not an invisible
rewrite. Preserve the source ref/digest, transformed ref/digest, rule and
revision, actor/authority, reason, loss/weakening, markings, provenance, and
evidence. A transformed action proposal is revalidated and admitted as the
resulting proposal; it must not silently change participant intent or inherit
the source admission result.

### Keep IFC claims and behavioral relations precise

Noninterference is an information-flow property; projected-history equality,
trace inclusion, simulation, refinement, and bisimulation are relations that
may support particular claims under declared models. They are not synonyms.
For every claim surface the design must bind the exact relation, subject,
projection/purge, policy revision, initial low-equivalence, high/hidden inputs,
allowed declassification events, quantifiers, time/order model, environment and
scheduler assumptions, termination/progress/timing sensitivity, probability or
nondeterminism treatment, and assurance status.

If noninterference is adopted, its governed definition must state whether its
obligation is expressed by low-equivalent traces, purge/unwinding,
self-composition, a simulation, or another precise formulation. Bisimulation
may be a chosen proof obligation only when the labelled transition systems,
hidden-action treatment, divergence, quantifiers, and proof artifact exist.
Bounded equal projected histories remain bounded evidence; they are not a
universal noninterference or bisimulation proof.

### Distinguish intervention and inject semantics

Approval is not execution, intervention is not merely an admission reason, and
behavior mode is not a mutable controller state. The design must preserve
ordered records for proposal, approval/denial, controller or authority change,
override/cancellation, admission, attempt, result, observation, and handoff.
Late or concurrent decisions need explicit stale-decision and conflict rules;
wall-clock timestamps alone are insufficient.

A participant-directed inject should retain its orchestration inject identity
while being governed as a participant disclosure/observation at delivery. If
it directs an action or changes control, it additionally binds the applicable
external-direction/intervention transition. An environment-directed inject
remains outside participant ingress and becomes participant-visible only
through the normal observation projection.

### Make backend obligations portable and fail closed

Backend support must extend the existing manifest feature-support pattern with
governed feature ids, support strength, disclosure refs, limitations, and
conformance evidence. Do not add scattered booleans or infer support from a
method's presence. Unsupported required semantics reject admission or target
selection. A permitted downgrade must be explicit, policy-authorized,
provenance-bound, participant/audience-visible where required, and unable to
claim the stronger relation.

Reference runtime behavior and backend realization remain separate claims.
Portable contracts state required inputs, outputs, dispositions, histories,
and evidence. A backend declares capability, realizes those obligations, and
is assessed by the existing bounded conformance machinery. Schema presence,
method presence, or passing probes does not prove runtime realization or a
universal relation.

## Canonical Cross-Cutting Incumbents

| Concern | Required incumbent and boundary |
| --- | --- |
| Authored SDL ingress | `load_sdl_yaml()`, source-profile limits, YAML 1.2 safe loading, duplicate/canonical key checks, `parse_sdl()`/`parse_sdl_file()`, `SDLModel(extra="forbid")`, `Scenario`, and `InstantiatedScenario`. Do not read raw YAML mappings in participant-control code. |
| Semantic validation | `SemanticValidator`, participant-behavior analyses, controlled-vocabulary/reference validation, instantiation, and full post-instantiation revalidation. Add rules here rather than a gateway-only validator. |
| Participant semantics and compiler | Existing action contracts, precondition/effect/failure classes, view rules/transitions, observation boundaries, behavior specifications, `ParticipantBehaviorRuntime`, compiled canonical addresses, and `view_relation_timeline`. |
| Neutral contracts | `ContractModel(extra="forbid")`, `ParticipantRuntimeBaseEnvelopeModel`, participant lifecycle/observation/shared-state/history/context models, `ParticipantImplementation*` models, `ParticipantExposurePolicyModel`, and `BehavioralClaimBindingModel`. Compose refs before adding a carrier. |
| Runtime admission and projection | `ParticipantControlMixin`, `ParticipantActionAdmissionRequest`, `participant_action_admission_request_violations()`, `ParticipantRuntime`, `BaseParticipantRuntime`, behavior-history/action-result records, and participant retrieval view models. Extend their obligations; do not treat current retrieval projection as a security enforcer. |
| Security and HTTP | `create_control_plane_app()`, `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneIdentity`, `ControlPlaneRole`, verified bearer/proxy identity, target binding, request-size guards, request fingerprints, idempotency keys, and `AuditEvent`. Caller auth, participant authority, and visibility remain separate gates. |
| State and persistence | First-class `RuntimeSnapshot` fields and `ControlPlaneStore` with `InMemoryControlPlaneStore`/`LocalControlPlaneStore`; existing episode, behavior, observation, shared-state, operation, audit, evidence, and provenance histories. No participant-gateway side store. |
| Backend capability | `BackendManifest`, `BackendManifestV2Model`, `ParticipantRuntimeCapabilities`, `ParticipantFeatureSupport`, `participant_runtime_capability_contract_gaps()`, and participant implementation manifests/selections. |
| Conformance and assurance | `aces_conformance`, `BackendConformanceReport`, existing fixture/target probe runners, `Diagnostic`/`Severity`, participant invariant oracles, negative leakage tests, property tests, counterexamples, formal-assurance policy, and behavioral claim bindings. Extend these rather than create an IFC runner/report silo. |
| Schema and concept governance | `schema_bundle()`, `contracts/schemas/`, valid/invalid fixtures, `contracts/schema-publication-manifest.json`, concept-authority catalogs/bindings, controlled vocabularies, ADR-061 compatibility classification, and generated-corpus parity. Free-form metadata is not authority. |
| Errors and observability | Collected SDL diagnostics, `Diagnostic`, `Severity`, `OperationReceipt`, `OperationStatus`, bounded HTTP 4xx details, the redacted FastAPI 500 envelope, `AuditEvent`, and `SessionReporter`. No new exception hierarchy, logger, or audit channel. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, `tools/verify_all.py`, repo-policy, requirement-governance, concept-authority, generated-schema, schema-publication, JSON-artifact, assurance, semantic-coverage, and docs checks. Requirement authority must exist before implementation issues depend on it. |

The package boundary remains `aces_sdl` for authored meaning,
`aces_processor` for compiled projections, `aces_contracts` for neutral
carriers, `aces_runtime` for live control/security/persistence,
`aces_backend_protocols` for backend obligations, and `aces_conformance` for
bounded assessment. `implementations/python/src/aces/` is compatibility-only
and must not acquire logic.

## Security And Operational Gates

1. **SDL parser and shape gate:** new authored policy references pass UTF-8,
   byte/scalar/alias/node/depth limits, forbidden-tag/directive checks,
   duplicate and canonical-key checks, variable rules, closed Pydantic shapes,
   semantic reference resolution, and post-instantiation validation. Policies
   are referenced/versioned artifacts, not executable expressions or arbitrary
   dictionaries.
2. **Contract and configuration gate:** every portable addition is a closed
   contract and passes model validation, generated JSON Schema, semantic
   invariants, valid/invalid fixtures, publication-manifest change accounting,
   compatibility review, concept binding, and consumer parity. Do not encode
   policy or transition meaning in `constraints`, `metadata`, `details`, or a
   backend configuration bag.
3. **Authentication and policy gate:** any future HTTP surface enters through
   the existing fail-closed app, size guard, identity verification, role and
   target binding, mutation idempotency/fingerprinting, and audit. It then
   separately evaluates participant actor/authority, action admission, and
   participant visibility/marking/declassification policy. Passing control-plane
   auth never bypasses the latter gates. A future participant-facing adapter
   must explicitly bind an authenticated principal to a participant subject;
   it must not impersonate a participant through the operator role or create a
   second authentication stack.
4. **Secret and hidden-state gate:** contracts, snapshots, audit, diagnostics,
   logs, errors, fixtures, and provenance carry safe ids, refs, digests,
   classifications, and bounded summaries only. Credentials, tokens, keys,
   hidden prompts/answers, world truth, policy bodies, raw rejected payloads,
   backend object representations, and environment dumps must not cross the
   participant or observability boundary.
5. **Projection and error-envelope gate:** participant egress must evaluate the
   compiled observation boundary, `V_p,t`, order point, exposure policy,
   markings, caller/participant authorization, declassification, redaction,
   loss, and evidence basis before serialization. Expected rejection uses
   stable dispositions and bounded diagnostics/4xx messages. Unexpected failure
   retains the redacted `{"detail":"internal server error"}` envelope; neither
   path echoes content or hidden policy facts. Reuse existing request-size and
   timeout patterns for payload, rate, execution, and output bounds; truncation,
   dropped delivery, and timeout are explicit loss/failure outcomes rather than
   silent masking.
6. **Persistence and audit gate:** append-only decisions and realized outcomes
   use existing snapshot/store and evidence/provenance carriers, including
   policy revision and order coordinates. Audit is not a participant
   observation, and raw backend logs are not evidence or disclosure.
7. **Environment and OS/process gate:** this design needs no new environment
   binding, secret loader, daemon, or subprocess. A later concrete adapter must
   use injected credential/policy providers, fixed invocation shapes,
   controlled working directories, bounded timeouts, and no `shell=True`; it
   must not place secrets, hidden content, policy bodies, or arbitrary payloads
   in argv, environment dumps, stdout, or stderr.
8. **Backend and conformance gate:** capability declaration validates against
   the canonical manifest and vocabulary, target admission rejects missing
   required semantics, realized crossings retain provenance/evidence, and
   existing conformance reports disclose finite scope and explicit nonclaims.

## Extensibility Seam

The stable seam is a policy-evaluation and projection relation over existing
addresses and envelopes, parameterized by participant/episode, direction,
interaction kind, actor/controller/authority, order and time model, policy
revision, projection and action refs, markings/declassification/redaction,
backend support posture, and evidence/provenance. Payloads remain typed existing
carriers or stable refs.

That seam must admit the next reasonable variants without redefining the core:
a participant-directed inject, human approval, temporary controller handoff,
automated intervention, per-phase policy revision, streaming output, weaker
backend realization, another audience projection, and later timed,
probabilistic, partial-order, or strategic claim models. Variation belongs in
explicit governed parameters and capability entries, not new top-level event
families or booleans.

## Gotchas And Anti-Patterns

Avoid:

- declaring that ACES already has one I/O boundary because related models,
  methods, endpoints, or specs exist;
- adding a generic `ParticipantIOEvent`, `message`, gateway DTO, policy bag,
  second visibility taxonomy, or duplicate action/observation history;
- exposing API-408 reference views directly to participants on the assumption
  that `_project_scope()` or a synthesized visibility ref is security masking;
- conflating control-plane caller authorization, participant authority,
  authored operating scope, backend capability, and participant visibility;
- conflating withholding, masking/projection, redaction, declassification,
  concealment, revocation, unsupported behavior, loss, and unknown state;
- treating approval as execution, intervention as an admission reason,
  behavior mode as controller state, or every inject as participant input;
- modifying a proposal in place, carrying its prior admission across a
  transformation, or deduplicating distinct attempts solely by payload value;
- treating an exposed action/tool as applicable, admitted, executed, or
  observed, or treating an implementation expectation as a grant;
- inferring past disclosure from current state, using future authorization to
  justify earlier exposure, or pretending revocation erases participant
  knowledge;
- using only wall-clock timestamps where concurrency, simultaneity, causality,
  stale approvals, or partial order matter;
- ignoring termination, progress, timing, scheduling, nondeterminism, chance,
  or concurrency while making an IFC or equivalence claim;
- calling projected-history equality noninterference, calling trace inclusion
  bisimulation, or promoting finite fixtures/probes/model checks to universal
  proof;
- adding capability booleans, backend-local downgrade conventions, free-form
  reason strings, hidden fallbacks, or success-with-warning when required
  semantics are absent;
- placing policy in `ParticipantExposurePolicyModel.constraints`, snapshot
  metadata, history details, audit details, logs, or backend-native DTOs;
- duplicating schemas, validators, controlled vocabularies, exception
  hierarchies, persistence, audit/logging, conformance runners, workflow logic,
  or schema registries;
- hand-editing generated schemas, bypassing publication and compatibility
  gates, adding logic to the compatibility tree, or changing an accepted ADR's
  meaning in place; and
- assigning implementation issues before their governing requirement authority
  exists or treating issue/requirement/ADR status as implementation evidence.

## Non-Goals And Implementation Boundaries

- No production SDL, schema, parser, compiler, contract, API, runtime, backend,
  persistence, migration, conformance, or proof implementation in issue #794 or
  this preflight.
- No selection or construction of a concrete participant I/O gateway,
  transport, UI, model provider, or human-control service.
- No universal noninterference, trace inclusion, equivalence, simulation,
  refinement, epistemic, strategic, or bisimulation claim from current bounded
  evidence.
- No forced unification of environment injects, participant observations,
  action proposals, approvals, interventions, and outputs into one carrier or
  transport.
- No replacement of participant, runtime, orchestration, observability,
  apparatus, backend-contract, or behavioral-relation authority without an
  explicit disposition and migration path.
- No requirement disposition, milestone issue graph, or implementation issue
  creation in this architecture preflight. The issue's assessment must perform
  those actions against live Ground Control and GitHub state after the adoption
  authority is settled.
