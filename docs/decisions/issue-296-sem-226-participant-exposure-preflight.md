# Issue 296 SEM-226 Participant Exposure Preflight

Date: 2026-07-20

Issue: #296. Requirement: SEM-226.

This note fixes the repository-wide boundary for participant exposure and
visibility enforcement. It is implementation guidance only: it adds no SDL,
contract, schema, projector, runtime behavior, API, persistence, or test.

ADR-083 already owns the seven-layer participant exposure model. Accepted
ADR-085 and the SEM-230 formal specification own revisioned information-flow
operations and their exact claim boundary. No new ADR, visibility taxonomy,
policy model, or formal relation is needed for this issue.

## Dependency And Baseline Gate

Implementation must start from a branch current with the development baseline
that delivered SEM-230 and SEM-220, then build on the delivered
`participant-decision-surface-v1` contract, time-indexed projector,
selection/admission binding, SEM-230 formal coordinates, and accepted ADR-085.
Stale local copies are not an alternate authority and must not be extended in
parallel.

The canonical dependency surfaces include:

- `ParticipantDecisionSurfaceModel`, its discriminated forms and action
  entries, and `validate_participant_decision_surface_context()`;
- `ParticipantDecisionSurfaceProjectionInput` and
  `project_participant_decision_surface()`;
- `participant_observation_effective_relation()`, the single compiled
  `V_p,o` selector shared with behavior-history validation;
- `bind_participant_decision_surface_selection()` and the existing
  `ParticipantActionAdmissionRequest` path; and
- `specs/formal/participant-semantics/information-flow-control.md`, including
  `Effective(rho,o)`, `MayCross`, the distinct operation table, and the
  explicit proof nonclaims.

## Binding Architecture Decisions

### Specialize the delivered projection; do not add another envelope

SEM-226 is the deny-first exposure specialization of the delivered
participant decision-surface and context-view projection. The serialization
boundary remains `ParticipantContextViewModel` plus its typed
`ParticipantDecisionSurfaceModel` payload. Do not publish a second context,
audience, decision-surface, observation, or generic participant-I/O envelope.

Every prospective serialized item must be resolved at `(participant, episode,
audience/role scope, observation point, order point, policy revision)` before
it is admitted to `visible_context_refs`, an action/affordance entry, an
observation payload, or another participant-facing result. The gate composes:

1. the compiled behavior, action/affordance, and observation-boundary scope;
2. `participant_observation_effective_relation()` at the exact history order;
3. the context source layer and governed transformation;
4. participant and audience/role binding;
5. the effective SEM-230 projection-policy identity and revision;
6. the selected exposure-policy identity/version/digest and withholding set;
7. markings and inherited disclosure restrictions;
8. explicit declassification, redaction, projection, or transformation refs;
9. evidence, provenance, loss, limitations, and backend posture; and
10. a separate realized delivery/observation basis when realization is
    claimed.

Missing, stale, ambiguous, cross-participant, unsupported, or unresolved
required coordinates fail closed. A later revision, final snapshot, or current
aggregate view cannot repair an earlier failed gate.

The implementation may add only the minimum typed per-item binding needed to
make this agreement checkable. It belongs inside the existing decision-surface
or referenced context/observation relation and carries stable refs/digests,
not copied policy bodies or payloads. It must not pre-empt API-423's future
common crossing-decision contract or create a universal exposure item.

### Keep the policy authorities distinct

`ParticipantDecisionSurfaceModel.projection_policy_ref` and
`projection_policy_revision` identify the SEM-230 policy coordinate used for
the order-scoped projection. `ParticipantExposurePolicyModel` records selected
run/apparatus exposure intent and capability compatibility. Its optional
version/digest and ref lists are not a complete SEM-230 policy, and its
`constraints` map is not a policy language.

Both authorities must resolve and agree where they overlap; neither may be
silently derived from the other. A manifest or selected exposure policy is not
authored participant authority, a declassification decision, or proof of
delivery. Backend support is not permission.

The SEM-230 operations stay independent:

- authorization and admission decide whether a crossing may proceed now;
- withholding records intentional non-release;
- projection/masking selects a participant-relative representation;
- redaction transforms already authorized content and never grants access;
- declassification changes release authority for explicit dimensions,
  audience, authority, policy revision, and order interval;
- disclosure records the authorized release decision;
- delivery/observation records realized participant-facing occurrences;
- concealment/revocation changes future availability without rewriting learned
  history; and
- loss/weakening reports reduced fidelity or assurance, not successful
  security enforcement.

### Preserve source strata and transformation identity

