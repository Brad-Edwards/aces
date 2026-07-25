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
scheduler/environment-, and order-relative and composes existing ACES world,
view, local-history, archival-evidence, control, authority, marking, and
provenance objects. The new content is limited to coordinates needed to bind
those prior definitions to existing ACES carriers. It does not copy publication
syntax or code and does not claim wire compatibility, universal proof,
production enforcement, or backend realization. No copied-code notice or
third-party distribution obligation is introduced by these publication
citations.

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
