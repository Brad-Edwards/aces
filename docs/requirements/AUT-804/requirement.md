---
id: AUT-804
title: "Language-Service And Structured Editing Support"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-03T07:15:29.980212Z
updated_at: 2026-05-23T06:09:57.181800Z
---

# AUT-804 — Language-Service And Structured Editing Support

## Statement

The ecosystem shall provide language-service support for completion, reference navigation, formatting, structured diagnostics, and structured editing.

## Rationale

Requirement inventory expansion. Mature language ecosystems require structured editing and language-service capabilities.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/language-service.md` (SDL language-service tool documentation)
- TESTS → TEST `implementations/python/tests/test_language_service.py` (SDL language-service helper tests)
- TESTS → TEST `implementations/python/tests/test_mcp_server.py` (MCP language-service tool tests)
