# Issue 262 ASR-514 determinism and stability verification preflight

Date: 2026-07-29

Issue: #262. Ground Control requirement: ASR-514. The issue statement and the
supplied requirement record are the delivery contract. `ASR-514` is the
requirement-governance context for CI because the branch name does not contain
the UID.

This note fixes the repository-wide boundary for determinism, stability, and
replay-consistency verification. It does not add a claim, comparator, schema,
fixture, runner, API, storage, or runtime behavior. No new ADR is needed.
ADR-066 owns observation/evidence separation, ADR-068 owns repeated runs and
replay claims, ADR-072 owns validation strength/disclosure, ADR-081 owns
behavioral-relation meaning, and ADR-084 owns deterministic trial realization
and controlled randomness.

## Decision boundary

ASR-514 applies when a producer makes an explicit repeatability claim. The
verification must bind that claim to exact subjects, inputs, execution or
artifact identities, an observation projection, a controlled-variation policy,
and a versioned comparison criterion. It must not infer repeatability from a
successful run, a seed, a retry, equal exit status, or two equal values.

Keep four concerns separate:

1. **Claim semantics** state what is expected to remain equal, equivalent, or
   within tolerance and under which variation. Use
   `BehavioralClaimBindingModel` and the canonical behavioral-relations
   catalog. Do not add a generic `repeatable`, `deterministic`, or `stable`
   Boolean, a local relation registry, or a free-form claim DTO.
   Relation carriers and observation projection are separate coordinates:
   for `canonical-artifact-identity`, left and right carriers are the two
   canonical artifacts, while the named canonicalization/projection profile
   belongs in the projection/criterion fields. Do not put a projection id in a
   carrier field. For a cohort larger than two, retain the individual
   baseline-to-repetition comparisons or use the study/statistical claim
   surface; do not silently reinterpret a binary relation as an n-ary one.
2. **Repetition identity and admission** identify distinct immutable artifacts
   or runs. Under ADR-068, a genuine re-execution has a distinct `run_id`;
   an idempotent pre-execution retry reuses the preallocated run identity and
   is not a replicate. Every compared scenario, task, run, study, apparatus,
   stochastic, time, evidence, and lineage artifact passes its existing
   structural and semantic validators before comparison.
3. **Comparison semantics** name the projection, canonicalization or metric,
   matching/variation policy, sample boundary, and decision rule before results
   are observed. Exact equality, projected equivalence, and statistical
   stability are different criteria, not modes of one untyped comparator.
4. **Evidence and disclosure** preserve the compared identities, provenance,
   projected observations or derived measures, mismatch evidence, limitations,
   and criterion outcome. Reuse experiment evidence/derived-measure/
   traceability carriers and `ValidationBasisDisclosureModel`. A comparator
   result does not replace those carriers or create validation strength by
   itself.

The relation and evidence authority depends on the claim:

| Claim family | Canonical authority and boundary |
| --- | --- |
| Exact artifact or pipeline-output determinism | `canonical-artifact-identity` plus one named canonicalization profile and exact input identity. `canonical_sdl_digest()`, `canonical_instantiated_sdl_digest()`, and `canonical_contract_digest()` are the incumbent canonicalizers for their owning types. Equality across a finite set is a bounded witness, not proof of universal determinism. |
| Replay consistency | Original and replay are distinct admitted run/artifact identities joined by preserved lineage. Compare only the declared observation projection. Use `participant-projected-history-equivalence` for two histories projected for the same named participant and projection revision, `canonical-artifact-identity` for exact canonical artifacts, or another already-defined relation whose full obligations match the projection. A completed replay is not consistency evidence by itself. |
| Stability under controlled variation | Use `ExperimentStudyModel`, factors, allocation, analysis plan, evidence, derived measures, and `statistical-similarity` or `statistical-equivalence`. Population, metric, tolerance/equivalence margin, uncertainty method, sample/stopping rule, and missing-data policy are predeclared. Pairwise equality is not a stability analysis. |
| Strict trace or behavioral equivalence | Use `trace-equivalence` or the narrower governed relation only when its projection, state, trace, scheduler, concurrency, probability, time, and quantifier obligations are actually met. Digest equality and shared seeds are not substitutes. |

