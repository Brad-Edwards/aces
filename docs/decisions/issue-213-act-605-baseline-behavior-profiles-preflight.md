# Issue #213 — ACT-605 Baseline Behavior Profiles Preflight

Date: 2026-08-01

Issue: #213.

Requirement: ACT-605.

This note records the architecture boundary for reconciling ACT-605 with the
current repository. It is implementation guidance only: it does not amend
ADR-092, change the formal specification or SDL, modify a published contract,
claim a backend realization, change Ground Control traceability, or transition
ACT-605 from `DRAFT`.

## Finding

The current architecture already satisfies ACT-605 end to end. Ordinary user,
automation, and ambient scenario activity is authored as
`ParticipantBehaviorSpecification.autonomous_execution` and executed by
ordinary participants under ADR-092 and the shared-time model. A
non-evaluated autonomous participant is an existing `green` participant, not a
background actor.

The remaining gap is reconciliation only:

- ADR-092 and
  `specs/formal/participant-semantics/autonomous-execution.md` define the
  required behavior but do not identify ACT-605 explicitly;
- `docs/explain/sdl/limitations.md` still lists “User behavior profiles” as an
  SDL expressiveness gap even though the v2/v3 autonomous policy surface is
  delivered; and
- the supplied Ground Control inventory contains issue-level `DOCUMENTS`
  links but no current code-level `IMPLEMENTS` or test-level `TESTS` evidence,
  while ACT-605 remains `DRAFT`.

No new ADR, schema, model, validator, compiler path, runtime service, backend
protocol, persistence carrier, API route, or test framework is warranted. If
the focused verification remains green, the implementation boundary is an
in-band ADR-092 amendment, a formal-specification clarification, correction of
the stale limitation, and external traceability/status reconciliation.

## Concept And Authority Boundaries

| Concern | Canonical owner | ACT-605 boundary |
| --- | --- | --- |
| Authored behavior | `ParticipantBehaviorSpecification.autonomous_execution` and `ParticipantAutonomousExecutionPolicyV1/V2/V3` | No `baseline_behavior`, `background_activity`, or pack-local profile root |
| Participant identity and role | Existing `agents`, participant roles, episodes, and implementation selection | `evaluation_authority.mode: none` requires existing `green`; “ambient” does not create another actor kind |
| Actions and observations | Existing participant action contracts, observation boundaries, native admission requests, and behavior history | A profile selects already-authorized actions; it does not widen action, target, observation, or evaluation authority |
| Time | ADR-090/091 shared clocks, progression policies, constraints, lifecycle, and provenance | No private clock, cron authority, host calendar, or background scheduler |
| Baseline policy | V1 fixed cadence and ordered cycle; v2 work/pause windows, bounded timing, weighted candidates, dependencies, retries, cooldowns, bursts, and finite limits | Profile version changes are explicit; v1 meaning and persisted digests remain stable |
| Resource governance | V3 scoped resource budget and ADR-097 | Resource priority/fairness is explicit and role-neutral; it is not inferred from `green` or “background” wording |
| Evaluation | `ParticipantEvaluationAuthority`, objectives, evaluator-plane contracts, ADR-073, and ADR-092 | Action execution never implies score, proof, receipt, adjudication, or outcome authority |
| Native realization | Exact execution bindings, participant-runtime capability/admission, lifecycle/readback, and conditional live conformance | Capability declarations permit admission but do not prove activity, service fidelity, or evidence |
| Durable evidence | Typed scheduler state, execution-service state, behavior history, shared-time state/provenance, resource state/events, and `RuntimeSnapshot` | Logs, metadata, timestamps, and control-operation success are not behavior evidence |

“Baseline profile” is requirement language for an autonomous participant
policy, not a new contract-family name. “Background” describes its scenario
purpose, not an execution plane, priority class, daemon, or hidden actor.
Service-internal maintenance that is not participant behavior remains owned by
the applicable service/runtime contract; exercise injects remain orchestration.

## Reconciliation Guardrails

