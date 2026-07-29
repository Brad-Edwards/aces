# Issue 810 Participant-Relative Opacity Architecture Preflight

Date: 2026-07-29

Issue: #810.

Requirements: none. The GitHub issue title, body, acceptance criteria, and
non-goals are the contract. Requirement-backed child work must not begin until
its owning DRAFT Ground Control authority exists.

This note records repository-wide architecture guardrails for the opacity
design and program. It is guidance only: it does not adopt an opacity relation,
publish or amend an ADR, change a formal specification or catalog, create a
requirement or child issue, implement a checker or runtime path, certify a
backend, or establish an opacity claim.

## Decisive Current-State Finding

RAES has the semantic carriers and enforcement/evidence seams needed to define
participant-relative opacity without creating a second information-flow
architecture. It does not yet have a governed opacity relation or a sufficiently
typed claim binding for one.

- ADR-022 separates world state, participant-visible state, participant local
  history or belief, and archival evidence.
- ADR-081,
  `contracts/concept-authority/behavioral-relations-v1.json`, and
  `raes_contracts.behavioral_relations` own revisioned relation identity,
  dimensions, assurance, and claim discipline. The current taxonomy is
  `raes-behavioral-relations` revision `rev4`; it contains
  `participant-projected-history-equivalence`, `policy-noninterference`, and
  `epistemic-indistinguishability`, but no opacity relation.
- ADR-085, ADR-095, and SEM-230 revision 2 own participant-relative projection,
  exact-cut policy decisions, adaptive low strategies, dynamic purge,
  declassification, memory scope, and the incumbent policy-noninterference
  claim. SEM-230 explicitly delegates opacity and supervisor visibility to
  issue #810.
- API-423 crossing contracts and RUN-319 mediation already distinguish request,
  decision, transformation, disclosure, delivery attempt, delivery,
  observation, and audit facts. They preserve participant, episode, audience,
  controller, policy decision/cut, order, backend posture, evidence, provenance,
  marking, loss, and append-only history.
- ASR-535 conformance already separates a catalog-bound obligation from a
  finite probe report. `BackendConformanceReport` remains
  `bounded-probe-success` even when a case attempts to falsify
  `policy-noninterference`.

The gap is not another redaction flag, access-control rule, event DTO, policy
engine, belief store, or conformance runner. The gap is a revisioned epistemic
security property plus a typed instantiation of its observer, secret,
information, supervisor-visibility, horizon, strategy, time/order, and
assurance coordinates.

The current `BehavioralClaimBindingModel` can name a relation, subject,
carriers, observation projection, quantifier/evidence scope, assurance status,
evidence, limitations, and nonclaims. It cannot structurally bind a secret
predicate, observer or coalition, initial-information model, memory/horizon
profile, active strategy domain, or supervisor-visibility profile.
`ParticipantPolicyBinding` carries some missing SEM-230 coordinates beside the
shared claim inside the conformance package; it is a bounded report adapter,
not a second relation authority and not a shape to copy into an opacity-only
binding.

`RelationAssuranceModel` also has only definition, implementation, test, and
proof axes. For opacity, a generic `implemented` value would be ambiguous
between a checker, runtime mediation, and backend realization. The design must
preserve definition, bounded checking, finite-state model checking,
mathematical proof, runtime enforcement, and backend realization as independent
facts.

## Binding Authorities

- ADR-009 and ADR-019 govern normative artifact placement and authority.
- ADR-012 and ADR-062 govern shared concept authority and prohibit parallel
  semantic registries.
- ADR-021 governs falsification-first evidence and explicit nonclaims.
- ADR-022 and `specs/formal/participant-semantics/` own world/view/history,
  action, observation, interaction, information-boundary, and participant
  memory semantics.
- ADR-054 and `specs/formal/participant-runtime/` own observable participant
  lifecycle, occurrence identity, delivery/observation separation, ordering,
  markings, redaction, shared state, and concurrency.
- ADR-059 requires accepted ADR changes to use a recorded amendment or
  supersession. Issue #810 must not silently rewrite ADR-081 or ADR-085.
- ADR-060 owns neutral participant/backend contracts and support disclosure.
- ADR-061, the schema-publication entries, and the generated-schema gate govern
  published contract evolution.
- ADR-066 owns the separation between participant observation, operational
  telemetry, captured evidence, derived analysis, and authorized audit views.
