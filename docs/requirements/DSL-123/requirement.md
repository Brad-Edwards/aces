---
id: DSL-123
title: "Scenario-Native Observability And Telemetry Systems"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T01:59:50.100713Z
updated_at: 2026-06-24T04:36:42.538398Z
---

# DSL-123 — Scenario-Native Observability And Telemetry Systems

## Statement

The language shall support scenario-native observability, telemetry, logging, tracing, monitoring, and comparable in-world data systems as first-class scenario elements that may be depended on, interacted with, or targeted.

## Rationale

This closes the gap between observability as part of the modeled world and observability as an external experiment concern. Some scenarios need observability systems to exist inside the environment as assets in their own right.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#127` (Observability plane separation & realization-augmentation semantics; scenario-native observability & authored evidence-requirement surfaces (SEM-224, 225, DSL-123, 124))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#336` (Scenario-Native Observability And Telemetry Systems (DSL-123))
- DOCUMENTS → ADR `docs/decisions/adrs/adr-066-observability-evidence-plane-separation.md` (ADR-066 Observability evidence plane separation)
- DOCUMENTS → SPEC `specs/formal/observability-evidence-plane.md` (Formal observability/evidence plane specification)
- DOCUMENTS → DOCUMENTATION `specs/sdl/observability-and-evidence.md` (SDL observability and evidence authoring catalog)
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#127` (Issue #127 observability and evidence semantics)
- IMPLEMENTS → SPEC `specs/formal/observability-evidence-plane.md` (Formal DSL-123 observability implementation coverage mapping)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/observability_plane_semantics.py` (Scenario-native observability runtime reference collector)
- TESTS → TEST `implementations/python/tests/test_dsl_123_scenario_native_observability.py` (DSL-123 scenario-native observability semantic validation tests)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#336` (Issue #336 scenario-native observability implementation)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#589` (PR #589 scenario-native observability coverage)
