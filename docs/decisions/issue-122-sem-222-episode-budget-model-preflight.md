# Issue 122 — SEM-222/223, DSL-120/121, ACT-623/624 Episode And Budget Model Preflight

Date: 2026-08-02

Issue: #122. Requirements: SEM-222, SEM-223, DSL-120, DSL-121, ACT-623,
ACT-624.

This note fixes the repository-wide implementation boundary for the joint
episode and resource-budget work. It is guidance only: it adds no SDL syntax,
schema, contract, runtime behavior, endpoint, persistence path, or
implementation plan.

No new ADR is needed. ADR-013 already owns participant episode identity,
lifecycle transitions, terminal reasons, reset/restart boundaries, and the
schema-first processor/runtime boundary. ADR-097 is the proposed authority for
scoped resource budgets, capacity, accounting, fairness, and reset
reconciliation. DSL-120 supplies authored episode structure; it must use those
authorities rather than create a DSL-local lifecycle system.

## Binding Decisions

An authored episode declaration is intent, not an execution record. It may
declare initialization conditions, interaction/turn structure, terminal and
truncation conditions, and reset-related policy, but it cannot assert that an
episode was initialized, a participant observed a turn, a reset occurred, or a
terminal condition was realized. Runtime state and evidence remain owned by
the existing participant-episode state/history contracts, `RuntimeSnapshot`,
and participant observation/evidence carriers.

Keep these axes independent:

- episode **control actions**: initialize, reset, restart;
- current **episode state** and stable participant identity;
- terminal **reason**: completed, timed out, truncated, interrupted;
- authored terminal/truncation **condition** and its evaluated truth/evidence;
- turn/interaction ordering and the ADR-095 decision epoch/state cut;
- time/deadline semantics and their clock/order authority; and
- resource-budget reset/accounting scope and generation.

In particular, truncation is a terminal reason, not a synonym for timeout,
budget exhaustion, cancellation, backend failure, workflow completion, or
process teardown. A budget rejection or exhaustion event has its own
accounting disposition; a declared policy may map that fact to episode
truncation only through an explicit, evidence-bearing semantic transition.
Likewise, reset creates a new episode instance and never rewrites prior
history. It resets only the state explicitly owned by the episode generation;
tenant, shared-service, fleet, persistent-growth, and unreconciled reservation
state follow ADR-097's typed reset/accounting rules.

The authored surface belongs with existing participant behavior specifications
and compiled participant metadata, using canonical addresses and typed refs.
It is not a new workflow language, scheduler, generic state machine, timeout
engine, counter/quota map, backend configuration bag, or top-level parallel
participant model. Reuse the existing closed condition, proposition/assertion,
temporal-constraint, observation-boundary, evidence-requirement, participant
and deployment-identity references; do not duplicate their syntax or resolve
them by name at runtime.

## Canonical Incumbents To Reuse

- **Normative meaning:** ADR-013, ADR-022, ADR-054, ADR-090, ADR-095, ADR-097,
  `specs/formal/participant-semantics/README.md`, and
  `specs/sdl/scientific-scenario-completeness.md`.
- **Authoring and validation:** `SDLModel(extra="forbid")`, `parse_sdl()`,
  `SemanticValidator`, existing participant-behavior specifications,
  `conditions`, propositions/assertions, temporal contracts/constraints,
  evidence requirements, deployment-tenancy identities, and parser limits.
- **Compilation/admission:** existing canonical-address compilation,
  `RuntimeModel`, compiler diagnostics, instantiated-artifact admission,
  planner capability admission, participant execution bindings/services, and
  the existing participant scheduler. Do not add an episode-specific compiler
  or a second admission walk.
- **Portable/runtime contracts:** `ParticipantEpisodeExecutionState`,
  `ParticipantEpisodeHistoryEvent`,
  `iter_participant_episode_snapshot_violations()`,
  `ParticipantResourceBudgetPolicy`, the budget state/event/pool contract
  family, `RuntimeSnapshot`, and the backend participant-reset and
  resource-budget protocols.
- **Errors, persistence, and observability:** `Diagnostic`/`Severity`,
  `OperationReceipt`, `OperationStatus`, `ControlPlaneStore` atomic commit
  methods, idempotency/request fingerprints, `AuditEvent`, snapshot history,
  evidence/provenance contracts, and conformance reports. No new exception,
  event store, audit channel, logger, or `metadata`/`details` side channel.
- **Schema and repository workflow:** hand-governed `contracts/schemas/`,
  `schema_bundle()`, `tools/generate_contract_schemas.py`,
  `tools/check_generated_schemas.py`, schema-publication entries, ADR-061/
  ADR-075 compatibility discipline, `.ground-control.yaml`,
  `.gc/plan-rules.md`, `noxfile.py`, and the repository-policy, requirement-
  governance, and verification gates.

## Required Cross-Cutting Gates

