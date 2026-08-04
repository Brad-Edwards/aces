---
id: REP-001
title: "Design: RAES-driven CAGE-2 replication and adapters-monorepo architecture"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 4
created_at: 2026-07-01T17:47:58.915590Z
updated_at: 2026-07-02T06:02:46.444081Z
---

# REP-001 — Design: RAES-driven CAGE-2 replication and adapters-monorepo architecture

## Statement

RAES shall define, in an accepted ADR and design record, the architecture for driving the TTCP CAGE Challenge 2 (Scenario2) scenario through the RAES pipeline into a conformant simulator backend. The design shall cover: the CAGE-2 to RAES SDL mapping; the CybORG simulation-backend adapter design against the published backend protocols (Provisioner, Orchestrator, Evaluator, ParticipantRuntime); the shared sim-adapter base package and backend conformance harness; the adapters-monorepo layout (isolated per-adapter projects each with their own lockfile, plus a per-adapter CI matrix for dependency isolation); the replication/equivalence success criteria used to judge that the authored scenario is realized consistently across backends; and the cross-repo issue-driven workflow (RAES issues drive adapters-monorepo work). Scope explicitly excludes realizing CAGE-2 on an emulation backend.

## Rationale

First target for demonstrating that RAES scenario portability is a property of the specification: one authored scenario realized across independent conformant backends. CAGE-2 is a recognized, published, simulation-only scenario whose original sim/emulation common-interface goal was abandoned, making it a pointed replication target.

## Traceability

- IMPLEMENTS → ADR `docs/decisions/adrs/adr-069-cage-2-replication-architecture.md` (ADR-069: CAGE-2 replication architecture)
- IMPLEMENTS → DOCUMENTATION `docs/decisions/cage-2-replication-design.md` (CAGE-2 replication design record)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-635-rep-001-cage-2-replication-preflight.md` (Issue 635 CAGE-2 replication architecture preflight)
- DOCUMENTS → DOCUMENTATION `changelog.d/635.added.md` (Changelog fragment for issue 635 / REP-001)
