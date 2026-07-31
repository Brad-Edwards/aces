# Cross-Backend Participant Control: Prior Art and Design Criteria

Date: 2026-07-31

This assessment asks a narrower question than general simulation
interoperability:

> What authority, composition, time, policy, and evidence must survive when
> the same participant-control intent is realized in simulation,
> emulation/operation, or both within one admitted trial?

It distinguishes mechanism, semantic authority, security policy, conformance,
empirical transfer, and proof. A common interface or successful run is never
promoted into a stronger relation.

The machine-readable source disposition is in
[`implementation-program.json`](implementation-program.json).

## 1. HLA 4 and the IEEE 1516 family

The current family is:

- [IEEE 1516-2025](https://standards.ieee.org/ieee/1516/6687/) for the
  framework and rules;
- [IEEE 1516.1-2025](https://standards.ieee.org/ieee/1516.1/6688/) for the
  federate interface; and
- [IEEE 1516.2-2025](https://standards.ieee.org/ieee/1516.2/6689/) for the
  Object Model Template.

The 2025 edition matters. Earlier RAES literature work cited the 2010 family.
Edition pinning is necessary because directed interactions and migration
details belong to newer HLA 4 work and must not be attributed to an older
standard.

### Services worth adopting as precedents

HLA separates concerns that a mixed RAES profile must also keep distinct:

- federation membership and synchronization;
- declaration and publish/subscribe;
- object instances, interactions, and attribute updates;
- data distribution and interest management;
- object/attribute ownership;
- directed interaction delivery;
- receive-order and timestamp-order delivery; and
- logical-time advancement, grants, and lookahead.

The
[HLA 4 migration analysis](https://www.sisostandards.org/resource/resmgr/events/siw/2024_siw/abstracts_2024_siw.pdf)
also describes staged deployment where earlier and newer federates coexist.
That is useful precedent for versioned capability negotiation and migration.

HLA ownership is materially stronger than current RAES realization machinery
in one dimension: it standardizes scoped responsibility transfer for
attributes of a simulated object. Ownership can be partial, transferred, or
unowned. Negotiated and unconditional divestiture and push/pull acquisition
produce visible service outcomes.

RAES should adopt the transition-state lesson:

```text
requested -> offered -> pending -> committed
          \-> failed | expired | cancelled | stale
```

The participant-control join stays different:

```text
participant
  -> acting controller
  -> authority basis and scope
  -> action admission
  -> realization provider
  -> backend effect
```

An HLA owner is responsible for publishing state for an attribute. That does
not identify who may direct a participant or authorize an action.

### Explicit rejections

- OMT standardizes representation and syntax, not domain content or
  behavioral equivalence.
- Declaration and DDM route data. They do not authorize a participant
  projection.
- Directed interaction selects a delivery target. It does not prove
  successful delivery or participant observation.
- RTI authorization, transport encryption, and federation membership are not
  RAES markings, declassification, IFC, or noninterference.
- HLA conformance does not imply that a backend realizes SEM-234.

### RAES consequences

- Capability entries name the exact HLA service and edition.
- Ownership and time services produce runtime readback and conformance
  evidence, not method-presence claims.
- Adapter transformations re-enter normal action/observation validation.
- HLA-specific handles and FOM fields stay behind the adapter boundary unless
  a future external-interchange requirement justifies a portable carrier.

## 2. NIST integrated federations and UCEF

NIST's
[integrated HLA federation work](https://www.nist.gov/publications/integrating-multiple-hla-federations-effective-simulation-based-evaluations-cps)
starts from limits of a single flat federation. The paper identifies:

- information hiding;
- limited shared resources;
- multiple time scales;
- organizational and IT policy boundaries; and
- translation across federations.

It evaluates shared-federate, parallel-connected, hierarchical, and clustered
patterns. An inter-federation component may need separate threads and explicit
message/time translation. Two logical times do not necessarily have a valid
mapping.

NIST's [UCEF architecture](https://www.nist.gov/ctl/smart-connected-systems-division/iot-devices-and-infrastructures-group/how-does-ucef-work)
explicitly integrates simulators, emulators, and hardware. A federate can be
equipment, a simulation model, or a combination. That is direct precedent for
requiring both OR and AND realization modes.

The
[Portico TLS/forwarder work](https://www.nist.gov/publications/extending-portico-hla-federations-federations-transport-layer-security)
uses routing/firewall behavior to limit exchange across clusters. It remains a
transport and topology mechanism.

### Metadata remains an information surface

Payload hiding alone does not close:

- membership;
- subscription and object/interaction class;
- region or destination;
- message size and cadence;
- synchronization and time requests;
- ownership change;
- retraction; or
- differential success and failure.

RAES authorizes the participant/audience projection before bridge filtering.
The bridge may narrow the set. It cannot widen it.

## 3. ACTING and EDL-FG

The 2026
[EDL-FG paper](https://arxiv.org/abs/2605.12170) separates:

- technical infrastructure;
- scenario screenplay, storylines, events, and injects;
- expected participant actions;
- federation;
- telemetry and situational awareness;
- exercise assessment;
- capacity; and
- resource brokering.

It explicitly describes hybrid simulated and emulated IT/OT component
abstractions. It also permits dynamic trainer modification.

This is strong framing for mixed composition. The RAES mapping is:

| EDL-FG concern | RAES incumbent |
| --- | --- |
| Scenario and screenplay | SDL, workflow/story, and scenario-family authority |
| Inject | Existing inject identity plus DSL-142 delivery |
| Participant interaction | Participant action/control plus API-423 crossing |
| Infrastructure | Apparatus manifests and admitted realization |
| Federation | Explicit topology and composition edges |
| Telemetry | Observation and evidence contracts |
| Assessment | Experiment, evaluation, run, evidence, and measure contracts |
| Capacity/brokering | Apparatus constraints and scheduling, not scenario meaning |

EDL-FG is a recent project-backed paper, not yet a mature interoperability
standard. The paper identifies systematic quantitative evaluation and
validation as future work. RAES therefore adopts the separation and mixed
component lesson, not its schema or a semantic-equivalence claim.

## 4. CybORG

The [CybORG paper](https://arxiv.org/abs/2108.09118) and
[official repository](https://github.com/cage-challenge/CybORG) define a
common agent interface for simulation and emulation. A scenario supplies
backend-specific implementations of actions.

The 2021 design selects simulation or emulation for a run. It is an OR
precedent, not evidence that components coexist in one world.

The transfer experiment is especially important. Across 21 agents and ten
evaluations each, 139 of 210 emulation evaluations succeeded. Some failures
came from agents learning a simulation observation artifact that was absent
from emulation.

That result establishes four rules for RAES:

1. interface parity is not observation equivalence;
2. action names do not remove backend-specific preconditions/effects/failures;
3. mismatches must remain first-class evidence; and
4. a simulation admission result cannot authorize a transformed emulation
   command without fresh validation and admission.

## 5. CyGIL

[CyGIL](https://arxiv.org/abs/2304.01244) combines:

- CyGIL-E, an emulation environment operating on a real network;
- CyGIL-S, a simulator derived from emulation traces; and
- an iterative training and evaluation loop between them.

It argues that abstract simulator actions can diverge from operational tools
and block transfer. A data-derived simulator approximates the
observation-transition model represented in its data. Unknown transitions
remain because coverage is incomplete.

The paper reports a 50-of-50 emulation evaluation for one policy after its
iteration. It also reports that smaller data collection was insufficient,
switching rules were heuristic, and broader scenarios remain future work.

The adoption is not “full transferability.” It is:

- model/data/version provenance is part of the simulator identity;
- unknown transitions require an explicit disposition;
- emulation-to-simulation regeneration creates a new derived artifact;
- simulation-to-emulation evaluation creates a new run; and
- empirical transfer is bounded to its scenario, agent, apparatus, trials,
  and measures.

This motivates linked inter-trial realization changes. It does not require
pretending alternating runs are one trial.

## 6. CyberBattleSim

The
[official CyberBattleSim repository](https://github.com/microsoft/CyberBattleSim)
provides an abstract simulated enterprise network, action space, observation,
attacker/defender structure, and reward model. Its documentation emphasizes
that the environment is deliberately simplistic, emits no real network
traffic, and is not for direct application to real systems.

Useful lessons:

- action/observation vocabulary can remain safe and abstract;
- simulator fidelity limits must be visible; and
- simulated compromise “ownership” is a domain fact, not HLA ownership or
  participant control.

CyberBattleSim is suitable as one candidate simulated lane. It supplies no
emulation or transfer claim.

## 7. FMI and HELICS

[FMI 3.0.2](https://fmi-standard.org/docs/3.0.2/) distinguishes Model
Exchange, Co-Simulation, and Scheduled Execution.

For co-simulation:

- exchange happens at communication points;
- an importer controls synchronization; and
- the co-simulation algorithm is not part of FMI.

For Scheduled Execution:

- scheduling is externalized; and
- local priorities do not determine the cross-component global order.

The lesson is exact: a shared package or interface does not supply composition
semantics.

[HELICS timing guidance](https://docs.helics.org/en/latest/user-guide/fundamental_topics/timing_configuration.html)
uses time requests and grants. Its
[dynamic-federation guidance](https://docs.helics.org/en/latest/user-guide/advanced_topics/dynamic_federations.html)
supports late joining, including real-time and hardware-in-the-loop
components used during only part of a co-simulation.

RAES adopts a bounded version:

- all possible members, manifests, mappings, clocks, and policies are admitted
  before execution;
- phase membership changes are finite and append-only;
- an unadmitted late join is rejected; and
- the runtime coordinator remains separate from participant controller
  authority.

## 8. LVC and synthetic-world composition

The
[NATO modelling and simulation glossary](https://www.sto.nato.int/publications/Management%20Reports/AMSP-02-MSGlossaryofTerms.pdf)
defines LVC as a mixture of live, virtual, and constructive simulation.
Related NATO work also records inconsistent usage of the categories.

That inconsistency makes labels unsafe as authority. A realization form needs:

- a definition;
- apparatus identity;
- capability and support strength;
- mapping and loss;
- time/pacing behavior;
- participant/action/observation scope; and
- evidence.

LVC is therefore a useful taxonomy and deployment precedent, not a portable
semantic relation.

## 9. Digital twins

The
[Digital Twin Consortium definition](https://www.digitaltwinconsortium.org/initiatives/the-definition-of-a-digital-twin/)
requires a data-driven virtual representation with synchronized interaction
at a specified frequency and fidelity. A prototype before synchronization is
not the same thing as a twin.

Relevant ISO work includes:

- [ISO 23247-2:2021](https://www.iso.org/standard/78743.html), reference
  architecture;
- [ISO 23247-5:2026](https://www.iso.org/standard/87425.html), digital thread;
  and
- [ISO 23247-6:2026](https://www.iso.org/standard/87426.html), composition.

ISO 23247-6 distinguishes integrated, unified, and federated composition.
Those are useful topology coordinates. They do not determine participant
authority or turn a cyber range into a digital twin.

RAES keeps these terms distinct:

- digital model;
- digital shadow;
- synchronized digital twin;
- simulator;
- emulator;
- co-simulation; and
- mixed runtime composition.

The design adopts synchronization, fidelity, topology, derivation, and
interaction as declared coordinates. It rejects “digital twin” as an
unevidenced backend label.

## 10. DSEEP, SIRL, VV&A, and provenance

[IEEE 1730.1-2023](https://standards.ieee.org/ieee/1730.1/11140/) overlays the
Distributed Simulation Engineering and Execution Process for environments
using multiple distributed-simulation architectures.

[IEEE 1730.2-2022](https://standards.ieee.org/ieee/1730.2/7311/) supplies a
VV&A overlay. The earlier HLA-specific IEEE 1516.4 practice is inactive; the
current DSEEP overlay is the relevant active source.

[SISO-STD-024-2024](https://www.sisostandards.org/page/StandardsProducts) and
[SISO-GUIDE-011-2024](https://www.sisostandards.org/resource/resmgr/guidance_products_/siso-guide-011-2024.pdf)
define Simulation Interoperability Readiness Levels. SIRL assesses whether
engineering evidence is sufficient to assess integration risk. It explicitly
does not determine that simulations are interoperable.

That distinction becomes a reporting rule:

```text
documentation/readiness
  != interface compatibility
  != contract conformance
  != runtime realization
  != empirical transfer
  != trace relation
  != bisimulation
  != IFC/noninterference
  != backend equivalence
```

[W3C PROV](https://www.w3.org/TR/prov-overview/) separates entities,
activities, agents, generation, derivation, and responsibility.
[RO-Crate 1.2](https://www.researchobject.org/ro-crate/specification/1.2/)
packages research data with contextual metadata.

RAES already has experiment, run, study, apparatus, evidence, associated
artifact, realization, and traceability carriers. It reuses those concepts
without adding a parallel PROV or RO-Crate schema. External packaging remains
future work unless an interchange requirement needs it.

## Design criteria

### DC-01 — Both OR and AND are explicit

The profile represents alternative realization and simultaneous mixed
realization separately. Two separate backend runs are never counted as a mixed
trial.

### DC-02 — SDL meaning remains backend-neutral

Allocation uses stable compiled refs in admitted experiment/trial intent.
Backend names and adapter classes do not enter authored world meaning.

### DC-03 — Allocation is bounded and complete

Revision 1 supports participant runtime, controlled scope, action family,
observation source, and crossing boundary. Missing or overlapping allocations
are rejected unless an explicit later arbitration profile governs them.

### DC-04 — Topology is not inferred

Single, integrated, unified, bridged/federated, and nested topologies are
named. Every edge is directed and evidence-bound.

### DC-05 — Authority relations remain independent

Participant identity, controller, authority scope, action admission, backend
responsibility, HLA ownership, routing, and disclosure remain separate.

### DC-06 — Revision 1 has one acting controller

Multiple realization providers do not imply distributed control. Lease,
simultaneous scoped-owner, and joint/fused controller semantics are rejected
until a later version supplies complete transition, order, failure, and
evidence rules.

### DC-07 — Routing follows authorization

SEM-230 and API-423 authorize the projection. DDM, filtering, encryption, and
directed delivery may realize it but never grant it.

### DC-08 — Metadata is part of the observation surface

Membership, subscriptions, classes, regions, sizes, timing, synchronization,
ownership, retraction, and failure are analyzed for leakage.

### DC-09 — Cross-clock order is admitted

Clock/domain mappings, progression roles, lookahead, grants, delivery order,
serialization, and readback are explicit. Timestamps alone are weak
disclosure.

### DC-10 — Trial variation preserves identity

Inter-trial changes use new linked plan entries/runs. Within-run membership
changes use finite pre-admitted phases. No change rewrites prior facts.

### DC-11 — Open/closed is three axes

Control loop, world assumption, and federation membership are separate
profiles with separate authority.

### DC-12 — Failure has no silent fallback

Missing, stale, unsupported, contradictory, or unmapped authority,
capability, policy, clock/order, allocation, or evidence rejects or produces a
declared weaker result. It never silently chooses another provider.

### DC-13 — Evidence binds the complete apparatus

Results pin scenario/policy, plan/run, apparatus/adapters, allocation,
topology, clocks, capability/conformance, mappings, model/data/seed,
loss/limitations, and reproduction.

### DC-14 — Claims do not promote

Conformance, readiness, transfer, trace inclusion, bisimulation,
IFC/noninterference, and equivalence remain independent.

### DC-15 — The program reuses RAES carriers

No generic federation event, universal message, HLA DTO, side store,
exception family, logger, or parallel conformance report is introduced.
