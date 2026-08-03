---
id: EXP-720
title: "Canonical Run Provenance Record"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-04T22:58:17.054011Z
updated_at: 2026-06-22T02:05:42.732625Z
---

# EXP-720 — Canonical Run Provenance Record

## Statement

The ecosystem shall define a canonical run provenance record, serving as the authoritative archival run record distinct from live execution state, capturing task reference, scenario and module digests, processor identity, backend identity, manifest references or digests, configuration, parameters, stochastic controls, timestamps, and result or evidence pointers.

## Rationale

Canonical provenance is required so the authoritative archival run record can support comparison, review, and reproduction without inferring critical execution context from mutable operational state.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#89` (Experiment provenance (EXP-710, 720, 722))
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#89` (Experiment provenance: provenance/traceability, canonical run provenance record, realized-form disclosure)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#576` (added: add experiment run provenance contract)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Experiment run provenance runtime contracts)
- IMPLEMENTS → SPEC `contracts/schemas/experiment-core/experiment-run-v1.json` (Experiment run v1 published schema)
- IMPLEMENTS → CONFIG `contracts/schema-publication-manifest.json` (Schema publication manifest entry for experiment-run-v1)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Experiment run provenance runtime contract tests)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-065-experiment-run-provenance-contract-boundary.md` (ADR-065 Experiment run provenance contract boundary)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#238` (Canonical Run Provenance Record (EXP-720))
