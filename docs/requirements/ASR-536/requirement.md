---
id: ASR-536
title: "Intentional-Subversion Participant Control Evaluation"
status: DRAFT
type: NON_FUNCTIONAL
priority: MUST
wave: 4
created_at: 2026-07-30T18:36:58.392300Z
updated_at: 2026-07-30T18:37:02.655471Z
---

# ASR-536 — Intentional-Subversion Participant Control Evaluation

## Statement

The ecosystem shall define revisioned participant-control evaluation profiles that distinguish honest from intentionally subverting behavior and bind main and side objectives, participant capabilities, policy and monitor knowledge, adaptive strategies, collusion and correlated monitor failure, audit budgets and selection rules, trusted editing, approval, deferral, interruption and shutdown protocols, cross-participant and cross-episode memory, replayable evidence, and separate safety, usefulness, intervention-cost, audit-cost, uncertainty, limitation, and nonclaim measures.

## Rationale

ASR-535 provides bounded participant-flow assurance discipline, but ordinary negative tests and monitor accuracy do not establish robustness against a participant that knows and adapts to the control protocol. Issue #812 adds an explicit experimental authority for intentional subversion without treating a monitor score as authorization or importing apparatus-specific LLM internals into portable records.

## Traceability

- TESTS → TEST `implementations/python/tests/test_issue_1004_apparatus_backend_capabilities.py` (ASR-536 honest/unsupported/weakened/overclaiming/colluding declaration fixtures)
- DOCUMENTS → GITHUB_ISSUE `https://github.com/OpenRAE/rae/issues/812` (Issue #812 adversarial participant control design)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-101-adversarial-participant-flow-control.md` (ADR-101: Adversarial Participant Boundary Flow Control)
- DOCUMENTS → SPEC `specs/formal/participant-semantics/adversarial-flow-control.md` (SEM-233 and ASR-536 formal authority)
- DOCUMENTS → DOCUMENTATION `docs/research/adversarial-participant-control/implementation-program.json` (Adversarial participant control implementation program)
- DOCUMENTS → GITHUB_ISSUE `https://github.com/OpenRAE/rae/issues/1004` (Issue #1004 apparatus and backend support)
- DOCUMENTS → GITHUB_ISSUE `https://github.com/OpenRAE/rae/issues/1007` (Issue #1007 adversarial evaluation)
- DOCUMENTS → GITHUB_ISSUE `https://github.com/OpenRAE/rae/issues/1008` (Issue #1008 evidenced documentation)
- DOCUMENTS → GITHUB_ISSUE `812` (Issue #812 adversarial participant control design)
