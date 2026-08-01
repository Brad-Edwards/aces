# Issue #964 — Participant Opacity Runtime Enforcement Preflight

Date: 2026-08-01

Issue: #964.

Requirements: `SEM-231`, `RUN-319`.

This note records repository-wide architecture guardrails for the bounded
reference-runtime enforcement lane. It is guidance only. It does not publish a
runtime profile or schema, change runtime behavior, advance catalog assurance,
establish opacity, or make a backend-realization or conformance claim.

## Decisive Current-State Finding

Issue #964 must close and constrain the existing SEM-231/RUN-319 seam. It must
not create an opacity monitor beside the participant crossing boundary.

- ADR-099 and the SEM-231 formal authority already own the one-sided opacity
  relation, observer information cell, secret predicate, memory, active
  strategy, supervisor visibility, release, order, time, probability, and
  relation boundaries.
- `BehavioralRelationProfileModel`, the corpus-backed profile loader,
  `BehavioralClaimBindingModel`, and `validate_behavioral_claim_binding()`
  already own profile identity and claim admission. The claim model already
  has the `runtime-enforcement/enforced` axis, and deliberately prevents finite
  runtime evidence from carrying a universal quantifier.
- The current `participant-opacity-baseline-v1@sem-231/rev3` artifact is not a
  live-runtime profile. Its carrier, observer, predicate, scheduler,
  environment, and cuts are fixture identities. Relabeling it, changing its
  evidence axis, or applying it to arbitrary runtime state would be a false
  join. Earlier bounded, model-check, and proof evidence must retain their exact
  historical catalog/profile coordinates.
- RUN-319 already supplies authenticated subject and audience binding,
  deny-first exact-cut crossing decisions, capability admission, governed
  transformation, scoped idempotency, append-only API-423 history,
  expected-head commits, restart validation, and participant-view projection
  before serialization.
- API-423 already distinguishes requested, decided, transformed, disclosed,
  delivery-attempted, delivered, observed, and audited facts. The runtime
  currently emits only requested, decided, and sometimes transformed crossing
  facts. Delivery, observation, omission/opportunity, retry, policy-change,
  evidence, and audit visibility are therefore not established merely because
  their portable stage types exist.
- The live crossing path currently covers ordinary action admission, API-409
  participant control, and governed status/history/context view serialization.
  Execution-service control/readback, episode initialize/reset/restart/
  terminate, the v2 decision-surface selection call, autonomous scheduler and
  clock activity, operation status, administrative snapshot/apparatus reads,
  `audit_log()`, direct backend calls, and observable error/status/timing
  behavior are separate reachable surfaces. A supported opacity declaration
  must either mediate each surface retained by its observer profile or prove it
  unreachable and fail admission when that fact changes.
- `commit_participant_transition()` is the correct persistence owner, but its
  current history-head cut covers behavior, control, and crossing streams only.
  A runtime-opacity cut cannot ignore episode, scheduler/time, operation,
  delivery, policy/profile, or evidence state when one of those coordinates
  affects the declared observation.

The bounded meaning of `runtime-enforcement` for this issue is therefore:

> For one exact, finite, revisioned runtime profile and carrier, every admitted
> in-scope observation is produced through the shared crossing boundary under
> one fresh trusted state cut, and any unknown, stale, out-of-carrier, or
> unmediated case is refused before observation or is converted by an already
> authorized weakening into an explicit nonclaim.

This is runtime containment of an admitted finite opacity profile. It is not a
live computation of arbitrary possible worlds, an online proof of the SEM-231
hyperproperty, or a claim about an unbounded deployment.

## Architecture Decisions And Guardrails

### Bind one runtime support declaration to the shared profile and claim seams

The runtime needs one closed support declaration that composes, rather than
copies:

