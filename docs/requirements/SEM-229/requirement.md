---
id: SEM-229
title: "Temporal Ordering, Causality, And Window Semantics"
status: DRAFT
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T03:33:02.920191Z
updated_at: 2026-06-11T15:26:06.587837Z
---

# SEM-229 — Temporal Ordering, Causality, And Window Semantics

## Statement

The ecosystem shall define explicit semantics for ordering, causality, simultaneity, deadlines, time windows, and timestamp interpretation independent of backend-local scheduler behavior.

## Rationale

Distributed simulation and temporal assertion systems repeatedly show that causality and temporal ordering need stronger semantics than raw timestamps alone provide.

## Traceability

- DOCUMENTS → DOCUMENTATION `/home/atomik/src/aces-sdl/research/primary/literature/time-and-simulation/taylor-sudra-hoffman-2003-time-management-cots-distributed-simulation.pdf` (Time management issues in COTS distributed simulation: a case study)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#117` (Time semantics & language/runtime surfaces (SEM-227…229, DSL-126…128, RUN-317, RUN-318))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#285` (Temporal Ordering, Causality, And Window Semantics (SEM-229))
