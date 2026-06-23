# ADR-067: Participant Behavior Model

## Status

proposed

## Date

2026-06-23

## Classification

Classification: FM2
Required artifacts: ADR, formal spec, clause matrix
Waivers: Executable SDL fields, contract schemas, fixtures, runtime emission,
and tests are owned by spawned implementation issues #204, #205, #206, #207,
and #208.

## Context

Issue #77 is the joint design surface for:

- `ACT-602`, executable participant behavior model;
- `ACT-603`, abstract participant interaction model;
- `ACT-606`, first-class participant behavior specifications;
- `ACT-607`, participant authority and scope boundaries; and
- `ACT-608`, participant behavior modes.

These requirements sit on top of already-published participant semantics:

- ADR-020 defines authored participant framing in SDL: identity, role,
  starting conditions, authority anchors, and operating scope.
- ADR-022 and `specs/formal/participant-semantics/` define the semantic model
  for participant actions, observations, visibility, failures, temporal
  ordering, attribution, and outcome interpretation.
- ADR-041 defines participant implementation manifests and run-level
  provenance for the apparatus that makes or relays decisions.
- ADR-054 and `specs/formal/participant-runtime/` define the observable
  runtime lifecycle, shared-state records, observation envelopes, behavior
  history, and concurrency boundaries.
- ADR-060 and `specs/formal/runtime-contracts/participant-backend-contracts.md`
  define the backend-facing carrier and retrieval contract surface.

The missing design is the joint behavior-model layer that tells child
implementation work how those pieces compose. Without one model, implementers
can accidentally create a parallel `participants` schema tree, treat action
names as portable behavior, place authority in credentials or bearer tokens,
use backend logs as observations, or add a second behavior-mode taxonomy.

## Decision

Adopt one participant behavior model that composes the existing participant
semantics, SDL framing, runtime evidence, backend contract, and implementation
provenance surfaces.

### 1. Participant behavior is a composed model, not a new stack

The participant behavior model is the composition of:

- authored participant framing from SDL `agents.*`;
- governed participant action contracts;
- participant observation boundaries and visibility transitions;
- participant-local outcome interpretation rules;
- declared authority, trust, access, control, and operating-scope boundaries;
- selected participant behavior mode;
- participant implementation manifest and provenance refs;
- backend realization and feature-support declarations; and
- runtime behavior-history, observation, shared-state, attribution, temporal,
  evidence, and outcome records.

No new top-level `participants` model, participant-specific persistence store,
exception hierarchy, audit stack, schema publication path, or backend-native
behavior abstraction is introduced by this design.

### 2. ACT-603 abstract interaction model is the semantic center

The abstract interaction model reuses ADR-022. A portable participant
interaction is defined over:

- actor identity and participant address;
- action contract and action attempt;
- participant-visible observation;
- participant-local and shared state references;
- preconditions, effects, side effects, and failure classes;
- authority and scope facts consulted by those preconditions;
- temporal context and ordering relation;
- joint-action, coordination, contention, interference, and shared-state
  relationships;
- attribution and evidence labels; and
- participant-local outcome interpretation.

Action names, tool names, ATT&CK/CVE labels, backend commands, reward values,
timestamps, scheduler order, and raw logs are not portable interaction
semantics unless they are bound through the governed ACES contracts above.

### 3. ACT-602 executable model means machine-checkable ACES contracts

The executable participant behavior model is executable because processors,
backends, conformance tools, and validators can check it, not because ACES
standardizes one participant runtime loop or one external agent API.

Executable behavior must flow through existing gates:

- parser and closed SDL model validation;
- semantic validation of action, observation, outcome, authority, scope, and
  named references;
- compiler output with canonical participant addresses;
- closed `ContractModel` payloads and generated schemas when a portable
  contract is published;
- runtime behavior-history and observation validation;
- backend capability and feature-support disclosures; and
- conformance diagnostics and evidence requirements.

Backends may realize behavior with humans, scripts, policies, LLM agents, RL
policies, emulators, simulators, services, or mixed controllers. The portable
claim is the ACES contract and evidence record, not the backend's private
implementation.

### 4. ACT-606 behavior specifications are first-class aggregates

A participant behavior specification is a named, versioned aggregate over the
existing behavior surfaces. It may bind:

- participant or participant-role refs;
- action contract refs;
- observation boundary refs;
- outcome interpretation rule refs;
- authority, trust, access, control, and scope refs;
- behavior mode;
- realization profile and fidelity/disclosure claims;
- required backend feature support and evidence contracts; and
- lifecycle, semantic version, and extension-policy metadata.

The aggregate is a specification artifact. It does not replace action
contracts, observation boundaries, outcome rules, participant implementation
manifests, backend capability declarations, or runtime evidence records.

### 5. ACT-607 authority and scope remain authored semantics

Participant authority and scope are scenario meaning. They are separate from
transport authentication, control-plane identity, OS users, credentials,
backend capability, participant implementation identity, and episode lifecycle
state.

The model keeps these facets distinct:

- starting accounts and initial access anchors;
- initial knowledge and starting conditions;
- authority anchors and trust bases;
- operating scope;
- action preconditions and failure classes;
- observation boundaries and visibility projections;
- implementation capability declarations; and
- control-plane authorization.

