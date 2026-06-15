# Related-Work Comparison Search Log

Issue: #508 (review LIT-1 / LIT-4).

Purpose: record the primary sources and grounded findings behind every non-ACES
cell in [`docs/explain/sdl/related-work-comparison.md`](../../explain/sdl/related-work-comparison.md).
Each precedent's capabilities were checked against its own documentation,
standard text, source, or originating-author literature — not from memory.

## Source Rule

Primary sources only for competitor capability claims: the maintaining body's
standard, the originating authors' papers, official project documentation, or
the project's own source repository. Where only a secondary source was
available, it is marked secondary. Absence-of-feature claims are made only after
searching the primary documentation and source for the feature.

## Tooling

- Web search and direct page/document fetch for standards, official
  documentation, and source repositories.
- Direct reads of project source (Rust parser, Python reference implementation,
  scenario/topology YAML, TOSCA type definitions) where the source is the
  authoritative encoding of the model.
- Crossref / arXiv / Semantic Scholar for DOIs and originating-author papers.

The eight comparison dimensions are defined in the comparison page; the findings
below are organized by precedent and then by dimension.

## Comparison Dimensions

1. Runtime inventory depth — observed runtime node/service state as first-class
   declarative inventory, distinct from authored topology.
2. Typed relationship subtypes — typed, directed relationship edges between
   elements, beyond plain topology links.
3. Participant behavior / episode contracts — actions, observations, rewards,
   episodes, partial observability as first-class semantics.
4. Authoring-vs-instantiation separation — a logical authored surface distinct
   from concrete deployment/instantiation.
5. Backend agnosticism + conformance — the same scenario across multiple
   backends, with a conformance contract.
6. Declarative objectives / workflows — objectives and workflow graphs as
   authored constructs.
7. Provenance / disclosure surfaces — run provenance, evidence, and participant
   information-boundary/disclosure as explicit artifacts.
8. Time semantics status — clock authority, logical/virtual time, ordering,
   causality, pacing/synchronization.

---

## Open Cyber Range (OCR) SDL

YAML-based, VM-centric authoring language for cyber defense/training exercises
(infrastructure, deployable software features, scoring objectives, narrative
event timelines, participant teams), implemented as a Rust parser used across
the Open Cyber Range platform (Ranger / Handlers / Deputy).

Primary sources:

- SDL Reference — Open Cyber Range documentation.
  <https://documentation.opencyberrange.ee/docs/sdl/reference/> and
  <https://documentation.opencyberrange.ee/docs/sdl/example>
- SDL-parser source (Rust) — Open-Cyber-Range, GitHub.
  <https://github.com/Open-Cyber-Range/SDL-parser> (`node.rs`, `feature.rs`,
  `infrastructure.rs`, `inject.rs`, `event.rs`, `script.rs`, `story.rs`,
  `entity.rs`, `metric.rs`, `evaluation.rs`, `vulnerability.rs`)
- Ranger / VMware Handlers / Deputy — Open Cyber Range documentation.
  <https://documentation.opencyberrange.ee/docs/ranger/>,
  <https://documentation.opencyberrange.ee/docs/handlers/vmware-handlers/>
- Kaunis, K. *Hypervisor Agnostic Scenario Definition Language for Cyber
  Ranges.* TalTech MSc thesis, 2022 (design intent / scope).

Findings:

1. Runtime inventory depth — **no.** Nodes are `Switch | VM`; Features are
   `service | configuration | artifact` install/configure actions
   (deployment intent), not observed runtime state. No directory, datastore,
   mail, DNS, or RBAC node types (SDL Reference; SDL-parser `node.rs`,
   `feature.rs`).
2. Typed relationship subtypes — **partial.** `InfraNode.links` (network) and
   `InfraNode.dependencies` (deploy order) are structurally distinct, and
   injects carry `from-entity`/`to-entities`; all are string references, with no
   trust/integration edge type or edge-type discriminator (SDL-parser
   `infrastructure.rs`, `inject.rs`).
3. Participant behavior / episode contracts — **partial.** Entities carry
   exercise roles (White/Green/Red/Blue) and receive event-triggered injects;
   condition-driven Metrics score trainees 0–1. No agent actions, observations,
   rewards, or episode/partial-observability semantics (SDL Reference, Entities
   and Metrics).
