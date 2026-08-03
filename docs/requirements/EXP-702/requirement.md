---
id: EXP-702
title: "Task And Scenario Separation"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T06:39:27.983815Z
updated_at: 2026-05-26T06:32:50.036856Z
---

# EXP-702 — Task And Scenario Separation

## Statement

The ecosystem shall distinguish scenario specifications from experiment tasks so that one scenario may participate in multiple tasks, protocols, or studies without semantic ambiguity.

## Rationale

Requirement inventory expansion. Scenario definitions and experiment tasks are related but not interchangeable concepts.

## Traceability

- IMPLEMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL objectives clarified as scenario-local, not experiment tasks)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Runtime contract schema and fixture tests)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-055-experiment-core-contract-boundary.md` (Experiment core contract boundary ADR)
