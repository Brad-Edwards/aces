---
id: EXP-710
title: "Provenance And Traceability"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T06:39:28.858157Z
updated_at: 2026-06-22T02:05:42.732590Z
---

# EXP-710 — Provenance And Traceability

## Statement

The ecosystem shall preserve traceability from task and run context through captured evidence to derived measures, evaluations, and experiment claims.

## Rationale

Requirement inventory expansion. Experiment claims require provenance and traceability rather than unsupported interpretation.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#89` (Experiment provenance (EXP-710, 720, 722))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#237` (Provenance And Traceability (EXP-710))
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#89` (Experiment provenance: provenance/traceability, canonical run provenance record, realized-form disclosure)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#576` (added: add experiment run provenance contract)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Experiment run provenance runtime contracts)
- IMPLEMENTS → SPEC `contracts/schemas/experiment-core/experiment-run-v1.json` (Experiment run v1 published schema)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Experiment run provenance runtime contract tests)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-065-experiment-run-provenance-contract-boundary.md` (ADR-065 Experiment run provenance contract boundary)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#237` (Provenance And Traceability (EXP-710))
