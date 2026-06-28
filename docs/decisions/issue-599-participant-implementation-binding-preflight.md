# Issue 599 Participant Implementation Binding Preflight

Date: 2026-06-28

Issue: #599.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records architecture guardrails for binding a compiled SDL-declared
participant to a selected participant implementation. It is guidance only: it
does not implement the binding, add schemas, change runtime behavior, or define
an implementation plan.

## Binding Sources

- ADR-013 owns participant episode lifecycle. The binding must run inside that
  lifecycle rather than treating a backend process, adapter process, or tool
  invocation as the episode.
- ADR-022 owns participant behavior semantics. Action names, tool labels,
  backend commands, timestamps, rewards, and logs are not portable action or
  observation semantics unless bound through action contracts, observation
  boundaries, and evidence/provenance records.
- ADR-041 owns participant implementation manifests and run-level provenance.
  A participant implementation is apparatus; it is distinct from authored SDL
  `agents`, backend manifests, processor manifests, control-plane callers, and
  evaluator identity.
- ADR-054 and `specs/formal/participant-runtime/` own participant runtime
  lifecycle, behavior history, shared state, concurrency, visibility, and
  no-leakage invariants.
- ADR-060 and `specs/formal/runtime-contracts/participant-backend-contracts.md`
  own the backend-facing participant carrier/retrieval surface.
- ADR-067 and
  `docs/decisions/issue-206-act-606-behavior-specifications-preflight.md` own
  behavior specifications as aggregates over existing participant behavior
  surfaces; runtime evidence must not become the authored behavior spec.
- `docs/decisions/issue-598-paper-reference-scenario-preflight.md` owns the
  authored paper scenario guardrails. Issue #599 consumes that compiled
  scenario shape; it must not add scenario-local backend or agent-runner syntax.
- ADR-063 and
  `docs/decisions/issue-197-run-314-reference-emulation-backend-preflight.md`
  own the reference backend boundary: portable ACES facts flow through manifests,
  snapshots, diagnostics, conformance, and runtime result contracts.
- `specs/agent-guidance/agent-guidance.yaml` forbids guidance/authoring tools
  as a route to scan, exploit, SSH, execute commands, reveal hidden state, or
  bypass backend controls.

## Architecture Decisions

- The binding is a narrow participant action-admission boundary. It consumes a
  compiled `ParticipantBehaviorRuntime`, the compiled action/observation
  addresses permitted by that behavior, and a selected participant implementation
  manifest/provenance record. It is not a general shell, RPC, or command
  execution API.
- The binding must enter through `RuntimeControlPlane` and the target's
  `ParticipantRuntime` component, so it inherits operation receipt/status,
  idempotency, persistence, audit, diagnostics, and snapshot validation.
- A backend may host or mediate the adapter, but the actor provenance emitted
  in behavior history must identify the participant implementation selection,
  not the backend component. Backend identity remains in `BackendManifest`;
  processor/control-plane/evaluator identities remain separate.
- Reference tests may use a deterministic in-process fake participant
  implementation. Any live coding-agent proof must be opt-in, injected, and
  bounded behind the same admission contract; default verification must stay
  hermetic and must not require a local agent binary, daemon, credentials, or
  network.
- Emitted state belongs in existing first-class surfaces:
  `RuntimeSnapshot.participant_episode_results`,
  `RuntimeSnapshot.participant_episode_history`, and
  `RuntimeSnapshot.participant_behavior_history`. Do not smuggle binding state
  through `RuntimeSnapshot.metadata`, `ApplyResult.details`, backend-private
  handles, or history `details` keys that duplicate first-class runtime fields.
- Behavior events must preserve compiled SDL addresses:
  `participant_address`, `episode_id`, `action_contract_address`,
  `observation_boundary_address`, action instance id, lifecycle phase,
  action/observation evidence refs, limitations, and actor provenance.
- Unsupported, missing, incompatible, or unsafe bindings fail as structured
  `Diagnostic` values and control-plane failed/rejected operations. They must
  not escape as backend-private exceptions or raw adapter tracebacks.
- The reusable seam for APTL and libvirt is the participant implementation
  selection plus action-admission request, not a backend-specific action runner.
  APTL, the reference backend, and libvirt should be able to consume the same
  compiled behavior/action/observation/provenance inputs and differ only behind
  injected adapter/provider leaves.

## Required Incumbents

- SDL and compiler ingress: `parse_sdl()` / `parse_sdl_file()`,
  `compile_scenario_runtime_model()`, `compile_runtime_model()`,
  `RuntimeModel.participant_behaviors`, `ParticipantBehaviorRuntime`,
  `ParticipantBehaviorSpecificationRuntime`,
  `ParticipantActionContractRuntime`, and
  `ParticipantObservationBoundaryRuntime`.
