---
id: EXP-734
title: "Realized Time Model And Clock Provenance"
status: DRAFT
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T03:33:03.542752Z
updated_at: 2026-04-05T03:33:03.542752Z
---

# EXP-734 — Realized Time Model And Clock Provenance

## Statement

The ecosystem shall preserve the realized time model for each run, including declared and realized time domains, clock authority, pacing or dilation policy, synchronization assumptions, and timing-relevant limits or apparatus choices.

## Rationale

Experimental comparison and replay claims depend on preserving how time was actually realized, not merely on recording timestamps after the fact.

## Traceability

- DOCUMENTS → DOCUMENTATION `/home/atomik/src/aces-sdl/research/primary/reference-ecosystems/open-range/docs/how-an-episode-works.md` (OpenRange: How an Episode Works)
- DOCUMENTS → DOCUMENTATION `/home/atomik/src/aces-sdl/research/primary/reference-ecosystems/open-range/docs/training-data-spec.md` (OpenRange Training Data Specification)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#118` (Time model contracts, conformance & provenance (API-421, ASR-528, EXP-734))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#293` (Realized Time Model And Clock Provenance (EXP-734))
