---
id: DSL-128
title: "Temporal Ordering, Window, And Deadline Surface"
status: DRAFT
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T03:33:02.415118Z
updated_at: 2026-04-05T03:33:02.415118Z
---

# DSL-128 — Temporal Ordering, Window, And Deadline Surface

## Statement

The language shall support authored temporal ordering, duration, window, deadline, cadence, and comparable time-scoped assertions over scenario, participant, workflow, evaluation, and evidence concerns.

## Rationale

Primary references from workflow, detection, and simulation systems show that deadlines, windows, and ordering relations are first-class expressive needs rather than incidental timestamp comparisons.

## Traceability

- DOCUMENTS → SPEC `/home/atomik/src/aces-sdl/research/primary/reference-ecosystems/sigma-specification/specification/sigma-correlation-rules-specification.md` (Sigma Correlation Rules Specification)
- DOCUMENTS → SPEC `/home/atomik/src/aces-sdl/research/primary/reference-ecosystems/stix-schemas/pattern_grammar/STIXPattern.g4` (STIX Pattern Grammar)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#117` (Time semantics & language/runtime surfaces (SEM-227…229, DSL-126…128, RUN-317, RUN-318))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#288` (Temporal Ordering, Window, And Deadline Surface (DSL-128))
