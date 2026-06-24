# Participant Behavior Model Formal Design

This document is the issue #77 formal design artifact for:

- `ACT-602` - Executable Participant Behavior Model
- `ACT-603` - Abstract Participant Interaction Model
- `ACT-606` - First-Class Participant Behavior Specifications
- `ACT-607` - Participant Authority And Scope Boundaries
- `ACT-608` - Participant Behavior Modes

It is governed by ADR-067. It composes the participant semantics from ADR-022
with SDL participant framing, participant runtime records, backend-facing
contracts, controlled vocabularies, and participant implementation provenance.
It is a design artifact, not an implementation artifact.

## Current Coverage And Gap

Existing coverage:

- ADR-020 pins authored participant framing on `agents.*`.
- ADR-022 and `specs/formal/participant-semantics/` define action,
  observation, visibility, interaction, attribution, temporal, and outcome
  semantics.
- ADR-041 defines participant implementation manifest and provenance records.
- ADR-054 and `specs/formal/participant-runtime/` define observable runtime
  lifecycle, behavior history, shared state, observation envelopes, and
  concurrency.
- ADR-060 and `specs/formal/runtime-contracts/participant-backend-contracts.md`
  define backend-facing carrier, retrieval, support, and outcome surfaces.
- `controlled-vocabularies-v1` already defines
  `participant-decision-surface-modes`.

Remaining issue #77 gap:

- no single behavior-model composition binding these surfaces to ACT-602,
  ACT-603, ACT-606, ACT-607, and ACT-608;
- no first-class behavior specification aggregate;
- no clause matrix tying authority/scope and mode selection to the behavior
  model; and
- no child-issue boundary that prevents each UID from publishing local behavior
  semantics.

## Model Summary

The participant behavior model is:

```text
ParticipantBehaviorModel =
  ParticipantFraming
  + ActionContractSet
  + ObservationBoundarySet
  + OutcomeInterpretationRuleSet
  + AuthorityScopeBoundarySet
  + BehaviorSpecificationSet
  + BehaviorModeSelection
  + RealizationAndEvidenceBindings
  + RuntimeBehaviorEvidence
```

The model has three layers:

1. **Authored layer** - SDL `agents.*`, action contracts, observation
   boundaries, outcome interpretation rules, authority/scope refs, and
   behavior specification aggregates.
2. **Realization layer** - participant implementation manifests, selected
   decision-surface mode, backend capability and feature-support claims,
   realization profile, fidelity claims, and disclosure refs.
3. **Evidence layer** - participant behavior history, lifecycle events,
   observation envelopes, shared-state records, attribution edges, outcome
   reports, conformance diagnostics, and evidence refs.

These layers are linked by stable references. They are not interchangeable.

## ACT-603 - Abstract Participant Interaction Model

An abstract participant interaction is the tuple:

```text
Interaction =
  participant_address
  action_contract_ref
  attempt_ref
  observation_boundary_ref*
  precondition_result*
  effect_claim*
  failure_class?
  authority_scope_ref*
  state_ref*
  temporal_context
  ordering_relation
  joint_action_ref?
  attribution_ref*
  outcome_interpretation_ref*
  evidence_ref*
```

Rules:

- `participant_address` identifies the runtime participant and episode scope;
  authored identity and role remain SDL framing refs.
- `action_contract_ref` is required for portable action meaning. A raw action
  name, command, tool label, technique label, or benchmark milestone is not
  enough.
- `observation_boundary_ref` defines what the participant may see or infer.
  Hidden truth and archival evidence are outside the participant-visible view
  unless an explicit disclosure rule projects them.
- Preconditions and effects are evaluated against declared state, authority,
  scope, visibility, and temporal context. Unknown or unresolved references fail
  closed.
- Failure classes use the existing participant-semantics taxonomy. Backend
  errors must map to governed failure classes before becoming portable
  semantics.
- Interaction among participants is represented as joint action,
  coordination, contention, interference, or shared-state change, never as
  backend scheduler order alone.
- Outcome interpretation is participant-local until a named rule relates it to
  scenario, workflow, objective, evaluation, evidence, or reward surfaces.

## ACT-602 - Executable Participant Behavior Model

Executable behavior means the model is machine-checkable through ACES gates.
The executable chain is:

```text
SDL authoring
  -> parser normalization and closed models
  -> semantic validation
  -> compiled participant addresses and runtime refs
  -> runtime carrier emission
  -> contract/schema validation
  -> semantic conformance diagnostics
  -> traceable evidence refs
```

Required executable properties:

- authored symbol keys are stable and cannot be created by variables;
- action, observation, outcome, authority, scope, and behavior-spec refs
  resolve before compilation;
- compiled runtime addresses are canonical and stable enough for traceability;
- runtime records preserve participant address, episode, order, source,
  marking, evidence, and redaction context;
- backend support claims resolve through governed vocabularies and contract
  evidence;
- weaker guarantees are explicit through support level, mapping loss,
  disclosure refs, and diagnostics; and
- conformance cannot rely on schema acceptance alone.

Implementation issue #204 owns executable contract bindings, validators,
fixtures, and conformance evidence for this requirement.

## ACT-606 - First-Class Participant Behavior Specifications

A behavior specification is a named, versioned aggregate:

```text
BehaviorSpecification =
  spec_id
  semantic_version
  lifecycle_state
  participant_ref*
  participant_role_ref*
  action_contract_ref*
  observation_boundary_ref*
  outcome_interpretation_rule_ref*
  authority_scope_ref*
  behavior_mode?
  realization_profile_ref?
  backend_feature_support_ref*
  evidence_contract_ref*
  extension_policy
```

Rules:

- A behavior specification is first-class because it can be named, versioned,
  traced, reviewed, and validated as an artifact.
