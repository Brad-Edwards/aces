# Issue 614 Libvirt Participant Runtime Preflight

Date: 2026-06-28

Issue: #614.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records architecture guardrails for adding a narrow libvirt-backed
`ParticipantRuntime` path for the paper scenario's red participant. It is
guidance only: it does not implement the participant runtime, add schemas,
change runtime behavior, or define an implementation plan.

## Binding Sources

- ADR-013 owns participant episode lifecycle. A libvirt domain boot, restart,
  probe, or driver action is not itself the participant episode.
- ADR-022, ADR-054, ADR-060, and
  `docs/research/participant-backend-contracts/preflight-guardrails.md` own
  participant behavior history, action/observation semantics, and backend-facing
  participant runtime declarations.
- ADR-041 and
  `docs/decisions/issue-599-participant-implementation-binding-preflight.md`
  own participant implementation manifests, selection, exposure policy, actor
  provenance, and the provider-neutral action-admission request.
- `docs/decisions/issue-598-paper-reference-scenario-preflight.md` and
  `examples/scenarios/paper-agent-loop.sdl.yaml` own the authored scenario
  shape. The libvirt runtime consumes compiled participant/action/observation
  addresses from that scenario; it does not add scenario-local backend names.
- `docs/decisions/issue-601-libvirt-provisioning-backend-preflight.md` and
  `docs/decisions/issue-601-techvault-live-verification.md` own the native
  libvirt/QEMU provisioning boundary and the distinction between native
  appliance realization and APTL/Docker comparison evidence.
- `.ground-control.yaml`, `.gc/plan-rules.md`, ADR-014, and
  `tools/verify_all.py` remain the repository workflow and verification
  authority.

## Architecture Decisions

- Add libvirt participant runtime support only as a libvirt backend component
  that implements the existing `ParticipantRuntime` protocol and is wired
  through `RuntimeTargetComponents.participant_runtime`. Do not add a direct
  libvirt helper API for participant actions.
- `create_libvirt_manifest(**config)` may declare
  `capabilities.participant_runtime` only when the same normalized target
  configuration will cause `create_libvirt_components()` to provide a matching
  participant runtime component and the manifest declares the required
  participant episode and behavior contract ids. A manifest-only flag is not
  sufficient.
- The live proof must enter through
  `RuntimeControlPlane.initialize_participant_episode()` and
  `RuntimeControlPlane.admit_participant_action()`. The latter already checks
  that the admitted action and observation boundary are compiled addresses
  declared by the selected `ParticipantBehaviorRuntime`.
- The libvirt participant runtime may use a deterministic first implementation,
  but the emitted participant implementation selection/provenance must disclose
  that limitation. Backend identity (`libvirt-qemu`), participant
  implementation identity, evaluator identity, and control-plane caller identity
  must remain separate.
- The action execution leaf must be a bounded participant-domain adapter: either
  execute from the realized participant domain or translate through a rigorously
  documented libvirt appliance boundary. It must not expose a general host shell,
  arbitrary libvirt command execution, raw QEMU/libvirt XML, or backend-native
  action labels as the portable action surface.
- The participant observation must be projected through the authored
  observation boundary. Terminal participant observation may name the DMZ portal
  surface and participant-visible evidence refs; internal DB state,
  Wazuh/evaluator internals, policy internals, hidden adjudication material, and
  backend-private libvirt details must not appear in participant-visible
  `visible_refs` or `disclosed_refs`.
- Participant episode state/history and behavior history must be first-class
  `RuntimeSnapshot` fields. Do not place these records in
  `RuntimeSnapshot.metadata`, `ApplyResult.details`, libvirt driver state, docs,
  or backend-private handles.
- Relevant conformance must include manifest validation, target shape
  validation, participant runtime contract-gap checks, live control-plane
  participant lifecycle/action admission, and `runtime-snapshot-v1` semantic
  diagnostics over the final snapshot. Do not fake orchestrator/evaluator
  components solely to reach an existing conformance profile.

## Required Incumbents

Reuse these repo surfaces before adding anything new:

- Libvirt target construction:
  `create_libvirt_manifest()`, `create_libvirt_components()`,
  `create_libvirt_target()`, `register_libvirt_backend()`,
  `LibvirtProvisioner`, `LibvirtDriver`, `TechVaultNativeLibvirtDriver`, and
  the injected driver/connection boundary.
