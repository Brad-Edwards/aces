# Issue 965 participant opacity backend realization preflight

Date: 2026-08-01

Issue: #965.

Requirements: `SEM-231`, `API-407`, `ASR-535`.

This note records repository-wide architecture guardrails for declaring and
falsifying backend support for the bounded participant-opacity profile. It is
guidance only. It does not add a feature term, contract, probe, backend
behavior, evidence, or assurance claim, and it is not an implementation plan.

No new ADR is required. ADR-060 already owns API-407 participant feature
support, ADR-081 owns behavioral claims, and ADR-099 owns participant-relative
predicate opacity and its independent assurance axes.

## Decisive current-state finding

Issue #965 belongs at the composition of three existing seams, not in a new
opacity subsystem:

- `ParticipantFeatureSupport`, the governed participant-runtime vocabularies,
  `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`, and
  `resolve_participant_feature_support()` own declaration, strength, required
  contracts, evidence, limitations, disclosures, and authorized downgrade.
- `participant-opacity-runtime-reference-v1`,
  `ParticipantOpacityRuntimeSupportModel`, and
  `validate_participant_opacity_runtime_enforcement()` own the exact supported
  SEM-231 profile, carrier/materializer, observer, predicate reference,
  observation inventory, rule, and finite runtime-enforcement join.
- `run_target_conformance()`, `ConformanceCaseResult`,
  `BackendConformanceReport`, `BehavioralClaimBindingModel`, and the report
  validator/serializer own finite target evidence and claim honesty.

The missing distinction is orthogonal to the existing execution basis:

```text
execution basis: fixture-only | hermetic-live | native-live
realization owner: declaration-only | runtime-mediated | backend-native
```

`native-live` currently describes an execution substrate. It does not prove
that opacity was realized by backend-owned behavior. Conversely, an in-process
reference backend can execute backend-owned code without a native daemon. The
report must therefore retain a separate realization-owner coordinate; target
name, method presence, backend invocation, or `native_conformance=True` cannot
stand in for it.

A positive backend-native result must be sensitive to backend behavior: an
adversarial backend that leaks or fabricates the same case must fail while the
runtime configuration is held fixed. If replacing the backend with a no-op or
dishonest implementation leaves every case passing because RUN-319 refused or
normalized the observation first, the evidence establishes runtime mediation
only. ADR-099 consequently forbids a positive `backend-conformance` opacity
claim until the exact profile has at least partial backend realization.

## Architecture decisions and guardrails

### Extend API-407 once, without turning opacity into policy

Use one governed participant-runtime behavior feature for the relation family,
`participant_predicate_opacity`. The feature id is a capability selector, not
the secret, observer, profile, relation definition, or assurance result. Exact
support remains bounded by the referenced SEM-231 profile and claim bindings.

Do not add opacity to `PARTICIPANT_RUNTIME_POLICY_FEATURES`: opacity is a
relation assurance concern, not a participant policy operation. Keep policy
membership separate from the incumbent rule that selected features require an
explicit declaration, evidence, limitations, disclosures, and fail-closed
admission. Generalize that evidence-required predicate once or add a distinct
relation-feature set in manifest authority; do not fork `ParticipantFeatureSupport`
or its Pydantic/dataclass validators.

The canonical term-level minimum contract set remains
`PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`. It must cover every
portable carrier actually used by the named profile's mediated positive and
adversarial cases. For the #964 reference profile that closure includes the
incumbent operation receipt/status, runtime snapshot, participant episode
state/history, participant behavior history, participant control occurrence,
participant crossing occurrence, and participant observation contracts. Exact
profile coverage is still resolved from the shared runtime support binding and
concrete observation inventory. Do not copy that inventory into the manifest,
infer support from the full backend contract list, or create an
opacity-specific backend profile under `contracts/profiles/backend/`.