4. Authoring-vs-instantiation separation — **partial.** Node templates and
   `count`/infrastructure addressing separate capability from instances
   (Templater builds reusable VM templates; Machiner instantiates), but the
   language is the VM-deployment spec, not a backend-neutral logical surface
   (SDL Reference, Infrastructure; VMware Handlers).
5. Backend agnosticism + conformance — **partial.** Ranger exposes a
   "virtualization-platform-agnostic" gRPC handler contract, but the only
   shipped handler suite is VMware vSphere/NSX-T and no backend conformance
   test suite was found (Ranger docs; VMware Handlers docs).
6. Declarative objectives / workflows — **yes.** Goals → TLOs → Evaluations →
   Metrics → Conditions scoring chain, plus Stories → Scripts → Events →
   Injects narrative timelines with parallel storylines and AND-gated condition
   triggers (SDL Reference and Example).
7. Provenance / disclosure surfaces — **partial.** Inject stdout/stderr are
   captured to the manager view and events are timestamped and scoped per
   entity, but the SDL document has no first-class provenance/disclosure
   construct (Executor / Ranger participant-guide docs).
8. Time semantics status — **partial.** Script `start-time`/`end-time`, `speed`
   multipliers, and condition poll `interval` give relative/narrative pacing;
   no clock authority, logical time, or causality model (SDL Reference,
   Scripts/Stories; SDL-parser `script.rs`, `story.rs`).

---

## CybORG (CAGE Challenge)

Discrete-step reinforcement-learning gym for autonomous cyber operations, with a
shared OpenAI-gym interface over both a simulation backend and an AWS emulation
backend, used across the CAGE Challenge series.

Primary sources:

- Standen, M., Lucas, M., Bowman, D., Richer, T.J., Kim, J., Marriott, D.
  "CybORG: A Gym for the Development of Autonomous Cyber Agents." arXiv:2108.09118,
  2021. <https://arxiv.org/abs/2108.09118>