Participant observations, authored control context, hidden truth,
adjudication/evaluator assets, private answer material, archival evidence,
derived analysis, scaffold guidance, and augmentation remain different source
classes. Reuse `ParticipantContextViewModel.source_layers`, transformation,
audience, evidence/provenance, marking, redaction, and limitation fields. The
existing SEM-214 source-binding and SEM-216 archival mediation validators are
incumbents, not optional checks.

Those validators are not sufficient role enforcement: `audience_scope` is a
closed classification, and the current API-408 HTTP read role authorizes a
control-plane caller for the target, not the participant subject or requested
audience. SEM-226 needs a semantic participant/audience binding gate before
serialization. Do not describe `_validate_sem216_audience_boundary()`,
`_project_scope()`, or an auditor/operator role check as that gate.

A redaction, summary, masking, or augmentation creates or selects a governed
result identity. Preserve source/result refs or digests, rule and revision,
actor/authority, reason, inherited markings, evidence/provenance, loss, and
limitations. Derived content inherits source markings and disclosure
restrictions unless a governed declassification decision explicitly changes
them. Never overwrite the source in place.

Reuse `ExperimentAugmentationDisclosureModel` for run-level processor/backend
augmentation provenance, classifications, markings, participant visibility,
observer effects, and evidence. SEM-226 still evaluates whether the referenced
augmentation result is exposed to this participant at this order; the run
disclosure alone does not authorize participant delivery.

### Separate authored policy, projection, and realized exposure

The exposure projector decides what may be serialized. Realized exposure is a
different fact and must agree with existing observation envelopes, behavior
history, delivery basis/order, evidence, and provenance. A surface policy ref,
manifest capability, visible entry, or generated response is not realization
evidence.

Use existing occurrence-bearing records and stable refs. Do not create a
decision-surface store, exposure cache, audit stream, log schema, or metadata
side channel. API-423 owns the future common portable crossing decision and
RUN-319 owns general runtime orchestration, append-only decision/realization
persistence, and audit. SEM-226 supplies the reusable exposure predicate and
agreement checks those layers must call; it does not fork their workflow.

## Canonical Incumbents To Reuse

- **Authored semantics:** `ParticipantBehaviorSpecification`, governed
  tool-affordance bindings, participant/role and authority/scope refs, action
  contracts, observation boundaries, `ParticipantViewRule`, and
  `ParticipantViewTransition`.
- **Ingress and semantic validation:** `load_sdl_yaml()`, source budgets and
  duplicate-key-safe loading, `parse_sdl()`, `parse_sdl_file()`,
  `SDLModel(extra="forbid")`, normalized keys, variable-key rejection,
  `SemanticValidator`, `analyze_participant_behavior()`, controlled-vocabulary
  validation, `instantiate_scenario()`, `admit_instantiated_scenario()`, and
  complete post-substitution revalidation.
- **Compilation and order:** canonical `participant.*` addresses,
  `ParticipantBehaviorSpecificationRuntime`,
  `ParticipantToolAffordanceRuntime`, `ParticipantActionContractRuntime`,
  `ParticipantObservationBoundaryRuntime`, compiled `view_relation_timeline`,
  behavior-history anchors, and `participant_observation_effective_relation()`.
- **Portable views and surfaces:** `ParticipantContextViewModel` and its source,
  transformation, comparability, and SEM-216 validators;
  `ParticipantDecisionSurfaceModel`, its forms/action entries,
  `validate_participant_decision_surface_context()`, and the published
  context-view/decision-surface fixtures.
- **Policy, apparatus, and admission:** SEM-230 `Effective(rho,o)`/`MayCross`,
  `ParticipantImplementationManifestModel`,
  `ParticipantImplementationSelectionModel`,
  `ParticipantExposurePolicyModel`, apparatus-context validation,
  `ParticipantActionAdmissionRequest`,
  `participant_action_admission_request_violations()`,
  `bind_participant_decision_surface_selection()`, and existing SEM-211
  result/history validation. The admission helper is not the complete
  exposure, argument-shape, or SEM-211 applicability evaluator.
- **Realization and evidence:** `ParticipantObservationEnvelopeModel`,
  `ParticipantBehaviorHistoryEventModel`, action results, runtime participant
  history checks, `ExperimentAugmentationDisclosureModel`, experiment evidence
  records, provenance refs, and realization limitations.
- **Runtime, persistence, and audit:** `RuntimeSnapshot`, `RuntimeControlPlane`,
  `ParticipantControlMixin`, `ControlPlaneStore`,
  `InMemoryControlPlaneStore`, `LocalControlPlaneStore`, and `AuditEvent`.
  Audit retention is not participant disclosure.
