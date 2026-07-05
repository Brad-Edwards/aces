# ASR-511/ASR-515 Clause Matrix

Date: 2026-07-05

Issue: #97.

Requirements: ASR-511, ASR-515.

This matrix maps the joint validation/admission profile design to the durable
documentation artifacts and incumbent structural gates. It is a docs/spec
acceptance artifact for ADR-071; it does not add new contract, schema, fixture,
runtime, storage, API, or validator behavior.

## Matrix

| Requirement | Clause | Design Artifact | Structural Gate Or Evidence |
|-------------|--------|-----------------|-----------------------------|
| ASR-511 | Define layered validation/admission profiles. | ADR-071 decision 1; formal spec `Validation Profile` and `Strength Class` definitions. | `tools/check_repo_policy.py` and `tools/check_authority_boundary.py` keep the taxonomy in governed authority roots. |
| ASR-511 | Distinguish structural validity claims. | ADR-071 decision 1; formal spec `structural` strength definition and invariants 1-3. | Existing schema and closed-world validation surfaces remain the structural floor; no new schema is published by this issue. |
| ASR-511 | Distinguish semantic validity claims. | ADR-071 decision 1; formal spec `semantic` strength definition and invariants 3-4, 15. | Existing SDL semantic validation and experiment-core validators remain the semantic authority; this issue records the taxonomy only. |
| ASR-511 | Distinguish behavioral validity/admission claims. | ADR-071 decisions 1 and 4; formal spec `behavioral` strength definition and invariants 4, 11-14, 19. | Existing participant action admission and conformance surfaces stay separate; no participant admission field is overloaded. |
| ASR-511 | Distinguish stronger validity claims. | ADR-071 decision 1; formal spec `evidence_backed` and `falsification_backed` definitions and invariants 5-6. | ADR-021 remains the falsification-status authority; experiment-core evidence/provenance surfaces remain the evidence chain. |
| ASR-511 | Keep profile terms governed and unambiguous. | ADR-071 decisions 2 and 6; formal spec `Validation Profile` and authority-separation invariants. | Requirement governance and authority-boundary checks run under `ACES_REQUIREMENT_UID=ASR-511`. |
| ASR-515 | Preserve and expose the profile used for a claim. | ADR-071 decisions 2-3; formal spec `Validation-Basis Disclosure` fields. | The clause matrix and formal spec require profile id/version on every disclosure. |
| ASR-515 | Preserve and expose achieved strength. | ADR-071 decisions 1, 3, and 5; formal spec strength ordering and disclosure-completeness invariants. | The formal invariants forbid implied strength escalation from schema presence or omitted weak gates. |
| ASR-515 | Preserve and expose limitations. | ADR-071 decision 5; formal spec invariants 8-10 and 20-21. | The design requires weaker, redacted, withheld, unsupported, or unknown basis to be explicit and safely publishable. |
| ASR-515 | Apply the disclosure basis to scenarios, tasks, runs, and studies. | ADR-071 decision 3; formal spec carrier reuse invariants 15-18. | Existing SDL and experiment-core authority points are reused; no scenario/task/run/study super-model is added. |
| ASR-515 | Prevent confusion with adjacent profile/admission concepts. | ADR-071 decisions 4 and 6; formal spec authority-separation invariants 11-14. | The design explicitly excludes semantic profiles, backend profiles, instantiation profiles, realization support, feature support, and participant action admission as validation-profile carriers. |

## Non-Goals Checked

- No published JSON Schema.
- No Python contract model or validator.
- No fixture corpus changes.
- No runtime, processor, backend, HTTP API, persistence, UI, evidence store, or
  conformance-runner behavior.
- No changes to participant action admission, semantic profiles, backend
  profiles, SEM-218 realization support, or API-407 feature support.
