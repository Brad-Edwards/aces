# Issue 197 RUN-314 Reference Emulation Backend Preflight

Date: 2026-06-20

Issue: #197.

Requirement: RUN-314.

This note records architecture preflight guardrails for a repository-owned
reference emulation backend. It is guidance for implementation only: it does
not implement a backend, add a profile, change manifests, publish schemas,
change conformance, or alter runtime behavior.

## Binding Sources

- ADR-004 defines the compile, plan, execute runtime architecture and requires
  backends to provide explicit domain protocols plus a `BackendManifest`.
- ADR-008 separates processor apparatus, backend apparatus, live runtime state,
  and archival run provenance.
- ADR-009, ADR-012, ADR-019, and ADR-061 define the authority boundary:
  contracts, fixtures, profiles, concept authority, and published schemas are
  authority; implementation code consumes and proves compatibility.
- ADR-036 defines package ownership: `aces_runtime` owns live control,
  `aces_backend_protocols` owns backend declarations, `aces_backend_stubs` owns
  non-normative stubs, `aces_contracts` owns neutral DTOs, and compatibility
  wrappers under `implementations/python/src/aces/` must stay thin.
- ADR-041 and ADR-055 keep participant implementation identity and experiment
  apparatus context separate from backend identity, authored SDL, and mutable
  runtime snapshots.
- ADR-060 and `docs/research/participant-backend-contracts/preflight-guardrails.md`
  govern participant-runtime declarations and retrieval surfaces.
- `docs/explain/reference/backend-conformance.md` governs backend conformance:
  profiles and fixtures are artifact-driven, schema-first, and diagnostic-based.
- `docs/explain/reference/explicitness-realization-semantics.md` governs the
  SEM-218 backend-realization boundary and provenance disclosure.
- `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`, and the policy
  tools define the verification graph and repository guardrails.

## Architecture Decisions

- Treat the reference emulation backend as an implementation-side backend that
  realizes plans through `Provisioner`, `Orchestrator`, `Evaluator`, and, if
  claimed, `ParticipantRuntime` protocol components. It must not become a new
  processor, runtime manager, conformance authority, schema authority, or
  experiment archive.
- Publish backend identity and capability through `BackendManifest` and
  `backend_manifest_payload()`. Do not create an emulation-specific manifest
  schema, local contract-id allowlist, or duplicate profile table.
- Construct executable targets through `BackendRegistry` and `RuntimeTarget`.
  Target creation must keep manifest introspection and component construction
  on the existing descriptor seam, and the component presence must match the
  manifest.
- Route apply/control operations through `RuntimeManager`,
  `RuntimeControlPlane`, `execute_operation()`, `execute_participant_action()`,
  `_call_backend_apply()`, and `_call_backend_diagnostics()`. Do not call
  backend components directly from CLI, tests, conformance, or HTTP adapters.
- Preserve the distinction between emulated infrastructure facts and portable
  ACES runtime facts. Docker, Podman, libvirt, VM, virtual-network, or container
  IDs are backend-native evidence unless mapped into existing
  `RuntimeSnapshot`, result, history, or SEM-218 provenance surfaces.
- Keep the in-memory stub backend non-normative. RUN-314 may use stub behavior
  as a test comparison point, but must not turn `aces_backend_stubs` into the
  reference emulation backend or into backend contract authority.
- A claim in `supported_contract_versions`, `realization_support`, or
  `capabilities.participant_runtime` is evidence-backed. The backend may only
  claim contracts and capability terms it actually emits, consumes, or validates
  through shared models and conformance/live tests.

## Required Incumbents

Reuse these repo surfaces before adding anything new:

- Backend protocols and declarations: `aces_backend_protocols.protocols`,
  `BackendManifest`, `BackendCapabilitySet`, `ProvisionerCapabilities`,
  `OrchestratorCapabilities`, `EvaluatorCapabilities`,
  `ParticipantRuntimeCapabilities`, `participant_runtime_capability_contract_gaps()`,
  and `backend_manifest_payload()`.
- Runtime construction and execution: `BackendRegistry`, `RuntimeTarget`,
  `RuntimeTargetComponents`, `_validate_runtime_target_shape`,
  `RuntimeManager`, `RuntimeControlPlane`, `_call_backend_apply()`,
  `_call_backend_diagnostics()`, `execute_operation()`, and
  `execute_participant_action()`.