Credentials, tokens, hidden prompts, answer keys, private traces, backend
private configuration, and adjudication assets are never portable authority
evidence inline. Use refs, digests, markings, redaction policies, and explicit
evidence boundaries.

### 6. ACT-608 behavior modes reuse the controlled vocabulary

Behavior modes are declared through the existing
`participant-decision-surface-modes` controlled vocabulary:

- `autonomous`;
- `scripted`;
- `policy-directed`;
- `replayed`;
- `human-supervised`; and
- `mixed-control`.

The ACT-608 word "supervised" maps to `human-supervised` for the current
surface. A broader non-human supervision concept must enter through the
governed vocabulary process rather than a casual `supervised` alias.

Behavior mode is not implementation kind, participant role, backend feature
support, control-plane authorization, or multi-participant interaction class.
It says how decisions are selected or controlled at the participant
decision-surface boundary.

### 7. Child implementation boundaries are fixed

This joint design establishes the model shape. Spawned issues own executable
work:

- #204 / ACT-602: executable behavior model gates, contract bindings, and
  conformance evidence.
- #205 / ACT-603: abstract interaction model implementation coverage.
- #206 / ACT-606: first-class behavior specification authoring and validation
  surface.
- #207 / ACT-607: authority/scope boundary authoring and validation surface.
- #208 / ACT-608: behavior-mode declaration, selection, and validation surface.

Those issues must reuse the seams named in this ADR. They must not publish
parallel semantics to avoid the composition constraints.

## Required Boundaries

- `agents.*.actions` is an authoring affordance; action contracts carry
  portable action semantics.
- Participant-visible observation is not hidden world truth, scoring state,
  centralized training state, or archival evidence.
- Authority is not possession of a credential, bearer token, OS account,
  backend handle, or control-plane caller identity.
- Behavior mode is not implementation kind, participant role, backend support
  strength, or control-plane authorization.
- Runtime behavior history is evidence of realized behavior; it is not the
  authored behavior specification.
- Backend capability declarations are support claims; they are not proof that a
  particular participant implementation ran.
- Schema validity is necessary but insufficient for semantic conformance.
  Runtime and conformance claims require evidence refs, negative fixtures, and
  diagnostics at the owning implementation issue.
- Hidden truth, answer keys, private prompts, credentials, raw command output,
  and backend-private objects must not be placed in portable specs, schemas,
  diagnostics, fixtures, logs, snapshots, or changelog text.

## Alternatives Considered

### Add a new top-level `participants` behavior model

Rejected. ADR-020 already establishes `agents.*` as the participant authoring
home unless a distinct concept requires another surface. A second top-level
model would split identity, role, authority, action, observation, and outcome
meaning across two SDL surfaces.

### Treat backend or agent-framework APIs as the executable model

Rejected. Gym-like, PettingZoo-like, CybORG-like, service, script, human, and
LLM-agent interfaces can all be useful realizations. None is the portable ACES
semantic authority. ACES claims must be expressed through its own contracts,
evidence, capability, and conformance surfaces.

### Treat behavior modes as free-form strings

Rejected. ACT-608 mode values affect comparability and evidence claims. They
must resolve through the controlled vocabulary and governed extension rules.

### Put authority and scope only in runtime enforcement

Rejected. ACT-607 is authored scenario meaning. Runtime enforcement may prove
or realize it, but the boundary must be declared and reviewable before a
backend acts.

## Consequences

### Positive

- The five ACT requirements share one vocabulary and boundary model.
- Implementation issues get concrete seams instead of negotiating behavior
  semantics independently.
- Existing parser, semantic validation, schema, runtime, backend, conformance,
  and controlled-vocabulary machinery stays canonical.
- Security-sensitive concepts stay separated: authority, credentials, control
  auth, observation, hidden truth, implementation identity, and backend support
  are not collapsed.

### Negative / costs

- Implementers must carry more references through the behavior model instead
  of adding local strings or metadata blobs.
- Behavior specifications need lifecycle, versioning, evidence, and extension
  discipline even before a backend can execute every behavior class.
- Reviewers must distinguish design coverage from executable implementation
  evidence for the spawned issues.

### Risks

- If a child issue treats action names or tool labels as action contracts,
  ACES behavior portability will be overstated.
- If behavior modes are duplicated outside the controlled vocabulary, run
  comparability and conformance will drift.
- If authority or scope is enforced only by credentials or backend sandboxing,
  scenario meaning will be tied to deployment apparatus rather than authored
  semantics.
- If runtime evidence is treated as the behavior specification, replay and
  audit records can be mistaken for authoring intent.

## References

- Participant behavior model formal design:
  `specs/formal/participant-behavior-model/README.md`
- [ADR-020: Declarative Participant Framing Boundaries](adr-020-declarative-participant-framing-boundaries.md)
- [ADR-022: Participant Behavior and Interaction Semantics](adr-022-participant-behavior-and-interaction-semantics.md)
- [ADR-041: Participant Implementation Manifest and Provenance Surface](adr-041-participant-implementation-manifest-and-provenance.md)
- [ADR-054: Participant Runtime Observable Lifecycle](adr-054-participant-runtime-observable-lifecycle.md)
- [ADR-060: Participant Backend-Facing Contract Surface](adr-060-participant-backend-facing-contract-surface.md)
