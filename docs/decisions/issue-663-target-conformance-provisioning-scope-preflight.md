# Issue 663 Target Conformance Provisioning Scope Preflight

Date: 2026-07-04

Issue: #663.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

This note records architecture guardrails for correcting target conformance
after issue #606. It is guidance only: it does not implement the probe, change
schemas, add profiles, or certify a downstream backend.

## Binding Sources

- `docs/explain/reference/backend-conformance.md` owns the backend conformance
  model: profiles and fixtures are published contract authority; target
  conformance is implementation-side verification.
- `docs/decisions/issue-606-libvirt-conformance-preflight.md` introduced the
  backend-neutral live provisioning probe. This issue narrows that guardrail:
  contract conformance and arbitrary scenario realizability are distinct.
- `contracts/profiles/backend/*.json`, `aces_contracts.backend_profiles`, and
  `BackendCapabilityProfile` define contract sets and known runtime surfaces.
  They are not scenario fixture catalogs.
- `BackendManifest`, `ProvisionerCapabilities`, `RealizationSupportDeclaration`,
  `backend_manifest_payload()`, and `BackendManifestV2Model` are the existing
  capability and realization declaration surfaces.
- `run_reference_processor()`, `RuntimeControlPlane`,
  `OperationReceipt`/`OperationStatus`, `RuntimeSnapshotEnvelope`, and
  `ConformanceCaseResult` are the incumbent live-probe and report seams.
- `_validate_payload()`, `_semantic_diagnostics()`,
  `_capability_gaps()`, `_declared_contract_gaps()`,
  `participant_runtime_capability_contract_gaps()`, and
  `observation_capability_contract_gaps()` are the shared validation and
  capability-claim gates that must remain active.

## Architecture Decisions

- Do not treat a backend profile as a promise to realize any arbitrary SDL
  scenario. Backend profiles certify contract sets and known runtime surfaces;
  realizability is a separate claim that must be negotiated from the manifest
  and the selected live-probe input.
- Keep `operation-status-v1` contract conformance separate from successful
  realization. A backend that rejects an unsupported scenario with a well-formed
  operation status and diagnostics may be contract-conformant; that rejection is
  not, by itself, proof that the backend lacks the provisioning contract.
- Keep issue #606's no-op guard for applicable live probes. When the selected
  probe scenario is within the backend's declared/provided support envelope,
  conformance must still require a succeeded provisioning operation,
  non-empty changed addresses, and a snapshot that validates and carries
  provisioning-domain state.
- Use existing manifest surfaces first. `realization_support.support_mode`,
  `supported_constraint_kinds`, `supported_exact_requirement_kinds`,
  `ProvisionerCapabilities`, and manifest `constraints` are the current
  disclosure surfaces for bounded or scenario-scoped realization. Do not add a
  second conformance-only capability schema.
- The reference scenario seam belongs at target-conformance invocation or
  target construction, using existing `Scenario`/`ProvisioningPlan` data and an
  expected snapshot/changed-address predicate. Do not put backend-specific
  scenario fixtures in `contracts/profiles/backend`, and do not hard-code APTL,
  libvirt, Docker, or VM assumptions in `aces_conformance`.
- If a backend supplies a supported reference scenario, process it through
  `parse_sdl()`/`run_reference_processor()` and the target manifest. Do not
  bypass the reference processor, planner manifest validation, or
  `RuntimeControlPlane`.
- The same boundary applies to participant-runtime live probes: a full remote
  control plane can still be required to prove RUN-311 control envelopes, but
  the probe must not require an arbitrary participant address or topology when a
  fixed-topology backend can only drive declared or realized participants.

## Required Incumbents

Reuse these before adding anything new:

- Conformance runner/reporting:
  `run_target_conformance()`, `_live_target_cases()`,
  `_provisioning_probe_case()`, `_live_snapshot_case()`,
  `_drive_participant_episode_probe()`, `ConformanceCaseResult`, and
  `BackendConformanceReport`.
- Profile and fixture authority:
  `required_contracts()`, `_resolve_required_contracts()`,
  `load_backend_profile_from_path()`, `fixtures_root()`, `profiles_root()`,
  `schema_bundle()`, and the published `contracts/` corpus.
- Manifest/capability authority:
  `BackendManifest`, `BackendCapabilitySet`, `ProvisionerCapabilities`,
  `RealizationSupportDeclaration`, `backend_manifest_payload()`,
  `BackendManifestV2Model`, `validate_backend_supported_contract_versions()`,
  and controlled-vocabulary validators.
- Planning/runtime gates:
  `run_reference_processor()`, planner manifest validation,
  `RuntimeTarget` shape validation, `RuntimeControlPlane.submit_provisioning()`,
  `_call_backend_diagnostics()`, `_call_backend_apply()`,
  `_snapshot_contract_diagnostics()`, `OperationReceipt`, `OperationStatus`,
  and `RuntimeSnapshot`.
- Claim-gap checks:
  `_capability_gaps()`, `_declared_contract_gaps()`,
  `participant_runtime_capability_contract_gaps()`, and
  `observation_capability_contract_gaps()`.
