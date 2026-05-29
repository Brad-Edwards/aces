# EXP-701 Through EXP-705 Literature Traceability Matrix

This matrix records the review-control pass for issue #87. It converts the
primary-literature and lineage criteria into explicit v1 commitments so future
review rounds can distinguish true contract gaps from future work.

## Source Families

- ML rigor: REFORMS, leakage, DOME, reproducibility reports, statistical
  comparison literature.
- Experiment metadata: OpenML, experiment databases, MEX, OntoDM, ontology of
  scientific experiments.
- Provenance and packaging: OPM, PROV rationale, FAIR, RO-Crate, CWLProv,
  Sumatra, ReproZip, noWorkflow.
- Cyber range and testbed research: DETER/CSET, cyber-range surveys,
  cross-testbed reproduction, VM/host verification metrics.
- Experiment design and V&V: empirical software engineering, simulation V&V,
  uncertainty quantification, computer experiment design.
- ACES lineage: `docs/explain/sdl/lineage.md`, especially benchmark,
  participant, runtime, time, causality, DSL, and apparatus sections.

## Classification Rules

- `v1 MUST`: the contract or formal spec currently makes, or should make, a
  conformance claim. It needs an enforcement point or a deliberate documented
  downgrade.
- `v1 SHOULD`: v1 must preserve a structured place for the evidence, but full
  semantic analysis is out of scope.
- `future/non-goal`: important to the research program, but not part of the
  EXP-701 through EXP-705 contract boundary.

## Criteria Matrix

