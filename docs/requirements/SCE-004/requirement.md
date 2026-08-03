---
id: SCE-004
title: "Flexible Tooling Selection in Scenario Steps"
status: ACTIVE
type: FUNCTIONAL
priority: COULD
wave: 3
created_at: 2026-07-15T03:17:25.848251Z
updated_at: 2026-07-20T19:04:49.525045Z
---

# SCE-004 — Flexible Tooling Selection in Scenario Steps

## Statement

Scenario steps shall allow agents or operators to choose their own tools and techniques to achieve step objectives, rather than prescribing specific hardcoded commands. Steps shall define goals and success criteria, not implementation details.

## Rationale

Hardcoded commands prevent agents from demonstrating creative problem-solving and make scenarios brittle to tool version changes. Goal-based steps are prerequisite for meaningful agent benchmarking.

## Traceability

- IMPLEMENTS → GITHUB_ISSUE `791` (SCE-002/SCE-004: implement typed runtime fact bindings)
- IMPLEMENTS → SPEC `contracts/schemas/participant-runtime/runtime-fact-binding-plane-v1.json` (Published runtime fact binding plane contract)
- TESTS → TEST `implementations/python/tests/test_runtime_fact_bindings.py` (Runtime fact binding contract, security, and conformance tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts/runtime_facts.py` (Closed runtime fact binding contract models and invariants)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/runtime_fact_binding_policy.py` (Runtime fact scope, authority, freshness, and projection policy)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/runtime_fact_bindings.py` (Append-only runtime fact plane and trusted binding orchestration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_runtime/runtime_fact_dispatch.py` (Trusted one-shot runtime fact dispatch boundary)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/orchestration.py` (Goal-oriented workflow step authoring model)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/_workflows_verify.py` (Governed goal-step reference validation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/compiler/workflow_steps.py` (Goal-step runtime compilation and capability projection)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/workflow.py` (Portable workflow-step attempt provenance)
- TESTS → TEST `implementations/python/tests/test_sce_004_goal_oriented_steps.py` (SCE-004 goal-oriented workflow step tests)
- IMPLEMENTS → SPEC `specs/formal/workflows/goal-oriented-steps.md` (Goal-oriented workflow step semantics)
- IMPLEMENTS → GITHUB_ISSUE `653` (SCE-004 — Goal-oriented and tool-flexible scenario steps)
