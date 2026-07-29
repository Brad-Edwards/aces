# Issue 261 ASR-513 Counterfactual And Necessity Validation Preflight

Date: 2026-07-28

Issue: #261. Ground Control requirement: ASR-513. The issue statement and the
supplied requirement record are the delivery contract. `ASR-513` is also the CI
branch UID and requirement-governance context.

This note fixes the repository-wide boundary for counterfactual and
necessity-oriented validation. It does not add SDL syntax, contracts, schemas,
catalog entries, fixtures, executors, reports, APIs, storage, or runtime
behavior. No new ADR is needed. ADR-022 already owns causal-attribution
strength, ADR-066 owns observation/evidence separation, ADR-068 and ADR-084 own
controlled variation and runs, ADR-072 owns validation strength and disclosure,
ADR-079 owns proposition truth, and ADR-081 owns behavioral-relation claims.

## Decision Boundary

ASR-513 validates a claim that a named candidate condition, weakness, control,
or behavior is necessary for a named outcome under one declared causal and
intervention boundary. It does not define those candidates or outcomes.

Keep five concerns separate:

1. **Claim semantics** state the exact candidate, outcome predicate, causal
   model, intervention, quantifier, and necessity criterion. Use
   `BehavioralClaimBindingModel` and the canonical behavioral-relations
   catalog. Because the catalog currently has no necessity relation, any
   portable ASR-513 claim must add the relation once to that authority and
   revision the catalog; it must not add a causal-claim DTO or local relation
   registry. Update every live binding, claim surface, fixture, and catalog
   assertion to the new exact revision in the same change; do not weaken
   `validate_behavioral_claim_binding()` into cross-revision fallback. A finite
   comparison remains a finite empirical claim.
2. **World construction** identifies a baseline world and one or more
   intervention worlds. Each world is an ordinarily admitted scenario
   snapshot, task/run intent, or existing subject-specific execution case.
   The intervention manifest states the one intended semantic difference and
   the policy for every held-fixed or permitted nuisance dimension. It is not a
   JSON patch, shell command, callback, backend mutation bag, or arbitrary
   object diff.
3. **World execution** exercises each admitted world through existing
   ASR-512, proposition-truth, experiment, conformance, runtime, and backend
   paths. Execution occurs only after ordinary parser, semantic, capability,
   authorization, configuration, trust, and cleanup gates. A replay without an
   intervention is not a counterfactual.
4. **Comparison** applies one predeclared, versioned necessity criterion to
   independently observed world outcomes. The minimum binary but-for shape is:
   the baseline outcome is decided true, the intervention is verified, the
   counterfactual outcome is decided false, and all differences outside the
   declared intervention satisfy the matching policy. Quantitative,
   probabilistic, sufficient-cause, actual-cause, or multi-cause criteria are
   different criteria, not silent interpretations of the binary result.
5. **Evidence and disclosure** preserve world identities, intervention
   evidence, outcome truth/evidence, comparability checks, cleanup/reset
   evidence, limitations, and the exact criterion result. Use the owning
   experiment, truth, participant, workflow, conformance, evidence, derived
   measure, behavioral-claim, and validation-basis carriers. A comparison
   result does not replace `ValidationBasisDisclosureModel` or promote itself
   to `falsification_backed`.

A passing bounded comparison supports only the recorded candidate, outcome,
worlds, intervention, apparatus, initial-state/reset policy, randomization,
time model, observation projection, and criterion. It is not proof across all
states, traces, strategies, environments, or implementations.

## Canonical Incumbents

