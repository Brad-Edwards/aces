# Issue 600 Paper Demonstration Corpus Preflight

Date: 2026-07-04

Issue: #600.

Requirement: none. The GitHub issue title, body, acceptance criteria, and
non-claims are the contract.

This note records architecture guardrails for publishing the paper
demonstration corpus: one APTL realization and one libvirt reference-backend
realization of the same authored ACES paper scenario, compared through an
inspectable invariant ledger. It is guidance only: it does not implement the
corpus, add schemas, fetch external evidence, or define an implementation plan.

## Binding Sources

- `docs/decisions/issue-598-paper-reference-scenario-preflight.md`,
  `examples/scenarios/paper-agent-loop.sdl.yaml`, and
  `examples/scenarios/paper-agent-loop.README.md` own the authored scenario,
  scenario hash boundary, declared action surface, observation boundary,
  evaluator/Wazuh evidence, negative boundary evidence, issue links, and
  paper non-claims.
- `docs/decisions/issue-599-participant-implementation-binding-preflight.md`
  and ADR-041 own participant implementation manifest/provenance and keep
  runner identity distinct from SDL participants, backends, evaluators, and
  control-plane callers.
- `docs/decisions/issue-614-libvirt-participant-runtime.md` owns the libvirt
  participant-runtime limitation: structural participant lifecycle/action
  admission through the libvirt runtime, not live domain execution.
- `docs/decisions/issue-615-libvirt-paper-evidence-preflight.md`,
  `aces_operations.libvirt_paper_evidence`, and
  `validate_libvirt_paper_evidence_artifact()` own the libvirt paper evidence
  artifact and its redaction/contract/boundary validator.
- ADR-064, ADR-065, ADR-066, and ADR-068 own evidence records, run
  provenance, evidence-plane separation, replication/replay claim limits, and
  the distinction between raw evidence, derived interpretation, run records,
  and study/comparison semantics.
- `contracts/schemas/backend-manifest/backend-manifest-v2.json`,
  `contracts/schemas/experiment-core/*`,
  `contracts/schemas/participant-runtime/*`,
  `contracts/schemas/control-plane/*`, and their
  `aces_contracts.contracts` models are the published contract authority.
- `docs/explain/reference/backend-conformance.md`, `aces_conformance`, and
  `contracts/profiles/backend/*` own backend profile/conformance authority.
- `.ground-control.yaml`, `.gc/plan-rules.md`, ADR-014, `noxfile.py`, and
  `tools/verify_all.py` remain the workflow and verification authority.

## Architecture Decisions

- Treat the #600 corpus as a backend-paired evidence package plus comparison
  ledger. It composes existing run/evidence artifacts; it is not a leaderboard,
  benchmark table, new SDL syntax, new participant runtime contract, or backend
  equivalence proof.
- The n=2 claim is exactly two independent backend realizations of the same
  authored scenario: APTL and libvirt. Optional repeat runs per backend may be
  retained for stability, but they must be labeled as repeats and kept separate
  from the two-backend claim.
- Use the same authored scenario identity tuple for both backend runs:
  scenario name/version/path plus byte-level `sha256:` content digest. Runtime
  addresses and invariant refs must come from parsed/compiled SDL, not from
  filenames, APTL service names, libvirt domain names, Docker names, or raw
  YAML dictionaries.
- The comparison ledger should be a thin local corpus artifact unless a future
  issue requires publication as a contract. Rows should reference stable ACES
  addresses, scenario digest, backend id, evidence refs, preserved invariant
  status, realization differences, unsupported/degraded surfaces, and evidence
  limitations. Do not publish a schema under `contracts/schemas/` just to carry
  one paper comparison.
- Each backend run entry must carry or link to the accepted evidence surfaces:
  scenario/source hash, processor artifact identity, backend manifest or
  capability profile, runtime snapshots, realized topology/network attachment
  matrix, participant implementation provenance, participant episode history,
  participant behavior history, terminal observation, evaluator/Wazuh evidence,
  and outcome interpretation evidence. Missing, translated, deterministic, or
  degraded surfaces must be first-class limitations, not inferred facts.
- Reachability evidence must remain evaluator evidence. Positive DMZ portal
  reachability must be tied to the declared participant action surface; direct
  internal DB and Wazuh/evaluator reachability must be absent or explicitly out
  of scope, and checked as negative evidence where a backend supports it.
- The APTL evidence issue and artifact may be linked or summarized, but ACES
  must not import APTL-private schemas, Docker inspect payloads, Compose names,
  container ids, secrets, credentials, or backend command transcripts as
  portable semantics.
- Libvirt evidence should be consumed through the existing
  `aces.libvirt.paper-evidence-run/v1` artifact and
  `validate_libvirt_paper_evidence_artifact()`. Do not fork the libvirt paper
  validator or reassemble libvirt-private state in the #600 corpus layer.