- **Contracts and concepts:** `ContractModel(extra="forbid")`,
  `schema_bundle()`, `contracts/schemas/`, `contracts/fixtures/`, the schema
  publication index and per-contract entry, `x-aces-invariants`,
  `controlled-vocabularies-v1`, concept bindings, and governed
  `x-<owner>:<term>` extensions.
- **Errors and observability:** collected SDL errors, `Diagnostic`, `Severity`,
  `OperationReceipt`, `OperationStatus`, bounded HTTP 4xx details, the redacted
  FastAPI 500 handler, existing audit events, and evidence records. Add no
  exposure exception hierarchy or logger.
- **Assurance:** SEM-208/210 order and leakage tests, SEM-216 boundary tests,
  SEM-225 augmentation tests, SEM-220 surface projection/bypass tests,
  participant backend-contract fixtures, control-plane authorization tests,
  runtime snapshot/conformance checks, and the bounded SEM-230 counterexamples.
  Extend these patterns; do not add another fixture loader or conformance
  runner.

## Cross-Cutting Gates And Security Posture

- **Baseline/workflow gate:** merge current development dependencies before
  code. Keep `ACES_REQUIREMENT_UID=SEM-226` because the branch name has no UID.
  Reuse `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and the
  canonical policy/verification scripts. Do not edit version or changelog
  artifacts.
- **Parser/config gate:** any authored additions remain inert refs behind the
  existing UTF-8/source-size, safe-YAML, alias/depth/node/tag/directive,
  normalized-key, closed-model, variable, reference-resolution, and
  post-instantiation gates. Do not evaluate policy text or compile raw YAML,
  query parameters, environment values, or backend dictionaries.
- **Contract/schema gate:** every portable shape remains closed and bounded and
  passes Pydantic plus published JSON Schema validation. A schema change needs
  generated-bundle parity, valid/invalid fixtures, compatibility
  classification, and the canonical publication `last_change`/content hash.
  Cross-record obligations that JSON Schema cannot express use the existing
  relational validators and `x-aces-invariants` convention.
- **Semantic exposure gate:** every emitted ref has one participant/episode,
  source layer, audience/role basis, exact order and effective policy revision,
  compiled visibility proof, marking/declassification result,
  transformation/redaction result, evidence/provenance, and limitations.
  Unknown or absent required state denies serialization.
- **Authentication/authorization gate:** a future HTTP surface must enter
  through `create_control_plane_app()`, `ControlPlaneSecurityConfig.strict_defaults()`,
  bearer or verified-proxy identity, target-bound read/mutating roles,
  request-size guards, mutation idempotency/fingerprints, and audit. Then it
  must separately bind caller/controller authority, participant subject,
  audience, and exposure policy. Current backend/operator/auditor roles do not
  confer participant visibility.
- **Secret-handling gate:** contracts, fixtures, diagnostics, audit, logs, and
  lineage contain safe ids, refs, digests, classifications, reason codes, and
  bounded summaries only. Exclude bearer tokens, credentials, private keys,
  hidden prompts, answer keys, canaries, raw policy/configuration bodies, raw
  evidence/payloads, backend objects, environment dumps, and tracebacks.
- **Error-envelope gate:** expected structural/semantic/runtime failures reuse
  the existing collected error and `Diagnostic`/operation-envelope paths.
  Bounded 4xx details must not reveal whether a hidden cross-participant item
  exists. Unexpected failures retain `{"detail":"internal server error"}`;
  native exceptions and rejected values stay out of responses and audit
  details.
- **Persistence/observability gate:** policy decisions and realized occurrences
  remain distinct and append-only in the owning history/evidence surfaces.
  `RuntimeSnapshot.metadata`, history `details`, exposure-policy `constraints`,
  audit `details`, and logs are not policy or evidence stores. Raw logs are
  evidence inputs only after governed capture; they are never participant
  output by default.
- **Environment/OS gate:** SEM-226 introduces no env var, secret-loader, CLI
  policy argument, subprocess, socket, listener, route, session, or shell
  command. Later adapters must keep secrets, policies, prompts, hidden data,
  and arbitrary user values out of process argv, filenames, environment
  captures, stdout/stderr, and shell strings; use injected providers, fixed
  invocation shapes, bounded timeouts, controlled working directories, and no
  `shell=True`.
- **Package/authority gate:** normative meaning stays under `specs/` and
  published contracts; authored models stay in `aces_sdl`, compiled projection
  in `aces_processor`, neutral DTOs in `aces_contracts`, live control/security/
  persistence in `aces_runtime`, backend declarations in
  `aces_backend_protocols`, and checks in `aces_conformance`. Add no logic to
  compatibility-only `implementations/python/src/aces/` and no `aces.*` import
  from owning packages.
- **Documentation/traceability gate:** update the participant section of
  `docs/explain/sdl/lineage.md` with SEM-226's exact ACES mappings, actual
  delivery status, evidence links, and explicit nonclaims. Change the lineage
  ledger and source audit only if a normative external derivation or
  compatibility claim changes. Reconcile IMPLEMENTS/TESTS links and semantic
  coverage only to shipped artifacts; DRAFT, schema-valid, tested, proved, and
  runtime-realized remain different statuses.

## Extensibility Seam

The stable seam is one pure, time-indexed exposure selector over existing
addresses and typed carriers. The projection request carries stable refs only;
trusted resolver dependencies supply the implementation selection, policy
history, item authorization records, and realized occurrence records. Its
variation parameters are:

- participant, episode, audience/role, source layer, and item ref;
- observation point, order model/order point, and history prefix;
- compiled observation boundary and effective `V_p,o` relation;
- projection-policy identity/revision/effective order and selected exposure
  policy identity/version/digest;
- operation kind: withhold, project/mask, redact, declassify, disclose,
  conceal/revoke, transform, lose/weaken, deliver, or observe;
- source/result identity, markings, authority, transformation/declassification
  rule and revision;
- backend/apparatus support and permitted weakening; and
- evidence, provenance, delivery basis, loss, and limitations.

The selector must compare every resolved record with the requested
participant, episode, audience, order, selected apparatus, immutable policy
version/digest, policy revision, and item ref. A realized occurrence also binds
the delivered item and the authorization record that was effective under the
policy resolved at delivery order. A projection-owned selection object, policy
sequence, authorization boolean, declassification claim, transformation claim,
or delivery payload is not an authority source.

API-423 can later publish common crossing-decision references over this seam,
and RUN-319 can invoke and persist it for additional ingress/egress kinds. A new
audience, per-phase policy revision, streaming output, participant-directed
inject, or weaker backend posture changes governed parameters; it must not
require another view relation, policy bag, DTO family, store, or workflow.

## Gotchas And Anti-Patterns

Avoid:

- treating API-408 query values, `_project_scope()`, current snapshot refs, or
  read-role authorization as participant-safe projection;
- treating `ParticipantContextViewModel.audience_scope` or the SEM-216 archival
  validator as proof that a participant is entitled to the view;
- treating `ParticipantExposurePolicyModel.constraints` as SEM-230 policy or
  using its ref lists without order/revision and semantic resolution;
- conflating authorization, admission, withholding, masking, redaction,
  declassification, disclosure, delivery, observation, concealment,
  revocation, transformation, loss, weakening, or unsupported state;
- applying current/future policy to past order points or deleting prior visible
  occurrences after revocation, concealment, rollback, or supersession;
- stripping markings/provenance from summaries, augmentations, redactions, or
  transformed results without governed declassification;
- serializing raw hidden/evidence/adjudication payloads and hoping a later
  response filter will mask them;
- treating a policy ref, manifest capability, surface entry, HTTP 200, log
  line, or audit record as realized participant delivery;
- treating visibility as eligibility/admission or presentation as selection,
  execution, result, or outcome;
- adding a generic `ParticipantExposureEvent`, `ParticipantIOEvent`, policy
  bag, payload map, duplicate schema/validator/exception hierarchy, exposure
  store/cache, logger/audit stream, endpoint, or backend-local workflow;
- making capability booleans or silent fallbacks authoritative when required
  semantics are unsupported; and
- claiming universal noninterference, equivalence, refinement, simulation, or
  bisimulation from finite leakage/history tests.

## Non-Goals And Implementation Boundary

- No new participant UI, prompt format, external-agent API, gateway,
  transport, policy-expression language/engine, credential broker, tool
  runner, shell/RPC protocol, or OS sandbox.
- No replacement of SEM-210 visibility, SEM-211 applicability/admission,
  SEM-214 context views, SEM-216 source/audience boundaries, SEM-220 decision
  surfaces, SEM-225 augmentation disclosure, or existing evidence/provenance.
- No common API-423 crossing contract, RUN-319 general runtime enforcement or
  persistence workflow, backend capability implementation, migration, or
  universal information-flow proof in SEM-226.
- No participant-safe claim for the generic API-408 retrieval endpoints until
  their caller/subject/audience and item-level exposure gates actually exist.
- No erasure claim: revocation and concealment affect future release, not
  participant knowledge or append-only evidence of prior exposure.
- No lineage-ledger/source-audit update unless implementation changes a
  normative external derivation or compatibility claim.
