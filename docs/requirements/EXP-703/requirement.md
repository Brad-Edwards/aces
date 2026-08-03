---
id: EXP-703
title: "Experiment Run Model"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T06:39:28.084775Z
updated_at: 2026-05-26T06:32:53.076762Z
---

# EXP-703 — Experiment Run Model

## Statement

The ecosystem shall support first-class archival run records representing specific executions of a declared task, distinct from live control-plane state and mutable execution lifecycle observation.

## Rationale

Requirement inventory expansion. Runs need to be modeled explicitly as archival execution records rather than inferred from mutable control-plane state or ad hoc archives.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#87` (Experiment core model: tasks, task/scenario separation, runs, apparatus context, studies (EXP-701…705))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#230` (Experiment Run Model (EXP-703))
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#87` (Experiment core model: tasks, task/scenario separation, runs, apparatus context, studies)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Experiment run contract model source)
- IMPLEMENTS → SPEC `contracts/schemas/experiment-core/experiment-run-v1.json` (Published experiment run schema)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Runtime contract schema and fixture tests)
- IMPLEMENTS → GITHUB_ISSUE `230` (Experiment Run Model (EXP-703))
