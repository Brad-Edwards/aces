# Issue #800 — ASR-535 Participant Information-Flow And Relation Assurance Preflight

Date: 2026-07-28

Issue: #800.

Requirement: ASR-535.

This note records architecture guardrails for executable participant
information-flow assurance and backend conformance. It is implementation
guidance only. It does not add assurance cases, change a contract or report,
run a model checker, certify a backend, change requirement status, or establish
universal noninterference, equivalence, refinement, simulation, or
bisimulation.

## Decisive Current-State Finding

The required architecture already exists. Issue #800 must compose and extend
it, not create another assurance subsystem:

- ADR-081 and the revision `rev3` behavioral-relation catalog already own
  relation identity, claim surfaces, quantifiers, evidence boundaries,
  assurance state, limitations, and explicit nonclaims.
- ADR-085 and
  `specs/formal/participant-semantics/information-flow-control.md` already own
  the `policy-noninterference` definition and its deliberately unproved status.
- API-423 and RUN-319 already provide closed participant-crossing records,
  deny-first gates, exact policy/state-cut coordinates, safe failure behavior,
  append-only persistence, and evidence/provenance refs.
- API-407 already provides governed participant-policy feature declarations,
  strength-aware admission, limitation/disclosure/evidence refs, and
  unsupported-capability handling.
- `raes_conformance.conformance` already owns the fixture runner, target runner,
  target probes, diagnostics, `ConformanceCaseResult`,
  `BackendConformanceReport`, `bounded-probe-success` claim construction, and
  the one machine-readable report projection.
- `raes_operations.realization_conformance` already owns redaction-gated,
  root-confined, atomic persistence of backend conformance reports.

The missing concern is executable assurance composition: finite semantic
falsification, participant-policy runtime probes, adversarial backend behavior,
and honest report bindings over those existing surfaces. No new ADR, report
family, relation registry, proof vocabulary, persistence store, exception
hierarchy, or workflow is justified.

## Binding Authorities

- ADR-021 governs falsification-first evidence.
- ADR-081,
  `contracts/concept-authority/behavioral-relations-v1.json`,
  `specs/formal/behavioral-relations/README.md`,
  `BehavioralClaimBindingModel`, and
  `validate_behavioral_claim_binding()` govern relation and claim discipline.
- ADR-085,
  `specs/formal/participant-semantics/information-flow-control.md`, and
  `test_sem_230_information_flow_control.py` govern the information-flow model,
  claim boundary, and current finite semantic evidence.
- API-423 `ParticipantCrossingOccurrenceModel` and
  `validate_participant_crossing_occurrence_context()` govern portable crossing
  evidence and cross-record validity.
- RUN-319 `ParticipantCrossingIntent`,
  `ParticipantCrossingPolicyResolver`, `RuntimeControlPlane`, crossing
  mediation, capability gates, `RuntimeSnapshot`, and `ControlPlaneStore`
  govern executable enforcement and persistence.
- API-407 `ParticipantFeatureSupport`,
  `PARTICIPANT_RUNTIME_POLICY_FEATURES`,
  `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`, and
  `resolve_participant_feature_support()` govern backend support claims and
  weakening.
- ASR-502/519/527 conformance decisions and
  `docs/explain/reference/backend-conformance.md` govern runner, report,
  realization-honesty, and backend evidence boundaries.
- ADR-007/018 and `specs/formal/assurance-policy.yaml` classify participant
  policy/control work as FM3. A solver is recommended, not mandatory.
- ADR-009/019/036/061 govern authority placement, package boundaries, and
  published-schema compatibility.
- `.ground-control.yaml`, `.gc/plan-rules.md`, and `noxfile.py` own verification
  workflow. The branch already contains issue `800`, but not requirement UID
  `ASR-535`; workflow commands must use `RAES_REQUIREMENT_UID=ASR-535`.

## Architecture Decisions And Guardrails

### Keep one claim authority and one report family