- exact catalog id/revision and `participant-predicate-opacity`;
- exact relation-profile id/revision/digest;
- exact finite normalized carrier/materializer identity and digest;
- observer participant or coalition and audience identity;
- secret-predicate ref/revision, never its raw value or evaluator body;
- an exact observation-surface inventory ref/revision/digest;
- trusted state-cut, projection, release, memory, opportunity, order, and
  enforcement-rule refs/revisions;
- limitations and explicit nonclaims; and
- one validated `BehavioralClaimBindingModel` with
  `assurance_axis=runtime-enforcement`, `assurance_status=enforced`, and a
  finite, non-universal evidence boundary.

The declaration is an axis-specific support/evidence join, not another
relation definition, policy binding, backend manifest, or claim DTO. If a
portable contract is needed, it belongs in `raes_contracts`, remains closed
under `ContractModel(extra="forbid")`, embeds or references the incumbent
claim/profile authorities, and follows normal schema publication. Runtime code
must not encode this declaration as an open dictionary, SDL metadata,
`RuntimeSnapshot.metadata`, an environment-variable bundle, or a set of
booleans.

Do not mutate the fixture-bound baseline profile into a runtime profile. Add
an exact runtime profile through the existing behavioral-relation profile
family and closed discriminator seam. Preserve the current profile and every
earlier evidence revision. If the behavioral catalog advances, archive the
exact prior catalog and keep historical resolution working; do not relabel old
bounded/model-check/proof evidence with the new revision.

The #961 `ParticipantOpacityAnalysisEvidenceModel` may be cited as bounded
evidence, but its `normalized-input-only` provenance explicitly does not
authenticate the source or materializer. It cannot authorize a runtime by
itself. A trusted runtime-owned materializer/resolver must recompute the exact
profile/carrier/cut joins or supply independently admitted immutable joins.
Changed profile, carrier, materializer, policy, inventory, or enforcement-rule
identity invalidates admission.

### Enforce through the existing crossing resolver and operation boundary

Compose runtime-opacity admission and decision data into the existing
`ParticipantCrossingPolicyResolver` / `ParticipantCrossingPolicyResolution`
seam. `RuntimeControlPlane`, its public in-process methods, and its HTTP adapter
must converge on the same operation-bound mediation. The runtime supplies the
state cut and completed decision; adapters supply only bounded intent and an
authenticated identity.

Do not add an opacity gateway, response-filter middleware, detached recorder,
belief-state store, world-state store, background monitor, or backend-local
policy engine. Do not run the bounded checker on each request. The finite
checker admits or falsifies an exact carrier; the runtime boundary keeps the
executed observation inside that admitted carrier and records the result.

The trusted resolver may evaluate a secret predicate internally only through a
revisioned injected evaluator bound by the profile. Raw truth values,
alternative points, information-cell keys, participant memory, policy bodies,
or supervisor internals never cross into API-423, operation, audit, diagnostic,
log, filename, or process surfaces.

### Treat observation coverage as a closed admission invariant

The observation inventory is exhaustive for the named observer, not a list of
the routes edited by #964. Each entry needs a stable surface id, owning carrier
or method, observer/audience, occurrence/content/absence treatment, projection
and order basis, opportunity or timing basis where applicable, and one of:
mediated, provably unreachable under the admitted configuration, or
unsupported. Unknown entries and reachable unsupported entries reject the
positive claim.

The repository surfaces that must be classified include:

| Surface family | Canonical owner and guardrail |
| --- | --- |
| Action and active probes | `ParticipantControlMixin.admit_participant_action()`, v1/v2 decision-surface selection, SEM-211 admission, and autonomous scheduler action paths. Every allowed probe uses the same crossing path; a passive profile must make all participant-driven probes unreachable rather than ignore them. |
| Supervisor/control | API-409 control occurrences and `ParticipantCrossingControlIngressMixin`. Approval, denial, edit/direction, intervention, handoff, override, cancellation, deferral, and occurrence/content visibility remain distinct observations. |
| Episode and execution lifecycle | initialize, reset, restart, terminate, execution-service control/readback, participant clock and scheduler reset. A runtime reset is a state transition, never participant forgetting unless the profile names a trusted reset rule covering every retained channel. |
| Participant egress | `ParticipantRetrievalMixin`, `serialize_participant_view()`, status/history/context views, directed inject delivery, SEM-226 exposure, and API-423 disclosure/delivery/observation stages. Projection precedes serialization and the required durable stages precede return. Delivery is not inferred to be observation. |
| Failure and omission | Operation receipts/status, rejection/error envelopes, withheld/failed/unsupported delivery attempts, retries, acknowledgements, timeouts, and declared opportunities. Silence is not evidence: observable omission is represented by a durable incumbent occurrence at a governed opportunity cut. |
| Time and order | Existing time-model, scheduler, logical/causal order, delivery order, and policy-cut authorities. The baseline may use governed logical opportunity or discrete timing labels; wall-clock latency, progress-sensitive behavior, jitter, and timed opacity remain unsupported. |
| Policy/release change | Exact-cut API-423 policy refs, SEM-226/230 release and declassification, projection refresh, controller/authority changes, and visible effects. Hiding a revision identifier does not hide changed behavior. |
| Retrieval/evidence/audit | Operation reads, `/snapshot`, apparatus summary, `audit_log()`, crossing/control histories, evidence refs, and any future evidence endpoint. Administrative authorization is not participant visibility. If such a reader is the observer or coalition member, the surface belongs in that profile. |
| External effects | Backend calls, target readback, participant execution, resource/scheduler effects, and retry/replay behavior. A reference-runtime claim stops at the declared boundary and cannot silently include direct adapter/native-backend use. |

An observation inventory that names only payload, decision, delivery, retry,
latency, and order at a coarse semantic level is insufficient for runtime
enforcement. The runtime support declaration binds the concrete surface
inventory while the SEM-231 profile continues to own semantic observation
meaning. Do not duplicate relation coordinates in each route or service.

### Represent omissions and timing without inventing knowledge

An omission is observable only when a profile binds an existing schedule,
opportunity, acknowledgement, logical deadline, or progress basis. Reuse
API-423 delivery-attempted dispositions and the incumbent scheduler/time or
owning occurrence reference where they express the fact. Emit a positive
durable withheld/failed/unsupported fact at the declared cut; absence of a log
entry cannot prove that an opportunity was observed and missed.

The current SEM-231 baseline is untimed and progress-insensitive. A discrete
logical timing bucket may be an observation label only when its bucket rule,
clock authority, cut, and order are governed and digest-bound. Do not sleep,
add random delay, read ambient wall time, or treat nondeterministic scheduling
as opacity evidence. Quantitative latency, deadlines based on elapsed host
time, progress-sensitive opacity, and probability-bearing claims require a
different governed relation/profile and evidence.

### Keep the durable claim on the owning API-423 decision

The durable crossing decision is the portable owner of the runtime-enforcement
fact. It must carry a compact, safe, typed binding to relation, exact profile,
secret-predicate ref/revision, observation-inventory ref/revision/digest, and
`assurance_axis=runtime-enforcement`, plus the claim/evidence reference and
limitations. It must not carry the predicate result, raw secret world, cell,
witness, memory, policy body, supervisor state, or alternative execution.

If API-423 cannot carry that binding without ambiguity, evolve its existing
decision component through normal compatible schema publication and contextual
validation. Do not place the only binding in `AuditEvent.details`, operation
diagnostics, `result_payload`, snapshot metadata, a parallel opacity history,
or a new database. Audit receives safe correlation refs only and remains an
authorized evidence surface, not semantic authority.

The API-423 context validator remains the single cross-record join owner. It
must resolve the compact binding against the exact claim, catalog, profile,
predicate authority, inventory, policy/cut, evidence, predecessor, participant,
episode, audience, and order indexes. Local Pydantic validators own only
closed-shape and single-record invariants. Routes, mediation, stores, replay,
and tests must not each reimplement this join.