ADR-092 is accepted and acceptance-content pinned. Any ACT-605 wording change
must follow ADR-059 in the same change: add a `#213` row to the ADR's
`## Amendments` table, add the matching amendment entry in
`docs/decisions/adrs/adr-index.yaml`, and update the canonical-content pin.
Editing the ADR without all three is invalid even when the prose change is
small.

The ADR and formal specification should identify ACT-605 as covered by the
existing autonomous-participant decision and invariants. They must not give
ACT-605 separate normative semantics or restate the policy in a way that can
drift from the v1/v2/v3 contract. The limitations table should remove the
false expressiveness gap. Any residual human-realism or production-fidelity
limitation belongs with the existing nonclaims; it is not a reason to retain
“User behavior profiles” as a missing SDL surface.

No published schema changes are implied. In particular, do not touch the
hand-governed SDL, backend-manifest, runtime-snapshot, behavior-history, or
control-plane schemas, their generated `schema_bundle()` counterparts, or the
schema-publication manifest unless focused verification first proves a real
contract mismatch. Documentation must describe the shipped contract rather
than change it to manufacture ACT-605-specific vocabulary.

Ground Control should point ACT-605 at the current canonical repository
identity (`OpenRAE/rae#213` and current repository paths), while preserving
historical issue links only as lineage. `DOCUMENTS`, `IMPLEMENTS`, and `TESTS`
must remain distinct: an issue or ADR is not an implementation link, and a code
file is not test evidence. `ACTIVE` is justified only after the repository
artifacts, focused verification, and those link sets agree.

## Canonical Cross-Cutting Incumbents

| Layer | Incumbent to reuse |
| --- | --- |
| Source ingress | `parse_sdl`, `load_sdl_yaml`, YAML 1.2 core resolution, duplicate/merge-key checks, `SDLParserLimits`, import/composition limits, and closed `SDLModel` shapes |
| Authored policy | `raes.participant_execution`, `ParticipantBehaviorSpecification.autonomous_execution`, and the existing v1/v2/v3 discriminated policy union |
| Semantic validation | `raes.semantics.participant_behavior`, `raes.validator._participant_execution_renderers`, `raes.validator._time_model`, and `_participant_resource_budget_owners` |
| Compilation | `_compile_autonomous_execution`, `ParticipantAutonomousExecutionRuntime`, `ParticipantExecutionBindingRuntime`, canonical address helpers, and canonical contract digests |
| Shared time and randomness | Existing time models/compiler/runtime controls; `RandomStreamControlBindingModel`, admitted `agent-policy` stochastic control, governed profile/corpus, stateless engine, and bounded-integer transform |
| Planning and manifest admission | `ParticipantRuntimeCapabilitiesModel`, `ParticipantRuntimeCapabilities`, manifest round-trip adapters, `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`, `participant_autonomous_execution_capability_gaps()`, resource-budget admission, and planner diagnostics |
| Runtime target and execution | `RuntimeTarget`, `BackendRegistry`, capability-specific participant/time protocols, `ParticipantScheduler`, `RuntimeParticipantExecutionMixin`, `ParticipantClockDriver`, `ParticipantActionApplyResult`, and `autonomous_action_result_violation()` |
| Lifecycle and control | Existing participant-execution bindings, generation-fenced control/readback contracts, `RuntimeControlPlane`, operation receipts/status, idempotency records, and coordinated reset protocols |
| Persistence | `RuntimeSnapshot.participant_autonomous_execution_states`, execution-service/resource carriers, participant behavior history, time-model state, `require_participant_autonomous_runtime_snapshot()`, `ControlPlaneStore`, and local/in-memory stores |
| Errors and observability | `SDLParseError`, `SDLValidationError`, bounded `Diagnostic`, `AuditEvent`, typed operation/snapshot/history/evidence records, and the redacted HTTP 500 envelope |
| Conformance | Participant execution live probes, snapshot semantics, backend profiles/manifests, published fixtures, and the focused DSL-437/#898/#899 negative and lifecycle tests |
| Publication and workflow | ADR-059 pin gate, `.ground-control.yaml`, `.gc/plan-rules.md`, schema/publication policy, canonical nox `verify`, repository-policy and requirement-governance checks, Ground Control traceability, and release-please |

