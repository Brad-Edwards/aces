# Issue #961 — Participant Opacity Profiles And Bounded Falsification Preflight

Date: 2026-07-30

Issue: #961.

Requirements: `SEM-231`, `ASR-535`.

This note records architecture guardrails for the first executable
participant-opacity assurance lane. It is guidance only. It does not publish a
profile or schema, implement a checker, execute a finite model, change catalog
assurance, establish opacity, activate `SEM-231`, or make a model-check, proof,
runtime-enforcement, backend-realization, or backend-conformance claim.

## Decisive Current-State Finding

Issue #961 must complete an existing shared seam, not create an opacity
subsystem.

- ADR-099 and the SEM-231 formal authority already define
  `participant-predicate-opacity`, its possible-point and information-cell
  semantics, active-strategy quantifier, supervisor visibility, release,
  memory, and relation boundaries.
- The behavioral catalog advanced to `raes-behavioral-relations@rev7` with
  this bounded-checker delivery and remains the
  only relation registry. `BehavioralClaimBindingModel` already carries a
  relation-profile ref/revision and assurance axis.
- `validate_behavioral_claim_binding()` currently checks that a required
  profile coordinate is present, but it does not resolve that coordinate to a
  governed profile or validate relation/profile/projection identity. That is
  the contract gap #961 must close.
- `raes_processor.satisfiability` and `raes_processor.exploit_path` already own
  the repository pattern for side-effect-free finite analysis: closed
  normalized inputs and evidence in `raes_contracts`, deterministic
  translation/admission/checking and replay in `raes_processor`, typed
  unsupported outcomes, digest joins, and value-free operational errors.
- `raes_conformance.behavioral_validation` remains the subject/backend
  execution-probe seam. Its trusted-executor, cleanup, and live-execution
  abstractions are useful discipline, but they are not the semantic carrier
  for an exhaustive pure opacity check.
- ASR-535 participant-policy probes, `BackendConformanceReport`, RUN-319, and
  API-407 concern runtime or backend behavior. A pure finite possible-point
  check does not pass those boundaries and must not be reported through them.

The smallest coherent addition is one shared, resolved behavioral-relation
profile contract, one normalized finite opacity input/evidence contract, and
one relation-specific processor analysis service. No new ADR, relation
registry, policy engine, runtime store, backend profile, conformance report,
exception hierarchy, logger, endpoint, or workflow is justified.

## Architecture Decisions And Guardrails

### Publish one shared relation-profile contract

The profile authority belongs under the existing normative `contracts/profiles`
family and the owning model/loader belongs in `raes_contracts`. Use a common
behavioral-relation profile header with a closed, discriminated
relation-specific parameter payload. The first payload variant is
`participant-predicate-opacity`; the next relation, including the
participant-bisimulation work, extends that same discriminated seam rather than
creating another registry.

The common header must bind:

- schema version, profile id, profile revision, relation id, and exact
  behavioral taxonomy coordinates;
- the observation projection ref/revision used by the claim;
- the possible-point carrier kind and finite analysis scope;
- limitations and explicit nonclaims; and
- any safe immutable source refs/digests needed to reproduce profile meaning.

The opacity payload must close, with typed fields or revisioned refs:

- individual observer or coalition, audience, and coalition fusion rule;
- secret-predicate identity/revision and one-sided truth polarity;
- possible-point and reachability carrier;
- initial-information and accumulated-observation functions;
- cut/horizon and retained-memory/reset behavior;
- passive or finite active-strategy domain;
- supervisor visibility and decision-observation posture;
- exact-cut policy and declassification/release schedule;
- scheduler and environment domains;
- nondeterminism support;
- order, concurrency, and partial-order treatment;
- time, progress, opportunity/deadline, and absence treatment; and
- the baseline exclusion of probability measures and quantitative leakage.

