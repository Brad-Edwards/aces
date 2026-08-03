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

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#84` (Agent-facing & structured-editing authoring surfaces (AUT-801, 804, 811))
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#224` (Language-Service And Structured Editing Support (AUT-804))
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#394` (added: add SDL language service tools)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/language-service.md` (SDL language-service tool documentation)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/language_service.py` (SDL language-service orchestration helpers)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_language_edit.py` (SDL structured edit primitives)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_language_references.py` (SDL reference navigation helpers)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_language_diagnostics.py` (SDL language-service diagnostic payload helpers)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_language_metadata.py` (SDL language-service completion metadata)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/tools/language_service.py` (MCP language-service tool wrappers)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/server.py` (MCP server registration for language-service tools)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_mcp/tools/operations.py` (MCP tool-surface metadata for language-service tools)
- TESTS → TEST `implementations/python/tests/test_language_service.py` (SDL language-service helper tests)
- TESTS → TEST `implementations/python/tests/test_mcp_server.py` (MCP language-service tool tests)
