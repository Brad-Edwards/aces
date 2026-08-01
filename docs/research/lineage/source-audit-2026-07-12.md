# SDL Lineage Source Audit - 2026-07-12

This bounded audit records the external identity and license checks used to
populate `contracts/provenance/sdl-lineage-ledger-v1.json`. It is evidence for
the ledger, not normative SDL authority and not a legal opinion. The checked-in
ledger and its offline gate preserve the reviewed results without making CI
depend on live services.

## Method

- Git sources were resolved through the public GitHub commit and contents APIs.
- Publication identity was checked against DOI registry metadata and the DOI's
  publisher destination; title, authors, year, container, and DOI were compared
  as separate fields.
- OASIS standards were checked against their canonical immutable version URLs.
- Current ACES paths were compared with the initial extracted SDL commit
  `2e73ee6ce11ef42fef10e1837ee2bb96570d030d`; explicit port statements were
  treated as derivation evidence, not inferred from similar names alone.

## Open Cyber Range SDL

- Project: Open Cyber Range SDL Parser.
- Release: v0.21.2.
- Full revision: `fe83e8281fc4b954967fbaa5a0d099007ddcb06c`.
- Revision date: 2024-12-20.
- Revision record: <https://github.com/Open-Cyber-Range/SDL-parser/commit/fe83e8281fc4b954967fbaa5a0d099007ddcb06c>.
- Source boundary: `sdl-parser/src/*.rs` at that revision, narrowed per ledger
  claim to the named Rust model file and ACES model boundary.
- License at the reviewed revision: MIT, copyright 2022 CR14,
  <https://github.com/Open-Cyber-Range/SDL-parser/blob/fe83e8281fc4b954967fbaa5a0d099007ddcb06c/LICENSE>.
- ACES derivation evidence: the initial extracted `scenario.py` identifies its
  OCR-derived top-level sections, and `nodes.py` states that it ports OCR
  `Node`/`VM`/`Switch`/`Resources`/`Role` structures. Current
  explanatory prose also used "direct port" for several OCR families. The
  audit therefore adopts the conservative disposition that the upstream MIT
  notice is required and includes it in `THIRD_PARTY_NOTICES.md`.
- Compatibility: partial syntax ancestry only. ACES does not claim drop-in
  parser, schema, validation, or runtime compatibility with OCR v0.21.2.

## CACAO v2.0

OASIS publishes *CACAO Security Playbooks Version 2.0*, Committee
Specification 01, at
<https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html>.
ACES adapts selected variable and workflow-graph concerns; it does not claim to
implement the CACAO object model or wire format.

## STIX v2.1

OASIS publishes *STIX Version 2.1* at
<https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html>. The ACES
relationship family adapts the typed directed-edge pattern; it is not a STIX
Relationship SRO and is not STIX serialization-compatible.

## CyRIS

The verified publication used by the ledger is Razvan Beuran et al.,
*Cybersecurity Education and Training Support System: CyRIS*, IEICE
Transactions on Information and Systems (2018),
<https://doi.org/10.1587/transinf.2017EDP7207>. An earlier candidate DOI,
`10.1007/978-3-319-24018-3_18`, was rejected because it resolves to an
unrelated publication. ACES adapts the account/content placement concerns, not
CyRIS code or deployment syntax.

### CyRIS v1.2 source pin

- Release/revision: 1.2 at
  `5f0d7843fed3dff782f7f62da9f8bcaa9a2a7481` (2020-12-17).
- Revision record:
  <https://github.com/crond-jaist/cyris/commit/5f0d7843fed3dff782f7f62da9f8bcaa9a2a7481>.
- Reviewed source boundary: `examples/basic.yml` marks a guest with
  `entry_point: yes`; `main/clone_environment.py` maps that entry point to TCP
  3389 for `windows.7` and TCP 22 otherwise.
- License at the reviewed revision: BSD-3-Clause,
  <https://github.com/crond-jaist/cyris/blob/5f0d7843fed3dff782f7f62da9f8bcaa9a2a7481/LICENSE>.
- Disposition: semantic analogue only. ACES adapts explicit entry eligibility
  but rejects CyRIS's OS-to-channel inference, deployment tunnel mechanics,
  generated accounts/passwords, addresses, and ports. No code or syntax was
  copied.