- Backend declarations:
  `BackendCapabilitySet`, `ParticipantRuntimeCapabilities`,
  `ParticipantFeatureSupport`, `PARTICIPANT_RUNTIME_CAPABILITY_REQUIRED_CONTRACTS`,
  `participant_runtime_capability_contract_gaps()`,
  `BackendManifestV2Model`, `backend_manifest_payload()`, and controlled
  vocabulary validation.
- Runtime construction and execution:
  `RuntimeTarget`, `RuntimeTargetComponents`,
  `_validate_runtime_target_shape()`, `RuntimeControlPlane`,
  `execute_participant_action()`, `_call_backend_apply()`,
  `OperationReceipt`, `OperationStatus`, `ApplyResult`, and `RuntimeSnapshot`.
- Participant runtime contracts:
  `ParticipantEpisodeInitializeRequest`,
  `ParticipantEpisodeExecutionState`, `ParticipantEpisodeHistoryEvent`,
  `ParticipantActionAdmissionRequest`,
  `participant_action_admission_request_violations()`,
  `participant_action_binding_events()`, and
  `participant_behavior_event_payload()`.
- Participant implementation apparatus:
  `ParticipantImplementationManifestModel`,
  `ParticipantImplementationSelectionModel`,
  `ParticipantImplementationProvenanceModel`, exposure-policy validation, and
  `participant_implementation_actor_provenance()`.
- Validation and conformance:
  `participant_runtime_state_contract_diagnostics()`,
  `participant_runtime_history_transition_diagnostics()`,
  `iter_participant_behavior_history_violations()`,
  `run_target_conformance()`, `_semantic_diagnostics("runtime-snapshot-v1",
  ...)`, and the published backend profiles/fixtures.
- Control-plane security and persistence if an HTTP surface is exercised:
  `create_control_plane_app()`, `ControlPlaneSecurityConfig.strict_defaults()`,
  `ControlPlaneIdentity`, `ControlPlaneRole`, request-size guards,
  idempotency keys, request fingerprints, audit events, `ControlPlaneStore`,
  and `LocalControlPlaneStore`.
