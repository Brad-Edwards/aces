---
id: EXP-709
title: "Derived Measure And Evaluation Model"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T06:39:28.747413Z
updated_at: 2026-06-22T15:12:00.516490Z
---

# EXP-709 — Derived Measure And Evaluation Model

## Statement

The ecosystem shall distinguish captured evidence from derived measures, evaluations, scores, summaries, and comparable analysis outputs computed from that evidence.

## Rationale

Requirement inventory expansion. Derived evaluations must stay distinct from the underlying evidence they interpret.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#88` (Experiment evidence & measures (EXP-707, 708, 709, 715))
- DOCUMENTS → ADR `docs/decisions/adrs/adr-064-experiment-evidence-and-measure-contract-boundary.md` (ADR-064 Experiment Evidence and Measure Contract Boundary)
- DOCUMENTS → SPEC `specs/formal/experiment-core/README.md` (Experiment Core Formal Specification)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Experiment derived measure contract model source (ExperimentDerivedMeasureModel))
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Experiment derived measure conformance and rejection tests)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#235` (Derived Measure And Evaluation Model (EXP-709))
- IMPLEMENTS → GITHUB_ISSUE `88` (Experiment evidence & measures (EXP-707, EXP-708, EXP-709, EXP-715))
