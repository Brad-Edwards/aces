---
id: RUN-313
title: "Reference Processor Implementation"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T01:46:38.804844Z
updated_at: 2026-06-20T06:06:25.167437Z
---

# RUN-313 — Reference Processor Implementation

## Statement

The ecosystem shall provide a repository-owned reference processor implementation that realizes the normative processing model, published processor manifests, portable contracts, and applicable conformance expectations end to end.

## Rationale

Portable semantics and contracts need at least one concrete processor implementation that exercises the full processing path in executable form without making implementation code the sole normative authority.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#75` (Reference processor & backend implementations (RUN-313, RUN-314, RUN-315))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#196` (Reference Processor Implementation (RUN-313))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_processor/reference.py` (Reference processor assembly (ReferenceProcessor / run_reference_processor))
- TESTS → TEST `implementations/python/tests/test_reference_processor.py` (Reference processor end-to-end + manifest-evidence tests)
