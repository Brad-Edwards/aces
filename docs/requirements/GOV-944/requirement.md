---
id: GOV-944
title: "Complete RAES ecosystem naming cutover"
status: DRAFT
type: CONSTRAINT
priority: MUST
created_at: 2026-07-26T16:10:02.534758Z
updated_at: 2026-07-26T16:10:02.534758Z
---

# GOV-944 — Complete RAES ecosystem naming cutover

## Statement

Every tracked live or current repository-owned surface shall use RAES naming across prose, source identifiers, published contracts and schemas, wire values, runtime artifacts, environment and workflow keys, specifications, tools, examples, and configuration. The retired project identity may remain only in content whose purpose is to preserve an immutable or dated historical fact. Repository verification shall scan the complete tracked tree and fail on any retired naming occurrence outside those semantically historical records.

## Rationale

Issue 908 is the terminal ecosystem naming cutover. Earlier rename requirements intentionally left governed contracts, artifacts, and workflow identifiers for later owners; this requirement closes those residual classes and prevents recurrence with a whole-repository structural gate.
