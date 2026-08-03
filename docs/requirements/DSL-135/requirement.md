---
id: DSL-135
title: "Scheduled Job Runtime Inventory"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-05-30T06:21:04.620874Z
updated_at: 2026-05-30T06:21:54.244422Z
---

# DSL-135 — Scheduled Job Runtime Inventory

## Statement

The language shall represent observed scheduled and periodic job state as a typed node-scoped runtime inventory primitive, including schedule cadence (interval, cron, calendar), enablement, command reference, and run state (last run, next run, last result), without overloading service-manager units, forwarding-agent source/transform/target state, process inventory, or prose-only relationships.

## Rationale

APTL SCN-010 misp-suricata-sync (#349) is a bare-container periodic sync loop, and MISP ships scheduled feed-fetch jobs; runtime.service_units models only systemd unit lifecycle (a TIMER's load/active/enabled state), so a non-systemd cadence cannot be encoded. Scoped as a shared primitive (cadence + run-state only) so source/transform/output stay on the referencing forwarding agent and are not double-encoded.

## Traceability

- TESTS → TEST `implementations/python/tests/test_runtime_scheduled_job.py` (test_runtime_scheduled_job.py)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-047-scheduled-job-runtime-inventory.md` (ADR-047 Scheduled Job Runtime Inventory)
