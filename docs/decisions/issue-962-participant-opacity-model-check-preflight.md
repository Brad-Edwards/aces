# Issue #962 — Participant Opacity Finite-State Model-Check Preflight

Date: 2026-07-30

Issue: #962.

Requirements: `SEM-231`, `ASR-535`.

This note records repository-wide architecture guardrails for the finite-state
participant-opacity model-check lane. It is guidance only. It does not define a
new relation or profile, publish a model or evidence schema, implement or run a
model checker, change catalog assurance, establish opacity, prove an unbounded
theorem, enforce a runtime policy, or certify a backend.

## Decisive Current-State Finding

Issue #962 is a new assurance executor over the existing SEM-231 authority, not
a new opacity subsystem.

- ADR-099, the SEM-231 formal specification, and behavioral-relation catalog
  `rev7` already own the one-sided possibilistic relation, possible points,
  information cells, active-strategy quantifier, supervisor visibility,
  release, memory, order, and exact relation boundaries.
- `participant-opacity-baseline-v1@sem-231/rev1` and
  `BehavioralRelationProfileModel` already close the semantic coordinates.
  `validate_behavioral_claim_binding()` already joins the catalog, profile,
  carrier, projection, assurance axis, and claim.
- #961 already supplies strict JSON ingress, the normalized possible-point
  primitives, finite-domain admission, the opacity information-cell kernel,
  deterministic counterexample selection, digest-bound evidence, replay, and
  safe operational failures.
- #961 deliberately trusts an input assertion that its possible-point carrier
  is complete. It scans that supplied carrier; it does not derive reachability
  from initial states and transitions. Relabeling its result
  `assurance_axis=model-check` would therefore be an assurance escalation, not
  #962.
- `raes_processor.exploit_path` supplies the closest incumbent execution
  pattern for #962: a closed normalized graph, canonical graph traversal,
  explicit explored counts, typed unsupported outcomes, deterministic
  witnesses, and replay. Its depth-limited result semantics are not reusable
  for a complete model check. `raes_processor.satisfiability` supplies the pinned
  tool-configuration and evidence-join pattern. Neither domain theory should
  be copied.

The smallest coherent addition is a distinct closed finite transition-model
input and model-check evidence envelope in `raes_contracts`, plus a
deterministic explicit-state explorer in the existing
`raes_processor.participant_opacity` package. The explorer derives the reachable
possible-point carrier and then reuses the #961 opacity kernel. No new relation,
profile registry, policy engine, conformance runner, exception hierarchy,
logger, store, endpoint, or workflow is justified.

## Architecture Decisions And Guardrails

### Keep one semantic authority and one profile seam

The model check uses relation `participant-predicate-opacity`, the current
behavioral taxonomy, the shared profile loader, and the shared claim validator.
It does not define `model-checked-opacity`, copy SEM-231 coordinates into a
checker-local profile, or use a generic graph property as a substitute for the
relation.

The governed profile remains the authority for observer or coalition, secret
predicate, initial information, observation projection, memory and horizon,
passive or active strategy domain, supervisor visibility, release, scheduler
and environment domains, nondeterminism, order, time, and probability scope.
The finite model supplies one exact realization of those coordinates; it does
not override them.

The shipped baseline remains passive, one-sided, possibilistic, untimed,
progress-insensitive, and total-order. Tests may inject another closed profile
to exercise active strategies, coalitions, memory, release, or order failures.
A positive result for such a variant requires its own governed profile artifact
and exact ref/revision/digest; an in-memory mutation is test evidence only.

### Add a transition model; do not overload the #961 carrier

The model-check input needs a separate schema because it has different
authority and assurance invariants from
`ParticipantOpacityAnalysisInputModel`. It must contain, in canonical form:

- model id, revision, source identity, and digest-bound materializer or model
  provenance;
- exact profile and taxonomy joins;
- the complete finite declared state set, initial-state set, and transition
  relation;
- stable canonical state and transition ordinals and safe references;
- the strategy, scheduler, environment, order, cut/horizon, observation,
  memory, release, coalition, and secret labels needed to derive SEM-231
  possible points;
