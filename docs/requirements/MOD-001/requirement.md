---
id: MOD-001
title: "Codebase Modularity And Layering"
status: ACTIVE
type: NON_FUNCTIONAL
priority: SHOULD
wave: 3
created_at: 2026-05-09T19:09:48.679Z
updated_at: 2026-05-09T19:10:04.263848Z
---

# MOD-001 — Codebase Modularity And Layering

## Statement

The raes codebase shall maintain one-way dependency direction between SDL and processor layers (no `raes` module shall import from `raes_processor`), and shall enforce a 600-line cap on non-test, non-generated source files under `implementations/python/packages/`. Both invariants shall be enforced by the repo-policy gate so violations are caught in CI rather than relying on review judgment. Existing oversized files are tracked in an explicit allowlist that drains as each file is split into subdomain modules.

## Rationale

Cross-cutting layering and size invariants prevent the architectural drift that produces tightly-coupled, oversized modules. Captured as a single initiative-level requirement so the cycle break, the structural CI gates, the foundational ADR, and the 14 follow-up file-split PRs share one governance anchor. Pre-existing audit (issue #3 scoping comment) found 14 source files >600 lines and a hard `raes` ↔ `raes_processor` cycle via `raes/validator.py` importing `raes_processor.semantics.{objectives,workflow}`. The cycle break and CI gates are foundational; the file splits are tracked under sibling children of #3.

## Traceability

- IMPLEMENTS → ADR `docs/decisions/adrs/adr-015-sdl-processor-layering-and-source-file-size-cap.md` (ADR-015: SDL/Processor Layering And Source-File Size Cap)
- IMPLEMENTS → GITHUB_ISSUE `410` (Re-architect SDL, processor, authoring suite, and runtime module boundaries)
- CONSTRAINS → POLICY `tools/policy/repo_policy.py` (Repository policy module-boundary checker)
- CONSTRAINS → CONFIG `tools/policy/adr_policy.yaml` (ADR policy module-boundary configuration)
- TESTS → TEST `implementations/python/tests/test_repo_policy_tools.py` (Repository policy module-boundary tests)
- IMPLEMENTS → PULL_REQUEST `412` (Implement runtime module boundaries)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-036-sdl-processor-runtime-module-boundaries.md` (ADR-036: SDL, Processor, Runtime Module Boundaries)
- IMPLEMENTS → PULL_REQUEST `759` (refactor: clear PR 753 Sonar findings)