- **Source/config shape:** parser source-size/alias limits, YAML normalization,
  closed Pydantic models, and `SemanticValidator` reject malformed, unknown,
  duplicate, unresolved, cyclic, or cross-scope authored declarations. An
  authored condition/ref is never a free-form backend expression, callable,
  shell fragment, environment lookup, or arbitrary policy blob.
- **Contract/schema shape:** any new portable contract is closed and versioned,
  generated identically by `schema_bundle()`, and published through the
  hand-governed schema surface and change ledger. Do not hand-maintain a
  second JSON schema or silently reinterpret published fields.
- **Semantic/instantiated/planner admission:** resolve participant, episode
  owner, condition, clock, evidence, budget owner/pool/meter, and reset
  authority before compilation and again at the applicable runtime cut. Missing,
  stale, ambiguous, future, cross-episode, cross-tenant, or unsupported facts
  fail closed. A backend capability claim is not configured capacity or
  realized enforcement.
- **Runtime/persistence:** mutate episode and budget state only through the
  existing generation-fenced, idempotent, atomic snapshot/store transition
  path. Preserve append-only history and exact participant/episode identities.
  Coordinated reset must retain the existing atomic rollback behavior and
  reconcile reservations before advancing generation.
- **Authentication/authorization:** DSL-120 itself adds no HTTP API. Any later
  mutation or retrieval uses `create_control_plane_app()`,
  `ControlPlaneSecurityConfig.strict_defaults()`, verified identity or bearer
  authentication, target-bound roles/participant bindings, request-size
  limits, idempotency, request fingerprints, and audit. Caller authorization,
  participant control authority, and participant-visible disclosure are
  separate gates.
- **Secrets and OS exposure:** declarations, diagnostics, audit, schemas,
  capability/configuration digests, and evidence carry safe references and
  redacted/bounded values only. They must not carry credentials, bearer tokens,
  hidden benchmark material, raw environment/config dumps, backend-native
  objects, or command strings. The requirement adds no listener, env binding,
  subprocess, filesystem, or argv surface; a later adapter must use fixed
  invocation shapes, injected secret providers, bounded inputs/timeouts, and
  never `shell=True` or secret-bearing argv/log output.
- **Error envelopes and observability:** structural/relational failures become
  bounded existing diagnostics; expected HTTP failures use existing bounded
  4xx envelopes and unexpected failures remain redacted. Do not expose native
  parser/backend exceptions, hidden condition inputs, policy contents, or
  evidence through errors. Audit/log output is not participant-visible
  observation or proof of execution.

## Extensibility Seam

The reusable seam is one typed, versioned episode-policy record evaluated for
a specific participant and episode generation. Its condition, interaction,
time/order, reset, evidence, and optional budget-policy references are
parameters resolved by the existing compiler and runtime authorities. A future
episode phase, new terminal condition family, or alternate turn structure adds
a governed discriminator/reference under ordinary schema-compatibility review;
it does not require another lifecycle root, scheduler, clock, budget counter,
or backend branch. Budget policy remains separately reusable across ordinary
and autonomous participants and shared services.

## Gotchas And Anti-Patterns

Avoid:

- encoding episode state/history in workflow/evaluation state, control-plane
  operation status, backend process state, `RuntimeSnapshot.metadata`, generic
  `details`, logs, or free-form YAML;
- treating authored declaration, condition truth, control request, accepted
  operation, execution attempt, terminal state, observation, and evidence as
  interchangeable;
- reusing decision epoch, behavior-history order, wall-clock timestamp, map
  order, scheduler order, or budget window as another order coordinate without
  an explicit declared relation;
- resetting a shared pool/counter because one participant episode resets, or
  reporting a local counter as backend/OS enforcement;
- making a terminal/truncation condition a backend callback convention,
  implicit exception mapping, or unbounded user expression;
- adding `max_*` fields, generic quotas, duplicate validators, exception
  hierarchies, DTOs, schemas, persistence, log/audit paths, or workflow logic;
- exposing policy, condition, evidence, or hidden-task details to a participant
  merely because they are needed by an assurance or backend layer; and
- claiming replay, fairness, timing, reset, or realized termination guarantees
  from schema acceptance, a capability manifest, an audit entry, or prose.

## Non-Goals And Implementation Boundary

- Designing an RL/Gym API, generic interaction transport, UI, prompt protocol,
  scheduler, policy engine, evaluator, world-state store, or backend process
  supervisor.
- Replacing workflow control, participant decision-surface delivery/admission,
  temporal semantics, information-flow policy, outcome interpretation,
  backend manifests, or resource-budget authority.
- Defining reward/scoring, trajectories/demonstrations, universal turn
  semantics, automatic reset behavior, or a claim that every backend can
  realize every authored episode policy.
- Adding a control-plane endpoint or OS/runtime integration solely for DSL-120.
  Those surfaces remain bounded by their existing contracts and require their
  own capability, security, and conformance evidence if changed later.
