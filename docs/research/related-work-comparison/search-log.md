# Related-Work Comparison Search And Freeze Log

Protocol: `protocol-v1`. Snapshot: `snapshot-2026-07-13`.

This log records how the source set was selected and frozen. The extraction
snapshot is the cell-level record; it contains the exact locator and rationale
for every system-axis and system-case observation.

## Search Rule

Capability claims use primary sources only:

- a maintaining body's exact standard;
- an originating-author publication;
- official project documentation; or
- the project's own source at a full Git commit.

Mutable official documentation requires a retrieval date and SHA-256 digest.
Git evidence requires a full 40-hex commit and a repository artifact path.
Publications and standards require an exact version, edition, DOI, or arXiv
revision. A missing capability is recorded only against the declared source
boundary and extraction procedure; it is not treated as proof of universal
absence.

## Corpus Freeze

The protocol includes eight independent identities:

- **ACES**, Open Cyber Range SDL, CRACK, and VSDL in the scenario-authoring
  stratum;
- **CybORG** in the agent-simulation stratum;
- **CACAO 2.0** in the playbook-orchestration stratum; and
- **Cyber DEM** and **Cyber FOM** in the federation-exchange stratum.

Cyber DEM and Cyber FOM are separate because the former is the
solution-independent model and the latter is its HLA-specific implementation.
CRACK and VSDL are separate because their syntax, formal analysis, delivery
pipeline, and evidence are independently attributable. KYPO and CyRIS from the
earlier comparison are excluded from this fixed corpus rather than folded into
a CRACK family column.

## Pinned External Sources

### Open Cyber Range SDL