- Repository policy:
  `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_generated_schemas.py`, `tools/check_schema_publication.py`,
  `tools/check_json_artifacts.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL/config ingress: select the paper scenario through existing
  `parse_sdl()` / `parse_sdl_file()` and `compile_runtime_model()` paths, then
  use compiled `ParticipantBehaviorRuntime`,
  `ParticipantActionContractRuntime`, and
  `ParticipantObservationBoundaryRuntime` addresses. Do not derive runtime
  addresses from file names, TechVault catalog ids, appliance names, or raw YAML
  dictionaries.
- Manifest authority gate: libvirt participant runtime claims must validate
  through `BackendManifest`, `BackendManifestV2Model`, controlled vocabularies,
  and `backend_manifest_payload()`. Supported contract versions must include the
  participant episode and behavior contracts needed by the claimed roles and
  features, or conformance must fail with capability-claim diagnostics.
- Runtime target gate: component presence must match the manifest. A target
  whose manifest declares participant runtime but whose components omit it, or
  vice versa, must fail `_validate_runtime_target_shape()` rather than limp
  into runtime.
- Participant implementation gate: selected implementations must validate
  through `ParticipantImplementationManifestModel` and
  `ParticipantImplementationSelectionModel`. The deterministic proof must use
  manifest/config refs and digests; prompts, credentials, raw policy bodies, and
  hidden task material stay outside portable provenance.
- Action-admission gate: `ParticipantActionAdmissionRequest` must carry the
  compiled participant address, action contract address, observation boundary
  address, action instance id, implementation manifest, implementation
  selection, exposure policy, evidence refs, and action result. Existing
  request validation enforces selection identity, contract support, exposure
  policy, and observation-boundary evidence refs.
- Backend apply/snapshot gate: `ParticipantRuntime.initialize()` and
  `admit_action()` must return `ApplyResult` through `_call_backend_apply()`.
  The gate deep-copies the baseline snapshot, wraps unexpected exceptions as
  `Diagnostic` values, validates `ApplyResult`, validates participant state and
  history, and rejects history rewrites without persisting bad output.
- Observation-boundary gate: participant-visible refs are limited to the task
  and DMZ portal observation permitted by the compiled boundary and exposure
  policy. Wazuh, policy, internal DB, negative-boundary, and libvirt-private
  material may be evaluator evidence or diagnostics only when carried by the
  existing evidence/provenance refs and redaction rules.
- Control-plane security gate: any HTTP route or proof harness must reuse
  fail-closed `ControlPlaneSecurityConfig`, role checks, request-size limits,
  idempotency fingerprints, audit records, and redacted error responses.
  Participant authority is scenario semantics, not HTTP caller authorization.
- Secret and OS-exposure gate: libvirt URIs, host paths, domain XML, MACs,
  console output, subprocess stdout/stderr, environment dumps, process argv,
  bearer tokens, private keys, guest credentials, prompts, and hidden answers
  must not enter snapshots, diagnostics, audit records, fixtures, docs, or
  changelog text. If a process leaf is unavoidable, use fixed argv, no
  `shell=True`, bounded timeouts, controlled working directories, and redacted
  diagnostics.
- Persistence and observability gate: live state uses `RuntimeSnapshot` and
  `ControlPlaneStore`; public failures use `Diagnostic`,
  `OperationReceipt`, and `OperationStatus`. Do not add a libvirt participant
  store, audit log, schema, exception hierarchy, or result envelope.
- Contract/schema gate: no new published schema is needed for this issue unless
  an existing first-class carrier cannot represent a portable fact. Any later
  schema change must go through `ContractModel`, `schema_bundle()`,
  generated-schema checks, fixtures, and
  `contracts/schema-publication-manifest.json`.

## Extensibility Seam

The seam for future participant implementations is the existing action
admission request plus libvirt target configuration:

- participant address, episode id, compiled behavior address, compiled action
  contract address, compiled observation boundary address, action instance id,
  implementation manifest/selection, exposure policy, evidence refs, and
  action-result refs belong in `ParticipantActionAdmissionRequest`;
- the libvirt-owned adapter/domain binding belongs behind
  `create_libvirt_target(**config)` or an injected participant runtime factory,
  parameterized by participant-domain selection, bounded action adapter, timeout,
  and probe/execution policy;
- the live proof may bind to the paper scenario's red participant, but the code
  must be address-driven so another scenario, participant implementation, or
  future coding-agent adapter can be selected without editing canonical libvirt
  manifest, registry, control-plane, or contract code.

## Gotchas And Anti-Patterns

Avoid:

- declaring `participant_runtime` in the manifest without a matching runtime
  component and required participant contracts;
- hardcoding `paper-agent-loop.sdl.yaml`, TechVault ids, libvirt domain names,
  appliance roles, or backend-local action names as portable behavior;
- bypassing `RuntimeControlPlane`, `admit_participant_action()`, or
  `_call_backend_apply()` for a direct libvirt driver call;
- treating the libvirt backend, control-plane caller, evaluator, OS account, or
  bearer-token identity as the participant implementation actor;
- putting participant episode or behavior history into metadata, generic
  details, driver snapshots, logs, or README prose instead of first-class
  snapshot fields;
- exposing a host shell, arbitrary libvirt command API, process argv, guest
  credentials, domain XML, console logs, backend-native object reprs, or
  tracebacks through diagnostics or observations;
- leaking internal DB, Wazuh/evaluator, policy, hidden adjudication, or
  backend-private libvirt details as participant observations;
- adding duplicate DTOs, schemas, validators, backend profiles, conformance
  runners, exception hierarchies, persistence stores, or audit logs;
- making default verification depend on a live libvirt daemon, privileged host
  access, external network, local agent binary, or private credentials.

## Non-Goals

- Implementing the libvirt participant runtime, deterministic participant,
  coding-agent adapter, live proof, tests, or corpus packaging in this
  preflight.
- Implementing Wazuh/evaluator evidence readback for issue #615, the
  cross-backend corpus for issue #600, or APTL-side realization/proof work.
- Adding SDL syntax, published schemas, participant implementation contracts,
  backend profiles, controlled vocabularies, authentication mechanisms, or
  general libvirt command surfaces unless a later implementation proves the
  existing surfaces cannot carry the portable fact.
- Claiming broad TechVault equivalence, Wazuh detection quality, model-defense
  robustness, autonomous-agent capability, or general n=2 backend equivalence
  from this narrow participant-runtime proof.