## CybORG

The ledger uses Standen et al., *CybORG: A Gym for the Development of
Autonomous Cyber Agents*, arXiv:2108.09118 (2021),
<https://arxiv.org/abs/2108.09118>. It supports the participant/agent concern;
the ACES agent and participant contracts are ACES-native models rather than a
copy of the CybORG API or scenario schema.

### CybORG v3.0 source pin

- Release/revision: v3.0 at
  `a2d03f99e587af153ae0ac50fb94ba6272e4fff2` (2022-10-13).
- Revision record:
  <https://github.com/cage-challenge/CybORG/commit/a2d03f99e587af153ae0ac50fb94ba6272e4fff2>.
- Reviewed source boundary:
  `CybORG/Simulator/Scenarios/scenario_files/Scenario1.yaml`, where
  `Agents.Blue.starting_sessions` includes an explicit `username`, `hostname`,
  `type: SSH`, and session name.
- License at the reviewed revision: MIT, with the repository's additional
  public-domain notice,
  <https://github.com/cage-challenge/CybORG/blob/a2d03f99e587af153ae0ac50fb94ba6272e4fff2/LICENSE>.
- Disposition: semantic analogue only. ACES adapts participant-local explicit
  host/channel association but does not adopt established-session state,
  simulator session types, usernames, or the scenario syntax. No code or
  syntax was copied.

## Participant Information-Flow Sources

On 2026-07-17, the two publication identities adopted by SEM-230 were checked
as bounded DOI records:

- Joseph A. Goguen and José Meseguer, *Security Policies and Security Models*,
  1982 IEEE Symposium on Security and Privacy,
  <https://doi.org/10.1109/SP.1982.10014>.
- Andrei Sabelfeld and David Sands, *Declassification: Dimensions and
  Principles*, Journal of Computer Security 17(5), 2009,
  <https://doi.org/10.3233/JCS-2009-0352>.

The SEM-230 derivation also reuses formal identities already adopted by the
participant and behavioral-relation authorities: Fagin, Halpern, Moses, and
Vardi's *Reasoning About Knowledge* (ISBN `9780262061629`), Milner's
*A Calculus of Communicating Systems* (DOI `10.1007/3-540-10235-3`), and van
Glabbeek's *The Linear Time-Branching Time Spectrum* (DOI
`10.1007/BFb0039066`). The existing ADR-054 order model supplies the indirect
Lamport happened-before, Winskel event-structure, and Mazurkiewicz trace-theory
lineage. SEM-230 references that governed model rather than creating another
clock, event-structure, or trace definition.

ACES adapts the noninterference policy obligation and explicit
declassification dimensions, interpreted-system local state, and labelled
transition/hiding discipline into the ACES-native `policy-noninterference`
relation. The governed mapping is participant-, audience-, policy-revision-,
exact-cut policy-decision-, participant-memory-, scheduler/environment-, and
order-relative and composes existing ACES world, view, local-history,
archival-evidence, control, authority, marking, and provenance objects. Issue
#909 extends the source set and mapping below for reactive strategies and
backend I/O refinement. It does not copy publication syntax or code and does
not claim wire compatibility, universal proof, production enforcement, or
backend realization. No copied-code notice or third-party distribution
obligation is introduced by these publication citations.

## Issue 909 Refinement, I/O, And Reactive Information-Flow Sources

On 2026-07-26, issue #909 extended the participant-decision lineage audit to
the formal obligations created by decision epoch zero, exact state cuts,
delivery, backend realization, adaptive participants, and cross-episode
memory. The following primary publication identities were checked:

- Martín Abadi and Leslie Lamport, *The Existence of Refinement Mappings*,
  Theoretical Computer Science 82(2), 1991,
  <https://doi.org/10.1016/0304-3975(91)90224-P>.
- Nancy A. Lynch and Frits W. Vaandrager, *Forward and Backward Simulations,
  Part I: Untimed Systems*, Information and Computation 121(2), 1995,
  <https://doi.org/10.1006/inco.1995.1134>.