- Test precedents:
  `test_runtime_conformance.py`, `test_reference_backend_conformance.py`,
  `test_libvirt_conformance.py`, `test_backend_conformance_cli.py`, and
  seeded corpus tests that assert stable diagnostic codes instead of exact
  validator prose.
- Repository policy:
  `.ground-control.yaml`, `.gc/plan-rules.md`, `tools/check_repo_policy.py`,
  `tools/check_requirement_governance.py`, and `tools/verify_all.py`.

## Cross-Cutting Layers

- Profile and corpus ingress: profile ids must keep flowing through
  `aces_contracts.backend_profiles` grammar and root confinement; fixtures and
  profile defaults must keep resolving through `aces_contracts.corpus`. The fix
  must not fetch remote scenarios, use path separators in profile ids, or add
  repo-root parent heuristics.
- SDL and planning layer: any supplied reference scenario must be parsed and
  planned by the existing parser/reference processor against the target
  manifest. Planner diagnostics for unsupported node types, OS families,
  content, accounts, workflow features, or realization requirements are real
  capability evidence, not strings to reinterpret locally in conformance.
- Contract shape layer: manifests, provisioning plans, operation receipts,
  operation statuses, and snapshots must validate through existing Pydantic
  contract models and closed-world schemas. Do not add local DTOs or ad hoc key
  checks for the new branch.
- Manifest authority layer: `supported_contract_versions`, concept bindings,
  capability vocabulary terms, and realization support declarations must pass
  existing validators. Do not suppress unsupported-contract or
  unsupported-capability diagnostics to make a scenario-scoped backend pass.
- Runtime target layer: `RuntimeTarget` component presence and callable
  signatures must still match the manifest. A target that declares a surface it
  does not provide must fail before probe negotiation matters.
- Control-plane/apply layer: live probes must submit through
  `RuntimeControlPlane`. `_call_backend_apply()` must continue to deep-copy the
  baseline snapshot, reject malformed `ApplyResult` values, preserve baseline
  state on failure, and validate snapshot/result contracts.
- Error-envelope layer: report public failures as `Diagnostic` values with
  stable codes, addresses, domains, severities, and redacted messages. Do not
  surface raw tracebacks, native object reprs, libvirt XML, compose files,
  stdout/stderr, host paths, connection URIs, credentials, tokens, or process
  environment.
- OS and secret exposure layer: target conformance must not require secrets in
  CLI arguments or process argv, inspect `~/.secrets`, read host daemon
  inventory, or rely on privileged libvirt/Docker/APTL state in the default
  hermetic verification path.
- Persistence layer: conformance remains report-oriented. Do not add a
  conformance database, native state ledger, or scenario cache. If durable
  report output is later required, reuse existing run-artifact writers rather
  than inventing a writer.

## Extensibility Seam

The seam is a selected live-probe input plus an applicability decision, not a
new profile family. The obvious future variation is a backend- or caller-supplied
reference scenario for a fixed topology. Keep that parameterized as a
`Scenario`/`ProvisioningPlan` source and expected changed-address/snapshot
predicate so future simulation, emulation, and infrastructure backends can
provide supported probes without editing the canonical runner for each backend.

If the realization/applicability declaration must become portable across
processes, extend `backend-manifest-v2` deliberately with schema-publication
governance. Until then, use the existing manifest capability/realization fields
and runner parameter seams rather than publishing a new schema or overloading
backend profiles.

## Gotchas And Anti-Patterns

Avoid:

- equating `provisioning-only`, `orchestration-evaluation`, or
  `full-remote-control-plane` with universal SDL scenario support;
- making a fixed hard-coded `vm` scenario the only proof path for all backends;
- deleting issue #606's mutation check for backends that can realize the
  selected probe scenario;
- treating an unsupported-scenario `OperationStatus(state="failed")` as a
  conformance failure when the failure is well-formed and diagnostically
  explains an out-of-envelope scenario;
- allowing a backend to pass live target conformance with a success-returning
  no-op when a supported probe was selected;
- adding APTL-specific, libvirt-specific, Docker-specific, or simulator-specific
  branches to `aces_conformance`;
- adding duplicate profile maps, capability DTOs, schemas, exception
  hierarchies, report formats, or validation helpers;
- hiding capability under-claims or over-claims by skipping
  `_declared_contract_gaps()` or capability-claim checks;
- using manifest `constraints` prose as the only machine-verifiable authority
  for a new portable claim without a later schema-governed field;
- changing published schemas or profiles without
  `contracts/schema-publication-manifest.json` and generated-schema parity.

## Non-Goals

- Implementing issue #663 in this preflight.
- Certifying APTL, libvirt, the reference backend, or any consumer repository.
- Redesigning backend profiles, published fixture structure, report schemas,
  `RuntimeControlPlane`, `ProvisioningPlan`, `RuntimeSnapshot`, or the
  reference processor.
- Weakening manifest contract coverage, capability-gap diagnostics, target
  shape validation, or snapshot semantic validation.
- Publishing a new schema, controlled vocabulary, backend profile, SDL syntax,
  or native topology fixture in this issue unless implementation proves the
  existing manifest and runner seams cannot carry the distinction.