| Concern | Canonical incumbent and required reuse |
| --- | --- |
| Validation taxonomy and disclosure | ADR-072, `validation-profile-catalog-v1.json`, `select_validation_profile()`, `ValidationBasisDisclosureModel`, gate-result rows, evidence refs, diagnostic refs, and explicit limitations. Profiles and disclosures never dispatch execution. |
| Causal and behavioral claim meaning | ADR-022 and ADR-081, `behavioral-relations-v1.json`, `BehavioralClaimBindingModel`, `validate_behavioral_claim_binding()`, and the existing catalog revision discipline. `ParticipantAttributionSupportClass` may label supporting participant evidence; it is not the ASR-513 protocol or result. |
| Outcome truth | ADR-079, `Proposition`, `Assertion`, `PropositionProbeBindingModel`, `PropositionTruthResultModel`, and runtime truth admission. Process success and evaluator lifecycle status are not outcome truth. |
| Per-world behavioral execution | The ASR-512 `BehavioralProbeCase`, digest-pinned `BehavioralProbeBinding`, injected capability-checked executor, sanitized diagnostics, evidence requirement, and cleanup rules. Reuse it where a world is a bounded behavioral probe; do not overload it with cross-world causal meaning. |
| Controlled worlds and variation | ADR-084, admitted scenario-family variation points, `ExperimentSelectionPolicyModel`, binding descriptors, immutable trial plans, explicit SDL instantiation, snapshot/run identity, and ordinary semantic revalidation. Do not invent a counterfactual scenario lifecycle. |
| Runs, controls, and comparison | ADR-068; `ExperimentRunModel`; `ExperimentStudyModel`; `ExperimentStudyFactorModel`; condition assignments; `ExperimentRunAllocationPlanModel`; `ExperimentAnalysisPlanModel`; `validate_experiment_run_against_task()`; and `validate_experiment_study_against_tasks_and_runs()`. One executed world is one existing archival run. |
| Randomness, time, and reset | Existing stochastic controls/draw records, semantic random-stream profiles, common-random-number consistency checks, experiment clock context, `TimeModelDeclarationModel`, `RealizedTimeModelProvenanceModel`, and `validate_realized_time_model()`. Pairing policy is explicit; identical wall time or a reused seed is not sufficient. |
| Observation, evidence, and analysis | ADR-064/066; capture specifications, `ExperimentEvidenceRecordModel`, `ExperimentDerivedMeasureModel`, source evidence refs, result summaries, traceability, loss/redaction, observer effects, and augmentation disclosures. Raw evidence, truth, and derived comparison remain separate. |
| Participant attribution | Existing attribution candidates, ordering bases, evidence bases, support classes, scope/visibility checks, and interpretation-rule refs. Do not treat a strong support-class enum value as proof that its evidence satisfies ASR-513. |
| Conformance execution | Existing fixture/target runners, `ExecutionBasis`, injected realization harness, capability admission, observations, residual-state checks, and bounded conformance claims. An out-of-envelope negative probe is not a counterfactual world. |
| Diagnostics and errors | `Diagnostic`, `Severity`, stable namespaced codes, Pydantic/SDL errors at their owning boundaries, operation envelopes, `PolicyFailure`, and the redacted HTTP 500 envelope. Add no ASR-513 exception hierarchy or logger. |
| Persistence and artifacts | Existing archival experiment/evidence/claim/disclosure artifacts. Live state stays in typed snapshots and `ControlPlaneStore`. Requested files use existing safe-path, redaction, validation, and atomic-write patterns. |
| Schema and workflow governance | Closed `ContractModel` shapes, `schema_bundle()`, `x-raes-invariants`, the schema publication manifest, fixtures, conformance registry, authority checks, `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and `tools/verify_all.py`. Extend each canonical graph once. |

The default design needs no new portable `counterfactual-case`,
`counterfactual-world`, `causal-model`, or `counterfactual-report` schema.
Experiment study/run/evidence/measure contracts already carry durable
controlled-comparison facts. A small frozen internal case/result seam in
`raes_conformance` is appropriate only for the executable join that has no
portable home. Its identities come from trusted admitted input; an executor may
return observations, evidence, diagnostics, and cleanup facts, but may not
replace the claim, worlds, intervention, criterion, or expected outcome.

## Cross-Cutting Validation, Security, And Operational Layers

1. **SDL source, parser, and phase admission.** Any authored variation still
   passes the bounded safe YAML loader, duplicate-key and source-profile
   checks, closed SDL shapes, module trust/composition rules, instantiation,
   unresolved-token rejection, and post-instantiation `SemanticValidator`.
   Parsing, schema generation, docs, and MCP inspection remain inert.
2. **Claim and reference shape.** Resolve one exact revisioned necessity claim,
   candidate address, outcome proposition/assertion or other governed outcome,
   baseline subject, intervention subjects, observation projection, and
   criterion. Existing role, scope, polarity, ref-kind, version, digest, and
   carrier-identity checks fail closed. Prose, a test name, path, tag, or object
   id is not claim identity.
3. **World and intervention admission.** The baseline must contain the
   candidate and be capable of the outcome. Every counterfactual world must
   derive from the same admitted family and exact baseline lineage. Verify that
   the intended intervention occurred and that undeclared semantic differences
   are absent or explicitly permitted. Failed, no-op, partial, or collateral
   intervention makes the comparison inconclusive or failed; it never supports
   necessity. Bare caller-supplied booleans or evidence-reference strings are
   not verification: a trusted assembler must derive intervention, matching,
   reset, and cleanup facts from typed artifacts after their owning validators
   pass and preserve the producer/validator identity.
4. **Contract and schema shape.** Portable changes use closed `ContractModel`
   shapes, schema versions, existing primitive/reference types, and
   `x-raes-invariants` for cross-artifact rules. Keep generated and published
   schemas identical and update the publication ledger, fixtures, registry,
   and conformance checks together. Internal dataclasses are not published
   contracts.
5. **Profile, capability, and apparatus admission.** Resolve the exact
   validation profile with `select_validation_profile()`. Resolve observation,
   evaluation, orchestration, participant, time, reset, isolation, cleanup,
   and intervention capability through existing manifests and admission
   helpers. Unsupported support is explicit. A profile or capability never
   grants execution or access.
6. **Configuration and environment shape.** ASR-513 needs no generic
   environment binder, causal-model root, executable path, plugin root, remote
   registry, or environment-selected corpus. Existing backends retain their
   closed config checks; libvirt retains `_validate_config_keys`, driver-mode
   and manifest/envelope agreement, and safe connection handling. Validate
   opt-in apparatus settings before driver creation. Ambient environment state
   is neither a held-fixed variable nor evidence.
7. **Executable artifact and supply-chain gate.** Treat scripts, packages,
   images, probes, and external analyzers as untrusted apparatus. Use pinned
   digests, declared trust policy, source limits, and allowlists. Contract data
   cannot select imports, callables, shell commands, executable URLs, images,
   guest commands, or backend dispatch. Candidate generation re-enters ordinary
   trust and admission.
8. **Authentication and authorization.** Prefer the existing in-process
   conformance composition root; no new route is needed. If execution crosses
   HTTP, use `create_control_plane_app()` and
   `ControlPlaneSecurityConfig.strict_defaults()`: verified identity,
   target-bound roles, participant-controller/audience bindings, request-size
   limits, idempotency keys, request fingerprints, and audit records remain
   mandatory. Scenario authority, causal-claim authorship, probe capability,
   and participant intervention authority are distinct.
9. **Secrets and information boundaries.** A secret or hidden answer is never
   a factor value, world id, digest input, claim text, fixture value, diagnostic,
   argv item, log, or public evidence payload. Use governed secret references
   only at authorized late-bound sinks. Preserve participant visibility,
   evidence sensitivity, marking, redaction, withholding, and audience-specific
   disclosure rules across every world. A stronger internal view cannot lend
   its strength to a weaker public comparison.
10. **OS and host exposure.** Adapters use fixed argument lists,
    `shell=False`, controlled working directories/environments, least
    privilege, and bounded time, output, CPU, memory, and filesystem use.
    Secrets, raw scenario/evidence bodies, connection URIs, host paths, native
    object dumps, and hidden assets never enter process argv. Reuse the OCI
    injected-runner/redacted-output pattern and the libvirt credential-free
    bounded fact channel; do not add a general guest command runner.
11. **Observation and evidence admission.** Outcome observations must be fresh,
    addressed, subject-bound, projection-bound, and collected at equivalent
    governed boundaries. Meet the declared observation strength and disclose
    loss, redaction, latency, observer effects, and apparatus augmentation.
    The trusted comparison assembler must resolve each truth result and its
    evidence through the exact `ExperimentRunModel`/traceability and
    `ExperimentEvidenceRecordModel.run_ref` for that world; matching only a
    truth-result address, result id, or free-form evidence ref is insufficient.
    Capture intent is not capture; logs are not portable evidence; raw evidence
    is not a derived comparison; participant-visible observations are not
    hidden truth.
12. **Error envelopes and observability.** Public failures expose only stable
    codes, safe addresses, coarse outcomes, and short redacted messages. Never
    expose rejected bodies, intervention payloads, commands, stdout/stderr,
    environment values, evidence content, native objects, or traces. Existing
    paths that render `str(exc)` are unsafe for untrusted counterfactual input;
    follow ASR-512 and disclose at most the exception type internally. Audit and
    logs summarize lifecycle activity; they are not causal evidence.
13. **Persistence, reset, and cleanup.** Each executed world gets its own
    immutable run/evidence identity. Never mutate one run into its
    counterfactual. Reset to the declared initial-state boundary between worlds,
    independently verify teardown, and reject residual state or cross-world
    leakage. Live snapshots, operation details, metadata, audit blobs, and logs
    are not the archival claim record. Validate and redact before atomic writes.
14. **Repository and package boundary.** SDL meaning stays in `raes`; portable
    DTOs in `raes_contracts`; compilation/admission in `raes_processor`; live
    control/security/storage in `raes_runtime`; capability declarations in
    `raes_backend_protocols`; concrete execution in adapters; comparison and
    conformance flow in `raes_conformance`; artifact assembly/writes in
    `raes_operations`; and user wiring in `raes_cli`. Keep the module policy and
    source-size cap intact; do not use private imports, compatibility shims, or
    `Any` bags to bypass ownership.

## Outcome And Concept Separation

| Surface | Question answered |
| --- | --- |
| Participant control `intervention` occurrence | Was a governed participant/control-plane action directed at an existing occurrence? |
| Causal intervention in an ASR-513 world | What one semantic candidate was removed, disabled, replaced, or held fixed for comparison? |
| Per-world probe/execution outcome | Did the bounded apparatus invocation run and meet its case contract? |
| Proposition outcome (`true`, `false`, `unknown`, `unsupported`) | What was the governed truth/support result for the outcome in one world? |
| Necessity comparison result | Does the admitted world evidence support, refute, or leave inconclusive the declared necessity criterion? |
| Validation gate outcome | Did one ASR-515 profile gate pass, fail, remain partial/not-run/unknown/unsupported/withheld, or not apply? |
| ADR-021 evidence status | What is the frozen falsification-protocol status: `untested`, `partial`, `demonstrated`, or `refuted`? |
| ASR-514 determinism/stability | Are repeated executions stable under a separately named variation and equivalence boundary? |

Mappings are explicit and cautious. Baseline true plus counterfactual false
supports a binary necessity criterion only after intervention, comparability,
evidence, and reset gates pass. Baseline false is non-vacuity failure. Both
worlds true refute the declared but-for claim; it is not an execution failure.
Unknown, unsupported, missing, stale, withheld, lossy, or incomparable evidence
is inconclusive, not false. Adding a candidate and observing the outcome may
support sufficiency; it does not establish necessity.

## Extensibility Seam

The stable seam is a subject-bound, immutable world-comparison case supplied by
trusted code to an injected, capability-checked executor/comparator. It binds:

- the revisioned behavioral claim and exact subject identity;
- baseline and intervention-world refs, versions, digests, lineage, and
  execution basis;
- candidate semantic address/type and a typed intervention kind;
- outcome proposition/assertion or governed metric plus projection revision;
- causal-model and necessity-criterion ids/versions, direction, threshold or
  tolerance, and quantifier/evidence boundary;
- a world-matching policy for initial state, allowed differences, apparatus,
  participants, scheduling, time, randomness, observations, and augmentations;
- finite case/replicate/allocation identity and canonical input digest;
- capability, authorization, time/resource, isolation, reset, and cleanup
  policy chosen by trusted code;
- typed verification producer/validator identity for intervention, matching,
  reset, cleanup, and truth-to-run joins; and
- evidence, diagnostic, limitation, audience, redaction, profile, and disclosure
  refs.

The next reasonable variation—a quantitative threshold, multiple ablations,
another candidate family, a statistical paired design, or a model-checked
criterion—adds one governed criterion/adapter and evidence mapping at this
seam. It must not require a new claim registry, scenario lifecycle, truth
algebra, run/trial identity, evidence graph, report root, exception tree,
logger, store, auth route, subprocess framework, or CI workflow.

## Whole-Repository Scope

- **Normative authority:** ADR-022/064/066/068/072/079/081/084; behavioral
  relations; participant semantics; proposition truth; validation profiles;
  experiment and evidence specifications; time/random-stream rules; and every
  changed concept catalog, profile, schema, fixture, publication record, and
  assurance mapping.
- **Implementation authority:** SDL parsing, semantic validation, variation,
  instantiation, and snapshot identity; experiment task/run/study/selection,
  stochastic, time, evidence, measure, traceability, and disclosure contracts;
  behavioral validation; conformance harnesses; manifests/capabilities;
  runtime auth/audit/store/cleanup; adapters; redaction; artifact writes; and
  CLI wiring only if a user command is explicitly in scope.
- **Verification authority:** positive and single-defect negative cases for
  claim/world/ref/digest/criterion admission; baseline non-vacuity; no-op,
  partial, wrong-target, collateral, stale, and reversed interventions;
  equivalent held-fixed dimensions; common-random-number and time-model
  consistency; missing/withheld/lossy evidence; unsupported capabilities;
  auth, redaction, argv, resource, reset, cleanup, residue, and exception
  leakage; plus schema, authority, module, behavioral-claim, and policy gates.
- **Workflow authority:** `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, and `tools/verify_all.py`. Set
  `RAES_REQUIREMENT_UID=ASR-513` because the branch name contains no UID.

