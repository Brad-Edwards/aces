# Issue #1001 — SEM-233 Boundary-Flow Semantics Architecture Preflight

Date: 2026-08-01

Issue: #1001.

Primary requirement: `SEM-233`.

Reused requirements: `SEM-230`, `ACT-617`, `API-409`, and `API-423`.

This note records architecture guardrails for publishing the first revisioned
SEM-233 semantic authority. It is guidance only. It does not publish the
profile, label algebra, carrier contract, schema, runtime resolver, final-sink
enforcement, backend capability, conformance result, or behavioral claim.

## Decisive Current-State Finding

Issue #1001 must sharpen the semantic authority already selected by ADR-101;
it must not start a second information-flow subsystem.

- The requirement payload supplied to preflight is active `API-423`, an
  already delivered crossing-contract dependency, while issue #1001 is the
  first delivery for DRAFT `SEM-233`. Preserve API-423's existing contract,
  schema, validation, migration, and traceability ownership; do not use it as
  the ownership UID for #1001. Because branch
  `1001-boundary-flow-semantics` contains no requirement UID, repository
  workflow commands use `RAES_REQUIREMENT_UID=SEM-233`.
- ADR-101 already fixes independent confidentiality and integrity, conservative
  derivation, distinct authority operations, typed carriage, and the last
  RAES-controlled sink. No new ADR is justified unless implementation discovers
  a conflict with that accepted decision.
- `specs/formal/participant-semantics/adversarial-flow-control.md` is the
  focused design authority, but its current phrases “least upper bound” and
  “conservative influence union” do not yet define an exact carrier, order,
  join, source default, or scoped release transition. That is the design gap
  #1001 closes.
- API-423 already owns crossing stages, exact policy/cut references,
  transformation identity, marking preservation, declassification basis, and
  cross-record validation. Runtime facts already own typed sources, scope,
  sensitivity, freshness, provenance, and action-input sinks. Neither is the
  complete SEM-233 two-coordinate label algebra.
- The behavioral catalog already owns `policy-noninterference` and the
  `participant-information-flow-policy` claim surface. SEM-233 parameterizes
  that existing relation; it does not justify an
  `adversarial-noninterference`, `flow-safe`, or similarly overlapping relation.
- Portable flow-policy and carrier DTOs are owned by #1002. Final-sink runtime
  enforcement and persistence changes are owned by #1003. Issue #1001 may use
  a test-local finite model as bounded falsification evidence, but it must not
  add production contracts or runtime code in anticipation of those issues.

The smallest coherent delivery is therefore one exact `sem-233/rev1` formal
profile, a typed mapping to incumbent carrier identities, a narrowly evolved
behavioral claim surface, lineage/assurance bookkeeping, and bounded synthetic
counterexamples. ADR-101, SEM-230, and the existing runtime boundaries remain
the owners of their current concepts.

## Architecture Decisions And Guardrails

### Publish an exact formal profile without publishing a wire contract

The focused SEM-233 specification is the authority for
`participant-boundary-flow-policy-v1@rev1`. It must name its authority revision
separately from the profile revision and distinguish these statuses:

- the formal definition is published;
- portable contract and schema support are not implemented;
- runtime and backend enforcement are not implemented;
- finite counterexamples are bounded tests, not a model check or proof; and
- `SEM-233` remains DRAFT while its downstream positive obligations remain
  open.

The profile is not a GOV-920 `SemanticProfileModel`: that incumbent describes
phase-wise contract, concept-family, binding, and behavior compatibility. It is
also not a `BehavioralRelationProfileModel`: that incumbent closes the
parameters of a behavioral claim or analysis. A future claim profile may
reference the SEM-233 flow-policy profile, but claim configuration must not
become the operative flow policy. Issue #1001 must not add either portable
profile variant; #1002 owns that contract decision.

### Require one exact two-coordinate algebra

The formal profile must select one exact, non-scalar revision-1 algebra. This
preflight deliberately does not choose its carrier representation. The
normative definition must close, for each independent coordinate:

- the carrier domain and equality/normalization rule;
- the partial-order direction and the meaning of incomparable values;
- the join and every extremal or explicitly absent extremal value;
- unknown-source, missing-label, conflict, and unsupported behavior;
- the sink-satisfaction predicate; and
- the authority-bounded operation that may change that coordinate on a fresh
  result.

