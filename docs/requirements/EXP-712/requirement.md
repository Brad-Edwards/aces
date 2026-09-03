---
id: EXP-712
title: "Reproducibility And Replay Claims"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
wave: 3
created_at: 2026-04-03T06:39:29.082366Z
updated_at: 2026-06-25T18:25:28.798036Z
---

# EXP-712 — Reproducibility And Replay Claims

## Statement

The ecosystem shall support reproducibility and replay claims for runs through preserved run context, evidence, provenance, and derived-result lineage.

## Rationale

Requirement inventory expansion. Reproducibility claims need preserved context and lineage, not just stored outputs.

## Traceability

- DOCUMENTS → ADR `docs/decisions/adrs/adr-068-experiment-trials-replication-and-replay-claims.md` (ADR-068: Experiment Trials, Replication, and Replay Claims)
- DOCUMENTS → SPEC `specs/formal/experiment-core/README.md` (Experiment Core Formal Specification)
- DOCUMENTS → DOCUMENTATION `docs/research/experiment-core/traceability-matrix-exp-706-712.md` (EXP-706/EXP-712 Clause Matrix)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-068-experiment-trials-replication-and-replay-claims.md` (ADR-068: Experiment Trials, Replication, and Replay Claims)
- IMPLEMENTS → SPEC `specs/formal/experiment-core/README.md` (Experiment Core Formal Specification)
- IMPLEMENTS → DOCUMENTATION `docs/research/experiment-core/traceability-matrix-exp-706-712.md` (EXP-706/EXP-712 Clause Matrix)
- IMPLEMENTS → DOCUMENTATION `docs/research/experiment-core/issue-105-exp-706-712-reproducibility-replay-preflight-guardrails.md` (Issue #105 Experiment Reproducibility and Replay Preflight Guardrails)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Runtime contract tests for experiment study allocation, run provenance, and derived measures)
