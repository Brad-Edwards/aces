---
id: DSL-117
title: "Participant Tool And Affordance Modeling"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T01:24:06.514527Z
updated_at: 2026-07-15T08:42:44.856602Z
---

# DSL-117 — Participant Tool And Affordance Modeling

## Statement

The language shall support declaration of participant-visible tools, affordances, interfaces, and interaction channels together with any relevant scope or availability constraints.

## Rationale

Primary-source refresh shows that tool-using participants require an explicit authoring surface for what interaction affordances are available, rather than leaving that surface implicit in one benchmark or agent harness.

## Traceability

- TESTS → TEST `implementations/python/tests/test_participant_interactive_access.py` (Participant interactive-access SDL and compiler tests)
- IMPLEMENTS → PULL_REQUEST `807` (feat(sdl): add participant interactive access)
