---
id: API-420
title: "Participant Implementation Identity, Capability, And Compatibility Manifest"
status: ACTIVE
type: INTERFACE
priority: MUST
created_at: 2026-04-05T02:10:21.639349Z
updated_at: 2026-05-29T01:20:49.639840Z
---

# API-420 — Participant Implementation Identity, Capability, And Compatibility Manifest

## Statement

The ecosystem shall define a participant-implementation manifest by which an agent, policy, script, human-control proxy, or comparable participant implementation declares its identity, supported participant contracts, supported decision-surface modes, tool and affordance expectations, compatibility surface, and declared constraints.

## Rationale

Current state: identified gap. Swappable participant implementations affect comparability and behavior just as processors and backends do, so they need their own declaration surface rather than being hidden inside backend or processor metadata.

## Traceability

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#129` (Participant implementation identity/capability/compatibility manifest, exposure conformance & implementation/exposure provenance (API-420, ASR-527, EXP-733))
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#343` (Participant Implementation Identity, Capability, And Compatibility Manifest (API-420))
- IMPLEMENTS → PULL_REQUEST `Brad-Edwards/aces#433` (Implement participant implementation manifest contracts)
- DOCUMENTS → GITHUB_ISSUE `Brad-Edwards/aces#129` (Participant implementation manifest, exposure conformance, and provenance)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts.py` (Participant implementation manifest and provenance contract models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/manifest_authority.py` (Participant manifest contract authority validators)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/versions.py` (Participant implementation contract version constants)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance.py` (Participant implementation contract conformance validators)
- TESTS → TEST `implementations/python/tests/test_participant_implementation_manifest.py` (Participant implementation manifest and provenance tests)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Runtime contract export tests)
- TESTS → TEST `implementations/python/tests/test_controlled_vocabularies.py` (Participant implementation controlled vocabulary tests)
- DOCUMENTS → ADR `ADR-041` (Participant Implementation Manifest and Provenance Surface)
- IMPLEMENTS → SPEC `contracts/schemas/participant-implementation-manifest/participant-implementation-manifest-v1.json` (Participant implementation manifest v1 JSON Schema)