- Runtime/control-plane path: `RuntimeControlPlane`,
  `execute_participant_action()`, `ParticipantRuntime`,
  `ReferenceParticipantRuntime`, `RuntimeTarget`, `BackendRegistry`,
  `RuntimeTargetComponents`, and `_validate_runtime_target_shape()`.
- Backend result gate: `_call_backend_apply()`, `_call_backend_diagnostics()`,
  `ApplyResult`, `RuntimeSnapshot`, `participant_runtime_state_contract_diagnostics()`,
  and `participant_runtime_history_transition_diagnostics()`.
- Participant history validators:
  `ParticipantBehaviorHistoryEvent`,
  `ParticipantBehaviorHistoryEventModel`,
  `iter_participant_behavior_snapshot_violations()`,
  `iter_participant_behavior_history_violations()`,
  participant episode validators, shared-state validators, concurrency
  validators, and participant retrieval view models.
- Participant implementation apparatus:
  `ParticipantImplementationManifestModel`,
  `ParticipantImplementationProvenanceModel`,
  `ParticipantImplementationSelectionModel`,
  `ExperimentApparatusContextModel`, `ExperimentRunModel`, and
  `validate_experiment_apparatus_context_against_manifests()`.
- Backend capability and manifest authority:
  `ParticipantRuntimeCapabilities`, `ParticipantFeatureSupport`,
  `BackendManifest`, `BackendManifestV2Model`, `backend_manifest_payload()`,
  `BACKEND_SUPPORTED_CONTRACT_IDS`, controlled-vocabulary validation, and
  concept bindings.
- Control-plane security and persistence:
  `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneIdentity`,
  `ControlPlaneRole`, request-size guards, request fingerprints, idempotency
  keys, `AuditEvent`, `ControlPlaneStore`, `InMemoryControlPlaneStore`,
  `LocalControlPlaneStore`, and redacted FastAPI internal-error handling.
- Diagnostics and public error shape: `Diagnostic`, `Severity`,
  `_failure_diagnostic()`, `OperationReceipt`, `OperationStatus`, existing
  HTTP `HTTPException` mappings, and conformance diagnostics.