- CybORG source and CAGE Challenge scenario files — cage-challenge, GitHub.
  <https://github.com/cage-challenge/CybORG>,
  CAGE Challenge 2 `Scenario1b.yaml`, CAGE Challenge 4 challenge details
  (<https://cage-challenge.github.io/cage-challenge-4/pages/>).

Findings:

1. Runtime inventory depth — **partial.** Host YAML declares OS, services,
   processes, users, and subnets and the simulator tracks live session/process
   state as a finite-state machine, but this is internal simulation state, not a
   separate first-class declarative runtime-inventory surface (arXiv:2108.09118,
   §2 "Scenario").
2. Typed relationship subtypes — **partial.** Host-to-subnet membership,
   process parent/child, and subnet NACL rules are implicit in the YAML and the
   FSM; there is no named, directed typed-edge vocabulary (arXiv:2108.09118 §2;
   `Scenario1b.yaml`).
3. Participant behavior / episode contracts — **yes.** Per-agent action spaces,
   role-filtered observations, per-agent reward calculators, partial
   observability, and step- or goal-bounded episodes are first-class; CAGE 4
   adds multi-agent coordination with restricted inter-agent messaging
   (arXiv:2108.09118 §2; `Scenario1b.yaml`; CAGE 4 details).
4. Authoring-vs-instantiation separation — **partial.** A scenario file deploys
   to sim or emulation and re-randomizes on reset; the `ScenarioGenerator`
   abstraction separates generation from use, but the boundary is a Python-code
   interface, not a declared logical/instance schema (arXiv:2108.09118 §3;
   CybORG changelog v3.0).
5. Backend agnosticism + conformance — **partial.** A genuine dual sim+emulation
   design sits behind one gym interface (each action defined for both), but
   backend equivalence is asserted/empirical, not a published conformance
   contract (arXiv:2108.09118 §2–3).
6. Declarative objectives / workflows — **partial.** Objectives are encoded in
   reward-calculator classes and episode-termination conditions, computed in
   code; there is no declarative objective expression or workflow graph
   (`Scenario1b.yaml` `reward_calculator_type`; arXiv:2108.09118).
7. Provenance / disclosure surfaces — **no.** Role-based observation filtering is
   an RL mechanism enforced at runtime, not a declared disclosure-boundary or
   provenance artifact; evaluation emits text result files, not structured
   provenance (arXiv:2108.09118 §2; CAGE 4 details).
8. Time semantics status — **partial.** Discrete steps with a fixed agent order,
   and CAGE 4 variable action durations (ticks); no clock authority,
   logical-time, or causality specification (arXiv:2108.09118 §2; CAGE 4
   details).

---

## CACAO Security Playbooks v2.0 (OASIS)

JSON schema and taxonomy for documenting, sharing, and orchestrating
cybersecurity response/detection/mitigation workflows across organizational and
tooling boundaries — a playbook workflow standard, not a cyber-range topology or
scenario DSL.

Primary source:

- CACAO Security Playbooks Version 2.0, OASIS Committee Specification 01,
  27 November 2023.
  <https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html>

Findings (section numbers are CACAO v2.0):

1. Runtime inventory depth — **no.** Agents and Targets (§7) are authoring-time
   connection references for command dispatch; runtime node/service state is
   explicitly out of scope.
2. Typed relationship subtypes — **partial.** Workflow steps carry typed,
   directed routing edges (`on_completion`, `on_success`/`on_failure`,
   `on_true`/`on_false`, `cases`, `next_steps`), but there is no general typed
   inter-object relationship graph (§4).
3. Participant behavior / episode contracts — **no.** No agent observation,
   reward, episode, or partial-observability concept; the standard orchestrates
   command execution (§1, §7).
4. Authoring-vs-instantiation separation — **yes.** `playbook_variables` are
   authored; `__variable__` substitution and step `in_args`/`out_args` resolve
   values at execution time, with step scope overriding playbook scope
   (§3.1, §4.1, §10.18).
5. Backend agnosticism + conformance — **partial.** Producer/consumer
   conformance classes and abstract agent/target plus multi-engine command
   types support exchange, but the spec notes playbooks "will require some amount
   of modification" per environment, and defines no equivalence test suite (§11).
6. Declarative objectives / workflows — **yes.** A full declarative workflow
   graph with eight step types (start, end, action, playbook-action, parallel,
   if-condition, while-condition, switch-condition), conditional routing, and
   nested playbook invocation (§4).
7. Provenance / disclosure surfaces — **yes.** First-class digital signatures
   (JSON Signature Scheme, embedded/detached, quantum-safe option), TLP/IEP/
   statement data markings applied to all objects, and `created_by` provenance
   (§2.4, §2.5, §9).
8. Time semantics status — **partial.** Step `delay`/`timeout` and playbook
   `valid_from`/`valid_until`; no clock authority or causal-ordering semantics
   (§3.1, §4.1).

---

## SISO Cyber DEM and Cyber FOM

A runtime data-exchange model (not a scenario-authoring DSL) defining a shared
ontology of cyber objects and events/effects so cyber conditions can be exchanged
bi-directionally between cyber ranges, cyber simulations, and the
Live-Virtual-Constructive environments of kinetic simulation. The Cyber FOM is
the HLA-specific federation object model derived from it.

Primary sources:

- SISO-STD-025-2023, Cyber Data Exchange Model (DEM) — SISO, 2023.
  <https://cdn.ymaws.com/www.sisostandards.org/resource/resmgr/standards_products/siso-std-025-2023_cyberdem.pdf>
- SISO-STD-025.3-2024 Cyber Federation Object Model and SIRL User's Guide —
  SISO, 2024.
  <https://www.sisostandards.org/news/690125/Publication-of-Cyber-FOM-and-SIRL-Users-Guide.htm>
- cyberdem-python reference implementation of the CyberDEM object/event model —
  CMU SEI, GitHub.
  <https://github.com/cmu-sei/cyberdem-python> (`base/__init__.py`,
  `enumerations/__init__.py`)
- IEEE Std 1516 (High Level Architecture) for the inherited federation and time
  management framework (secondary, for HLA mechanics).

Findings:

1. Runtime inventory depth — **partial.** Defines exchangeable cyber objects
   (Device, System, Application, OperatingSystem, Service, Network, NetworkLink,
   Data) as transmitted model-state; this is live federation exchange, not an
   authored per-node declarative inventory (cyberdem-python `base`).
2. Typed relationship subtypes — **yes.** A first-class `Relationship` object
   with a `RelationshipType` enumeration of ten directed subtypes
   (Administers/AdministeredBy, ComponentOf/HasComponent, ContainedIn/Contains,
   ProvidedBy/Provides, ResidesOn/HasResident) (cyberdem-python `enumerations`).
