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

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#87` (Experiment core model: tasks, task/scenario separation, runs, apparatus context, studies (EXP-701…705))
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#87` (Experiment core model: tasks, task/scenario separation, runs, apparatus context, studies)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Experiment task contract model source)
- IMPLEMENTS → SPEC `contracts/schemas/experiment-core/experiment-task-v1.json` (Published experiment task schema)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Runtime contract schema and fixture tests)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#228` (Experiment Task Model (EXP-701))
