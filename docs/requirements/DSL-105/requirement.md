---
id: DSL-105
title: "Typed Parsing, Normalization, And Authoritative SDL Format"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:55:57.534488Z
updated_at: 2026-04-05T00:58:02.608558Z
---

# DSL-105 — Typed Parsing, Normalization, And Authoritative SDL Format

## Statement

The language shall define one authoritative SDL source format with typed parsing, structural normalization, shorthand expansion, and clean rejection of incompatible dialects.

## Rationale

Requirement inventory phase. Status audit deferred until the full canonical graph is complete.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/parser.md` (SDL parser behavior: normalization, shorthands, and SDL-only format boundary)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/testing.md` (SDL testing strategy covering parser normalization and format boundary)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/index.md` (SDL overview linking parser behavior and authoritative usage)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-001-scenario-description-language.md` (ADR-001: SDL-only parsing and format boundary)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-009-normative-artifact-authority-and-repository-structure.md` (ADR-009: authoritative artifact authority)
- CONSTRAINS → SPEC `contracts/schemas/README.md` (Authoritative machine-readable schema artifacts)
- CONSTRAINS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (Versioned authoritative SDL authoring schema)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/parser.py` (SDL parser implementation for normalization and shorthand expansion)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_base.py` (SDL base model configuration for typed structural validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/scenario.py` (Typed Scenario model construction target)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (Parser tests for normalization, shorthands, and SDL-only format rejection)
- TESTS → TEST `implementations/python/tests/test_sdl_fuzz.py` (Fuzz tests for clean parser rejection behavior)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (Runtime network sensor semantic validation)
- IMPLEMENTS → GITHUB_ISSUE `429` (SDL cannot express scenario-native network-sensor (NSM/IDS) monitoring posture)
- IMPLEMENTS → PULL_REQUEST `435` (added: runtime network sensor posture)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_network_sensor.py` (Runtime network sensor SDL model)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_configuration.py` (Runtime configuration network_sensors field)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_module_runtime_aliases.py` (Runtime subobject module alias helpers)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema network_sensors contract)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated scenario schema network_sensors contract)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-042-network-sensor-runtime-monitoring.md` (ADR-042 Network Sensor Runtime Monitoring)
- TESTS → TEST `implementations/python/tests/test_runtime_network_sensor.py` (Runtime network sensor SDL tests)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (SDL validation documentation for runtime network sensors)
- IMPLEMENTS → GITHUB_ISSUE `720` (Reject duplicate YAML keys and normalized-key collisions before SDL construction)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_yaml_loader.py` (Authoritative source-marked SDL YAML composition and ambiguity rejection)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_errors.py` (Structured source-ranged SDL parse diagnostics)
- TESTS → TEST `implementations/python/tests/test_yaml_mapping_keys.py` (Mapping-key injectivity and ambiguity rejection tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_mapping_scopes.py` (Structural and literal SDL mapping-key scope classification)
- DOCUMENTS → SPEC `specs/sdl/document-model.md` (Normative SDL mapping identity and construction semantics)
- TESTS → TEST `implementations/python/tests/test_mcp_server.py` (MCP authoring-boundary diagnostic propagation tests)
- IMPLEMENTS → PULL_REQUEST `731` (Reject ambiguous SDL mapping keys)
- DOCUMENTS → SPEC `specs/sdl/diagnostics.md` (Normative SDL parse diagnostic contract)
