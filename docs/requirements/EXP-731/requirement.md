---
id: EXP-731
title: "Evidence Requirement Refinement And Extension"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T01:59:50.735706Z
updated_at: 2026-06-28T18:07:50.939641Z
---

# EXP-731 — Evidence Requirement Refinement And Extension

## Statement

The ecosystem shall support task-, run-, or study-level refinement and extension of authored data and evidence requirements without silently rewriting authored scenario meaning.

## Rationale

Different experiments may need to add or tighten evidence requirements without changing the base scenario contract, and that relationship needs to be explicit rather than implicit.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#128` (Operational apparatus observability; observation-augmentation disclosure contracts; observability-plane/augmentation conformance; evidence-requirement refinement & realized-evidence provenance (RUN-316, API-419, ASR-525, EXP-731, 732))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#341` (Evidence Requirement Refinement And Extension (EXP-731))
- IMPLEMENTS → GITHUB_ISSUE `128` (Issue #128 - Observability evidence conformance implementation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (Run-refinement diagnostics require authored and evidence references for realized evidence refinements)
- TESTS → TEST `implementations/python/tests/test_observability_evidence_conformance.py` (Tests verify capture-window and measurement-channel refinements preserve authored and evidence references)
