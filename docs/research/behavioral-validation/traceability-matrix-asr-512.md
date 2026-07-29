# ASR-512 Executable Behavioral Validation Matrix

Date: 2026-07-28.

Issue: #260.

Requirement: ASR-512.

ASR-512 requires executable validation probes for behavioral properties claimed
by scenarios, participants, workflows, or experiments. The repository
implements that capability through a subject-bound execution seam and
subject-specific claim, adapter, and evidence surfaces. This matrix records the
join, its incumbents, and their structural gates. It does not introduce a
portable universal probe contract, report, or truth algebra.

## Clause Matrix

| Clause | Executable implementation | Structural gate or evidence |
| --- | --- | --- |
| Support executable validation probes. | `BehavioralProbeCase` joins one exact subject, validated claim, digest-pinned probe implementation, finite input digest, and execution basis. `run_behavioral_validation_probe()` admits and invokes a trusted injected executor and returns a `BehavioralProbeResult` whose identities come only from that case. Existing target and realization conformance runners remain concrete adapters. | `test_behavioral_validation_probes.py::test_probe_result_joins_subject_claim_binding_execution_and_evidence` executes the join for every admitted subject kind. Existing target and realization conformance tests continue to cover their concrete execution boundaries. |
| Bind a probe to the behavioral property it evaluates. | The case carries the revisioned `BehavioralClaimBindingModel` beside `BehavioralProbeBinding`; its canonical digest covers the subject, complete claim, implementation identity and digest, capability refs, input, basis, and mutation posture. Before execution, the runner validates the claim against the canonical relation catalog and requires its left carrier to equal the admitted subject ref. It copies those admitted identities into the result. | `test_case_digest_changes_when_any_joined_identity_changes`, `test_unknown_claim_relation_fails_closed_before_execution`, `test_claim_for_another_subject_fails_closed_before_execution`, and the parameterized join test prove identity binding and pre-execution refusal. |
| Validate scenario claims. | A trusted scenario adapter supplies `subject_kind=scenario`, the stable scenario or snapshot ref, its admitted behavioral claim, and a subject-specific executor. Existing target conformance remains the concrete scenario execution adapter. | The scenario parameters of the join and subject-claim mismatch tests prove the enforced join and refusal boundary. `test_runtime_conformance.py::test_target_conformance_accepts_supplied_reference_scenario` covers the concrete target path. |
| Validate participant claims. | A trusted participant adapter supplies `subject_kind=participant`, its participant-local claim and observation boundary, and the existing lifecycle, execution, or conformance executor. The result cannot replace that participant ref or claim with executor-returned metadata. | The participant parameters of the join and subject-claim mismatch tests protect the property-to-result binding. `test_reference_backend_conformance.py::test_reference_target_drives_full_participant_probe_case_set` and the dishonest/no-op participant tests cover the concrete participant adapters. |
| Validate workflow claims. | A trusted workflow adapter supplies `subject_kind=workflow`, a workflow-scoped behavioral claim, and an executor that observes the governed step or window boundary. The result preserves the case claim rather than inferring truth from lifecycle success. | The workflow parameters of the join and subject-claim mismatch tests protect the property-to-result binding. Existing target-conformance and truth-result tests protect orchestration execution and the separate lifecycle/truth boundary. |
| Validate experiment claims. | A trusted experiment adapter supplies `subject_kind=experiment`, a study, run, or task ref, a catalog-valid claim, and an executor tied to its apparatus and evidence rules. The result binds actual evidence refs to that admitted finite case; owning experiment carriers retain the archive record. | The experiment parameters of the join and subject-claim mismatch tests protect the property-to-result binding. Behavioral-relation and validation-disclosure tests continue to protect the owning study claim and disclosure carriers. |
| Preserve the finite evidence boundary of a passing probe. | The case claim must pass `validate_behavioral_claim_binding()` before execution, so finite evidence cannot carry a universal quantifier. A passed result additionally requires at least one non-empty evidence reference identifier from this invocation. Existing `_bounded_conformance_claim()` remains the backend-report projection for finite conformance cases. | `test_unknown_claim_relation_fails_closed_before_execution`, `test_passed_probe_requires_evidence`, `test_passed_probe_rejects_blank_evidence_reference`, `test_behavioral_relations.py::test_claim_binding_rejects_bounded_evidence_promoted_to_universal_claim`, and the behavioral-claim policy gate protect the boundary. |
| Preserve capability, diagnostics, cleanup, and sensitive-data boundaries. | The runner refuses missing bound capabilities before execution, preserves executor-reported failures and structured diagnostics, requires verified cleanup and no residual state for mutating cases, and reduces executor exceptions to a stable code plus exception type without exception text. | `test_missing_executor_capability_fails_closed_before_execution`, `test_executor_reported_failure_is_preserved_without_synthetic_diagnostic`, `test_executor_diagnostic_is_preserved_and_downgrades_passed_outcome`, the cleanup/residual-state parameterized test, and `test_executor_failure_is_sanitized_and_fails_closed` cover the generic join. Existing realization and report tests retain deeper native mutation and report-redaction coverage. |

## Existing Authority

- ADR-066 separates observations from evidence.
- ADR-072 defines validation strength and validation-basis disclosure.
- ADR-079 defines proposition, assertion, probe-binding, and truth-result
  semantics.
- ADR-081 defines behavioral relations, finite evidence boundaries, assurance,
  limitations, and nonclaims.
- The issue #260 preflight records the implementation guardrails and package
  boundaries for future probe adapters.

## Nonclaims

- A passing finite probe does not establish coverage of all inputs or traces.
- A conformance case does not establish behavioral equivalence, bisimulation,
  participant strategy coverage, experiment validity, or proof.
- Process exit, HTTP success, operation completion, workflow completion, or an
  evidence reference alone does not decide a behavioral property.
- ASR-512 does not implement ASR-513 counterfactual or necessity validation, or
  ASR-514 determinism or stability validation.
