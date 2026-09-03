---
id: ASR-532
title: "Runtime Backend Result Integrity"
status: DRAFT
type: NON_FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-05-18T04:25:47.598518Z
updated_at: 2026-08-19T00:00:00Z
---

# ASR-532 — Runtime Backend Result Integrity

## Statement

The runtime shall validate backend results at the execution boundary and reject
or sanitize results that violate RAE-owned portable contracts, plan authority,
runtime-domain ownership, or snapshot-transition invariants. Rejections shall
preserve the trusted predecessor state and identify the violated invariant with
structured diagnostics.

## Rationale

ADR-004 and ADR-036 assign backend invocation and result validation to the RAE
runtime. Issue #158 characterizes that boundary with controlled result
perturbations. Certification of external backend implementations, verification
of backend manifest truthfulness, infrastructure observation, malicious-backend
containment, and comprehensive backend acceptance testing remain outside this
requirement.
