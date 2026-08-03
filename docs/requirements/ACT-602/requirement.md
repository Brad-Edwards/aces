---
id: ACT-602
title: "Executable Participant Behavior Model"
status: ACTIVE
type: FUNCTIONAL
priority: SHOULD
wave: 2
created_at: 2026-04-03T05:40:05.861982Z
updated_at: 2026-06-24T00:50:07.504068Z
---

# ACT-602 — Executable Participant Behavior Model

## Statement

The ecosystem shall define an executable participant behavior model that supporting backends can implement without altering SDL or runtime semantics.

## Rationale

Requirement inventory expansion. Participant behavior must be modeled portably rather than left as backend-local invention.

## Traceability

- IMPLEMENTS → ADR `docs/decisions/adrs/adr-067-participant-behavior-model.md` (ADR-067 Participant Behavior Model)
- IMPLEMENTS → SPEC `specs/formal/participant-behavior-model/README.md` (Formal participant behavior model specification)
- IMPLEMENTS → GITHUB_ISSUE `77` (Issue #77 - Participant behavior model)
- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (Runtime conformance regression for participant behavior binding)
- DOCUMENTS → SPEC `specs/formal/assurance-fulfillment.yaml` (ACT-602 assurance fulfillment evidence)
- IMPLEMENTS → GITHUB_ISSUE `204` (Issue #204 - Executable Participant Behavior Model)
