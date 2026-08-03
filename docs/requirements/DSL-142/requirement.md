---
id: DSL-142
title: "Participant-Directed Inject Binding And Delivery"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 3
created_at: 2026-07-15T05:45:06.862070Z
updated_at: 2026-07-26T01:48:06.467151Z
---

# DSL-142 — Participant-Directed Inject Binding And Delivery

## Statement

The language shall model participant-directed inject bindings and delivery policies distinctly from environment-directed injects while preserving orchestration identity, participant addressee, disclosure and observation basis, temporal and ordering semantics, intervention meaning when applicable, and required delivery evidence.

## Rationale

DSL-111 models orchestration injects and timelines but does not define participant addressees, governed disclosure, delivery receipts, or the boundary between environment effects and participant input.

## Traceability

- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/composition/__init__.py` (DSL-142 composition reference rewriting)
- DOCUMENTS → GITHUB_ISSUE `794` (Assess and design formal participant I/O control with information-flow and bisimulation semantics)
- DOCUMENTS → DOCUMENTATION `docs/research/participant-io-control/requirement-disposition.md` (Issue #794 participant information-flow/control requirement disposition)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/participant_inject_delivery.py` (DSL-142 participant inject delivery authoring model)
- IMPLEMENTS → GITHUB_ISSUE `797` (DSL-142 — Participant-Directed Inject Binding And Delivery)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/participant_behavior_specification.py` (DSL-142 participant behavior delivery relation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_processor/compiler/participant_inject_deliveries.py` (DSL-142 typed participant delivery compiler metadata)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes/validator/_participant_inject_deliveries.py` (DSL-142 semantic admission and fail-closed validation)
- IMPLEMENTS → SPEC `specs/sdl/sections.md` (DSL-142 normative SDL section contract)
- IMPLEMENTS → SPEC `specs/sdl/references.md` (DSL-142 normative delivery reference semantics)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (DSL-142 governed authoring schema)
- TESTS → TEST `implementations/python/tests/test_dsl_142_participant_inject_delivery.py` (DSL-142 participant inject delivery tests)
- IMPLEMENTS → SPEC `contracts/schemas/sdl/instantiated-scenario-v1.json` (DSL-142 governed instantiated scenario schema)
- TESTS → TEST `implementations/python/tests/test_sdl_catalog_parity.py` (DSL-142 SDL catalog parity tests)
