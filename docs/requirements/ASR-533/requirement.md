---
id: ASR-533
title: "Repository Claim Evidence Registry"
status: DRAFT
type: NON_FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-05-18T04:51:02.904198Z
updated_at: 2026-05-18T04:51:02.904198Z
---

# ASR-533 — Repository Claim Evidence Registry

## Statement

The ecosystem shall maintain a repository-owned, machine-readable claim evidence registry that records major architecture and maturity claims, evidence gate references, current evidence status, protocol references, evidence artifact references or digests, version and run context, known limitations, invalidation conditions, and related requirements, ADRs, and issues.

## Rationale

ASR-530 establishes that major claims remain unproven until falsification protocols and evidence artifacts demonstrate them. To make that durable and reviewable, the evidence state must live in the repository as a governed artifact rather than only in issue comments, paper drafts, or transient external analysis. Large raw artifacts may live outside Git, but the registry should preserve the claim, status, references, digests, and limits needed for reproducible maturity summaries and papers.