`bounded-probe-success` may describe that the finite verifier cases executed.
It does not itself mean determinism, replay consistency, statistical stability,
trace equivalence, or backend equivalence. The default design needs no new
generic repeatability relation: the existing relations intentionally preserve
the distinctions above.

The existing
`implementations/python/tests/test_pipeline_determinism.py` is a valid narrow
exact-output witness for parse -> instantiate -> compile, including
cross-process `PYTHONHASHSEED` variation. It is not the portable ASR-514
comparison contract, and its local serializer must not become a public
canonicalization API or an oracle for runtime, replay, or statistical claims.

The comparison core belongs in `raes_conformance` only when the required join
has no existing subject-specific validator. It should consume already-admitted
typed artifacts and evidence; it must not parse authoring input, schedule
repetitions, replay a run, select a backend, resolve secrets, dispatch commands,
or persist results. A trusted assembler must derive projection, matching,
lineage, reset, cleanup, and evidence facts from their typed authorities.
Caller-supplied booleans or bare digest/evidence-reference strings are not
verification.

The ASR-513 `necessity_evidence` path is the incumbent pattern for a
digest-pinned validator authority, typed run/evidence joins, assembler-owned
facts, stable diagnostics, and an internal comparison result. Reuse that
discipline, not its causal concepts. Do not route ASR-514 through
`BoundedButForCase`, `NecessityMatchingPolicy`, intervention records, or
necessity outcomes. If producer/validator binding and verification-record
identity are byte-for-byte common, promote those neutral primitives once
rather than copying them; necessity-specific and repeatability-specific facts
remain separate.

## Canonical incumbents

| Concern | Canonical incumbent and required reuse |
| --- | --- |
| Validation taxonomy and disclosure | ADR-072, `validation-profile-catalog-v1.json`, `select_validation_profile()`, `ValidationBasisDisclosureModel`, gate-result rows, evidence/diagnostic refs, and explicit limitations. A supported ASR-514 result may support existing behavioral/evidence gate rows; it does not require a second profile loader or strength taxonomy. |
| Claim meaning | ADR-081, `behavioral-relations-v1.json`, `BehavioralClaimBindingModel`, and `validate_behavioral_claim_binding()`. Use the relation matching the comparison criterion; do not weaken catalog-revision or carrier checks. |
| SDL identity and lifecycle | `parse_sdl()`, `parse_sdl_file()`, safe source normalization, module trust/composition, `SemanticValidator`, `instantiate_scenario()`, post-instantiation admission, `canonical_sdl_digest()`, and `canonical_instantiated_sdl_digest()`. |
| Contract canonicalization | `ContractModel(extra="forbid")`, `model_dump(mode="json")`, the shared RFC 8785/JCS canonicalization path, and `canonical_contract_digest()`. Do not use `repr`, object identity, host paths, insertion-order text, broad field scrubbing, or `default=str` as portable identity. If a non-`ContractModel` internal case needs canonical JSON identity, expose/reuse the existing neutral JCS helper through a policy-compliant public boundary instead of copying another `json.dumps`/`hashlib` serializer. |
| Repeated runs and studies | ADR-068; `ExperimentTaskModel`, `ExperimentRunModel`, `ExperimentStudyModel`, membership, factors, condition assignments, `ExperimentRunAllocationPlanModel`, `ExperimentAnalysisPlanModel`, `validate_experiment_run_against_task()`, and `validate_experiment_study_against_tasks_and_runs()`. |
| Randomness and time | ADR-084; executable stochastic controls, random-stream profiles/addresses/draw records, `ExperimentRunModel` stochastic draw/control validation, study common-random-number consistency checks, `TimeModelDeclarationModel`, `RealizedTimeModelProvenanceModel`, and `validate_realized_time_model()`. A seed alone is insufficient. |
| Reset, cleanup, and isolation | `TrialCleanupPlanModel`, `TrialCleanupReceiptModel`, `validate_trial_cleanup_receipt()`, `SchedulerIsolationProofModel`, backend `CleanupCapabilities`, `require_cleanup_plan_capability()`, and time/participant coordinated-reset capability admission. These authorities decide whether state-bearing repetitions are comparable; a comparator must not replace them with a `cleanup_verified` or `isolated` caller Boolean. |
| Per-run execution | ASR-512 `BehavioralProbeCase` and trusted injected executor where a subject needs a bounded behavioral probe; existing conformance fixture/target runners and realization harnesses otherwise. Per-run probe success is input evidence, not the cross-run conclusion. |
| Evidence and analysis | `ExperimentEvidenceRecordModel`, `ExperimentDerivedMeasureModel`, `ExperimentRunTraceabilityModel`, result summaries, realized-form/augmentation disclosures, capture specs, source evidence refs, redaction/loss disclosure, and claim refs grounded by derived measures. |
| Diagnostics and errors | `Diagnostic`, `DiagnosticModel`, `Severity`, namespaced stable codes, `sanitized_failure_message()`, existing SDL/Pydantic errors at their owning boundaries, operation envelopes, and the redacted HTTP 500 handler. Add no ASR-514 exception hierarchy or logger. |
| Artifact persistence | Existing operations-owned artifacts use their artifact-specific validation/redaction gate plus `run_artifact_path()`, `portable_artifact_ref()`, and `atomic_write_json_artifact()`. `redaction_violations()` is the incumbent for the existing evidence-run artifact family, not a general secret classifier for a new carrier. Live state remains in typed runtime snapshots and `ControlPlaneStore`; archival claims remain in experiment/evidence/disclosure artifacts. |
| Existing deterministic witnesses | `test_pipeline_determinism.py` covers the SDL parse/instantiate/compile path; `test_random_stream_determinism.py` covers schedule, partition, thread, process, and hash-seed invariance; random-stream vector tests cover the published cross-language profile. Reuse their fixture and fixed-argv techniques where applicable, but do not promote their local serializers into portable identity. |
| Workflow governance | `.ground-control.yaml`, `.gc/plan-rules.md`, ADR-014, `noxfile.py`, `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`, and `tools/verify_all.py`. Tests under the existing marker taxonomy are already discovered by the canonical `verify` graph; do not add a second workflow or nox path unless a genuinely new external-runtime class cannot use an incumbent session. |

