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
participant-internal loop. The primary lineage reinforces that boundary:
Gymnasium, PettingZoo, OpenSpiel, CybORG, CyberBattleSim, and CyGIL expose
actions, observations, rewards or returns, legal-action spaces or masks,
termination/truncation, episode control, active-agent/current-actor state,
chance nodes, mean-field updates, and multi-agent interaction without requiring
access to private agent internals. OpenSpiel's information-state discipline
reinforces that observation, action-observation history, and perfect recall are
separate claims. Lamport clocks, HLA time management, Time Warp, DEVS, and FMI
separate timestamp, ordering, causality, pacing, synchronization, lookahead,
rollback, and realization. OCSF, STIX, CACAO, OpenC2, and CALDERA show that
portable event and command semantics need typed envelopes, identity,
versioning, classification, normalized status, provenance, markings, and
extension rules rather than raw backend objects.

## Decision

Adopt a participant runtime model based on observable lifecycle envelopes,
versioned shared-state records, explicit observation boundaries, and
partial-order concurrency records.

### 1. The lifecycle is an observable runtime projection

`RUN-306` defines the portable runtime points ACES can mediate, record, or
observe:

1. **intent or proposal observed**: a participant, adapter, policy, human
   operator, backend, or scenario rule exposes an action intent, command,
   choice set, or external trigger to the runtime;
2. **selection or admission recorded**: the runtime records whether the
   attempt was admitted, rejected, withheld, externally supplied, unknown, or
   not applicable for the participant or action;
3. **execution attempt recorded**: the runtime records the action attempt,
   action contract, actor provenance, temporal context, operation state, and
   failure or support basis;
4. **observation emitted**: participant-visible observations are emitted
   through observation boundaries and remain separate from hidden world state,
   scoring state, centralized-training state, and archival evidence;
5. **state update committed**: participant-local, shared operational,
   visibility, evidence, and outcome surfaces are updated through explicit
   state records.

These points are event semantics at the runtime boundary. They are not a
mandate that a participant expose a planner, workflow, chain-of-thought,
policy-network step, prompt, reward loop, or internal decision trace.

Adapters MAY declare a lifecycle phase as `opaque`, `externally_supplied`,
`not_applicable`, `unknown`, or `unsupported` when the participant
implementation does not expose that phase. The runtime MUST still record the
observable attempt, observation, state transition, and evidence/provenance basis
needed to interpret results.

### 2. Lifecycle vocabulary is closed and not overloaded

The lifecycle uses closed semantic vocabularies. Adapters may preserve
source-specific labels, but portable ACES claims use normalized wire values.
Wire values are snake_case; the formal design uses PascalCase names for the
same values.

Phase realization uses:

- `observed`: the phase occurred at the runtime boundary and was observed;
- `runtime_mediated`: ACES or a governed backend admitted, selected, or
  transformed the phase;
- `externally_supplied`: a human, service, scenario rule, or external
  controller supplied the phase;
- `opaque`: the participant may have an internal counterpart, but it is not
  exposed to ACES;
- `unknown`: the phase might be relevant, but the adapter cannot determine what
  happened;
- `not_applicable`: the phase has no semantic counterpart for this participant
  or action;
- `unsupported`: the backend or adapter cannot provide the guarantee needed for
  a portable claim.

Selection/admission disposition uses:

- `admitted`: the attempt may proceed;
- `rejected`: the attempt is denied and does not execute unless a later retry is
  explicitly recorded;
- `withheld`: a participant, controller, scenario rule, or runtime intentionally
  does not release the attempt;
- `not_applicable`: no admission decision exists for this action or
  participant;
- `unknown`: an admission decision may exist, but ACES cannot determine it.

Long-running operation state uses:

- `submitted`, `acknowledged`, `running`, `blocked`, `completed`, `partial`,
  `failed`, `timed_out`, `cancelled`, `unknown`, and `unsupported`.

