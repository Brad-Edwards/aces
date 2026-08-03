---
id: EXP-704
title: "Execution Apparatus Context"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T06:39:28.197537Z
updated_at: 2026-05-26T06:32:58.337756Z
---

# EXP-704 — Execution Apparatus Context

## Statement

The ecosystem shall preserve execution apparatus context for each run, including processor identity, backend identity, selected manifests, applied compatibility declarations, configuration, parameters, stochastic controls, and other setup context, as information distinct from the task, authored scenario meaning, live execution state, and run results.

## Rationale

Requirement inventory expansion. Apparatus context must remain separate from task definition, authored scenario meaning, live execution state, and derived results so comparison, provenance, and reproducibility do not depend on inference.

## Traceability

- IMPLEMENTS → SPEC `contracts/schemas/experiment-core/experiment-apparatus-context-v1.json` (Published experiment apparatus context schema)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Runtime contract schema and fixture tests)
