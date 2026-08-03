---
id: ASR-534
title: "Reproducible Related-Work Claim Comparison"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
wave: 3
created_at: 2026-07-13T05:26:37.284747Z
updated_at: 2026-07-13T16:24:37.255995Z
---

# ASR-534 — Reproducible Related-Work Claim Comparison

## Statement

The ecosystem shall publish a preregistered, revision-pinned related-work comparison that evaluates each system independently across the twelve declared axes, binds every cell to primary-source evidence and a reproducible rationale, exercises representative authoring tasks and negative cases, reports scope-qualified Pareto findings with disclosed sensitivity reversals, and mechanically prevents public wording from drifting beyond the evidence.

## Rationale

Issue #728 replaces a prose-only, internally selected comparison with a frozen evidence bundle and an offline integrity gate so breadth, quality, maturity, and standardization claims remain distinct and reproducible.

## Traceability

- IMPLEMENTS → DOCUMENTATION `docs/research/related-work-comparison/extraction-snapshot-2026-07-13.json` (Revision-pinned primary-source extraction snapshot)
- IMPLEMENTS → DOCUMENTATION `docs/research/related-work-comparison/protocol-v1.json` (Preregistered related-work comparison protocol)
- IMPLEMENTS → DOCUMENTATION `docs/explain/sdl/related-work-comparison.md` (Published evidence-bounded related-work comparison)
- IMPLEMENTS → CODE_FILE `tools/check_related_work_comparison.py` (Offline related-work integrity checker)
- IMPLEMENTS → DOCUMENTATION `docs/research/related-work-comparison/analysis-v1.json` (Recomputed Pareto and sensitivity analysis)
- TESTS → TEST `implementations/python/tests/test_related_work_comparison.py` (Focused related-work comparison checker tests)
- TESTS → TEST `noxfile.py` (Canonical verification graph integration)
- IMPLEMENTS → GITHUB_ISSUE `728` (Issue #728)
- IMPLEMENTS → PULL_REQUEST `765` (PR #765)