## Gotchas And Anti-Patterns

Avoid:

- treating a negative fixture, failed action, replay, missing candidate,
  out-of-envelope probe, timestamp order, correlation, or outcome difference
  as counterfactual necessity;
- calling participant `intervention`, experiment `control`, a security control,
  control-plane control, and a causal intervention the same concept;
- using `counterfactual_support` or another attribution support enum as the
  validation protocol, comparison result, or proof;
- claiming necessity when the baseline outcome is false, the candidate is
  absent, the intervention is unverified/no-op/partial, or other semantic
  dimensions changed;
- treating an executor failure or cleanup failure as a false counterfactual
  outcome, or treating both-worlds-true as a probe failure rather than claim
  refutation;
- silently choosing but-for, threshold, sufficient-cause, actual-cause,
  probabilistic, or multi-cause semantics from the observed values;
- comparing mutable status updates, runtime snapshots, operation ids, tags,
  logs, audit blobs, or backend-native ids instead of immutable admitted worlds
  and archival runs;
- reusing one run id for two worlds, changing the baseline after observing the
  result, or failing to preserve the original falsifying evidence;
- inferring held-fixed state from a shared seed, wall-clock proximity, the same
  backend name, or free-form parameter equality;
- ignoring scheduler/order, nondeterminism, concurrency, time, observer
  effects, augmentation, hidden-state, carryover, reset, or participant-policy
  differences;
