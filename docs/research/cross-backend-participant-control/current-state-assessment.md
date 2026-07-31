# Mixed Cross-Backend Participant Control: Current-State Assessment

Date: 2026-07-31

## Finding

RAES has the semantic, contract, trial, runtime, time, backend, and evidence
parts needed to design mixed participant realization. It does not have the
composition authority that joins those parts for one simultaneously mixed
trial.

The gap is not a new scenario language, participant model, controller field,
message bus, or evidence database. It is one revisioned allocation/topology
profile plus downstream extensions at existing seams.

## Authored scenario and participant meaning

### Existing coverage

ADR-022 and the participant formal design already distinguish:

- participant identity and behavior;
- action, observation, visibility, failure, causality, outcome, and time;
- portable intent from backend realization; and
- simulation, emulation, live, human-mediated, or stubbed realization
  profiles.

ADR-085 and SEM-230 add participant/audience-relative projection, exact-cut
policy, memory, strategies, release, delivery/observation separation, and
explicit noninterference boundaries.

ADR-095 adds decision epochs, stable state cuts, order, and participant
knowledge. ADR-101 adds independent confidentiality/integrity flow design and
the final-sink boundary without changing participant identity.

### Missing

No authored or formal profile defines:

- which stable participant/action/observation scope is realized by which
  apparatus component;
- which components coexist in one trial;
- the edges between them; or
- how realization allocation changes without changing portable SDL meaning.

Backend selection must not be added to SDL to fill this gap. Doing so would
make scenario membership depend on apparatus and undermine cross-backend
comparison.

## Experiment and trial realization

### Existing coverage

ADR-084 defines:

```text
authored family
  -> deterministic composition
  -> experiment selection
  -> deterministic trial compilation/admission
  -> SDL instantiation
  -> runtime/backend execution
  -> archival run/study evidence
```

`AdmittedTrialEntryModel` already seals:

- one logical coordinate and run id;
- selections and bindings;
- stochastic draws;
- apparatus;
- execution control;
- instantiation provenance; and
- a content digest.

`AdmittedApparatusBindingModel` pins manifest refs, participant manifests, one
realization-envelope identity, and capability refs.

`ExperimentApparatusContextModel` can report multiple apparatus components,
selected manifests, compatibility declarations, configuration, stochastic
controls, clocks, measurement channels, observed setup evidence, and
limitations.

The distinction is important:

- admitted apparatus is pre-run intent;
- apparatus context is observed run evidence.

### Missing

The admitted apparatus binding has no mixed component graph. Its one
realization envelope cannot express:

- one participant runtime in simulation and another in emulation;
- one action family realized by a simulator and another by an operational
  tool;
- one observation supplied by hardware while other state remains simulated;
- explicit bridge mappings between components; or
- a finite within-run activation schedule.

The apparatus context cannot be repurposed as authorization because it is
observational. It may validate that an admitted profile was realized, but it
cannot create the profile after execution.

ADR-084 already supplies the identity answer:

- a realization change between trials is a new admitted entry/run linked to
  its source;
- a retry is not a new selection; and
- runtime facts and schedulers cannot change trial identity or apparatus.

SEM-234 adds only finite pre-admitted within-run phases. It does not reopen
these rules.

## Participant control

### Existing coverage

ACT-617, API-409, RUN-310, and the participant-control models separate:

- participant proposal and external direction;
- approval and denial;
- handoff, override, cancellation, and intervention;
- controller and authority;
- controlled scope;
- action admission and execution;
- state revision and validity;
- idempotency and replay; and
- append-only control history.

The current effective state has one acting controller per participant and
episode. A transition is revision-fenced. The runtime uses state/history
checks and atomic persistence.

### Missing and deliberately rejected

`controlled_scope_refs` can describe scope, but one controller field cannot
represent different simultaneous owners of different scopes. A validity
window does not supply lease renewal, expiry, fencing, or order. A list of
controllers does not define joint authority.

Issue #813 therefore rejects positive revision-1 support for:

- simultaneous scoped controllers;
- leases;
- quorum, priority, arbitration, or unanimity;
- fused authority; and
- oscillation/livelock handling beyond the existing single-controller
  transition.

These remain a future versioned profile. Mixed backends are realization
providers below action admission, not controllers.

## Crossings, delivery, and information flow

### Existing coverage

API-423 supplies typed crossing occurrences for request, decision,
transformation/release, delivery attempt, delivery, observation, and audit.
Context validation binds participant, controller, audience, policy cut, order,
predecessors, and evidence.