`opaque`, `unknown`, `not_applicable`, and `unsupported` are different claims
and must not be collapsed into a generic missing value. `unsupported` is a
capability disclosure. `unknown` is an epistemic disclosure. `opaque` is an
apparatus boundary. `not_applicable` says the modeled participant or action has
no such phase. `rejected`, `withheld`, and long-running operation states are not
phase realization modes; they are separate fields so a record can say, for
example, that a runtime-mediated selection was rejected.

### 3. Envelopes carry identity, schema, provenance, and markings

Every portable lifecycle, observation, shared-state, operation, joint-action,
or evidence-facing record carries a common envelope foundation:

- stable `event_id`, `schema_name`, `schema_version`, `event_type`, and
  extension policy;
- normalized event classification and source status fields when the record
  makes an event-status, severity, or security-telemetry claim, including
  category, class, activity, type, severity, status, source status code, and
  status detail;
- `participant_address`, `episode_id`, monotonic `sequence_number`, and related
  action, command, operation, observation, state, and evidence references;
- `occurred_at`, `recorded_at`, `ingested_at`, clock authority, temporal
  context, ordering basis, logical order, and predecessor event references;
- actor, producer, source system, source record, raw source, confidence, and
  provenance references, plus raw-data hash, size, and truncation metadata when
  raw evidence is summarized or moved to controlled storage;
- lifecycle phase, phase realization, admission disposition when applicable,
  operation state when applicable, and source-specific status labels when
  mapping loss exists;
- observation references, shared-state read/write references, emitted state
  update references, and joint action references;
- security markings, granular field markings, redaction policy reference,
  authorization scope, and safe raw/evidence references.

This follows the same design lesson as OCSF and STIX without adopting their
full object models: portable records need event identity, schema evolution,
classification, timestamps with distinct meanings, confidence, markings,
extension boundaries, source/raw mapping, and granular selectors for
field-level markings. Raw logs, backend DTOs, command output, or telemetry
records are evidence inputs until ACES projects them through the governed
runtime contract.

### 4. Keep episode lifecycle separate from behavior lifecycle

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

### 5. Observation records carry information-boundary guarantees

Participant-visible observations must identify the visibility projection that
produced them. The runtime must distinguish:

- hidden world truth;
- participant-visible observation;
- participant action-observation history;
- participant information state claimed by ACES;
- centralized-training/global-state views;
- scoring or evaluator state;
- archival evidence used for review or replay.

An observation envelope declares an information guarantee:

- `observation_only`: the record is only the emitted observation;
- `history_consistent`: the participant's portable action-observation history
  can reconstruct the information state ACES claims for that participant;
- `perfect_recall`: the runtime preserves every prior action and observation
  needed for a perfect-recall information state;
- `lossy_projection`: the observation is intentionally partial, sampled,
  delayed, noisy, redacted, or aggregated, with loss disclosed;
- `unknown`: the adapter cannot determine the information-state guarantee;
- `unsupported`: the backend cannot support a portable information-state claim.

The observation function is a contract boundary: it maps runtime state, a
visibility rule, participant identity, and an order point to an observation
record. A stronger information-state claim is valid only when the portable
action-observation history, visibility rule, redaction markings, stochastic or
noise disclosure, ordering context, and governed reconstruction algorithm or
proof reference are sufficient to reproduce the claimed information state.
Global state exposed for centralized training, debugging, scoring, or backend
operation is not participant-visible state unless an explicit visibility rule
projects it to that participant.

### 6. RL and multi-agent step signals are explicit but separate

When a backend exposes an RL-style or game-style step surface, ACES records the
participant-visible step signals without adopting Gymnasium, PettingZoo, or
OpenSpiel as the runtime protocol. The runtime envelope may therefore carry:

- action-space and observation-space references;
- interaction-context records for the order point, including interaction mode,
  active agent set, current actor for sequential/AEC surfaces, simultaneous
  actor set for parallel surfaces, chance mode/distribution or sampled outcome,
  and mean-field population/update references;