There is no controller, repository, mutable registry, replay scheduler, or
generic environment binder in the default design. There is also no need for a
portable `repeatability-report`, `determinism-result`, `replay-result`, or
`stability-result` root schema. Existing run/study/evidence/derived-measure/
claim/disclosure carriers already own durable facts. A small frozen internal
case/result seam is justified only for the executable join that has no portable
home.

## Cross-cutting validation, security, and operational layers

1. **SDL source, parser, and phase admission.** Compared scenario artifacts
   pass the bounded safe YAML loader, duplicate-key/source-profile checks,
   closed SDL shapes, module trust/composition rules, instantiation,
   unresolved-token rejection, and post-instantiation `SemanticValidator`.
   Parsing, schema generation, documentation, and MCP inspection stay inert.
2. **Claim and reference shape.** Resolve one exact catalog revision, relation,
   subject/carrier pair, projection revision, quantifier/evidence scope, and
   explicit nonclaims. Resolve every artifact/run/study reference by stable id,
   version, and digest where the owning type supports one. Paths, test names,
   tags, object ids, or prose are not claim identity.
3. **Repetition and matching admission.** Compared executions use distinct run
   identities, compatible task/scenario lineage, and one declared policy for
   held-fixed and deliberately varied dimensions. Validate apparatus,
   participant implementation, parameters, scheduler/order, time, randomness,
   observation, augmentation, reset, cleanup, and residual-state facts through
   their owners. Ambient similarity is not verification.
4. **Contract and schema shape.** Portable changes use closed
   `ContractModel` shapes, existing primitive/reference types, schema versions,
   and `x-raes-invariants` for cross-artifact rules. Keep generated and
   published schemas identical and update the publication ledger, fixtures,
   registry, and conformance checks together. Internal dataclasses and test
   serializers are not published contracts.
