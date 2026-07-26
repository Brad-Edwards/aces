# Issue 897 Autonomous Participant Activity Policy Preflight

Issue: #897

Requirement: none; the issue is the authoritative contract.

Date: 2026-07-26

This note fixes architecture guardrails before implementation. It is not an
implementation plan and adds no schema, compiler, runtime, backend, or release
behavior.

## Decision And Incumbent Authority

Issue #897 extends
`ParticipantBehaviorSpecification.autonomous_execution`, ADR-092, and the
formal autonomous-execution semantics. It does not create a live-activity,
background-actor, benign-user, scheduler, calendar, or randomizer root.

The fixed-cadence `participant-autonomous-execution/v1` profile keeps its
current `ordered_cycle` meaning. The richer contract is a discriminated v2
profile under the same field. This is required because adding optional policy
fields to v1 would make an already-admitted document change meaning under the
same profile id.

The internal authorities to compose are:

- ADR-013, ADR-022, ADR-041, ADR-054, ADR-067, and ADR-085 for participant
  episode, action, implementation, history, behavior, and information-flow
  authority;
- ADR-090 and ADR-091 for exact shared time, clock ownership, lifecycle,
  capability, runtime readback, and realized-time provenance;
- ADR-084 and the EXP-718 random-stream suite for stateless governed draws,
  profile versioning, canonical addressing, exact transforms, and archival
  stochastic provenance;
- ADR-094 for explicit cross-plane owner identity and fail-closed binding
  resolution; an activity policy's stochastic-control reference is not a
  configuration target and must not be inferred from matching names;
- ADR-061 and ADR-075 for schema compatibility, profile/version meaning,
  migration, and release governance; and
- ADR-080 and the SDL lineage ledger for revision-pinned source and internal
  authority traceability.

Existing lineage already records CybORG benign-agent/reset precedent,
Gymnasium/PettingZoo/OpenSpiel participant and chance/ordering boundaries,
ROS 2 clock lifecycle, FMI scheduled execution, HLA time management, TENA
execution/archive separation, and OpenSCENARIO entity/action/trigger
separation. The random-stream research records L'Ecuyer-style semantic streams,
counter-addressable generation, NumPy's seed-versus-algorithm distinction, and
schedule-independent derivation. Issue #897 must extend those existing audit
and ledger claims; it must not add an unpinned second bibliography or imply
wire compatibility.

## Semantic Shape And Boundaries

### Availability and shared time

Work windows are inclusion references and pauses are exclusion references to
existing shared-time `window` constraints. Every referenced constraint resolves
to the policy clock and time domain, is actually of kind `window`, and names
the governed behavior specification or every participant to which the policy
applies as a subject. An unrelated object's window is not reusable merely
because it uses the same clock. Eligibility is the normalized union of work
windows minus pause windows; declaration order is not semantic.

Window endpoint semantics belong to the shared-time authority and must be
defined once over the existing superdense `(tick, microstep)` coordinate before
runtime behavior depends on them. The safe default for adjacent work/pause
windows is half-open `[start, end)`, which avoids executing twice at a shared
boundary. A participant-only competing interpretation is forbidden.

V2 admits finite declared windows. Locale names, IANA time zones, daylight
saving rules, holiday feeds, cron syntax, and host calendars are not portable
time authority. The extension seam for recurring civil calendars is a future
versioned shared-time constraint profile; the participant policy continues to
reference constraints rather than embedding calendar calculation.

Global clock pause/resume remains the existing lifecycle operation. An authored
pause window changes action eligibility; it does not pause the shared clock or
mint a private lifecycle state.

### Bounded deterministic timing

Timing variation is expressed in positive integer ticks on the policy clock,
with explicit inclusive lower/upper bounds and finite occurrence/attempt
budgets. The next eligible coordinate is a pure function of the admitted
policy, prior typed scheduler state, shared-time state, and addressed draw.

No implementation may clamp an out-of-window draw, redraw until a convenient
time appears, consult wall time, sleep outside the existing clock driver, or
advance a backend/system/external-authority clock. The policy must give one
deterministic disposition for a candidate outside eligibility, such as skip or
move to the next declared opening, and that disposition is part of policy
identity and backend admission. Searching for a next opening is bounded.

Clock transition preflight continues to reject a transition that would skip
the next governed due coordinate. Repeated work at one tick uses superdense
microsteps or an explicit serialized/joint-action record; equal ticks alone do
not mean simultaneous execution.

