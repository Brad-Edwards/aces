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

- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/__init__.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/__main__.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/server.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/tools/__init__.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/tools/authoring.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/tools/inspection.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/tools/reference.py`
- TESTS → TEST `implementations/python/tests/test_mcp_server.py`
- IMPLEMENTS → GITHUB_ISSUE `397` (Cross-agent asset inventory capture skill)
- IMPLEMENTS → DOCUMENTATION `.claude/skills/aces-asset-inventory-capture/SKILL.md` (ACES asset inventory capture skill)
- TESTS → TEST `implementations/python/tests/test_agent_inventory_skill.py` (Agent inventory skill structural gate)
- IMPLEMENTS → DOCUMENTATION `.codex-skills/aces-asset-inventory-capture/SKILL.md` (ACES asset inventory capture Codex skill)
- IMPLEMENTS → GITHUB_ISSUE `445` (Add gap-remediation implement overlay skill)
- IMPLEMENTS → CONFIG `.codex` (Codex repo skill discovery rules)
- IMPLEMENTS → DOCUMENTATION `.claude/skills/aces-gap-remediation-implement/SKILL.md` (ACES gap remediation Claude skill)
- IMPLEMENTS → DOCUMENTATION `.codex-skills/aces-gap-remediation-implement/SKILL.md` (ACES gap remediation Codex skill)
- IMPLEMENTS → PULL_REQUEST `477` (docs: register gap remediation overlay)