3. Participant behavior / episode contracts — **partial.** Typed action/effect
   events (CyberAttack/CyberDefend/CyberRecon with MITRE ATT&CK references; a
   Deny/Detect/Manipulate effect hierarchy) carry `actor_ids`, `target_ids`, and
   a `phase`; no observation model, reward, or episode boundary
   (cyberdem-python `base`).
4. Authoring-vs-instantiation separation — **out of scope.** Objects and events
   are exchanged between running federates at runtime; there is no authored
   scenario surface compiled to an instance (SISO-STD-025-2023 scope;
   originating-author statement that CyberDEM represents cyber events/objects in
   a format independent of simulation interoperability solutions).
5. Backend agnosticism + conformance — **yes.** Designed to be independent of,
   but unambiguously translatable to, HLA/TENA/DIS/JSON; the Cyber FOM is an
   IEEE 1516-compliant HLA FOM, inheriting formal HLA federate conformance
   (SISO-STD-025-2023; SISO-STD-025.3-2024 Cyber FOM; IEEE 1516).
6. Declarative objectives / workflows — **no.** No objective, mission-goal, or
   workflow construct; `CyberOrder` is a command/control directive, not a
   declarative objective or workflow graph (cyberdem-python `base`;
   SISO-STD-025-2023 scope).
7. Provenance / disclosure surfaces — **partial.** A `SensitivityType`
   classification (17 values) plus `Data.confidentiality`, `encrypted`, and
   `status` track information state, but there is no participant
   information-boundary or evidence/provenance artifact (cyberdem-python
   `enumerations`, `base`).
8. Time semantics status — **yes.** `_CyberEvent` carries `event_time` and
   `duration`, and the Cyber FOM inherits the full HLA time-management stack
   (time-advance request/grant, Time Stamp Order delivery, lookahead, GALT,
   time-constrained/regulating roles) (cyberdem-python `base`; IEEE 1516 time
   management; SISO-REF-072-2024).

---

## Academic range DSLs: CRACK, KYPO, CyRIS

Academic cyber-range systems for security-training exercise generation,
deployment, and (CRACK) formal verification. The comparison column leads with
**CRACK** and notes KYPO/CyRIS where they differ.

Primary sources:

