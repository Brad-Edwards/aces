# Reproducible Agentic Environments System

Reproducible Agentic Environments System (RAES) describes, realizes, controls,
evaluates, and supports bounded reproduction of agentic environments. An
agentic environment is a declared and realized setting in which participants
receive observations, take actions, interact with resources or other
participants, and are evaluated under stated controls.

Cyber, AI security, AI safety, testing, research, and evaluation are
non-exhaustive application areas. Additional domains can use the same
authored-intent, realization, participant, observation, evidence, provenance,
and conformance boundaries through their own profiles, assets, examples, and
backends.

The current `raes` distribution provides RAES SDL, a Python reference
implementation, published contracts, examples, and assurance material. RAES
names the overall system; RAES SDL is the authored scenario language. The
reference implementation can validate authored meaning, instantiate and
compile runtime models, plan against backend manifests, and check published
backend contracts.

The repository is not a managed environment service and does not ship
production backend implementations. It is a working codebase for evaluating
language, semantic, runtime, and assurance claims against source code, schemas,
examples, and tests. Its reproducibility surfaces support a bounded
reproduction attempt; they do not guarantee deterministic runtime behavior,
equal outcomes, exact replay, or reproducibility.

## Quick Start

```python
from raes import parse_sdl, parse_sdl_file

# Parse from a string
scenario = parse_sdl(yaml_string)

# Parse from a file
scenario = parse_sdl_file(Path("scenarios/my-scenario.yaml"))

# Skip semantic validation (structural only)
scenario = parse_sdl(yaml_string, skip_semantic_validation=True)

# Non-fatal authoring advisories
for advisory in scenario.advisories:
    print(advisory)
```

## What's Included

- **Author-facing SDL** models and parsing for 21 scenario sections
- **Semantic validation** and formal semantic artifacts
- **Processor layer** with compiler, planner, and control-plane contracts
- **Schemas** and backend conformance fixtures
- **CLI commands**, docs, examples, reusable authoring templates, patterns, and tests

## Reader Map

- New users can start with the getting-started guide to choose the smallest
  current entrypoint for their task and rigor level.
- Agentic-environment users can start with the glossary and reference map to
  distinguish authored scenarios, realized environments, apparatus, evidence,
  and conformance.
- Scenario authors usually start with the SDL guide, sections reference,
  parser behavior, validation rules, and limitations.
- Backend implementers usually start with runtime architecture, contract
  schemas, backend conformance, and the canonical reference map.
- Researchers usually start with lineage, design precedents, formal
  specifications, glossary, and limitations.
- Contributors should read the documentation style guide before changing prose.

```{toctree}
:maxdepth: 2
:caption: Getting Started

explain/getting-started
```

```{toctree}
:maxdepth: 2
:caption: Maintainer Guide

explain/releasing
```

```{toctree}
:maxdepth: 2
:caption: SDL Guide

explain/sdl/index
explain/sdl/sections
explain/sdl/parser
explain/sdl/variation-points
explain/sdl/language-service
explain/sdl/agent-guidance
explain/sdl/validation
explain/sdl/precedents
explain/sdl/lineage
explain/sdl/related-work-comparison
explain/sdl/scientific-scenario-completeness
explain/sdl/scenario-delivery-drift-audit
explain/sdl/complex-scenarios
explain/sdl/limitations
explain/sdl/testing
```

```{toctree}
:maxdepth: 2
:caption: Runtime

explain/sdl/runtime-architecture
```

```{toctree}
:maxdepth: 2
:caption: Asset Inventory

raes/inventory/index
```

```{toctree}
:maxdepth: 2
:caption: Architecture Decisions

decisions/index
```

```{toctree}
:maxdepth: 2
:caption: Reference

explain/reference/README
explain/reference/coding-standards
explain/reference/canonical-reference-map
explain/reference/documentation-style-guide
explain/reference/glossary
explain/reference/shared-concept-model
explain/reference/shared-semantic-integrity
explain/reference/backend-conformance
explain/reference/reference-emulation-backend
explain/reference/normative-artifact-authority
explain/reference/assessment-semantics
explain/reference/objective-semantics
explain/reference/explicitness-realization-semantics
explain/reference/realization-envelopes
explain/reference/scenario-variation-and-trial-realization
explain/reference/experiment-binding-contracts
explain/reference/participant-decision-surface-v2-migration
```

```{toctree}
:maxdepth: 2
:caption: Formal Specifications

specs/formal
```

```{toctree}
:maxdepth: 2
:caption: Project Notes

lessons/README
migration/README
migration/raes-rename
research/experiment-core/index
research/realization-envelope/index
research/scenario-variation-trial-realization/index
research/scoring-scope/index
research/validation-admission-profiles/index
research/primary/index
research/lineage/source-audit-2026-07-12
research/behavioral-relations/conflation-audit-2026-07-13
research/related-work-comparison/index
research/dsl-language-evaluation/index
research/specification-coverage/index
research/formal-semantic-validation/index
research/participant-backend-contracts/index
research/participant-io-control/index
research/participant-interactive-access/index
research/time-model/prior-art-and-design-criteria
research/initial-service-state-precedents-2026-07-24
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/sdl
api/sdl-semantics
api/processor
api/processor-semantics
api/contracts
api/runtime
api/cli
```