- Contract DTOs and validation: `ContractModel(extra="forbid")`,
  `BackendManifestV2Model`, plan models, operation receipt/status models,
  `RuntimeSnapshotEnvelopeModel`, workflow/evaluation/participant result
  models, `schema_bundle()`, and `contracts/schema-publication-manifest.json`.
- Capability/profile authority: `BACKEND_SUPPORTED_CONTRACT_IDS`,
  `validate_backend_supported_contract_versions()`,
  `contracts/profiles/backend/*.json`, `BackendProfileModel`,
  `load_backend_profile_from_path()`, and the `fixtures_root` /
  `profiles_root` override seams in conformance.
- Vocabulary and concept authority: `validate_controlled_vocabulary_scope_values()`,
  `ConceptBindingEntryModel`, `RealizationSupportDeclarationModel`,
  `RealizationSupportMode`, governed `x-<owner>:<term>` extension syntax, and
  the concept-authority catalogs.
- Observability and error shape: `aces_contracts.diagnostics.Diagnostic`,
  `Severity`, runtime diagnostic helpers, operation records, audit events, and
  conformance report envelopes.
- Persistence: `ControlPlaneStore`, `InMemoryControlPlaneStore`,
  `LocalControlPlaneStore`, `_snapshot_payload()`, `_record_payload()`, and
  append-only audit records.
- HTTP/security: `create_control_plane_app()`,
  `ControlPlaneSecurityConfig.strict_defaults()`, `ControlPlaneIdentity`,
  `ControlPlaneRole`, request-size guards, idempotency fingerprints, audited
  authorization, and redacted FastAPI internal errors.
- Apparatus and provenance: `ExperimentApparatusContextModel`,
  `ExperimentRunModel`, `ParticipantImplementationManifestModel`,
  `ParticipantImplementationProvenanceModel`, and
  `validate_experiment_apparatus_context_against_manifests()`.
- Verification: `.ground-control.yaml`, `.gc/plan-rules.md`, `noxfile.py`,
  `tools/check_repo_policy.py`, `tools/check_requirement_governance.py`,
  `tools/check_generated_schemas.py`, `tools/check_json_artifacts.py`, and
  `tools/verify_all.py`.

## Cross-Cutting Layers

The intended design must pass every layer it touches:

- SDL/config ingress: scenario input still flows through `parse_sdl()` /
  `parse_sdl_file()`, `instantiate_scenario()`, `compile_runtime_model()` or
  `compile_scenario_runtime_model()`, and `plan()`. Backend configuration must
  be explicit data passed through `BackendRegistry` factories, not hidden SDL
  keys or ambient YAML side channels.
- Manifest authority gate: `supported_contract_versions`, concept bindings,
  realization-support declarations, participant-runtime role/feature terms, and
  backend compatibility must validate through the existing manifest models and
  authority helpers.
- Runtime target shape gate: manifest component claims must match actual
  provisioner, orchestrator, evaluator, and participant-runtime components, and
  each method must be invokable with the runtime call shape.
- Backend apply gate: backend methods must return `ApplyResult` with a
  `RuntimeSnapshot`; `_call_backend_apply()` deep-copies snapshots, converts
  backend exceptions to diagnostics, validates result shape, validates runtime
  result contracts, runs SEM-218 non-approximation/provenance checks where
  applicable, and reverts to the baseline snapshot on contract failure.
- Runtime snapshot gate: portable observation belongs in first-class snapshot,
  result, history, participant episode, shared-state, and
  `realization_provenance` fields. Do not smuggle emulation state through
  `RuntimeSnapshot.metadata` or generic `details` when a first-class carrier
  exists.
- Control-plane security gate: any HTTP/JSON exercise surface must use
  `create_control_plane_app()` and explicit `ControlPlaneSecurityConfig`.
  Defaults remain fail-closed: no trusted header identities, no bearer tokens,
  verified proxy headers only when enabled, target-bound identities, role
  checks for read/mutating operations, request-size limits, idempotency
  fingerprints, audit records, and redacted internal 500s.
