---
id: RUN-317
title: "Runtime Clock And Time-Domain Handling"
status: DRAFT
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T03:33:03.083582Z
updated_at: 2026-04-05T03:33:03.083582Z
---

# RUN-317 — Runtime Clock And Time-Domain Handling

## Statement

The runtime shall support portable handling of declared clocks and time domains across instantiation, execution, live observation, timeout handling, reset, and replay.

## Rationale

If authored scenarios and experiments can depend on time domains, the runtime needs a portable model for carrying those domains through execution and observation.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#117` (Time semantics & language/runtime surfaces (SEM-227…229, DSL-126…128, RUN-317, RUN-318))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#289` (Runtime Clock And Time-Domain Handling (RUN-317))