- Nancy A. Lynch and Mark R. Tuttle, *An Introduction to Input/Output
  Automata*, CWI Quarterly 2(3), 1989, also MIT/LCS/TM-373,
  <https://groups.csail.mit.edu/tds/papers/Lynch/CWI89.html>.
- Rajeev Alur, Thomas A. Henzinger, Orna Kupferman, and Moshe Y. Vardi,
  *Alternating Refinement Relations*, CONCUR 1998,
  <https://doi.org/10.1007/BFb0055622>.
- Michael R. Clarkson and Fred B. Schneider, *Hyperproperties*, Journal of
  Computer Security 18(6), 2010,
  <https://doi.org/10.3233/JCS-2009-0393>.
- Aaron Bohannon, Benjamin C. Pierce, Vilhelm Sjöberg, Stephanie Weirich, and
  Steve Zdancewic, *Reactive Noninterference*, CCS 2009,
  <https://doi.org/10.1145/1653662.1653673>.

RAES adapts the refinement and I/O sources into a directional backend
obligation. Concrete participant behavior must remain admitted by the abstract
RAES semantics, but trace inclusion is not enough: participant and environment
inputs, participant-facing outputs, ownership, availability, fairness, exact
delivery, and state-cut treatment remain explicit obligations. RAES does not
adopt an I/O-automaton wire format and does not make bisimulation the default
backend-conformance relation.

The information-flow sources refine the SEM-230 obligation from an open-loop
trace comparison to a hyperproperty over bounded or universally quantified
run supports under the same adaptive low-participant strategies. The claim
must bind exact-cut policy decisions and an explicit participant-memory scope.
Episode reset alone is not evidence that a human, agent process, external
controller, or shared memory forgot previously delivered information.

These are semantic adaptations only. The issue copies no publication code or
syntax, introduces no source-compatible schema, and claims neither universal
refinement nor universal reactive noninterference from the bounded executable
counterexamples.

## Issue 1001 Boundary-Flow Control Sources

On 2026-08-01, issue #1001 extended the participant information-flow audit to
classical lattice and decentralized IFC, robust downgrading, deployed
operating-system IFC, cross-domain controlled interfaces, dynamic taint, and
whole-system provenance. The following primary publication and institutional
source identities were checked:

- Dorothy E. Denning, *A Lattice Model of Secure Information Flow*,
  Communications of the ACM 19(5), 1976,
  <https://doi.org/10.1145/360051.360056>.
- Andrew C. Myers and Barbara Liskov, *Complete, Safe Information Flow with
  Decentralized Labels*, 1998 IEEE Symposium on Security and Privacy,
  <https://doi.org/10.1109/SECPRI.1998.674834>.
- Andrew C. Myers, Andrei Sabelfeld, and Steve Zdancewic, *Enforcing Robust
  Declassification and Qualified Robustness*, Journal of Computer Security
  14(2), 2006, <https://doi.org/10.3233/JCS-2006-14203>.
- Ethan Cecchetti, Andrew C. Myers, and Owen Arden, *Nonmalleable Information
  Flow Control*, ACM CCS 2017,
  <https://doi.org/10.1145/3133956.3134054>.
- Nickolai Zeldovich, Silas Boyd-Wickizer, Eddie Kohler, and David Mazières,
  *Making Information Flow Explicit in HiStar*, OSDI 2006,
  <https://www.usenix.org/conference/osdi-06/making-information-flow-explicit-histar>.
- Maxwell Krohn, Alexander Yip, Micah Brodsky, Natan Cliffer, M. Frans
  Kaashoek, Eddie Kohler, and Robert Morris, *Information Flow Control for
  Standard OS Abstractions*, SOSP 2007,
  <https://pdos.csail.mit.edu/papers/flume-sosp07.pdf>.
- NIST SP 800-53 Revision 5, control AC-4, *Information Flow Enforcement*,
  <https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final>, and the National
  Security Agency's National Cross Domain Strategy and Management Office,
  <https://www.nsa.gov/Cybersecurity/Partnership/National-Cross-Domain-Strategy-Management-Office/>.