Below-exact or authorized weakening uses the existing support-level,
constraint, limitation, disclosure, policy-ref, and provenance-ref rules. A
weakening removes the stronger opacity claim; it never changes SEM-231 meaning,
edits a prior result, or turns a runtime-mediated result into backend-native
realization.

### Reuse the exact runtime profile and shared claim model

Backend artifacts reference the exact catalog/profile and the compact safe
coordinates already admitted by #964. They do not restate the predicate body,
possible points, observer memory, policy/supervisor implementation, alternative
worlds, observation semantics, or relation formula.

Use three independently validated `BehavioralClaimBindingModel` values:

- `backend-declaration/declared/structural` for the exact manifest feature
  entry;
- `backend-realization/realized` with `structural` or `finite` scope for
  backend-owned implementation evidence; and
- `backend-conformance/conformant/finite` for the named executed cases.

All three must join to the same catalog revision, relation, profile id/revision,
carrier, observation projection, backend implementation/configuration identity,
and safe evidence lineage. A declaration does not imply realization; a
realization does not imply conformance; a conformance run cannot manufacture a
missing declaration or realization.

The report-level relation remains `bounded-probe-success`. The SEM-231 axis
bindings describe the obligation and assurance lane within the report; they do
not promote the finite report itself to universal predicate opacity. Keep the
finite quantifier, limitations, failed/unsupported cases, and nonclaims visible.

Do not overload the SEM-230-specific `ParticipantPolicyBinding` or add an
opacity-local claim class. If the current case shape cannot carry the three
bindings, extend the existing report family with the smallest generic
collection of incumbent claim bindings plus exact relation-profile and
backend/tool/environment digests. Do not reuse `envelope_digest` for a relation
profile or hide required coordinates in case names and prose.

### Keep one backend-neutral conformance runner

The extension seam is `_TargetConformanceOptions` and an injected, typed,
in-process probe harness, following the ASR-535 participant-policy and ASR-519
realization-honesty patterns. The harness supplies exact profile-bound inputs,
safe case labels, expected observations, and a deterministic probe-set digest.
The runner constructs or invokes the target, observes effects, and owns the
verdict. A harness must not return a pass boolean, prebuilt report, claimed
observation, arbitrary callable/module path, or backend-private object.

Backend-specific setup and observation stay behind that structural harness.
`raes_conformance` remains backend-neutral and must not import the reference or
libvirt backend. A conformance-owned direct backend probe may establish a
backend-native owner, but it is not a new public participant route and does not
change #964's runtime reachability inventory. Production dishonest modes,
backend-name dispatch, monkeypatching the gate under test, and a second runner
are prohibited.

The finite matrix must compare secret and nonsecret cases under the same
profile and active strategy, and must observe the complete declared transcript,
not payload alone. At minimum it preserves distinct checks for decisions and
failures, action availability, delivery and governed omission opportunities,
retry/replay, logical order and timing buckets, policy/release effects, and
participant-visible external effects. Omission requires the profile's explicit
opportunity basis. Untimed support uses governed logical buckets; sleeps,
ambient wall time, jitter, or randomized response are not opacity evidence.

### Validate and finalize one report before persistence

`validate_backend_conformance_report()` remains the cross-field honesty seam.
It validates every nested claim against the catalog and profile. It requires
each cited case to be present. It also binds exact backend, manifest, profile,
tool, environment, and probe-set digests. It rejects axis mismatches and
enforces this progression:

```text
declared -> at least partially backend-realized -> finitely conformant
```

Failed, unsupported, skipped, weakened, and counterexample cases remain in the
claim boundary. A declared profile that was not exercised is non-passing.
Runtime-mediated and backend-native cases remain separately labelled even when
both appear in one report.

Reports carry allowlisted safe refs, digests of already nonsecret canonical
material, bounded counts, result codes, limitations, and sanitized
counterexample refs. Hashing a secret value, raw witness, policy body, memory,
environment dump, or backend object does not make it safe metadata.

