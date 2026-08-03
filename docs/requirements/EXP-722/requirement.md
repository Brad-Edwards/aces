---
id: EXP-722
title: "Realized Form Disclosure"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T00:54:58.634035Z
updated_at: 2026-06-22T02:05:42.732638Z
---

# EXP-722 — Realized Form Disclosure

## Statement

The ecosystem shall preserve, as part of run and apparatus provenance, the realized forms chosen by processors and backends for underspecified concerns, distinct from the authored scenario and from derived results.

## Rationale

Current state: identified gap. When authors leave details open, the realized choices still affect interpretation, comparison, and reproduction and therefore must be preserved explicitly.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#89` (Experiment provenance (EXP-710, 720, 722))
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#89` (Experiment provenance: provenance/traceability, canonical run provenance record, realized-form disclosure)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#576` (added: add experiment run provenance contract)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Experiment run provenance runtime contracts)
- IMPLEMENTS → SPEC `contracts/schemas/experiment-core/experiment-run-v1.json` (Experiment run v1 published schema)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Experiment run provenance runtime contract tests)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-065-experiment-run-provenance-contract-boundary.md` (ADR-065 Experiment run provenance contract boundary)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#239` (Realized Form Disclosure (EXP-722))