### Extend the existing atomic cut; do not add persistence

`RuntimeSnapshot`, `ControlPlaneStore`, `InMemoryControlPlaneStore`, and
`LocalControlPlaneStore` remain the only state owners. Reuse
`commit_participant_transition()` and its expected-head write-set semantics so
the applicable crossing stages, operation state/result, safe audit
correlation, profile/inventory cut, and any participant-visible result become
durable atomically before output.

The commit precondition must cover every observation-affecting head or digest
named by the profile, not just the three current participant history heads.
Episode state, policy/profile/inventory revision, release, scheduler/time,
delivery/retry/opportunity, operation status, controller/authority, evidence,
and relevant backend support are part of the cut when the profile retains
them. A changed coordinate causes a fresh decision; it is not repaired by
updating the fingerprint after resolution.

Intermediate `RUNNING`, authorization, delivery-attempted, failure, retry, and
commit-conflict states are observations when the profile retains them. A
two-commit action path must not expose an unclassified intermediate result.
Backend dispatch or participant serialization cannot precede the durable
authorization stage. If an external backend effect cannot be rolled back when
final persistence fails, that path is outside the bounded reference-runtime
claim and must be refused or disclosed as a weakening that removes the opacity
claim.

Restart first parses closed snapshot models, validates append-only prefixes,
and re-resolves API-423 plus runtime-opacity context before serving or mutating
state. Missing legacy crossing/profile/inventory history, unresolved historical
profiles, stale digests, truncated state, or a reset that merely clears
runtime-local caches fails closed. The issue #802 legacy-presence distinction
must not be collapsed into “empty means no prior knowledge.”

Idempotency reuses the incumbent scoped key, semantic fingerprint, operation
record, and result-history cut. The fingerprint binds every profile,
predicate, observer/audience, inventory, policy/release, rule, subject,
marking, opportunity, order, capability, and expected-head coordinate that can
affect observation. An exact retry returns the same durable result without a
new decision. A stale retry, replay, handoff, reset, policy revision, or
inventory change conflicts and discloses no protected detail.

The local store remains a single-process, single-writer reference
implementation. Atomic replacement and an in-process lock do not establish
multi-process transactions, distributed linearizability, or crash atomicity
with native external effects.

### Fail closed or remove the claim under explicit weakening

Malformed, incomplete, unsupported, stale, cross-cut, out-of-carrier, or
unmediated profile coordinates fail before a participant-visible result. The
only alternative is an already policy-authorized disclosed weakening that:

- records the exact safe limitation/loss and authorization basis;
- does not retain or emit the positive opacity runtime-enforcement binding;
- does not mutate an earlier decision or erase retained observation; and
- does not treat API-407 backend weakening as authority to weaken SEM-231.

No “best effort opacity,” warning-only bypass, implicit default profile,
`latest` revision, current-snapshot fallback, or randomized response is
permitted.

### Advance assurance narrowly

One exact supported runtime profile may carry a finite
`runtime-enforcement/enforced` claim. The catalog-level
`runtime_enforcement_status` becomes at most `partial` because #964 supports a
bounded subset. `implementation_status` remains consistent with the positive
checker/runtime axes. Backend declaration, realization, and conformance remain
negative until #965 supplies their separate evidence.