- ADR-072 owns validation/admission strength disclosure. Structural validity,
  semantic validity, behavioral checking, evidence-backed results, and
  falsification-backed results are not interchangeable.
- ADR-081 and `specs/formal/behavioral-relations/README.md` own relation
  classification, catalog shape, claim bindings, dimensions, and overclaim
  policy.
- ADR-083 owns participant decision-surface and exposure distinctions.
- ADR-085, ADR-095, and
  `specs/formal/participant-semantics/information-flow-control.md` own SEM-230
  crossings, projection, exact-cut policy, declassification, memory, and
  policy noninterference.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and
  `tools/verify_all.py` own repository workflow and verification.
- The focused primary-source record in
  `docs/research/participant-opacity/prior-art-and-design-criteria.md` is design
  input, not relation authority or delivery evidence.

These authorities warrant a new opacity decision during the issue #810 design
work. That decision should compose ADR-081 and ADR-085 and use ADR-059 if either
accepted decision needs a substantive amendment. This preflight does not make
that decision.

## Architecture Decisions And Guardrails

### Select one predicate-opacity kernel, not one relation per variant

The design should select one-sided participant-relative predicate opacity as a
distinct governed relation, with a separate catalog identity. It must not alias
redaction, access control, policy noninterference, projected-history equality,
epistemic indistinguishability, trace equivalence, bisimulation, or an opaque
implementation.

Initial-state, current-state, K-step, infinite-step, language-based, symmetric,
passive, active, timed, partial-order, and supervisor-knowledge variants are
profiles or parameterizations of the kernel unless a variant changes the
mathematical property enough to require a separately sourced relation. The
baseline must state that it is one-sided and possibilistic. Symmetric and
probabilistic opacity are stronger, explicit selections.

The relation should use the catalog's epistemic class with unary direction, but
the secret predicate and the relation classification must remain distinct
concepts. Calling the secret a "predicate" does not by itself make the relation
equivalent to the catalog's structural-validity predicates.

The catalog entry must not manufacture a second carrier merely because the
current shared shape names `left_carrier` and `right_carrier`. Opacity is a
unary property of one declared possible-point system/profile. Use an explicit
not-applicable treatment for the unused side, or evolve the shared catalog
shape if it cannot represent that honestly; do not disguise the nonsecret
witness as a second system carrier.

### Reuse the existing possible-state carriers

The opacity carrier must compose existing state rather than define a second
world or participant model. A possible point needs at least:

```text
(model/supervisor realization, run, evaluation cut,
 observer local state and retained memory, exact-cut policy realization,
 scheduler/environment and order context)
```

The corresponding RAES coordinates come from SEM-230 `W`, `V`, `H`, `X`, `R`,
controller, authority, marking, and exact-cut policy state; participant
decision surfaces; API-409 control occurrences; and API-423 crossing,
delivery, observation, and audit occurrences. A possible point is not merely
two JSON event arrays or two final snapshots.

The information cell must be induced by a declared initial-information
function and accumulated observation function. A selected secret predicate
must be a revisioned, typed reference over allowed point coordinates and a
declared cut or horizon. Neither the predicate nor a counterexample may embed
raw secret payloads in a catalog, binding, diagnostic, report, or log.

### Make the observer and supervisor threat model explicit

An observer is a participant, a named audience, or an explicit coalition with a
declared observation-fusion and memory rule. Individual opacity never implies
coalition opacity. Observer, authenticated API caller, participant subject,
controller, policy authority, backend, operator, and auditor are independent
identities.

The relation profile must select one supervisor-visibility posture:

- full policy and supervisor realization known;
- public contract known, realization hidden;
- supervisor behavior learned online from decisions and effects; or
- selectively disclosed or delayed decision information.

For each posture, policy revision, policy body, supervisor implementation,
controller identity, control authority, decision rule, and revision/change
event must be classified as low, high, declassified, or observer-relative.
Hidden implementation is not hidden behavior. If approvals, denials, edits,
deferrals, handoffs, cancellations, timing, or changed outcomes distinguish a
supervisor revision, hiding the revision event does not preserve opacity.

### Treat the observation function as a security boundary

The observation profile must separately decide whether it retains:

- visible content, markings, and transformation/loss disclosures;
- occurrence, non-occurrence, withholding, and delivery status;
- approval, denial, failure, edit, cancellation, deferral, intervention,
  handoff, and other control decisions;
- decision content, occurrence, issuance, delivery, and timing;
- retry, replay, episode, controller-handoff, and policy-revision history;
- total order, participant-local order, causal partial order, simultaneity, or
  backend-serialized order;
- logical time, wall-clock time, duration, bucketed time, progress, or no time;
  and
- authorized retrieval, evidence, audit, and operational surfaces.

"Not observed" and "known not to have occurred" are different. Omission is
observable only when a declared opportunity, deadline, acknowledgement,
progress, or clock model makes absence detectable. A redacted denial can still
leak through its status, existence, ordering, latency, retry behavior, or error
envelope.

Audit and observability are not automatically outside the threat model. They
are separate planes under ADR-066, but an auditor, operator, retrieval client,
or coalition with access to them is an observer whose authorized surface must
be modeled.

### Keep active probing and passive observation separate

A passive profile observes admitted behavior only. An active profile quantifies
over a declared set of allowed adaptive participant strategies that map retained
observations to inputs. Actual and alternative worlds use the same strategy.
The strategy domain is bounded by participant capabilities, authority, action
contracts, admission policy, and the selected environment; "all strategies"
must not silently include impossible inputs or omit permitted probes.

Approval/denial or timing differences reachable only after an adaptive input
are still leaks. Finite scripted cases remain bounded falsification evidence
even when every allowed input in that finite model was enumerated.

### State time, concurrency, nondeterminism, and probability independently

The existing relation dimensions for nondeterminism, concurrency, probability,
time, and partial order remain canonical. The opacity profile must bind their
actual choices rather than inherit defaults from SEM-230 or from a backend:

- possibilistic baseline compares support, not probability mass;
- randomized or nondeterministic supervision changes the possible-point set but
  is not itself assurance;
- timed opacity requires a governed clock and timed observation model;
- a partial-order witness is valid only when its scheduler/order context is
  admitted by the carrier and observation equivalence;
- one linearization does not establish a partial-order claim; and
- probability-weighted leakage, posterior bounds, entropy, or differential
  privacy require a separate quantitative relation and evidence method.

### Preserve exact relation implications and non-implications

Under matching carriers, observers, initial information, observation maps,
memory, active strategies, release policy, time/order, scheduler, environment,
and probability treatment:

- SEM-230 policy noninterference implies opacity for every eligible secret
  predicate protected by that same policy;
- opacity of one predicate does not imply policy noninterference;
- epistemic indistinguishability defines membership in an information cell,
  while opacity constrains the secret labels present in the whole cell;
- one equal projected-history pair can provide one alternative witness but
  cannot discharge the universal actual-secret quantifier;
- trace inclusion/equivalence, simulation, refinement, and strong, weak, or
  branching bisimulation imply opacity only with an explicit preservation
  argument for the selected carrier, secret, and observation semantics; and
- opacity does not generally imply those structural or behavioral relations.

These are conditional mathematical statements, not a proof that any RAES
system satisfies them.

### Treat release, concealment, and prior knowledge correctly

Declassification may intentionally shrink the observer's information cell and
make a protected predicate knowable. That can be authorized and still change
knowledge. Conformance after release requires either a policy revision that no
longer protects that predicate or a remaining nonsecret alternative.

Concealment, revocation, rollback, and supersession alter future availability;
they do not erase prior observations from a remembering observer. The profile
must state memory behavior across retries, replay, episodes, policy revisions,
controller handoffs, and coalitions. An episode-local reset is not a knowledge
reset unless the observer model explicitly justifies it.

### Extend the shared claim seam; do not create an opacity registry

The catalog remains the only relation registry and
`BehavioralClaimBindingModel` remains the only consumer claim authority. The
design must not put opacity meaning into a consumer-local enum,
`ParticipantOpacityBinding`, backend report field set, SDL metadata, or prose
convention.

The smallest safe extension is an optional closed, revisioned
relation-parameter profile reference on the shared claim binding, with the
catalog declaring when the reference is required. For opacity, that profile
must resolve at least observer/coalition and audience, secret predicate and revision,
initial-information and observation functions, possible-point carrier,
horizon/cut, memory, passive/active strategy domain, supervisor visibility,
policy/release schedule, time/order/scheduler/environment, nondeterminism, and
probability-support choices.