## Required Incumbents

Reuse these before adding anything new:

- Scenario ingress: `parse_sdl_file()`, `parse_sdl()`,
  `compile_runtime_model()`, `compile_scenario_runtime_model()`,
  `SDLModel(extra="forbid")`, `SemanticValidator`, `SDLParseError`,
  `SDLValidationError`, and `ScenarioValidationError`.
- Paper scenario artifacts: `examples/scenarios/paper-agent-loop.sdl.yaml`,
  `examples/scenarios/paper-agent-loop.README.md`, and the #598/#599/#614/#615
  decision notes.
- Libvirt paper evidence: `run_libvirt_paper_evidence()`,
  `LibvirtPaperEvidenceConfig`, `LibvirtPaperEvidenceReport`,
  `EVIDENCE_RUN_SCHEMA`, `validate_libvirt_paper_evidence_artifact()`,
  `EvidenceCheck`, `run_artifact_path()`, `is_valid_run_id_label()`, and
  `atomic_write_json_artifact()`.
- Backend/runtime envelopes: `backend_manifest_payload()`,
  `BackendManifestV2Model`, `participant_runtime_capability_contract_gaps()`,
  `observation_capability_contract_gaps()`, `RuntimeManager`,
  `RuntimeControlPlane`, `_call_backend_apply()`, `RuntimeSnapshot`,
  `OperationReceipt`, `OperationStatus`, `Diagnostic`, and `Severity`.
- Participant contracts: `ParticipantImplementationManifestModel`,
  `ParticipantImplementationProvenanceModel`,
  `ParticipantImplementationSelectionModel`,
  `ParticipantBehaviorHistoryEventModel`,
  `ParticipantObservationEnvelopeModel`, `ParticipantOutcomeReportModel`,
  participant episode/history validators, and the deterministic participant
  fixtures used by the libvirt proof.
- Experiment/evidence contracts: `ExperimentEvidenceRecordModel`,
  `ExperimentRawEvidenceContentModel`, `ExperimentDerivedMeasureModel`,
  `ExperimentRunModel`, `ExperimentRunTraceabilityModel`,
  `ExperimentRealizedFormDisclosureModel`,
  `ExperimentApparatusContextModel`,
  `validate_experiment_apparatus_context_against_manifests()`, and
  `validate_experiment_run_against_task()`.
- Evaluation contracts: `EvaluationResultStateModel`,
  `EvaluationHistoryEventModel`, `evaluation_result_contract_diagnostics()`,
  and the control-plane evaluation result/history envelopes.
- Security/control-plane defaults if any API is exercised:
  `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneIdentity`,
  `ControlPlaneRole`, request-size guards, request fingerprints,
  idempotency keys, `AuditEvent`, `ControlPlaneStore`,
  `LocalControlPlaneStore`, and redacted FastAPI internal-error handling.
