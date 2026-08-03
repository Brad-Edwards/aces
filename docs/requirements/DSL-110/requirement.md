---
id: DSL-110
title: "Assessment Model"
status: DEPRECATED
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:55:58.139676Z
updated_at: 2026-07-06T04:54:25.514810Z
---

# DSL-110 — Assessment Model

## Statement

The language shall model assessment constructs through conditions, metrics, evaluations, TLOs, and goals.

## Rationale

Requirement inventory phase. Status audit deferred until the full canonical graph is complete.

## Traceability

- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL sections reference for the conditions-to-metrics-to-evaluations-to-TLOs-to-goals pipeline)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (Validation rules for assessment references and scoring-threshold invariants)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/precedents.md` (Design precedents documenting the direct OCR scoring-pipeline port)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/parser.md` (Parser behavior for min-score shorthand expansion in the assessment model)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/runtime-architecture.md` (Runtime architecture for compiled evaluation graph ordering and contracts)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-001-scenario-description-language.md` (ADR-001: preserve OCR scoring pipeline in the SDL surface)
- CONSTRAINS → SPEC `contracts/schemas/sdl/sdl-authoring-input-v1.json` (SDL authoring schema for metrics, evaluations, TLOs, and goals)
- CONSTRAINS → SPEC `contracts/schemas/sdl/instantiated-scenario-v1.json` (Instantiated SDL schema carrying normalized assessment-model constructs)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/conditions.py` (Condition model for boolean gate definitions used by the assessment pipeline)
