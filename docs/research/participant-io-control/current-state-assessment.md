# Participant Information-Flow And Control Current-State Assessment

Date: 2026-07-15
Issue: [#794](https://github.com/Brad-Edwards/aces/issues/794)
Milestone: `Participant Information-Flow & Behavioral Equivalence`

This assessment distinguishes normative definition, implementation, test,
proof/model-check evidence, and runtime realization. A closed issue, accepted
ADR, ACTIVE requirement, published schema, passing fixture, and realized
backend are different facts. The machine-readable companion is
[`adoption-program.json`](adoption-program.json).

## Conclusion

ACES has adjacent participant-control mechanisms, not one portable participant
ingress/egress semantic boundary or enforcement point.

The repository already defines participant-relative world/view/history,
actions, observations, visibility changes, admission, lifecycle, ordering,
markings, redaction fields, behavior histories, neutral carriers, retrieval
views, capability declarations, bounded conformance, and relation-claim
discipline. It does not yet define one revisioned policy decision spanning
ingress and egress, a governed declassification authority, participant-directed
inject delivery, ordered controller transitions, transformation identity, or a
portable crossing evidence record. It also has no governed noninterference
relation, evaluator, model check, proof, or universal runtime claim.

The correct adoption is one policy/evidence relation over existing carriers,
not one generic message, transport, gateway, lifecycle, view, history, store,
or logger.

## Live requirement status

The following statuses were read from Ground Control on the assessment date.
Traceability counts refer to live `IMPLEMENTS` and `TESTS` links, not prose
claims.

| Requirement | GC status | Delivery evidence | Assessment |
| --- | --- | --- | --- |
| SEM-208 | ACTIVE | implementation and tests | Action/observation/state/history semantics are implemented and tested; complete policy enforcement and proof are not. |
| SEM-209 | ACTIVE | implementation and tests | Interaction and joint-action semantics exist; mixed-control and IFC scheduler obligations do not. |
| SEM-210 | ACTIVE | implementation and tests | `V_p,o`, observation boundaries, ordered visibility transitions, and leakage cases exist; payload-level IFC/declassification is partial. |
| SEM-211 | ACTIVE | implementation and tests | Typed applicability/effects/failures and admission exist; external controller decisions are not modeled. |
| SEM-212 | ACTIVE | implementation and tests | Attribution strengths exist; counterfactual proof is not implied. |
| SEM-213 | ACTIVE | implementation and tests | Participant temporal contracts exist; timed/partial-order equivalence is unproved. |
| SEM-219 | DRAFT | documentation only | ADR-083 design exists; issue #294 has not delivered authored/runtime bindings. |
| SEM-220 | DRAFT | documentation only | ADR-083 design exists; issue #295 has not delivered a decision surface. |
| SEM-226 | DRAFT | documentation only | ADR-083 design exists; issue #296 has not delivered exposure enforcement. |
| ACT-617 | DRAFT | documentation only | Mixed control is required but controller state and transitions are undefined in executable artifacts. |
| RUN-305 | DRAFT | tests plus a bounded implementation described by ADR-054 | State/history append-only checks exist, but live GC traceability is incomplete and the full runtime envelope is partial. |
| RUN-306 | ACTIVE | implementation and tests | Observable lifecycle carriers exist; supervision/handoff remains RUN-310. |
| RUN-307 | ACTIVE | implementation and tests | Shared-state contracts and persistence exist; participant disclosure remains a separate policy decision. |
| RUN-308 | ACTIVE | implementation and tests | Concurrency/order/time-management carriers exist; universal ordering/equivalence claims do not. |
| RUN-310 | DRAFT | documentation only | Supervisory lifecycle is not implemented. |
| API-406 | ACTIVE | contracts, conformance, tests | Neutral carriers are published; schema presence is not producer or backend realization. |
| API-407 | ACTIVE | manifest feature-support implementation | The incumbent feature-support seam exists; participant-control terms are not declared yet. |
| API-409 | DRAFT | documentation only | External input/intervention contracts are not published. |
| DSL-111 | ACTIVE | SDL/compiler implementation and tests | Orchestration inject/timeline identity exists; participant addressee/delivery semantics do not. |
| ASR-519 | ACTIVE | bounded conformance implementation | Realization honesty is enforced generally; it does not supply participant IFC assurance. |
| ASR-527 | ACTIVE | participant implementation/exposure conformance | Apparatus/exposure claims have an assurance seam; the new policy path is absent. |

Issue #794 created the uncovered DRAFT authorities only after this disposition
was established: SEM-230, DSL-142, API-423, RUN-319, and ASR-535. Their
statements and scopes are recorded in
[`requirement-disposition.md`](requirement-disposition.md). DRAFT means
authorized work remains to be implemented; it is not completion.

## Existing thread disposition

### Participant semantics: #71, SEM-208 through SEM-213, ADR-022

[ADR-022](../../decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md)
is accepted. It distinguishes world truth, participant-visible state, local
history, and archival evidence; makes actions semantic contracts; models
interaction; and makes information boundaries first-class. The formal
`specs/formal/participant-semantics/README.md` specification defines `W_t`,
`V_p,t`, `H_p,t`, observations, actions, joint actions, invariants, and
section-per-UID implementation mappings.

Implementation exists in:

- `implementations/python/packages/aces_sdl/participant_behavior.py` and
  `participant_action_semantics.py`;
- `implementations/python/packages/aces_sdl/semantics/participant_behavior.py`;
- `implementations/python/packages/aces_processor/compiler/` and
  `aces_processor/models/`;
- `implementations/python/packages/aces_contracts/contracts.py`; and
- `implementations/python/packages/aces_conformance/conformance.py`.

Tests include `test_sem_208_participant_behavior.py`,
`test_sem_211_participant_action_semantics.py`,
`test_sem_212_participant_attribution_semantics.py`,
`test_sem_213_temporal_participant_semantics.py`, and
`test_participant_semantics_invariant_oracle.py`.

These artifacts establish typed and tested semantic slices. They do not define
a revisioned IFC policy, purge/low-equivalence relation, declassification
authority, common crossing decision, or universal proof. The formal spec's
opening sufficiency text predates later implementations and must not be used as
the sole current status source; its per-UID implementation sections and live
traceability are the more precise evidence.

Disposition: reuse ADR-022 and SEM-208 through SEM-213. Compose them under
SEM-230; do not replace or silently amend their accepted meaning.

### Participant runtime: #74, RUN-305 through RUN-308, ADR-054

[ADR-054](../../decisions/adrs/adr-054-participant-runtime-observable-lifecycle.md)
is accepted. It defines observable proposal/admission/attempt/observation/state
points, closed realization/disposition vocabularies, identity/provenance/
marking envelopes, participant information guarantees, ordering, shared state,
and concurrency. The formal design in
`specs/formal/participant-runtime/README.md` separates episode, behavior,
operation, observation, shared-state, and interaction records.

Reusable implementation includes
`ParticipantActionAdmissionRequest` and
`participant_action_admission_request_violations()` in
`aces_contracts/participant_binding.py`, `ParticipantControlMixin` in
`aces_runtime/participant_control.py`, `RuntimeSnapshot` in
`aces_contracts/runtime_state.py`, and `ControlPlaneStore` in
`aces_runtime/control_plane_store.py`.

RUN-306 through RUN-308 have implementation/test traceability. RUN-305 has a
bounded append-only state/history implementation and test but remains DRAFT in
Ground Control and has incomplete implementation traceability. Even the
delivered runtime slices do not create one ingress/egress policy path or prove
backend realization.

Disposition: reuse lifecycle, envelope, order, state, persistence, and history
incumbents. RUN-319 adds enforcement/evidence obligations; it does not add
another lifecycle or store.

### Affordances, decision surfaces, and exposure: #119 and #294-#296

[ADR-083](../../decisions/adrs/adr-083-participant-tool-decision-surface-and-exposure-semantics.md)
is proposed and issue #119 is closed. It correctly separates action meaning,
authored availability, apparatus support, run selection, current decision
surface, realized exposure, and decision/outcome. It refines the existing
participant view rather than inventing a second visibility system.

Ground Control has only documentation links for SEM-219, SEM-220, and SEM-226;
issues [#294](https://github.com/Brad-Edwards/aces/issues/294),
[#295](https://github.com/Brad-Edwards/aces/issues/295), and
[#296](https://github.com/Brad-Edwards/aces/issues/296) remain open. Therefore
the ADR and formal matrix establish design, not runtime mediation or delivered
exposure.

Disposition: retain and strengthen the three issues under this program. SEM-226
composes with SEM-230 but keeps its existing `V_p,o` authority.

### Behavioral relations: #747, ADR-081, and revision 1

[ADR-081](../../decisions/adrs/adr-081-behavioral-relation-taxonomy-and-claim-discipline.md)
is accepted. The normative `specs/formal/behavioral-relations/README.md`
specification and `contracts/concept-authority/behavioral-relations-v1.json`
define structural and semantic validity, capability declarations, bounded probes, trace
inclusion/equivalence, simulations, refinement, strong/weak bisimulation,
projected-history equality, epistemic and strategic relations, and empirical
relations. `BehavioralClaimBindingModel`, policy checks, counterexamples, and
property tests are implemented.

Revision 1 deliberately does not prove universal trace inclusion, equivalence,
simulation, refinement, bisimulation, epistemic, strategic, probabilistic,
timed, or partial-order relations. It has no governed noninterference relation.
`participant-projected-history-equivalence` compares two bounded histories
under the same participant and policy projection; it is not information-flow
noninterference.

Disposition: reuse the catalog and binding discipline. SEM-230/ASR-535 may add
or bind a governed policy-noninterference relation through the catalog's normal
revision process; no local IFC synonym or proof shortcut is permitted.

### Mixed control: ACT-617, API-409, RUN-310, #251, #252, and #255

The three requirements and issues are DRAFT/open. Existing behavior modes,
admission dispositions, actor provenance, lifecycle events, and histories are
adjacent primitives. They do not distinguish controller state, proposal,
approval, direction, intervention, handoff, override, cancellation, execution,
and observation.

Disposition: amend and implement the existing requirements rather than replace
them. #251 owns authored/controller semantics, #252 owns portable contracts,
and #255 owns runtime lifecycle. All three now have bounded scope and ordered
dependencies in milestone 67.

### Backend-facing carriers and capabilities: API-406/API-407

[ADR-060](../../decisions/adrs/adr-060-participant-backend-facing-contract-surface.md)
is proposed. `ParticipantRuntimeBaseEnvelopeModel`,
`ParticipantObservationEnvelopeModel`, runtime snapshot/history carriers,
`ParticipantFeatureSupportModel`, `ParticipantRuntimeCapabilitiesModel`, and
`BackendManifestV2Model` are published from
`aces_contracts/contracts.py`. `participant_runtime_capability_contract_gaps()`
and `BackendConformanceReport` provide the canonical capability/conformance
seams.

API-406 is ACTIVE with implementation/test evidence. API-407 is ACTIVE and
already owns governed feature support, constraints, disclosure, and strength.
Neither currently records the common policy decision for an ingress/egress
crossing or the new participant-control features.

Disposition: API-423 composes typed crossing/evidence refs with existing
carriers. API-407 is amended through #801; no backend-specific DTO family or
capability booleans are added.

### Orchestration injects: DSL-111

`aces_sdl/orchestration.py` defines `Inject`; scenario, composition, validation,
planning, compilation, published schemas, and tests preserve inject/event/
script/story identity and schedule. These are orchestration resources. They do
not bind a participant addressee, observation boundary, authorization,
declassification, delivery receipt, or participant behavior history.

Disposition: reuse DSL-111 unchanged. DSL-142 adds the missing participant-
directed binding/delivery semantics. Environment injects remain orchestration
events and become participant-visible only through normal projection.

### Scientific completeness finding

`contracts/profiles/scientific-completeness/delivery-assessment-2026-07-12.json`
marks `participant-action-observation` partial because action contracts and
observation boundaries exist but participant-relative information-flow
admission is incomplete. It marks the behavioral-relation taxonomy implemented
while explicitly retaining universal relation nonclaims.

Disposition: preserve this as a delivery assessment, not authority or proof.
Update it only after shipped evidence from the child issues changes the status.

## Cross-cutting implementation inventory

| Concern | Canonical incumbent | Gap for adoption |
| --- | --- | --- |
| Authored input | `load_sdl_yaml()`, `SDLModel(extra="forbid")`, `SemanticValidator`, instantiation/revalidation | New governed refs and inject bindings only after authority exists. |
| Admission | `ParticipantActionAdmissionRequest`, SEM-211, `ParticipantControlMixin` | No common policy revision/decision/evidence across all ingress kinds. |
| Projection | observation boundaries, `V_p,o`, `participant_retrieval._project_scope()` | API-408 projection is not participant-safe enforcement by itself. |
| Security | `ControlPlaneSecurityConfig.strict_defaults()`, identity/role/target binding, request size, idempotency/fingerprint | Authenticated operator authority is not participant subject/visibility authority. |
| Error handling | `Diagnostic`, bounded 4xx details, redacted `{"detail":"internal server error"}` | New decisions must not echo hidden policy or payload content. |
| Persistence/audit | `RuntimeSnapshot`, `ControlPlaneStore`, `AuditEvent`, behavior/observation/evidence histories | No append-only crossing-decision/realization relation yet. |
| Contracts | `ContractModel`, ADR-054 envelopes, API-406/API-409 refs | No shared policy/transformation/disposition/evidence record. |
| Backend support | API-405/407 manifests and capability-gap diagnostics | Missing participant-control feature identifiers and evidence criteria. |
| Conformance | `BackendConformanceReport`, fixture/target runners, relation bindings | Missing adversarial IFC/declassification/weakening cases. |
| Governance | schema bundle/publication manifest, concept authority, ADR-061, Ground Control | New requirements/issues must precede implementation and preserve claim status. |

No new logger, exception hierarchy, environment binding, secret loader,
subprocess, gateway store, or authentication stack is needed.

## Gap and overlap analysis

Already adequate and reused unchanged:

- world/view/history/evidence separation;
- typed action, observation, lifecycle, shared-state, ordering, and provenance
  incumbents;
- API-407 feature-support pattern;
- behavioral-relation catalog and claim bindings;
- control-plane security, persistence, audit, and redacted errors; and
- schema/concept/compatibility governance.

Authorities that require composition or amendment:

- SEM-226 exposure with SEM-230 policy operations;
- ACT-617/API-409/RUN-310 for explicit mixed-control transitions;
- API-407 for participant-control features; and
- the relation catalog if `policy-noninterference` becomes a governed relation.

Missing authorities supplied by this program:

- SEM-230 policy semantics;
- DSL-142 participant-directed inject delivery;
- API-423 crossing policy/evidence contracts;
- RUN-319 enforcement/persistence; and
- ASR-535 falsification and formal-assurance progression.

Terminology that must not collapse:

- action mask, decision-surface membership, eligibility, admission, execution,
  and outcome;
- visibility, authorization, disclosure, declassification, redaction,
  withholding, concealment, revocation, loss, and unsupported behavior;
- environment inject, participant disclosure, external direction, and
  intervention;
- projected-history equality, trace inclusion, simulation, refinement,
  noninterference, and bisimulation; and
- definition, implementation, test, proof/model check, and runtime realization.

## Assessment nonclaims

This artifact does not implement the program, accept ADR-084, transition any
new requirement ACTIVE, prove any behavioral or information-flow relation,
select a gateway, or certify a backend. It records the evidence and gaps from
which the adoption decision and implementation program follow.