Runtime tests and mediation do not change the result relation to
policy-noninterference, projected-history equality, epistemic
indistinguishability, trace equivalence, simulation, refinement, or
bisimulation. They do not relabel bounded checking as model checking or the
Isabelle theorem as a concrete runtime proof.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Opacity semantics | ADR-099 and `specs/formal/participant-semantics/participant-predicate-opacity.md`; do not redefine the information cell, possible points, memory, strategy, release, supervisor, or relation boundary in runtime code. |
| Shared profile and claim | `BehavioralRelationProfileModel`, corpus-backed exact-revision loaders, `BehavioralClaimBindingModel`, `BehavioralRelationCatalogModel`, `validate_behavioral_claim_binding()`, and RFC 8785 canonical digests. Add no runtime-only relation registry or claim model. |
| Bounded admission evidence | `ParticipantOpacityAnalysisInputModel`, `ParticipantOpacityAnalysisEvidenceModel`, the #961 deterministic checker/replay, and their authenticity nonclaim. Recompute trusted joins; never treat a passing fixture as runtime authority. |
| Information-flow and crossing | ADR-085/095, SEM-230, API-423 `ParticipantCrossingOccurrenceModel`, `validate_participant_crossing_occurrence_context()`, and all distinct crossing stages. Reference carriers; do not copy payloads or collapse stages. |
| Runtime mediation | `RuntimeControlPlane`, `ParticipantCrossingPolicyResolver`, `ParticipantCrossingPolicyResolution`, `prepare_participant_crossing()`, crossing ingress/egress/control boundaries, SEM-211 admission, and SEM-226 exposure. Extend this seam instead of adding a monitor. |
| Identity and authorization | `ControlPlaneSecurityConfig.strict_defaults()`, `_ControlPlaneApiAuth`, `ControlPlaneIdentity`, `ControlPlaneRole`, target binding, and separate participant controller/audience bindings. Caller role never establishes participant visibility or opacity. |
| Capability | `PARTICIPANT_RUNTIME_POLICY_FEATURES`, required-contract mappings, and `resolve_participant_feature_support()`. Capability is a gate and posture, not relation evidence or weakening authority. |
| Runtime carriers | Participant episode, behavior, control, crossing, delivery/observation, execution-service, scheduler/time, resource, operation, evidence, and audit carriers. Reuse their lifecycle and append-only validators; do not create opacity copies. |
| Persistence | `RuntimeSnapshot`, `ControlPlaneOperationRecord`, `AuditEvent`, `ControlPlaneStore.commit_participant_transition()`, both shipped stores, atomic replacement, expected-head checks, restart parsing, and append-only history validators. Add no opacity side store. |
| Diagnostics and HTTP | `Diagnostic`, `Severity`, `OperationReceipt`/`OperationStatus`, request-size guards, `_request_fingerprint()`, idempotency, governed retrieval response models, and the exact redacted 500 envelope. Add no exception hierarchy or logger. |
| Contract publication | Hand-governed `contracts/schemas/`, valid/invalid fixtures, `schema_bundle()`, schema-publication entries/hashes, compatibility classification, `tools/check_generated_schemas.py`, and `tools/check_schema_publication.py`. |
| Claim/concept governance | `contracts/concept-authority/behavioral-relations-v1.json`, its historical revisions and fixtures, `tools/check_behavioral_relation_claims.py`, concept-authority gates, and all claim-bearing consumers. Advance the current revision once; do not rewrite historical evidence. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, repository/requirement policy, JSON/schema/concept/docs gates, `tools/verify_all.py`, and `RAES_REQUIREMENT_UID=SEM-231` on this issue-number branch. Add no issue-local runner. |

Package ownership remains: `specs` owns semantics; `raes_contracts` owns
portable profiles, claims, and crossing/evidence shapes; `raes_processor` owns
pure bounded analysis and trusted compilation/materialization; `raes_runtime`
owns live mediation/security/state/persistence; `raes_backend_protocols` owns
capability declarations; and `raes_conformance` owns backend probes. #964 must
not move runtime policy into the checker or backend claims into runtime state.

## Cross-Cutting Layers And Security Posture

1. **Profile/config ingress.** Runtime support resolves exact grammar-checked
   ids through the canonical corpus loader or receives an explicitly trusted
   typed in-process object. Bounded UTF-8 JSON rejects duplicate keys,
   non-finite numbers, unknown fields, path traversal, caller-selected roots,
   arbitrary imports, URLs, expressions, and `latest` aliases. No profile or
   policy comes from a request, snapshot metadata, or ambient environment.
