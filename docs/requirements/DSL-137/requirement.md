---
id: DSL-137
title: "Orchestration Authority Runtime Inventory"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-05-30T06:21:14.941474Z
updated_at: 2026-05-30T06:21:56.176838Z
---

# DSL-137 — Orchestration Authority Runtime Inventory

## Statement

The language shall represent container-orchestration control-authority state as a typed node-scoped runtime inventory primitive, including a reference to the observed control interface, engine identity and API version, organizational and environment scope, spawn templates, lifecycle policy, realized child workloads, and privilege classification, held to a guard requiring a resolvable read-write control-interface reference for host-root-equivalent authorities, without overloading the anonymous control-interface mount shell, transport services, or prose-only relationships.

## Rationale

APTL SCN-010 shuffle-orborus (#355) and cortex (#357) hold the Docker socket and spawn ephemeral worker/analyzer containers; RuntimeControlInterface types the socket as a present read-write mount shell but carries no field for what the holder is authorized to do (spawn image X into scope Y under policy Z) and has no id to reference. This host-root-equivalent spawn authority is the defining and most security-relevant logical state of these nodes.

## Traceability

- TESTS → TEST `implementations/python/tests/test_runtime_orchestration.py` (test_runtime_orchestration.py)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-051-orchestration-authority-runtime-inventory.md` (ADR-051 Orchestration Authority Runtime Inventory)