### Governed random streams

The SDL policy carries a stochastic-control reference, not a seed. The admitted
run/apparatus control has role `agent-policy` and supplies the existing
`RandomStreamControlBindingModel`: exact immutable profile, randomness
namespace, and public seed or governed entropy reference.

SDL validation can prove only the local policy shape and reference syntax.
It cannot claim that an experiment-owned control resolves when no experiment
context is present. Standalone scenario compilation must preserve that
external reference without treating the scenario as executable. The
run-scoped join resolves exactly once by `control_id`, requires role
`agent-policy` and an executable binding, and is sealed into ADR-084's admitted
trial/execution handoff before runtime admission. If that incumbent handoff is
not yet available, it is a delivery dependency or the authority under which a
minimal typed carrier is completed—not permission to place the binding in
`RuntimeSnapshot.metadata`, SDL `spec`, an environment variable, or a backend
constraint string.

This is activity during one run. It is not:

- scenario-family variation, variation-point selection, allocation, blocking,
  factor assignment, or trial compilation;
- permission to reinterpret legacy descriptive stochastic fields as
  executable; or
- permission for a backend to resample after rejection, timeout, retry,
  capability failure, or service failure.

The current `StreamAddressModel` is intentionally experiment-selection-shaped.
Do not place participant values in `selection_policy_id` or
`variation_point_id`. Extend the existing versioned random-stream address
family with a closed participant-runtime variant containing:

- the admitted randomness namespace;
- autonomous policy and participant canonical addresses;
- shared-time segment/reset generation;
- occurrence ordinal;
- governed draw purpose; and
- stable local draw coordinate.

Worker, process, thread, host, queue, map order, wall time, retry count, call
count, backend availability, and aggregate scenario/experiment digests are
forbidden coordinates. Retries reuse the occurrence's timing and selection;
they do not consume a new choice merely because transport or native execution
was retried.

Exact weighted choice uses stable keyed candidate ids and positive integer
weights in canonical candidate order. At least one candidate must be eligible,
the bounded sum must be representable, and dependency filtering happens before
the addressed draw. Floating-point weights, implicit normalization, hash/map
order, library defaults, and repeated sampling are forbidden.

The accepted `blake3-xof-v1` profile is immutable and its address shape is
experiment-selection-specific. Participant-runtime addressing therefore
requires a new immutable profile/version, closed dispatch, published profile
data, independent conformance vectors, and exact backend/apparatus support.
The new profile should reuse the incumbent bounded-integer transform unless a
demonstrated requirement cannot be expressed by it. Bounded timing draws an
integer from the declared inclusive interval. Weighted selection draws an
integer from the bounded total weight and maps it through canonical
candidate-order prefix intervals. Those mappings are participant-policy
semantics and need conformance cases, but they are not a second RNG transform.
Do not edit `blake3-xof-v1` into a different compatibility unit.

### Actions, dependencies, retries, cooldowns, and bursts

V2 action policy uses stable keyed candidates that reference existing
participant action contracts. Candidate identity, weight, dependency guards,
and recovery policy are scheduler policy; applicability, typed preconditions,
effects, portable failure classes, interactions, and service targets remain
owned by `ParticipantActionContract`.

Dependency guards resolve prior typed occurrence/attempt outcomes and explicit
participant or service-state observations already admitted to the participant
boundary. They do not copy service truth into a scheduler state bag, treat a
runtime resource dependency as an action dependency, or infer causality from
timestamps. A causal claim still requires the existing
`ParticipantAttributionEdgeModel` evidence basis.

Dependency graphs are acyclic where statically expressible and must admit an
initial candidate. At runtime an empty eligible set follows one declared
bounded disposition; it never falls back to all actions or the first action.

Retries are new uniquely identified attempts within one occurrence. They are
allowed only for declared portable `ParticipantFailureClass` values, have a
finite per-occurrence bound, and cite the predecessor attempt. A success is
never retried. Protocol-invalid or indeterminate native work is not blindly
replayed. Global action-attempt limits include retries; occurrence, attempt,
success, failure, retry, burst, and in-flight counters remain distinct.

Cooldown is an exact logical-tick eligibility guard on the policy clock.
Limited bursts have a separate positive bound and never reuse
`max_in_flight` as a burst-size alias. The reference runtime may serialize a
burst, but must record realized order and distinct occurrence/action identities.
A backend claiming actual concurrency uses the existing joint-action and
shared-state contracts.

