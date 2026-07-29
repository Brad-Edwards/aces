# ASR-514 Determinism And Stability Verification Matrix

Date: 2026-07-29.

Issue: #262.

Policy UID: ASR-514.

Issue #262 requires the ecosystem to support verification of determinism,
stability, or replay-consistency where repeatability claims are made. Following
the binding architecture preflight, determinism and replay-consistency claims
bind existing behavioral relations rather than a new one, so no catalog
revision changes. The implementation adds only the executable join that has no
portable home: one bounded comparator over a single binary baseline-to-repetition
pair of one held-fixed subject, under the exact `canonical-artifact-identity`
relation. The claim's two carriers name the two compared projected artifacts,
and a larger set of repeated runs composes as several pairwise cases rather than
one n-ary comparison. The comparator does not schedule, replay, canonicalize
runs, execute, or persist; it consumes already-admitted typed runs and evidence,
and every projection, variation, reset, and cleanup fact is derived by a
digest-pinned validator and resolved through the exact run traceability. Case
and verification-record identities use the repository JCS canonical digest, and
diagnostics use a fixed JSON-Pointer address.

## Clause Matrix

| Clause | Executable implementation | Structural gate or evidence |
| --- | --- | --- |
| Verify a repeatability claim over admitted repeated executions. | `RepeatabilityConsistencyCase` binds one revisioned repeatability claim to an exact subject, a baseline and a repetition `RepetitionRef`, an observation projection, a versioned criterion, a variation policy, required capabilities, and a validator authority; its JCS `digest` seals every join input. `assemble_repeatability_consistency_evidence()` invokes the digest-pinned validator and `compare_repeatability_consistency()` returns a distinct `consistent`, `divergent`, `inconclusive`, or `unsupported` result. | `test_verified_equal_pair_is_consistent`, `test_divergent_projected_outcomes_refute_without_execution_failure`, and `test_case_digest_changes_for_every_join_identity`. |
| Bind the claim to an existing relation whose carriers name the compared artifacts. | The comparator admits only `SUPPORTED_REPEATABILITY_RELATION_IDS` (`canonical-artifact-identity`) and requires the claim's left and right carriers to equal the baseline and repetition `projected_artifact_ref` and the projection to match, then calls `validate_behavioral_claim_binding()` against the catalog revision without weakening it. No catalog relation, revision, or schema is added. | `test_claim_binds_the_existing_canonical_artifact_identity_relation`, `test_claim_carriers_must_identify_the_baseline_and_repetition_artifacts`, `test_wrong_relation_or_stale_catalog_coordinate_fails_before_comparison`, and `test_non_finite_claim_boundary_is_not_interpreted_by_the_comparator`. |
| Require a distinct, lineage-preserving repetition of the same subject. | `RepeatabilityConsistencyCase._validate_pair()` requires distinct `run_ref` and `projected_artifact_ref` values and a subject held fixed by ref and digest (ADR-068 distinct-run identity, not a retry). The assembler revalidates each run against its task and matches run, snapshot, and digest identities. | `test_case_requires_a_distinct_lineage_preserving_pair`, `test_assembler_rejects_a_side_that_does_not_match_the_typed_run`, and `test_assembler_runs_the_canonical_task_run_validator`. |
| Require a declared variation policy. | `VariationPolicy` names held-fixed dimensions and permitted variation. The assembler derives the variation disposition through the admitted validator and independently computes every observed variation not permitted by the policy; any unpermitted observed variation leaves the comparison inconclusive. | `test_variation_reset_and_cleanup_gates_fail_closed`, `test_unpermitted_observed_variation_makes_the_pair_incomparable`, and `test_variation_verification_must_match_the_declared_policy`. |
| Require reset, isolation, and absence of residue. | `ResetVerificationRecord` and `CleanupVerificationRecord` carry only run-bound refs; the admitted validator derives their dispositions. A comparison is not consistent without verified reset, verified cleanup, run-resolved evidence, and an empty residual-state set. | `test_variation_reset_and_cleanup_gates_fail_closed`, `test_unsupported_verification_disposition_remains_unsupported`, and `test_diagnostics_use_a_stable_json_pointer_address_and_hide_untrusted_values`. |
| Decide identity and divergence correctly. | Once every gate passes, an equal baseline and repetition projected digest yields `consistent`; an unequal pair yields `divergent` and refutes the finite claim without reporting an execution failure. Unsupported or indeterminate projected outcomes remain `unsupported` or `inconclusive`. | `test_verified_equal_pair_is_consistent`, `test_divergent_projected_outcomes_refute_without_execution_failure`, `test_indeterminate_projected_outcome_is_inconclusive`, and `test_unsupported_projected_outcome_remains_unsupported`. |
| Bind claim, subject, projection, criterion, capabilities, and evidence exactly. | Admission resolves the supported relation and criterion, matches the claim carriers to the artifacts and projection, checks required capabilities, and matches the sealed evidence to the case digest and admitted pair. The assembler pins the validator to the case authority, resolves each projected observation through the exact run traceability, and joins each variation, reset, and cleanup record to an admitted pair run. | `test_unsupported_criterion_is_rejected_before_comparison`, `test_missing_comparator_capability_fails_before_evidence_interpretation`, `test_case_digest_mismatch_is_rejected_before_comparison`, `test_comparator_rejects_pair_evidence_mismatch_in_sealed_evidence`, `test_assembler_rejects_validator_outside_the_case_authority_pin`, `test_assembler_rejects_projection_evidence_from_the_other_run`, and `test_assembler_rejects_verification_evidence_outside_the_pair`. |
| Preserve security and disclosure boundaries. | Direct `RepeatabilityConsistencyEvidence` construction is blocked and assembled values carry a module-owned authenticity token rechecked by the comparator. Caller-constructible verification inputs contain no disposition, binding, or digest. The host-owned admitted adapter derives projections and dispositions, the assembler computes record digests with the JCS canonical helper and preserves authority identity, and the comparator rechecks the preserved identities. Neither layer performs import selection, command dispatch, environment lookup, filesystem access, secret binding, logging, or persistence. Diagnostics use a fixed JSON-Pointer address and coarse messages; unmatched values and raw evidence are never rendered. | `test_comparison_evidence_cannot_be_constructed_directly`, `test_comparator_rejects_an_unsealed_copy_of_assembled_evidence`, `test_comparator_rejects_authority_mismatch_in_sealed_evidence`, `test_verification_inputs_cannot_assert_disposition_binding_or_digest`, and `test_diagnostics_use_a_stable_json_pointer_address_and_hide_untrusted_values`. |

