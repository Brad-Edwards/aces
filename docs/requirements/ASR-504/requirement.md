---
id: ASR-504
title: "Validation Corpus"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:40:05.622267Z
updated_at: 2026-05-17T05:29:31.051602Z
---

# ASR-504 — Validation Corpus

## Statement

The ecosystem shall maintain a validation corpus spanning unit, example, real-world, fuzz, and negative-path scenarios.

## Rationale

Current state: partially implemented. The repo has strong unit, negative-path, stress, real-world, and fuzz coverage, but the example-corpus leg is stale after the reorg because the example scenario test path still targets the old location.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/testing.md` (SDL Testing)
- CONSTRAINS → ADR `ADR-007` (Lightweight Formal Methods Policy for Semantic Systems)
- TESTS → TEST `implementations/python/tests/test_sdl_models.py` (SDL Model Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (SDL Validator Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (SDL Parser Tests)
- TESTS → TEST `implementations/python/tests/test_scenarios.py` (SDL Example Scenario Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_realworld.py` (SDL Real-World Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_stress.py` (SDL Stress Tests)
- TESTS → TEST `implementations/python/tests/test_sdl_fuzz.py` (SDL Fuzz Tests)
- DOCUMENTS → GITHUB_ISSUE `#7` (Repair example corpus test paths after repo reorg)
- IMPLEMENTS → GITHUB_ISSUE `67` (Issue #67 Validation corpus: restore example-scenario leg)
- TESTS → TEST `implementations/python/tests/test_mcp_server.py` (SDL Example Corpus MCP-Tool Tests)
- TESTS → TEST `implementations/python/tests/test_example_schema_conformance.py` (SDL Example Published-Schema Conformance Tests)
- IMPLEMENTS → GITHUB_ISSUE `501` (Issue #501 Validate worked examples against published JSON Schemas (CT-4))
- IMPLEMENTS → GITHUB_ISSUE `7` (ASR-504: Validation Corpus)
- IMPLEMENTS → PULL_REQUEST `709` (test: add example corpus non-vacuity guard)
- IMPLEMENTS → TEST `implementations/python/tests/test_scenarios.py` (SDL Example Scenario Tests)
