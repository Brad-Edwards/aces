"""Libvirt backend participant runtime acceptance tests (issue #614).

Tests are ordered so earlier checks (manifest, conformance, component
construction) gate the deeper behavioral checks (episode lifecycle, action
admission, observation-boundary projection, failure-path rejection, and the
end-to-end paper-scenario proof), covering every issue acceptance criterion.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from aces_backend_libvirt.manifest import create_libvirt_manifest
from aces_backend_libvirt.participant_runtime import LibvirtParticipantRuntime
from aces_backend_libvirt.target import create_libvirt_components
from aces_backend_protocols.capabilities import participant_runtime_capability_contract_gaps
from aces_conformance.conformance import run_target_conformance
from aces_contracts.contracts import (
    ParticipantActionResultModel,
    ParticipantImplementationManifestModel,
    ParticipantImplementationSelectionModel,
)
from aces_contracts.participant_binding import ParticipantActionAdmissionRequest
from aces_processor.models import (
    iter_participant_behavior_history_violations,
    iter_participant_episode_snapshot_violations,
)
from libvirt_participant_proof import LibvirtParticipantProofResult, run_libvirt_participant_proof

from aces.core.runtime.compiler import compile_runtime_model
from aces.core.runtime.control_plane import RuntimeControlPlane
from aces.core.runtime.models import (
    OperationState,
    ParticipantEpisodeTerminalReason,
)
from aces.core.runtime.registry import RuntimeTarget
from aces.core.sdl import parse_sdl

_PAPER_SCENARIO_PATH = Path(__file__).parents[3] / "examples" / "scenarios" / "paper-agent-loop.sdl.yaml"

_DISCLOSURE_REF = "docs/decisions/issue-614-libvirt-participant-runtime.md"


# ---------------------------------------------------------------------------
# Null driver — no real libvirt daemon needed for these structural tests
# ---------------------------------------------------------------------------


class _NullLibvirtDriver:
    """No-op libvirt driver for structural tests that do not call realize()."""

    def realize(self, *, networks, domains):
        from aces_backend_libvirt.driver import DriverResult

        return DriverResult()

    def destroy(self, *, networks, domains):
        from aces_backend_libvirt.driver import DriverResult

        return DriverResult()

    def realized_addresses(self):
        return frozenset()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _libvirt_target_with_participant_runtime() -> RuntimeTarget:
    manifest = create_libvirt_manifest(participant_runtime=True)
    components = create_libvirt_components(manifest=manifest, driver=_NullLibvirtDriver())
    return RuntimeTarget(
        name=manifest.name,
        manifest=manifest,
        provisioner=components.provisioner,
        participant_runtime=components.participant_runtime,
    )


def _libvirt_implementation_manifest() -> ParticipantImplementationManifestModel:
    return ParticipantImplementationManifestModel.model_validate(
        {
            "schema_version": "participant-implementation-manifest/v1",
            "identity": {"name": "libvirt-deterministic-agent", "version": "1.0.0"},
            "implementation_kind": "agent",
            "supported_contract_versions": [
                "participant-implementation-manifest-v1",
                "participant-implementation-provenance-v1",
                "participant-episode-state-envelope-v1",
                "participant-episode-history-event-stream-v1",
                "participant-behavior-history-event-stream-v1",
            ],
            "compatibility": {
                "participant_runtimes": ["libvirt-qemu"],
                "processors": ["aces-reference-processor"],
                "backends": ["libvirt-qemu"],
            },
            "concept_bindings": [
                {"scope": "implementation_kind", "family": "apparatus-declarations"},
                {
                    "scope": "capabilities.supported_participant_contracts",
                    "family": "apparatus-declarations",
                },
                {
                    "scope": "capabilities.supported_decision_surface_modes",
                    "family": "apparatus-declarations",
                },
                {
                    "scope": "capabilities.tool_affordance_expectations",
                    "family": "tools-and-artifacts",
                },
                {"scope": "capabilities.exposure_policy_kinds", "family": "provenance-and-evidence"},
            ],
            "constraints": {
                "max_parallel_episodes": "1",
                "simulation_disclosure": "deterministic-simulation: no live libvirt domain execution",
            },
            "capabilities": {
                "supported_participant_contracts": [
                    "participant-episode-state-envelope-v1",
                    "participant-episode-history-event-stream-v1",
                    "participant-behavior-history-event-stream-v1",
                ],
                "supported_decision_surface_modes": ["policy-directed"],
                "tool_affordance_expectations": ["http-api"],
                "exposure_policy_kinds": ["task-statement", "observation-stream"],
            },
        }
    )


def _libvirt_implementation_selection(participant_address: str) -> ParticipantImplementationSelectionModel:
    return ParticipantImplementationSelectionModel.model_validate(
        {
            "participant_address": participant_address,
            "implementation_identity": {"name": "libvirt-deterministic-agent", "version": "1.0.0"},
            "manifest_ref": "contracts/fixtures/participant-implementation-manifest/libvirt-deterministic.json",
            "manifest_digest": "sha256:" + "1" * 64,
            "selected_decision_surface_mode": "policy-directed",
            "participant_contract_versions": [
                "participant-episode-state-envelope-v1",
                "participant-behavior-history-event-stream-v1",
            ],
            "exposure_policy": {
                "policy_id": "libvirt-paper-agent-policy",
                "policy_version": "1.0.0",
                "policy_digest": "sha256:" + "3" * 64,
                "exposure_policy_kinds": ["task-statement", "observation-stream"],
                "disclosed_refs": [],
                "withheld_refs": [
                    "content.evaluator-notes",
                    "nodes.customer-db.services.postgres",
                    "nodes.wazuh-manager",
                    "nodes.wazuh-indexer",
                    "nodes.participant-policy-gate",
                ],
                "tool_affordance_refs": [],
                "visibility_scope_refs": [],
            },
        }
    )


def _paper_scenario_action_result(
    *,
    participant_address: str,
    episode_id: str,
    action_instance_id: str,
    action_contract_address: str,
    contract_spec: dict,
) -> ParticipantActionResultModel:
    """Build a deterministic succeeded action_result for the paper scenario action contract.

    Reports all declared preconditions with empty refs and only the ``no_effect``
    effects (which require no target_refs or evidence_refs). This avoids any
    hidden-ref violations while satisfying the SEM-211 precondition completeness check.
    """
    preconditions_raw = contract_spec.get("preconditions", ())
    effects_raw = contract_spec.get("effects", ())

    preconditions = []
    for pc in preconditions_raw:
        if not isinstance(pc, dict) or not pc.get("precondition_id") or not pc.get("precondition_class"):
            continue
        preconditions.append(
            {
                "precondition_id": pc["precondition_id"],
                "precondition_class": pc["precondition_class"],
                "status": "satisfied",
                "participant_address": participant_address,
                "episode_id": episode_id,
                "action_contract_address": action_contract_address,
                "observation_point": f"{action_instance_id}:pc-{pc['precondition_id']}",
                "support_refs": [],
                "evidence_refs": [],
            }
        )

    effects = []
    for eff in effects_raw:
        if not isinstance(eff, dict) or not eff.get("effect_id") or not eff.get("effect_class"):
            continue
        if eff["effect_class"] == "no_effect":
            effects.append(
                {
                    "effect_id": eff["effect_id"],
                    "effect_class": eff["effect_class"],
                    "description": eff.get("description", "No effect (deterministic proof)."),
                }
            )

    return ParticipantActionResultModel.model_validate(
        {
            "status": "succeeded",
            "participant_address": participant_address,
            "episode_id": episode_id,
            "action_instance_id": action_instance_id,
            "action_contract_address": action_contract_address,
            "observation_point": f"{action_instance_id}:terminal-observation",
            "preconditions": preconditions,
            "effects": effects,
            "observations": [f"{action_instance_id}:terminal-observation"],
            "evidence_refs": [],
        }
    )


# ---------------------------------------------------------------------------
# AC-1: Manifest declares participant_runtime when participant_runtime=True
# ---------------------------------------------------------------------------


def test_ac1_manifest_declares_participant_runtime_when_enabled():
    manifest = create_libvirt_manifest(participant_runtime=True)

    assert manifest.has_participant_runtime is True
    assert manifest.participant_runtime is not None
    pr = manifest.participant_runtime
    assert pr.name == "libvirt-deterministic-participant-runtime"
    assert "red" in pr.supported_participant_roles
    assert pr.supported_behavior_features
    assert pr.supported_interaction_features
    assert "participant-episode-state-envelope-v1" in manifest.supported_contract_versions
    assert "participant-episode-history-event-stream-v1" in manifest.supported_contract_versions
    assert "participant-behavior-history-event-stream-v1" in manifest.supported_contract_versions


def test_ac1_manifest_default_is_provisioning_only():
    manifest = create_libvirt_manifest()
    assert manifest.has_participant_runtime is False


# ---------------------------------------------------------------------------
# AC-2: run_target_conformance passes for libvirt target with participant_runtime
# ---------------------------------------------------------------------------


def test_ac2_conformance_passes_with_participant_runtime_manifest():
    target = _libvirt_target_with_participant_runtime()
    report = run_target_conformance(target)

    assert report.passed is True, f"conformance failed: {report.diagnostics}"
    assert report.unsupported_contract_gaps == ()
    assert report.unsupported_capability_gaps == ()


# ---------------------------------------------------------------------------
# AC-3: create_libvirt_components does not raise when participant_runtime=True
# ---------------------------------------------------------------------------


def test_ac3_components_construction_succeeds_with_participant_runtime():
    manifest = create_libvirt_manifest(participant_runtime=True)
    components = create_libvirt_components(manifest=manifest, driver=_NullLibvirtDriver())

    assert components.participant_runtime is not None
    assert isinstance(components.participant_runtime, LibvirtParticipantRuntime)


def test_ac3_components_construction_still_raises_for_orchestrator():
    from aces_backend_stubs.stubs import create_stub_manifest

    orchestrator_manifest = create_stub_manifest()
    with pytest.raises(ValueError, match="orchestrator"):
        create_libvirt_components(manifest=orchestrator_manifest, driver=_NullLibvirtDriver())


# ---------------------------------------------------------------------------
# AC-4: Full RUN-311 episode lifecycle runs end-to-end via control plane
# ---------------------------------------------------------------------------


def test_ac4_episode_lifecycle_initialize_reset_terminate_restart():
    target = _libvirt_target_with_participant_runtime()
    control_plane = RuntimeControlPlane(target)
    participant_address = "participant.behavior.paper-agent"

    def _episode_state() -> dict:
        snap = control_plane.get_snapshot().snapshot
        return snap.participant_episode_results[participant_address]

    r_init = control_plane.initialize_participant_episode(participant_address, episode_id="ep-1")
    init_state = _episode_state()
    assert init_state["episode_id"] == "ep-1"
    assert init_state["sequence_number"] == 0

    r_reset = control_plane.reset_participant_episode(participant_address, reason="clean slate for AC-4")
    # Direct post-reset state assertions, independent of the snapshot validator:
    # reset MUST allocate a new episode and advance the sequence. Without these,
    # a success-returning no-op reset would pass every receipt/status/validator
    # check, because the later restart's jump to sequence=1 masks the missing
    # reset side-effect.
    reset_state = _episode_state()
    assert reset_state["episode_id"] != "ep-1"
    assert reset_state["sequence_number"] == 1
    assert reset_state["previous_episode_id"] == "ep-1"

    r_term = control_plane.terminate_participant_episode(
        participant_address,
        terminal_reason=ParticipantEpisodeTerminalReason.COMPLETED,
        detail="AC-4 test complete",
    )
    r_restart = control_plane.restart_participant_episode(participant_address, reason="second run")
    # Direct post-restart state assertions: restart MUST allocate a further
    # episode chained off the reset episode and advance the sequence again.
    restart_state = _episode_state()
    assert restart_state["episode_id"] not in {"ep-1", reset_state["episode_id"]}
    assert restart_state["sequence_number"] == 2
    assert restart_state["previous_episode_id"] == reset_state["episode_id"]

    r_term2 = control_plane.terminate_participant_episode(
        participant_address,
        terminal_reason=ParticipantEpisodeTerminalReason.COMPLETED,
        detail="AC-4 second run complete",
    )

    for receipt, label in [
        (r_init, "initialize"),
        (r_reset, "reset"),
        (r_term, "terminate"),
        (r_restart, "restart"),
        (r_term2, "terminate2"),
    ]:
        op = control_plane.get_operation(receipt.operation_id)
        assert receipt.accepted is True, f"{label} was not accepted"
        assert op is not None
        assert op.state == OperationState.SUCCEEDED, f"{label} operation did not succeed: {op}"

    snapshot = control_plane.get_snapshot().snapshot
    episode_violations = list(
        iter_participant_episode_snapshot_violations(
            snapshot.participant_episode_results,
            snapshot.participant_episode_history,
        )
    )
    assert episode_violations == []


# ---------------------------------------------------------------------------
# AC-5: admit_participant_action records behavior history with no internal refs
# ---------------------------------------------------------------------------


def test_ac5_admit_action_records_behavior_history_without_internal_refs():
    sdl = parse_sdl(_PAPER_SCENARIO_PATH.read_text())
    runtime_model = compile_runtime_model(sdl)
    behavior = runtime_model.participant_behaviors["participant.behavior.paper-agent"]
    action_address = behavior.action_contract_addresses[0]
    boundary_address = behavior.observation_boundary_addresses[0]
    contract = runtime_model.action_contracts[action_address]

    target = _libvirt_target_with_participant_runtime()
    control_plane = RuntimeControlPlane(target)
    control_plane.initialize_participant_episode(behavior.address, episode_id="ep-5")

    action_result = _paper_scenario_action_result(
        participant_address=behavior.address,
        episode_id="ep-5",
        action_instance_id="probe-0001",
        action_contract_address=action_address,
        contract_spec=contract.spec,
    )
    admission_request = ParticipantActionAdmissionRequest(
        participant_address=behavior.address,
        action_contract_address=action_address,
        observation_boundary_address=boundary_address,
        action_instance_id="probe-0001",
        implementation_manifest=_libvirt_implementation_manifest(),
        implementation_selection=_libvirt_implementation_selection(behavior.address),
        visible_refs=(),
        disclosed_refs=(),
        evidence_refs=(),
        observation_boundary_evidence_refs=(),
        action_result=action_result,
    )
    receipt = control_plane.admit_participant_action(behavior, admission_request)
    op = control_plane.get_operation(receipt.operation_id)

    assert receipt.accepted is True, f"admit_action rejected: {op}"
    assert op is not None
    assert op.state == OperationState.SUCCEEDED

    snapshot = control_plane.get_snapshot().snapshot
    behavior_history = snapshot.participant_behavior_history.get(behavior.address, [])

    # Three events: ACTION_ATTEMPTED, STATE_TRANSITION_RECORDED, OBSERVATION_EMITTED
    assert [e["event_type"] for e in behavior_history] == [
        "action_attempted",
        "state_transition_recorded",
        "observation_emitted",
    ]

    # Actor provenance names the libvirt deterministic agent (not the backend)
    assert "libvirt-deterministic-agent" in behavior_history[0]["actor_provenance"]
    assert "participant-implementation:" in behavior_history[0]["actor_provenance"]

    # Terminal observation is anchored to the correct action/boundary
    obs_event = behavior_history[-1]
    assert obs_event["action_contract_address"] == action_address
    assert obs_event["observation_boundary_address"] == boundary_address

    # No internal (withheld) refs leak into the observation details
    internal_refs = {
        "content.evaluator-notes",
        "nodes.customer-db.services.postgres",
        "nodes.wazuh-manager",
        "nodes.wazuh-indexer",
        "nodes.participant-policy-gate",
    }
    details = obs_event.get("details", {})
    emitted_refs = (
        set(details.get("visible_refs", []))
        | set(details.get("disclosed_refs", []))
        | set(details.get("evidence_refs", []))
    )
    assert emitted_refs.isdisjoint(internal_refs), f"internal refs leaked: {emitted_refs & internal_refs}"

    # Episode and behavior history are structurally valid
    assert (
        list(
            iter_participant_episode_snapshot_violations(
                snapshot.participant_episode_results,
                snapshot.participant_episode_history,
            )
        )
        == []
    )
    assert (
        list(
            iter_participant_behavior_history_violations(
                behavior_history,
                action_contracts=runtime_model.action_contracts,
                observation_boundaries=runtime_model.observation_boundaries,
                participant_episode_history=snapshot.participant_episode_history.get(behavior.address, []),
                expected_participant_address=behavior.address,
            )
        )
        == []
    )


# ---------------------------------------------------------------------------
# AC: Unsafe / missing / unsupported bindings fail with redacted diagnostics
#     and a failed control-plane operation status (no history rewrite)
# ---------------------------------------------------------------------------


def test_ac_missing_episode_binding_fails_with_redacted_diagnostic():
    sdl = parse_sdl(_PAPER_SCENARIO_PATH.read_text())
    runtime_model = compile_runtime_model(sdl)
    behavior = runtime_model.participant_behaviors["participant.behavior.paper-agent"]
    action_address = behavior.action_contract_addresses[0]
    boundary_address = behavior.observation_boundary_addresses[0]
    contract = runtime_model.action_contracts[action_address]

    target = _libvirt_target_with_participant_runtime()
    control_plane = RuntimeControlPlane(target)

    # No initialize_participant_episode() — the binding has no live episode.
    action_result = _paper_scenario_action_result(
        participant_address=behavior.address,
        episode_id="ep-missing",
        action_instance_id="probe-0001",
        action_contract_address=action_address,
        contract_spec=contract.spec,
    )
    admission_request = ParticipantActionAdmissionRequest(
        participant_address=behavior.address,
        action_contract_address=action_address,
        observation_boundary_address=boundary_address,
        action_instance_id="probe-0001",
        implementation_manifest=_libvirt_implementation_manifest(),
        implementation_selection=_libvirt_implementation_selection(behavior.address),
        visible_refs=(),
        disclosed_refs=(),
        evidence_refs=(),
        observation_boundary_evidence_refs=(),
        action_result=action_result,
    )

    receipt = control_plane.admit_participant_action(behavior, admission_request)
    status = control_plane.get_operation(receipt.operation_id)

    # The submission is acknowledged, but the binding execution fails: the
    # control-plane operation status is FAILED, not a silent success.
    assert status is not None
    assert status.state == OperationState.FAILED
    assert status.diagnostics, "expected at least one diagnostic on the failed binding"
    assert any("no live episode" in diag.message for diag in status.diagnostics)

    # Redacted: no backend-private libvirt detail, host path, XML, or argv leaks
    # into the public diagnostic surface.
    for diag in status.diagnostics:
        lowered = diag.message.lower()
        assert "<domain" not in lowered
        assert "/var/lib/libvirt" not in lowered
        assert "qemu:///" not in lowered

    # No behavior-history rewrite occurred for the rejected binding.
    snapshot = control_plane.get_snapshot().snapshot
    assert snapshot.participant_behavior_history.get(behavior.address, []) == []


# ---------------------------------------------------------------------------
# AC-6: No capability contract gaps in the participant_runtime manifest
# ---------------------------------------------------------------------------


def test_ac6_no_participant_runtime_capability_contract_gaps():
    manifest = create_libvirt_manifest(participant_runtime=True)
    gaps = participant_runtime_capability_contract_gaps(manifest)
    assert gaps == (), f"unexpected capability contract gaps: {gaps}"


# ---------------------------------------------------------------------------
# AC-7: run_libvirt_participant_proof validates the paper scenario end-to-end
# ---------------------------------------------------------------------------


def test_ac7_proof_driver_validates_paper_scenario():
    result = run_libvirt_participant_proof(_PAPER_SCENARIO_PATH)

    assert isinstance(result, LibvirtParticipantProofResult)
    assert result.errors == (), f"proof errors: {result.errors}"
    assert result.episode_snapshot_violations == (), (
        f"episode snapshot violations: {result.episode_snapshot_violations}"
    )
    assert result.behavior_history_violations == (), (
        f"behavior history violations: {result.behavior_history_violations}"
    )
