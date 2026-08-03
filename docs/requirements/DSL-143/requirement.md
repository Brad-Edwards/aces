---
id: DSL-143
title: "Enterprise Identity And Deployment-Tenancy Semantics"
status: DRAFT
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-07-24T03:15:18.446277Z
updated_at: 2026-07-24T03:15:18.446277Z
---

# DSL-143 — Enterprise Identity And Deployment-Tenancy Semantics

## Statement

The language shall represent enterprise identity forests and typed federation, endpoint personas, logical-node carrier placement and kernel boundaries, deployment-cell isolation intent, and shared-service tenant, workload-authentication, mutable-state, and reset-generation ownership as governed provider-neutral authoring semantics, with composition-safe references and fail-closed validation, without embedding provider allocation data, credentials, concrete application mapper configuration, or duplicating logical topology.

## Rationale

Downstream dense enterprise ranges need to preserve logical scenario identity while realizing real directory authority, packed hosts, bounded deployment cells, and shared compute. Existing domain, runtime directory, network-namespace, and orchestration inventories cover adjacent facts but cannot express the complete authored authority and tenant-isolation contract without ungoverned prose or provider-specific duplication.

## Traceability

- DOCUMENTS → SPEC `specs/sdl/enterprise-deployment-tenancy.md` (Enterprise Identity and Deployment Tenancy)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-087-enterprise-identity-and-deployment-tenancy-authoring.md` (ADR-087: Enterprise Identity and Deployment-Tenancy Authoring)
- DOCUMENTS → GITHUB_ISSUE `857` (Add enterprise identity and deployment-tenancy semantics to SDL)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/lineage.md` (SDL Lineage and Prior Work)
