# ADR-035: Participant Runtime Observable Lifecycle

## Status

proposed

## Date

2026-05-26

## Context

Issue #74 is the joint design surface for `RUN-305`, `RUN-306`, `RUN-307`,
and `RUN-308`. These requirements define the participant runtime model:
portable state and history, an action lifecycle, shared operational state, and
concurrent participant execution.

The repository already has the adjacent pieces that this design must reuse:

- ADR-013 defines participant episode identity, lifecycle state, terminal
  reason, reset, restart, and append-only episode history.
- ADR-020 defines authored participant framing in SDL without collapsing
  scenario identity, accounts, control-plane identity, runtime apparatus, or
  participant implementations into one concept.
- ADR-022 and `specs/formal/participant-semantics/` define role-neutral
  participant behavior semantics: actions, observations, visibility, failures,
  temporal ordering, attribution, and outcome interpretation.
- Runtime contracts already use schema-first, plain-data envelopes, generated
  schemas, `RuntimeSnapshot`, `Diagnostic`, `ControlPlaneStore`, backend
  capability declarations, and conformance checks.

Those pieces do not yet define the operational runtime surface that connects an
active participant episode to behavior history, shared operational state, and
concurrent execution. `RUN-306` names a lifecycle of proposal, selection,
execution, observation, and state update, but that lifecycle cannot mean that
every participant is internally workflow-based. ACES must support LLM agents,
RL policies, scripts, humans, playbooks, simulators, external services, and
hybrid participants whose internal reasoning is opaque, continuous,
stochastic, or not reported to ACES at all.

The design therefore needs a runtime-observable lifecycle, not a required
participant-internal loop.

## Decision

Adopt a participant runtime model based on observable lifecycle envelopes and
versioned shared-state records.

### 1. The lifecycle is an observable runtime projection

`RUN-306` defines the portable runtime points ACES can mediate, record, or
observe:

1. **intent or proposal observed**: a participant, adapter, policy, human
   operator, backend, or scenario rule exposes an action intent, command,
   choice set, or external trigger to the runtime;
2. **selection or admission recorded**: the runtime records whether the
   attempt was admitted, withheld, selected from alternatives, externally
   selected, or unknown because the participant implementation did not expose a
   selection phase;
3. **execution attempt recorded**: the runtime records the action attempt,
   action contract, actor provenance, temporal context, and failure or support
   basis;
4. **observation emitted**: participant-visible observations are emitted
   through observation boundaries and remain separate from hidden world state
   and archival evidence;
5. **state update committed**: participant-local, shared operational,
   visibility, evidence, and outcome surfaces are updated through explicit
   state records.

These points are event semantics at the runtime boundary. They are not a
mandate that a participant expose a planner, workflow, chain-of-thought,
policy-network step, prompt, reward loop, or internal decision trace.

Adapters MAY declare a lifecycle phase as opaque, externally selected,
not-applicable, or unknown when the participant implementation does not expose
that phase. The runtime MUST still record the observable attempt, observation,
state transition, and evidence/provenance basis needed to interpret results.

### 2. Keep episode lifecycle separate from behavior lifecycle

Participant episode lifecycle from ADR-013 answers when a participant episode
exists, resets, restarts, and terminates. The observable behavior lifecycle
answers what happened inside an active episode.

The two surfaces must be linked by stable `participant_address`, per-episode
`episode_id`, and monotonic `sequence_number`, but they must not be collapsed:

- workflow execution state is not participant behavior state;
- evaluator state is not participant behavior state;
- control-plane operation status is not participant behavior state;
- episode terminal reason is not participant-local action outcome;
- backend process restart is not participant episode restart;
- action lifecycle phases are not episode lifecycle states.

### 3. Shared operational state is a versioned runtime contract

`RUN-307` shared state belongs in a typed runtime contract surface, not in
`RuntimeSnapshot.metadata`, backend-native stores, raw logs, cache keys, or
unstructured `details` maps.

A shared operational state record carries at minimum:

- stable state address;
- state scope: participant-local, shared-environment, visibility,
  evidence-facing, or outcome-facing;
- state kind or contract family;
- revision, digest, or equivalent version marker;
- ordering basis;
- conflict policy or unsupported-concurrency disclosure;
- visibility projection basis;
- provenance for author-declared, processor-derived, backend-realized, or
  participant-observed values;
- evidence references when the record supports an observation, attribution, or
  outcome claim.