5. **Profile, capability, and apparatus admission.** Resolve the exact
   validation profile with `select_validation_profile()`. Resolve processor,
   backend, observation, evaluation, time, isolation, reset, cleanup, and
   participant capability through existing manifests/profiles and admission
   helpers. Comparator adapters use the existing injected-adapter pattern and
   exact required-capability refs; there is no generic comparison capability in
   the backend manifest to assume or add by default. Unsupported support remains
   explicit. Neither a profile nor a capability grants execution or evidence
   access.
6. **Configuration and environment shape.** The comparison core reads no
   ambient environment and adds no executable path, plugin root, profile root,
   remote registry, credential, or generic config mapping. Repeated runs retain
   typed experiment parameters and apparatus context. Concrete backends retain
   their closed config checks; libvirt keeps `_validate_config_keys`, driver
   mode/manifest/envelope agreement, and safe connection handling. Environment
   dumps are neither held-fixed evidence nor replay context.
7. **Executable artifact and supply-chain gate.** Any script, package, image,
   probe, or external analyzer used to produce repetitions is untrusted
   apparatus. Reuse pinned digests, declared trust policy, allowlists, source
   limits, and `ImageTrustPolicy` where applicable. Claim/profile/comparison
   data must not choose imports, Python callables, shell commands, executable
   URLs, images, guest commands, or backend dispatch.
8. **Authentication and authorization.** Prefer an in-process conformance
   composition root; ASR-514 needs no new route. If execution or evidence access
   crosses HTTP, use `create_control_plane_app()` and
   `ControlPlaneSecurityConfig.strict_defaults()`: verified identity,
   target-bound roles, participant controller/audience bindings, request-size
   guards, idempotency keys, request fingerprints, and append-only
   `AuditEvent`s remain mandatory. Claim authorship, replay permission,
   execution capability, and evidence-read authority are distinct.
9. **Secrets and information boundaries.** Secrets, hidden answers, prompts,
   raw environment values, credentials, and sensitive entropy never enter a
   comparison key, variation label, projection digest, claim text, fixture,
   diagnostic, argv item, log, or public evidence payload. Use governed
   references at authorized late-bound sinks. Preserve evidence sensitivity,
   redaction, withholding, loss, participant visibility, and audience rules.
   A public result cannot borrow strength from a stronger hidden comparison.
10. **OS and host exposure.** The comparison core performs no subprocess,
    network, daemon, or privileged operation. A concrete adapter uses the
    existing injected-runner pattern: fixed argv, `shell=False`, controlled
    cwd/environment, bounded time/output/resources, least privilege, and owned
    cleanup. Tokens, raw scenario/evidence bodies, connection URIs, host paths,
    seeds/entropy, native object dumps, and hidden assets never enter argv or
    child output. Reuse the OCI fixed-argv/redacted-output boundary and
    credential-free libvirt fact channels; do not add a general guest runner.
11. **Observation and evidence admission.** Compare fresh, addressed,
    subject-bound observations under the same named projection revision.
    Resolve each observation/derived value through the exact run traceability
    and evidence record. Capture intent is not capture; raw evidence is not a
    derived measure; a log is not portable evidence; participant-visible state
    is not hidden truth. Redaction or loss can make the result inconclusive.
12. **Error envelopes and observability.** Failures expose stable codes, safe
    addresses, coarse outcomes, counts, and short fixed messages. Use
    `sanitized_failure_message()` rather than `str(exc)` for untrusted inputs.
    Any diagnostic that may become a `DiagnosticModel` must satisfy its closed
    shape: lower-case namespaced code/domain, a JSON Pointer `address` (not a
    dotted internal label or raw caller id), and the 512-character message
    bound.
    Never expose rejected bodies, compared values, mismatch payloads, commands,
    stdout/stderr, environment, evidence content, native objects, or traces.
    Logs and audit events may summarize lifecycle activity; they are not
    repeatability evidence.
13. **Persistence, reset, and cleanup.** Never mutate one run into a replay or
    replicate. Every executed repetition has immutable run/evidence identity.
    State-bearing comparisons require the declared reset boundary, independent
    cleanup verification, and no residual owned state. Validate and redact
    before `atomic_write_json_artifact()`. Runtime snapshots, operation
    details, audit blobs, tags, and logs are not the archival claim record.
