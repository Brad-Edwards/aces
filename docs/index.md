# RAES SDL Documentation

**A backend-agnostic cyber range scenario description language and reference
implementation.**

`raes-sdl` provides the RAES Python implementation for describing cyber
range scenarios and experiments, validating their authored meaning, compiling
runtime models, and checking published backend contracts.

The repository is not a managed cyber range and does not ship production
backend implementations. It is a working codebase for testing language,
semantic, runtime, and assurance claims against source code, schemas, examples,
and tests.

## Quick Start

```python
from aces_sdl import parse_sdl, parse_sdl_file

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

aces/inventory/index
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