Do not encode those coordinates in an open `dict`, an executable expression,
SDL metadata, `subject`, `evidence_boundary`, `limitations`, an opacity-local
enum registry, or a copy of `ParticipantPolicyBinding`. Complex functions are
revisioned references implemented by trusted code or materialized into a
finite model; profile JSON is never an import path, Python expression, remote
URL, or policy program.

Profile identity is exact. A claim's profile ref and revision must resolve to
one artifact whose relation, taxonomy, and observation-projection coordinates
match the claim. There is no `latest` alias, version range, fallback profile,
or consumer-selected partial default.

### Keep profile validation and claim validation as one join

`validate_behavioral_claim_binding()` remains the canonical semantic join. Its
profile-aware path must:

- resolve the profile through the shared canonical loader;
- require ref/id and requested/artifact revision equality;
- require relation id and taxonomy coordinates to agree across catalog,
  profile, and claim;
- require the claim projection pair to equal the profile projection pair; and
- retain the existing quantifier/evidence/assurance-axis checks.

The loader must follow the hardened corpus precedents: validate profile-id
grammar before path construction, resolve through
`corpus_family_root(PROFILES)`, use bounded duplicate-rejecting JSON ingress,
validate a closed `ContractModel`, assert artifact/request identity, and work
identically from a source checkout and packaged corpus. Tests may inject an
explicit trusted profile/catalog object; production validation must not accept
an arbitrary root from the claim.

Cross-reference rules belong in this one semantic validator. Pydantic shape
validators enforce local invariants; conformance, studies, completeness
profiles, policy scripts, and future model checking must not each reimplement
relation/profile resolution.

### Decide only a declared finite possible-point model

The #961 evaluator is a deterministic finite falsifier for the SEM-231 kernel:
for each reachable secret point in the admitted finite carrier, it seeks a
reachable nonsecret point in the same declared information cell. It is not a
runtime monitor and it does not explore an implicit transition system.

Its admitted input must be typed and digest-bound and must declare exact finite
bounds and realized counts for points, states/runs or run refs, cuts,
strategies, schedulers/environments, and order variants used by the profile.
Every point and reference must resolve inside that input. A missing coordinate,
unresolved ref, duplicate id, or digest/count mismatch is rejected at
admission. A valid shape with an unsupported dimension, exceeded deterministic
resource bound, truncated enumeration, or timeout produces a typed unsupported
or operational failure according to the incumbent analyzer boundary; it never
becomes a passing opacity result or durable partial evidence.

Information-cell equality is derived from the profile's initial-information,
observation, memory, coalition, strategy, release, and order coordinates. It
must not be reduced to payload equality or a caller-supplied `same_cell`
boolean. For an active profile, the actual and alternative point use the same
strategy, and all declared finite strategies are checked. For a coalition,
the checker uses the declared fused member observations and memories, not a
representative individual.

Absence is observable only when the profile supplies an opportunity,
deadline, acknowledgement, clock, or progress basis. Declassification may
split a cell and change knowledge; later concealment, revocation, reset,
rollback, or supersession does not remove retained observations unless the
profile contains a trusted memory-reset rule.

A finite carrier with no reachable protected secret point must not be reported
as positive assurance. It is vacuous or inapplicable evidence and needs an
explicit non-passing disposition. Empty or unreachable cells likewise do not
establish opacity.

### Keep the normalized finite input separate from the profile

The profile selects semantics and bounds; it is not a container for one
fixture's possible worlds. A separate closed normalized input represents the
exact finite points admitted under that profile. It may carry only
checker-relevant abstract coordinates: stable safe point/run/strategy refs,
reachability, secret truth labels, initial-information and observation keys,
cut/release/memory coordinates, declared bounds, and exact
source/profile/materializer digests.

The normalized input is a finite projection of the incumbent SEM-230,
participant-view, decision, crossing, delivery, observation, policy-cut,
scheduler, environment, order, and memory carriers. It is not a new
world-state or participant-history model. A trusted materializer constructs
it; the opacity evaluator does not accept raw runtime/backend objects or
invent a second projection policy.