The definition must state and exercise the algebraic laws required for stable
composition: closure, associativity, commutativity, idempotence, monotonicity,
and traversal-order independence. It must make mechanically clear that adding
a confidentiality restriction or possible integrity influence cannot widen a
release. An unresolved source, label, authority, profile revision, or join
must yield the profile's deny-equivalent result or a typed unsupported result;
it never becomes empty, public, or trusted by default.

Authentication, signatures, hashes, sensitivity, markings, confidence, and
monitor scores may be evidence used by a resolver; none is either coordinate
by itself. The integrity value coordinate records conservative possible
influence, while a sink requirement is a predicate over that value; those are
not two meanings to collapse into one trust score. The chosen revision-1
domain must preserve mutually distrustful and incomparable principals or
audiences rather than assuming one global classification ladder.

### Keep provenance, label state, and authority transitions separate

For a derivation `d`, the conservative default is:

```text
L_phi(d) = join_phi { L_phi(x) | x may influence d }
```

The possible-input set includes participant context and retained memory plus
the participant, tool, service, transformation, monitor, or apparatus source
when that source can influence the result. Copying, summarizing, redacting,
prompting, parsing, editing, or changing participant/controller does not remove
an input. A typed transformation may exclude an influence only through a
closed, revisioned non-influence relation with evidence; absence from a
caller-supplied list is not proof.

Provenance remains an immutable graph of source and derivation refs. It is
evidence for label resolution and replay, not authorization. Labels are the
policy obligations derived from that graph at a named profile/cut. Do not put
the graph inside the label or treat possession of provenance as permission.

Declassification and integrity endorsement are coordinate-specific rewrites:

- declassification may remove or replace only named confidentiality
  obligations;
- endorsement may replace only named integrity obligations while retaining
  their immutable influence refs; it changes the sink-admission predicate, not
  the recorded possible-writer history;
- each operation binds source and fresh result identities, unchanged
  coordinate, exact obligation delta, destination/sink, authority basis,
  profile/revision, decision/cut, predecessors, and safe evidence; and
- neither mutates the source label or provenance history.

Redaction and ordinary transformation retain both coordinates unless their
governed relation says otherwise. Approval, authentication, authorization,
admission, handoff, and trusted editing imply neither rewrite. Trusted editing
creates a new result and re-enters ordinary validation and policy gates.

### Reuse the exact-cut crossing decision instead of adding a policy engine

Use a final predicate named distinctly from declassification, for example:

```text
MayFlowAtSink_phi(x, sink, destination, cut) =
  ConfidentialityObligationsSatisfied(...)
  and IntegrityObligationsSatisfied(...)
  and existing caller/target/participant authority gates
  and existing action admission
  and existing API-407 effective capability gate
  and existing API-423 transformation/projection gates
  and FreshExpectedHistoryHeads(cut)
```

Every conjunct is deny-first. “Release” must not ambiguously mean both the
declassification operation and this final composite decision. The SEM-230
participant/audience projection and API-423 `MayCross` relation remain
incumbents; SEM-233 adds the two obligation checks at the same exact cut.

Policy changes never reinterpret a historical decision. Source labels,
derivations, declassification/endorsement operations, and decisions retain
their original profile, policy, and cut refs. Reuse under a later policy or
episode requires a fresh sink decision. Episode reset, handoff, controller
change, participant change, replay, or snapshot reload never clears labels or
provenance.

### Map semantics to incumbent carriers by reference

Issue #1001 must publish a complete carrier/derivation table but must not edit
these contracts. The mapping is semantic and reference-based:

| Flow stage | Canonical incumbent | SEM-233 mapping boundary |
| --- | --- | --- |
| observations, tool results, retrieved values, derived facts | `ParticipantObservationEnvelopeModel`; runtime-fact declaration/version models and `RuntimeFactBindingPlane` | source and derivation refs resolve to an effective label; `RuntimeFactSensitivity` is only one input to that resolution |
| participant context, information state, and memory | participant context/history/information-state/episode carriers and SEM-230 memory scope | every retained or replayed value preserves source, label-profile, derivation, and release-history refs |
| proposals and action arguments | participant decision surfaces, `ParticipantActionAdmissionRequest`, action argument definitions, and runtime-fact sinks | structural/action admission composes with label resolution; it does not duplicate it or imply flow permission |
| control and handoff | API-409 `ParticipantControlOccurrenceModel` and contextual validator | controller/authority changes remain separate from declassification, endorsement, and action admission |
| crossing, transformation, and disclosure | API-423 `ParticipantCrossingOccurrenceModel`, typed subjects, predecessor stages, and contextual validator | later contracts reference label/derivation decisions; they do not copy source payloads or invent a second crossing history |
| output, delivery, observation, and errors | API-423 disclosure/delivery/observation stages and participant-facing views | every participant/external serialization is a sink; disclosure, delivery, and observation remain distinct |
| persistence and replay | `RuntimeSnapshot`, participant histories, operation/idempotency records, and expected heads | downstream enforcement uses the existing atomic transition; #1001 makes no persistence change |

