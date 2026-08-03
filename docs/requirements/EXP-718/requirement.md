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

- DOCUMENTS → GITHUB_ISSUE `aces-framework/aces-sdl#108` (Experiment: controlled randomness/seed preservation & treatment/controlled-variation design (EXP-718, 719))
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts/random_stream.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/random_stream_engine.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/random_stream_profiles.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts/experiment_run_stochastic.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts/experiment_apparatus.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts/experiment_run.py`
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/contracts/experiment_analysis.py`
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
- IMPLEMENTS → GITHUB_ISSUE `Brad-Edwards/aces#274` (Controlled Randomness And Seed Preservation (EXP-718))
