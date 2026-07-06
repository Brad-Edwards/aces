# Related-Work Comparison

This page positions ACES against precedent systems dimension by dimension. It is
the comparison a peer review asks for first: what can ACES express that the
precedents cannot, and where do the precedents still lead ACES.

It is an evidence surface, not a ranking and not a marketing claim. ACES leads on
some dimensions and trails on others, and several ACES surfaces are formally
specified but still materializing in the runtime. For element-by-element source
provenance see [Design Precedents](precedents.md); for the narrative source map
see [Lineage and Prior Work](lineage.md). Every non-ACES cell below is grounded
in the precedent's own documentation, standard text, source, or
originating-author literature, with the full audit trail in the
[related-work comparison research notes](../../research/related-work-comparison/search-log.md).
ACES cells cite repository specs, ADRs, and contracts; this page does not define
new ACES semantics.

## How To Read The Matrix

Each cell is one of:

- **yes** — the system treats the dimension as a first-class capability.
- **partial** — the system addresses part of the dimension, or addresses it as a
  side effect of another mechanism rather than as a first-class construct.
- **no** — the system does not address the dimension.
- **oos** — out of scope: the dimension is outside the system's design purpose.

Columns:

- **ACES** — this repository.
- **OCR SDL** — Open Cyber Range Scenario Definition Language.
- **CybORG** — the CAGE Challenge reinforcement-learning gym.
- **CACAO** — OASIS CACAO Security Playbooks v2.0.
- **Cyber DEM/FOM** — SISO Cyber Data Exchange Model and Cyber Federation Object
  Model.
- **CRACK\*** — academic range DSLs; the column leads with CRACK and notes KYPO
  and CyRIS where they differ.

