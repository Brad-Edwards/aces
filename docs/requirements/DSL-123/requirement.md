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

- DOCUMENTS → ADR `docs/decisions/adrs/adr-066-observability-evidence-plane-separation.md` (ADR-066 Observability evidence plane separation)
- DOCUMENTS → SPEC `specs/formal/observability-evidence-plane.md` (Formal observability/evidence plane specification)
- DOCUMENTS → DOCUMENTATION `specs/sdl/observability-and-evidence.md` (SDL observability and evidence authoring catalog)
- IMPLEMENTS → SPEC `specs/formal/observability-evidence-plane.md` (Formal DSL-123 observability implementation coverage mapping)
- TESTS → TEST `implementations/python/tests/test_dsl_123_scenario_native_observability.py` (DSL-123 scenario-native observability semantic validation tests)