- action masks or legal-action references, including the projection and order
  point at which the mask was valid;
- participant-visible reward and cumulative return records;
- per-participant termination and truncation signals, separate from ACES
  episode terminal reason;
- auxiliary info references when the backend exposes metrics or debug data,
  with markings preventing hidden state from becoming participant-visible by
  accident.

Reward, return, termination, truncation, and action masks are not inferred from
objective success, scorer state, or backend debug fields. If they are used for
benchmark comparison, they must be recorded as governed step signals with
space definitions, visibility policy, seed/randomization context, and run
provenance.

Sequential, AEC, simultaneous, chance, and mean-field claims are not implied by
the presence of a step signal. A participant action is valid only when the
participant is in the recorded active-agent set and, for sequential/AEC
surfaces, is the current actor. Chance and mean-field nodes are environment
updates unless a scenario explicitly models them as participants; their
distribution, sampled outcome, or population update must be recorded or the
claim must downgrade.

### 7. Shared operational state is a versioned runtime contract

`RUN-307` shared state belongs in a typed runtime contract surface, not in
`RuntimeSnapshot.metadata`, backend-native stores, raw logs, cache keys, or
unstructured `details` maps.

A shared operational state record carries at minimum:

- stable state address;
- state scope: participant-local, shared-environment, visibility,
  evidence-facing, or outcome-facing;
- state kind or contract family;
- revision, digest, or equivalent version marker;
- ordering basis, logical order, and predecessor state references;
- conflict policy or unsupported-concurrency disclosure;
- visibility projection basis;
- provenance for author-declared, processor-derived, backend-realized,
  participant-observed, or externally supplied values;
- evidence references when the record supports an observation, attribution, or
  outcome claim;
- security markings, field-level redaction policy, and authorization scope for
  values that cannot be safely disclosed to all consumers.

World state, participant-visible state, participant belief/history, shared
operational state, and archival evidence remain distinct concepts. A backend
may maintain richer native state internally, but portable ACES claims can only
use the published contract projection.

### 8. Concurrency is explicit ordering, isolation, and conflict semantics

`RUN-308` concurrent participant execution is defined over shared state records
and behavior-history events. It is not raw threads mutating a snapshot, and it
is not backend scheduler order hidden behind final state.

When concurrent attempts touch shared operational state, the runtime contract
must preserve or disclose:

- the joint action set or coordination interval;
- realized total order, partial order, simultaneity group, or unsupported order;
- logical/vector clock context, simulation time, wall-clock time, lookahead,
  time-advance grants, or a disclosed weaker clock basis;
- state revisions read and written by each attempt;
- snapshot basis, isolation guarantee, and atomicity scope;
- conflict class and policy, such as coordination, contention, interference,
  shared-state change, serialization, rejection, retry, merge, rollback, or
  unsupported simultaneity;
- participant-visible observations that may differ across participants;
- retry, cancellation, timeout, fairness, and starvation disclosures for
  long-running or contended operations;
- provenance and evidence sufficient for replay and review.

Backends that cannot provide serializable, simultaneous, causal, or snapshot
semantics must disclose the weaker guarantee before results are used for
comparison.

Distributed-simulation modes are explicit contract claims. A conservative or
HLA-style runtime must record the time-regulation/time-constrained basis,
lookahead, time-advance request/grant, and message send/receive causality that
justify delivery order. An optimistic or Time Warp-style runtime must record
rollback, anti-message or compensation references, and the post-rollback
supersession relation without deleting prior records. A DEVS/FMI-style runtime
must name the time domain, internal/external/confluent transition basis, and
step negotiation or unsupported disclosure. Backend serialization is a valid
weaker realization only when labeled as such.