## Canonical incumbents to reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Opacity authority | ADR-099, `participant-predicate-opacity.md`, the current/historical behavioral catalog, and `participant-opacity-runtime-reference-v1`; reference exact revisions instead of redefining semantics. |
| Profile/runtime binding | `BehavioralRelationProfileModel`, exact-revision loaders, `ParticipantOpacityRuntimeSupportModel`, `ParticipantOpacityRuntimeEnforcementBindingModel`, and `validate_participant_opacity_runtime_enforcement()`. |
| API-407 declaration | `ParticipantFeatureSupport` and `ParticipantFeatureSupportModel`, participant feature vocabularies, canonical required-contract map, manifest dataclass/model parity, and `resolve_participant_feature_support()`. |
| Claims | `BehavioralClaimBindingModel`, `validate_behavioral_claim_binding()`, ADR-081 assurance rules, and the behavioral-claim policy checker. |
| Conformance | `run_fixture_suite()`, `run_target_conformance()`, `_TargetConformanceOptions`, `ConformanceCaseResult`, `BackendConformanceReport`, `_bounded_conformance_claim()`, and `validate_backend_conformance_report()`. |
| Runtime boundary | `RuntimeControlPlane`, `RuntimeTarget`, RUN-319 crossing mediation, API-423 occurrences, participant controller/audience binding, operation records, and backend-call accounting. |
| Diagnostics | `Diagnostic`, `Severity`, stable `conformance.*` codes, and `sanitized_failure_message()`; expected failures are values, not a new exception hierarchy. |
| Persistence | `backend_conformance_report_payload()`, `redaction_violations()`, `write_backend_conformance_report()`, `run_artifact_path()`, and `atomic_write_json_artifact()`. No new store or ledger. |
| Publication | `ContractModel(extra="forbid")`, `schema_bundle()`, hand-governed schemas, valid/invalid fixtures, publication entries/hashes, packaged-corpus parity, and compatibility gates. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, canonical nox sessions, repo policy, requirement governance, schema/concept/claim checks, and `tools/verify_all.py` with `RAES_REQUIREMENT_UID=SEM-231` on this issue-number branch. |

## Cross-cutting layers and security posture

1. **Manifest/config shape.** External manifests retain the existing bounded
   `--manifest` file path, UTF-8 JSON-object parse,
   `BackendManifestV2Model.model_validate()`, and
   `backend_manifest_from_v2_model()` reconstruction; native factories produce
   the same typed manifest and canonical projection. The dataclass validators,
   published schema, governed feature vocabulary, required-contract map, and
   concept bindings all still apply. No opacity fragment, boolean,
   environment-variable bundle, or unvalidated mapping bypasses those layers.
   Exact profile ids resolve through grammar-checked, root-confined corpus
   loaders with pinned revision and digest; no `latest`, caller-selected root,
   path, URL, open metadata, or environment-selected profile is admitted.
2. **Relation/profile join.** Each axis binding passes
   `validate_behavioral_claim_binding()` against the exact catalog and profile.
   The separate #964 runtime-support binding passes
   `validate_participant_opacity_runtime_enforcement()` before it is cited as
   prerequisite evidence; backend-axis claims are not relabeled runtime
   bindings. Profile, predicate ref, carrier/materializer, observer/audience,
   inventory, projection, memory, release, order, opportunity, rule, and
   evidence coordinates agree. Shape validity or a non-empty ref is
   insufficient.
3. **Authentication and authority.** In-process conformance makes no HTTP-auth
   claim, but runtime-mediated cases still use `ControlPlaneIdentity`, exact
   target role, controller/audience binding, deny-first policy, and API-407
   admission. If an existing HTTP path is exercised it retains
   `ControlPlaneSecurityConfig.strict_defaults()`,
   `request_size_guard_response()`, `_ControlPlaneApiAuth`, role/target checks,
   and separate participant controller/audience subject bindings. A direct
   backend probe is a trusted test-composition boundary, not an unauthenticated
   endpoint or participant authority bypass. Caller/backend authorization does
   not establish observer membership, visibility, declassification, or
   opacity.