`raes_contracts.bounded_domains` may supply exact, enum, Boolean,
governed-reference, and closed-record value shapes. A
`NumericIntervalDomain` is not by itself enumerable: any numeric range in an
exhaustive profile needs a finite enumeration or a bounded step/cardinality
whose expansion is itself validated and digest-bound.

### Use the processor analysis/evidence/replay pattern

Portable profile, normalized-input, checker-configuration, outcome, and
evidence DTOs belong in `raes_contracts`. Deterministic preflight, evaluation,
canonical counterexample selection, and replay belong in a narrow public
`raes_processor` analysis package, following satisfiability and exploit-path
analysis. The checker is in-process, read-only, and side-effect free.

Reuse the claim-admission, canonical-digest, stable-diagnostic, typed
unsupported, deterministic ordering, and fail-closed disciplines from
behavioral validation and existing processor analyzers. Do not wrap the pure
algorithm in `BehavioralProbeCase`, fake a participant subject or live
execution basis, fork the generic behavioral-probe runner, or project the
result into `BackendConformanceReport`.

The harness supplies only admitted finite inputs and expected fixtures. The
production evaluator derives information cells, checks every admitted point,
and owns the verdict. Counterexample choice follows a declared canonical order
so input permutation and Python hash order cannot change result identity.

### Bind results to exact evidence and an honest claim

Follow `ScenarioSatisfiabilityEvidenceModel` and
`ExploitPathAnalysisEvidenceModel`: one closed evidence envelope is assembled
from admitted inputs and records:

- exact taxonomy, relation, profile, model, and checker ids/revisions/digests;
- declared bounds and realized checked counts;
- deterministic completed relation outcome or typed unsupported outcome;
- a `BehavioralClaimBindingModel` using
  `assurance_axis=bounded-test`, `assurance_status=tested`,
  `evidence_scope=finite`, and `quantifier_scope=finite-cases`;
- limitations and explicit nonclaims; and
- either bounded positive evidence refs or one safe counterexample ref/digest.

The positive outcome is named “no counterexample found within the declared
finite bounds,” not `opaque`, `proved`, `verified`, `model-checked`,
`conformant`, or an unqualified `passed`. The claim's evidence boundary names
only the exact finite model and declared strategy/scheduler/order domain. A
successful exhaustive loop over that artifact is bounded testing. It is not
`model-check`, `proof`,
`runtime-enforcement`, `backend-realization`, or `backend-conformance`, and it
must not use universal claim quantifiers.

Counterexamples use checker-generated safe ordinals/labels, governed refs,
counts, and digests. They do not echo caller-controlled point ids when those
ids may reveal secrets, and they never serialize raw worlds, secret values,
participant memory, policy bodies, supervisor state, observation content,
credentials, backend objects, or rejected input. Hashing secret-bearing
content does not make it safe to publish.

Replay must recompute and compare every source/profile/model/checker/result
join and reject any changed bound, input, profile, materializer/checker
configuration, outcome, count, evidence ref, or counterexample identity. A
replay mismatch is an evidence failure, not a fresh opacity disposition.
Malformed input remains an ingress/operational error and does not produce an
analysis evidence envelope.

The bounded checker authenticates neither a source artifact nor the
materializer that projected it. Those input assertions remain covered by the
normalized-input digest so replay detects changes, but the evidence envelope
does not repeat them as provenance. It declares a
`normalized-input-only` provenance scope and an explicit source/materializer
authenticity nonclaim. A future trusted materializer may strengthen this
boundary only by resolving the actual source and recomputing those joins.

### Advance catalog assurance honestly

The current catalog revision is `rev7`; the implementation program's older
`rev5` wording is historical, not an implementation pin. If #961 changes the
opacity relation's checker or evidence state, it must advance the current
catalog revision once and move every live taxonomy-revision producer,
byte-identical fixture, claim surface, policy test, reader-facing authority,
and embedded claim fixture together.

