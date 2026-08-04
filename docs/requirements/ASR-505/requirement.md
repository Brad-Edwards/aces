---
id: ASR-505
title: "Classification-Based Assurance Policy"
status: ACTIVE
type: NON_FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-04-03T05:55:58.950578Z
updated_at: 2026-05-17T18:11:55.602909Z
---

# ASR-505 — Classification-Based Assurance Policy

## Statement

The ecosystem shall define a classification-based assurance policy that maps structural, semantic, graph, and stateful changes to proportionate verification artifacts.

## Rationale

Requirement inventory phase. Status audit deferred until the full canonical graph is complete.

## Traceability

- IMPLEMENTS → SPEC `specs/formal/assurance-policy.yaml` (Classification-based assurance policy (canonical machine-readable mapping))
- IMPLEMENTS → POLICY `tools/check_assurance_policy.py` (Structural gate validator for the classification-based assurance policy)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-018-classification-based-assurance-policy.md` (ADR-018: Canonical Mapping for the Classification-Based Assurance Policy)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-007-lightweight-formal-methods-policy.md` (ADR-007: Lightweight Formal Methods Policy (FM0/FM1/FM2/FM3 ladder; pre-existing policy decision))
- IMPLEMENTS → DOCUMENTATION `docs/explain/reference/coding-standards.md` (Coding Standards: contributor-facing classification ladder reference)
- IMPLEMENTS → DOCUMENTATION `docs/specs/formal.md` (Formal Specifications overview (FM Classification reference))
- IMPLEMENTS → CONFIG `noxfile.py` (nox verification graph (wires the assurance-policy gate into policy/verify/hook sessions))
- TESTS → TEST `implementations/python/tests/test_assurance_policy.py` (Unit tests for the assurance-policy validator (57 cases))
- IMPLEMENTS → DOCUMENTATION `docs/explain/reference/fm-classification-ledger.yaml` (FM classification ledger for ADR-023 through ADR-058)
- IMPLEMENTS → DOCUMENTATION `docs/decisions/adrs/TEMPLATE.md` (ADR template classification record fields)
- IMPLEMENTS → DOCUMENTATION `docs/explain/reference/shared-semantic-integrity.md` (Shared semantic integrity reference for FM classification ledger location and gate)
- IMPLEMENTS → SPEC `specs/formal/assurance-fulfillment.yaml` (Per-subsystem assurance fulfillment map (delivered/waived artifacts per classified formal domain))
- TESTS → TEST `implementations/python/tests/test_participant_runtime_invariants.py` (Participant runtime invariant oracle property tests)
- DOCUMENTS → SPEC `specs/formal/participant-runtime/README.md` (Participant runtime invariant oracle predicate mapping)