## Existing Authority Reused

- ADR-066 separates observations, evidence, and derived results.
- ADR-068 owns repeated runs, replication, and replay claims; a genuine
  re-execution has a distinct run identity, and an idempotent retry is not a
  replicate.
- ADR-072 owns validation strength and disclosure.
- ADR-081 owns behavioral-relation meaning and claim discipline.
- ADR-084 owns deterministic trial realization and controlled randomness.
- `canonical-artifact-identity` remains the exact-identity relation; the
  comparator adds only the baseline-to-repetition admission around it and never
  reinterprets the binary relation as n-ary.
- The ASR-513 `necessity_evidence` discipline is reused for the digest-pinned
  validator authority, typed run and evidence joins, assembler-owned facts, and
  stable diagnostics; the shared neutral primitives are promoted into
  `verification_authority`, and no necessity concept is imported.
- The repository JCS canonical digest (`canonical_json_digest`) computes case and
  verification-record identities; no local serializer is introduced.

## Trust Boundary

The comparator is a trusted-composition-only surface, invoked by code that owns
the validator authority and the case. The module assembly token is integrity
defense-in-depth against accidental or unsealed construction, not access control
against a caller already trusted to drive the comparator. Each evidence
reference is bound to the digest-verified run's declared evidence set; because
the experiment-run traceability model does not admit per-evidence content
digests and this comparator adds no evidence store, content authenticity of an
individual evidence record remains owned by the platform evidence provenance and
resolution layer that supplies the records.

## Nonclaims

- A consistent result applies only to the exact finite pair, subject,
  observation projection, variation policy, and equality criterion.
- A shared seed, a reused task identifier, wall-clock proximity, an exit or run
  status, a retry, or a completed replay does not establish repeatability.
- The result does not establish universal determinism, statistical equivalence,
  trace equivalence, bisimulation, backend equivalence, necessity, experiment
  validity, proof, or falsification-backed strength.
- Statistical stability under controlled variation and participant-history
  replay are separate criteria bound to `statistical-equivalence` or
  `participant-projected-history-equivalence`; the shipped criterion decides
  exact canonical projected-outcome identity only.
- The comparator does not construct, schedule, or execute repetitions. Ordinary
  parsing, semantic admission, authorization, capability, execution, evidence,
  reset, and cleanup boundaries remain with their owning layers.
