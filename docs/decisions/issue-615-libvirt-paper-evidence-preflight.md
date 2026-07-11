# Issue 615 Libvirt Paper Evidence Preflight

Date: 2026-06-29

Issue: #615.

Requirement: none. The GitHub issue title, body, acceptance criteria, and
non-claims are the contract.

This note records architecture guardrails for extending the libvirt paper live
proof into an evaluator-facing evidence artifact for the enterprise
participant/evidence scenario. It is guidance only: it does not implement the
artifact, add schemas, change runtime behavior, or define an implementation
plan.

## ASR-519 correction

Issue 714 narrows this preflight's native evidence assumptions. A generated
TechVault domain or reachable listener is not guest, service, or SOC evidence.
Current native evidence is limited to exact, bounded libvirt daemon readback of
the admitted VM/network substrate. Wazuh/SOC channels in the paper artifact are
structural evaluator declarations, not native readback. Generic readiness,
negative-reachability, and name-derived SOC claims are withdrawn pending
concern-specific guest observation work.

## Binding Sources

- `docs/decisions/issue-598-paper-reference-scenario-preflight.md`,
  `examples/scenarios/paper-agent-loop.sdl.yaml`, and
  `examples/scenarios/paper-agent-loop.README.md` own the authored paper
  scenario, action contract, observation boundary, Wazuh evaluator evidence,
  negative boundary evidence, and paper non-claims.
- `docs/decisions/issue-614-libvirt-participant-runtime-preflight.md` and
  `docs/decisions/issue-614-libvirt-participant-runtime.md` own the libvirt
  `ParticipantRuntime` path and its deterministic-domain limitation.
- ADR-066 owns observability/evidence plane separation. Wazuh/SOC evidence and
  negative reachability checks are evaluator evidence, not participant-visible
  observations unless a governed participant observation boundary projects
  them.
- ADR-064 and ADR-065 own experiment evidence records and run provenance.
  `experiment-evidence-record-v1` is raw captured evidence;
  `experiment-derived-measure-v1` is interpreted analysis; `experiment-run-v1`
  is the archival run join point.
- `docs/decisions/issue-601-techvault-live-verification.md`,
  `aces_operations.techvault_live`, and
  `aces_backend_libvirt.techvault_native` own the native libvirt live-gate
  substrate and bounded daemon-observed surface. Guest readiness and SOC state
  are explicitly `not-observed`.
- `contracts/schemas/backend-manifest/backend-manifest-v2.json`,
  `BackendManifestV2Model`, and `backend_manifest_payload()` own backend
  manifest/capability shape.
- `.ground-control.yaml`, `.gc/plan-rules.md`, ADR-014, and
  `tools/verify_all.py` remain the repository workflow and verification
  authority.

## Architecture Decisions

- Treat the issue-615 output as a stable libvirt paper evidence artifact that
  composes existing ACES contracts. Use a stable artifact path/name such as
  `runs/<run-id>/paper-evidence/libvirt-paper-evidence-run.json` and a stable
  envelope identifier such as `aces.libvirt.paper-evidence-run/v1`; do not
  create a second experiment-run, evidence-record, participant-runtime, backend
  manifest, or evaluator schema unless an existing published carrier cannot
  represent a portable fact.
- The artifact must be an evaluator/corpus artifact, not an ad hoc log dump.
  It should contain bounded summaries and/or embedded validated contract
  payloads for published ACES contracts, plus refs/checksums for any content
  stored outside the artifact.
- Required evidence surfaces are: authored scenario identity and content hash;
  compiled processor/runtime artifact identity; backend manifest payload and
  capability/profile/conformance result; libvirt realization provenance;
  realized topology and network attachment matrix; participant action proof
  from `LibvirtParticipantRuntime`; terminal participant observation envelope
  or behavior-history equivalent; evaluator-only declarations of Wazuh/SOC
  evidence channels with explicit limitation; structural negative-boundary
  checks for internal DB and Wazuh/evaluator surfaces; evaluator outcome and
  limitation records; and redaction/provenance metadata.
- Wazuh/SOC evidence must remain evaluator-only evidence. If the native libvirt
  proof has no concern-specific guest observation, the artifact must state
  `not-observed`; it must not synthesize translated native readback from domain
  names, declared services, or generic reachability.
- The participant proof must enter through `RuntimeControlPlane` and
  `LibvirtParticipantRuntime`, reusing the issue-614 action-admission and
  behavior-history machinery. Do not replace the participant proof with a
  host-side probe result.
- Negative boundary checks must be recorded as evaluator evidence or derived
  analysis over evaluator evidence. They must not become participant
  observations, action effects, hidden-state disclosures, or scenario-authored
  topology semantics.
