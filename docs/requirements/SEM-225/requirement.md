---
id: SEM-225
title: "Realization Augmentation And Environment-Visibility Semantics"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T01:59:50.501378Z
updated_at: 2026-06-23T04:06:33.107397Z
---

# SEM-225 — Realization Augmentation And Environment-Visibility Semantics

## Statement

The ecosystem shall define explicit semantics for processor or backend augmentation used to satisfy evidence, evaluation, or operational requirements, including when such augmentation is environment-visible, participant-visible, or comparability-relevant.

## Rationale

If processors or backends add instrumentation or other augmentation, the ecosystem needs normative rules for when that remains apparatus-only and when it becomes part of the realized world.

## Traceability

- IMPLEMENTS → ADR `docs/decisions/adrs/adr-066-observability-evidence-plane-separation.md` (ADR-066 Observability evidence plane separation)
- IMPLEMENTS → SPEC `specs/formal/observability-evidence-plane.md` (Formal observability/evidence plane specification)
- IMPLEMENTS → DOCUMENTATION `specs/sdl/observability-and-evidence.md` (SDL observability and evidence authoring catalog)
- IMPLEMENTS → SPEC `contracts/schemas/experiment-core/experiment-run-v1.json` (experiment-run-v1 SEM-225 augmentation disclosure schema)
- TESTS → TEST `implementations/python/tests/test_sem_225_augmentation_semantics.py` (SEM-225 augmentation disclosure semantics regression tests)
