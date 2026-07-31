# Issue 813 mixed cross-backend participant-control preflight

Date: 2026-07-31

Issue: #813.

Requirements at preflight: none. The issue title, body, research clarification,
acceptance criteria, and non-goals were the contract. SEM-234 and ASR-537 were
created in DRAFT only after preflight and planning.

This note records the repository-wide guardrails used by the design. It does
not publish a portable contract, alter trial compilation or runtime behavior,
declare a backend capability, execute a demonstration, or establish mixed
realization, transfer, interoperability, information-flow security, or
behavioral equivalence.

## Decisive current-state findings

RAES already separates most authorities that a mixed composition needs:

- ADR-084 and SCE-002 own backend-neutral scenario families, experiment
  selection, deterministic trial admission, apparatus pinning, immutable plan
  and run identities, and runtime-fact limits.
- ADR-085, ADR-095, SEM-230, API-423, RUN-310, and RUN-319 own participant
  projection, one acting controller, authority, action admission, handoff,
  crossing stages, exact state cuts, append-only history, and atomic
  commit-before-effect.
- ADR-090 and ADR-091 own shared time domains, clocks, progression, portable
  time capabilities, realization evidence, and conformance.
- API-407 owns declared and effective backend feature strength, constraints,
  downgrade, realization, and evidence.
- Experiment apparatus, run, evidence, associated-artifact, realization, and
  behavioral-claim contracts already separate apparatus identity, raw
  evidence, derived interpretation, conformance, and formal relations.
- The issue #600 cross-backend corpus compares two separate realizations of the
  same scenario. It is not one simultaneously mixed run.

The missing authority is a revisioned composition profile that can admit
multiple participant realization providers in one trial, bind every edge
between them, represent finite pre-admitted membership changes, and preserve
the existing authority and evidence boundaries. The existing admitted trial
entry pins one realization envelope. The experiment apparatus context may
describe many observed components, but it does not authorize a mixed execution
topology.

Current controller semantics are also narrower than HLA ownership services.
They support one acting controller with active/revoked authority,
revision-fenced transition, and total effective order. They cannot truthfully
claim simultaneous scoped owners, leases, or joint/fused control.

## Binding precedent guardrails

### HLA

Use the current IEEE 1516-2025 family and pin the exact part and edition.
Framework rules, the federate interface, and OMT have different
responsibilities. Adopt the following as service-specific precedents:

- declaration and interest-management capabilities;
- scoped ownership acquisition and divestiture states;
- requested, offered, pending, committed, failed, expired, cancelled, and
  stale transfer outcomes;
- time-regulating and time-constrained roles;
- lookahead, advance requests, grants, receive order, timestamp order, and
  readback evidence; and
- directed delivery as an addressed interaction service.

Reject these conflations:

- object or attribute ownership is not participant identity, controller
  authority, action authority, or handoff;
- publish/subscribe, regions, and DDM are not authorization, declassification,
  IFC, or noninterference;
- directed delivery is not participant observation; and
- OMT representation does not establish common behavior.

### Integrated federations and co-simulation

NIST's integrated-federation work makes bridge topology, information hiding,
independent time scales, translation, and shared-resource effects explicit.
FMI leaves the co-simulation algorithm outside the standard. HELICS makes time
requests/grants and dynamic federation membership explicit.

The RAES consequence is one explicit composition edge per exchange boundary.
Each edge needs component and adapter identities, direction, authority,
action/observation mapping, participant/audience policy, clock/order mapping,
support strength, loss, failure behavior, and evidence. A flat bus, common
interface, or gateway is insufficient.

Unadmitted dynamic membership remains prohibited. A design may admit a finite
within-run phase schedule when all possible members and mappings are pinned
before execution.

### Cyber ranges and agent environments

ACTING/EDL-FG is strong precedent for separating infrastructure, screenplay,
injects, interactions, federation, telemetry, and assessment and for naming
hybrid simulated/emulated components. It is a recent preprint, not a ratified
interoperability standard.

CybORG is evidence that one API can span simulation and emulation while
transfer still fails. Its published experiment succeeded in 139 of 210
emulation evaluations and records simulation-only observation artifacts.
CyGIL is evidence for linked emulation-to-simulation model generation and
simulation-to-emulation evaluation. Its 50-of-50 result remains one bounded
scenario and apparatus result with unknown transitions and heuristic switching.
CyberBattleSim is a safe abstract simulation precedent, not an operational
fidelity claim.

No common interface, successful case, or capability declaration may be
reported as equivalence.

## Architecture guardrails

### Allocation and trial identity

- Portable SDL remains backend-neutral.
- Realization allocation is admitted experiment/trial intent over stable
  compiled refs.
