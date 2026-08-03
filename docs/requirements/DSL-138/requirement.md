---
id: DSL-138
title: "Typed Runtime Access Relationship Subtypes"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-05-30T06:21:19.646973Z
updated_at: 2026-05-30T06:21:57.589416Z
---

# DSL-138 — Typed Runtime Access Relationship Subtypes

## Statement

The language shall represent forwarding, service-integration, and reverse-proxy-upstream access relationships as typed relationship subtypes carrying domain-specific protocol, authentication-principal, identity-classification, and TLS-termination detail, with an upstream-target field on application routes and scenario-level cross-reference resolution and agreement validation, without collapsing those facts into untyped relationship properties.

## Rationale

The SCN-010 SOC stack is heavily integrated by API keys, log-forwarding enrollment, and reverse-proxy upstreams (wazuh-sidecars to manager, TheHive to Cortex, shuffle-frontend to backend, dashboard to indexer). A generic Relationship.properties dict cannot structurally validate enrollment-identity classification, enum sentinels, or cross-ref resolution — the same justification RelationshipDatabaseAccess and RelationshipMailAccess earned. RuntimeApplicationRoute has no upstream field.

## Traceability

- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/relationships.py` (Relationship typed subtype wiring)
- DOCUMENTS → ADR `docs/decisions/adrs/adr-052-typed-runtime-relationship-subtypes.md` (ADR-052 Typed Runtime Relationship Subtypes)
- TESTS → TEST `implementations/python/tests/test_runtime_forwarding_agent.py` (RelationshipForwardingEdge tests)
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#458` (PR #458)