4. **Runtime/backend boundary.** Runtime refusal, normalization, durable
   crossing evidence, backend invocation, backend-owned observation, and
   participant-visible serialization are recorded separately. A positive
   backend-native case proves backend code was causally exercised and that an
   adversarial backend is detectable; method presence or an uncalled adapter
   fails this gate.
5. **Observation completeness.** Cases cover every enabled observable channel
   retained by the exact profile, including occurrence/content, errors,
   omissions, retry, order, logical timing, release/policy changes, and external
   effects. Unknown, reachable-unmediated, stale, or unsupported channels fail
   or remove the claim; payload redaction alone never passes.
6. **Report validation and error envelope.** The existing report finalizer
   validates claim/case/axis consistency before serialization. Expected
   backend, Pydantic, file, or harness failures pass through
   `sanitized_failure_message()` and stable bounded `Diagnostic` codes and
   messages. Unexpected HTTP failures retain exactly
   `{"detail":"internal server error"}` with only safe class/code and
   correlation data in authorized audit. Never emit `str(exc)`, rejected input,
   host paths, target internals, policy/gate inventory, backend error text,
   tracebacks, stdout/stderr, or participant existence details. Status and
   logical timing remain profile observations even when content is redacted.
   Expected refusals use uniform, value-independent status and detail behavior
   for protected existence.
7. **Runtime persistence and ordering.** Runtime-mediated cases reuse
   `RuntimeSnapshot`, operation records, audit, append-only API-423 histories,
   `ControlPlaneStore.commit_participant_transition()`, expected history heads,
   idempotency, restart validation, and conflict behavior. A native side effect
   that cannot be reconciled with durable finalization is outside the positive
   claim. No harness or report becomes a second runtime state store.
8. **Report persistence/redaction.** The validated report is projected once,
   passed through the shared redaction gate, root-confined by safe run id, and
   written atomically. API-423/runtime state remains in incumbent stores and is
   cited by safe ref; no opacity report database, raw transcript, witness
   archive, or duplicate audit stream is added.
9. **Secrets and OS/process exposure.** The reference path is typed and
   in-process. Secret values, predicate bodies/results, worlds, memories,
   policy/supervisor bodies, credentials, tokens, raw observations, and full
   environment/configuration never enter CLI arguments, process argv,
   environment variables, filenames, shell history, logs, diagnostics,
   reports, or test ids. Environment digests are computed from an explicit
   nonsecret allowlist, not from `os.environ` or an environment dump. No new
   subprocess, socket, daemon, privilege, or host-file dependency is justified.
10. **Schema/concept governance.** Any portable field or feature-term change
   moves with the current and historical concept authority, schema, fixture,
   publication-manifest hash, generated bundle, package exports, report
   consumers, and compatibility review. Historical #961-#964 evidence retains
   its original taxonomy/profile coordinates.

## Whole-repository surfaces in scope

- **Authority:** ADR-060/081/099, SEM-231 formal semantics, current and
  historical behavioral catalogs, controlled vocabularies, relation profiles,
  assurance aggregates, and claim validation.
- **Contracts/manifests:** backend manifest dataclass and Pydantic projections,
  participant feature support, required-contract mapping, API-423 opacity
  bindings, schemas, fixtures, publication records, and packaged corpus.
- **Runtime/backend:** reference target manifest and participant runtime,
  runtime opacity support, crossing resolver/mediation, backend calls,
  operation/audit evidence, and exact participant-visible observation paths.
- **Conformance/operations:** target options, injected harness boundary, case
  and report projection/validation, diagnostic sanitizer, redaction gate,
  root-confined atomic writer, and adversarial test fixtures.
