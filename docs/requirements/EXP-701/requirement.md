---
id: EXP-701
title: "Experiment Task Model"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T06:39:27.862269Z
updated_at: 2026-05-26T06:32:47.062414Z
---

# EXP-701 — Experiment Task Model

## Statement

The ecosystem shall support first-class experiment tasks that bind a scenario or environment definition to an evaluation protocol and experiment intent.

## Rationale

Requirement inventory expansion. Experiment tasks need to be distinct objects so evaluation intent and protocol are not collapsed into scenario specification alone.

## Traceability

- IMPLEMENTS → SPEC `contracts/schemas/experiment-core/experiment-task-v1.json` (Published experiment task schema)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Runtime contract schema and fixture tests)