- Secret and OS exposure gate: daemon endpoints, API tokens, registry
  credentials, VM credentials, SSH keys, passwords, private host paths, raw
  environment dumps, process argv, backend inspect payloads, and backend-native
  object reprs must not appear in manifests, fixtures, diagnostics, audit
  details, snapshots, conformance reports, or examples. References, digests,
  sensitivity labels, and redaction classifications are the portable surface.
- Host process boundary: if a backend must invoke local emulation tools, use
  fixed argv, no `shell=True`, no tokens in process arguments, bounded timeouts,
  controlled working directories, and structured stdout/stderr handling that
  cannot leak secrets through diagnostics.
- Persistence gate: durable live state goes through `ControlPlaneStore`; local
  backend working directories or emulator state are backend-private caches, not
  a second ACES operation store or snapshot schema.
- Error-envelope gate: public failures are `Diagnostic` values,
  `OperationReceipt`, `OperationStatus`, existing SDL exceptions, or existing
  HTTP error envelopes. Do not add a backend-specific public exception
  hierarchy, raw tracebacks, log channel, or unredacted payload dump.
- Conformance gate: fixture validation and live target certification use
  `aces_conformance.conformance`, published fixtures, published backend
  profiles, and structured diagnostics. Do not certify an emulation backend by
  local smoke tests alone.
- Package/import gate: new backend implementation code, if needed, belongs in
  an implementation package that consumes `aces_backend_protocols`,
  `aces_contracts`, and the public runtime registry seam. Core packages must
  not import a concrete backend, and no implementation logic belongs in the
  compatibility-only `implementations/python/src/aces/` tree.

## Extension Boundary

The primary extension seam is the backend registry descriptor:
`manifest_factory(**config)` plus `components_factory(manifest=manifest,
**config)`. The next reasonable variation should select or configure an
emulation provider, workspace, network namespace, image source, and resource
limits through that seam without rewriting `RuntimeManager`,
`RuntimeControlPlane`, conformance, or manifest rendering.

The manifest extension seam is the existing backend manifest fields:
`supported_contract_versions`, `realization_support`,
`capabilities.provisioner`, optional `orchestrator`, optional `evaluator`, and
optional `participant_runtime`. Future claims require authority-backed
contract ids, governed vocabulary terms, fixtures, and conformance evidence.

The conformance extension seam is the published backend profile artifact and
contract id. If a new profile is genuinely needed, add it under
`contracts/profiles/backend/` and load it through the existing profile loader;
do not edit a Python-only profile map.

## Gotchas And Anti-Patterns

Avoid:

- treating "reference emulation backend" as a new authority surface instead of
  a concrete implementation of existing backend contracts;
- adding an emulation-specific manifest schema, schema registry, fixture loader,
  profile table, vocabulary table, exception hierarchy, operation store, audit
  log, or HTTP adapter;
- bypassing `BackendRegistry`, `RuntimeTarget`, `RuntimeManager`,
  `RuntimeControlPlane`, `_call_backend_apply()`, or conformance runners for
  convenience;
- using backend-native IDs, daemon inspect payloads, container/VM names,
  scheduler order, timestamps, or tool labels as portable ACES semantics
  without typed mapping and provenance;
- collapsing backend capability, processor capability, participant
  implementation identity, control-plane identity, and experiment apparatus
  context into one concept;
- claiming participant runtime support without publishing state/history through
  the snapshot fields that conformance checks;
- putting raw emulator command output, credentials, tokens, SSH keys, private
  paths, host environment, or raw tracebacks into portable artifacts;
- adding Docker/Podman/libvirt-specific SDL syntax, top-level runtime fields, or
  public contracts when existing runtime surfaces already carry the portable
  fact;
- editing published schemas without the schema publication manifest and
  generated-schema parity gate;
- adding implementation logic under `implementations/python/src/aces/` or
  weakening ADR policy to make imports pass.

## Non-Goals

- No backend implementation code in this preflight.
- No new schema, fixture, manifest, profile, conformance, CLI, runtime, or
  package-metadata changes in this preflight.
- No production cloud, managed cyber range, orchestration platform, or
  privileged host daemon policy.
- No new authentication mechanism, secret store, persistence backend, logging
  stack, process manager, or emulator abstraction.
- No redesign of SDL authoring syntax, processor planning, runtime snapshots,
  participant implementation manifests, experiment-run provenance, or backend
  conformance.
- No implementation plan, task breakdown, requirement status transition, or PR
  merge guidance.
