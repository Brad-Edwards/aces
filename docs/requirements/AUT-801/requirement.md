---
id: AUT-801
title: "Agent-Facing Tool Surface"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T07:15:29.493969Z
updated_at: 2026-05-23T02:41:31.120132Z
---

# AUT-801 — Agent-Facing Tool Surface

## Statement

The ecosystem shall provide a self-describing agent-facing tool surface for authoring, parsing, validation, inspection, and experiment operations without requiring repository-local code access.

## Rationale

Requirement inventory expansion. Agents need a first-class usable surface rather than an implicit dependency on source-code familiarity.

## Traceability

- TESTS → TEST `implementations/python/tests/test_mcp_server.py` (Agent-facing MCP operation tests)