### State, reset, service continuity, and provenance

Continuation extends `ParticipantAutonomousExecutionStateModel` rather than
adding a second store. It carries only the minimum restart cursor and accounting
needed to reproduce the next transition: policy/profile digest, clock segment,
episode/generation identity, next eligibility coordinate, occurrence and
attempt counters, cooldown/burst continuation, and safe random-control/profile
identity. Append-only history, not mutable state, is occurrence evidence.

`ParticipantBehaviorHistoryEventModel` and its API-408 projection are the
occurrence provenance surface. A typed nested record should preserve policy
address/profile, occurrence and attempt ids, predecessor/dependency refs,
selected candidate, timing coordinate/disposition, burst position, safe
random-control/address/transform refs, and terminal outcome. It must not expose
root entropy, derived keys, raw blocks, secret refs beyond their governed safe
identity, complete candidate domains, or backend-private objects.

Every native attempt still passes the current sequence:

1. bind the selected participant implementation and action;
2. execute through `ParticipantRuntime.admit_action`;
3. require a typed terminal action result and exact ordered behavior history;
4. commit native/service snapshot and portable history; then
5. advance scheduler continuation.

A valid terminal failure may have changed service state; subsequent dependency
and retry evaluation uses the returned committed snapshot. A protocol-invalid
result restores the predecessor portable snapshot and consumes identity without
claiming native rollback.

Shared-clock reset continues through the capability-specific atomic
`reset_with_participants` plus participant `reset_many` transaction. Only after
that transaction succeeds may scheduler generation change. The new time segment
and participant episode start a new occurrence generation whose random address
includes the segment; predecessor episode/generation lineage remains
observable. Service state is whatever its owning backend lifecycle actually
preserves or resets—scheduler state cannot fabricate rollback or continuity.

Plan reapplication preserves continuation only when the complete resolved v2
policy, windows, time declarations, stochastic-control/profile identity, action
entries, weights, dependencies, recovery rules, and bounds match the policy
digest. Any material drift fails before mutation.

## Canonical Cross-Cutting Incumbents

| Layer | Incumbent to extend |
| --- | --- |
| Authored SDL shape | `raes.participant_execution.ParticipantAutonomousExecutionPolicy`; `ParticipantBehaviorSpecification.autonomous_execution`; `SDLModel` closed-shape validation |
| Source ingress | `raes.parser.parse_sdl`, `load_sdl_yaml`, YAML 1.2 core resolution, duplicate/merge-key checks, `SDLParserLimits` |
| Semantic validation | `raes.semantics.participant_behavior` and `raes.validator._participant_execution_renderers`; `raes.validator._time_model` |
| Shared time | `raes.time_model`, `raes_processor.compiler.time_model`, `CompiledTimeModel`, `RuntimeTimeControlMixin`, and time capability admission |
| Canonical compilation | `_compile_autonomous_execution`, `ParticipantAutonomousExecutionRuntime`, compiled-address helpers, the stable v1 `_policy_digest`, and `canonical_contract_digest()` for a new typed v2 resolved-policy identity |
| Random streams | `RandomStreamControlBindingModel`, `ExperimentStochasticControlModel`, versioned random-stream profiles/corpus, controlled draw-purpose vocabulary, stateless engine and bounded-integer transform, RFC 8785/JCS canonicalization, diagnostics, and vectors |
| Cross-plane binding | ADR-094 owner/binding discipline and admitted trial/run carriage; do not reuse `ExperimentBindingDescriptorModel` as a stochastic-control DTO or infer a control from matching ids |
| Planning/admission | `participant_autonomous_execution_capability_gaps`, `_participant_execution_diagnostics`, backend `ParticipantRuntimeCapabilities`, `TimeCapabilities`, and exact manifest conversion |
| Runtime target gate | `RuntimeTarget` registry probes and capability-specific participant/time protocols |
| Execution | `ParticipantScheduler`, `participant_scheduler_operations`, `autonomous_action_result_violation`, `RuntimeParticipantExecutionMixin`, and `ParticipantClockDriver` |
| Persistence | `RuntimeSnapshot.participant_autonomous_execution_states`, `require_participant_autonomous_runtime_snapshot`, `ControlPlaneStore`, `LocalControlPlaneStore`, and API snapshot conversion |
| Occurrence evidence | `ParticipantBehaviorHistoryEventModel`, `ParticipantHistoryViewBehaviorEventModel`, participant retrieval projection, action-result/temporal-context/attribution contracts, and experiment-run stochastic draw provenance |
| Conformance | `raes_conformance.conformance.snapshot_semantics`, schema fixtures, backend-manifest fixtures, random vectors, and cross-process determinism witnesses |
| Publication/workflow | authored `contracts/schemas/`, `schema_bundle()` parity, `contracts/schema-publication-manifest.json`, release-please, the canonical nox `verify` graph, and Ground Control issue/PR checks |

