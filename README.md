# Reproducible Agentic Environments System

Reproducible Agentic Environments System (RAES) is a system for describing,
realizing, controlling, evaluating, and reproducing agentic environments. An
agentic environment is a declared and realized setting in which participants
receive observations, take actions, interact with resources or other
participants, and are evaluated under stated controls. Participants can
include software agents, policies, scripts, and human-control proxies.

RAES supports a bounded reproduction attempt by connecting authored intent,
deterministic or governed variation, realization inputs, participant behavior,
observations, apparatus identity, provenance, evidence, replay boundaries, and
conformance results. It does not guarantee deterministic runtime behavior,
equal outcomes, exact replay, scientific validity, or reproducibility.

Cyber, AI security, AI safety, testing, research, and evaluation are
non-exhaustive application areas. The general model can support additional
domains through domain-specific examples, controlled vocabularies, semantic
profiles, reusable assets, backend profiles, and evidence requirements.

The current repository materializes RAES through its Scenario Description
Language (SDL), Python reference implementation, published contracts, examples,
and assurance material. RAES names the overall system; RAES SDL is the authored
scenario language within it.

The repository separates authored scenario meaning from processors, backends,
participant implementations, runtime state, and archived evidence. In the
current implementation, an SDL document can be parsed, validated,
instantiated, compiled into runtime models, and checked against published
backend contracts without binding the authored scenario to one cloud, range
implementation, or execution harness.

This is an academic and engineering project. The repository is intended to be
read, tested, and used as reference implementation code, not treated as a
managed service.

The repository is not a managed environment service and does not include a
production backend. Backend contracts, stubs, conformance checks, and examples
are present; real deployment backends remain separate implementations. Cyber is
the strongest current example and lineage base, not the boundary of the core.

