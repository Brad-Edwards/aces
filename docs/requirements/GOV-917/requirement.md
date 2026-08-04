---
id: GOV-917
title: "Canonical Concept Authority For Cyber-Domain Meaning"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 2
created_at: 2026-04-05T15:37:11.965668Z
updated_at: 2026-04-05T17:27:06.766943Z
---

# GOV-917 — Canonical Concept Authority For Cyber-Domain Meaning

## Statement

The ecosystem shall define a canonical concept authority for cyber-domain concepts used across SDL, manifests, contracts, provenance, reporting, and related ecosystem artifacts.

## Rationale

A shared concept authority is needed so ecosystem surfaces can point to the same meaning instead of repeating loosely aligned strings. Primary-source review suggests UCO is a strong candidate semantic spine for cyber-domain concepts, but the requirement is for explicit concept authority rather than ad hoc artifact-local definitions.

## Traceability

- DOCUMENTS → DOCUMENTATION `research/primary/reference-organizations/cdo-community/README.md` (CDO Community Sources)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/shared-concept-model.md` (Shared Concept Model)
- DOCUMENTS → DOCUMENTATION `docs/explain/reference/README.md` (Reference Notes)
- IMPLEMENTS → SPEC `specs/concept-authority/concept-authority.md` (Concept authority normative specification)
- IMPLEMENTS → SPEC `contracts/concept-authority/concept-families-v1.json` (Authoritative concept family catalog)
- IMPLEMENTS → SPEC `contracts/schemas/concept-authority/concept-families-v1.json` (Concept families JSON Schema v1)
- IMPLEMENTS → CODE_FILE `tools/generate_contract_schemas.py` (Schema generation routing for concept-families-v1)
- TESTS → TEST `implementations/python/tests/test_concept_authority.py` (Concept authority catalog tests)
- TESTS → TEST `implementations/python/tests/test_runtime_contracts.py` (Schema bundle and closed-world contract tests)
- CONSTRAINS → ADR `docs/decisions/adrs/adr-032-directory-domain-identity-runtime-surface.md` (ADR-032: Directory and Domain Identity Runtime Surface)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (Runtime identity authority parser and semantic reference tests)
- TESTS → TEST `implementations/python/tests/test_scenarios.py` (Identity authority scenario example load coverage)
- TESTS → TEST `implementations/python/tests/test_mcp_server.py` (SDL validation reference MCP documentation test)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/lineage.md` (SDL identity authority lineage and literature basis)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/precedents.md` (SDL identity authority design precedents)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/sections.md` (SDL identity authority authoring reference)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/validation.md` (SDL identity authority validation reference)
- DOCUMENTS → DOCUMENTATION `docs/explain/sdl/limitations.md` (SDL identity authority limitations and validation scope)
- VERIFIES → RISK_SCENARIO `examples/scenarios/hospital-ransomware-surgery-day.sdl.yaml` (Hospital AD and ADFS identity authority scenario example)
- DOCUMENTS → DOCUMENTATION `changelog.d/401.added.md` (Issue 401 identity authority changelog fragment)
- DOCUMENTS → DOCUMENTATION `docs/index.md` (Documentation navigation for ADR-032 identity authority decision)
- IMPLEMENTS → SPEC `contracts/concept-authority/uco-alignment-v1.json` (UCO alignment evidence catalog (uco-alignment-v1))
- IMPLEMENTS → SPEC `contracts/schemas/concept-authority/uco-alignment-v1.json` (UCO alignment JSON Schema v1)
- TESTS → TEST `implementations/python/tests/test_uco_alignment.py` (UCO alignment shape, coverage, version-pin, divergence and IRI tests)
- IMPLEMENTS → GITHUB_ISSUE `486` (GOV-917: Canonical Concept Authority For Cyber-Domain Meaning)
