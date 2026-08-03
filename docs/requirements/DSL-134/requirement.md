---
id: DSL-134
title: "Application-Internal Authorization Runtime Inventory"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-05-30T06:20:59.439789Z
updated_at: 2026-05-30T06:21:52.872349Z
---

# DSL-134 — Application-Internal Authorization Runtime Inventory

## Statement

The language shall represent application-internal authorization state as a typed node-scoped runtime inventory primitive referenced by datastore and platform surfaces, including principals (users, service accounts, API keys, backend roles) with credential classification, roles, resource-scoped permission grants keyed on a declared resource vocabulary, role mappings, tenants, and an auth-enabled posture, held to a guard requiring at least one matching grant per declared vocabulary member, without overloading operating-system local identity, wire-protocol directory identity authorities, the relational grant model, or prose-only relationships.

## Rationale

Application-internal RBAC is the single highest-recurrence SCN-010 expressivity gap (8+ sites: OpenSearch security plugin internal_users/roles/role-mappings, Cassandra system_auth, Redis ACL, MISP/TheHive/Cortex orgs-users-api-keys-roles). runtime.identity is OS /etc only; identity_authorities has no resource-scoped permission grant and presupposes a wire protocol these embedded stores lack; DatabaseGrant is closed to database|schema|table. Typing it per-app would fork ~8 divergent RBAC models — the exact divergence epic #439 forbids — so it is extracted once.

## Traceability

- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_app_authorization.py` (runtime_app_authorization.py)
- TESTS → TEST `implementations/python/tests/test_runtime_app_authorization.py` (test_runtime_app_authorization.py)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-046-app-authorization-runtime-inventory.md` (ADR-046 App Authorization Runtime Inventory)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#458` (PR #458)