2. **Closed shape and semantic join.** Published schema, `ContractModel`, local
   validators, the behavioral claim/profile/catalog validator, and the API-423
   contextual validator agree on exact revisions, digests, observer/audience,
   predicate, carrier, inventory, projection, policy/cut, order, evidence, and
   axis. A valid string ref or Pydantic shape alone is insufficient.
3. **Runtime support admission.** The trusted materializer and enforcement
   rule match the exact finite carrier; the inventory is complete; every
   enabled participant surface is mediated or unreachable; every unsupported
   dimension is explicit; and the finite claim uses no universal quantifier.
   Vacuity, incomplete enumeration, untrusted #961 source assertions, or a
   stale digest cannot admit enforcement.
4. **HTTP size and value bounds.** `request_size_guard_response()` bounds body
   bytes before parsing, then closed request DTOs validate the body. The
   current guard does not bound path, query, or header values, and FastAPI's
   default request-validation response can echo rejected input. Every touched
   participant path/query/idempotency value needs the incumbent bounded-value
   rules and a sanitized validation envelope before it belongs to a supported
   profile.
5. **Authentication and subject binding.** Bearer or verified-proxy identity
   passes `_ControlPlaneApiAuth`, role and exact target checks, then separate
   controller or audience binding. Tokens and identity headers never enter
   fingerprints, crossings, claims, diagnostics, audit details, or logs.
   Operator/auditor/backend roles do not imply participant authority or
   observer membership.
6. **Deny-first policy and capability.** Participant authority, admission,
   visibility, markings, declassification, transformation, backend support,
   opacity-profile admission, and observation-surface coverage are independent
   gates at the same state cut. `NOT_APPLICABLE`, unknown, stale, missing, or
   unsupported at a required gate denies.
7. **Projection, delivery, and omission.** Only a validated governed carrier
   is serialized. Required disclosure, delivery-attempted, delivered,
   observed, retry, and audited facts remain distinct and are committed only
   with their owning evidence. An omission has an explicit opportunity basis;
   delivery never proves observation.
8. **Persistence, restart, and concurrency.** Complete candidate state passes
   snapshot, append-only transition, API-423 context, and runtime-opacity joins
   before the expected-head atomic write set commits. Restart repeats those
   joins before service. Concurrent or stale cuts conflict without output;
   local atomicity is not a distributed claim.
9. **Expected-error envelope.** Denials and unsupported outcomes use stable,
   bounded, value-independent `Diagnostic` codes/messages and uniform public
   status/detail behavior for protected existence. Do not expose `str(exc)`,
   Pydantic `input`/`input_value`, participant/episode existence, hidden refs,
   gate differences, policy inventory, traceback, or backend objects. Existing
   route paths that interpolate exception or unknown participant text cannot be
   reused unchanged for a supported observer.
10. **Unexpected-error envelope.** The HTTP adapter retains exactly
    `{"detail":"internal server error"}` while audit records only a safe
    exception class/code and correlation. Failure latency and status are still
    observations when the profile retains them; redacted content alone does
    not close the channel.
11. **Secret, audit, and logging boundary.** Profiles, crossings, snapshots,
    operations, audit, diagnostics, tests, evidence, docs, stdout/stderr, and
    host logs carry safe refs, digests, codes, markings, counts, limitations,
    and nonclaims only. Raw predicate values/worlds, cell/witness data,
    participant private memory, policy/supervisor internals, payloads,
    credentials, rejected values, environment dumps, and tracebacks are
    excluded. Hashing secret-bearing content does not make it safe metadata.
12. **OS/process exposure.** #964 needs no new environment binding, secret
    loader, CLI policy/profile argument, subprocess, shell, daemon, socket,
    privilege, or host file. Typed config and corpus artifacts are injected
    in-process; no token, policy, profile contents, secret, witness, evidence
    payload, or full result enters argv, environment variables, filenames,
    shell history, stdout, stderr, or host logs. The existing HTTP socket and
    local-store directory remain their already governed deployment surfaces.