The opacity assurance change is narrow: checker implementation becomes
positive and bounded-test evidence becomes executable. Model-check, proof,
runtime enforcement, backend declaration, backend realization, and backend
conformance remain negative. The legacy `implementation_status` aggregate must
remain consistent with the positive checker axis. Do not change only the
profile or only the catalog assurance record.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Opacity meaning | ADR-099 and `specs/formal/participant-semantics/participant-predicate-opacity.md`; do not redefine possible points, information cells, active strategies, release, memory, or relation boundaries in conformance code. |
| Information-flow carriers | ADR-085/095 and SEM-230 exact-cut policy, projection, adaptive strategy, declassification, memory, scheduler/environment, and order semantics. |
| Relation and claim authority | `contracts/concept-authority/behavioral-relations-v1.json`, `BehavioralRelationCatalogModel`, `BehavioralClaimBindingModel`, `load_behavioral_relation_catalog()`, `validate_behavioral_claim_binding()`, and `tools/check_behavioral_relation_claims.py`. |
| Profile corpus | `contracts/profiles/`, `corpus_family_root(PROFILES)`, installed-corpus force includes, hardened backend/random-stream profile-id and identity checks, and strict JSON ingress. The relation profile is a distinct family, not a semantic, backend, validation, or random-stream profile. |
| Closed contracts and digests | `ContractModel(extra="forbid")`, `parse_bounded_json_object()`, `PrefixedDigestString`, `SourceArtifactIdentityModel`, RFC 8785 `canonical_json_digest()` / `canonical_contract_digest()`, and exact ref/revision pairing. |
| Analysis service | `raes_processor.satisfiability` and `raes_processor.exploit_path`: normalized closed inputs, typed evidence/outcomes, bounded preflight diagnostics, deterministic engines, canonical selection, value-free operational failures, and replay. Do not copy either domain theory. |
| Behavioral-validation discipline | `BehavioralProbeBinding`, claim admission, input/checker digests, capability identity, stable diagnostics, and fail-closed outcomes. Reuse the discipline, not the subject/backend runner or report shapes. |
| Diagnostics and errors | `Diagnostic`, `DiagnosticModel`, `Severity`, stable domain-specific codes, bounded preflight accumulators, typed unsupported outcomes, and the value-free satisfiability/exploit-path operational-error posture. Do not import conformance merely to reuse its sanitizer or add an opacity exception hierarchy. |
| Schema publication | `schema_bundle()`, `tools/generate_contract_schemas.py`, hand-governed `contracts/schemas/`, valid/invalid conformance fixtures, the conformance validator registry, schema-publication entries/hashes, and generated/publication drift gates. |
| Evidence/artifacts | Existing canonical JSON, digest, safe-ref, root-confined artifact-path, atomic-write, and redaction-gate patterns. Introduce no mutable witness store. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, requirement governance, concept/claim/schema/JSON/docs gates, and `tools/verify_all.py`. Because branch `961-participant-opacity` has no requirement UID, workflow commands use `RAES_REQUIREMENT_UID=ASR-535`. |

Package boundaries stay intact: `raes_contracts` owns the portable profile,
normalized input, outcome/evidence, and resolution; `raes_processor` owns
deterministic finite evaluation and replay; `raes_conformance`, `raes_runtime`,
and `raes_backend_protocols` are not changed by #961.

## Cross-Cutting Layers And Security Posture

1. **Profile/config ingress.** The profile is bounded UTF-8 JSON, duplicate
   members and non-finite numbers are rejected, the root is an object, the
   profile id is grammar-checked before path construction, and the path comes
   from the packaged/source corpus root. There is no YAML expression, env
   binding, arbitrary import, URL fetch, or caller-selected production root.
2. **Closed schema and semantic gate.** `ContractModel`, the published schema,
   valid/invalid fixtures, local validators, and one cross-reference validator
   reject unknown fields, missing coordinates, invalid discriminators,
   unresolved refs, inconsistent observer/coalition shapes, and ref/revision
   mismatch. A Python-only shape is not a published contract.