- Repository workflow and policy: `.ground-control.yaml`, `.gc/plan-rules.md`,
  `noxfile.py`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, `tools/check_generated_schemas.py`,
  `tools/check_schema_publication.py`, `tools/check_json_artifacts.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers

- SDL/config ingress: binding tests must start from parsed/compiled SDL or a
  deliberately constructed compiled model. Do not compile directly from raw
  dicts, skip `SDLModel(extra="forbid")`, or derive runtime addresses from
  free-form YAML names.
- Compiled behavior gate: the admitted action must be a compiled action
  contract address present in the selected `ParticipantBehaviorRuntime` or
  behavior specification. The selected observation boundary must be one of the
  compiled boundaries for that participant behavior.
- Participant implementation manifest gate: selected implementations must
  validate through `ParticipantImplementationManifestModel`; implementation
  kind, supported contracts, decision-surface modes, tool affordances, exposure
  policy kinds, concept bindings, and compatibility claims must use governed
  vocabularies.
- Provenance gate: run-level selection must use
  `ParticipantImplementationProvenanceModel` fields: implementation identity,
  manifest ref/digest, optional config ref/digest, decision-surface mode,
  participant contract versions, exposure policy, and processor/backend manifest
  refs. Hidden prompts, credentials, raw configuration, and decision-surface
  contents stay out of this portable record.
- Backend capability gate: backend support is read from `BackendManifest` /
  `BackendManifestV2Model` and `capabilities.participant_runtime`, including
  feature-support disclosures. A backend support claim is not proof that the
  selected participant implementation ran.
- Runtime target gate: target component presence must match the manifest. The
  binding must not bypass `RuntimeTarget` shape validation or import a concrete
  backend from core runtime packages.
- Backend apply/snapshot gate: participant binding methods must return
  `ApplyResult` with a `RuntimeSnapshot`. `_call_backend_apply()` must be able
  to deep-copy the baseline, wrap unexpected exceptions as diagnostics, validate
  result shape, validate participant state/history, enforce append-only history,
  and reject invalid snapshots without persisting them.
- Participant semantic gate: emitted behavior history must also pass the
  existing SEM validators when supplied with compiled action contracts and
  observation boundaries. The runtime gate checks portable snapshot integrity;
  it does not replace deeper action, observation, visibility, temporal,
  attribution, outcome, shared-state, or concurrency validation.
- Control-plane security gate: any HTTP route added later must reuse
  `create_control_plane_app()`, strict fail-closed security defaults, mutating
  role checks, request-size limits, idempotency fingerprints, audit records, and
  redacted internal errors. Participant authority is scenario meaning, not
  control-plane authorization.
- Secret and OS-exposure gate: adapter config, credentials, prompts, bearer
  tokens, private keys, hidden answers, environment dumps, process argv, raw
  stdout/stderr, backend-native object reprs, and full tracebacks must not
  enter SDL, snapshots, diagnostics, audit details, fixtures, docs, or
  changelog fragments. If a live local adapter must invoke a process, use fixed
  argv, no `shell=True`, no secrets in argv or environment dumps, bounded
  timeouts, controlled working directories, and redacted diagnostics.
- Persistence gate: live state uses `ControlPlaneStore` and `RuntimeSnapshot`.
  Archival apparatus/run evidence uses experiment and participant
  implementation provenance contracts. Do not add a participant-binding store,
  log, cache, or artifact database as a side channel.
- Error-envelope gate: expected binding failures are `Diagnostic` values in
  `OperationReceipt`/`OperationStatus` or bounded HTTP conflict/bad-request
  details if an API is exposed. Do not introduce a participant-binding exception
  hierarchy or public adapter-specific error payload.
- Contract/schema gate: do not publish a new schema unless the implementation
  truly introduces a portable payload that existing contracts cannot carry. If
  a schema is necessary, it must be a closed `ContractModel`, generated through
  `schema_bundle()`, covered by valid/invalid fixtures, and recorded in
  `contracts/schema-publication-manifest.json`.
- Verification gate: tests should stitch together existing fixtures and
  validators rather than copying validation logic. Policy, generated-schema,
  JSON-artifact, and full verify gates remain authoritative.

## Relationship To Linked Issues

- #598 provides the authored enterprise participant/evidence scenario. #599 is
  the runtime/backend binding that consumes the compiled participant behavior,
  selected participant implementation, and declared action/observation
  addresses from that scenario.
- #600 is the cross-backend corpus/proof direction. #599 should keep the binding
  substrate-neutral so APTL and libvirt can consume the same compiled and
  provenance inputs.
- #614 and APTL #557 are downstream proof/consumer issues. They must not require
  a different participant-action schema or a backend-hardcoded actor.
- #343, #344, and #345 are related through the repo's current participant
  runtime and apparatus surfaces: participant episode lifecycle, participant
  behavior/runtime history, backend-facing participant contracts, and
  participant implementation manifest/provenance. #599 composes those surfaces;
  it does not redefine or fork them.

## Extensibility Seam

The seam is a typed participant action-admission request plus participant
implementation selection. It should be parameterized by participant address,
episode id, compiled behavior/spec address, action contract address,
observation boundary address, action instance/correlation id, implementation
identity or provenance ref, decision-surface mode, exposure-policy refs, and
evidence/limitation refs.

Future variations should add another adapter behind that seam, another
participant implementation manifest/provenance selection, another governed
feature-support/disclosure term, or another compiled action/observation
address. They should not require changing SDL syntax, published participant
history schemas, `RuntimeControlPlane`, conformance runners, or backend
manifests solely to support APTL vs libvirt vs in-process execution.

## Gotchas And Anti-Patterns

Avoid:

- treating the backend, control plane, evaluator, OS account, or bearer-token
  principal as the participant implementation actor;
- treating `agents.*.actions` or behavior-spec refs as proof that an
  implementation ran;
- admitting arbitrary commands, prompt text, shell fragments, paths, env vars,
  or backend-native action names through the portable binding;
- using backend logs, timestamps, scheduler order, stdout, stderr, tracebacks,
  container/VM ids, ATT&CK/CVE labels, or reward values as participant behavior
  semantics without governed contracts and limitations;
- writing participant episode or behavior state into metadata, generic details,
  backend-private stores, or README prose instead of first-class snapshot and
  provenance fields;
- adding duplicate DTOs, schemas, validators, exception hierarchies, operation
  stores, audit logs, conformance runners, or HTTP adapters;
- bypassing `RuntimeControlPlane`, `execute_participant_action()`,
  `_call_backend_apply()`, or the snapshot validators for convenience;
- importing concrete backend or live-agent adapter packages from `aces_runtime`,
  `aces_contracts`, `aces_processor`, or compatibility wrappers;
- exposing hidden truth, prompts, credentials, private runner config, raw
  environment, process argv, backend-native object reprs, or full tracebacks in
  diagnostics, snapshots, fixtures, docs, logs, or changelog text.

## Non-Goals

- Implementing the binding, fake participant implementation, live coding-agent
  adapter, APTL adapter, libvirt participant runtime, HTTP route, CLI, tests, or
  proof artifacts in this preflight.
- Adding SDL syntax, published schemas, backend profiles, controlled
  vocabularies, contract fixtures, conformance runners, persistence stores, or
  authentication mechanisms unless a later implementation proves an existing
  surface cannot carry the portable fact.
- Redesigning participant framing, behavior specifications, action contracts,
  observation boundaries, participant episode lifecycle, runtime behavior
  history, participant implementation manifest/provenance, backend manifests,
  control-plane security, runtime persistence, or experiment-run provenance.
- Making default verification depend on local agent installation, network
  access, host daemon state, privileged execution, or external credentials.