These incumbents already own the concern. Do not duplicate them as an ACT-605
DTO, validator, exception hierarchy, scheduler, controller, repository, audit
stream, logger, schema generator, fixture runner, or workflow script.

## Whole-Path Security And Validation Gates

1. **SDL source and shape.** An authored baseline policy continues through
   byte/scalar/depth/node/alias/import/composition limits, safe YAML
   construction, duplicate/merge-key policy, the closed Pydantic model, and
   semantic validation. Unknown “background” fields fail rather than becoming
   extensions or metadata.
2. **Reference and authority validation.** Participant, role, action,
   observation, clock, progression, window/cadence, stochastic-control,
   resource-owner, objective, implementation, and target refs resolve through
   existing registries and canonical addresses. Non-evaluated role and
   authority-widening checks remain fail closed.
3. **Configuration and secrets.** Participant implementation configuration
   stays behind `ConfigurationTargetRegistryModel`, literal versus
   `secret-reference` validation, selection/configuration digests, and the
   authorized sink. SDL policies, manifests, snapshots, histories,
   diagnostics, and provenance carry safe refs/digests, never resolved
   credentials or raw entropy. ACT-605 requires no new environment binding or
   secret resolver.
4. **Manifest and backend admission.** Closed manifest models, controlled
   vocabularies, exact profile/feature/strategy/action/observation/target/time/
   random/resource support, relational execution bindings, required contract
   ids, and positive finite limits must agree. Booleans, installed libraries,
   method presence, or separate action/target lists are insufficient.
5. **Runtime target and native commit.** Registry probes require claimed
   capability-specific methods. Each action is generation fenced, invokes the
   selected native binding, returns a typed terminal outcome, appends the exact
   ordered behavior history, and passes snapshot/history/state validation
   before durable commit. Control-operation success is not action success.
6. **Authentication and egress.** ACT-605 adds no endpoint or caller-controlled
   input. Existing execution control and readback stay within
   `create_control_plane_app()`, `ControlPlaneSecurityConfig.strict_defaults()`,
   bearer or verified-proxy identity, role/target checks, request-size guards,
   request fingerprints, idempotency, and audit. Policy presence grants no
   control, participant-subject, evaluator, or secret-read authority.
7. **Persistence and conformance.** Save, load, API projection, and conformance
   reuse the canonical autonomous-state, clock-segment, episode, lifecycle,
   generation, accounting, and append-only history invariants. No state belongs
   in `RuntimeSnapshot.metadata`, operation details, log text, or a new store.
8. **OS and process exposure.** The reference scheduler and random engine stay
   in process. A backend adapter remains an impure leaf using preconfigured
   targets, fixed argv when a process is unavoidable, no shell, bounded
   time/input/output, controlled working directory/environment, and no
   credentials, policy payloads, entropy, or action data in argv. ACT-605 adds
   no CLI, subprocess, socket, daemon, host service, environment variable, or
   temporary-file surface.
9. **Errors and observability.** Authoring failures use the existing SDL error
   types; planner/runtime failures use bounded diagnostics and typed operation
   records; unexpected HTTP failures retain the generic redacted 500 response.
   Do not expose raw Pydantic inputs, candidate sets, weights, entropy,
   credentials, adapter errors, backend reprs, paths, command output,
   environment dumps, or tracebacks. Typed history/snapshot/evidence is the
   scientific observability surface; logs and audit carry only safe,
   low-cardinality identifiers, codes, counts, generations, and durations.

The reconciliation itself should not cross any runtime, auth, secret, config,
or OS boundary; it documents the boundary already enforced by those layers.

## Evidence And Traceability Boundary

The primary implementation links should identify the existing authored model,
semantic validator, compiler, capability admission, scheduler/native-result
validation, and durable-state validator/store. The primary test links are:

- `test_dsl_437_benign_participant_execution.py` for parsing, semantic
  rejection, v1/v2 compilation, exact admission, shared-time execution,
  retries, cooldowns, bursts, reset, native outcome, and wall-driver cases;
