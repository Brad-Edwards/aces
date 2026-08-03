---
id: ACT-607
title: "Participant Authority And Scope Boundaries"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:14:52.825753Z
updated_at: 2026-06-24T00:50:07.671591Z
---

# ACT-607 — Participant Authority And Scope Boundaries

## Statement

The ecosystem shall support explicit declaration of participant authority boundaries, operating scope, trust anchors, and initial access or control anchors.

## Rationale

Requirement inventory expansion. Participant behavior depends on declared authority and scope rather than implicit backend assumptions.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#77` (Participant behavior model (ACT-602, 603, 606, 607, 608))
- DOCUMENTS → GITHUB_ISSUE `347` (Issue #347 — Multi-Organizational Authority And Governance Contracts)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-067-participant-behavior-model.md` (ADR-067 Participant Behavior Model)
- IMPLEMENTS → SPEC `specs/formal/participant-behavior-model/README.md` (Formal participant behavior model specification)
- IMPLEMENTS → GITHUB_ISSUE `77` (Issue #77 - Participant behavior model)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models.py` (ACT-607 participant authority and scope runtime metadata models)
- TESTS → TEST `implementations/python/tests/test_sem_208_participant_behavior.py` (ACT-607 participant authority and scope runtime regression tests)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#207` (Participant Authority And Scope Boundaries (ACT-607))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/__init__.py` (ACT-607 authority and scope runtime address compiler mapping)
