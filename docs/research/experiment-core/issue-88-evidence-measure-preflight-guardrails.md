# Issue #88 Evidence And Measure Preflight Guardrails

Date: 2026-06-21

Issue: #88.

Requirements: EXP-707, EXP-708, EXP-709, EXP-715.

The architecture preflight confirmed that ADR-055,
`specs/formal/experiment-core/README.md`, and
`docs/research/experiment-core/preflight-guardrails.md` already cover the
EXP-701 through EXP-705 boundary. Issue #88 adds only the evidence and measure
contract extension described below.

## Binding Guardrails

- Keep EXP-707 as a declarative capture specification: it records what evidence
  should be captured, not runtime capture, storage, or collection success.
- Keep EXP-708 as raw captured observations/artifacts: evidence records carry
  raw content references or bounded summaries, sensitivity, redaction state,
  loss disclosure, and provenance.
- Keep EXP-709 as derived measures/evaluations: derived measures cite source
  evidence records and carry method, value status, value, uncertainty,
  limitations, and provenance.
- Keep EXP-715 as a backend capability declaration in the existing manifest,
  profile, concept-authority, and conformance stack.
- Do not implement runtime capture, retention, persistence, HTTP APIs,
  schedulers, statistical engines, packet/log parsers, or new SDL syntax in
  issue #88.
- Do not collapse capture specs, raw evidence, and derived measures into one
  result blob or into existing run result summaries.

## Required Incumbents

- `implementations/python/packages/aces_contracts/contracts.py`,
  `versions.py`, `schema_bundle()`, and
  `tools/generate_contract_schemas.py`.
- `contracts/schemas/`, `contracts/fixtures/`, and
  `contracts/schema-publication-manifest.json`.
- `contracts/concept-authority/controlled-vocabularies-v1.json` and its
  fixture corpus for governed observation capability vocabularies.
- `aces_backend_protocols.capabilities`, `aces_backend_protocols.manifest`,
  backend profiles, and conformance checks.
- Existing ACES semantic invariant annotations and fixture validation tests.
