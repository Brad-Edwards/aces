---
id: DSL-120
title: "Participant Episode Structure And Termination Surface"
status: DRAFT
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T01:39:32.895216Z
updated_at: 2026-04-05T01:39:32.895216Z
---

# DSL-120 — Participant Episode Structure And Termination Surface

## Statement

The language shall support authored participant episode structure, including initialization, turn or interaction structure, termination conditions, truncation conditions, and reset-related declarations where tasks or experiments require them.

## Rationale

Primary-source refresh shows that participant-supporting ecosystems frequently treat episodes, turns, reset behavior, and termination structure as first-class authored concerns rather than backend-local conventions.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#122` (Participant episode/reset & budget/quota: semantics + language surfaces + model (SEM-222, 223, DSL-120, 121, ACT-623, 624))
- DOCUMENTS → SPEC `specs/formal/participant-episode-model/README.md` (Participant episode + budget model formal design (issue #122))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#307` (Participant Episode Structure And Termination Surface (DSL-120))