RUN-319 provides the shared deny-first mediator and final persistence
boundary. SEM-230 owns participant projection. DSL-142 preserves directed
inject identity and delivery semantics.

### Missing

No edge binds one runtime component to another with:

- adapter/bridge identity;
- action or observation transformation;
- policy projection;
- cross-clock/order mapping;
- capability strength;
- mapping loss; and
- failure/readback evidence.

This is a composition-edge profile, not a new message carrier. API-423 remains
the crossing history.

## Time and ordering

### Existing coverage

ADR-090 and ADR-091 define:

- time domains and clock authority;
- progression and scheduling;
- participant time-management context;
- backend time capabilities;
- realized time models;
- ordering basis; and
- conformance diagnostics.

The existing participant semantics reject timestamp-as-causality and require
weakening when a backend serializes or drops concurrency.

### Missing

The current trial apparatus does not bind a mapping between each component's
clock/order service. A mixed trial needs:

- per-component clock and role;
- edge mapping;
- request/grant or pacing behavior;
- lookahead when applicable;
- delivery-order realization;
- serialization/readback evidence; and
- partial/unknown disposition.

No mapping means no exact cross-clock order claim.

## Backend capability and conformance

### Existing coverage

API-407 extends `backend-manifest/v2`
`capabilities.participant_runtime.feature_support`. It separates declared
support, effective strength, required contracts, constraints, disclosures,
downgrade, realization, and conformance.

The support order is:

```text
unsupported < disclosed_weak < bounded < exact
```

Existing conformance reports, case results, participant-policy probes,
realization probes, and time diagnostics are reusable.

### Missing

The governed vocabulary has no complete mixed-composition feature family for:

- allocation granularity;
- topology/bridge behavior;
- cross-clock mapping;
- phase membership;
- ownership-transfer realization;
- addressed delivery;
- policy projection across a bridge; or
- mapping-loss/readback evidence.

The gap belongs in the existing manifest and conformance surfaces. A new
capability block would duplicate API-407.

## Evidence and scientific claims

### Existing coverage

RAES already has:

- experiment task, protocol, run, study, apparatus, evidence, measure, and
  traceability records;
- associated artifact manifests;
- realization envelopes and provenance;
- behavioral claim bindings;
- safe digests and limitations; and
- explicit separation of finite falsification, conformance, model checking,
  proof, and empirical study.

The issue #600 corpus supplies two separate backend runs and a bounded
invariant ledger. Issues #810 through #812 further separate opacity,
bisimulation, adversarial control, runtime, backend, and proof claims.

### Missing

No protocol binds:

- pure simulation;
- pure emulation/operation;
- simultaneous mixed composition;
- staged realization;
- open-loop and closed-loop behavior; and
- cross-backend mismatch cases

under one revisioned evidence plan.

The existing paired corpus must not be relabeled as mixed. It can be a source
of apparatus and invariant patterns only.

## Exact reuse map

| Concern | Incumbent | SEM-234/ASR-537 use |
| --- | --- | --- |
| Scenario meaning | SDL phases, ADR-078, ADR-084 | Keep backend-neutral |
| Stable targets | ADR-076 canonical addresses | Allocation scope refs |
| Experiment selection | Experiment authoring/factor/allocation contracts | Select profile and trial variation |
| Trial admission | Admitted trial plan and compiler | Pin graph and finite phases |
| Apparatus | Manifests, constraints, contexts | Components and observed realization |
| Realizability | ADR-070 envelopes | Per-component admitted support |
| Participant control | ACT-617/API-409/RUN-310 | One controller; revision-fenced handoff |
| Crossing/IFC | SEM-230/API-423/RUN-319 | Edge policy and histories |
| Time | ADR-090/091 time contracts | Per-component clocks and edge mappings |
| Capability | API-407 | Mixed service terms and effective strength |
| Conformance | Existing report/case/probe families | Service-specific probes |
| Evidence | Experiment/evidence/associated-artifact contracts | Complete apparatus and result binding |
| Claims | ADR-081/ASR-535 | Prevent relation promotion |

## Required downstream changes

The dependency order is:

1. #1013: semantic authority;
2. #1014: portable contracts;
3. #1015: deterministic trial admission;
4. #1016: fail-closed runtime coordination;
5. #1017: backend capability and conformance;
6. #1018: demonstration and evaluation; and
7. #1019: evidence-led claim reconciliation.

Until those issues land, mixed realization is DRAFT design only.
