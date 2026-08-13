---
id: RUN-317
title: "Runtime Clock And Time-Domain Handling"
status: DRAFT
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T03:33:03.083582Z
updated_at: 2026-04-05T03:33:03.083582Z
---

# RUN-317 — Runtime Clock And Time-Domain Handling

## Statement

The runtime shall support portable handling of declared clocks and time domains across instantiation, execution, live observation, timeout handling, reset, and replay.

## Rationale

If authored scenarios and experiments can depend on time domains, the runtime needs a portable model for carrying those domains through execution and observation.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `1102` (Fail-closed workflow timeout reconciliation)
- DOCUMENTS → DOCUMENTATION `docs/decisions/issue-1102-workflow-timeout-reconciliation-preflight.md` (Wall-clock timeout reconciliation boundary)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/raes_runtime/control_plane_timeouts.py` (Strict persisted timestamp and elapsed-time handling)
- TESTS → TEST `implementations/python/tests/test_runtime_workflow_timeout_reconciliation.py` (Malformed timestamp, boundary, and restart regressions)
