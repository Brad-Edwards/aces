---
id: DSL-126
title: "Time Domain And Clock Surface"
status: DRAFT
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T03:33:01.935317Z
updated_at: 2026-04-05T03:33:01.935317Z
---

# DSL-126 — Time Domain And Clock Surface

## Statement

The language shall support authored references to time domains, clocks, and comparable temporal authorities when scenario or experiment meaning depends on them.

## Rationale

Cross-domain time research shows that mature ecosystems distinguish system time, simulated or logical time, and other clock domains rather than treating time as a single implicit backdrop.

## Traceability

- DOCUMENTS → SPEC `https://design.ros2.org/articles/clock_and_time.html` (ROS 2 Clock and Time)
- DOCUMENTS → SPEC `https://fmi-standard.org/docs/3.0.2/` (FMI 3.0.2 Specification)
- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#117` (Time semantics & language/runtime surfaces (SEM-227…229, DSL-126…128, RUN-317, RUN-318))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#286` (Time Domain And Clock Surface (DSL-126))
