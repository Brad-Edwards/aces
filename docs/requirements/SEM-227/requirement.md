---
id: SEM-227
title: "Clock And Time-Domain Semantics"
status: DRAFT
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T03:33:02.560452Z
updated_at: 2026-06-11T15:26:04.046755Z
---

# SEM-227 — Clock And Time-Domain Semantics

## Statement

The ecosystem shall define explicit semantics for wall-clock, simulated, logical, and other declared time domains together with clock authority, visibility, and conversion boundaries.

## Rationale

Broader simulation and runtime research consistently separates time domains and clock authority; portability requires that ACES do the same explicitly.

## Traceability

- DOCUMENTS → DOCUMENTATION `/home/atomik/src/aces-sdl/research/primary/literature/time-and-simulation/misra-virtual-time-and-timeout-in-client-server.pdf` (Virtual Time and Timeout in Client-Server Networks)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#117` (Time semantics & language/runtime surfaces (SEM-227…229, DSL-126…128, RUN-317, RUN-318))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#283` (Clock And Time-Domain Semantics (SEM-227))