- Russo, E., Costa, G., Armando, A. "Building next generation Cyber Ranges with
  CRACK." *Computers & Security* 95:101837, 2020. DOI:
  [10.1016/j.cose.2020.101837](https://doi.org/10.1016/j.cose.2020.101837).
- Russo, E., Costa, G., Armando, A. "Scenario Design and Validation for Next
  Generation Cyber Ranges." IEEE NCA 2018. IEEE Xplore 8548324.
- CRACK source (TOSCA type definitions) — enricorusso/CRACK, GitHub.
  <https://github.com/enricorusso/CRACK>
- Vykopal, J., et al. "KYPO Cyber Range: Design and Use Cases." ICSOFT 2017.
  DOI: [10.5220/0006428203100321](https://doi.org/10.5220/0006428203100321).
- KYPO hands-on training behavior dataset, PMC10770710, 2024;
  KYPO platform documentation, <https://docs.crp.kypo.muni.cz/>.
- Pham, C., Tang, D., Chinen, K.-I., Beuran, R. "CyRIS: A Cyber Range
  Instantiation System for Facilitating Security Training." SoICT 2016. DOI:
  [10.1145/3011077.3011087](https://doi.org/10.1145/3011077.3011087);
  source — crond-jaist/cyris, GitHub.

Findings (verdict leads with CRACK):

1. Runtime inventory depth — **partial.** CRACK node types carry `runtime`
   Datalog predicate maps (`isConnected`, `listeningOn`, `hostACL`,
   `existsRoute`) executed as live checks to confirm authored predicates, not a
   structured inventory record; KYPO/CyRIS topology is static authored YAML
   (Russo et al. 2020; CRACK `types/`; Vykopal et al. 2017; Pham et al. 2016).
2. Typed relationship subtypes — **yes.** CRACK defines typed, directed TOSCA
   relationships (e.g., `SetsWeakPassword`, `SetsEnumerableUsername`) and typed
   capability kinds (VulnerabilityContainer, PrivilegeProvider, KnowledgeProvider,
   GoalProvider, PrincipalProvider); KYPO/CyRIS encode connectivity edges only
   (CRACK `types/sdl.yaml`; Russo et al. 2020).
3. Participant behavior / episode contracts — **partial.** CRACK `Principal`
   nodes carry a role and a knowledge requirement, with Goals linked to
   principals; these are static role/knowledge assignments, not action/
   observation/reward/episode contracts. KYPO prescribes tasks/scoring; CyRIS
   models none (CRACK `types/sdl-principal.yaml`, `sdl-goal.yaml`;
   PMC10770710).
4. Authoring-vs-instantiation separation — **yes.** CRACK separates the SDL
   specification from instantiation via an ARIA TOSCA orchestrator that
   generates OpenStack/Terraform/Packer deploy scripts; KYPO separates a sandbox
   definition from pool allocation (Russo et al. 2020; Vykopal et al. 2017).
5. Backend agnosticism + conformance — **no.** CRACK and KYPO target OpenStack
   only; CyRIS supports KVM and AWS but with no cross-backend conformance suite
   (CRACK `types/openstack-*.yaml`; KYPO OpenStack requirements; Pham et al.
   2016).
6. Declarative objectives / workflows — **yes.** CRACK `Goal` node subtypes
   (CanReach, GainPrivilege, Knows) and `Invariant` types are first-class
   declarative constructs verified against the model; KYPO encodes
   human-readable objectives plus flag answers (CRACK `types/sdl-goal.yaml`,
   `sdl-invariant.yaml`; Russo et al. 2020; PMC10770710).
7. Provenance / disclosure surfaces — **no (KYPO partial).** CRACK `Knows`
   models knowledge as a verification predicate, not a disclosure/provenance
   artifact; KYPO collects observational event logs and command histories, not a
   first-class authored construct (CRACK `types/`; PMC10770710 §3.3–3.4).
8. Time semantics status — **no (KYPO partial).** CRACK's Datalog encoding is
   atemporal (set-theoretic reachability/privilege); KYPO records timestamps and
   notes absolute time does not order events across trainees (relative
   timestamps added); CyRIS has only an `attack_time` date (Russo et al. 2018;
   PMC10770710 §3.5; CyRIS `examples/full.yml`).

CRACK's distinguishing strength is machine-checkable formal verification:
SDL specifications are encoded into Datalog and checked against validation
goals, and verification traces are turned into runtime conformance test cases
(Russo et al. 2018; Russo et al. 2020). ACES's SMT/formal scenario verification
is deferred (see [`precedents.md`](../../explain/sdl/precedents.md), "VSDL SMT
verification"), so this is a genuine dimension where this class leads ACES.

---

## Precedents Scoped Out Of The Matrix

These README-lineage precedents are not comparison columns because their purpose
is not scenario authoring or runtime scenario modeling. Each is accounted for so
the matrix coverage is complete.

- **OCSF** — a normalized security event/finding schema. ACES borrows its
  observation/evidence style; it is not a scenario-authoring or runtime-modeling
  language (<https://ocsf.io/>).
- **STIX 2.1** — a cyber-threat-intelligence object and relationship model. ACES
  adapts its typed-relationship pattern for scenario elements; STIX models
  threat intelligence, not scenarios
  (<https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html>).
- **TENA** — a runtime test-range integration architecture and object-model
  middleware for live test ranges, not an authoring DSL; relevant to runtime
  federation maturity, captured under dimensions 5 and 8
  (<https://www.trmc.osd.mil/tena-about.html>).
- **IEEE HLA (1516)** — a distributed-simulation interoperability architecture
  (RTI, FOM, time management), the substrate the Cyber FOM builds on, not an
  authoring DSL; its time-management strength is represented through the SISO
  Cyber DEM/FOM column (<https://standards.ieee.org/ieee/1516/3744/>).
- **MITRE CALDERA** — an adversary-emulation execution platform; ACES treats it
  as a behavior/execution source scenarios may bind to, not a scenario DSL
  (<https://github.com/mitre/caldera>).
- **Atomic Red Team** — a library of ATT&CK-mapped atomic test definitions;
  test-execution content, not a scenario DSL
  (<https://github.com/redcanaryco/atomic-red-team>).