- William Enck, Peter Gilbert, Byung-Gon Chun, Landon P. Cox, Jaeyeon Jung,
  Patrick McDaniel, and Anmol N. Sheth, *TaintDroid: An Information-Flow
  Tracking System for Realtime Privacy Monitoring on Smartphones*, OSDI 2010,
  <https://www.usenix.org/conference/osdi10/taintdroid-information-flow-tracking-system-realtime-privacy-monitoring>.
- Thomas Pasquier, Xueyuan Han, Mark Goldstein, Thomas Moyer, David Eyers,
  Margo Seltzer, and Jean Bacon, *Practical Whole-System Provenance Capture*,
  SoCC 2017, <https://doi.org/10.1145/3127479.3129249>.

RAES adapts the shared semantic discipline: ordered and conservative label
propagation; principal-relative policy; independent confidentiality and
integrity; authority-bounded release and endorsement; controlled-interface
mediation at the final sink; and provenance carriage that does not itself
grant authority. The sources also bound the claim. Fixed global labels do not
capture every mutual-distrust policy; declassification and untaint privileges
can become over-powerful trusted paths; label administration and compatibility
have operational cost; dynamic taint does not completely cover implicit,
native, control, or covert flows; provenance capture has coverage, volume, and
overhead limits; and cross-domain assessment does not prove every downstream
sink safe.

SEM-233 is therefore an ACES-native, revisioned semantic profile rather than a
copy of any source syntax, label vocabulary, operating-system API, guard
product profile, or wire protocol. It claims no source compatibility,
certification, runtime enforcement, backend completeness, or covert-channel
control. No copied-code notice or third-party distribution obligation is
introduced by these publication and institutional citations.

## DSL-437 Participant And Simulation Sources

This addendum was reviewed on 2026-07-24 for DSL-437. It records semantic
precedents only. ACES does not copy source code or syntax and does not claim
compatibility with any source named below.

### DSL-437 participant-interface sources

- CybORG remains pinned to v3.0 commit
  `a2d03f99e587af153ae0ac50fb94ba6272e4fff2`. The additional reviewed
  boundaries are `CybORG/Agents/SimpleAgents/GreenAgent.py`, where a benign
  agent selects from an action set using an observation-facing agent method,
  and `CybORG/Shared/AgentInterface.py`, where action selection, observation
  update, reset, and episode termination are separated. These are evidence for
  treating benign activity as participant behavior, not a source scheduler or
  ACES runtime protocol.
- Towers et al., *Gymnasium: A Standard Interface for Reinforcement Learning
  Environments*, arXiv:2407.17032 (2024),
  <https://arxiv.org/abs/2407.17032>, supplies the reset/step boundary and the
  separation of observation, reward, termination, truncation, and auxiliary
  information.
- Terry et al., *PettingZoo: Gym for Multi-Agent Reinforcement Learning*,
  NeurIPS 2021, <https://arxiv.org/abs/2009.14471>, supplies the Agent
  Environment Cycle and explicit per-agent ordering concern.
- Lanctot et al., *OpenSpiel: A Framework for Reinforcement Learning in Games*,
  arXiv:1908.09453 (2019), <https://arxiv.org/abs/1908.09453>, supplies the
  explicit current-player, legal-action, information-state, chance, and
  simultaneous-move distinctions.

ACES adapts only the participant/environment boundary, episode lifecycle, and
multi-participant ordering concerns. It does not adopt Gymnasium tuples,
PettingZoo AEC or parallel APIs, OpenSpiel state APIs, CybORG action ids, reward
arrays, observations, or agent implementation.

### DSL-437 simulation-time sources

- Foote, *Clock and Time*, ROS 2 Design (2018),
  <https://design.ros2.org/articles/clock_and_time.html>, supplies the
  separation of system, steady, and externally controlled time plus explicit
  pause and time-jump handling.
- Modelica Association Project FMI, *Functional Mock-up Interface
  Specification* 3.0.2 (2024), <https://fmi-standard.org/docs/3.0.2/>, supplies
  importer-controlled advancement, clocks, capability flags, Co-Simulation,
  and Scheduled Execution boundaries.