Every backend assurance report remains a `BackendConformanceReport`, and every
behavioral assertion remains a validated `BehavioralClaimBindingModel`.
Participant-policy cases extend `ConformanceCaseResult`; they do not create an
`InformationFlowReport`, `NoninterferenceReport`, proof-result schema, or
relation-local claim DTO.

The report-level relation for finite fixture and target cases remains
`bounded-probe-success`. A participant-policy case may reference the
`policy-noninterference` obligation it attempts to falsify, but passing finite
cases does not change the report's relation to `policy-noninterference`.
`policy-noninterference` may carry `model-checked` or `proved` assurance only
when its universal quantifier and corresponding model-check/proof evidence are
actually present and validated.

The existing report and claim structures must be extended in place only where
needed to make issue #800 coordinates machine-reviewable. Do not encode exact
bindings solely in case names or prose. A participant-policy case and the
report claim together must identify:

- taxonomy and exact relation revision;
- participant, episode or declared cross-episode memory scope, audience, and
  projection identity/revision;
- policy id, revision/digest, exact decision/state cut, and declassification
  schedule when applicable;
- left and right carrier/evidence refs for the varied high/low cases;
- quantifier scope and finite generated or enumerated case/model boundary;
- time/order, concurrency, scheduler, environment, nondeterminism, termination,
  progress, timing, probability, and partial-order assumptions;
- execution basis, target/profile/configuration binding, and backend declared
  and effective support;
- assurance status, evidence refs and digests, limitations, counterexample
  outcome, and explicit nonclaims.

Use stable refs and digests to API-423 occurrences, participant-visible history
projections, policy decisions, and evidence artifacts. Do not copy hidden
payloads, policy bodies, world state, participant memory, or backend-native
objects into the report. If the current report fields cannot preserve one of
these coordinates, extend `ConformanceCaseResult` or the existing claim binding
compatibly and update all embedded published schemas; do not add a parallel
claim record.

Report construction must have one final cross-field validation seam before
serialization or persistence. It must validate the claim against the catalog,
ensure every claimed case is present (including failed, unsupported, and
counterexample cases), reject a universal quantifier backed only by finite
evidence, and prevent `native_conformance` or a stronger assurance status from
being inferred from fixture-only or hermetic evidence.

### Preserve independent assurance lanes

Four evidence lanes remain distinguishable in the same claim/report
discipline:

1. **Semantic falsification:** the pure SEM-230 model and property/counterexample
   tests vary high inputs, policy/declassification schedules, strategies,
   memory scope, and assumptions. This lane can refute a bounded model but says
   nothing about production enforcement or a backend.
2. **Runtime enforcement:** probes use the real `RuntimeControlPlane`,
   `ParticipantCrossingPolicyResolver`, authenticated identity/subject binding,
   RUN-319 crossing mediation, capability admission, append-only store, and
   retrieval/action/inject boundaries. Unit-level direct construction of an
   occurrence is contract evidence, not enforcement evidence.
3. **Backend conformance:** the existing target runner drives a named target
   through the same runtime boundary and reports declared versus effective
   feature strength, operation/status, crossing/history evidence, and finite
   execution basis. Manifest validity and method presence remain insufficient.
4. **Formal verification:** a bounded model-check or proof is an optional
   stronger lane. It is recorded only when explicitly claimed and never inferred
   from property tests, exhaustive enumeration by an ordinary unit test, or a
   green conformance report.

No lane promotes another automatically. The report may cite multiple lanes,
but their assurance statuses and evidence boundaries remain independently
visible.

### Inject participant-policy probes through the existing target runner

`run_target_conformance()` and `_TargetConformanceOptions` are the extension
seam. Add a backend-neutral participant-policy probe harness/policy parameter
there rather than hard-coding a reference-backend branch or adding another
runner. The harness must supply:

- a validated policy resolver and validation context;
- deterministic participant, episode, audience, controller/authority, policy,
  projection, state-cut, and evidence coordinates;
- safe actions, views, control transitions, and participant-directed inject
  carriers that enter through existing public runtime boundaries;
- a declared finite case/mutation policy and deterministic digest;
- an independent expected-observation and no-mutation ledger; and
- report-safe evidence refs and limitations.