Do not encode these as an untyped `dict`, duplicate them into every report or
runtime record, or overload `subject`, `evidence_boundary`, `limitations`, or
`observation_projection_ref` with a serialized mini-language. The binding
should reference the profile; the profile should reference existing carriers
and policy/observation artifacts by safe, revisioned identity.

This is a behavioral-relation parameter profile, not a GOV-920 semantic
profile, backend capability profile, validation profile, instantiation
profile, or participant support declaration. Those incumbent profile families
retain their current meanings.

This same seam must support the next reasonable variations—symmetric,
K/infinite-step, coalition, active, timed, partial-order, or quantitative
profiles—without adding fields to every claim-bearing carrier. A quantitative
variant may still require a separately governed relation; the parameter seam
must not be used to pretend a changed property is only configuration.

### Separate assurance axes in the shared catalog and reports

The shared assurance model must make these states independently representable:

- mathematical definition;
- checker or monitor implementation;
- bounded examples and negative-leakage tests;
- finite-state model checking and its exact model/bound;
- mathematical proof and assumptions;
- reference-runtime enforcement;
- backend capability declaration;
- backend realization; and
- bounded backend conformance.

A valid schema, catalog entry, profile, binding, example, runtime record,
manifest declaration, or passing probe establishes only its named state.
`BehavioralClaimBindingModel` and the catalog must reject universal
quantification backed only by finite evidence. `BackendConformanceReport` stays
the backend report family and must not become an opacity proof certificate.

Counterexamples and information-state witnesses should be bounded artifacts
with safe refs/digests, selected abstract coordinates, evidence boundaries, and
explicit nonclaims. They must not serialize raw secret worlds, participant
memory, policy bodies, prompts, credentials, hidden payloads, or backend-native
objects merely to make a witness inspectable.

### Keep enforcement claims narrower than the definition

Action admission can prevent an active probe; egress mediation can suppress or
transform a release; scheduling can coarsen or delay an observation; and a
synthesized or nondeterministic supervisor can preserve alternatives in a
declared model. None alone enforces opacity across every observation channel.

A runtime enforcement claim requires the complete selected observation surface
to pass one trusted mediation boundary, including failures, decision
occurrence, timing/order, retry and delivery behavior, policy/supervisor change
effects, and authorized evidence/retrieval views. A route-only response filter,
backend-local check, redactor, delayed message, or added random choice is
insufficient.

Reference runtime enforcement and backend realization remain separate. Backend
support extends the incumbent API-407 `ParticipantFeatureSupport` strength,
limitation, disclosure, and evidence pattern. It must not add opacity booleans
or infer support from a method, schema, solver, or nondeterministic behavior.
Missing required support fails closed; an authorized downgrade removes the
stronger claim and records limitations and disclosure.