Do not duplicate these models in a scenario-pack DTO, backend adapter, API
request, or persistence repository.

## Security And Whole-Path Gates

1. **SDL source gate.** Policy input passes input-byte, scalar, depth, node,
   alias, import, composition, and namespace limits; safe YAML construction;
   duplicate/merge-key policy; closed Pydantic shape; then semantic validation.
   Candidate ids, integer weights, bounds, references, and graph sizes need
   explicit limits before compilation. Unknown v2 fields fail; they are not
   stored as extensions.
2. **Experiment/config gate.** The stochastic control passes the existing
   `ExperimentSpecModel`/apparatus/run shapes,
   `ExperimentStochasticControlModel`, and
   `RandomStreamControlBindingModel`. The run-scoped join—not standalone SDL
   validation—must resolve a policy reference exactly once to role
   `agent-policy`; profile, namespace, and control identity must agree across
   admitted execution handoff, runtime, draw, and run provenance. Do not add
   another YAML loader, configuration descriptor, config registry, or generic
   metadata bag.
3. **Secret gate.** Public fixed-width seeds and governed entropy references
   remain the existing closed union. The current reference engine executes
   public seeds only; issue #897 does not authorize inventing a secret resolver.
   A governed reference fails admission unless a separately governed,
   authorized in-process resolver already exists and verifies immutable
   version, caller/scope, purpose, and byte length. SDL,
   environment-variable names, URI credentials, file paths, and backend
   constraint strings are not secret-resolution mechanisms.
4. **Authentication/authorization gate.** Issue #897 needs no new endpoint.
   Existing API-408 history/status retrieval remains behind
   `ControlPlaneSecurityConfig.strict_defaults()`, bearer or verified-proxy
   identity, read-role/target checks, request-size guards, and audit events.
   If a later mutation endpoint is proposed, it requires the existing
   operator/backend authorization and idempotency path; policy presence does
   not grant participant control or entropy-read authority.
5. **Compiler and admission gate.** All refs compile to canonical addresses;
   semantic validation proves role/evaluation and graph/window invariants;
   planning proves exact participant policy/profile/strategy/action/
   observation/target/random/time support and finite maxima. Manifest booleans,
   free-form `constraints`, installed libraries, or native method presence are
   not substitutes for exact claims.
6. **Runtime protocol gate.** Registry signature probes still require native
   binding and coordinated reset methods when claimed. Runtime validates every
   action result, history append, clock/episode/generation binding, counter
   equation, and policy digest before durable commit. Retry never bypasses
   native binding or typed terminal outcome validation.
7. **Persistence/conformance gate.** Save, load, API conversion, and conformance
   all invoke the canonical autonomous snapshot invariants. Random continuation
   does not live in `RuntimeSnapshot.metadata`, operation `details`, tags, audit
   details, or a new seed database. Unknown, contradictory, or stale state
   fails closed.
8. **OS exposure gate.** Draws execute in process through the stateless engine.
   Seeds, governed refs, derived keys, candidate sets, selected values, and
   participant stream addresses never enter environment variables, process
   argv, shell interpolation, temporary command files, or `shell=True`.
   `PYTHONHASHSEED` may vary only as test apparatus and never enters semantics.
9. **Error-envelope gate.** Authoring failures use existing
   `SDLParseError`/`SDLValidationError`; operational failures use bounded
   `Diagnostic` values with safe code, domain, canonical concern address,
   profile id, and counts. Do not add an activity exception hierarchy or echo
   raw Pydantic input, entropy, complete weights/candidates, backend exception
   strings, environment, or traceback. HTTP retains the generic redacted 500
   envelope.
10. **Logging/observability gate.** Scientific inspection uses typed snapshot,
    behavior history, random-draw, run, and conformance records. Logs and audit
    events may carry safe ids, profile versions, counts, stage outcomes, and
    durations only—not entropy, derived material, candidate domains,
    selections, sensitive service state, or raw backend failures.

## Compatibility, Extensibility, And Traceability

