---
id: DSL-140
title: "Scenario-Level Off-Node Forwarding Agents"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-05-31T17:31:13.228730Z
updated_at: 2026-05-31T17:36:43.068812Z
---

# DSL-140 — Scenario-Level Off-Node Forwarding Agents

## Statement

The language shall represent off-node log-forwarding and content-synchronization agents as scenario-level forwarding-agent records when the forwarder is infrastructure realization rather than an inventoried scenario node, reuse RuntimeForwardingAgent rather than introducing a sidecar-specific schema, allow RelationshipForwardingEdge.forwarder_ref to resolve across node-hosted and scenario-level forwarding agents, require forwarding_agent_id uniqueness across both registries, and validate scenario-level ship target node and service references without weakening unresolved-reference diagnostics.

## Rationale

Issue #460 blocks APTL TechVault SDL reconciliation because Wazuh sidecar containers for PostgreSQL and Suricata are real forwarders but are not scenario participants with inventory bundles. Hoisting those agents onto the source node or manager node asserts false runtime ownership, while adding sidecars as top-level nodes pollutes the scenario graph with infrastructure-only realization. A scenario-level registry preserves the typed forwarding-edge contract and avoids prose-only relationship properties.

## Traceability

- TESTS → TEST `implementations/python/tests/test_runtime_forwarding_agent.py` (Scenario-level forwarding agent parser and validator tests)
- IMPLEMENTS → GITHUB_ISSUE `460` (Runtime SDL: forwarding_edge cannot represent off-node sidecar forwarders)