`_UnavailableConformanceCrossingPolicyResolver` is an appropriate fail-closed
default for unrelated adapter probes, but it is not participant-policy
conformance evidence. A positive API-407 participant-policy declaration must
not pass merely because the current adapter probe avoided the crossing path.
When no policy probe harness is supplied for a positive claim, the case is
unsupported or failed, never silently skipped or passed.

The obvious future variation is another policy model, participant memory scope,
order model, scheduler/environment class, crossing kind, target, or observer.
Those variations plug into the harness and case policy; backend names and
feature ids do not become dispatch branches in the conformance engine.

### Make adversarial cases single-fault and boundary-faithful

Adversarial targets and resolvers are test fixtures behind the same
`RuntimeTarget`/`RuntimeControlPlane`/store boundary. They must not add dishonest
modes to a production backend or monkeypatch the gate under test. Each case
injects one prohibited behavior so its stable failure reason is attributable.

The finite suite must cover these distinct obligations:

| Concern | Required observable result |
| --- | --- |
| denial | denied gate, no backend execution or participant-visible release, append-only safe decision/audit evidence |
| withholding | intentional non-release remains distinct from failure, redaction, concealment, or later revocation |
| redaction | only an already-authorized representation is transformed; source markings/provenance remain unless governed declassification changes them |
| governed declassification | exact authority basis, policy revision/state cut, release dimensions, markings, and schedule; absent/stale authority fails closed |
| transformation | fresh result identity and evidence; ingress result receives fresh structural, semantic, policy, capability, and action admission |
| stale or revoked policy | no retroactive authorization, no replay across an advanced state cut, and no mutation/release |
| cross-participant leakage | participant/audience binding mismatch fails before serialization; no sibling history, payload, or evidence ref leaks |
| participant-directed inject delivery | preserves DSL-142/DSL-111 identity, addressee, policy decision, delivery and observation distinction, and ordering |
| backend weakening | only policy-authorized downgrade is admitted; effective weaker strength, limitations, disclosures, and stronger nonclaim are recorded |
| unsupported capability | explicit unsupported gap and failed/unsupported case; no fallback from method presence or generic participant runtime support |
| adversarial overclaim | a target that declares exact support but omits, leaks, mutates, weakens, or fabricates evidence fails without retaining the exact claim |

Negative cases must assert both semantic refusal and side-effect boundaries:
portable snapshot/store history, participant-visible result, backend call
ledger, audit event, and report claim. A denied case that still called the
backend or serialized a hidden value is a failure even when its final status is
denied.

### Keep formal evidence optional and exact

ASR-535 does not require a universal proof or a model checker merely to satisfy
the finite conformance outcome. If the implementation makes no model-check or
proof claim, keep `policy-noninterference` deliberately unproved and state that
explicitly.

When a model-check or proof claim is made, its evidence must name the exact:

- formal model and immutable revision/digest;
- finite bound or universal domain and all quantifiers;
- participant/projection/policy/memory/declassification coordinates;
- time/order, scheduler, environment, nondeterminism, concurrency, progress,
  termination, divergence, timing, probability, and partial-order assumptions;
- tool and version, invocation/reproduction procedure, and input/config digest;
- explored state/transition count or proof-check result;
- result and complete counterexample ref when one exists; and
- output artifact digest, assurance status, limitations, and nonclaims.

Use the existing `BehavioralClaimBindingModel` evidence scope and refs to bind
that artifact. Do not reuse `scheduler-isolation-proof-v1` or
`exploit-path-analysis-evidence-v1` for a different semantic domain, and do not
publish a generic proof vocabulary solely for this issue. Any invoked tool must
be pinned and run hermetically through the repository's existing verification
tooling; unpinned network downloads or opaque hosted solver results are not
reproducible evidence.

### Update lineage without inventing compatibility