- V1 documents and manifests retain their exact fixed-cadence meaning. V2 is
  opt-in and unsupported consumers reject its profile before provisioning.
- V1 policy-digest bytes remain stable for persisted snapshots. V2 identity
  uses a typed resolved-policy payload plus the incumbent
  `canonical_contract_digest()` rather than extending the scheduler's ad hoc
  JSON hashing or introducing another canonicalizer.
- The authoring/compiled/runtime/schema discriminators, random-stream profile,
  participant address variant, backend feature terms, and occurrence provenance
  version independently. A package version or schema filename does not stand in
  for any of them.
- The main extensibility seam is the v2 policy's closed strategy/profile ids
  plus stable keyed action entries. A new selection or timing strategy adds an
  exact policy mapping and capability term without editing existing profile
  semantics; it adds a random transform only when the incumbent bounded-integer
  transform cannot express the operation. A future recurring civil calendar
  extends shared-time constraint authority, not the participant scheduler.
- Published schema edits require hand-governed schema changes, matching
  `schema_bundle()` output, fixtures, and a `last_change` summary/hash in the
  schema-publication manifest. Breaking stable changes mint a new contract
  lineage; current draft status does not excuse unrecorded drift.
- Migration guidance must show v1 unchanged and an explicit v1-to-v2 authoring
  example. There is no automatic migration from `action_order` to weighted
  candidates, because weights, dependencies, recovery, windows, and stochastic
  control cannot be inferred.
- There is no formal Ground Control requirement UID; do not invent one. Issue
  #897 is the contract and must link the ADR/design decision, implementation
  files, focused and conformance tests, the PR, and the release. The external
  consumer link is `autarchy-ai/penumbra-scenarios#556`.
- Release trace uses a consumer-visible Conventional Commit/PR title so
  release-please creates the package release. Do not edit `CHANGELOG.md`, add a
  fragment, or hand-edit `_version.py`.

## Gotchas And Anti-Patterns

Avoid:

- a parallel live-activity actor, service, scheduler, clock, calendar, policy
  root, action schema, snapshot map, or provenance stream;
- changing v1 semantics through optional fields or treating absence as a new
  default;
- embedding raw seed material in SDL or copying a stochastic control into each
  action/occurrence;
- overloading pre-run `selection_policy_id`/`variation_point_id` as runtime
  coordinates;
- mutable RNG cursors, process-global randomness, floating weights, modulo
  bias, resampling, fallback actions, map-order choice, or retry-driven draws;
- a duplicate weighted-choice RNG transform or misuse of cross-plane
  configuration descriptors as stochastic-control bindings;
- cron, host locale/time zone, wall clock, sleep, or operational watchdog time
  as shared scenario time;
- clamping timing into a window, silently skipping a missed due coordinate, or
  allowing reset/reapply to change a policy without changing its digest;
- using `refresh_dependencies` or service placement graphs as action-policy
  dependencies;
- treating a failed action as no state change, retrying a success, replaying an
  indeterminate native call, or claiming copied snapshots roll back backends;
- treating same-tick burst actions as simultaneous without microstep/order or
  joint-action evidence;
- duplicating validation in compiler/runtime after a semantic helper can own
  it, or adding a new exception, diagnostic, logger, audit, schema registry,
  store, loader, CI workflow, or conformance runner; and
- claiming human realism, causal proof, service fidelity, exactly-once native
  execution, or production backend support from reference scheduler tests.

## Non-Goals And Implementation Boundaries

- No KeplerOps, Penumbra, pack-local role, product, workflow, action, service,
  or historical-content semantics enter RAES.
- The policy does not allocate trials, vary scenario structure, assign
  experiment factors, score participants, interpret outcomes, or grant
  evaluator authority.
- It does not introduce a general workflow engine, behavior tree, expression
  language, state-machine DSL, cron/calendar service, secret manager, HTTP
  endpoint, worker queue, or general-purpose RNG plugin system.
- It does not implement governed-secret resolution; the reference path remains
  limited to public seeds unless that capability is separately governed.
- It does not define externally paced transition notifications; ADR-092's
  fail-closed boundary remains.
- It does not guarantee human-like behavior, unpredictability, cryptographic
  secrecy, environmental replay, backend fidelity, native rollback, or causal
  attribution.
- The reference runtime owns portable scheduling semantics and evidence.
  Backend-native optimizations are allowed only when exact admission,
  observable ordering, state, history, provenance, and conformance remain
  equivalent.
