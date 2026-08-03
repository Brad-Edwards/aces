---
id: ASR-502
title: "Backend Conformance Suite And Fixture Corpus"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:40:05.368711Z
updated_at: 2026-07-24T17:48:24.012369Z
---

# ASR-502 — Backend Conformance Suite And Fixture Corpus

## Statement

The ecosystem shall provide a backend conformance suite and fixture corpus that can validate backend behavior and manifest claims against the published contracts.

## Rationale

Implemented and verified. The repository-owned backend conformance runner and CLI resolve the normative contracts/fixtures and contracts/profiles/backend corpus through the shared packaged-resource/source-checkout corpus loader. Fixture, manifest-claim, capability-gap, live-target behavior, seeded-violation, and installed-wheel tests provide executable conformance evidence.

## Traceability

- CONSTRAINS → ADR `ADR-009` (Normative Artifact Authority and Repository Structure)
- DOCUMENTS → DOCUMENTATION `contracts/README.md` (Contracts Overview)
- CONSTRAINS → SPEC `contracts/profiles/backend/provisioning-only.json` (Provisioning Only Profile)
- CONSTRAINS → SPEC `contracts/profiles/backend/orchestration-evaluation.json` (Orchestration Evaluation Profile)
- CONSTRAINS → PROOF `contracts/fixtures/control-plane/workflow-result-envelope-v1/invalid/pending-with-outcome.json` (Workflow Result Invalid Fixture)
- TESTS → TEST `implementations/python/tests/test_runtime_conformance.py` (Runtime Conformance Tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/runner.py` (Backend Conformance CLI Delegate)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_cli/conformance.py` (aces conformance backend Typer Subcommand)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/backend_profiles.py` (BackendProfileModel + Loader Authority)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/backend-conformance.md` (Backend Conformance Architecture Reference)
- CONSTRAINS → SPEC `contracts/schemas/profiles/backend-profile-v1.json` (Backend Profile v1 Published JSON Schema)
- CONSTRAINS → SPEC `contracts/profiles/backend/orchestration-capable.json` (Orchestration Capable Profile)
- CONSTRAINS → SPEC `contracts/profiles/backend/full-remote-control-plane.json` (Full Remote Control Plane Profile)
- TESTS → TEST `implementations/python/tests/test_backend_profiles.py` (Backend Profile Authority Tests)
- TESTS → TEST `implementations/python/tests/test_backend_conformance_cli.py` (aces conformance backend CLI Tests)
- DOCUMENTS → GITHUB_ISSUE `RAESystem/rae#6` (ASR-502: Backend Conformance Suite And Fixture Corpus)
- IMPLEMENTS → GITHUB_ISSUE `RAESystem/rae#66` (Backend conformance suite and fixture corpus on the current contracts tree)
- IMPLEMENTS → GITHUB_ISSUE `RAESystem/rae#502` (Backend conformance end-to-end proof with seeded violations)
- IMPLEMENTS → PULL_REQUEST `RAESystem/rae#136` (Make published backend profiles the conformance authority)
- IMPLEMENTS → PULL_REQUEST `RAESystem/rae#553` (Add backend conformance proof tests with seeded violations)
- IMPLEMENTS → PULL_REQUEST `RAESystem/rae#543` (Ship the contract corpus as package data and add a versioned release line)
- IMPLEMENTS → PULL_REQUEST `RAESystem/rae#642` (Prove real snapshot mutation in provisioning-only backend conformance)
- CONSTRAINS → PROOF `contracts/fixtures/backend-manifest/backend-manifest-v2/valid/stub.json` (Backend Manifest v2 Valid Fixture)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance/profiles.py` (Backend conformance profile and canonical corpus-root resolution)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance/fixture_suite.py` (Backend fixture corpus conformance execution)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance/target.py` (Backend manifest-claim and target-conformance orchestration)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_conformance/conformance/target_probes.py` (Live backend behavior conformance probes)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_contracts/corpus.py` (Installed-distribution and source-checkout contract corpus resolution)
