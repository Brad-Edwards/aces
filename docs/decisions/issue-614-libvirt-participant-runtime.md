# Issue 614 Libvirt Participant Runtime

Date: 2026-06-29

Issue: #614.

Requirement: none. The GitHub issue title, body, and acceptance criteria are
the contract.

## Summary

This decision record documents the design choices made when implementing
`LibvirtParticipantRuntime` for the paper scenario's red participant.  The
implementation scope is narrow: a structural proof runtime that drives
RUN-311 episode lifecycle transitions inside the libvirt provisioning backend
without invoking real libvirt domain operations.

## Binding Sources

All pre-existing guardrails from
`docs/decisions/issue-614-libvirt-participant-runtime-preflight.md` are
binding.  Specifically:

- ADR-013 owns the participant episode lifecycle.
- ADR-022, ADR-054, ADR-060, and
  `docs/research/participant-backend-contracts/preflight-guardrails.md` own
  participant behavior history, action/observation semantics, and
  backend-facing participant runtime declarations.
- ADR-041 and
  `docs/decisions/issue-599-participant-implementation-binding-preflight.md`
  own participant implementation manifests, selection, exposure policy, actor
  provenance, and the provider-neutral action-admission request.
- `docs/decisions/issue-598-paper-reference-scenario-preflight.md` and
  `examples/scenarios/paper-agent-loop.sdl.yaml` own the authored scenario
  shape.

## Architecture Decisions

### 1. Extract `BaseParticipantRuntime`

**Decision:** Extract the RUN-311 episode lifecycle from
`ReferenceParticipantRuntime` into
`aces_backend_protocols.participant_runtime_base.BaseParticipantRuntime`.
`ReferenceParticipantRuntime` becomes a zero-override subclass.

**Rationale:** The lifecycle logic (initialize → reset/restart → terminate,
action admission with binding events, history tracking) is backend-neutral.
Duplicating it in the libvirt backend would create maintenance debt and risk
divergence.  The base carries no backend-specific hook; `LibvirtParticipantRuntime`
overrides `admit_action` to model the domain side-effect (via the injected
adapter) and then delegates to `super().admit_action`, so the shared machinery
stays free of unused extension parameters.

### 2. Domain adapter protocol boundary

**Decision:** Introduce `LibvirtParticipantDomainAdapter` as a `Protocol` in
`aces_backend_libvirt.participant_domain`.  `LibvirtParticipantRuntime`
accepts an adapter at construction time, defaulting to
`DeterministicParticipantDomainAdapter` (identity: returns request
unchanged).

**Rationale:** Live libvirt domain execution (network probes, VM command
dispatch, Wazuh evidence collection) is intentionally out of scope for this
issue.  The Protocol boundary makes the structural proof independently
testable and allows future live adapters to be injected without modifying the
runtime.  The deterministic adapter is the disclosed limitation noted in the
manifest's `feature_support` entries.

### 3. Manifest gating via `participant_runtime=True`

**Decision:** `create_libvirt_manifest()` defaults to provisioning-only.
Passing `participant_runtime=True` adds the six participant contract versions
and a `ParticipantRuntimeCapabilities` with `disclosed_weak` feature support
for all declared behavior and interaction features.

**Rationale:** Provisioning deployments that do not need participant episode
support should not carry the capability declaration overhead.  The flag keeps
the default manifest minimal and avoids introducing participant runtime
capability gaps for existing libvirt provisioning targets.

### 4. Provisioning-only guard lifted for `participant_runtime` arm

**Decision:** `create_libvirt_components` continues to raise `ValueError` for
orchestrator or evaluator manifests.  It no longer raises for participant
runtime manifests.

**Rationale:** The original guard blocked the entire runtime surface.
Participant episode support is a distinct, bounded capability that does not
require orchestration or evaluation surfaces.  Keeping the orchestrator and
evaluator arms of the guard ensures no accidental mis-registration.

### 5. Address-driven proof driver

**Decision:** `run_libvirt_participant_proof(sdl_path)` loads the SDL,
compiles the runtime model, then drives the full episode lifecycle (initialize
→ one action admission per view-transition anchor → terminate) using the
`action_instance_id` values extracted from the compiled observation boundary's
`view_transitions` field, rather than generating synthetic IDs.

**Rationale:** The behavior history validator checks that each view-transition
anchor resolves to a real `OBSERVATION_EMITTED` event in the behavior history.
The anchor format is `{action_instance_id}:terminal-observation`.  Using
view-transition `action_instance_id` values (e.g., `"probe-0001"` for the
`discover-customer-portal` transition in the paper scenario) ensures anchors
resolve without requiring the proof driver to be scenario-aware.

**Placement:** The proof driver lives in the test layer
(`tests/libvirt_participant_proof.py`), not in the `aces_backend_libvirt`
package. The ADR-036 module boundaries make `aces_backend_libvirt` a leaf that
may only reach `aces_runtime.registry` — it must not import the compiler
(`aces_processor`), the SDL parser (`aces_sdl`), or `aces_runtime.control_plane`.
The proof compiles SDL and drives the control plane, so it is integration/
verification code: it belongs with the tests that consume it (the tests tree is
exempt from the package module-boundary policy), keeping the shipped backend
component a clean leaf. A future reusable cross-backend corpus harness (#600,
out of scope here) would instead live in `aces_operations` against the
`RuntimeManager` API.

### 6. SEM-211 action result: all preconditions, `no_effect` effects only

**Decision:** The proof action result reports all declared preconditions as
`satisfied` with empty `support_refs` and `evidence_refs`, and reports only
`no_effect` effects.

**Rationale:**
- `iter_participant_behavior_history_violations` requires that all declared
  preconditions be reported when the contract has SEM-211 precondition/effect
  classes.
- Non-`no_effect` effects require `target_refs` or `evidence_refs`.  Including
  refs for internal scenario nodes (e.g., `nodes.wazuh-manager`) would trigger
  hidden-ref visibility violations because those nodes remain hidden throughout
  the proof episode.  Reporting only `no_effect` effects avoids all hidden-ref
  and boundary-evidence validation failures without sacrificing lifecycle
  correctness.

## Disclosed Limitations

The `DeterministicParticipantDomainAdapter` does NOT perform:

- Real libvirt VM actions (boot, halt, command dispatch).
- Network connectivity checks or port probes.
- Wazuh evidence collection.

All behavior features (`action_contracts`, `observation_boundaries`,
`behavior_history`, `state_transitions`) and the `contention` interaction
feature are declared `disclosed_weak` in the manifest with this file as the
`disclosure_ref`.  Live domain execution requires a custom
`LibvirtParticipantDomainAdapter` implementation injected at construction
time.

## Files Changed

- `packages/aces_backend_protocols/participant_runtime_base.py` — new
- `packages/aces_reference_backend/participant_runtime.py` — refactored to
  subclass `BaseParticipantRuntime`
- `packages/aces_backend_libvirt/participant_domain.py` — new
- `packages/aces_backend_libvirt/participant_runtime.py` — new
- `tests/libvirt_participant_proof.py` — new (test-layer proof driver; see
  decision 5 "Placement")
- `packages/aces_backend_libvirt/manifest.py` — `participant_runtime=True` gate
- `packages/aces_backend_libvirt/target.py` — lifted participant runtime guard
- `packages/aces_backend_libvirt/__init__.py` — new exports
- `tests/test_libvirt_participant_runtime.py` — acceptance-criteria tests
  (manifest gating, conformance, episode lifecycle, action admission,
  observation-boundary projection, failure-path rejection, end-to-end proof)
