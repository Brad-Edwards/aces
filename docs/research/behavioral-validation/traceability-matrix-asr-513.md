# ASR-513 Counterfactual And Necessity Validation Matrix

Date: 2026-07-28.

Issue: #261.

Policy UID: ASR-513.

Issue #261 requires support for counterfactual or necessity-oriented
validation when RAES claims that a named condition, weakness, control, or
behavior is required for an outcome. The implementation provides one bounded
binary but-for criterion over already-admitted worlds and evidence. It does not
create a causal-model language, execute arbitrary interventions, or infer a
universal causal result.

## Clause Matrix

| Clause | Executable implementation | Structural gate or evidence |
| --- | --- | --- |
| Support counterfactual or necessity-oriented validation. | `BoundedButForCase` binds one revisioned `bounded-but-for-necessity` claim to exact candidate, outcome, baseline/intervention-world, immutable run/digest, intervention, criterion, matching-policy, capability, validator-authority, and input identities. `assemble_bounded_but_for_evidence()` invokes that exact digest-pinned adapter before `compare_bounded_but_for()` returns a distinct `supported`, `refuted`, `inconclusive`, or `unsupported` result. | `test_verified_true_to_false_comparison_supports_only_the_bounded_claim`, `test_case_digest_changes_for_every_causal_join_identity`, and the behavioral-catalog tests protect the positive join and canonical relation authority. |
| Require a true baseline outcome. | The admitted `NecessityEvidenceValidator` derives both existing closed `PropositionTruthResultModel` values from run-bound evidence. The assembler resolves every decided truth evidence ref through the exact `ExperimentEvidenceRecordModel`, its `run_ref`, and the world run's traceability. A false baseline produces `inconclusive`; unknown truth remains inconclusive and unsupported apparatus remains unsupported. | The false/unknown/unsupported tests distinguish truth from comparison status. The cross-world evidence, missing-run-traceability, and wrong-outcome-address tests prove the exact truth-to-run join. |
| Require a verified candidate intervention. | The case binds a closed `InterventionKind`, revisioned intervention identity and digest, and exact producer/validator authority. `InterventionVerificationRecord` carries only scoped run/evidence inputs; it has no caller-set disposition, binding, or digest. The admitted adapter derives the full disposition, while the assembler computes the canonical record digest and preserves the authority identity. | The intervention row of the gate test proves that failed verification cannot support the claim. The authority-pin, unsupported-disposition, wrong-verification-run, missing-verification-evidence, and direct-construction tests prove that caller booleans or free-form refs cannot enter the comparator. |
| Compare only admitted worlds with the declared difference. | `NecessityWorldRef` preserves distinct immutable world and run identities with one family and baseline lineage. `NecessityMatchingPolicy` names held-fixed dimensions and admitted differences; the admitted adapter derives matching disposition and the assembler independently retains every symmetric policy difference. | `test_case_rejects_reused_run_identity_and_unrelated_world_lineage`, `test_case_digest_mismatch_is_rejected_before_comparison`, and the comparability row of the gate test protect world identity and matching. |
| Require reset, cleanup, and absence of residue. | `CleanupVerificationRecord` binds only the counterfactual world, run, subject, evidence, and observed residue. The admitted adapter derives its full disposition. A comparison cannot support necessity without `VERIFIED`, run-resolved evidence, and an empty residual-state set; `UNSUPPORTED` remains distinct from `FAILED`. | The cleanup and residual-state rows of `test_intervention_comparability_and_cleanup_gates_fail_closed` and `test_unsupported_verification_disposition_remains_unsupported` protect the cross-world isolation boundary. |
| Interpret true-to-false and true-to-true correctly. | Once all gates pass, baseline true plus counterfactual false supports only the finite claim. Baseline true plus counterfactual true refutes that declared binary but-for claim; it is not an execution failure. | `test_verified_true_to_false_comparison_supports_only_the_bounded_claim` and `test_both_worlds_true_refutes_the_claim_without_reporting_execution_failure` cover both decided outcomes. |
| Bind relation, candidate, outcome, capabilities, and evidence exactly. | Admission calls `validate_behavioral_claim_binding()` against catalog revision `rev6`, requires `bounded-but-for-necessity`, and checks candidate/outcome carriers and capabilities. Before that boundary, the assembler calls `validate_experiment_run_against_task()`, authenticates the adapter against the case authority pin, matches case world/run/snapshot/digests, and resolves every truth and verification ref through the exact immutable run. | Wrong relation/stale coordinate, unsupported criterion, claim/case mismatch, case/evidence mismatch, case/run mismatch, invalid task/run, adapter-authority mismatch, cross-world evidence, missing traceability, wrong verification run, and missing-capability tests prove fail-closed admission. |
| Preserve security and disclosure boundaries. | Direct `BoundedButForEvidence` construction is blocked and assembled values carry a module-owned authenticity token rechecked by the comparator. Caller-constructible verification inputs contain no disposition or authority assertion. The host-owned admitted adapter derives truth and verification states, the assembler computes record digests, and the comparator rechecks the preserved authority identities. Neither layer performs import selection, command dispatch, environment lookup, filesystem access, secret binding, logging, or persistence. Diagnostics use stable codes and coarse fixed messages; unmatched values and raw evidence are never rendered. | The direct-construction, authority-pin, unsupported-disposition, and identity-preservation assertions protect provenance. `test_diagnostics_are_stable_and_do_not_echo_untrusted_values` protects redaction. Repository module, policy, source-size, and secret checks cover the package surface. |

## Existing Authority Reused

- ADR-022 separates causal attribution from temporal association.
- ADR-066 separates observations, evidence, and derived results.
- ADR-068 owns immutable experiment studies, runs, factors, assignments, and
  analysis.
- ADR-072 owns validation strength and disclosure.
- ADR-079 owns proposition truth and probe bindings.
- ADR-081 owns behavioral-relation meaning and claim discipline.
- ADR-084 owns admitted scenario-family variation.
- ASR-512 remains the per-world executable behavioral-probe boundary; its
  result is execution evidence, not a cross-world causal conclusion.

## Nonclaims

- A supported comparison applies only to the exact finite claim, worlds,
  intervention, apparatus, time/randomness policy, observation projection,
  evidence boundary, and matching policy.
- Replay, temporal order, correlation, a failed action, a no-op intervention,
  a negative fixture, or different outcomes from incomparable worlds do not
  establish necessity.
- The result does not establish actual causation, sufficiency, probabilistic or
  universal causation, determinism/stability, experiment validity, proof, or
  falsification-backed strength.
- The comparator does not construct or execute worlds. Ordinary parsing,
  semantic admission, authorization, capability, experiment execution,
  evidence, reset, and cleanup boundaries remain with their owning layers.