The participant section of `docs/explain/sdl/lineage.md` must record issue #800
delivery status, exact RAES artifact mappings, evidence links, and nonclaims.
`contracts/provenance/sdl-lineage-ledger-v1.json` and
`docs/research/lineage/source-audit-2026-07-12.md` change only if issue #800
changes a normative derivation or compatibility claim. New test or conformance
evidence alone does not justify rewriting the lineage ledger.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Formal relation | `specs/formal/participant-semantics/information-flow-control.md`, the SEM-230 abstract model/tests, and catalog relation `policy-noninterference`; do not redefine low equivalence, purge, projection, memory, or strategy semantics in conformance code. |
| Relation authority | `BehavioralRelationCatalogModel`, `BehavioralClaimBindingModel`, `load_behavioral_relation_catalog()`, `validate_behavioral_claim_binding()`, and `tools/check_behavioral_relation_claims.py`. |
| Crossing contract | `ParticipantCrossingOccurrenceModel`, its published API-423 schema/fixtures, and `validate_participant_crossing_occurrence_context()`; reference typed subjects and occurrences rather than copying payloads. |
| Runtime policy | `ParticipantCrossingIntent`, `ParticipantCrossingPolicyResolver`, crossing boundary/mediation/policy/records modules, and the deny-first gate helpers. |
| Authentication and authorization | `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneIdentity`, `ControlPlaneRole`, target binding, participant controller/audience subject bindings, and existing audit denials. |
| Capability | API-407 feature-support entries, `PARTICIPANT_RUNTIME_POLICY_FEATURES`, `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`, and `resolve_participant_feature_support()`. |
| Persistence and ordering | `RuntimeSnapshot`, participant crossing/control/behavior histories, `ControlPlaneStore.commit_participant_transition()`, history-head compare-and-swap, request fingerprint, and idempotency/state-cut replay guards. |
| Conformance | `run_fixture_suite()`, `run_target_conformance()`, `_TargetConformanceOptions`, target probes, `ConformanceCaseResult`, `BackendConformanceReport`, and `_bounded_conformance_claim()`. |
| Diagnostics | `Diagnostic`, `Severity`, stable `conformance.*` codes, and the existing report projection. Expected failures are values, not a new exception hierarchy. |
| Report persistence | `backend_conformance_report_payload()`, `redaction_violations()`, `write_backend_conformance_report()`, `run_artifact_path()`, and `atomic_write_json_artifact()`. |
| Corpus and publication | `corpus_family_root()`, canonical fixtures/profiles, `ContractModel(extra="forbid")`, `schema_bundle()`, published-schema entries, and generated-schema/publication gates. |
| Lineage | participant lineage prose, `SDLLineageLedgerModel`, the lineage ledger/source audit, and `tools/check_sdl_lineage.py`. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, canonical nox sessions, repo policy, requirement governance, schema/concept/lineage gates, and `tools/verify_all.py`. |

## Cross-Cutting Layers And Security Posture

1. **Corpus/config shape.** Fixture and profile identifiers continue through
   grammar-checked, root-confined `raes_contracts.corpus` and backend-profile
   loaders. Tests may inject temporary roots, but production defaults remain the
   published corpus. A participant-policy harness is a typed in-process option,
   not an arbitrary module path, remote URL, executable expression, or JSON
   policy bag.
2. **Closed contract/parser gate.** External JSON passes bounded UTF-8 parsing,
   object/list shape checks, closed Pydantic `ContractModel` descendants, the
   matching published schema, and semantic/context validators. Crossing
   evidence additionally passes API-423 subject/policy/evidence/authority and
   predecessor/order validation. Do not repeat these joins with ad hoc key
   checks in the runner.
3. **Authentication and target gate.** In-process conformance makes no HTTP
   authentication claim. Runtime probes still use `ControlPlaneIdentity`,
   permitted role, target binding, participant/controller or audience binding,
   and audit denial. If later exposed through HTTP, use the existing strict
   control-plane app, request-size limits, verified identity, target scope,
   idempotency/fingerprint, and redacted error handlers; do not add a
   conformance auth route.