- **Host/workflow:** in-process reference execution, no ambient secrets or new
  OS services, repository policy, requirement governance, schema/concept/claim
  checks, traceability, and full verification.

## Extensibility seam

The stable seam is:

```text
API-407 family feature + exact support strength
  -> SEM-231 catalog/profile + #964 safe runtime support binding
     -> realization owner + backend/config/tool/environment identity
        -> injected finite case policy and independent observation
           -> three axis-specific shared claim bindings
              -> one validated backend conformance report
```

It is parameterized by profile id, revision, and digest. It also binds backend
implementation, configuration digest, realization owner, execution basis, and
observer or audience. The remaining parameters are the finite case/probe-set
digest, tool/observer version, and evidence refs.

A second supported profile, backend, observer, strategy set, or logical
opportunity class changes those values and its typed case policy. It does not
add a feature boolean, backend-name branch, report family, claim type, or
relation copy.

Timed, quantitative, probabilistic, progress-sensitive, coalition, or
partial-order opacity does not fit by changing a string. It requires the
corresponding governed relation/profile and independent evidence.

## Gotchas and anti-patterns

Avoid:

- treating `participant_predicate_opacity` as a policy operation or copying it
  into `PARTICIPANT_RUNTIME_POLICY_FEATURES`;
- copying the runtime observation inventory, secret predicate, observer model,
  possible worlds, relation formula, or policy body into a manifest/report;
- inferring support from a boolean, feature list membership, method presence,
  importability, contract-list breadth, or a green schema round trip;
- using `ParticipantPolicyBinding`, `envelope_digest`, `native-live`, or
  `native_conformance` to mean backend-owned opacity realization;
- passing backend conformance when only RUN-319 was exercised, when the backend
  was never called, or when an adversarial backend is masked by runtime denial;
- treating one equal projected history, payload-redaction pair, randomized
  result, hidden supervisor body, or finite probe set as predicate opacity;
- omitting supervisor decisions, failure/status shape, observable silence,
  retry, timing, order, release/policy effects, or external behavior from the
  observed transcript;
- comparing active actual and alternative cases under different strategies,
  treating reset/revocation as forgetting, or treating delivery as observation;
- silently skipping an unexercised declaration, filtering failed/unsupported
  cases, or retaining a strong claim after authorized weakening;
- adding an opacity backend profile, runner, report/schema, claim DTO, registry,
  gateway, public probe endpoint, policy engine, store, exception hierarchy,
  logger, environment-variable bundle, or workflow;
- exposing raw exception text, rejected values, secrets or secret-derived
  digests, raw witnesses/transcripts, policy/memory/backend objects, host paths,
  credentials, headers, environment dumps, or tracebacks; and
- advancing only the Python model, only the schema, only the current catalog,
  or only a reference manifest while leaving historical resolution, fixtures,
  publication hashes, serializers, stub/reference expectations, and report
  validators inconsistent.

## Non-goals and implementation boundary

Issue #965 may add one governed API-407 opacity family feature. It may declare
bounded support for exact profiles and record backend-owned realization
evidence. It may also add finite adversarial cases and separate axis claim
bindings in the existing report family.

It does not:

- redefine SEM-231, add a secret language, copy or widen the #964 profile, or
  claim unnamed profile support;
- establish universal backend opacity, proof, model checking, cross-backend
  equivalence, timed/quantitative/probabilistic opacity, or behavior outside the
  named backend/profile/tool/environment/cases;
- make runtime mediation backend-native, make declaration conformance, or make
  finite conformance mathematical proof;
- expose a participant-facing direct backend path, add authentication/config
  surfaces, persist raw secret-capable evidence, or require a daemon/network/
  privileged host integration; or
- claim policy noninterference, projected-history equality, epistemic
  indistinguishability, trace inclusion/equivalence, simulation, refinement,
  strong/weak/branching bisimulation, erasure, differential privacy, or a
  quantitative leakage bound.