The eight dimensions are defined in [Dimensions](#dimensions) below.

## Matrix

| Dimension | ACES | OCR SDL | CybORG | CACAO | Cyber DEM/FOM | CRACK\* |
| --------- | ---- | ------- | ------ | ----- | ------------- | ------- |
| 1. Runtime inventory depth | yes | no | partial | no | partial | partial |
| 2. Typed relationship subtypes | yes | partial | partial | partial | yes | yes |
| 3. Participant behavior / episode contracts | partial | partial | yes | no | partial | partial |
| 4. Authoring vs. instantiation separation | yes | partial | partial | yes | oos | yes |
| 5. Backend agnosticism + conformance | yes | partial | partial | partial | yes | no |
| 6. Declarative objectives / workflows | yes | yes | partial | yes | no | yes |
| 7. Provenance / disclosure surfaces | yes | partial | no | yes | partial | no |
| 8. Time semantics status | partial | partial | partial | partial | yes | no |

\* CRACK ([Russo et al. 2020](https://doi.org/10.1016/j.cose.2020.101837)),
with KYPO ([Vykopal et al. 2017](https://doi.org/10.5220/0006428203100321)) and
CyRIS ([Pham et al. 2016](https://doi.org/10.1145/3011077.3011087)) noted where
they differ.

## Dimensions

Each dimension below states its definition, then a one-line justification and
citation per system. Competitor citations are summarized here and recorded in
full in the [research notes](../../research/related-work-comparison/search-log.md).

### 1. Runtime inventory depth

Observed runtime node and service state — service listeners, identity and
directory authorities, datastores, mail and DNS services, application RBAC
stores, software components — modeled as first-class declarative inventory,
distinct from authored topology.

- **ACES — yes.** A typed `Node.runtime.*` family models observed state
  (identity authorities, application authorizations, datastore/mail/DNS
  services, security-monitoring managers, detection engines, service listeners,
  and more) as inventory distinct from authored nodes; see the runtime sections
  of [precedents.md](precedents.md) ("Deliberate Omissions") and
  [lineage.md](lineage.md), governed by ADRs such as
  [ADR-043](../../decisions/adrs/adr-043-runtime-service-listener-surface.md)
  and
  [ADR-054](../../decisions/adrs/adr-054-participant-runtime-observable-lifecycle.md).
- **OCR SDL — no.** Nodes are VMs or switches and Features are
  service/configuration/artifact deployment actions, with no observed-state
  inventory ([SDL Reference](https://documentation.opencyberrange.ee/docs/sdl/reference/)).
- **CybORG — partial.** Host YAML and the simulator's finite-state machine track
  services, processes, and sessions, but as internal simulation state rather than
  a separate declarative inventory surface
  ([Standen et al. 2021, §2](https://arxiv.org/abs/2108.09118)).
- **CACAO — no.** Agents and targets are command-dispatch references; runtime
  service state is out of scope
  ([CACAO v2.0 §7](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)).
- **Cyber DEM/FOM — partial.** Defines exchangeable cyber objects (Device,
  System, Service, Network, Data) as transmitted model-state, not an authored
  per-node inventory
  ([SISO-STD-025-2023](https://cdn.ymaws.com/www.sisostandards.org/resource/resmgr/standards_products/siso-std-025-2023_cyberdem.pdf)).
- **CRACK\* — partial.** CRACK node types carry Datalog `runtime` predicates that
  verify authored facts on deployed nodes, not a structured inventory record;
  KYPO/CyRIS topology is static
  ([Russo et al. 2020](https://doi.org/10.1016/j.cose.2020.101837)).

### 2. Typed relationship subtypes

Typed, directed relationship edges between scenario elements, beyond plain
topology or workflow-routing links.

- **ACES — yes.** Seven STIX-derived relationship types plus typed-detail edges
  (forwarding, service-integration, proxy-upstream), with typed runtime
  relationship subtypes specified in
  [ADR-052](../../decisions/adrs/adr-052-typed-runtime-relationship-subtypes.md)
  (see also the STIX mapping in [precedents.md](precedents.md)).
- **OCR SDL — partial.** Network links and deploy-order dependencies are
  structurally distinct string references, with no trust/integration edge type
  ([SDL-parser source](https://github.com/Open-Cyber-Range/SDL-parser)).
- **CybORG — partial.** Host-subnet, process parent/child, and NACL relations are
  implicit in the YAML and FSM, with no named typed-edge vocabulary
  ([Standen et al. 2021, §2](https://arxiv.org/abs/2108.09118)).
- **CACAO — partial.** Workflow steps carry typed routing edges
  (`on_success`/`on_failure`, `on_true`/`on_false`, `cases`), but there is no
  general typed inter-object relationship graph
  ([CACAO v2.0 §4](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)).
- **Cyber DEM/FOM — yes.** A first-class `Relationship` object with a
  `RelationshipType` enumeration of ten directed subtypes (Administers,
  ComponentOf, ContainedIn, ProvidedBy, ResidesOn and inverses)
  ([cyberdem-python](https://github.com/cmu-sei/cyberdem-python)).
- **CRACK\* — yes.** CRACK defines typed, directed TOSCA relationships
  (`SetsWeakPassword`, `SetsEnumerableUsername`) and typed capability kinds
  ([Russo et al. 2020](https://doi.org/10.1016/j.cose.2020.101837)).

### 3. Participant behavior / episode contracts

Participant actions, observations, rewards, episodes, and partial observability
as first-class semantics.

- **ACES — partial.** A formal participant-semantics specification defines
  actions, observations, visibility, causality, and outcomes portable across
  human, AI-agent, scripted, and simulated participants
  ([ADR-022](../../decisions/adrs/adr-022-participant-behavior-and-interaction-semantics.md),
  `specs/formal/participant-semantics/`),
  with backend-facing contracts in
  [ADR-060](../../decisions/adrs/adr-060-participant-backend-facing-contract-surface.md);
  the executed episode runtime is still materializing.
- **OCR SDL — partial.** Entities hold exercise roles and receive event-triggered
  injects, and Metrics score trainees, but there are no agent
  action/observation/reward/episode semantics
  ([SDL Reference](https://documentation.opencyberrange.ee/docs/sdl/reference/)).
- **CybORG — yes.** Per-agent action spaces, role-filtered observations,
  per-agent rewards, partial observability, and bounded episodes are the system's
  core ([Standen et al. 2021, §2](https://arxiv.org/abs/2108.09118)).
- **CACAO — no.** No agent observation, reward, or episode concept; CACAO
  orchestrates command execution
  ([CACAO v2.0 §1, §7](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)).
- **Cyber DEM/FOM — partial.** Typed action/effect events carry actor, target,
  and phase, but there is no observation model, reward, or episode boundary
  ([cyberdem-python](https://github.com/cmu-sei/cyberdem-python)).
- **CRACK\* — partial.** CRACK `Principal` nodes carry role and knowledge linked
  to Goals, as static assignments rather than behavioral contracts
  ([Russo et al. 2020](https://doi.org/10.1016/j.cose.2020.101837)).

### 4. Authoring vs. instantiation separation

A logical authored scenario surface distinct from concrete deployment or
instantiation.

- **ACES — yes.** A logical scenario surface is kept separate from backend
  realization, with instantiation-time variable resolution
  (`specs/sdl/variables-and-instantiation.md`,
  [explicitness-realization-semantics.md](../reference/explicitness-realization-semantics.md)).
- **OCR SDL — partial.** Node templates and `count`/infrastructure addressing
  separate capability from instances, but the language is the VM-deployment spec
  ([SDL Reference](https://documentation.opencyberrange.ee/docs/sdl/reference/);
  [VMware Handlers](https://documentation.opencyberrange.ee/docs/handlers/vmware-handlers/)).
- **CybORG — partial.** A scenario deploys to sim or emulation and re-randomizes
  on reset via a `ScenarioGenerator`, but the boundary is a Python-code
  interface, not a declared schema
  ([Standen et al. 2021, §3](https://arxiv.org/abs/2108.09118)).
- **CACAO — yes.** `playbook_variables` are authored and `__variable__`
  substitution resolves values at execution time
  ([CACAO v2.0 §3.1, §10.18](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)).
- **Cyber DEM/FOM — oos.** A runtime data-exchange model between running
  federates; there is no authored scenario compiled to an instance
  ([SISO-STD-025-2023](https://cdn.ymaws.com/www.sisostandards.org/resource/resmgr/standards_products/siso-std-025-2023_cyberdem.pdf)).
- **CRACK\* — yes.** CRACK separates the SDL specification from instantiation via
  a TOSCA orchestrator that generates deploy scripts; KYPO separates a sandbox
  definition from pool allocation
  ([Russo et al. 2020](https://doi.org/10.1016/j.cose.2020.101837);
  [Vykopal et al. 2017](https://doi.org/10.5220/0006428203100321)).

### 5. Backend agnosticism + conformance

The same scenario realized across multiple backends, with a conformance
contract between definition and backend.

- **ACES — yes.** A backend-agnostic boundary with a defined backend-conformance
  model and conformance profiles
  ([backend-conformance.md](../reference/backend-conformance.md),
  `contracts/profiles/backend/`,
  [ADR-009](../../decisions/adrs/adr-009-normative-artifact-authority-and-repository-structure.md));
  the conformance contract is defined while concrete backend implementations are
  still being built.
- **OCR SDL — partial.** Ranger exposes a platform-agnostic gRPC handler
  contract, but only a VMware handler ships and no conformance suite was found
  ([Ranger docs](https://documentation.opencyberrange.ee/docs/ranger/)).
- **CybORG — partial.** A dual sim+emulation design sits behind one gym
  interface, but backend equivalence is asserted, not a published conformance
  contract ([Standen et al. 2021, §2–3](https://arxiv.org/abs/2108.09118)).
- **CACAO — partial.** Producer/consumer conformance classes and multi-engine
  command types support exchange, though the spec notes playbooks require
  per-environment modification and defines no equivalence test suite
  ([CACAO v2.0 §11](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)).
- **Cyber DEM/FOM — yes.** Independent of, but translatable to, HLA/TENA/DIS/JSON;
  the Cyber FOM is an IEEE 1516-compliant HLA FOM inheriting formal federate
  conformance
  ([SISO Cyber FOM / SIRL](https://www.sisostandards.org/news/690125/Publication-of-Cyber-FOM-and-SIRL-Users-Guide.htm)).
- **CRACK\* — no.** CRACK and KYPO target OpenStack only; CyRIS supports KVM and
  AWS but with no cross-backend conformance suite
  ([Russo et al. 2020](https://doi.org/10.1016/j.cose.2020.101837)).

### 6. Declarative objectives / workflows

Objectives and workflow graphs (branching, parallel, joins) as authored
constructs.

- **ACES — yes.** Declarative objectives (actor-target-window-success, where
  success references observable `conditions`) and a workflow graph (decisions,
  switch/case, parallel, joins, retries, cancel and timeout, compensation).
  Unlike OCR, ACES carries **no** in-SDL scoring chain: the OCR-inherited
  `metrics`/`evaluations`/`tlos`/`goals` sections were removed by
  [ADR-073](../../decisions/adrs/adr-073-scoring-reward-language-scope.md), and
  graded scoring/reward lives in the experiment/evaluator plane (ADR-055/064/069)
  ([objective-semantics.md](../reference/objective-semantics.md),
  [assessment-semantics.md](../reference/assessment-semantics.md),
  `specs/formal/objectives/`, `specs/formal/workflows/`).
- **OCR SDL — yes.** A Goals → TLOs → Evaluations → Metrics → Conditions scoring
  chain and Stories → Scripts → Events → Injects timelines with parallel
  storylines and AND-gated triggers
  ([SDL Reference](https://documentation.opencyberrange.ee/docs/sdl/reference/)).
- **CybORG — partial.** Objectives are encoded in reward-calculator classes and
  termination conditions computed in code, not declared
  ([Standen et al. 2021](https://arxiv.org/abs/2108.09118)).
- **CACAO — yes.** A declarative workflow graph with eight step types
  (start, end, action, playbook-action, parallel, if-, while-, switch-condition)
  and nested playbook invocation
  ([CACAO v2.0 §4](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)).
- **Cyber DEM/FOM — no.** No objective or workflow construct; `CyberOrder` is a
  command/control directive
  ([cyberdem-python](https://github.com/cmu-sei/cyberdem-python)).
- **CRACK\* — yes.** CRACK `Goal` subtypes (CanReach, GainPrivilege, Knows) and
  `Invariant` types are first-class declarative constructs verified against the
  model ([Russo et al. 2020](https://doi.org/10.1016/j.cose.2020.101837)).

### 7. Provenance / disclosure surfaces

Run provenance and evidence, and participant information-boundary / disclosure,
as explicit artifacts.

- **ACES — yes.** Participant information-boundary projection plus runtime value
  redaction and credential-posture classification
  ([ADR-056](../../decisions/adrs/adr-056-runtime-observed-values-and-credential-posture.md),
  [ADR-057](../../decisions/adrs/adr-057-runtime-secret-name-classifier-boundaries.md)),
  participant-implementation provenance
  ([ADR-041](../../decisions/adrs/adr-041-participant-implementation-manifest-and-provenance.md)),
  and experiment-core run records
  ([ADR-055](../../decisions/adrs/adr-055-experiment-core-contract-boundary.md)).
- **OCR SDL — partial.** Inject stdout/stderr capture and timestamped per-entity
  events provide runtime evidence, but the SDL has no first-class
  provenance/disclosure construct
  ([Ranger / Executor docs](https://documentation.opencyberrange.ee/docs/ranger/)).
- **CybORG — no.** Observation filtering is an RL mechanism, not a declared
  disclosure or provenance artifact
  ([Standen et al. 2021, §2](https://arxiv.org/abs/2108.09118)).
- **CACAO — yes.** First-class digital signatures (JSON Signature Scheme,
  quantum-safe option) and TLP/IEP/statement data markings on all objects
  ([CACAO v2.0 §2.4, §2.5](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)).
- **Cyber DEM/FOM — partial.** A `SensitivityType` classification and
  data-state attributes track information state, but there is no participant
  disclosure-boundary or evidence artifact
  ([cyberdem-python](https://github.com/cmu-sei/cyberdem-python)).
- **CRACK\* — no.** CRACK `Knows` is a verification predicate, not a provenance
  artifact; KYPO collects observational event logs only (partial), not an
  authored construct
  ([Russo et al. 2020](https://doi.org/10.1016/j.cose.2020.101837);
  [KYPO dataset, PMC10770710](https://pmc.ncbi.nlm.nih.gov/articles/PMC10770710/)).

### 8. Time semantics status

Clock authority, logical or virtual time, ordering, causality, and
pacing/synchronization.

- **ACES — partial.** ACES separates timestamp, ordering, clock authority,
  pacing, and causality at the lineage level and is materializing the authoring
  surface (the
  [Runtime, Time, And Causality](lineage.md#runtime-time-and-causality)
  section; [SEM-213 temporal-participant preflight](../../decisions/sem-213-temporal-participant-preflight.md)).
  The full time/clock authoring model is **not complete**.
- **OCR SDL — partial.** Relative script offsets and `speed` multipliers provide
  narrative pacing, with no clock authority or causality
  ([SDL Reference](https://documentation.opencyberrange.ee/docs/sdl/reference/)).
- **CybORG — partial.** Discrete steps with fixed agent order, and variable
  action durations in CAGE 4, but no clock-authority or causality specification
  ([Standen et al. 2021, §2](https://arxiv.org/abs/2108.09118)).
- **CACAO — partial.** Step `delay`/`timeout` and playbook
  `valid_from`/`valid_until`, with no clock-authority or causal-ordering
  semantics
  ([CACAO v2.0 §3.1, §4.1](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)).
- **Cyber DEM/FOM — yes.** Event timestamps and durations plus the inherited HLA
  time-management stack (Time Stamp Order delivery, lookahead, GALT,
  time-constrained/regulating roles)
  ([SISO Cyber FOM](https://www.sisostandards.org/news/690125/Publication-of-Cyber-FOM-and-SIRL-Users-Guide.htm);
  [IEEE 1516](https://standards.ieee.org/ieee/1516/3744/)).
- **CRACK\* — no.** CRACK's Datalog encoding is atemporal; KYPO records
  timestamps for analysis (partial) but not as a scenario-language semantic
  ([Russo et al. 2018, IEEE NCA](https://doi.org/10.1016/j.cose.2020.101837);
  [KYPO dataset, PMC10770710](https://pmc.ncbi.nlm.nih.gov/articles/PMC10770710/)).

## Where Precedents Lead ACES

The matrix is not one-directional. Several precedents are more mature than ACES
on dimensions they were built for, and the documentation states this directly.

- **Time semantics and federated time management — Cyber DEM/FOM, TENA, HLA.**
  The Cyber FOM inherits IEEE 1516 HLA time management: Time Stamp Order
  delivery, lookahead, GALT, and conservative/optimistic execution with
  distributed causality. ACES cites this literature but its time-authoring
  surface is partial and explicitly incomplete
  ([IEEE 1516](https://standards.ieee.org/ieee/1516/3744/)).
- **Standardization and federation interoperability — Cyber DEM/FOM, TENA, HLA.**
  SISO-STD-025-2023 is an approved multi-vendor standard with HLA-conformant
  federation and canonical mappings to HLA/TENA/DIS/JSON. ACES has a defined
  conformance model but no equivalent standards body, conformance authority, or
  multi-vendor implementor community
  ([SISO-STD-025-2023](https://cdn.ymaws.com/www.sisostandards.org/resource/resmgr/standards_products/siso-std-025-2023_cyberdem.pdf)).
- **Declarative workflow taxonomy and signed provenance — CACAO.** CACAO ships an
  OASIS-standardized eight-step workflow taxonomy with conditional and looping
  steps, plus first-class digital signatures and TLP/IEP data markings — a
  signed-provenance mechanism ACES does not have
  ([CACAO v2.0](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)).
- **Executed RL episode discipline — CybORG.** CybORG's per-agent observation,
  reward, partial-observability, and multi-agent episode machinery is a working,
  iterated implementation; ACES specifies participant semantics formally but the
  executed episode runtime is still materializing
  ([Standen et al. 2021](https://arxiv.org/abs/2108.09118)).
- **Formal scenario verification — CRACK.** CRACK encodes scenarios into Datalog,
  checks them against validation goals, and turns verification traces into
  runtime conformance tests. ACES's SMT/formal scenario verification is deferred
  (see [precedents.md](precedents.md), "VSDL SMT verification")
  ([Russo et al. 2020](https://doi.org/10.1016/j.cose.2020.101837)).
- **Operational training-runtime maturity — OCR SDL.** Open Cyber Range ships a
  deployed scoring and narrative-orchestration runtime (Ranger, VMware handlers,
  Deputy package library, participant UI); ACES's comparable runtime is younger
  ([Open Cyber Range docs](https://documentation.opencyberrange.ee/docs/)).

## Where ACES Leads

ACES's distinguishing contributions, against this set, are the depth of
first-class **runtime inventory** (dimension 1) and the consistent **separation
of authored meaning, instantiation, backend realization, participant
implementations, runtime state, and evidence** (dimensions 4, 5, 7). No system
in this comparison models observed runtime node state — identity authorities,
datastores, detection engines, application RBAC stores, and similar — as a
typed, redaction-aware inventory distinct from authored topology. Those gains are
expressivity gains in the authoring and runtime-modeling layer; they do not
extend to the federated time management, standardization, or formal-verification
maturity the precedents above hold.

## Precedents Scoped Out Of The Matrix

These README lineage precedents are not comparison columns
because their purpose is not scenario authoring or runtime scenario modeling;
each is accounted for here so coverage is complete.

- **OCSF** — a normalized security event/finding schema. ACES borrows its
  observation/evidence style; it is not a scenario language
  (<https://ocsf.io/>).
- **STIX 2.1** — a cyber-threat-intelligence object/relationship model. ACES
  adapts its typed-relationship pattern; STIX models threat intelligence, not
  scenarios
  (<https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html>).
- **TENA** — runtime test-range integration middleware, not an authoring DSL; its
  federation maturity is reflected in dimensions 5 and 8
  (<https://www.trmc.osd.mil/tena-about.html>).
- **IEEE HLA (1516)** — a distributed-simulation interoperability architecture
  and the substrate the Cyber FOM builds on, not an authoring DSL; represented
  through the Cyber DEM/FOM column
  (<https://standards.ieee.org/ieee/1516/3744/>).
- **MITRE CALDERA** — an adversary-emulation execution platform scenarios may
  bind to, not a scenario DSL (<https://github.com/mitre/caldera>).
- **Atomic Red Team** — a library of ATT&CK-mapped atomic test definitions;
  test-execution content, not a scenario DSL
  (<https://github.com/redcanaryco/atomic-red-team>).

## References

- [Related-work comparison research notes](../../research/related-work-comparison/index.md)
  and [search log](../../research/related-work-comparison/search-log.md) — the
  primary sources and grounded findings behind every non-ACES cell.
- [Design Precedents](precedents.md) — element-level source mapping.
- [Lineage and Prior Work](lineage.md) — narrative source map.
- [Documentation Style Guide](../reference/documentation-style-guide.md) — the
  accuracy-before-persuasion and citation rules this page follows.