Runtime occurrence records should acquire opacity coordinates only when they
record an opacity-related check or enforcement fact. In that case they should
carry the existing participant/audience/policy/cut/order coordinates plus safe
relation/profile and secret-predicate references, disposition, evidence,
limitations, and nonclaims. Ordinary crossings must not be bloated with raw
belief states or secret values. Backend manifests carry feature strength and
evidence refs, not copies of the opacity relation or predicate.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Relation authority | `contracts/concept-authority/behavioral-relations-v1.json`, `BehavioralRelationCatalogModel`, `BehavioralRelationDefinitionModel`, `RelationQuantificationModel`, `RelationDimensionsModel`, `RelationAssuranceModel`, `BehavioralClaimBindingModel`, `validate_behavioral_claim_binding()`, and `specs/formal/behavioral-relations/README.md`. Revise these together; add no opacity-local registry. |
| Claim policy | `tools/check_behavioral_relation_claims.py`, `test_behavioral_relations.py`, `test_behavioral_relation_claims.py`, catalog fixtures, claim-surface entries, and all current taxonomy-revision producers. Extend semantic validation instead of adding an opacity keyword ban. |
| Claim consumers | `ExperimentStudyModel`/`ExperimentSpecModel.behavioral_claims`, `CompletenessProfileModel`, behavioral-validation and necessity-validation bindings, `BackendConformanceReport`, participant-policy case bindings, evidence-run artifact production, scientific-completeness profiles, and public/lineage claim guidance. A shared binding change must preserve every consumer and every embedded published schema. |
| Participant semantics | ADR-022, `ParticipantViewRule`, `ParticipantViewTransition`, `ParticipantObservationBoundary`, compiled `ParticipantObservationBoundaryRuntime`, participant behavior histories, observation envelopes, and decision-surface v2 carriers. Reuse world/view/history and occurrence identity. |
| Information-flow semantics | ADR-085, ADR-095, SEM-230 revision 2, `Effective(rho,c)`, `MayCross`, exact-cut policy, dynamic purge, declassification schedules, adaptive strategies, and participant memory. Compose these; do not redefine noninterference. |
| Crossing contracts | `ParticipantCrossingOccurrenceModel` and its request, decision, transformation, disclosure, delivery-attempt, delivery, observation, and audit variants; `ParticipantCrossingPolicyReferenceModel`; `ParticipantCrossingDecisionGatesModel`; and `validate_participant_crossing_occurrence_context()`. Reference existing facts rather than copying payloads. |
| Runtime mediation | `ParticipantCrossingIntent`, `ParticipantCrossingEvidence`, `ParticipantCrossingPolicyResolver`, `ParticipantCrossingValidationContext`, crossing ingress/egress mixins, `RuntimeControlPlane`, `ParticipantControlMixin`, and participant retrieval. Any enforcement child enters the shared boundary, not route-only middleware. |
| Security and HTTP | `create_control_plane_app()`, `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneIdentity`, `ControlPlaneRole`, participant/audience subject bindings, request-size guards, `_request_fingerprint()`, idempotency keys, and the redacted unexpected-error envelope. Caller authorization never establishes opacity. |
| Persistence and audit | `RuntimeSnapshot`, `ControlPlaneStore`, shipped in-memory/local stores, expected-head atomic participant commits, append-only crossing/control/observation histories, and `AuditEvent`. Add no belief-state, opacity, witness, or gateway side store. |
| Backend support | `ParticipantFeatureSupportModel`, `ParticipantFeatureSupport`, `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`, `resolve_participant_feature_support()`, manifest round trips, supported-contract allowlists, and capability-gap diagnostics. Extend the existing strength pattern only when realization work exists. |
| Conformance and evidence | `ParticipantPolicyAssumptions`, `ParticipantPolicyBinding`, `ParticipantPolicyProbeHarness`, `run_fixture_suite()`, `run_target_conformance()`, `ConformanceCaseResult`, `BackendConformanceReport`, `validate_backend_conformance_report()`, `Diagnostic`, `Severity`, and `sanitized_failure_message()`. Generalize shared claim coordinates rather than copying the conformance-local wrapper. |
| Validation and errors | `ContractModel`/Pydantic model validators, `validate_behavioral_claim_binding()`, `ValidationError` at artifact ingress, `Diagnostic`/`DiagnosticModel` at processor/runtime/conformance boundaries, bounded operation responses, and sanitized unexpected failures. Add no opacity exception hierarchy or raw-value error formatter. |
| Observability planes | ADR-066 participant observation, operational telemetry, captured evidence, derived analysis, and authorized audit boundaries; experiment evidence, traceability, redaction/loss, and provenance contracts. Audit or evidence access is an observer surface when the profile says so. |
| Schema publication | `ContractModel(extra="forbid")`, `schema_bundle()`, `tools/generate_contract_schemas.py`, hand-governed `contracts/schemas/`, fixtures, `x-raes-invariants`, schema-publication entries, and generated/publication drift gates. Python-only or schema-only edits are not authority. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and the repo-policy, requirement-governance, ADR, concept-authority, claim, schema-publication, generated-schema, JSON-artifact, lineage, assurance, documentation, and full verification gates. No issue-local workflow or runner. |

The current package boundaries remain: `raes` for authored semantics,
`raes_processor` for compiled projections, `raes_contracts` for portable
contracts and relation authority, `raes_runtime` for live security/mediation
and persistence, `raes_backend_protocols` for backend declarations and
admission, and `raes_conformance` for bounded assessment.

## Cross-Cutting Layers And Security Posture