A worked example of RAES SDL driving a concrete range is
[APTL (Advanced Purple Team Lab)](https://github.com/Brad-Edwards/aptl), a
separate project that specifies its scenarios as RAES SDL documents and
realizes the selected topology on a Docker Compose backend.

## Contents

- [Agentic Environments And RAES SDL](#agentic-environments-and-raes-sdl)
- [Getting Started](#getting-started)
- [Using the Python Reference Implementation](#using-the-python-reference-implementation)
- [Repository Layout](#repository-layout)
- [Lineage](#lineage)
- [Documentation](#documentation)
- [Verification](#verification)
- [Contributing](#contributing)
- [Versioning](#versioning)
- [Citation](#citation)
- [License](#license)
- [Maintainer](#maintainer)

## Agentic Environments And RAES SDL

RAES SDL records authored scenario and experiment intent. An SDL file can
describe topology, hosts, services, identities, content, relationships, agents,
objectives, workflows, variables, and evaluation material without directly
describing a specific backend's infrastructure primitives. Processors,
backends, participant implementations, and runtime choices turn that authored
scenario into a realized environment; the realization is not identical to the
SDL document.

```yaml
name: hospital-ransomware-surgery-day
description: Surgery-day ransomware exercise for a regional hospital.

variables:
  surgery_day_speed:
    type: number
    default: 1.0

nodes:
  internet-edge:
    type: Switch
    description: Public ingress for email, VPN, and external access

  mail-gateway:
    type: VM
    os: linux
    source: secure-mail-gateway
    resources: {ram: 2 gib, cpu: 1}
    services:
      - {port: 25, name: smtp-inbound}
    roles: {mail-admin: postfix}
```

Complete examples live in [`examples/scenarios/`](https://github.com/RAESystem/rae/tree/main/examples/scenarios).
Reusable non-normative templates and patterns are indexed by
[`examples/library/catalog.yaml`](https://github.com/RAESystem/rae/blob/main/examples/library/catalog.yaml).

## Getting Started

Prerequisites:

- Python 3.11 or newer
- [uv](https://github.com/astral-sh/uv)
- [nox](https://nox.thea.codes/) for the repository verification graph, or
  `uvx nox` without a separate install

Set up the Python reference implementation:

```shell
git clone https://github.com/RAESystem/rae.git
cd rae/implementations/python
uv sync --all-extras
uv run raes --help
```

## Using the Python Reference Implementation

Parse and validate a scenario from Python:

```python
from pathlib import Path

from raes import parse_sdl_file

scenario = parse_sdl_file(
    Path("../../examples/scenarios/hospital-ransomware-surgery-day.sdl.yaml")
)

for advisory in scenario.advisories:
    print(advisory)
```

Run the CLI from `implementations/python`:

```shell
uv run raes sdl resolve ../../examples/scenarios/hospital-ransomware-surgery-day.sdl.yaml
uv run raes sdl verify-imports ../../examples/scenarios/hospital-ransomware-surgery-day.sdl.yaml
uv run raes sdl publish ../../examples/scenarios/hospital-ransomware-surgery-day.sdl.yaml
uv run raes processor --help
uv run raes conformance --help
uv run raes-mcp
```

## Repository Layout

- `specs/` - normative prose and formal specification material
- `contracts/` - published schemas, fixtures, manifests, and profiles
- `implementations/` - reference implementations and their local tooling
- `examples/` - worked SDL scenario examples plus reusable authoring templates and patterns
- `docs/` - explanatory documentation, API docs, and architecture decisions
- `research/` - supporting literature and reference ecosystem material
- `tools/` - repository maintenance, policy, and publication tooling

## Lineage

- [Open Cyber Range SDL](https://documentation.opencyberrange.ee/docs/sdl/reference/)
- [Open Cybersecurity Schema Framework](https://schema.ocsf.io/)
- [CACAO Security Playbooks v2.0](https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html)
- [STIX 2.1](https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html)
- [CybORG](https://github.com/cage-challenge/CybORG)
- [TENA](https://www.trmc.osd.mil/tena-about.html)
- [IEEE High Level Architecture](https://standards.ieee.org/standard/1516-2025.html)
- [SISO Cyber DEM](https://cdn.ymaws.com/www.sisostandards.org/resource/resmgr/standards_products/siso-std-025-2023_cyberdem.pdf)
- [SISO Cyber FOM](https://www.sisostandards.org/news/690125/Publication-of-Cyber-FOM-and-SIRL-Users-Guide.htm)
- [MITRE CALDERA](https://github.com/mitre/caldera)
- [Atomic Red Team](https://github.com/redcanaryco/atomic-red-team)

For a dimension-by-dimension comparison against these systems — what RAES
expresses that they do not, and where they still lead RAES — see
[Related-Work Comparison](https://github.com/RAESystem/rae/blob/main/docs/explain/sdl/related-work-comparison.md).

## Documentation

The documentation source is under [`docs/`](https://github.com/RAESystem/rae/tree/main/docs). Important entry points:

- [`docs/index.md`](https://github.com/RAESystem/rae/blob/main/docs/index.md) - documentation index
- [`docs/explain/getting-started.md`](https://github.com/RAESystem/rae/blob/main/docs/explain/getting-started.md) - use-case and rigor-level entrypoint
- [`docs/migration/raes-rename.md`](https://github.com/RAESystem/rae/blob/main/docs/migration/raes-rename.md) - RAES rename hard-cutover map
- [`examples/README.md`](https://github.com/RAESystem/rae/blob/main/examples/README.md) - current worked example inventory
- [`examples/library/catalog.yaml`](https://github.com/RAESystem/rae/blob/main/examples/library/catalog.yaml) - template and pattern library catalog
- [`docs/explain/reference/canonical-reference-map.md`](https://github.com/RAESystem/rae/blob/main/docs/explain/reference/canonical-reference-map.md) - current reference map
- [`docs/explain/reference/documentation-style-guide.md`](https://github.com/RAESystem/rae/blob/main/docs/explain/reference/documentation-style-guide.md) - documentation style and citation rules
- [`docs/explain/reference/glossary.md`](https://github.com/RAESystem/rae/blob/main/docs/explain/reference/glossary.md) - current terminology
- [`docs/explain/sdl/index.md`](https://github.com/RAESystem/rae/blob/main/docs/explain/sdl/index.md) - SDL guide
- [`docs/explain/sdl/runtime-architecture.md`](https://github.com/RAESystem/rae/blob/main/docs/explain/sdl/runtime-architecture.md) - runtime architecture
- [`docs/explain/reference/backend-conformance.md`](https://github.com/RAESystem/rae/blob/main/docs/explain/reference/backend-conformance.md) - backend conformance model
- [`docs/decisions/adrs/README.md`](https://github.com/RAESystem/rae/blob/main/docs/decisions/adrs/README.md) - architecture decisions
- [`contracts/README.md`](https://github.com/RAESystem/rae/blob/main/contracts/README.md) - contract publication surface

## Verification

`nox` is the canonical verification graph. From the repository root:

```shell
uvx nox -s verify
uvx nox -s verify-changed
uvx nox -s tests
uvx nox -l
```

The full `verify` session is unconditional and runs the project checks expected
for pull requests, including repository policy, governed evidence and generated
artifacts, parallel worker-safe test coverage, serial integration tests, and
docs. Use `verify-changed` while iterating: it compares the branch and working
tree with the upstream ref, skips evidence and regression stages only for
allowlisted prose or research-only changes, and fails closed to the full local
gate for unknown, deleted, renamed, executable, contract, or configuration
changes. The pre-push hook uses the same change-aware plan.

Whole-scenario finite-domain satisfiability can be inspected without applying
or provisioning a scenario:

```shell
uv run --project implementations/python raes processor satisfiability \
  path/to/scenario.sdl.yaml \
  --profile raes-finite-domain-satisfiability-v1
```

The command emits the published replayable evidence envelope. Exit `0` is a
completed satisfiable or unsatisfiable analysis, `2` is an explicit unsupported
fragment result, and `1` is an input or operational failure. See ADR-086 for the
bounded target coverage and nonclaims.

## Contributing

Contributions are welcome where they improve the language, reference
implementation, contracts, tests, examples, or documentation. Start with
[CONTRIBUTING.md](https://github.com/RAESystem/rae/blob/main/CONTRIBUTING.md).

Language and contract changes should be discussed before implementation because
small SDL changes can affect validation, generated schemas, backend
conformance, and existing scenario examples.

## Versioning

The Python package version lives in
[`implementations/python/packages/raes/_version.py`](https://github.com/RAESystem/rae/blob/main/implementations/python/packages/raes/_version.py)
and is bumped by [release-please](https://github.com/googleapis/release-please)
from the Conventional Commit history on `main`, which also generates
`CHANGELOG.md`. Do not hand-edit the version or `CHANGELOG.md`. See
[`docs/explain/releasing.md`](https://github.com/RAESystem/rae/blob/main/docs/explain/releasing.md).

Published JSON Schemas use versioned contract identifiers such as
`sdl-authoring-input-v1`, but the suffix is not the same as a stability promise.
The authoritative schema publication index assembles independent per-contract
records, each carrying its schema's `draft` or `stable` stability class and
canonical content hash. Current checked-in schemas
are draft until a maintainer explicitly promotes them; stable breaking changes
must mint a new schema version as described in
[ADR-061](https://github.com/RAESystem/rae/blob/main/docs/decisions/adrs/adr-061-published-schema-evolution-policy.md).

## Maintainers

- Brad Edwards — [Personal GitHub](https://github.com/Brad-Edwards), [PANW GitHub](https://github.com/Brad-Edwards-SecOps), [LinkedIn](https://www.linkedin.com/in/bradley-edwards-dev/)

## Citation

If you use RAES in academic work, cite the system:

```bibtex
@software{raes,
  author       = {Edwards, Brad},
  title        = {RAES: Reproducible Agentic Environments System},
  year         = {2026},
  license      = {MIT},
  url          = {https://github.com/RAESystem/rae}
}
```

## License

Released under the MIT License. See [LICENSE](https://github.com/RAESystem/rae/blob/main/LICENSE).
Third-party attribution and license notices are recorded in
[THIRD_PARTY_NOTICES.md](https://github.com/RAESystem/rae/blob/main/THIRD_PARTY_NOTICES.md).