World state, participant-visible state, participant belief/history, shared
operational state, and archival evidence remain distinct concepts. A backend
may maintain richer native state internally, but portable ACES claims can only
use the published contract projection.

### 4. Concurrency is explicit ordering, revision, and conflict semantics

`RUN-308` concurrent participant execution is defined over shared state records
and behavior-history events. It is not raw threads mutating a snapshot and it
is not backend scheduler order hidden behind final state.

When concurrent attempts touch shared operational state, the runtime contract
must preserve or disclose:

- the joint action set or coordination interval;
- realized ordering or partial-order relation;
- state revisions read and written by each attempt;
- conflict class and policy, such as coordination, contention, interference,
  shared-state change, serialization, rejection, retry, or unsupported
  simultaneity;
- participant-visible observations that may differ across participants;
- provenance and evidence sufficient for replay and review.

Backends that cannot provide serializable or simultaneous semantics must
disclose the weaker guarantee before results are used for comparison.

### 5. Participant internals are apparatus, not portable semantics

Concrete participant implementations are apparatus surfaces. They may be LLM
agents, RL policies, scripts, humans, external APIs, simulators, tools, or
compositions of those. Their internal prompts, policy states, hidden rewards,
tool traces, or private memory are not automatically ACES runtime state.

If such internals are relevant to a claim, they must be exposed through an
explicit observation, evidence, provenance, or apparatus contract with
redaction and leakage controls. They must not be smuggled into diagnostics,
audit details, history `details`, snapshots, generated schemas, or changelog
text.

### 6. Reuse existing runtime and security boundaries

Future implementation must reuse:

- `RuntimeSnapshot` and participant episode / behavior history surfaces;
- `Diagnostic` and existing redacted error envelopes;
- `ControlPlaneSecurityConfig`, control-plane identity, role checks,
  request-size limits, idempotency, request fingerprints, and audit flow;
- `ControlPlaneStore` JSON-like persistence;
- backend manifests, `ParticipantRuntimeCapabilities`, controlled vocabulary
  scopes, and conformance checks;
- `aces_contracts` contract models and generated schema publication;
- SDL parser, `SDLModel(extra="forbid")`, `SemanticValidator`,
  instantiation revalidation, compiler addresses, and runtime planning
  diagnostics.

Do not introduce parallel schemas, validators, exception hierarchies,
persistence stores, audit logs, backend-native DTOs, or compatibility-wrapper
logic for participant runtime state.

## Consequences

### Positive

- `RUN-306` remains feasible for LLM agents, RL agents, humans, scripts, and
  opaque external services because the lifecycle is a boundary projection, not
  an internal algorithm contract.
- `RUN-305`, `RUN-306`, `RUN-307`, and `RUN-308` share one runtime model
  instead of four drifting local designs.
- Shared state and concurrency become reviewable through revisions, ordering,
  conflict policy, visibility projection, and evidence rather than hidden
  backend behavior.
- Existing episode lifecycle, participant semantics, runtime contract,
  manifest, conformance, and control-plane security patterns remain canonical.

### Negative

- Runtime adapters must expose more structured records than raw logs or final
  state.
- Some participants will legitimately produce incomplete lifecycle envelopes,
  so downstream consumers must handle opaque, unknown, externally selected, or
  unsupported phases.
- The model adds another explicit contract layer before full implementation can
  land.

### Risks

- If implementors treat the observable lifecycle as a required internal loop,
  ACES will exclude the LLM/RL/human/external-service participants it needs to
  model.
- If shared state is stored in `RuntimeSnapshot.metadata` or backend-native
  stores, portability and conformance will degrade.
- If concurrency is inferred from timestamps or scheduler order, replay,
  attribution, and comparison claims will be invalid.
- If participant internals are recorded without explicit observation/evidence
  contracts, prompts, credentials, hidden answer keys, private traces, or
  sensitive state may leak.

## Non-Goals

- Implementing participant runtime contracts, schemas, APIs, backends, or
  storage.
- Adding new SDL participant syntax.
- Replacing ADR-013 participant episode lifecycle semantics.
- Replacing ADR-022 participant behavior and interaction semantics.
- Requiring chain-of-thought, prompts, policy internals, reward traces, or
  planner steps from participant implementations.
- Designing archival study provenance or benchmark asset lifecycle beyond the
  runtime fields needed to preserve participant history and shared-state
  evidence.
