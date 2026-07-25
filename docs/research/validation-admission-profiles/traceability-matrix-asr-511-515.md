# ASR-511/ASR-515 Clause Matrix

Date: 2026-07-05 (ASR-515 rows updated 2026-07-24, issue #259).

Issue: #97 (design). Executable coverage: #258 (ASR-511), #259 (ASR-515).

Requirements: ASR-511, ASR-515.

This matrix maps the joint validation/admission profile design to the durable
documentation artifacts and incumbent structural gates. Issue #97 itself is a
docs/spec acceptance artifact for ADR-072 that added no contract, schema,
fixture, runtime, storage, API, or validator behavior. Issue #259 subsequently
delivered the executable ASR-515 validation-basis disclosure contract,
published schema, fixture corpus, and test suite; the ASR-515 rows below now
point at that concrete structural gate instead of the design-only artifact.

## Matrix

| Requirement | Clause | Design Artifact | Structural Gate Or Evidence |
|-------------|--------|-----------------|-----------------------------|
| ASR-511 | Define layered validation/admission profiles. | ADR-072 decision 1; formal spec `Validation Profile` and `Strength Class` definitions. | `tools/check_repo_policy.py` and `tools/check_authority_boundary.py` keep the taxonomy in governed authority roots. |
| ASR-511 | Distinguish structural validity claims. | ADR-072 decision 1; formal spec `structural` strength definition and invariants 1-3. | Existing schema and closed-world validation surfaces remain the structural floor; no new schema is published by this issue. |
| ASR-511 | Distinguish semantic validity claims. | ADR-072 decision 1; formal spec `semantic` strength definition and invariants 3-4, 15. | Existing SDL semantic validation and experiment-core validators remain the semantic authority; this issue records the taxonomy only. |
| ASR-511 | Distinguish behavioral validity/admission claims. | ADR-072 decisions 1 and 4; formal spec `behavioral` strength definition and invariants 4, 11-14, 19. | Existing participant action admission and conformance surfaces stay separate; no participant admission field is overloaded. |
| ASR-511 | Distinguish stronger validity claims. | ADR-072 decision 1; formal spec `evidence_backed` and `falsification_backed` definitions and invariants 5-6. | ADR-021 remains the falsification-status authority; experiment-core evidence/provenance surfaces remain the evidence chain. |
| ASR-511 | Keep profile terms governed and unambiguous. | ADR-072 decisions 2 and 6; formal spec `Validation Profile` and authority-separation invariants. | Requirement governance and authority-boundary checks run under `ACES_REQUIREMENT_UID=ASR-511`. |
| ASR-515 | Preserve and expose the profile used for a claim. | ADR-072 decisions 2-3; formal spec `Validation-Basis Disclosure` fields; `ValidationBasisDisclosureModel.profile_id`/`profile_version` (`implementations/python/packages/aces_contracts/contracts/validation_disclosure.py`). | `ValidationBasisDisclosureModel`'s model validator resolves the exact `(profile_id, profile_version, subject_kind)` triple via `select_validation_profile()` and fails closed on an unknown identity; `implementations/python/tests/test_validation_disclosure.py::test_disclosure_fails_closed_for_unknown_profile_identity`. |
| ASR-515 | Preserve and expose achieved strength. | ADR-072 decisions 1, 3, and 5; formal spec strength ordering and disclosure-completeness invariants; `ValidationBasisDisclosureModel.achieved_strength` and the ADR-072 cumulative gate-ordering tables. | The `_validate_strength_ordering` cross-row check requires every ADR-072-ordered gate for the claimed strength to be an actual `passed` row (structural never implies semantic; semantic never implies behavioral); `test_structural_rows_cannot_claim_semantic_strength`, `test_semantic_rows_cannot_claim_behavioral_strength`, `test_evidence_backed_requires_at_least_one_evidence_ref`, `test_falsification_backed_requires_protocol_and_status_passed`. |
| ASR-515 | Preserve and expose limitations. | ADR-072 decision 5; formal spec invariants 8-10 and 20-21; `ValidationLimitationModel` and the required-gate/`not_applicable`/sub-minimum/audience-restricted limitation checks. | `_validate_required_gate_failures_capped`, `_validate_not_applicable_gates_disclosed`, `_validate_minimum_strength_not_silently_below`, and `_validate_audience_restriction_disclosed` each fail closed without an explicit limitation; `test_required_gate_failure_requires_explicit_limitation`, `test_not_applicable_gate_requires_explicit_limitation`, `test_sub_minimum_strength_is_legal_only_with_explicit_limitation`, `test_audience_restricted_view_requires_audience_restricted_limitation`. |
| ASR-515 | Apply the disclosure basis to scenarios, tasks, runs, and studies. | ADR-072 decision 3; formal spec carrier reuse invariants 15-18; `ExperimentTaskModel.validation_basis_disclosures`, `ExperimentRunModel.validation_basis_disclosures`, `ExperimentStudyModel.validation_basis_disclosures`. | Scenario/scenario-snapshot subjects are referenced by existing stable identity/digest via `ValidationSubjectReferenceModel`; task/run/study carriers embed the disclosure and cross-check `subject_kind`/`subject_ref` against the carrier's own identity via `validate_carrier_validation_basis_disclosures()`; `test_experiment_task_accepts_matching_validation_basis_disclosure`, `test_experiment_task_rejects_disclosure_with_mismatched_subject_ref`, `test_experiment_task_rejects_disclosure_with_mismatched_subject_kind`. |
| ASR-515 | Prevent confusion with adjacent profile/admission concepts. | ADR-072 decisions 4 and 6; formal spec authority-separation invariants 11-14. | The disclosure contract adds no field to `ParticipantActionAdmissionRequest`/`admission_disposition`, semantic profiles, backend profiles, or instantiation profiles; `select_validation_profile()` is the only profile-use join, never a second loader or carrier-specific enum. |

## Non-Goals Checked (issue #97, design phase)

- No published JSON Schema.
- No Python contract model or validator.
- No fixture corpus changes.
- No runtime, processor, backend, HTTP API, persistence, UI, evidence store, or
  conformance-runner behavior.
- No changes to participant action admission, semantic profiles, backend
  profiles, SEM-218 realization support, or API-407 feature support.

## Executable Coverage (issue #259)

Issue #259 (ASR-515) delivered the following executable artifacts, referenced
by the ASR-515 rows above:

- Contract: `implementations/python/packages/aces_contracts/contracts/validation_disclosure.py`
  (`ValidationBasisDisclosureModel`, `ValidationBasisDisclosureDocumentModel`,
  `ValidationGateResultModel`, `ValidationLimitationModel`,
  `ValidationSubjectReferenceModel`, `ValidationProducerReferenceModel`).
- Published schema: `contracts/schemas/profiles/validation-basis-disclosure-v1.json`,
  with a matching change-ledger entry under `contracts/schema-publication/entries/`.
- Fixture corpus: `contracts/fixtures/profiles/validation-basis-disclosure-v1/{valid,invalid}/`.
- Conformance registration: `aces_conformance/conformance/validators.py`.
- Carrier embedding: optional `validation_basis_disclosures` fields on
  `ExperimentTaskModel`, `ExperimentRunModel`, `ExperimentStudyModel`.
- Tests: `implementations/python/tests/test_validation_disclosure.py`.

This remains a contract-only surface: no endpoint, store, service, event
stream, or admission field was added. Participant action admission,
conformance execution, SDL parsing/semantic validation, and evidence capture
remain the separate authorities the disclosure only references.