- `test_dsl_437_evaluation_authority.py` for evaluator-plane separation;
- `test_dsl_437_snapshot_durability_conformance.py` for save/load/API/
  conformance and clock/episode contradictions;
- `test_issue_898_participant_execution_control.py` for relational bindings,
  lifecycle/readback, generation fencing, authentication, concurrency, and
  conditional live conformance; and
- `test_issue_899_participant_resource_budgets.py` for the v3 policy,
  admission, resource accounting, reset reconciliation, and isolation.

Preflight verification passed 112 focused cases across those files. The HTTP
case `test_control_plane_exposes_authenticated_generation_bound_execution_control`
initially timed out while entering Starlette `TestClient`, before it issued its
first request or reached an ACT-605 assertion. Its isolated rerun passed, and
the subsequent focused suite passed all 113 cases. The canonical completion
suite also passed before publication.

Reference-backend tests prove portable protocol behavior, not a production
adapter, realistic human behavior, workload fidelity, or actual scenario
activity. Ground Control links and public prose must preserve that claim
boundary.

## Extensibility Seam

The stable extension seam is the versioned autonomous policy profile plus
stable keyed action candidates and exact backend execution bindings. A new
timing or selection meaning mints a new profile/capability term while preserving
v1/v2/v3 semantics. A new product or service adds an admitted action-to-target
binding and evidence behind the incumbent participant-runtime protocol. A
future civil-calendar constraint extends shared-time authority, not the
participant scheduler.

This seam lets additional ordinary user, automation, or ambient activities
reuse the same participant/action/observation/time/evidence path without
reopening ACT-605 or editing a central “baseline activity” catalog. If a future
variation cannot be expressed by the existing bounded-integer transform or
contract version, it receives a separately versioned governed profile rather
than an optional field that changes historical meaning.

## Gotchas And Anti-Patterns

- Do not equate `green`, non-evaluated, background, low-priority, hidden,
  harmless, deterministic, or non-adversarial. These are different concerns.
- Do not turn “ambient scenario activity” into host/runtime noise, a service
  daemon ontology, exercise injects, historical files, or pack-local workflow.
- Do not infer action authority, target access, observation scope, evaluation
  authority, or backend support from the word “baseline” or from participant
  color.
- Do not introduce a parallel actor, live-activity service, scheduler, clock,
  calendar, action schema, behavior profile root, snapshot map, or evidence
  stream.
- Do not change v1 defaults or digests, silently treat v2/v3 as compatible, or
  use optional fields to alter an existing profile's meaning.
- Do not use cron, wall time, host locale/time zone, sleep, process order, map
  order, mutable RNG state, floating weights, retry-driven draws, or backend
  logs as semantic authority.
- Do not treat control receipt, health, readiness, lifecycle, native outcome,
  scheduler state, participant episode, and behavior evidence as synonyms.
- Do not claim native execution, human realism, fidelity, causality, rollback,
  or exactly-once side effects from schema validity, capability flags, or
  reference tests.
- Do not add code or regenerate schemas merely to create ACT-605-named
  artifacts; trace the requirement to the canonical artifacts that already
  implement it.
- Do not update an accepted ADR without its amendment row, manifest entry, and
  pin, or mark ACT-605 `ACTIVE` before `DOCUMENTS`/`IMPLEMENTS`/`TESTS` evidence
  and verification agree.

## Explicit Non-Goals

- A new background-actor, baseline-profile, ambient-activity, scheduler, time,
  calendar, workflow, daemon, or evaluation ontology.
- New SDL fields, contract versions, backend capabilities, API routes,
  configuration/env shapes, secret resolution, persistence, logging,
  exception, or conformance frameworks.
- Product-, pack-, workload-, service-, or historical-content-specific
  semantics.
- Scoring, objectives, proof or receipt authority, experiment allocation,
  scenario-family variation, inject delivery, or service lifecycle redesign.
- A guarantee of human likeness, stochastic unpredictability, workload
  realism, production throughput, backend fidelity, native rollback, causal
  attribution, or golden-range equivalence.
- A Ground Control status change or external traceability mutation during this
  architecture preflight.
