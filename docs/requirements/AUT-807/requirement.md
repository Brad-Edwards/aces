---
id: AUT-807
title: "Machine-Readable Guidance And Discovery Surfaces"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T07:15:30.410028Z
updated_at: 2026-05-09T05:20:55.546125Z
---

# AUT-807 — Machine-Readable Guidance And Discovery Surfaces

## Statement

The ecosystem shall provide machine-readable guidance, discovery, and help surfaces sufficient for agents and tools to discover and use the ecosystem without external prose-only documentation.

## Rationale

Requirement inventory expansion. Agent and tool usability requires machine-readable guidance and discovery surfaces.

## Traceability

- TESTS → TEST `implementations/python/tests/test_mcp_server.py`
- IMPLEMENTS → GITHUB_ISSUE `397` (Cross-agent asset inventory capture skill)
- TESTS → TEST `implementations/python/tests/test_agent_inventory_skill.py` (Agent inventory skill structural gate)
- IMPLEMENTS → GITHUB_ISSUE `445` (Add gap-remediation implement overlay skill)
- IMPLEMENTS → CONFIG `.codex` (Codex repo skill discovery rules)
- IMPLEMENTS → PULL_REQUEST `477` (docs: register gap remediation overlay)
