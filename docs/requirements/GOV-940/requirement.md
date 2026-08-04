---
id: GOV-940
title: "Multi-Organizational Authority And Governance Contracts"
status: DRAFT
type: NON_FUNCTIONAL
priority: MUST
wave: 3
created_at: 2026-05-18T17:19:03.107569Z
updated_at: 2026-05-18T17:19:08.100436Z
---

# GOV-940 — Multi-Organizational Authority And Governance Contracts

## Statement

The ecosystem shall define explicit multi-organizational authority and governance contract semantics for data-sharing rules, approval rights, evidence ownership and release constraints, reporting obligations, and cross-organization custody boundaries across scenarios, runs, evidence, results, and studies.

## Rationale

Multi-organization cyber range scenarios require more than participant visibility and evidence capture: they need portable semantics for which organization owns, may approve, may receive, must report, or may release governed information and evidence. Without this, RAES can model multiple organizations acting in a scenario but cannot precisely model the authority and governance constraints that make cross-organization exercises realistic and auditable.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `347` (Issue #347 — Multi-Organizational Authority And Governance Contracts)
- CONSTRAINS → ADR `ADR-008` (ADR-008 — Processor Layer And Execution Artifact Boundaries)
- CONSTRAINS → ADR `ADR-009` (ADR-009 — Normative Artifact Authority And Repository Structure)
- CONSTRAINS → ADR `ADR-019` (ADR-019 — Canonical Manifest For The Normative Artifact Authority Boundary)
- CONSTRAINS → ADR `ADR-020` (ADR-020 — Declarative Participant Framing Boundaries)
- CONSTRAINS → ADR `ADR-021` (ADR-021 — Participant Behavior And Interaction Semantics)