3. **Relation/claim gate.** Catalog, relation, profile, projection, carrier,
   assurance axis, evidence scope, quantifier, and nonclaims are joined before
   execution and again before evidence projection. A present profile string is
   insufficient.
4. **Finite-model admission gate.** Exact declared bounds, realized counts,
   reachability, strategies, scheduler/environment choices, order variants,
   source/profile/materializer/checker digests, and deterministic resource caps
   are validated before evaluation. Malformed input fails before evidence;
   unsupported dimensions and deterministic cap exhaustion are typed
   unsupported; unexpected timeout/operational failure emits no evidence.
   Vacuity and partial execution cannot pass.
5. **Authentication and runtime-policy boundary.** The #961 checker is
   in-process and pure; it does not traverse HTTP authentication, RUN-319
   authorization, API-407 capability, runtime persistence, or backend gates
   and therefore makes no claim about them. A future API wrapper must reuse
   `create_control_plane_app()`, strict security defaults, identity/role/target
   binding, request-size limits, fingerprints/idempotency, and audit rather
   than exposing a new unauthenticated checker endpoint.
6. **Secret-handling boundary.** Profiles, models, fixtures, diagnostics,
   counterexamples, evidence, logs, and review output use synthetic bounded
   values and safe refs/digests only. Raw secret values, possible worlds,
   memories, policy/supervisor internals, participant content, credentials,
   rejected values, and environment dumps are excluded.
7. **Diagnostic/error-envelope gate.** Expected failures use stable codes,
   schema-derived safe addresses, and bounded generic messages. Do not
   interpolate `str(exc)`, Pydantic `input_value`, rejected keys/ids, model
   content, tracebacks, or tool output. If later exposed over HTTP, unexpected
   failures retain `{"detail":"internal server error"}`.
8. **Artifact/persistence gate.** Validate the complete evidence and claim
   before canonical serialization. Durable evidence uses safe root-confined
   names, atomic writes, content digests, replay, and the existing redaction
   gate. It does not enter `RuntimeSnapshot.metadata`, operation details,
   `AuditEvent`, a log line, `BackendConformanceReport`, or a new database.
9. **OS/process exposure gate.** The default checker is an in-process,
   deterministic, fixture-only function with no network, subprocess, daemon,
   socket, privilege, or secret loader. Profile/model content, secrets,
   witnesses, credentials, and full results never enter argv, environment
   variables, filenames, stdout/stderr, shell history, or host logs.
10. **Governance gate.** Profile schema, corpus packaging, fixture validation,
    catalog revision, current claim producers, formal/docs wording,
    schema-publication hashes, and requirement traceability move through their
    existing gates. No issue-local verification script or schema authority is
    added.

## Whole-Repository Surfaces In Scope

- **Normative authority:** ADR-099, SEM-231, behavioral relation/catalog
  assurance, the new relation-profile contract, profile corpus, published
  schema, fixtures, and schema-publication record.
- **Shared consumers:** every model embedding `BehavioralClaimBindingModel`,
  behavioral-validation and necessity-validation probes, conformance report
  claims, scientific-completeness and experiment-study fixtures, evidence-run
  production, public claim guidance, and claim-policy scanning.
- **Bounded execution:** processor analysis preflight, deterministic opacity
  evaluator, typed unsupported/invalid boundaries, replay, safe
  result/counterexample evidence, and focused negative fixtures.
- **Packaging:** `raes_contracts` exports, contract schema bundle, validator
  registry, contract corpus force include, wheel/sdist corpus tests, and
  source/install loader parity.
- **Verification:** profile schema/semantic fixtures, all six issue negative
  cases, catalog/profile/claim cross-reference tests, digest determinism,
  sanitization tests, vacuity/truncation tests, claim-policy gate, docs build,
  repo policy, requirement governance, and canonical verification.

## Extensibility Seam

The stable seam is:

```text
catalog relation
  -> resolved closed relation profile
     -> digest-bound normalized finite carrier
        -> trusted materializer/checker configuration
           -> axis-specific claim + safe evidence
```

