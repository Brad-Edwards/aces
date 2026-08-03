---
id: MOD-884
title: "Hard-cut Python SDL imports from the legacy namespace to raes"
status: DRAFT
type: CONSTRAINT
priority: MUST
created_at: 2026-07-25T18:22:10.174781Z
updated_at: 2026-07-25T18:22:14.794227Z
---

# MOD-884 — Hard-cut Python SDL imports from the legacy namespace to raes

## Statement

The published raes Python distribution shall expose the canonical SDL API through the top-level raes import namespace, repository source and user-facing examples shall use raes instead of the legacy import namespace, and the legacy import package shall be removed without a backwards-compatibility alias or shim.

## Rationale

The published PyPI distribution is named raes, but its canonical SDL import namespace remains the legacy one. The user has explicitly required a hard cut to raes with no backwards-compatibility alias or shim.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `884` (Reframe RAES documentation around reproducible agentic environments)