13. **Governance/publication.** Any changed portable contract moves with its
    hand-governed schema, fixtures, publication manifest/hash, generated bundle,
    compatibility review, package exports, packaged-corpus tests, and all
    embedding consumers. Catalog/profile history, claim policy, docs, and
    requirement traceability advance together through the canonical nox and
    policy graph.

## Whole-Repository Surfaces In Scope

- **Normative and concept authority:** ADR-099, SEM-231, SEM-230/RUN-319
  composition, the current and historical behavioral catalog, the shared
  relation profile family, claim validation, assurance status, and explicit
  nonclaims.
- **Published contracts:** relation profile and any narrow runtime-support
  declaration, API-423 decision/stage shapes, runtime snapshot and operation
  envelopes when changed, their schemas, fixtures, publication records, and
  packaged-corpus parity.
- **Runtime:** control-plane construction, crossing resolver/mediation,
  ingress/control/egress, participant lifecycle and execution-service paths,
  decision surfaces, directed injects, scheduler/time/retry paths, operation
  and administrative reads, snapshot, audit, store, restart, and concurrency.
- **Security and observability:** HTTP guards/auth, participant controller and
  audience bindings, error/status/latency behavior, safe diagnostics,
  idempotency/fingerprints, evidence/audit visibility, operational summaries,
  and the absence of a new logging channel.
- **Analysis and claims:** exact #961 profile/input/evidence resolution,
  runtime-owned materializer authenticity, finite claim binding, catalog
  partial-enforcement evidence, replay, and historical evidence preservation.
- **Verification:** profile/admission negatives, boundary bypass tests for each
  enabled surface, decision/content/omission/timing/retry/reset/policy-change/
  audit cases, atomic/idempotent/restart/concurrency tests, sanitization and
  existence-leak tests, claim/catalog/profile joins, schema/concept/docs gates,
  and canonical repository verification.
- **Host/runtime:** the existing in-process reference runtime, HTTP adapter,
  local single-writer store, optional backend call boundary, filesystem
  containment, and no additional ambient secrets, network services,
  subprocesses, or privileges.

## Extensibility Seam

The stable seam is:

```text
catalog relation + exact relation profile
  -> finite admitted carrier + trusted runtime materializer
     -> observation-surface inventory + enforcement rule
        -> existing crossing resolver at one exact state cut
           -> API-423 stages + atomic operation/audit evidence
              -> one finite runtime-enforcement claim
```

It is parameterized by exact profile/predicate, observer/audience, inventory,
materializer/rule, policy/release/memory, opportunity, order, expected heads,
and evidence identities. A second safe predicate, participant, audience,
logical opportunity class, or newly governed carrier plugs into those closed
artifacts and resolver indexes rather than adding route branches or fields to
every participant DTO.

A new surface kind extends the common inventory vocabulary and mapping once.
A durable multi-writer store implements the same expected-cut write-set seam.
Active strategies require every allowed action path and same-strategy carrier
mapping. Coalitions require an explicit fused-observation/memory resolver.
Timed, progress-sensitive, probabilistic, quantitative, partial-order, or
mathematically different opacity is not hidden behind this seam; it requires
the corresponding governed relation/profile and independent evidence.

## Gotchas And Anti-Patterns

Avoid:

- relabeling `participant-opacity-baseline-v1@sem-231/rev3`, the #961 bounded
  outcome, #962 model check, or #963 theorem as runtime evidence;
- reporting runtime enforcement for arbitrary live state when the admitted
  carrier is finite, fixture-bound, stale, vacuous, incomplete, or not
  authentically materialized;
- implementing an online possible-world/belief-state engine or storing raw
  secret truth, information cells, witnesses, or participant memory;
- creating an opacity policy engine, resolver stack, gateway, middleware-only
  filter, side store, history, audit stream, exception hierarchy, logger,
  schema registry, claim DTO, backend manifest block, or workflow;
