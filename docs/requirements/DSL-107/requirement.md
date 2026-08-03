---
id: DSL-107
title: "Topology And Infrastructure Modeling"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:55:57.796782Z
updated_at: 2026-04-05T00:59:55.177473Z
---

# DSL-107 — Topology And Infrastructure Modeling

## Statement

The language shall model nodes, infrastructure, connectivity, scaling, per-link addressing, services, and access-control constructs.

## Rationale

Requirement inventory phase. Status audit deferred until the full canonical graph is complete.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL sections reference for nodes, infrastructure, services, and ACLs)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-001-scenario-description-language.md` (ADR-001: topology and infrastructure are core SDL surface)
- CONSTRAINS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema for node and infrastructure modeling)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/nodes.py` (Node, resource, service, and asset-value models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/infrastructure.py` (Infrastructure, per-link addressing, and ACL models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/parser.py` (Infrastructure count shorthand and SDL topology parsing)
- TESTS → TEST `implementations/python/tests/test_sdl_models.py` (Model tests for nodes, services, infrastructure, and ACLs)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (Validator tests for links, scaling, per-link IPs, and ACL references)
- TESTS → TEST `implementations/python/tests/test_sdl_stress.py` (Stress scenarios exercising infrastructure and ACL-rich topologies)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (Topology and infrastructure validation rules)
- DOCUMENTS → GITHUB_ISSUE `368` (Issue #368 container host config, namespace security, and mount facts)
- IMPLEMENTS → PULL_REQUEST `369` (PR #369 feat(sdl): add runtime inventory surfaces)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_container.py` (Container runtime host, namespace, security, mount-adjacent, and health models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_configuration.py` (Node runtime aggregation model for mounts and container inventory facts)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (Parser tests for runtime mount and container host/security fields)
- VERIFIES → SPEC `examples/scenarios/techvault.sdl.yaml` (TechVault scenario example exercising container host config and mount runtime facts)
- IMPLEMENTS → GITHUB_ISSUE `395` (Scenario-node software state cannot be normatively declared at granularities finer than runtime.packages)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_software.py` (Runtime software component inventory model)
- TESTS → TEST `implementations/python/tests/test_runtime_models.py` (Runtime compiler preservation tests for node software components)
- CONSTRAINS → POLICY `tools/policy/requirement_order.yaml` (Requirement-order mapping for DSL language-surface work)
- IMPLEMENTS → PULL_REQUEST `408` (PR #408 feat(sdl): add runtime software component inventory)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-034-runtime-software-component-inventory.md` (ADR-034 runtime software component inventory)
- IMPLEMENTS → GITHUB_ISSUE `420` (SDL gap: typed mail service runtime inventory under Node.runtime)
- IMPLEMENTS → PULL_REQUEST `425` (Add runtime mail service SDL surface)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_mail_service.py` (Runtime mail service SDL models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_mail_vocab.py` (Runtime mail service vocabulary)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_runtime_mail_semantics.py` (Runtime mail semantic validation helpers)
- TESTS → TEST `implementations/python/tests/test_runtime_mail_service.py` (Runtime mail service model and semantic tests)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-038-runtime-mail-service-logical-state.md` (ADR-038 Runtime Mail-Service Logical State)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema with runtime mail services)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated SDL schema with runtime mail services)