1. **Authority and SDL/config shape.** Issue #810 is design/program work and
   needs no SDL or runtime configuration field. A future authored opacity
   profile must enter through safe SDL loading where SDL-owned, closed models,
   `SemanticValidator`, instantiation, and post-instantiation validation.
   External policy/relation profiles should be bounded UTF-8 files or typed
   in-process objects with revision/digest validation, not expressions in YAML,
   environment variables, or metadata bags.
2. **Closed contract and schema gate.** Catalog, binding, profile, report, or
   runtime additions use `ContractModel(extra="forbid")`, generated schemas,
   semantic invariants, valid/invalid fixtures, publication-entry hashes, and
   compatibility classification. Cross-reference resolution belongs in one
   shared semantic validator, not repeated in Pydantic constructors, runtime
   services, conformance, and policy scripts. Because
   `BehavioralClaimBindingModel` is embedded in experiment-study and
   scientific-completeness contracts, changing it can regenerate multiple
   published schemas and fixtures; every affected publication entry and
   consumer must move together, not only `behavioral-relations-v1`.
3. **Concept and relation authority gate.** Relation identity and assurance
   live only in the behavioral catalog. Observer kinds, profile kinds, support
   strengths, and portable statuses use existing concept/controlled-vocabulary
   governance when cross-implementation comparison requires them. Do not add
   consumer-local aliases or advance only some `rev4` producers.
4. **Authentication and subject-binding gate.** Any future query, enforcement,
   witness, or report API reuses strict control-plane authentication, roles,
   target binding, participant/audience subject binding, request bounds,
   fingerprints/idempotency for mutations, and audit. It then separately
   applies participant authority, visibility, marking, release, and
   observer-profile policy. Operator or auditor authorization cannot grant
   participant visibility or establish an opacity property.
5. **Secret-handling gate.** Catalogs, profiles, bindings, crossings,
   diagnostics, reports, counterexamples, audit, logs, fixtures, examples, and
   issue evidence carry safe ids, refs, revisions, digests, classifications,
   bounded abstract values, limitations, and nonclaims. They exclude raw secret
   values, participant prompts or private memory, credentials, hidden policy
   bodies, hidden answer/world state, raw evidence, rejected payloads, backend
   object representations, and environment dumps.
6. **Observation and decision-channel gate.** Participant-facing content,
   status, failures, reason codes, response shapes, omissions, order, and
   latency all pass the selected observation projection. A generic safe reason
   code can still leak through branch choice or timing. Administrative
   retrieval, audit, and operational telemetry do not become participant
   observations accidentally, but they are included for an observer authorized
   to see them.
7. **Diagnostic and error-envelope gate.** Expected validation or policy
   failures use existing bounded `Diagnostic` codes and sanitized messages that
   identify safe relation/profile/field coordinates, not predicate truth,
   rejected values, possible worlds, or policy/controller inventories.
   Unexpected HTTP failures retain `{"detail":"internal server error"}`.
   Tracebacks remain internal and must not enter evidence or audit details.
8. **Persistence gate.** Runtime truth remains in typed `RuntimeSnapshot` and
   append-only `ControlPlaneStore` histories. A checker result or witness is a
   versioned evidence artifact or safe reference, not mutable snapshot
   `metadata`, operation `details`, an audit blob, a log line, or a new belief
   database. If an enforcement decision is durable, it uses the existing atomic
   participant commit and expected-head/idempotency discipline.
9. **Backend and conformance gate.** Feature declarations, required contracts,
   runtime enforcement facts, finite probe results, native execution,
   counterexamples, model checks, and proofs remain separate. A backend
   declaration or passing finite case cannot promote an opacity binding or
   silently change its evidence scope.
10. **Environment and OS/process exposure gate.** The design adds no
    environment binding, secret loader, subprocess, daemon, socket, or host
    service. Future tools pass safe paths, refs, profile ids, and digests only.
    Raw predicates, policies, models, witnesses, evidence, participant content,
    credentials, or tokens must not appear in process argv, environment
    variables, filenames, stdout/stderr, shell history, or host logs.
11. **Workflow and governance gate.** A relation/catalog change advances its
    taxonomy revision, formal reader view, catalog fixture, schema/publication
    record when shape changes, claim surfaces, current producers, tests, and
    documentation together. A requirement-backed child starts only after a
    DRAFT authority exists and uses the repository's normal Ground Control and
    verification workflow.

## Extensibility Seam

The stable seam is one shared behavioral claim binding that references one
closed, revisioned relation-parameter profile. The profile fixes:

- observer/coalition, audience, and initial information;
- secret predicate identity/revision and evaluation cut/horizon;
- possible-point carrier and retained memory;
- observation projection and decision/supervisor visibility;
- passive or active strategy domain;
- policy/release schedule;
- scheduler/environment, nondeterminism, time/order/concurrency/partial-order,
  and probability-support choices; and
- the independent assurance and evidence boundary being claimed.

Runtime, backend, conformance, study, and report carriers reference that profile
and the catalog relation; they do not copy its fields. This supports the next
reasonable change—coalition, symmetric, K-step, active, timed, partial-order, or
quantitative analysis—by adding a governed profile or relation rather than
editing every consumer. The seam is a typed reference, not an open parameter
map or executable predicate language.

## Gotchas And Anti-Patterns

Avoid:

- using "opaque" to mean redacted, unauthorized, hidden implementation,
  encrypted, unavailable, or hard to inspect;
- treating opacity, noninterference, projected-history equality, epistemic
  indistinguishability, trace equivalence, bisimulation, and access control as
  synonyms or as one implication ladder;
- defining one relation id for every DES variant, or one catch-all relation that
  absorbs noninterference and bisimulation;
- classifying the secret predicate, relation class, observer, participant,
  authenticated caller, controller, policy authority, backend, and auditor as
  one concept;
- assuming a hidden policy/supervisor revision is epistemically hidden while
  its decisions, latency, retries, or effects remain distinguishable;
- omitting failures, denial/approval occurrence, withholding, delivery status,
  reason-code branch, timing, order, or policy changes from the observation
  function;
- treating absence as an observation without an opportunity/progress/deadline
  model;
- comparing actual and witness runs under different active strategies without
  saying so, or calling finite scripted probes universal;
- treating a low-probability alternative as a posterior-risk bound, or added
  randomization/nondeterminism as proof;
- using one scheduler linearization as a partial-order witness;
- treating declassification as knowledge-preserving, or concealment/revocation
  as erasing prior knowledge;
- overloading `subject`, `evidence_boundary`, `limitations`, metadata, details,
  or free-form strings with observer/secret/profile meaning;
- calling the relation-parameter profile a semantic, backend, validation,
  instantiation, or support profile, or putting it in those registries;
- copying `ParticipantPolicyBinding` into an opacity-local binding or adding a
  second relation catalog, assurance vocabulary, report, fixture runner,
  policy engine, exception hierarchy, logger, audit channel, persistence store,
  or workflow;
- putting raw secret values, belief states, possible worlds, policy bodies,
  payloads, prompts, credentials, rejected inputs, evidence, backend objects,
  environment/process data, or tracebacks in portable artifacts or diagnostics;
- treating a catalog/schema/profile entry, checker implementation, runtime
  record, backend declaration, finite probe, model check, or proof as evidence
  for any other assurance axis;
- hand-editing generated schemas, advancing only some taxonomy consumers, or
  changing accepted ADR content without ADR-059 records; and
- opening requirement-backed implementation children before the required DRAFT
  Ground Control authority exists.

## Non-Goals And Implementation Boundaries

- No opacity relation, catalog revision, ADR, SEM-230 amendment, formal proof,
  model check, checker, monitor, synthesis algorithm, or nondeterministic
  supervisor is delivered by this preflight.
- No SDL syntax, executable predicate language, policy engine, participant
  gateway, transport, endpoint, UI, credential broker, provider integration,
  subprocess, daemon, scheduler, or OS sandbox is added.
- No new world state, participant view/history, observation boundary,
  lifecycle, crossing/control carrier family, evidence plane, relation
  registry, validation stack, exception hierarchy, logger, audit stream,
  persistence store, conformance runner, or backend profile family is created.
- No participant internals, prompts, chain-of-thought, private memory,
  credentials, hidden policy bodies, raw secret payloads, hidden answer/world
  state, raw evidence, or backend-private objects become portable data.
- No claim is made that current RAES behavior is opaque, that RUN-319 enforces
  opacity, that a backend realizes opacity, or that existing bounded
  noninterference cases establish opacity.
- No replacement or weakening of policy noninterference, projected-history
  equality, epistemic indistinguishability, trace relations, simulation,
  refinement, or bisimulation is authorized.