The common header owns relation, taxonomy, projection, carrier, and evidence
identity. The discriminated opacity payload owns observer, secret, memory,
strategy, supervisor, release, scheduler/environment, time/order, and support
semantics. Consumers reference the profile; they do not copy its coordinates.

This lets #962 reuse the same finite profile and carrier with
`assurance_axis=model-check`, and lets a later relation add a closed parameter
variant without editing every claim-bearing DTO. Larger domains, another
observer, active strategies, coalitions, K-step horizons, releases, or order
models add profile/model artifacts. Timed, probabilistic, quantitative, or
mathematically different properties may still require a new governed relation;
the profile seam cannot disguise a changed property as configuration.

## Gotchas And Anti-Patterns

Avoid:

- resolving only that a profile ref string is non-empty;
- creating `ParticipantOpacityBinding`, an opacity relation registry, profile
  enum, report, runner, exception hierarchy, logger, store, endpoint, or
  workflow beside the incumbents;
- reusing a semantic/backend/validation profile family or
  `ParticipantPolicyBinding` for relation parameters;
- treating the possible-point model as a participant to satisfy a generic
  subject enum;
- wrapping the pure checker in `BehavioralProbeCase`, a live execution basis,
  or `BackendConformanceReport`;
- trusting a caller-supplied information-cell id or `same_observation` boolean
  without the profile-bound projection/materializer identity;
- accepting a single equal-history pair when another secret point has no
  nonsecret alternative;
- comparing active actual and witness points under different strategies;
- checking individuals independently and inferring coalition opacity;
- treating absence as observable without opportunity/deadline/progress
  semantics;
- omitting approval/denial, modification, deferral, handoff, cancellation,
  delivery, retry, error branch, order, or latency retained by the profile;
- treating declassification as knowledge-preserving or
  concealment/revocation/reset as knowledge erasure;
- treating no reachable secret point, an empty cell, incomplete enumeration,
  timeout, skipped strategy, unsupported dimension, or count mismatch as pass;
- calling exhaustive ordinary finite tests a model check or proof, using a
  universal quantifier, or changing the relation to
  `bounded-probe-success`;
- promoting one passing profile to generic opacity, SEM-230
  noninterference, epistemic indistinguishability, trace equivalence,
  simulation, refinement, or bisimulation;
- advancing only the opacity catalog entry while leaving the taxonomy
  revision or live producers stale;
- minting a local JSON serializer or digest instead of RFC 8785 canonical
  helpers;
- treating a numeric interval as an exhaustive finite enumeration, or allowing
  input/hash iteration order to choose a different counterexample;
- echoing point ids, rejected values, raw Pydantic/backend exceptions, hidden
  observations, or counterexample contents into diagnostics; and
- passing profiles, models, secrets, witnesses, or credentials through argv,
  environment variables, filenames, logs, or CI artifacts.

## Non-Goals And Implementation Boundary

Issue #961 may publish the shared resolved relation-profile contract and its
opacity variant, add closed normalized finite input/evidence contracts and
fixtures, implement a deterministic bounded opacity processor analysis with
replay, emit digest-bound bounded outcomes or safe counterexample refs, and
update only the checker/bounded-test assurance facts and supporting
documentation.

It does not:

- model-check or prove universal opacity;
- synthesize a supervisor or enforce opacity at runtime;
- add SDL syntax, a secret-predicate expression language, policy engine,
  participant gateway, route, transport, UI, or backend capability;
- change RUN-319 mediation, API-407 declarations, runtime persistence, control
  plane authentication, backend protocols, or backend conformance;
- certify RAES, any participant, policy, scheduler, environment, runtime, or
  backend outside the exact finite checked artifact;
- establish noninterference, trace equivalence, simulation, refinement,
  bisimulation, timed/progress-sensitive opacity, quantitative leakage,
  probabilistic opacity, or unbounded coalition/strategy claims; or
- require network access, external solvers, subprocess execution, live
  backends, ambient secrets, privileged host resources, or a new durable
  evidence service.
