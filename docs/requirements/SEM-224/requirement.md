---
id: SEM-224
title: "Observability Plane Separation Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T01:59:50.378983Z
updated_at: 2026-06-23T04:06:28.568679Z
---

# SEM-224 — Observability Plane Separation Semantics

## Statement

The ecosystem shall define explicit semantics distinguishing scenario-native observability systems, authored evidence requirements, processor or backend operational observability, captured evidence, and derived analysis outputs.

## Rationale

The ecosystem needs a clear semantic split between in-world observability, experiment evidence requirements, and apparatus observability so these concerns do not collapse into one another.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#127` (Observability plane separation & realization-augmentation semantics; scenario-native observability & authored evidence-requirement surfaces (SEM-224, 225, DSL-123, 124))
- DOCUMENTS → GITHUB_ISSUE `347` (Issue #347 — Multi-Organizational Authority And Governance Contracts)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-066-observability-evidence-plane-separation.md` (ADR-066 Observability evidence plane separation)
- IMPLEMENTS → SPEC `specs/formal/observability-evidence-plane.md` (Formal observability/evidence plane specification)
- IMPLEMENTS → DOCUMENTATION `specs/sdl/observability-and-evidence.md` (SDL observability and evidence authoring catalog)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#127` (Issue #127 observability and evidence semantics)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/observability_plane_semantics.py` (SEM-224 observability/evidence plane classifier)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (SEM-224 x-aces-plane annotation on claim-bearing experiment-core contracts)
- TESTS → TEST `implementations/python/tests/test_sem_224_observability_plane_semantics.py` (SEM-224 plane classifier + five-distinction test suite)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#334` (Observability Plane Separation Semantics (SEM-224))