| ID | Criterion | Literature/lineage basis | Classification | Enforcement or disposition |
| --- | --- | --- | --- | --- |
| EC-T01 | Scenario meaning, task protocol, run record, apparatus context, and study/collection must remain distinct. | OpenML, experiment databases, cyber-range scenario work, DSL lineage. | v1 MUST | Separate `experiment-task-v1`, `experiment-apparatus-context-v1`, `experiment-run-v1`, and `experiment-study-v1`; constrained reference models; formal separation invariants; regression tests for wrong reference kinds. |
| EC-T02 | Task records must bind scenario material to an evaluation protocol, metrics, unit of analysis, intended use, population/construct, leakage controls, apparatus constraints, validity notes, and supporting artifacts. | REFORMS, DOME, leakage, OpenML, Model Cards/Datasheets. | v1 MUST for structural support; v1 SHOULD for context-dependent leakage/validity population completeness. | `ExperimentTaskModel`, `ExperimentEvaluationProtocolModel`, metric key invariant, split/leakage model, apparatus constraints. Completeness of domain-specific leakage analysis remains review responsibility. |
| EC-T03 | Scenario/snapshot identity must bind task and run so a run cannot silently execute a different scenario. | OpenML task/run separation; PROV entity/activity lineage. | v1 MUST | `validate_experiment_run_against_task` checks task id/version and scenario snapshot identity/digest when task binds a snapshot. |
| EC-T04 | Apparatus is scientific instrument context, including processor/backend identity, manifests, compatibility, parameters, stochastic controls, clocks, measurement channels, observed setup evidence, and limitations. | DETER, cyber-emulation V&V, simulation V&V, cross-testbed reproduction. | v1 MUST | `ExperimentApparatusContextModel` requires canonical processor/backend, selected manifests, compatibility declarations, parameters, stochastic controls, clocks, measurement channels, observed setup evidence, and known limitations. |
| EC-T05 | Processor/backend manifest references must bind to concrete manifest payload identity and digest evidence. | Provenance, FAIR, apparatus-manifest lineage. | v1 MUST | Apparatus model validates selected manifest consistency; `validate_experiment_apparatus_context_against_manifests` validates payload identities and optional digests. |
| EC-T06 | Runs must be archival provenance records, not mutable lifecycle/status envelopes. | PROV/OPM, workflow provenance, Ground Control/ACES runtime lineage. | v1 MUST | `ExperimentRunModel` has task/scenario/apparatus/timestamp/result/evidence fields; ADR and formal spec forbid reconstructing runs from runtime snapshots. |
| EC-T07 | Evidence artifact references must carry integrity and access metadata, and evidence requirements with digest/path must bind to actual artifact checksum/path. | FAIR, RO-Crate, PROV, artifact-review practice. | v1 MUST | `ExperimentArtifactRefModel` requires checksum, size, media type, URI, source, timestamp, sensitivity; task/run validator checks required evidence digest and path against artifact checksum and URI. Regression probes cover digest/path mismatch. |
| EC-T08 | Result summaries must be metric-grounded and evidence-backed. | OpenML evaluations, experiment databases, REFORMS, PROV. | v1 MUST | `ExperimentResultSummaryModel`, run validator result-evidence resolution, and task/run semantic validator enforce task-declared metrics and metric evidence requirements. |
| EC-T09 | Redacted or withheld structured parameters must not leak concrete values. | Security guardrails, FAIR access metadata, lineage privacy/redaction disclosure. | v1 MUST | `ExperimentParameterModel` rejects concrete values when `redaction` is `redacted` or `withheld`; condition-assignment parameters require `redaction: none`. |
| EC-T10 | Study/benchmark records must include research questions, allocation/comparison structure, analysis plan, and validity threats. | Empirical software engineering, V&V, statistical comparison literature. | v1 MUST | `ExperimentStudyModel` requires research questions, run allocation, analysis plan, and validity notes for `study` and `benchmark`; JSON Schema mirrors the conditional requirement. |
| EC-T11 | Analysis plans must name metrics, primary metric, statistical/estimation method, uncertainty method, multiplicity policy, and missing-data policy. | Dietterich, Demsar, Nadeau/Bengio, Arlot/Celisse, REFORMS. | v1 MUST | `ExperimentAnalysisPlanModel` requires these structures and validates primary metric membership. |
| EC-T12 | Study metrics must be grounded in included task protocols and present as run result summaries or explicit missing/withheld statuses. | Experiment databases, OpenML, ML reproducibility, missing-data reporting. | v1 MUST | `validate_experiment_study_against_tasks_and_runs` checks task membership, declared metrics, and per-evaluation-run result coverage. |
| EC-T13 | Run allocation must use declared compared conditions, explicit condition assignments, auditable run-level criteria, distinct condition criteria, eligible runs, and target counts. | Empirical experiment design, blocking/randomization/statistical comparison practice. | v1 MUST | `ExperimentRunAllocationPlanModel` and `validate_experiment_study_against_tasks_and_runs` enforce assignment keys, factor levels, criteria uniqueness, grouping, eligibility, single-condition satisfaction, and target counts. |
| EC-T14 | Blocking factors must be declared variables with levels and appropriate role. | Empirical software engineering, designed experiments, V&V. | v1 MUST | `ExperimentStudyModel` rejects undeclared blocking factors, empty blocking-factor levels, and treatment/other factors used as blocking factors. |
| EC-T15 | Schema publication must distinguish structural JSON Schema checks from named ACES semantic validators. | FAIR machine readability, schema evolution practice, repo policy. | v1 MUST | Generated schemas carry `x-aces-semantic-profile` and `x-aces-invariants`; schema publication and semantic coverage checks validate the profile. |
| EC-T16 | Benchmark and agent-evaluation records should preserve starter files, evaluators, subtasks, gold steps, milestones, human assistance, scaffold disclosure, baseline disclosure, and cost/resource traces. | Cybench, AutoPenBench, AI Agents That Matter, offensive-security benchmark practice in lineage. | v1 SHOULD | `ExperimentArtifactRefModel.role` has explicit artifact roles for these evidence surfaces. Full benchmark semantics remain a future contract extension. |
| EC-T17 | Participant-visible observations must not be treated as hidden world truth. | Gym/Gymnasium, PettingZoo, OpenSpiel, POMDP/POSG lineage. | v1 SHOULD | v1 preserves observation/evidence artifacts and participant implementation references; full participant epistemic state belongs to participant-semantics/runtime contracts. |
| EC-T18 | Causality and attribution require explicit evidence, not post-hoc temporal adjacency. | Halpern-Pearl causality lineage; security-event provenance. | future/non-goal | v1 records evidence and lineage but does not implement causal inference or attribution engines. |
| EC-T19 | RO-Crate/PROV/OpenML export should be possible without importing those payloads as ACES core. | FAIR, RO-Crate, PROV, OpenML. | v1 SHOULD | Stable ids, versions, artifact roles, lineage references, checksums, and schemas support future export mapping; exporters are out of scope. |
| EC-T20 | Runtime APIs, persistence, schedulers, and statistical engines must remain out of this design issue. | Pre-flight guardrails, ADR boundary. | future/non-goal | ADR-037 and formal spec keep this issue to contracts/specification/fixtures/tests. |

## Review Outcome

The initial traceability pass found three `v1 MUST` enforcement gaps and one
`v1 SHOULD` support gap. The enforcement gaps were artifact digest/path binding,
redacted parameter value leakage, and mandatory validity notes for
claim-bearing studies. The support gap was explicit artifact roles for
benchmark and agent-evaluation evidence surfaces. All four are represented in
the contract source and covered by regression tests or schema assertions.

Subsequent bounded closure gates did not change the criteria matrix, but they
found additional closure issues against the same checklist: declared run
allocation now validates even when a collection/cohort omits an analysis plan;
semantic-invariant annotations now resolve to callable validators; artifact
sensitivity metadata is now an explicit schema-required field; and EXP-701
through EXP-705 requirement governance now maps the generated schema
publication surface.
