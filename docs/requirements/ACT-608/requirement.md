---
id: ACT-608
title: "Participant Behavior Modes"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T06:14:52.930230Z
updated_at: 2026-06-24T00:50:07.720652Z
---

# ACT-608 — Participant Behavior Modes

## Statement

The ecosystem shall support participant behavior modes including autonomous, scripted, policy-directed, replayed, supervised, and mixed-control operation.

## Rationale

Requirement inventory expansion. Participant behavior needs explicit mode distinctions without binding the ecosystem to one execution framework.

## Traceability

- IMPLEMENTS → ADR `docs/decisions/adrs/adr-067-participant-behavior-model.md` (ADR-067 Participant Behavior Model)
- IMPLEMENTS → SPEC `specs/formal/participant-behavior-model/README.md` (Formal participant behavior model specification)
- IMPLEMENTS → GITHUB_ISSUE `77` (Issue #77 - Participant behavior model)
- IMPLEMENTS → SPEC `contracts/concept-authority/controlled-vocabularies-v1.json` (ACT-608 participant decision-surface mode vocabulary)
- IMPLEMENTS → SPEC `contracts/fixtures/concept-authority/controlled-vocabularies-v1/valid/reference.json` (ACT-608 controlled-vocabulary reference fixture)
- TESTS → TEST `implementations/python/tests/test_controlled_vocabularies.py` (ACT-608 behavior-mode governed-scope tests)
- TESTS → TEST `implementations/python/tests/test_sem_208_participant_behavior.py` (ACT-608 participant behavior-mode parse/validate/compile tests)
- IMPLEMENTS → GITHUB_ISSUE `208` (Issue #208 Participant Behavior Modes)