- exact declared counts for states, transitions, initial states, strategies,
  scheduler/environment pairs, order variants, and evaluation points; and
- an explicit declaration that the transition artifact is the complete model
  being claimed, not a sample, depth prefix, or timeout-truncated export.

Reuse `ContractModel`, `PrefixedDigestString`, `SourceArtifactIdentityModel`,
the existing safe observation-cell coordinate vocabulary, and the existing
safe-ref/revision/digest primitives where their meanings match. Do not reuse
`OpacityPossiblePointModel` as a model state: its caller-supplied `reachable`
field is part of #961's bounded-carrier semantics, while #962 must derive
reachability. Do not fork the shared coordinate semantics or change the #961
input/evidence invariants, which correctly pin that lane to
`bounded-test/tested/finite/finite-cases`.

The transition model does not carry a caller-supplied `reachable` verdict or
information-cell id. Reachability is derived from the declared initial states
and transitions. Information cells are derived from the profile-relevant
initial-information, observation, memory, release, coalition, strategy, and
order coordinates. State reduction must not merge states with different values
for any of those coordinates without a separate preservation proof.

### Make exhaustive reachability the assurance boundary

The checker performs a canonical fixed-point traversal of the finite transition
relation. It terminates because the admitted state set is finite, not because a
depth, wall-clock, or iteration timeout was reached.

Admission rejects duplicate or unresolved ids, noncanonical order, transition
endpoints outside the state set, missing initial states, count/digest mismatch,
and model/profile domain mismatch. Every active strategy declared by the
profile must have its required initial and transition domain, and actual and
witness points remain under the same strategy. Scheduler/environment and order
coverage must exactly match the profile's declared domains and supported
quantifier treatment.

The shipped baseline has singleton scheduler and environment domains, so its
v1 quantifier posture is unambiguous. A future multi-valued scheduler or
environment profile must first declare its quantifier order in the shared
relation profile. The engine must not guess universal versus existential
treatment from a tuple of refs.

Evidence records both declared and explored state/transition counts, reachable
evaluation-point and secret-point counts, and counts per strategy and declared
scheduler/environment/order domain. Unreachable declared states remain visibly
distinct from explored reachable states and cannot satisfy an opacity
obligation.

A depth bound, sampled schedule, early counterexample exit, skipped strategy,
missing domain cell, timeout, resource-cap interruption, or partial frontier
cannot produce a model-checked result. Valid but unsupported profile
dimensions, vacuous secret domains, and deterministic pre-admission cap
exhaustion are typed non-positive outcomes. Malformed models and unexpected
operational failures emit no evidence envelope.

### Reuse the opacity kernel without relabeling bounded evidence

After complete reachability, the explorer materializes the canonical reachable
SEM-231 possible points and invokes one extracted internal opacity kernel from
the #961 implementation. Both lanes must share:

- information-cell construction;
- the universal reachable actual-secret-point scan;
- same-strategy witness selection;
- one-sided secret polarity;
- deterministic lowest-canonical counterexample selection; and
- vacuity and safe-counterexample rules.

The model-check service must not call
`analyze_participant_opacity_input()` and relabel its
`ParticipantOpacityAnalysisEvidenceModel`. The model-check evidence separately
binds the transition model, exploration configuration, explored fixed point,
derived carrier digest, result, and `model-check` claim. Agreement tests compare
#961 and #962 on shared finite carriers and independently assert the expected
outcome; equality alone is not an oracle.

### Use a deterministic in-process explicit-state tool

The proportionate tool is a versioned in-process explicit-state explorer in
`raes_processor.participant_opacity`. The property requires graph reachability
and an information-cell check; the existing Z3 adapter, a new external model
checker, or a shell wrapper adds no semantic capability for this finite
baseline.

The closed checker configuration records the tool id and semantic version,
algorithm revision, traversal and ordering rules, opacity-kernel revision,
counterexample selection, supported profile dimensions, and deterministic
state/transition/resource caps. Its canonical digest and the implementation or
source revision are evidence. Measure the installed tool/package version at the
execution boundary as the satisfiability adapter does; do not accept a
caller-authored version string. Python set/dict order, locale, wall-clock time,
process ids, and host paths never affect result identity.