The mapping must include cross-participant handoff, shared/joint state, and
cross-episode replay examples. It must name which values can influence each
derived carrier, including error branches and destination/tool arguments. An
open `taint`, `security_labels`, `context`, `metadata`, or backend-options bag
is not a typed mapping.

### Evolve the existing claim authority without strengthening assurance

`policy-noninterference` remains the relation. The SEM-233 profile supplies a
revisioned classification/flow-policy parameter to SEM-230 low equivalence,
dynamic purge, declassification schedule, projection, and adaptive-strategy
quantification. It does not replace those definitions or make a separate
behavioral relation.

If #1001 changes the current catalog, it must evolve it once from current
`rev11`:

- preserve byte-for-byte `rev11` under
  `contracts/concept-authority/history/` before advancing the current file;
- register `rev11` in `_HISTORICAL_CATALOG_PATHS` so stored bindings remain
  resolvable;
- update the existing `participant-information-flow-policy` claim surface
  rather than creating an overlapping surface;
- keep the catalog schema at `behavioral-relations/v1` when its closed shape is
  unchanged; and
- move every current revision literal, fixture, claim producer, publication
  entry/hash, and catalog test together.

The catalog must not report SEM-233 runtime enforcement, backend declaration,
realization, conformance, model checking, or proof. Existing SEM-230 evidence
does not implement the stronger SEM-233 label propagation. A #1001 finite model
is test-local bounded falsification evidence and must bind finite scope and
explicit nonclaims; a successful enumeration is not universal
noninterference, intentional-subversion robustness, or backend behavior.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| participant-relative policy and relation | ADR-085/095 and `information-flow-control.md`: reuse exact cuts, projection, hiding, memory, adaptive strategies, dynamic purge, declassification, order, and `policy-noninterference` |
| SEM-233 design decision | ADR-101 and the existing adversarial-control research record; amend the focused formal spec, not the accepted ADR, unless a real decision conflict appears |
| action and admission | SEM-211, participant decision surfaces, `ParticipantActionAdmissionRequest`, action argument definitions, and incumbent admission validators |
| runtime facts and sinks | runtime-fact declaration/version/sink/binding models, `RuntimeFactBindingPlane`, `validate_binding()`, dispatch, secret references, freshness, and projection redaction |
| control and handoff | ACT-617, API-409 participant-control occurrence models, contextual validation, controller/authority binding, and control history |
| crossings | API-423 models/vocabulary/context validator, `ParticipantCrossingIntent`, `ParticipantCrossingPolicyResolver`, exact policy refs, fresh transformation identity, and crossing history |
| capability | API-407 manifests/profiles, required-contract maps, and `resolve_participant_feature_support()`; semantic definition is not a capability declaration |
| persistence | `RuntimeSnapshot`, `ControlPlaneStore.commit_participant_transition()`, `LocalControlPlaneStore`, operation records, semantic fingerprints, idempotency, expected heads, and `AuditEvent` |
| claims | `behavioral-relations-v1.json`, historical catalogs, `BehavioralRelationCatalogModel`, `BehavioralClaimBindingModel`, `validate_behavioral_claim_binding()`, and `check_behavioral_relation_claims.py` |
| validation and diagnostics | `ContractModel(extra="forbid")`, contextual validators, `Diagnostic`, `Severity`, operation envelopes, sanitized failures, and the generic redacted HTTP 500 response |
| formal assurance | ADR-007/018, FM3 participant-semantics fulfillment, the SEM-230 test-local model pattern, and bounded counterexample/nonclaim discipline |
| lineage and workflow | SDL lineage ledger/model/checker, source audit, `.ground-control.yaml`, `.gc/plan-rules.md`, canonical nox/policy/verification commands, and requirement traceability |