- The artifact must be close enough to the APTL paper proof artifact to support
  issue #600's invariant ledger, but ACES must not import APTL-private schemas,
  Docker/container ids, Wazuh rule bodies, credentials, or backend command
  transcripts.

## Required Incumbents

Reuse these repo surfaces before adding anything new:

- Libvirt live-gate surface:
  `validate_techvault_live()`, `TechVaultLiveConfig`,
  `TechVaultLiveReport`, `TechVaultNativeLibvirtDriver`,
  `expected_surface()`, and the existing safe `run_id` filesystem-label check.
- Libvirt runtime/provisioning surface:
  `create_libvirt_target()`, `create_libvirt_manifest()`,
  `create_libvirt_components()`, `LibvirtProvisioner`,
  `LibvirtDriver`, `TechVaultNativeLibvirtDriver`, `RuntimeManager`, and
  `RuntimeControlPlane`.
- Participant-runtime proof surface:
  `LibvirtParticipantRuntime`, `LibvirtParticipantDomainAdapter`,
  `run_libvirt_participant_proof()`,
  `ParticipantActionAdmissionRequest`,
  `ParticipantObservationEnvelopeModel`,
  `ParticipantOutcomeReportModel`,
  `iter_participant_episode_snapshot_violations()`, and
  `iter_participant_behavior_history_violations()`.
- Experiment and evidence contracts:
  `ExperimentRunModel`, `ExperimentRunTraceabilityModel`,
  `ExperimentRealizedFormDisclosureModel`,
  `ExperimentEvidenceRecordModel`, `ExperimentRawEvidenceContentModel`,
  `ExperimentDerivedMeasureModel`, `ExperimentApparatusContextModel`,
  `ExperimentManifestReferenceModel`, `ExperimentArtifactRefModel`, and
  `validate_experiment_run_against_task()`.
- Evaluation contracts:
  `EvaluationResultStateModel`, `EvaluationHistoryEventModel`,
  `EvaluationExecutionState`, `EvaluationHistoryEvent`,
  `EvaluationResultContract`, `EvaluationExecutionContract`, and
  `evaluation_result_contract_diagnostics()`.
- Backend manifest/conformance:
  `backend_manifest_payload()`, `BackendManifestV2Model`,
  `participant_runtime_capability_contract_gaps()`,
  `observation_capability_contract_gaps()`, `load_backend_profile()`,
  `profile_for_manifest()`, and `run_target_conformance()`.
- Security, persistence, and diagnostics:
  `Diagnostic`, `OperationReceipt`, `OperationStatus`, `RuntimeSnapshot`,
  `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneIdentity`,
  `ControlPlaneRole`, request-size guards, idempotency fingerprints,
  `AuditEvent`, `ControlPlaneStore`, `LocalControlPlaneStore`, and redacted
  HTTP error handling if any API path is exercised.