If a later profile genuinely needs an external timed, symbolic, probabilistic,
or partial-order tool, that is a separate tool decision. It must use
`tools/tool_versions.py` or an immutable archive/container digest,
checksum-verified acquisition, fixed list-form argv with no shell, empty or
allowlisted environment, no verification-time network, bounded CPU/memory/time
and output, safe stdout/stderr handling, and a canonical nox integration. It
must not inherit a model-check result from this untimed possibilistic lane.

### Bind one exact model-check result

The model-check evidence envelope is separate from the #961 bounded evidence
envelope and binds:

- taxonomy revision and catalog digest, relation, profile, projection, and
  claim coordinates;
- model id/revision, exact source and canonical model digests, and any
  unauthenticated materializer assertions as such;
- checker configuration and digest;
- complete declared counts and exact explored counts;
- derived reachable possible-point carrier digest;
- outcome, safe counterexample or typed unsupported reason;
- mutation/agreement evidence refs and digests when retained;
- limitations, provenance scope, and explicit nonclaims; and
- replay data sufficient to recompute every join and result.

The claim uses
`assurance_axis=model-check`, `assurance_status=model-checked`, and
`evidence_scope=model-check`. A passive profile uses `all-traces` for the
reachable exact finite model; an active profile uses `all-strategies` and its
evidence boundary additionally states that all reachable actual points and
traces under each declared strategy were explored. These universal words are
relative to the exact model/profile digest, never to every RAES runtime,
backend, policy, or future profile.

A positive outcome should read as the SEM-231 property holding on the exact
complete finite model, not as RAES being opaque. A counterexample is still a
completed model-check result, but the evidence outcome—not the assurance
status—states that the model violates the relation.

The catalog may advance its model-check axis only after the exact checked model,
negative mutations, replay, and independent reproduction are committed and
passing. Advancing the catalog requires a taxonomy revision and synchronized
updates to every live revision producer and fixture. The legacy
`proof_status` remains `deliberately-unproved` when
`model_check_status=model-checked`; the compatibility value
`proof_status=model-checked` is accepted only when the explicit model-check
axis is also positive. No `assurance_axis=proof` claim is created.

Because a relation profile embeds the taxonomy revision, do not change profile
bytes under the same `profile_revision` when the catalog advances. Publish or
retain an exact new profile revision and keep historical evidence bound to its
old catalog/profile digests. Normal execution may use the canonical loaders as
a convenience; replay must accept or resolve the exact catalog and profile
artifacts named by the evidence and must not substitute ambient “latest”
content.

### Keep counterexamples safe, deterministic, and replayable

A model-check counterexample identifies a canonical actual secret point and a
canonical path or state/transition ordinal sequence sufficient to reproduce the
secret-only information cell. It binds the model, profile, strategy, and result
digests. It does not serialize raw state, secret values, accumulated
observations, participant memory, policy bodies, supervisor internals,
credentials, rejected input, or native tool output.

Counterexample search may remember the lowest canonical failure while still
finishing the full exploration required for complete coverage counts. Result
identity is invariant under source ordering. Replay rejects any changed model,
catalog, profile, checker, bound, explored count, derived carrier, claim,
outcome, or counterexample digest.

The negative suite must cover the issue's six boundaries independently:
pair-probe incompleteness, supervisor decision/omission observation, an active
strategy leak, coalition/memory/policy-change drift, single-linearization
promotion, and possibilistic-to-probabilistic promotion. Each mutation changes
one semantic fact and both #961 and #962 must reject or falsify it at their
respective admission/execution boundary.

## Canonical Incumbents To Reuse