- It aggregates existing behavior surfaces. It does not replace action
  contracts, observation boundaries, outcome rules, manifests, backend
  capabilities, or runtime evidence.
- `behavior_mode` binds to the controlled vocabulary described in ACT-608.
- `realization_profile_ref` records how the behavior can be realized without
  exposing private implementation configuration.
- `evidence_contract_ref` names the contracts needed to prove the behavior
  claim in a run or conformance report.
- Extension fields follow the governed `x-<owner>:<term>` discipline.

Implementation issue #206 owns the executable authoring and validation surface
for this aggregate.

## ACT-607 - Authority And Scope Boundaries

Authority and scope are authored semantics. The model distinguishes:

| Facet | Portable meaning | Not equivalent to |
| --- | --- | --- |
| `starting_accounts` | Initial declared access anchors | proof of authority |
| `initial_knowledge` | Participant starting knowledge refs | hidden truth |
| `starting_conditions` | Declared state or setup preconditions | setup commands |
| `authority_anchors` | Declared bases for allowed or expected action | bearer tokens, HTTP auth, OS user |
| `operating_scope` | Declared targetable action/observation boundary | backend sandbox, process boundary |
| action preconditions | Contract-level applicability checks | free-form policy prose |
| observation boundaries | Participant-visible information rules | backend logs or world truth |
| backend capability | Realization support claim | scenario permission |
| control-plane auth | API caller authorization | participant authority |

Rules:

- Authority and scope refs resolve through existing named-reference and
  targetable-element validation patterns.
- Action authority belongs in typed preconditions, evidence refs, and governed
  failure classes such as `authority_denied`.
- Observation access belongs in observation boundaries and visibility
  transitions.
- Credentials, tokens, prompts, answer keys, hidden truth, and backend private
  config are never inline authority evidence.
- Runtime denial, backend sandboxing, or control-plane authorization may enforce
  a boundary, but they do not define the authored boundary by themselves.

Implementation issue #207 owns executable authority/scope extensions beyond
the ACT-601 fields already shipped.

## ACT-608 - Participant Behavior Modes

Behavior mode declares how decisions are selected or controlled at the
participant decision-surface boundary.

| Requirement wording | Controlled vocabulary term |
| --- | --- |
| autonomous | `autonomous` |
| scripted | `scripted` |
| policy-directed | `policy-directed` |
| replayed | `replayed` |
| supervised | `human-supervised` |
| mixed-control | `mixed-control` |

Rules:

- Mode values resolve through `participant-decision-surface-modes`.
- The current `supervised` requirement wording maps to `human-supervised`.
  A broader supervised concept requires a governed vocabulary update.
- Behavior mode is distinct from participant role, implementation kind,
  backend feature support, control-plane authorization, and interaction class.
- `replayed` mode identifies decision-source replay. It does not by itself
  define trajectory corpus, evidence retention, dataset, or benchmark split
  semantics.
- `policy-directed` mode identifies policy-mediated decisions. It does not
  grant scenario authority or control-plane permission.
- `mixed-control` mode identifies combined control over one participant
  decision surface. It is not multi-participant interaction semantics.

Implementation issue #208 owns executable declaration, selection, validation,
and conformance for behavior modes.

## Cross-Clause Invariants

| ID | Invariant | Primary clauses |
| --- | --- | --- |
| PBM-01 | Action names are not portable behavior semantics without action contracts. | ACT-602, ACT-603 |
| PBM-02 | Observation is a participant-visible projection, not hidden truth or archival evidence. | ACT-603, ACT-606 |
| PBM-03 | Authority is authored scenario meaning, not credential possession or control-plane auth. | ACT-607 |
| PBM-04 | Behavior mode resolves through controlled vocabularies, not artifact-local strings. | ACT-608 |
| PBM-05 | Runtime behavior history is evidence of realized behavior, not the authored behavior specification. | ACT-602, ACT-606 |
| PBM-06 | Backend support claims require governed feature terms, support levels, disclosure refs, and evidence contracts. | ACT-602, ACT-608 |
| PBM-07 | Hidden prompts, credentials, answer keys, raw command output, backend-private objects, and adjudication assets stay out of portable behavior artifacts. | ACT-606, ACT-607 |
| PBM-08 | Unknown, opaque, unsupported, not applicable, bounded, lossy, and exact are distinct claims. | ACT-602, ACT-603, ACT-608 |

## Child-Issue Mapping

| Issue | UID | Executable ownership |
| --- | --- | --- |
| #204 | ACT-602 | Machine-checkable behavior model gates, fixtures, and conformance evidence. |
| #205 | ACT-603 | Abstract interaction implementation coverage over actions, observations, state, preconditions, effects, failure classes, and joint interactions. |
| #206 | ACT-606 | First-class behavior specification authoring, validation, versioning, and traceability. |
| #207 | ACT-607 | Authority/scope boundary authoring, validation, evidence, and failure mapping. |
| #208 | ACT-608 | Behavior-mode declaration, selection, controlled-vocabulary validation, and conformance. |

## Verification Expectations

Any executable issue that claims this model must provide:

- parser/model negative tests for unknown fields and variable-created keys;
- semantic validation tests for unresolved action, observation, outcome,
  authority, scope, and behavior-spec refs;
- generated schema and publication-manifest checks when a contract is added or
  changed;
- valid and invalid fixtures for every new portable contract;
- runtime or conformance tests that prove behavior-history, observation,
  authority, mode, evidence, and redaction invariants; and
- Ground Control IMPLEMENTS/TESTS or DOCUMENTS traceability links appropriate
  to the artifact.

Issue #77 satisfies the design requirement by publishing ADR-067 and this
formal spec. It does not claim runtime emission, SDL syntax, schema, fixture,
or conformance implementation for #204 through #208.
