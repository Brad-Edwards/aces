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