- putting runtime meaning into a consumer-local enum, open mapping, metadata,
  audit details, error prose, route name, or method-presence check;
- inventorying only payloads while omitting decision occurrence/content,
  denial/withholding/failure, action availability, lifecycle, delivery,
  acknowledgement, omission, retry, order, timing labels, release/policy
  effects, retrieval, evidence, audit, operation status, or external effects;
- treating a disabled HTTP route as proof that an in-process method, scheduler,
  backend adapter, retry/replay path, administrative read, or error side channel
  is unreachable;
- permitting a passive profile while any participant-controlled probe path is
  enabled outside mediation, or comparing active actual/witness points under
  different strategies;
- treating a response payload filter, generic 403, random delay, jitter,
  nondeterministic supervisor, or a hidden policy body as opacity;
- treating silence as an observable omission without a governed opportunity,
  or treating wall-clock latency buckets as untimed baseline evidence;
- treating delivery as observation, audit retention as participant delivery,
  authorization as visibility, redaction as declassification, reset as
  forgetting, revocation as erasure, or backend downgrade as relation
  weakening authority;
- allowing v2 selection, lifecycle/execution control, autonomous scheduling,
  operation/snapshot/apparatus retrieval, or direct backend use to bypass the
  supported crossing path;
- binding the decision to current/final snapshot state, timestamp, receipt
  order, or only the crossing-history head instead of every relevant exact-cut
  coordinate;
- independent snapshot/operation/audit writes, output before commit,
  last-writer-wins, retry across an advanced cut, or a claim of distributed
  atomicity from file replacement and an in-process lock;
- retaining a positive opacity claim after fail-open behavior, partial
  coverage, unsupported dimensions, disclosed weakening, external side effect
  without durable finalization, or missing restart context;
- emitting universal quantifiers from finite runtime evidence or setting the
  catalog runtime status to generally `enforced` for one supported subset;
- exposing raw `str(exc)`, FastAPI/Pydantic rejected input, participant
  existence, secret-bearing refs/digests, policy/gate inventories, backend
  diagnostics, tracebacks, tokens, headers, or environment/process data; and
- advancing only Python, only the schema, only the profile, only the catalog,
  or only one embedded claim producer while leaving publication/history and
  consumers stale.

## Non-Goals And Implementation Boundary

Issue #964 may add one exact finite runtime-support/profile declaration,
compose its trusted admission and observation inventory into RUN-319, extend
the existing API-423 decision/stage and expected-cut persistence seams only as
needed, mediate the explicitly supported reference-runtime surfaces, and
publish finite boundary/security evidence plus one exact
runtime-enforcement claim.

It does not:

- establish general, unbounded, timed, progress-sensitive, probabilistic,
  quantitative, coalition, all-strategy, all-schedule, partial-order, or
  whole-deployment opacity;
- prove opacity, synthesize a supervisor, run the finite checker as a live
  monitor, or authenticate arbitrary #961 source/materializer assertions;
- implement backend-native realization, backend declaration or conformance,
  cross-backend equivalence, distributed ordering, or external-effect
  transactions;
- add SDL syntax, a secret-predicate expression language, policy programming
  language, participant gateway, new transport, UI, credential broker,
  provider integration, arbitrary plugin/callable loading, or generic
  evidence service;
- replace or duplicate SEM-211 admission, SEM-226 exposure, SEM-230 policy,
  API-409 control, API-423 crossings, RUN-319 mediation, API-407 capability,
  participant lifecycle/history, scheduler/time, evidence/provenance, audit,
  or persistence authorities;
- expose raw secrets, possible worlds, belief state, participant private
  memory, policy/supervisor internals, hidden backend state, rejected input, or
  backend-private objects in portable or observable records; or
- claim policy noninterference, projected-history equality, epistemic
  indistinguishability, trace inclusion/equivalence, simulation, refinement,
  strong/weak/branching bisimulation, erasure, differential privacy, or
  quantitative leakage bounds.
