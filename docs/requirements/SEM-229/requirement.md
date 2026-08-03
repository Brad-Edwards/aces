---
id: SEM-229
title: "Temporal Ordering, Causality, And Window Semantics"
status: DRAFT
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T03:33:02.920191Z
updated_at: 2026-06-11T15:26:06.587837Z
---

# SEM-229 — Temporal Ordering, Causality, And Window Semantics

## Statement

The ecosystem shall define explicit semantics for ordering, causality, simultaneity, deadlines, time windows, and timestamp interpretation independent of backend-local scheduler behavior.

## Rationale

Distributed simulation and temporal assertion systems repeatedly show that causality and temporal ordering need stronger semantics than raw timestamps alone provide.