The conflict predicate is semantic, not just physical. Attempts conflict when
their declared read/write sets, exclusive resource claims, visibility effects,
evidence streams, or action contracts say one attempt can affect another's
preconditions, observations, effects, outcome, or provenance. Last-writer-wins
is only portable when represented as an explicit serialization policy with
realized ordering, read/write revisions, and evidence. Merge is portable only
when the action contract declares commutativity or a merge rule.

Capability claims are vectors over concerns, not one scalar. Each concern uses
the ordered levels:

```text
unsupported < disclosed_weak < bounded < exact
```

`not_applicable` is outside that order. A backend satisfies a contract only when
its declared guarantee vector is at least as strong as the contract's required
vector for every required concern. Two vectors are incomparable when each is
stronger on different required concerns. Downgrades must be recorded as
component-level capability disclosures, not hidden in diagnostics or final
state.

### 9. Cyber actions preserve command, knowledge, and actuator context

Cyber actions are not just opaque strings. When an action maps to OpenC2,
CACAO, CALDERA, ATT&CK, CybORG, CyberBattleSim, or backend-native commands, the
runtime envelope preserves the portable parts of that mapping:

- action or command verb, target, arguments, and contract reference;
- OpenC2 profile, command id, request id, action, target, args, actuator, and
  response status/result references when an OpenC2 command or response is the
  source mapping;
- CACAO playbook id, workflow step id/type, command, agent, target, variables,
  authentication reference, success/failure successor, and external reference
  mappings when a playbook step is the source mapping;
- CALDERA operation, adversary, planner, ability, link, fact, agent, executor,
  and tactic/technique references when CALDERA is the source mapping;
- actuator, executor, session, authority, and privilege context;
- credential and secret references as redacted evidence or state references,
  never raw secret values;
- knowledge, foothold, visibility, detection-surface, and outcome deltas;
- source ability, playbook step, tool invocation, or backend action reference;
- response, observation, error, and evidence references.

These fields make cyber behavior comparable without forcing ACES to adopt any
one command language, playbook schema, attack graph, or RL environment API.

### 10. Experiment and benchmark provenance is a runtime input

Participant-runtime envelopes do not define a full study-management system, but
they must carry the fields needed to make benchmark claims auditable:

- run id, repeat id, scenario version, contract bundle digest, and backend
  manifest digest;
- participant implementation reference, scaffold/tool exposure, model or policy
  version, and adapter version;
- seed, randomization, holdout/canary exposure labels, and run configuration
  digest;
- evaluator/scoring references, assistance disclosures, cost/resource traces,
  timeout/budget limits, and relevant environment build references.
- statistical repetition plan, trial/replicate identity, baseline/evaluator
  version, metric aggregation plan, confidence-interval/test/effect-size
  policy, cost-normalization policy, exclusion/retry policy, and comparison
  cohort when records are used for comparative claims;
- evaluator leakage model, baseline eligibility policy, paired-run group,
  artifact immutability refs, and exclusion decision refs when records are used
  to support an academic or engineering benchmark conclusion;
- contamination-audit evidence, holdout asset digests, canary policy, scaffold
  exposure matrix, and public/private material labels sufficient to support the
  claim that hidden benchmark material was not exposed to a participant.

These fields align the runtime surface with the benchmark lineage while keeping
the full archival study lifecycle out of scope for this ADR. ACES can preserve
the runtime evidence needed for later statistical analysis, but run context
alone is not a validity model. A comparative or non-contamination conclusion
requires an explicit benchmark-validity claim that cites the metric,
aggregation, uncertainty, baseline comparability, evaluator leakage, exposure,
exclusion/retry, cost-normalization, and artifact-immutability procedures it
depends on.

### 11. Participant internals are apparatus, not portable semantics

Concrete participant implementations are apparatus surfaces. They may be LLM
agents, RL policies, scripts, humans, external APIs, simulators, tools, or
compositions of those. Their internal prompts, policy states, hidden rewards,
tool traces, or private memory are not automatically ACES runtime state.