- The first profile may allocate participant runtime, controlled scope, action
  family, observation source, and crossing boundary.
- Runtime and schedulers cannot select outside the sealed allocation.
- An inter-trial realization change creates a linked new plan entry and run.
- A within-run change is a finite pre-admitted phase transition. It appends
  state and evidence and never rewrites trial identity, prior delivery, or
  participant knowledge.

### Control and ownership

Preserve this join:

```text
participant identity
  -> acting controller
  -> authority basis and controlled scope
  -> action admission
  -> selected realization provider
  -> adapter or bridge responsibility
  -> final backend effect
```

HLA ownership belongs beside realization responsibility, not in the
controller field. Pull and push acquisition preserve their initiator and
negotiation evidence but converge only after an atomic revision-fenced commit.
Oscillation needs explicit cycle/livelock, cooldown or retry, and evidence
semantics.

Revision 1 retains exactly one acting controller per participant and episode.
It rejects lease, simultaneous scoped-owner, and joint/fused-control claims.
A future profile needs controller/scope identities, renewal and fencing or
quorum/arbitration semantics, clocks/order, failure and oscillation behavior,
and conformance evidence.

### Information distribution

Routing and filtering realize an already-authorized projection. SEM-230,
API-423, markings, release/declassification, and the exact policy/order cut
remain authoritative.

Leakage analysis includes membership, subscriptions, class, region,
destination, size, timing, synchronization, ownership change, retraction, and
differential failure. Audit retention is an authorized evidence audience, not
participant disclosure.

### Time and ordering

Reuse the accepted time model and conformance machinery. Cross-clock
comparison needs an admitted mapping. A timestamp-only backend is
`disclosed_weak`; it cannot claim governed logical order. Backend
serialization requires a named clock/service, runtime readback, and
conformance evidence.

Staleness binds controller, authority, capability, policy revision, state
revision, history head, and governed order. Wall-clock recency is
insufficient. Rollback, replay, concealment, and retraction append facts; they
do not erase delivery or participant knowledge.

### Open and closed

Do not create one `open` boolean. Separate:

1. open-loop versus closed-loop observation and actuation;
2. closed-world versus bounded-open-world assumptions; and
3. fixed versus pre-admitted dynamic federation membership.

Each has a different authority owner and failure behavior.

## Required existing seams

- SDL ingress: `parse_sdl()`, `parse_sdl_file()`, closed SDL models,
  `SemanticValidator`, compilation, and post-instantiation validation.
- Trial: admitted trial plans, apparatus bindings, realization envelopes,
  cleanup, isolation, immutable identities, and deterministic compilation.
- Control: participant-control contracts, contextual validation, RUN-310
  mediation, revision checks, idempotency, and history-head compare-and-swap.
- Crossing: API-423 carriers, deny-first policy resolution, delivery and
  observation separation, and RUN-319 mediation.
- Time: shared time models, participant time-management context,
  `TimeCapabilities`, realized-time evidence, and conformance diagnostics.
- Backend: API-407 feature support, controlled vocabularies, required
  contracts, effective strength, limitation, downgrade, and conformance.
- Evidence: experiment task/run/apparatus/evidence contracts, associated
  artifacts, realization provenance, behavioral claim bindings, and digests.
- Diagnostics: existing bounded diagnostics, operation receipts, audit events,
  and sanitized backend failures.

Do not add an HLA DTO, universal federation message, generic event,
federation-controller service, side store, exception family, logger, or
duplicate conformance report.

## Demonstration boundaries

The downstream protocol needs pure simulation, pure emulation/operation,
simultaneous mixed, inter-trial transition, pre-admitted phase transition,
open-loop, and closed-loop cases.

Adversarial cases include stale handoff, concurrent intervention, unsupported
or false capability, timestamp-only/unmapped order, simulation-only
observation, unrealizable action, directed-delivery failure, prior-delivery
retraction, and bridge-metadata leakage. Denied authority, policy, mapping,
admission, and commit cases require zero prohibited effects.

Every result binds scenario and policy digests, trial and run identity,
apparatus and adapters, allocation and topology, clocks/order, capability and
conformance, mappings, loss, provenance, limitations, and reproduction
evidence.

## Non-goals

- No issue implementation, schema, runtime coordinator, backend adapter, or
  demonstration.
- No default HLA, FMI, HELICS, EDL-FG, CybORG, CyGIL, or CyberBattleSim
  compatibility.
- No distributed, leased, simultaneous scoped-owner, or joint/fused
  controller support in revision 1.
- No interoperability, transfer, trace inclusion, bisimulation,
  IFC/noninterference, or backend-equivalence result.
