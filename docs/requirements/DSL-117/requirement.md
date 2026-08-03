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

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#120` (Participant tool/affordance & decision-exposure language surfaces (DSL-116, 117, 118, 125))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#298` (Participant Tool And Affordance Modeling (DSL-117))
- TESTS → TEST `implementations/python/tests/test_participant_interactive_access.py` (Participant interactive-access SDL and compiler tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (contracts.py)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/participant_behaviors.py` (participant_behaviors.py)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models/__init__.py` (__init__.py)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/models/behavior_resources.py` (behavior_resources.py)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_mapping_scopes.py` (_mapping_scopes.py)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_language_metadata.py` (_language_metadata.py)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/agents.py` (agents.py)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/composition.py` (composition.py)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/semantics/participant_interactive_access.py` (participant_interactive_access.py)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/_content_objectives.py` (_content_objectives.py)
- IMPLEMENTS → PULL_REQUEST `807` (feat(sdl): add participant interactive access)
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#805` (SDL: authored participant interactive-access (SSH/RDP) declarations)