If such internals are relevant to a claim, they must be exposed through an
explicit observation, evidence, provenance, or apparatus contract with markings,
redaction, authorization, and leakage controls. They must not be smuggled into
diagnostics, audit details, history `details`, snapshots, generated schemas, or
changelog text.

### 12. Reuse existing runtime and security boundaries

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
- Closed realization, disposition, operation, observation, conflict, and
  capability vocabularies make weak or missing guarantees explicit instead of
  silently lossy.
- RL/MARL step signals are preserved when present without forcing all
  participants through an RL API shape.
- `RUN-305`, `RUN-306`, `RUN-307`, and `RUN-308` share one runtime model
  instead of four drifting local designs.
- Shared state and concurrency become reviewable through revisions, ordering,
  isolation, conflict policy, visibility projection, and evidence rather than
  hidden backend behavior.
- Information-state claims become falsifiable against action-observation
  histories, visibility projections, redaction markings, and stochastic/noise
  disclosures.
- Distributed-simulation and backend-serialized executions can be compared only
  when their time, causality, rollback, and guarantee disclosures support the
  claim being made.
- Existing episode lifecycle, participant semantics, runtime contract,
  manifest, conformance, and control-plane security patterns remain canonical.

### Negative

- Runtime adapters must expose more structured records than raw logs or final
  state.
- Some participants will legitimately produce incomplete lifecycle envelopes,
  so downstream consumers must handle opaque, unknown, externally supplied,
  unsupported, rejected, withheld, or partial phases.
- Backends must classify information-state, ordering, isolation, conflict,
  capability, redaction, and provenance guarantees before they can make
  comparable runtime claims.
- The model adds another explicit contract layer before full implementation can
  land.

### Risks

- If implementors treat the observable lifecycle as a required internal loop,
  ACES will exclude the LLM/RL/human/external-service participants it needs to
  model.
- If `unknown`, `opaque`, `not_applicable`, and `unsupported` are conflated,
  reviewers will be unable to tell missing evidence from an intentional
  apparatus boundary or a backend capability limit.
- If rejection, withholding, failure, timeout, and cancellation are modeled as
  phase-realization statuses, selection semantics and long-running action
  semantics will be ambiguous.
- If shared state is stored in `RuntimeSnapshot.metadata` or backend-native
  stores, portability and conformance will degrade.
- If concurrency is inferred from timestamps or scheduler order, replay,
  attribution, and comparison claims will be invalid.
- If observation records do not declare an information-boundary guarantee,
  hidden truth, centralized-training state, and participant-visible state may be
  accidentally collapsed.
- If reward, return, action masks, termination, or truncation are inferred from
  objective/scorer/backend internals, RL results will not be portable or
  reviewable.
- If time-advance, lookahead, rollback, or message-causality records are
  missing, HLA/DEVS/FMI/Time-Warp-style claims will collapse into timestamp
  folklore.
- If benchmark comparison records omit statistical repetition, baseline
  versions, cost normalization, scaffold exposure, or contamination evidence,
  the runtime may preserve history but still fail academic benchmark review.
- If security markings and redaction policies are not field-level, portable
  evidence may leak credentials, prompts, hidden answer keys, private traces, or
  sensitive state.

## Non-Goals

- Implementing participant runtime contracts, schemas, APIs, backends, or
  storage.
- Adding new SDL participant syntax.
- Replacing ADR-013 participant episode lifecycle semantics.
- Replacing ADR-022 participant behavior and interaction semantics.
- Requiring chain-of-thought, prompts, policy internals, hidden reward traces,
  or planner steps from participant implementations.
- Making Gymnasium, PettingZoo, OpenSpiel, OpenC2, CACAO, CALDERA, OCSF, STIX,
  HLA, DEVS, Time Warp, or FMI wire-compatible ACES protocols.
- Defining a solver, policy optimizer, reward-learning API, centralized
  training protocol, or reward API.
- Defining a full archival study-management system beyond the runtime fields
  needed to preserve participant history, shared-state evidence, and benchmark
  reproducibility claims.
