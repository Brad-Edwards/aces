---
id: EXP-718
title: "Controlled Randomness And Seed Preservation"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 3
created_at: 2026-04-03T07:58:36.599973Z
updated_at: 2026-07-20T19:04:33.815488Z
---

# EXP-718 — Controlled Randomness And Seed Preservation

## Statement

The ecosystem shall support explicit specification and preservation of randomness controls, seeds, and comparable stochastic run inputs where experiment behavior or results depend on them.

## Rationale

Requirement inventory expansion. Repeatability and honest comparison require stochastic controls to be represented explicitly when they matter.

## Traceability

- IMPLEMENTS → SPEC `contracts/schemas/profiles/random-stream-profile-v1.json`
- IMPLEMENTS → SPEC `contracts/schemas/profiles/random-stream-vector-v1.json`
- IMPLEMENTS → CONFIG `contracts/profiles/random-stream/blake3-xof-v1.json`
- TESTS → TEST `implementations/python/tests/test_random_stream_contracts.py`
- TESTS → TEST `implementations/python/tests/test_random_stream_profile.py`
- TESTS → TEST `implementations/python/tests/test_random_stream_vectors.py`
- TESTS → TEST `implementations/python/tests/test_random_stream_collisions.py`
- TESTS → TEST `implementations/python/tests/test_random_stream_run_integration.py`
- TESTS → TEST `implementations/python/tests/test_random_stream_study_integration.py`
- TESTS → TEST `implementations/python/tests/test_random_stream_determinism.py`