- Repository policy:
  `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_json_artifacts.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL/config ingress: select the paper scenario through `parse_sdl_file()` and
  `compile_runtime_model()`. The artifact must cite the scenario path/name and
  content hash, but runtime addresses must come from compiled participant,
  action, observation, objective, and evaluation addresses, not from filenames,
  appliance names, or raw YAML dictionaries.
- Manifest/profile gate: render libvirt backend identity through
  `backend_manifest_payload()` and validate with `BackendManifestV2Model`.
  If the implementation claims observation or evaluator capability, it must add
  the actual manifest capability and pass the existing contract-gap/profile
  checks; otherwise the artifact may carry evaluator evidence as a paper proof
  record without claiming generic backend evaluator support.
- Runtime target/apply gate: provisioning, participant action admission, and
  any evaluation execution must pass through `RuntimeManager`,
  `RuntimeControlPlane`, and `_call_backend_apply()` so malformed backend
  output becomes `Diagnostic`/`OperationStatus` data and invalid snapshots are
  rejected.
- Participant visibility gate: participant-visible content is limited to the
  compiled observation boundary and participant implementation exposure
  policy. Wazuh/SOC channel declarations, policy internals,
  evaluator limitations, libvirt native details, and negative checks must stay
  outside `visible_refs` and `disclosed_refs` unless an existing governed
  boundary explicitly permits disclosure.
- Evidence/run contract gate: raw evidence must use
  `ExperimentEvidenceRecordModel` dimensions: source refs, capture time/window,
  raw content reference or bounded summary, sensitivity, redaction state,
  checksum/loss disclosure, and provenance. Derived outcomes or invariant
  judgments belong in derived-measure/evaluation/run limitation surfaces, not
  raw evidence records.
- Evaluation gate: evaluator outcome records must match the existing
  evaluation result/history envelopes and contracts. If libvirt remains without
  a generic evaluator component, the paper artifact must make that limitation
  explicit rather than smuggling evaluator state into `RuntimeSnapshot.metadata`
  or backend-private details.
- Secret-handling gate: the artifact must contain no raw libvirt XML, domain
  UUIDs as portable semantics, QEMU command lines, host paths, libvirt
  connection URIs with secrets, credentials, private keys, unredacted tool
  transcripts, backend-native inspect payloads, raw Wazuh rule bodies, raw
  prompts, hidden answers, environment dumps, process argv, or full tracebacks.
- OS-level exposure gate: future concern-specific guest probes must keep
  secrets out of argv and diagnostics. Generic ping/TCP checks are not
  realization evidence. Use fixed argv, no `shell=True`, bounded timeouts,
  controlled working directories, and bounded sanitized diagnostics.
- Persistence gate: use the existing run archive directory and atomic JSON
  writing pattern where durable control-plane state is needed. Do not add a
  libvirt evidence database, participant store, audit log, schema registry, or
  backend-private state ledger.
- Error-envelope/logging gate: public failures must remain structured
  `Diagnostic`, `OperationReceipt`, `OperationStatus`, and report check
  records. Do not serialize exception reprs, stdout/stderr dumps, native object
  reprs, or unchecked backend payloads into the artifact, audit, tests, docs,
  or changelog.
- Contract/schema gate: if a published schema changes, update the contract
  source, generated schema bundle, fixtures, and
  `contracts/schema-publication-manifest.json`. A local proof-artifact wrapper
  must not become a shadow published contract.

## Extensibility Seam

The extension seam belongs in a backend-neutral paper evidence producer over
runtime/evidence contract inputs, parameterized by:

- `scenario_path`, `run_id`, `output_dir`, and optional artifact locator or
  sealing policy;
- backend target factory/config, including libvirt connection and participant
  runtime factory;
- evidence source policy separating authored, planned, driver-reported,
  daemon-observed, guest-observed, and derived facts;
- invariant-ledger mapping, which should reference stable ACES addresses and
  evidence refs rather than libvirt domain names, UUIDs, Docker ids, host paths,
  or APTL-private identifiers.

A future #600 cross-backend ledger should consume the artifact as evidence
refs, bounded summaries, and validated contract payloads. It should not require
rewriting the libvirt live gate, backend manifest schema, participant-runtime
contracts, or experiment-core schemas to add one more backend or evidence
source.

## Gotchas And Anti-Patterns

Avoid:

- treating the existing native live-gate manifest as sufficient paper evidence
  without adding participant proof, evaluator outcome, boundary checks,
  limitation disclosure, and redaction/provenance metadata;
- inventing a new evidence schema, evaluator schema, exception hierarchy,
  validator, conformance runner, persistence store, audit log, or DTO stack;
- putting evidence records, evaluation results, participant observations, and
  backend readiness checks into one generic `evidence` object with untyped
  semantics;
- using `RuntimeSnapshot.metadata`, `ApplyResult.details`, diagnostics, audit
  details, or README prose as the carrier for first-class evidence or
  provenance;
- making Wazuh/SOC readback participant-visible or using it as a participant
  observation envelope;
- claiming libvirt evaluator or observation capability in the backend manifest
  without actual capability implementation and contract-gap checks;
- fabricating native appliance SOC readback from names, listeners, topology, or
  daemon-only substrate facts;
- using libvirt domain UUIDs, XML, MACs, host paths, QEMU commands, Docker ids,
  APTL Compose names, or backend-local action labels as portable semantics;
- overfitting the artifact to one run id, host, libvirt network naming policy,
  IP allocation, or paper corpus directory layout;
- making default verification require privileged libvirt access, a running
  daemon, external network, private credentials, or upstream Wazuh internals.

## Non-Goals

- Implementing the libvirt paper evidence artifact, live probes, tests,
  schemas, corpus packaging, or issue #600 invariant ledger in this preflight.
- Adding new SDL syntax, published contracts, backend profiles, controlled
  vocabularies, evaluator APIs, observation capability declarations, or
  persistence systems unless later implementation proves existing surfaces
  cannot carry the portable fact.
- Claiming Wazuh detection quality, model-defense robustness, byte-equivalence
  between libvirt appliances and APTL containers, application-internals
  equivalence, full semantic equivalence, or broad n=2 backend equivalence.
- Replacing the existing issue-614 participant runtime proof or issue-601
  native substrate proof; issue #615 composes and augments those surfaces for
  evaluator-facing evidence.