| Concern | Canonical incumbent and required use |
| --- | --- |
| Opacity semantics | ADR-099, `specs/formal/participant-semantics/participant-predicate-opacity.md`, and catalog relation `participant-predicate-opacity`; do not redefine possible points, information cells, strategies, memory, release, supervisor visibility, or relation boundaries. |
| Relation profile and claim | `BehavioralRelationProfileModel`, `load_behavioral_relation_profile()`, `BehavioralClaimBindingModel`, `load_behavioral_relation_catalog()`, `validate_behavioral_claim_binding()`, and `tools/check_behavioral_relation_claims.py`. |
| #961 primitives and kernel | `raes_contracts.participant_opacity`, `raes_processor.participant_opacity`, canonical information-cell construction, finite domain admission, outcome/counterexample vocabulary, deterministic ordering, and replay. Extract and reuse the kernel; do not relabel its bounded evidence. |
| Explicit-state exploration | `raes_processor.exploit_path` normalized graph, preflight, canonical graph traversal, explored counts, typed unsupported outcome, deterministic witness, and replay patterns. Its depth-bound semantics do not apply to a complete model check. |
| Tool/evidence identity | `SolverConfigurationModel`, checker-configuration digests, `canonical_json_digest()` / `canonical_contract_digest()`, exact tool pins, and source/model/configuration joins. |
| Closed ingress and diagnostics | `parse_bounded_json_object()`, `ContractModel(extra="forbid")`, `DiagnosticModel`, stable domain codes, bounded generic messages, and the existing `ParticipantOpacityOperationalError` / `ParticipantOpacityEvidenceError` boundary. Expected unsupported or vacuous cases are values; add no model-check exception hierarchy. |
| CLI seam | Existing `raes processor` Typer application and its analyzer exit-code/error conventions, only if a reproducibility command is added. Do not add another executable or place model content in argv. |
| Artifact persistence | Canonical JSON, `redaction_violations()`, safe root-confined labels, `run_artifact_path()`, and `atomic_write_json_artifact()` if durable archival is added. The checker itself remains read-only and owns no store. |
| Schema publication | `schema_bundle()`, formal-analysis schema routing, hand-governed `contracts/schemas/`, `raes_conformance.conformance.validators` for structural contract conformance, valid/invalid fixtures, publication entries and `last_change` hashes, generated-schema parity, and JSON artifact validation. The validator registry is not backend conformance evidence. |
| Packaging | `corpus_family_root()`, wheel/sdist corpus force-includes, installed/source parity tests, and package facade/export tests. |
| Workflow | `.ground-control.yaml`, `.gc/plan-rules.md`, the canonical nox `verify` graph, repo policy, requirement governance, concept/claim/schema/docs gates, and `tools/verify_all.py`. Branch `962-model-check-opacity` contains no requirement UID, so governed commands use `RAES_REQUIREMENT_UID=ASR-535`. |

Package boundaries remain intact: `raes_contracts` owns portable transition
model and evidence contracts; `raes_processor.participant_opacity` owns
admission, exploration, relation evaluation, and replay; optional CLI rendering
stays in `raes_cli.processor`. `raes_runtime`, `raes_conformance`,
`raes_backend_protocols`, and `raes_operations` do not become model-check
authorities.

## Cross-Cutting Layers And Security Posture

1. **Profile/config ingress.** Profile ids are grammar-checked before path
   construction and resolved only through the packaged/source corpus. Model
   input is bounded duplicate-rejecting UTF-8 JSON with an object root. There
   is no YAML expression, Python import path, remote URL, `latest` alias,
   caller-selected production corpus root, or environment-bound semantic
   default.
2. **Closed schema and semantic gate.** The published schema,
   `ContractModel`, canonical-order validators, graph-reference validators,
   exact count/digest validators, and catalog/profile/claim join all pass before
   exploration. Published JSON Schema and Python generation stay identical;
   cross-field invariants remain Pydantic validators with
   `x-raes-invariants`, not duplicated ad hoc checks.
3. **Finite-model and quantifier gate.** Initial states, transitions,
   strategies, scheduler/environment pairs, order variants, evaluation cuts,
   reachable fixed point, and declared/explored counts must agree. Unsupported
   time, probability, concurrency, partial-order, coalition, or active
   semantics fail closed until the checker configuration explicitly supports
   them. No partial run can enter the model-check evidence state.
4. **Authentication and authorization boundary.** The intended checker is a
   local read-only processor and crosses no HTTP, RUN-319, API-407, runtime, or
   backend authorization surface. It therefore makes no authentication,
   enforcement, or realization claim. Any future HTTP exposure must reuse
   `create_control_plane_app()`, `ControlPlaneSecurityConfig.strict_defaults()`,
   verified identity/role/target binding, request-size guards,
   fingerprint/idempotency, and audit; no unauthenticated analysis route is
   added.