- IEEE Std 1516.1-2010, *High Level Architecture Federate Interface
  Specification* (2010), DOI
  [10.1109/IEEESTD.2010.5954120](https://doi.org/10.1109/IEEESTD.2010.5954120),
  supplies the time-regulation, time-constrained advancement, and
  timestamp-order delivery service boundary.
- TENA Software Development Activity, *TENA Is Establishing the Foundation for
  DoD Range Interoperability* (2024),
  <https://www.tena-sda.org/attachments/TENA-Overview-FS-2024-02-29-DistA.pdf>,
  supplies the separation among execution middleware, object models,
  repository content, and the Logical Range Data Archive.
- ASAM e.V., *ASAM OpenSCENARIO XML 1.3.0* (2024),
  <https://publications.pages.asam.net/standards/ASAM_OpenSCENARIO/ASAM_OpenSCENARIO_XML/v1.3.0/>,
  supplies the separation among entities, storyboard lifecycle, triggers,
  actions, and simulation-time conditions, especially sections 7.2 and 8.4.

ACES composes those concerns through its own shared-time and participant
contracts. It does not adopt ROS topics or `/clock`, an FMI importer/FMU API,
an HLA federation or RTI, TENA middleware/object models, or the OpenSCENARIO
automotive hierarchy and XML format. DSL-437 uses an ACES-owned wall-paced
driver only for runtime-authority real-time and dilated participant cadence,
requires non-negative reachable cadence points, and rejects externally paced
autonomous policies until an ACES portable transition-notification contract
exists. Coordinated clock/participant reset is an ACES backend transaction
obligation, not a derivation from any source rollback API. No source callback,
transaction protocol, or wire protocol is implied.

### Issue 897 autonomous activity extension review

The participant and simulation-time source boundaries above were re-reviewed
on 2026-07-26 for issue #897. No new external syntax, API, scheduler, calendar,
or wire contract was adopted. Work/pause window algebra, bounded logical-tick
timing, canonical integer-weight selection, dependency/retry/cooldown/burst
policy, exact backend admission, and typed occurrence provenance are
ACES-defined extensions under ADR-092.

The participant activity profile reuses the ACES-governed random-stream
principles and sources already audited in
`docs/research/scenario-variation-trial-realization/prior-art-and-design-criteria.md`.
It publishes a distinct participant-occurrence profile/address and does not
reinterpret experiment selection-policy or variation-point coordinates.
Accordingly, NumPy, Random123, and stream-splitting precedents remain design
criteria rather than source compatibility or copied-code claims. No additional
license notice is required by this extension.

### Issue 898 portable execution-control review

The DSL-437 participant and simulation-time sources above were re-reviewed on
2026-07-26 for issue #898. The following operational-control precedents add
design criteria without changing the existing semantic derivation:

- Modelica Association Project FMI, *Functional Mock-up Interface
  Specification* 3.0.2 (2024), <https://fmi-standard.org/docs/3.0.2/>,
  separates importer-controlled activation, legal lifecycle states, and
  quiescent termination, while explicitly leaving parallel computation outside
  the FMI API.
- gRPC, *Health Checking*,
  <https://grpc.io/docs/guides/health-checking/>, separates
  implementation-maintained service health from ordinary application calls.
- Google, *AIP-151: Long-running operations*,
  <https://google.aip.dev/151>, uses a shared operation resource and makes
  parallel-operation behavior explicit.
- Kubernetes, *Pod Conditions*,
  <https://kubernetes.io/docs/concepts/workloads/pods/pod-condition/>, binds
  observations to an `observedGeneration`, so a consumer can detect stale
  readiness.
- OASIS, *Topology and Orchestration Specification for Cloud Applications
  Version 2.0* (2024),
  <https://docs.oasis-open.org/tosca/TOSCA/v2.0/cs01/TOSCA-v2.0-cs01.html>,
  separates portable lifecycle interface operations from the implementation
  artifacts that realize them.

RAES adapts only the separation of scheduler activation, lifecycle legality,
generation-bound readback, reusable operation status, health/readiness, and
backend-owned implementations. It does not adopt an FMI importer/FMU API, gRPC
service, Google operation schema, Kubernetes resource model, TOSCA topology or
workflow language, or any source lifecycle vocabulary or wire compatibility.
Bounded concurrent native participant execution, coordinated drain/reset, and
action-to-target evidence remain RAES-defined obligations under ADR-092,
ADR-054/RUN-308, ADR-091, and issue #898.

### Issue 899 scoped resource-governance review

The participant execution and deployment-tenancy sources were re-reviewed on
2026-07-27 for issue #899. The following primary sources add design criteria:

- Kubernetes, *Resource Quotas*,
  <https://kubernetes.io/docs/concepts/policy/resource-quotas/>, separates
  namespace-scoped aggregate limits from individual workload declarations.
- Kubernetes, *API Priority and Fairness*,
  <https://kubernetes.io/docs/concepts/cluster-administration/flow-control/>,
  separates classification, priority, queueing, and concurrency allocation.
- Kueue, *Cluster Queue*,
  <https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/>, distinguishes
  nominal quota, cohorts, borrowing/lending, and priority.
- Ghodsi et al., *Dominant Resource Fairness: Fair Allocation of Multiple
  Resource Types* (NSDI 2011),
  <https://www.usenix.org/conference/nsdi11/dominant-resource-fairness-fair-allocation-multiple-resource-types>,
  establishes a multi-resource fairness precedent rather than a single
  scalar-cost reduction.
- Open Container Initiative, *Linux Container Configuration*,
  <https://github.com/opencontainers/runtime-spec/blob/main/config-linux.md>,
  separates logical container configuration from cgroup and device
  enforcement.
- Kubernetes, *Dynamic Resource Allocation*,
  <https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/>,
  separates workload demand, device classes, claims, allocation, and driver
  realization.
- OpenTelemetry, *Metrics semantic conventions* and *Generative AI metrics*,
  <https://opentelemetry.io/docs/specs/semconv/general/metrics/> and
  <https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-metrics.md>,
  require explicit metric identity, units, and bounded attribute sets and
  provide token-usage observation precedent.

RAES adapts only the separation of authored demand, configured capacity,
multi-resource fairness obligations, logical isolation claims, and measured
realization. The v3 SDL shape, owner graph, resource kinds and units, meter
profiles, exact atomic admission, generation-fenced accounting, reset rules,
manifest carriers, runtime events, and evidence obligations are RAES-defined
under ADR-097. RAES does not adopt Kubernetes, Kueue, OCI, or OpenTelemetry
syntax, APIs, object identity, scheduler algorithms, device models, cgroup
configuration, telemetry wire formats, or compatibility. Dominant Resource
Fairness is precedent for keeping vectors comparable; v3 does not claim to
implement the paper's allocator. No source code or schema was copied, and no
additional license notice is required.

## CRACK Publications

Two related works by Russo, Costa, and Armando are distinct and must not share
one title/year label:

- *Scenario Design and Validation for Next Generation Cyber Ranges*, IEEE NCA
  2018, <https://doi.org/10.1109/NCA.2018.8548324>.
- *Building next generation Cyber Ranges with CRACK*, Computers & Security 95
  (2020), <https://doi.org/10.1016/j.cose.2020.101837>.

The first is the scenario-design/validation paper. The second is the later
CRACK system paper. Neither is a source-code derivation claim for ACES.

## Notice And Distribution Disposition

`THIRD_PARTY_NOTICES.md` reproduces the OCR MIT notice required by the
conservative derivation disposition. The source distribution includes that
file, and the wheel build maps the same source notice into the packaged
contract corpus. No separate source-code derivation claim is made for CACAO,
STIX, CyRIS, CybORG, or CRACK, so their citations do not create a copied-code
notice disposition in this audit.

## Current Documentation Link Audit

On 2026-07-12, the URLs in the current SDL lineage, precedent, and related-work
pages were checked as a bounded audit rather than a CI dependency. Four stale
targets were corrected to current primary or archival records: NIST SP 800-61
Revision 3, PettingZoo, Fidge's logical-time paper, and Adya's dissertation.
The two CRACK DOI identities were checked separately as described above.

Some official sites reject automated requests even when the cited page remains
available. Such responses were not recorded as proof that a source is dead.
The offline checker therefore validates recorded identifiers, pins, and
internal evidence, but does not claim that every external server will remain
available or answer an automated request.