- creating a second relation catalog, causal graph, schema family, validator,
  truth table, experiment model, run/trial record, evidence store, report
  graph, exception hierarchy, logger, or workflow;
- adding a necessity relation without revising the catalog coordinate, or
  accepting old bindings against changed meaning through implicit fallback;
- executable code, imports, commands, URLs, filesystem discovery, dynamic
  plugins, or dispatch tables in claim/profile/protocol data;
- arbitrary dictionaries such as `causal_metadata`, `world_overrides`,
  `counterfactual_config`, `comparison_details`, or `intervention_payload`;
- selecting an executor, path, profile, target, candidate, or default
  counterfactual from untrusted data;
- raw evidence in truth/disclosure records, derived measures as raw
  observations, snapshots/logs as archive evidence, or public strength borrowed
  from hidden evidence;
- accepting `intervention_verified`, `matching_policy_satisfied`,
  `cleanup_verified`, or similar caller assertions as evidence without resolving
  typed producer output and the exact truth/evidence-to-run joins;
- `shell=True`, open child environments, unbounded output/time/resources,
  secrets or raw payloads in argv, and unsanitized `str(exc)`; or
- promoting one bounded comparison to universal causality, backend
  equivalence, participant strategy coverage, experiment validity,
  determinism/stability, proof, or `falsification_backed`.

## Non-Goals And Implementation Boundaries

- This preflight does not implement issue #261 or choose final field/class
  names.
- It does not add a general structural causal model, causal graph language,
  do-calculus engine, theorem prover, model checker, statistics engine, query
  language, or counterfactual scenario DSL.
- It does not redesign SDL variation, proposition truth, participant
  attribution/control, experiment allocation/analysis, random streams, time,
  profiles, disclosures, evidence storage, conformance, security, or cleanup.
- It does not implement ASR-514 determinism/stability. Repetition is evidence
  only under ASR-513's declared matching and uncertainty boundary.
- It does not guarantee executable replay, artifact retrieval, backend
  equivalence, universal causal identification, actual causation, sufficient
  causation, mediation, interaction effects, or transportability.
- It adds no API, service, UI, database, mutable registry, remote probe
  service, plugin system, credential broker, command endpoint, generic guest
  execution channel, or authoring-time side effect.
- Unsupported or unsafe candidate/outcome/intervention families remain
  explicit. The implementation must not weaken the claim, substitute a nearby
  probe, or invent a default world to make validation proceed.