4. **Participant policy gate.** Caller authorization, target authorization,
   participant authority, action admission, visibility, marking authorization,
   declassification, backend support, and transformation validity remain
   independent and deny-first. `NOT_APPLICABLE` at a required gate becomes
   unresolved, not permit. Policy resolution is bound to the exact state cut;
   stale/revoked policy and replay after an advanced history head fail closed.
5. **Capability and backend gate.** A governed feature id, required minimum
   strength, required contract/evidence set, declared entry, and optional
   already-authorized downgrade all pass through
   `resolve_participant_feature_support()`. Schema validity, method presence,
   a positive manifest entry, or an unsupported case does not establish
   behavior. Declared and effective strength remain separate report facts.
6. **Transformation/result gate.** Redaction, declassification, projection, and
   transformation preserve source/result identity, markings, provenance,
   rule/revision, evidence, and loss. A transformed ingress action re-enters
   ordinary validation and admission. The report never treats loss or a hash as
   declassification.
7. **Persistence/ordering gate.** Prepare and validate the complete candidate
   history before `commit_participant_transition()` atomically commits snapshot,
   operation, and audit. Compare expected history heads. A rejected or
   conflicted case leaves backend state and participant-visible state unchanged
   while preserving only the safe denial/audit evidence required by the owning
   contract.
8. **Diagnostic and error-envelope gate.** Reports expose bounded stable codes,
   safe addresses, governed ids/refs/digests, and generic messages. Existing
   conformance paths currently concatenate raw `str(exc)` or nested diagnostic
   messages in `conformance/validators.py`, `conformance/target.py`, and
   `conformance/target_probes.py`; issue #800 must not reuse those paths for
   policy/backend failures without sanitizing them. Raw rejected payloads,
   policy lookup details, backend exceptions, Pydantic `input_value`, stdout,
   stderr, tracebacks, and object representations never enter a report, log,
   audit detail, CLI error, or HTTP envelope.
9. **Secret and hidden-content gate.** Probes, fixtures, digests, reports, model
   evidence, and lineage contain safe synthetic ids, refs, classifications, and
   bounded summaries only. They exclude credentials, bearer tokens, keys,
   prompts, chain-of-thought, private memory, hidden answers/world state,
   policy bodies, raw participant/backend payloads, host paths, connection URIs,
   environment dumps, and native object ids. Hashing secret-bearing content
   does not make it an acceptable portable identifier.
10. **Report/redaction gate.** Validate the complete report and claim before
    rendering. Apply the shared `redaction_violations()` gate before any durable
    write, then use the root-confined run-id path and atomic writer. The pattern
    gate is defense in depth, not a substitute for safe diagnostic construction:
    it cannot recognize every hidden participant or policy value.
11. **Config/env and OS/process gate.** Default finite and hermetic probes need
    no secret loader, dotenv, socket, daemon, privilege, shell, or network
    access. Do not place policy text, participant data, evidence payloads,
    credentials, or full reports in argv, environment variables, filenames, or
    host logs. A future solver or native target receives typed configuration and
    injected handles, uses fixed argv with no `shell=True`, bounded resources
    and timeouts, pinned versions, and explicit opt-in; unavailable tooling is
    unsupported, never a passing result.
12. **Governance/publication gate.** If an existing published model embedded in
    experiment-study or scientific-completeness schemas changes, update the
    hand-governed schema, publication `last_change` hash, generated bundle,
    fixtures, compatibility classification, and all current consumers together.
    A report-only internal dataclass change does not create a new public schema
    by implication.

## Whole-Repository Surfaces In Scope

- **Normative and concept authority:** participant information-flow semantics,
  behavioral-relation catalog and claim surface, assurance policy/fulfillment,
  and participant lineage.
- **Published contracts:** API-423 crossing occurrence, backend manifest and
  participant feature support, any schema that embeds
  `BehavioralClaimBindingModel`, their fixtures, and schema-publication records
  only when their shape changes.
- **Runtime:** participant crossing boundary, mediation, policy, records,
  action/egress/control/inject entry points, capability admission, runtime
  target, snapshot, store, audit, and control-plane security.