14. **Repository and package boundary.** SDL meaning stays in `raes`; portable
    DTOs in `raes_contracts`; compilation/admission in `raes_processor`; live
    control/security/storage in `raes_runtime`; capabilities in
    `raes_backend_protocols`; concrete execution in adapters; comparison and
    conformance flow in `raes_conformance`; artifact assembly/writes in
    `raes_operations`; and user wiring in `raes_cli`. Keep module policy and
    source-size limits intact; do not use private imports, compatibility
    wrappers, or `Any` bags to evade ownership.

## Outcome and concept separation

| Surface | Question answered |
| --- | --- |
| Exact canonical comparison | Are the named projected artifacts byte/digest-identical under one canonicalization revision? |
| Replay-consistency comparison | Does the replay match the original under the declared observation relation and projection? |
| Statistical stability result | Does the preregistered metric satisfy the stated tolerance/equivalence criterion for the sampled population? |
| Per-run probe outcome | Did one bounded apparatus invocation execute and meet its case oracle? |
| Proposition truth outcome | What is the governed truth/support result for one proposition in one run? |
| Validation gate outcome | Did one ASR-515 gate pass, fail, remain partial/not-run/unknown/unsupported/withheld, or not apply? |
| Operation/workflow status | Did apparatus work progress or complete? |
| ADR-021 evidence status | What is the falsification-protocol status: `untested`, `partial`, `demonstrated`, or `refuted`? |

Mappings are explicit. A mismatch may refute one exact bounded determinism or
replay-consistency claim after identity, projection, matching, and evidence
gates pass. Missing, stale, withheld, lossy, unsupported, incomparable, or
cleanup-invalid evidence is inconclusive or unsupported, not a match or
mismatch. A stable sample does not prove deterministic execution; exact equality
does not establish statistical stability, trace equivalence, backend
equivalence, or falsification-backed strength.

## Extensibility seam

The stable seam is a subject-bound, immutable comparison case supplied by
trusted code to a criterion-specific, capability-checked comparator. It binds:

- exact revisioned claim and subject/carrier identities;
- comparison family and criterion id/version;
- observation projection and canonicalization/metric revision;
- immutable original/baseline and repetition artifact/run identities, digests,
  and lineage;
- controlled-variation/matching policy with held-fixed and deliberately varied
  dimensions;
- replicate/sample identity, minimum count or stopping rule, and canonical
  input digest;
- scheduler/concurrency, time, random-stream, participant, apparatus,
  augmentation, reset, cleanup, and missing-data policies where relevant;
- digest-pinned producer/validator authority and required capabilities; and
- evidence, derived-measure, diagnostic, limitation, audience, redaction,
  profile, and disclosure refs.

Future variations add one governed criterion/projection adapter at this seam.
Examples include a new canonical projection, an allowed jitter tolerance, a
participant-history replay, a different scheduler perturbation, or a
preregistered statistical criterion. They must not require a new claim
registry, scenario lifecycle, trial identity, evidence graph, report root,
exception tree, logger, store, auth route, subprocess framework, or CI
workflow.

## Whole-repository scope

- **Normative authority:** ADR-066/068/072/081/084; behavioral relations;
  validation profiles; experiment, evidence, time, random-stream, participant,
  workflow, and replay-claim specifications; and every changed catalog, schema,
  fixture, profile, publication record, and assurance mapping.
- **Implementation authority:** SDL parse/validate/instantiate/canonicalize;
  contract canonicalization; task/run/study/allocation/analysis/evidence/
  traceability/disclosure contracts; random streams and time models;
  cleanup plans/receipts and scheduler-isolation proofs; behavioral probes;
  conformance harnesses; manifests/capabilities; runtime auth/audit/store/reset;
  adapters; artifact-family redaction; artifact writes; and CLI wiring only if
  a user command is explicitly in scope.
