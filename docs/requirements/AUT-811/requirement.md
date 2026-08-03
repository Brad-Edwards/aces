---
id: AUT-811
title: "Agent-Usable Invariants, Scope, And Review Guidance"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T07:16:00.222627Z
updated_at: 2026-05-23T16:20:21.075142Z
---

# AUT-811 — Agent-Usable Invariants, Scope, And Review Guidance

## Statement

The ecosystem shall provide machine-usable guidance capturing scope boundaries, invariants, review priorities, and safe-operating expectations for agentic contributors and operators.

## Rationale

Requirement inventory expansion. Agent-facing operation needs explicit guardrails and review guidance in machine-usable form.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#84` (Agent-facing & structured-editing authoring surfaces (AUT-801, 804, 811))
- IMPLEMENTS → SPEC `specs/agent-guidance/agent-guidance.yaml` (Canonical ACES agent guidance profile)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/agent_guidance.py` (Agent guidance profile loader and audience filter)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/tools/operations.py` (aces_agent_guidance MCP tool and guidance tool family)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/server.py` (MCP server instructions directing agents to guidance)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/agent-guidance.md` (Agent guidance profile user documentation)
- DOCUMENTS → DOCUMENTATION `docs/explain/getting-started.md` (Getting started guidance for agent tool discovery)
- DOCUMENTS → DOCUMENTATION `docs/api/sdl.rst` (API documentation for aces_sdl.agent_guidance)
- TESTS → POLICY `tools/check_agent_guidance.py` (Agent guidance profile structural checker)
- TESTS → TEST `implementations/python/tests/test_agent_guidance.py` (Agent guidance helper unit tests)
- TESTS → TEST `implementations/python/tests/test_agent_guidance_policy.py` (Agent guidance policy checker tests)
- TESTS → TEST `implementations/python/tests/test_mcp_server.py` (MCP server agent guidance surface tests)
- TESTS → CONFIG `noxfile.py` (Nox policy wiring for agent guidance profile checker)
- IMPLEMENTS → GITHUB_ISSUE `225` (Issue #225 Agent-Usable Invariants, Scope, And Review Guidance)
