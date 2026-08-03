---
id: RUN-312
title: "Budgeted Participant Execution Accounting"
status: DRAFT
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T01:39:33.803505Z
updated_at: 2026-04-05T01:39:33.803505Z
---

# RUN-312 — Budgeted Participant Execution Accounting

## Statement

The runtime shall track and expose participant budget and quota consumption together with any limit-triggered state changes, interventions, or termination.

## Rationale

Primary-source refresh shows that budgeted participant execution requires runtime accounting surfaces rather than implicit backend-local counters.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#123` (Participant episode/reset & budget contracts, runtime accounting & conformance (API-417, 418, RUN-312, ASR-523, EXP-728))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#313` (Budgeted Participant Execution Accounting (RUN-312))