No new relation registry, semantic-profile family, policy engine, source or
sink registry, action/crossing hierarchy, validator stack, exception hierarchy,
logger, audit stream, store, workflow script, or issue-local schema authority
is justified.

## Cross-Cutting Layers And Security Posture

Issue #1001 is definition-only, so it traverses repository authority and
claim-validation layers, not live transport or execution. That distinction is
part of the assurance boundary.

1. **Formal authority and revision gate.** The focused spec names
   `sem-233/rev1`, the flow-profile id/revision, all algebraic domains and
   laws, exact-cut semantics, carrier mappings, limitations, and nonclaims.
   ADR-101 remains the decision owner and SEM-230 remains the relation owner.
2. **Concept/catalog shape gate.** Any behavioral catalog change validates
   through the closed `BehavioralRelationCatalogModel`, exact revision loader,
   publication fixture/entry, JSON artifact checks, concept-authority checks,
   and historical-revision tests. Free-form prose cannot substitute for a
   governed claim surface.
3. **Claim-strength gate.** `validate_behavioral_claim_binding()` and
   `tools/check_behavioral_relation_claims.py` continue to require exact
   taxonomy/relation/projection/evidence boundaries. Definition and bounded
   examples cannot advance implementation, runtime, backend, model-check, or
   proof axes.
4. **Formal-assurance gate.** Participant semantics remains FM3. The invariant
   list, test-local bounded model, unit/property counterexamples, abstract
   transition semantics, and existing typed-contract waiver remain honest.
   Issue #1001 must not claim that prose or a test dataclass closes #1002's
   typed-contract obligation.
5. **Lineage and governance gate.** New normative derivations update the
   existing lineage authority and source audit; explanatory repetition does
   not. Repository policy, requirement governance, assurance, concept,
   lineage, JSON, documentation, and full verification stay in the canonical
   workflow. `SEM-233`, not the supplied API-423 payload, is the workflow UID.
6. **Secret-handling gate.** Formal examples and tests use synthetic bounded
   values and safe refs only. No raw confidential value, prompt, credential,
   private state, hidden objective, policy body, rejected input, or secret-
   derived digest enters docs, fixtures, diagnostics, or test output. Hashing a
   secret does not make it safe evidence.
7. **Config and environment gate.** The semantic delivery adds no runtime
   configuration, environment variable, secret loader, feature flag, CLI
   option, endpoint, or caller-selectable profile root. The only environment
   binding is the existing workflow UID. Policy/profile content never comes
   from environment or open metadata.
8. **OS/process exposure gate.** The bounded semantic model is in-process and
   deterministic. It adds no network access, subprocess, socket, daemon,
   sidecar, host path, temporary secret file, or privileged operation. Labels,
   values, policies, and witnesses do not enter argv, environment, filenames,
   stdout/stderr, or host logs.
9. **Exception, logging, and error-envelope gate.** Test-local invalid cases use
   assertions or incumbent validation failures. Do not add a SEM-233 exception
   hierarchy or logger. Because #1001 exposes no API, it does not traverse HTTP
   envelopes; consequently it makes no error-redaction claim. #1003 must reuse
   stable `Diagnostic` codes, safe `AuditEvent` fields, operation envelopes,
   and `{\"detail\":\"internal server error\"}` for unexpected HTTP failures.
10. **Auth, final-sink, and persistence boundary.** #1001 does not traverse
    `ControlPlaneSecurityConfig.strict_defaults()`, bearer/proxy identity,
    target/role/participant/controller/audience binding, request-size guards,
    `RuntimeControlPlane`, `RuntimeTarget`, capability admission, atomic commit,
    or replay. The formal predicate must name every one as a conjunct or
    downstream realization obligation, but must not claim it has passed them.

## Whole-Repository Surfaces In Scope

- **Normative semantics:** ADR-101, SEM-230, the focused SEM-233 formal spec,
  participant-semantics README, formal-assurance fulfillment, and any clause
  mapping derived from them.
- **Concept and claims:** current and historical behavioral catalogs, the
  `participant-information-flow-policy` claim surface, catalog loader and
  validators, claim bindings, publication metadata, and claim-policy tests.
- **Lineage:** the existing SDL lineage explanation, machine-readable lineage
  ledger, primary-source audit, and their checkers. The currently edited
  lineage/research files remain independent working-tree content and must not
  be overwritten by the #1001 implementation.