- **Verification authority:** positive and single-defect negative cases for
  claim/ref/digest/criterion/projection admission; distinct run identity;
  stale or cross-run evidence; held-fixed and deliberately varied dimensions;
  hash seed, ordering, scheduling, concurrency, time, random stream, reset,
  retry, redaction, missing-data, mismatch, cleanup, residue, capability, auth,
  argv, and exception leakage; plus schema, authority, module, claim, and
  repository-policy gates.
- **Workflow authority:** `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, and `tools/verify_all.py`.
  `RAES_REQUIREMENT_UID=ASR-514` is required for governance commands on this
  branch.

## Gotchas and anti-patterns

Avoid:

- a generic `repeatable`, `stable`, `deterministic`, `replay_passed`, or
  `consistent` Boolean without a claim, projection, variation policy,
  criterion, sample boundary, and evidence;
- treating same seed, task id, scenario name, backend name, wall-clock
  proximity, exit code, response status, run status, retry, or operation id as
  equivalent inputs or outputs;
- calling two equal outputs universal determinism, or calling one unequal pair
  instability without first proving comparable inputs and projections;
- treating exact digest equality as trace, participant-history, behavioral,
  statistical, or backend equivalence;
- putting the canonicalization/projection id in a relation carrier field,
  treating a binary catalog relation as an n-ary cohort relation, or giving an
  exact-equality-only comparator a generic stability/statistics name;
- sorting away semantically ordered lists, dropping all time-like keys, or
  excluding volatile fields without naming their producer and exclusion
  rationale;
- promoting the local `test_pipeline_determinism.py` serializer into a public
  contract or copying it into production comparators;
- reusing one run id for multiple executions, reconstructing a replay from
  mutable live state, or changing the comparison policy after seeing results;
- accepting projection/matching/reset/cleanup success, output digests, metrics,
  or evidence refs as caller assertions rather than resolving typed
  producer/validator output through exact run/evidence joins;
- using a necessity world/intervention type, proposition truth, validation gate
  outcome, probe outcome, operation status, or ADR-021 evidence status as the
  repeatability result;
- adding a generic replay record, repeatability report, determinism schema,
  comparison graph, evidence store, runtime snapshot metadata bag, exception
  hierarchy, logger, registry, or workflow;
- executable code, commands, imports, URLs, paths, dynamic plugins, or dispatch
  tables in claim/profile/criterion data;
- arbitrary dictionaries such as `repeatability_metadata`,
  `comparison_config`, `replay_context`, `stability_metrics`, or
  `ignored_fields`;
- selecting a comparator, executor, path, profile, projection, target, or
  fallback criterion from untrusted data;
- emitting dotted or caller-derived diagnostic addresses that later fail or
  leak through the closed `DiagnosticModel` JSON Pointer boundary;
- raw evidence in disclosures or derived measures, logs/snapshots as archival
  evidence, public strength borrowed from hidden evidence, or missing/withheld
  data silently discarded; and
- `shell=True`, open child environments, unbounded output/time/resources,
  secrets or raw payloads in argv, unsanitized `str(exc)`, unverified cleanup,
  or ignored residual state.

## Non-goals and implementation boundaries

- This preflight does not implement issue #262 or choose final field/class
  names.
- It does not add a runtime replay engine, scheduler, worker, artifact
  retrieval/retention service, environment snapshotter, generic comparison
  service, statistics engine, model checker, theorem prover, or query language.
- It does not redesign SDL parsing/canonicalization, experiment runs/studies,
  random streams, time, behavioral relations, profiles/disclosures, evidence,
  conformance, authentication, redaction, persistence, reset, or cleanup.
- It does not guarantee exact environmental recreation, external artifact
  availability, deterministic participant or backend behavior, universal trace
  equivalence, backend equivalence, statistical generalization, experiment
  validity, proof, or falsification-backed strength.
- It adds no API, MCP tool, UI, database, mutable registry, remote plugin
  system, credential broker, command endpoint, general guest execution channel,
  or authoring-time side effect.
- Unsupported comparison families or insufficiently evidenced claims remain
  explicit. The implementation must not weaken the claim, substitute a nearby
  relation/criterion, silently canonicalize a mismatch away, or invent a
  default projection/variation policy to make verification pass.
