# Agentic Cyber Environment System

Agentic Cyber Environment System (ACES) is a backend-agnostic scenario
description language, Python reference implementation, and contract surface
for cyber range scenarios and experiments.

The repository separates authored scenario meaning from processors, backends,
participant implementations, runtime state, and archived evidence. In the
current implementation, an SDL document can be parsed, validated,
instantiated, compiled into runtime models, and checked against published
backend contracts without binding the authored scenario to one cloud, range
implementation, or execution harness.

This is an academic and engineering project. The repository is intended to be
read, tested, and used as reference implementation code, not treated as a product
surface.

The repository is not a managed cyber range and does not include a production
backend. Backend contracts, stubs, conformance checks, and examples are present;
real deployment backends remain separate implementations.

A worked example of ACES SDL driving a concrete range is
[APTL (Advanced Purple Team Lab)](https://github.com/Brad-Edwards/aptl), a
separate project that specifies its scenarios as ACES SDL documents and
realizes the selected topology on a Docker Compose backend.

## Contents

- [What ACES SDL Describes](#what-aces-sdl-describes)
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

## What ACES SDL Describes

An SDL file is a declarative scenario document. It can describe topology,
hosts, services, identities, content, relationships, agents, objectives,
workflows, variables, and evaluation material without directly describing a
specific backend's infrastructure primitives.

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

Complete examples live in [`examples/scenarios/`](https://github.com/Brad-Edwards/aces/tree/main/examples/scenarios).
Reusable non-normative templates and patterns are indexed by
[`examples/library/catalog.yaml`](https://github.com/Brad-Edwards/aces/blob/main/examples/library/catalog.yaml).

## Getting Started

Prerequisites:

- Python 3.11 or newer
- [uv](https://github.com/astral-sh/uv)
- [nox](https://nox.thea.codes/) for the repository verification graph, or
  `uvx nox` without a separate install

Set up the Python reference implementation:

```shell
git clone https://github.com/Brad-Edwards/aces.git
cd aces/implementations/python
uv sync --all-extras
uv run aces --help
```

## Using the Python Reference Implementation

Parse and validate a scenario from Python:

```python
from pathlib import Path

from aces_sdl import parse_sdl_file

scenario = parse_sdl_file(
    Path("../../examples/scenarios/hospital-ransomware-surgery-day.sdl.yaml")
)

for advisory in scenario.advisories:
    print(advisory)
```

Run the CLI from `implementations/python`:

```shell
uv run aces sdl resolve ../../examples/scenarios/hospital-ransomware-surgery-day.sdl.yaml
uv run aces sdl verify-imports ../../examples/scenarios/hospital-ransomware-surgery-day.sdl.yaml
uv run aces sdl publish ../../examples/scenarios/hospital-ransomware-surgery-day.sdl.yaml
uv run aces processor --help
uv run aces conformance --help
uv run aces-mcp
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

For a dimension-by-dimension comparison against these systems — what ACES
expresses that they do not, and where they still lead ACES — see
[Related-Work Comparison](https://github.com/Brad-Edwards/aces/blob/main/docs/explain/sdl/related-work-comparison.md).

## Documentation

The documentation source is under [`docs/`](https://github.com/Brad-Edwards/aces/tree/main/docs). Important entry points:

- [`docs/index.md`](https://github.com/Brad-Edwards/aces/blob/main/docs/index.md) - documentation index
- [`docs/explain/getting-started.md`](https://github.com/Brad-Edwards/aces/blob/main/docs/explain/getting-started.md) - use-case and rigor-level entrypoint
- [`examples/README.md`](https://github.com/Brad-Edwards/aces/blob/main/examples/README.md) - current worked example inventory
- [`examples/library/catalog.yaml`](https://github.com/Brad-Edwards/aces/blob/main/examples/library/catalog.yaml) - template and pattern library catalog
- [`docs/explain/reference/canonical-reference-map.md`](https://github.com/Brad-Edwards/aces/blob/main/docs/explain/reference/canonical-reference-map.md) - current reference map
- [`docs/explain/reference/documentation-style-guide.md`](https://github.com/Brad-Edwards/aces/blob/main/docs/explain/reference/documentation-style-guide.md) - documentation style and citation rules
- [`docs/explain/reference/glossary.md`](https://github.com/Brad-Edwards/aces/blob/main/docs/explain/reference/glossary.md) - current terminology
- [`docs/explain/sdl/index.md`](https://github.com/Brad-Edwards/aces/blob/main/docs/explain/sdl/index.md) - SDL guide
- [`docs/explain/sdl/runtime-architecture.md`](https://github.com/Brad-Edwards/aces/blob/main/docs/explain/sdl/runtime-architecture.md) - runtime architecture
- [`docs/explain/reference/backend-conformance.md`](https://github.com/Brad-Edwards/aces/blob/main/docs/explain/reference/backend-conformance.md) - backend conformance model
- [`docs/decisions/adrs/README.md`](https://github.com/Brad-Edwards/aces/blob/main/docs/decisions/adrs/README.md) - architecture decisions
- [`contracts/README.md`](https://github.com/Brad-Edwards/aces/blob/main/contracts/README.md) - contract publication surface

## Verification

`nox` is the canonical verification graph. From the repository root:

```shell
uvx nox -s verify
uvx nox -s tests
uvx nox -l
```

The full `verify` session runs the project checks expected for pull requests,
including repository policy, generated artifact checks, tests, and docs.

## Contributing

Contributions are welcome where they improve the language, reference
implementation, contracts, tests, examples, or documentation. Start with
[CONTRIBUTING.md](https://github.com/Brad-Edwards/aces/blob/main/CONTRIBUTING.md).

Language and contract changes should be discussed before implementation because
small SDL changes can affect validation, generated schemas, backend
conformance, and existing scenario examples.

## Versioning

The Python package version lives in
[`implementations/python/pyproject.toml`](https://github.com/Brad-Edwards/aces/blob/main/implementations/python/pyproject.toml)
and is bumped by [release-please](https://github.com/googleapis/release-please)
from the Conventional Commit history on `main`, which also generates
`CHANGELOG.md`. Do not hand-edit the version or `CHANGELOG.md`. See
[`docs/explain/releasing.md`](https://github.com/Brad-Edwards/aces/blob/main/docs/explain/releasing.md).

Published JSON Schemas use versioned contract identifiers such as
`sdl-authoring-input-v1`, but the suffix is not the same as a stability promise.
The authoritative schema publication manifest records each schema's `draft` or
`stable` stability class and canonical content hash. Current checked-in schemas
are draft until a maintainer explicitly promotes them; stable breaking changes
must mint a new schema version as described in
[ADR-061](https://github.com/Brad-Edwards/aces/blob/main/docs/decisions/adrs/adr-061-published-schema-evolution-policy.md).

## Maintainers

- Brad Edwards — [Personal GitHub](https://github.com/Brad-Edwards), [PANW GitHub](https://github.com/Brad-Edwards-SecOps), [LinkedIn](https://www.linkedin.com/in/bradley-edwards-dev/)

## Citation

If you use ACES SDL in academic work, cite the repository:

```bibtex
@software{aces_sdl,
  author       = {Edwards, Brad},
  title        = {ACES SDL: Backend-Agnostic Scenario Description Language for Cyber Range Experiments},
  year         = {2026},
  license      = {MIT},
  url          = {https://github.com/Brad-Edwards/aces}
}
```

## License

Released under the MIT License. See [LICENSE](https://github.com/Brad-Edwards/aces/blob/main/LICENSE).
Third-party attribution and license notices are recorded in
[THIRD_PARTY_NOTICES.md](https://github.com/Brad-Edwards/aces/blob/main/THIRD_PARTY_NOTICES.md).