5. **Secret-handling gate.** Profiles, model fixtures, counterexamples,
   diagnostics, evidence, logs, and CI artifacts contain only synthetic bounded
   values, safe ordinals/refs, counts, and digests. Raw possible worlds, secret
   values, observation content, memory, policy/supervisor internals,
   credentials, environment dumps, and host/native objects are excluded.
   Hashing secret-bearing content does not make it a safe portable identifier.
6. **Diagnostic and error-envelope gate.** Expected non-positive results are
   typed values with stable codes, schema-derived addresses, and bounded
   generic messages. Never concatenate `str(exc)`, Pydantic `input_value`,
   rejected keys/ids, tracebacks, stdout/stderr, or model contents into
   diagnostics, CLI stderr, logs, audit, or evidence. A future HTTP wrapper
   retains the incumbent `{"detail":"internal server error"}` envelope.
7. **Artifact and persistence gate.** Validate the complete evidence, claim,
   counterexample, and redaction posture before serialization. If archived,
   use safe root-confined names and atomic writes. Do not put the result in
   `RuntimeSnapshot.metadata`, `AuditEvent`, operation details,
   `BackendConformanceReport`, a mutable database, or a new evidence service.
8. **CLI, environment, and OS/process gate.** The default in-process checker
   needs no secret loader, dotenv, subprocess, shell, socket, network, daemon,
   privilege, or native backend. Model/profile contents, secrets, witnesses,
   credentials, and complete results never enter argv, environment variables,
   filenames, shell history, or host logs. An optional existing CLI command
   passes only a neutral input path and governed profile id and emits validated
   JSON; the portable source id comes from validated content rather than an
   absolute or sensitive host path, and failures remain value-free.
9. **Logging and observability gate.** Progress logs are not evidence. The
   default service emits no model-state or transition logs; exact declared and
   explored counts live in the validated evidence envelope. Unexpected
   failures may be named by safe exception class at an outer boundary but never
   include exception text or model content.
10. **Governance/publication gate.** Any new public model/evidence schema
    updates the hand-governed schema, schema bundle, semantic invariants,
    valid/invalid fixtures, publication entry/hash, validator routing,
    packaging, and compatibility assessment together. A catalog assurance
    change advances the taxonomy revision and every current producer. No
    issue-local verification script bypasses the canonical workflow.

## Whole-Repository Surfaces In Scope

- **Normative and concept authority:** ADR-099, SEM-231, behavioral relation
  catalog/reader-facing specification, relation profile, claim validation, and
  assurance aggregates.
- **Portable contracts:** the existing opacity/profile primitives, a distinct
  finite transition-model input and model-check evidence shape, schemas,
  fixtures, invariants, publication records, and corpus packaging.
- **Processor:** participant-opacity admission, canonical explicit-state
  traversal, shared opacity kernel, counterexample selection, evidence
  assembly, replay, and optional existing CLI projection.
- **Verification:** graph closure/count/digest tests, all quantifier domains,
  fixed-point completeness without depth truncation, #961 agreement,
  single-fault mutations, vacuity/unsupported/operational boundaries,
  permutation determinism, secret/error sanitization, replay drift, schema and
  installed-corpus parity, claim-policy checks, docs, and canonical
  verification.
- **Host/runtime:** local hermetic in-process execution, deterministic
  pre-admission resource caps, no ambient credentials or network, and safe
  artifact handling. Runtime, backend, conformance, and control-plane layers
  are explicit non-traversed boundaries.

## Extensibility Seam

The stable seam is:

```text
catalog relation
  -> resolved closed relation profile
     -> exact finite transition model
        -> canonical reachable fixed point
           -> shared SEM-231 possible-point kernel
              -> axis-specific model-check evidence and replay
```

The required parameter is the resolved relation profile; the model-check
service must not hard-code observer, strategy, scheduler, environment, order,
memory, release, or supervisor assumptions outside it. The explorer has a
closed capability declaration for supported profile dimensions and an
evaluation-point projection seam that converts reachable states to the existing
opacity point primitive.

