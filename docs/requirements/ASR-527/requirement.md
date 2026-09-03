---
id: ASR-527
title: "Participant Implementation Manifest And Exposure Conformance"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-04-05T02:10:41.830432Z
updated_at: 2026-05-29T01:20:49.639872Z
---

# ASR-527 — Participant Implementation Manifest And Exposure Conformance

## Statement

The ecosystem shall provide validation and conformance artifacts that verify participant-implementation manifest claims, participant-exposure handling, and run-level disclosure of participant implementations and their decision surfaces.

## Rationale

Current state: identified gap. Participant implementations should not be allowed to claim capabilities or receive hidden context without executable checks and disclosure discipline.

## Traceability

- TESTS → TEST `implementations/python/tests/test_participant_implementation_manifest.py` (Participant implementation conformance and invalid-fixture tests)
- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (Runtime conformance registration tests)
- DOCUMENTS → ADR `ADR-041` (Participant Implementation Manifest and Provenance Surface)
- IMPLEMENTS → SPEC `contracts/schemas/participant-implementation-manifest/participant-implementation-manifest-v1.json` (Participant implementation manifest v1 JSON Schema)
- IMPLEMENTS → SPEC `contracts/schemas/participant-implementation-provenance/participant-implementation-provenance-v1.json` (Participant implementation provenance v1 JSON Schema)