- Repository policy: `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/check_json_artifacts.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_example_library.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL/config ingress: every scenario-derived fact must pass safe YAML parsing,
  closed SDL models, semantic validation, and processor compilation. The corpus
  layer must not derive runtime addresses from raw dicts or skip validation to
  make an external artifact fit.
- Scenario hash gate: compute or compare the byte-level `sha256:` digest of
  the authored ACES scenario. Do not hash normalized YAML, generated processor
  output, APTL translated input, libvirt realization output, or README text as
  the authored scenario identity.
- Artifact ingestion gate: libvirt artifacts must revalidate through
  `validate_libvirt_paper_evidence_artifact()`. Embedded published payloads
  must revalidate through their `ContractModel` classes. APTL artifacts may be
  linked or translated into bounded summaries, but backend-private fields must
  stay outside the ACES ledger.
- Backend manifest/profile gate: any ACES backend manifest payload must render
  through `backend_manifest_payload()` and validate with
  `BackendManifestV2Model`. Capability gaps and unsupported/degraded surfaces
  must remain visible; do not claim evaluator, observation, participant, or
  Wazuh capability because an evidence artifact contains a bounded summary.
- Runtime/control-plane gate: runtime evidence generated inside ACES must pass
  through `RuntimeManager`, `RuntimeControlPlane`, `_call_backend_apply()`, and
  snapshot/result validators so malformed backend output is converted into
  diagnostics and invalid snapshots are rejected before persistence.
- Participant provenance gate: participant implementation identity belongs in
  `ParticipantImplementationManifestModel` and
  `ParticipantImplementationProvenanceModel`; it must not be inferred from
  backend ids, OS accounts, bearer-token callers, container names, or libvirt
  domain labels.
- Participant visibility gate: participant-visible observations, evaluator
  evidence, hidden internal state, and outcome interpretation must remain
  separate. Wazuh/SOC readback, direct DB/Wazuh negative checks, policy
  internals, and evaluator notes must not appear in participant visible or
  disclosed refs unless an existing governed observation boundary permits it.
- Evidence/run contract gate: raw captured evidence belongs in evidence-record
  shapes with sensitivity, redaction, checksum/loss disclosure, source refs,
  and provenance. Cross-backend invariant judgments are derived interpretation,
  not raw evidence and not participant observations.
- Redaction gate: the corpus must contain no raw secrets, participant
  credentials, private keys, bearer tokens, hidden answers, prompt bodies,
  environment dumps, process argv, stdout/stderr dumps, full tracebacks,
  backend-native inspect payloads, raw libvirt XML, QEMU command lines, host
  paths, libvirt connection URIs with secrets, domain UUIDs as semantics,
  Docker private ids as semantics, Compose internals as semantics, or raw Wazuh
  rule bodies.
- OS-level exposure gate: any CLI or helper must use safe run-id labels,
  confined output paths, fixed argv, no `shell=True`, bounded timeouts, and
  redacted diagnostics. Default verification must not require a live libvirt
  daemon, Docker daemon, network, privileged host access, or private
  credentials.
- Persistence gate: write corpus artifacts under the existing run-archive
  pattern and atomic JSON helper if durable JSON is produced. Do not add a
  corpus database, backend-private state ledger, participant store, audit log,
  or schema registry.
- Error-envelope/logging gate: expected failures remain `Diagnostic`,
  `EvidenceCheck`, `OperationReceipt`, `OperationStatus`, or validator
  violation strings. Do not add a #600 exception hierarchy or leak native
  exception reprs into artifacts, logs, docs, tests, or changelog text.
- Contract/schema gate: avoid new published schemas. If later implementation
  proves a portable contract is necessary, update the hand-governed schema,
  generator parity, fixtures, semantic invariant annotations, and
  `contracts/schema-publication-manifest.json` in the same change.
- Workflow/policy gate: policy, requirement-governance, JSON artifact,
  generated-schema, schema-publication, example-library, and full verify gates
  remain authoritative.

## Extensibility Seam

The seam is a backend-run evidence descriptor plus invariant-ledger row, not a
new scenario section or backend-specific schema. Parameterize by:

- authored scenario ref and `sha256:` digest;
- backend id and evidence-source mode;
- evidence artifact locator and validator/translator;
- processor/backend/participant manifest refs and digests;
- stable ACES addresses for participant, action contract, observation boundary,
  topology nodes/networks, evaluator evidence, and outcome interpretation;
- per-backend support status, degradation/unsupported-surface disclosures, and
  evidence limitations.

A future backend should add another backend-run descriptor and ledger entries
without editing the paper SDL, parser, compiler, backend manifest schema,
participant-runtime contracts, experiment-core contracts, or libvirt evidence
producer.

## Gotchas And Anti-Patterns

Avoid:

- presenting repeated runs on one backend as the n=2 backend claim;
- turning the invariant ledger into a leaderboard, score table, Wazuh-quality
  comparison, model-defense robustness result, or autonomous-agent benchmark;
- accepting two artifacts with different authored scenario digests as one
  paired corpus;
- treating libvirt deterministic participant action proof as live domain
  execution, or APTL Docker/Wazuh telemetry as proof of ACES semantic
  equivalence;
- flattening participant history, behavior history, terminal observation,
  evaluator evidence, negative reachability, and outcome interpretation into
  one generic `evidence` object;
- using APTL container ids, Compose service names, Docker inspect fields,
  libvirt domain UUIDs, MACs, host paths, QEMU commands, scheduler order,
  timestamps, backend-local action labels, reward values, or final scores as
  portable semantics;
- copying validation logic from published contracts into a #600-specific
  validator instead of invoking existing models and validators;
- weakening redaction or boundary checks to preserve inspectability;
- making default verification depend on external GitHub fetches, APTL private
  state, Docker/libvirt daemons, privileged host access, private credentials,
  local images, upstream Wazuh internals, or network access.

## Non-Goals

- Implementing the #600 corpus, APTL evidence import, libvirt evidence changes,
  tests, CLI, changelog, schemas, or invariant ledger in this preflight.
- Proving participant/model performance, autonomous-agent capability, Wazuh
  detection quality, model-defense robustness, byte-equivalence, Docker/libvirt
  substrate equivalence, full semantic equivalence, or application-internals
  equivalence.
- Redesigning SDL authoring, participant binding, runtime control-plane
  security, backend manifests, experiment-core contracts, participant-runtime
  contracts, evaluation contracts, conformance, redaction policy, or run
  persistence.
- Closing Brad-Edwards/aptl#558, Brad-Edwards/aces#614, or
  Brad-Edwards/aces#615; #600 consumes those evidence surfaces and records
  limitations.
