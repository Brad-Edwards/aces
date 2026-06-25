# ACES SDL Documentation

**A backend-agnostic cyber range scenario description language and reference
implementation.**

`aces-sdl` currently provides a Python implementation for describing cyber
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
explain/sdl/language-service
explain/sdl/agent-guidance
explain/sdl/validation
explain/sdl/precedents
explain/sdl/lineage
explain/sdl/related-work-comparison
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

decisions/adrs/README
decisions/adrs/adr-000-use-adrs
decisions/adrs/adr-001-scenario-description-language
decisions/adrs/adr-002-declarative-sdl-objectives
decisions/adrs/adr-003-workflows-targetable-subobjects-and-enum-variables
decisions/adrs/adr-004-sdl-runtime-layer
decisions/adrs/adr-005-control-flow-primitives
decisions/adrs/adr-006-workflow-control-language-redesign
decisions/adrs/adr-007-lightweight-formal-methods-policy
decisions/adrs/adr-008-processor-layer-and-execution-artifact-boundaries
decisions/adrs/adr-009-normative-artifact-authority-and-repository-structure
decisions/adrs/adr-010-repository-realignment-order-and-compatibility-policy
decisions/adrs/adr-011-narrow-end-to-end-mvp-validation
decisions/adrs/adr-012-shared-concept-authority-and-aces-extension-discipline
decisions/adrs/adr-013-participant-episode-lifecycle-boundaries
decisions/adrs/adr-014-nox-as-canonical-verification-graph
decisions/adrs/adr-015-sdl-processor-layering-and-source-file-size-cap
decisions/adrs/adr-016-semantic-layer-scope-and-coverage-model
decisions/adrs/adr-017-conversation-surface-hardening
decisions/adrs/adr-018-classification-based-assurance-policy
decisions/adrs/adr-019-normative-authority-boundary-manifest
decisions/adrs/adr-020-declarative-participant-framing-boundaries
decisions/adrs/adr-021-falsification-first-claim-evidence-gate
decisions/adrs/adr-022-participant-behavior-and-interaction-semantics
decisions/adrs/adr-023-container-image-build-provenance-surface
decisions/adrs/adr-024-local-identity-inventory-surface
decisions/adrs/adr-025-container-network-realization-surface
decisions/adrs/adr-026-application-http-surface-inventory
decisions/adrs/adr-027-container-init-reaper-runtime-surface
decisions/adrs/adr-028-container-seccomp-security-options-surface
decisions/adrs/adr-029-database-logical-state-runtime-surface
decisions/adrs/adr-030-process-scoped-linux-capability-policy
decisions/adrs/adr-031-ssh-server-configuration-surface
decisions/adrs/adr-032-directory-domain-identity-runtime-surface
decisions/adrs/adr-033-scenario-delivery-boundary-for-runtime-node-state
decisions/adrs/adr-034-runtime-software-component-inventory
decisions/adrs/adr-035-service-manager-unit-state-runtime-surface
decisions/adrs/adr-036-sdl-processor-runtime-module-boundaries
decisions/adrs/adr-037-runtime-file-service-and-filesystem-presence-semantics
decisions/adrs/adr-038-runtime-mail-service-logical-state
decisions/adrs/adr-039-dns-service-runtime-inventory
decisions/adrs/adr-040-security-monitoring-manager-runtime-inventory
decisions/adrs/adr-041-participant-implementation-manifest-and-provenance
decisions/adrs/adr-042-network-sensor-runtime-monitoring
decisions/adrs/adr-043-runtime-service-listener-surface
decisions/adrs/adr-044-network-detection-engine-runtime-inventory
decisions/adrs/adr-045-security-monitoring-detection-definition-semantics
decisions/adrs/adr-046-app-authorization-runtime-inventory
decisions/adrs/adr-047-scheduled-job-runtime-inventory
decisions/adrs/adr-048-datastore-service-runtime-inventory
decisions/adrs/adr-049-platform-application-runtime-inventory
decisions/adrs/adr-050-forwarding-agent-runtime-inventory
decisions/adrs/adr-051-orchestration-authority-runtime-inventory
decisions/adrs/adr-052-typed-runtime-relationship-subtypes
decisions/adrs/adr-053-sdl-module-composition-for-inventory-backed-scenarios
decisions/adrs/adr-054-participant-runtime-observable-lifecycle
decisions/adrs/adr-055-experiment-core-contract-boundary
decisions/adrs/adr-056-runtime-observed-values-and-credential-posture
decisions/adrs/adr-057-runtime-secret-name-classifier-boundaries
decisions/adrs/adr-058-datastore-node-engine-provenance-and-endpoints
decisions/adrs/adr-059-adr-amendment-policy-and-pin-gate
decisions/adrs/adr-060-participant-backend-facing-contract-surface
decisions/adrs/adr-061-published-schema-evolution-policy
decisions/adrs/adr-062-concept-authority-catalog-governance-gate
decisions/adrs/adr-063-reference-emulation-backend
decisions/adrs/adr-064-experiment-evidence-and-measure-contract-boundary
decisions/adrs/adr-065-experiment-run-provenance-contract-boundary
decisions/issue-248-sem-216-boundary-semantics-preflight
decisions/sem-213-temporal-participant-preflight
decisions/issue-508-related-work-comparison-preflight
decisions/issue-42-validator-package-split-preflight
decisions/issue-567-pr-title-guard-preflight
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
research/experiment-core/index
research/primary/index
research/related-work-comparison/index
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