- [SDL-parser commit `fe83e8281fc4b954967fbaa5a0d099007ddcb06c`](https://github.com/Open-Cyber-Range/SDL-parser/tree/fe83e8281fc4b954967fbaa5a0d099007ddcb06c),
  especially `sdl-parser/src/` and its parser snapshots.
- [Official SDL Reference Guide](https://documentation.opencyberrange.ee/docs/sdl/reference/),
  retrieved 2026-07-13, SHA-256
  `96d4585aec45b92548d6615de8b0db3c2a076a9d8ddec4877edc0f6098cfcbc4`.

The source and reference cover nodes, infrastructure, features, roles,
entities, stories, scripts, injects, metrics, evaluations, TLOs, and Goals.
The parser repository is the executable evidence boundary; the mutable guide is
used for author-facing semantics and examples.

### CybORG

- Standen et al., [*CybORG: A Gym for the Development of Autonomous Cyber
  Agents*, arXiv:2108.09118v1](https://arxiv.org/abs/2108.09118v1), SHA-256 of
  the v1 PDF
  `69fc40a8ca959adb3333a2716fa4bc6f52bf1e3bebf76129fcf42fe9891ed783`.
- [CybORG commit `2742b5e0ce4330c9b14006b38acd3b5ebe00d6fd`](https://github.com/cage-challenge/CybORG/tree/2742b5e0ce4330c9b14006b38acd3b5ebe00d6fd),
  including `ScenarioGenerator`, `Scenario1b.yaml`, actions, observations, and
  reward calculators.

The paper supplies the common simulation/emulation and research-purpose claims.
The source supplies executable agent, scenario, observation, reward, and
episode evidence.

### CACAO 2.0

- OASIS, [*CACAO Security Playbooks Version 2.0*, Committee Specification 01,
  27 November 2023](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/cs01/security-playbooks-v2.0-cs01.html),
  SHA-256 of the CS01 PDF
  `584eae31ad4be42b6363a600d433d22d460b1f749916a0e3c4cca90ab8b2f428`.

The exact Committee Specification, not the moving `latest` URL, is the source
for workflow objects, variables, sub-playbooks, agents/targets, data markings,
signatures, mandatory features, and producer/consumer conformance.

### Cyber DEM

- SISO, [SISO-STD-025-2023 Cyber Data Exchange Model](https://cdn.ymaws.com/www.sisostandards.org/resource/resmgr/standards_products/siso-std-025-2023_cyberdem.pdf),
  SHA-256
  `e351e2c73ede003cea62c1ec0c22acb4430220b4d033c4de625645c6a8560e72`.
- [cyberdem-python commit `577543d53fa9ffb2b818a91e0ed61881c9bd7bfa`](https://github.com/cmu-sei/cyberdem-python/tree/577543d53fa9ffb2b818a91e0ed61881c9bd7bfa),
  especially `cyberdem/base/` and `cyberdem/enumerations/`.

The standard defines the solution-independent exchange boundary. The reference
implementation supplies object, relationship, event, effect, sensitivity, and
enumeration evidence without being treated as proof of independent adoption.

### Cyber FOM

- SISO, [SISO-STD-025.3-2024 Cyber Federation Object Model](https://www.sisostandards.org/page/StandardsProducts).

The exact standard identity is the evidence boundary. The SISO product catalog
states that the Cyber FOM is the HLA-specific implementation of the Cyber DEM.
No Cyber DEM reference-implementation behavior is silently credited to the
Cyber FOM row.

### CRACK

- Russo, Costa, and Armando, [*Building next generation Cyber Ranges with
  CRACK*, Computers & Security 95:101837](https://doi.org/10.1016/j.cose.2020.101837).
- [CRACK commit `1f22c729a379d09001f446d19e01a5561eed6ca9`](https://github.com/enricorusso/CRACK/tree/1f22c729a379d09001f446d19e01a5561eed6ca9),
  especially `types/sdl*.yaml`, runtime predicates, and OpenStack plugin types.

The paper supplies the design, Datalog verification, generation, and automated
runtime-test claims. The source supplies the TOSCA types and pinned deployment
boundary.

### VSDL

- Costa, Russo, and Armando, [*Automating the Generation of Cyber Range Virtual
  Scenarios with VSDL*, arXiv:2001.06681v1](https://arxiv.org/abs/2001.06681v1),
  SHA-256 of the v1 PDF
  `d8b505602afee6962c39f02d6691fc5ab7aba77acb3ea35760bb8211e85381b4`.

The paper is the fixed boundary for syntax, QFLIA/SMT semantics,
satisfiability, temporal guards, composition, and generated OpenStack,
Terraform, and Packer scripts. No maintained public source revision was added
to this snapshot, so implementation-maturity and negative-diagnostic claims
remain limited.

## ACES Freeze

ACES is pinned to pre-change `dev` commit
[`1b63b2a0b10dcd80e29b8bad14558ad9c6b706d0`](https://github.com/Brad-Edwards/aces/tree/1b63b2a0b10dcd80e29b8bad14558ad9c6b706d0).
The snapshot records per-file hashes for the cited authoring schema, production
parser, parser tests, participant semantics, experiment study contract,
scientific-completeness assessment, composition model, lineage ledger, backend
profile, author guide, and authority ADR.

ACES implementation claims require executable evidence where the axis concerns
shipped behavior. The scientific-completeness assessment remains the delivery
truth for partial, missing, external-contract, and deliberately-excluded
concerns. Accepted designs and formal prose do not upgrade implementation
maturity.

## Authoring Tasks And Negative Cases

The protocol freezes three representative tasks:

1. author a multi-host scenario with roles and an objective;
2. compose and version reusable authored material; and
3. declare a controlled participant experiment.

It also freezes two single-defect negative cases: a dangling reference and
contradictory constraints. The snapshot contains every system-case pair. ACES
uses existing repository execution where the cited production/tests already
exercise the boundary. External systems use source walkthroughs, which are
identified as such and do not become usability or execution claims.

## Analysis Freeze

Pareto dominance is computed only within a scope stratum and only over axes
applicable to every system in that group. Four scenario-authoring weight
profiles were fixed: equal evidence, breadth/composition, formal rigor, and
maturity/governance. Their first-ranked systems differ. The analysis therefore
records a sensitivity reversal and prohibits a weight-independent winner.

`Out of scope`, `not observed`, `not implemented`, and `not evaluated` remain
distinct. The checker never coerces `out of scope` to zero.

## Archival And Security Boundary

The repository stores metadata, digests, precise locators, and paraphrased
findings. It does not store unrestricted copies of standards, papers,
documentation, or source repositories. Normal checks perform no network fetch,
clone, package installation, shell evaluation, or third-party execution. Source
locators must use HTTPS and cannot contain URI userinfo or secret-bearing query
parameters.

Changing a rubric or corpus rule requires a new protocol revision. Refreshing a
source requires a new extraction snapshot. The current protocol amendment log
is empty.