A new passive or active strategy set, observer, coalition, memory scope,
release schedule, scheduler/environment domain, or total-order variant adds a
profile/model artifact without changing the opacity kernel. A timed,
probabilistic, quantitative, progress-sensitive, or true partial-order property
may require a new tool or relation; the seam must reject it rather than encode
it as an unvalidated option.

## Gotchas And Anti-Patterns

Avoid:

- changing only the #961 claim axis from `bounded-test` to `model-check`;
- treating `complete_enumeration=true`, a supplied `reachable` flag, a depth
  limit, sampled schedule, pair probe, property test, or fixture corpus as a
  reachable-state model check;
- duplicating the SEM-231 information-cell algorithm in a second checker or,
  conversely, relabeling #961 evidence instead of deriving reachability;
- trusting caller-supplied information-cell ids, observation equality, or
  strategy coverage;
- stopping at the first counterexample and reporting full explored coverage;
- allowing active actual and witness runs to use different strategies, or
  omitting one declared strategy because passive traces passed;
- inferring coalition opacity from individual checks or episode-local opacity
  after memory fusion, retry, policy change, release, or handoff;
- treating hidden supervisor implementation as hidden decisions, behavior,
  omissions, timing, order, retries, action availability, or external effects;
- treating an omission as observable without a declared opportunity basis;
- promoting one named linearization to all linearizations, concurrency, causal
  frontier, or partial-order semantics;
- promoting possibilistic support to a probability bound, posterior,
  quantitative leakage, entropy, or differential-privacy statement;
- calling a finite model-check result an unbounded proof, runtime enforcement,
  backend realization, conformance, policy noninterference, projected-history
  equality, epistemic indistinguishability, trace relation, simulation,
  refinement, or bisimulation;
- creating another relation/profile registry, claim DTO, result vocabulary,
  report family, graph framework, exception hierarchy, logger, store,
  executable, endpoint, auth stack, or workflow;
- using Z3 or an external tool merely because it is present, without a property
  or scale requirement that the direct explicit-state explorer cannot meet;
- accepting timeout, skipped work, unavailable tooling, vacuity, cap
  exhaustion, missing mutation, digest drift, or replay mismatch as positive
  evidence;
- changing catalog model-check status before exact evidence and independent
  reproduction exist, or changing it without the required taxonomy-wide
  revision and legacy aggregate consistency;
- mutating catalog or profile bytes without advancing their revisions and
  preserving the exact historical digest binding, or replaying against ambient
  “latest” artifacts;
- echoing rejected values, state/transition refs, observation or memory keys,
  raw counterexamples, exception text, tool output, host paths, or secrets into
  portable surfaces; and
- passing models, profiles, policies, secrets, witnesses, credentials, or full
  evidence through argv, environment variables, filenames, logs, or audit.

## Non-Goals And Implementation Boundary

Issue #962 may add a closed finite transition-model and model-check evidence
contract, implement deterministic complete reachable-state exploration in the
existing participant-opacity processor, reuse the #961 relation kernel, emit
safe digest-bound results/counterexamples with replay, add agreement and
mutation evidence, optionally extend the existing processor CLI, and advance
only the exact model-check assurance facts after reproduction.

It does not:

- redefine SEM-231 or the delivered baseline profile to make a model pass;
- prove unbounded opacity or the future mathematical theorems owned by #963;
- synthesize a supervisor or policy;
- enforce opacity in RUN-319 or add runtime mediation owned by #964;
- declare, realize, or conform a backend feature owned by #965;
- add SDL syntax, a secret-predicate expression language, world-state/history
  store, participant gateway, transport, UI, generic graph platform, hosted
  solver, or proof service;
- establish policy noninterference, projected-history equality, epistemic
  indistinguishability, trace inclusion/equivalence, simulation, refinement,
  bisimulation, timed/progress-sensitive opacity, probability or quantitative
  leakage, or a stronger concurrency/partial-order result;
- certify any model, profile, strategy, scheduler, environment, policy,
  participant, runtime, or backend outside the exact digest-bound checked
  artifact; or
- require network access, ambient credentials, a daemon, subprocess,
  privileged host resource, live participant, runtime, or backend.