- **Bounded evidence:** one test-local SEM-233 model and focused algebra,
  missing-label, laundering, stale-cut, cross-participant, cross-episode, and
  release-operation-conflation counterexamples. Production packages are out of
  scope.
- **Incumbent carrier inventory:** action/admission, observation, context,
  memory, runtime-fact, control/handoff, crossing, transformation, delivery,
  snapshot/history, capability, diagnostics, audit, and operation surfaces are
  mapped but unchanged.
- **Verification:** policy, requirement governance, concept authority,
  behavioral claims, lineage, assurance policy, JSON/schema publication when
  applicable, focused tests, docs, and `tools/verify_all.py`.

## Extensibility Seam

The semantic seam is the tuple:

```text
(profile_ref,
 profile_revision,
 source_label_resolver_ref,
 derivation_rule_ref,
 sink_policy_ref,
 authority_resolver_ref,
 participant,
 audience,
 direction,
 interaction_kind,
 destination,
 sink_class,
 exact_cut)
```

The profile owns the confidentiality/integrity obligation domains, order,
join, unknown defaults, release/endorsement rewrite rules, and sink predicates.
Resolvers bind existing carrier/source identities to that profile. Existing
carriers later reference label, derivation, and decision identities rather than
embedding full policies or acquiring apparatus-specific branches.

This seam permits the next source kind, sink class, owner policy, participant,
apparatus, backend, or episode scope to add a revisioned resolver/profile rule
without editing every carrier. A third independent policy dimension would be a
new profile revision and algebraic decision, not an overloaded integrity or
confidentiality field. Timed, probabilistic, quantitative leakage, covert-flow,
or stronger behavioral properties require their own governed relation/profile
decision; configuration cannot disguise a changed theorem.

## Gotchas And Anti-Patterns

Avoid:

- implementing #1001 under `API-423`, changing API-423's active contract
  authority, or treating its supplied traceability list as SEM-233 completion;
- publishing `sem-233/rev1` while leaving the actual order, join, equality,
  unknown element, or release rewrite implicit;
- a single ordered security level, `trusted` flag, sensitivity, marking,
  confidence, signature, checksum, role, or monitor score standing in for both
  coordinates;
- treating source authenticity, content integrity, provenance availability,
  action authorization, confidentiality, and admitted origin trust as the same
  concept;
- letting empty labels, absent provenance, an unknown source, unresolved
  profile, missing authority, or ambiguous join mean public or trusted;
- omitting participant context, retained memory, tool arguments, destination,
  error output, monitor inputs, transformation apparatus, shared state,
  handoff, replay, or episode history from the possible-influence set;
- treating redaction, sanitization, summarization, projection, parsing,
  trusted editing, approval, or handoff as automatic declassification or
  endorsement;
- removing provenance when endorsement changes the admitted integrity
  coordinate, or mutating a historical label after policy change;
- overloading API-423 declassification to represent endorsement, or adding
  caller-authored policy/cut/label fields to headers, query parameters,
  metadata, or backend options;
- creating a new relation or claim surface beside
  `policy-noninterference`/`participant-information-flow-policy`;
- advancing the behavioral catalog without archiving/resolving rev11 and
  moving all live producers and fixtures together;
- reporting bounded algebra tests as universal noninterference, model checking,
  proof, final-sink enforcement, backend realization, covert-channel control,
  monitor honesty, or intentional-subversion robustness; and
- implementing #1002 contracts, #1003 runtime/store changes, #1004 backend
  capability, or #1007 adversarial evaluation as “helpful” work in #1001.

## Non-Goals And Implementation Boundaries

- No portable DTO, JSON Schema, public API, SDL syntax, config surface, or
  runtime policy loader.
- No final-sink enforcement, external call, participant delivery, streaming,
  persistence, idempotency, audit, or error-envelope change.
- No backend declaration, apparatus integration, quarantine mechanism,
  monitor service, gateway, prompt policy, agent framework, or trajectory
  store.
- No replacement or modification of API-409/API-423, runtime-fact, action,
  observation, history, snapshot, experiment, evidence, or conformance carrier
  ownership.
- No model alignment, chain-of-thought or private-state safety, monitor honesty,
  covert-channel protection, intentional-subversion robustness, universal
  noninterference, bisimulation, opacity, model-check, proof, runtime
  realization, or backend-conformance claim.
