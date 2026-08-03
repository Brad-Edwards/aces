---
id: DSL-437
title: "Benign participant activity and runtime execution semantics"
status: DRAFT
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-07-24T04:32:00.397864Z
updated_at: 2026-07-24T14:02:11.974014Z
---

# DSL-437 — Benign participant activity and runtime execution semantics

## Statement

ACES shall support deterministic benign and environmental simulated participants by composing existing agent identity and green-role semantics, participant behavior and action contracts, observation and evaluation boundaries, and the shared clock, time-domain, lifecycle, and runtime execution model, with explicit controls preventing non-evaluated participants from exercising score, objective, or receipt authority.

## Rationale

Ordinary user and automation activity improves range realism, but benign simulated users remain participants. Determinism is a reproducibility property, not a separate actor ontology, and live scheduling cannot define a private time model outside ACES's joint time and runtime architecture.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `861` (DSL-437 — Deterministic live activity policy and target bindings)
- CONSTRAINS → GITHUB_ISSUE `117` (Joint time semantics and language/runtime surfaces)
- CONSTRAINS → GITHUB_ISSUE `118` (Time model contracts, conformance, and provenance)
- CONSTRAINS → ADR `ADR-022` (Participant Behavior and Interaction Semantics)
- CONSTRAINS → ADR `ADR-067` (Participant Behavior Model)
