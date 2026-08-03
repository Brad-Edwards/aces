---
id: EXP-715
title: "Observation Capability Declaration"
status: ACTIVE
type: INTERFACE
priority: MUST
wave: 2
created_at: 2026-04-03T06:39:29.450399Z
updated_at: 2026-06-22T15:43:18.790479Z
---

# EXP-715 — Observation Capability Declaration

## Statement

The ecosystem shall require backends to declare supported observation and evidence-collection capabilities separately from execution capabilities.

## Rationale

Requirement inventory expansion. Observation support must be declared explicitly so the runtime remains agnostic and experiment claims remain honest.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#88` (Experiment evidence & measures (EXP-707, 708, 709, 715))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#236` (Observation Capability Declaration (EXP-715))
- DOCUMENTS → ADR `docs/decisions/adrs/adr-064-experiment-evidence-and-measure-contract-boundary.md` (ADR-064 Experiment Evidence and Measure Contract Boundary)
- DOCUMENTS → SPEC `specs/formal/experiment-core/README.md` (Experiment Core Formal Specification)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/capabilities.py` (EXP-715 observation capability protocol dataclass and contract-gap helper)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (EXP-715 backend-manifest observation capability contract model)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_backend_protocols/manifest.py` (EXP-715 backend manifest observation payload renderer)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (EXP-715 observation capability conformance gap enforcement)
- TESTS → TEST `implementations/python/tests/test_backend_manifest.py` (EXP-715 backend manifest observation capability tests)
- IMPLEMENTS → GITHUB_ISSUE `236` (Observation Capability Declaration (EXP-715))
- IMPLEMENTS → GITHUB_ISSUE `88` (Experiment evidence & measures (EXP-707, EXP-708, EXP-709, EXP-715))