- **Conformance and operations:** fixture/target runners, target probes,
  diagnostics, report/serializer, realization-honesty harness patterns,
  redaction validation, safe artifact paths, and atomic writer.
- **Verification:** SEM-230 property/counterexample tests, API-423 context tests,
  RUN-319 enforcement/security/persistence tests, API-407 strength tests,
  single-fault dishonest targets, report cross-field/redaction tests, policy
  gate tests, docs build, and canonical repository verification.
- **Host/runtime:** default local hermetic execution, optional explicitly
  configured model checker or native target, filesystem containment, fixed
  process invocation, bounded resources/timeouts, and no ambient secrets or
  privileges.

## Gotchas And Anti-Patterns

Avoid:

- changing the relation on a finite backend report from
  `bounded-probe-success` to `policy-noninterference`;
- treating equal sampled histories, no observed leak, property-test coverage,
  finite enumeration, or a bounded model check as universal proof;
- treating `policy-noninterference`, projected-history equivalence, trace
  inclusion/equivalence, refinement, simulation, and bisimulation as aliases;
- reporting a universal quantifier without model-check/proof evidence, or
  reporting model-checked/proved assurance without a pinned reproducible
  artifact and exact assumptions;
- creating another report, claim binding, relation registry, proof vocabulary,
  fixture runner, backend profile family, exception hierarchy, logger, store,
  endpoint, auth stack, or workflow;
- adding a report-only participant/policy DTO that duplicates API-423
  occurrences instead of binding stable refs and digests;
- allowing a positive manifest claim or method presence to substitute for a
  participant-policy probe, or counting skipped/unsupported work as passed;
- using `_UnavailableConformanceCrossingPolicyResolver` as positive evidence;
- driving only a test-local resolver/model while claiming runtime or backend
  enforcement;
- injecting dishonest behavior into production backends, monkeypatching the
  gate under test, or combining multiple faults in one diagnostic case;
- checking only final status while ignoring backend calls, portable/native
  mutation, participant serialization, audit, persistence, or claim strength;
- treating redaction as authorization, transformation as declassification,
  withholding as failure, revocation as erasure, delivery as observation, or
  audit retention as participant disclosure;
- applying a later policy/declassification/controller state retroactively or
  replaying an idempotent result after the relevant state cut advanced;
- concatenating `str(exc)`, backend diagnostics, rejected refs, or raw model
  validation prose into `Diagnostic.message`;
- relying solely on the generic redaction-pattern scan to make unsafe report
  content safe;
- putting credentials, policy/payload content, hidden state, solver inputs,
  connection URIs, or full reports in argv/environment/logs; and
- updating the lineage ledger for evidence-only delivery or failing to update
  it when a real normative derivation/compatibility claim changes.

## Non-Goals And Implementation Boundary

Issue #800 may extend the existing conformance case/report and target-runner
seams, add deterministic participant-policy and adversarial target probes,
strengthen shared claim/report validation and error redaction, add bounded
semantic properties/counterexamples, add a reproducible model-check artifact
only when explicitly claimed, and update participant lineage/evidence status.

It does not:

- change the SEM-230 relation definition merely to make a test pass;
- mandate universal noninterference, equivalence, refinement, simulation,
  bisimulation, epistemic, strategic, timed, probabilistic, or partial-order
  proof;
- introduce SDL syntax, a policy-expression language, generic participant
  message/payload carrier, transport, gateway, universal policy engine, or
  backend-neutral hidden-state observer;
- redesign API-423 crossing records, RUN-319 policy enforcement, API-407
  capability declarations, control-plane authentication, runtime persistence,
  or backend protocols beyond the narrow conformance extension seam;
- certify every participant, policy, strategy, scheduler, environment, backend,
  target, configuration, or unexecuted trace;
- require default verification to access a network, daemon, live participant,
  secret, privileged host resource, or native backend; or
- infer runtime realization, native conformance, scientific completeness, or a
  universal behavioral relation from schema validity, issue closure, requirement
  activation, passing fixtures, or finite evidence.
