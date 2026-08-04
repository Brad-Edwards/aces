---
id: DSL-131
title: "Network Detection Engine Runtime Inventory"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-05-29T06:19:51.738736Z
updated_at: 2026-05-29T06:38:03.965683Z
---

# DSL-131 — Network Detection Engine Runtime Inventory

## Statement

The language shall represent network IDS/NDR detection-engine runtime state as typed node-scoped runtime inventory, including engine identity, app-layer parser enablement, rule-source inventories, network zoning/address-set variables, alert or telemetry output streams, reload/control channels, and evidence references, without overloading network-sensor monitoring posture, SIEM/security-monitoring manager inventory, transport services, processes, filesystem evidence, raw rule contents, alert telemetry, or prose-only relationships.

## Rationale

Issue #430 identifies a downstream inventory blocker from APTL TechVault Suricata capture: RAES can represent the surrounding sensor posture, package/process/filesystem/control-socket evidence, and SIEM manager inventory, but lacks a typed, queryable surface for the detection engine's observable parser, rule-source, zoning, output, and reload semantics.

## Traceability

- IMPLEMENTS → GITHUB_ISSUE `430` (SDL has no typed IDS/NDR detection-engine runtime service family)
- TESTS → TEST `implementations/python/tests/test_runtime_network_detection.py` (Runtime network detection-engine tests)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL sections documentation for network detection engines)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (SDL validation documentation for network detection engines)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/lineage.md` (SDL lineage documentation for network detection engines)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/precedents.md` (SDL precedent index entry for network detection engines)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/limitations.md` (SDL limitations documentation for network detection engines)
- VERIFIES → CONFIG `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema for network detection engines)
- VERIFIES → CONFIG `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated scenario schema for network detection engines)
- DOCUMENTS → DOCUMENTATION `changelog.d/430.added.md` (Changelog fragment for issue 430)
- IMPLEMENTS → PULL_REQUEST `437` (Add network detection-engine runtime inventory)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-044-network-detection-engine-runtime-inventory.md` (ADR-044 Network Detection Engine Runtime Inventory)
