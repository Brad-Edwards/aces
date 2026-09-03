---
id: SEC-001
title: "Vetted-Author-Only Conversation Surface"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
created_at: 2026-05-17T05:12:55.073843Z
updated_at: 2026-05-17T05:12:59.843642Z
---

# SEC-001 — Vetted-Author-Only Conversation Surface

## Statement

The repository's issue, pull-request, and discussion surfaces shall accept input only from vetted authors. Mechanism, scope, and lifetime of the control are operational details outside this requirement statement and outside any artifact change-controlled in this repository. Past content authored outside the vetted set shall be reviewed and curated where appropriate.

## Rationale

The repository's issue, pull-request, and discussion threads are consumed by both human maintainers and agent-assisted workflows that load historical thread content as context when responding to current work. Unrestricted authorship on those surfaces is a path for arbitrary external input to influence those downstream consumers; the requirement is the policy boundary that closes it.

## Traceability

- IMPLEMENTS → ADR `docs/decisions/adrs/adr-017-conversation-surface-hardening.md` (ADR-017: Conversation Surface Hardening)
- IMPLEMENTS → GITHUB_ISSUE `150`
- IMPLEMENTS → PULL_REQUEST `153` (PR #153 docs: harden conversation surface against external interaction)
