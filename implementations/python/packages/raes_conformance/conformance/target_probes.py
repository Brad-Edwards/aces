"""Target/control-plane conformance probes and the default probe scenario."""

from __future__ import annotations

from textwrap import dedent
from typing import Any

from raes_backend_protocols.manifest import backend_manifest_payload
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.participant_episode import (
    ParticipantEpisodeTerminalReason,
    iter_participant_episode_snapshot_violations,
)
from raes_contracts.planning import ProvisioningPlan, RuntimeDomain
from raes_contracts.runtime_state import RuntimeSnapshotEnvelope
from raes_processor.reference import ScenarioInput, run_reference_processor
from raes_runtime.control_plane import RuntimeControlPlane
from raes_runtime.registry import RuntimeTarget

from raes_conformance.conformance.diagnostics import _SEMANTIC_INVALID_DIAGNOSTIC_CODE, _diagnostic
from raes_conformance.conformance.participant_execution_probes import (
    _drive_participant_execution_probe,
    _participant_execution_probe_snapshot,
)
from raes_conformance.conformance.profiles import (
    BackendCapabilityProfile,
    BackendProfileSelector,
    _to_known_profile,
)
from raes_conformance.conformance.report import ConformanceCaseResult
from raes_conformance.conformance.semantics import _semantic_diagnostics
from raes_conformance.conformance.validators import _validate_payload

# Default reference scenario the target-conformance adapter probe drives when the
# caller supplies none. Backend-neutral: a single generic linux vm node.
#
# Issue #663 makes this a *default*, not a universal assumption. A fixed-topology
# emulation or bounded simulation backend that cannot realize this generic
# scenario supplies one it can realize via
# ``run_target_conformance(reference_scenario=...)``; the target probe then holds
# it to adapter-level accounting for *that* scenario. This runner-parameter
# bridge — superseded by the realizability-envelope design (#667) and the
# scenario/envelope subsumption relation (#668), which will let the probe
# negotiate an in-envelope witness instead of carrying a default at all.
_DEFAULT_CONFORMANCE_SCENARIO = dedent(
    """
    name: conformance
    nodes:
      vm:
        type: vm
        os: linux
        resources: {ram: 1 gib, cpu: 1}
        conditions: {health: ops}
        roles: {ops: operator}
    conditions:
      health: {proposition: health-state, command: /bin/true, interval: 15}
    entities:
      blue: {role: blue}
    propositions:
      health-state:
        description: The conformance VM is declared in the admitted scenario.
        subjects: [nodes.vm]
        basis: declared_state
        predicate:
          kind: presence
          property: node
          semantic_ref: urn:aces:declared-property:node
          operator: exists
    assertions:
      health:
        proposition: health-state
        role: postcondition
    objectives:
      validate:
        entity: blue
        success: {assertions: [health]}
    workflows:
      response:
        start: run
        steps:
          run:
            type: objective
            objective: validate
            on_success: finish
          finish: {type: end}
    """
)


def _participant_snapshot_consistency_case(
    control_plane: RuntimeControlPlane,
    participant_address: str,
    contract_name: str,
) -> ConformanceCaseResult:
    """Validate the post-lifecycle snapshot exposes live participant-episode state.

    A target that registers a participant runtime but never populates the
    snapshot fields fails the snapshot-state-not-empty check, so the live
    conformance probe cannot certify a backend whose runtime accepts every
    action but produces no observable state.
    """

    snapshot = control_plane.snapshot
    final_diagnostics: list[Diagnostic] = []
    if not snapshot.participant_episode_results:
        final_diagnostics.append(
            _diagnostic(
                "conformance.participant-runtime-empty",
                f"runtime.snapshot.participant-episode-results.{participant_address}",
                (
                    "Participant runtime accepted every control action but the snapshot "
                    "exposes no participant_episode_results. RUN-311 backends must publish "
                    "live episode state through the snapshot."
                ),
            )
        )
    if not snapshot.participant_episode_history:
        final_diagnostics.append(
            _diagnostic(
                "conformance.participant-runtime-empty",
                f"runtime.snapshot.participant-episode-history.{participant_address}",
                (
                    "Participant runtime accepted every control action but the snapshot "
                    "exposes no participant_episode_history. RUN-311 backends must publish "
                    "live episode history events through the snapshot."
                ),
            )
        )
    for address, message in iter_participant_episode_snapshot_violations(
        snapshot.participant_episode_results,
        snapshot.participant_episode_history,
    ):
        final_diagnostics.append(_diagnostic(_SEMANTIC_INVALID_DIAGNOSTIC_CODE, address, message))
    return ConformanceCaseResult(
        name="participant-snapshot-consistent",
        contract_name=contract_name,
        valid=True,
        passed=not final_diagnostics,
        diagnostics=tuple(final_diagnostics),
    )


def _drive_participant_episode_probe(
    control_plane: RuntimeControlPlane,
    *,
    participant_address: str,
) -> list[ConformanceCaseResult]:
    """Drive a full RUN-311 participant lifecycle via the control plane.

    Each control action becomes one ``ConformanceCaseResult`` so that
    ``run_target_conformance`` reports a separate failure for any step
    the backend rejects, and a final case validates the resulting
    ``participant_episode_results`` / ``participant_episode_history``
    against the shared snapshot invariants.

    A target that registers a participant runtime but never populates
    the snapshot fields fails the snapshot-state-not-empty check, so
    the live conformance probe cannot certify a backend whose runtime
    accepts every action but produces no observable state.
    """

    cases: list[ConformanceCaseResult] = []
    actions = (
        ("participant-initialize", lambda: control_plane.initialize_participant_episode(participant_address)),
        ("participant-reset", lambda: control_plane.reset_participant_episode(participant_address)),
        (
            "participant-terminate",
            lambda: control_plane.terminate_participant_episode(
                participant_address,
                terminal_reason=ParticipantEpisodeTerminalReason.COMPLETED,
            ),
        ),
        ("participant-restart", lambda: control_plane.restart_participant_episode(participant_address)),
    )
    contract_name = "participant-episode-state-envelope-v1"
    for case_name, invoke in actions:
        try:
            receipt = invoke()
        except Exception as exc:
            # Defensive: a well-behaved backend does not raise here; surface it as a diagnostic.
            cases.append(
                ConformanceCaseResult(
                    name=case_name,
                    contract_name=contract_name,
                    valid=True,
                    passed=False,
                    diagnostics=(
                        _diagnostic(
                            "conformance.participant-runtime-failed",
                            f"runtime.control-plane.participant.{participant_address}",
                            f"{case_name} raised {type(exc).__name__}: {exc}",
                        ),
                    ),
                )
            )
            continue
        status = control_plane.get_operation(receipt.operation_id)
        diagnostics: list[Diagnostic] = []
        if status is None:
            diagnostics.append(
                _diagnostic(
                    "conformance.participant-runtime-missing-status",
                    f"runtime.control-plane.participant.{participant_address}",
                    f"{case_name} did not produce an OperationStatus record",
                )
            )
        elif status.state.value not in {"succeeded"}:
            diagnostics.append(
                _diagnostic(
                    "conformance.participant-runtime-failed",
                    f"runtime.control-plane.participant.{participant_address}",
                    (
                        f"{case_name} returned state {status.state.value!r} with diagnostics: "
                        + "; ".join(diag.message for diag in status.diagnostics)
                    ),
                )
            )
        cases.append(
            ConformanceCaseResult(
                name=case_name,
                contract_name=contract_name,
                valid=True,
                passed=not diagnostics,
                diagnostics=tuple(diagnostics),
            )
        )

    cases.append(_participant_snapshot_consistency_case(control_plane, participant_address, contract_name))
    return cases


def _provisioning_probe_case(
    control_plane: RuntimeControlPlane,
    provisioning_plan: ProvisioningPlan,
) -> ConformanceCaseResult:
    """Drive hermetic target-adapter provisioning and prove portable mutation.

    Backend-neutral (issue #606): every known profile requires a provisioner,
    so target conformance always submits the reference scenario's provisioning
    plan through the control plane. A backend that accepts the plan but realizes
    nothing — a failed apply, or a success that reports no changed addresses —
    fails here rather than certifying clean on manifest validation alone.
    """

    address = "runtime.control-plane.provisioning"
    receipt = control_plane.submit_provisioning(provisioning_plan)
    status = control_plane.get_operation(receipt.operation_id)
    diagnostics: list[Diagnostic] = []
    if status is None:
        diagnostics.append(
            _diagnostic(
                "conformance.provisioning-missing-status",
                address,
                "Provisioning submission did not produce an OperationStatus record.",
            )
        )
    elif status.state.value != "succeeded":
        diagnostics.append(
            _diagnostic(
                "conformance.provisioning-failed",
                address,
                (
                    f"Provisioning returned state {status.state.value!r} with diagnostics: "
                    + "; ".join(diag.message for diag in status.diagnostics)
                ),
            )
        )
    elif not status.changed_addresses:
        diagnostics.append(
            _diagnostic(
                "conformance.provisioning-empty",
                address,
                (
                    "Provisioning succeeded but reported no changed addresses; the backend "
                    "did not realize the scenario, so the snapshot was not mutated."
                ),
            )
        )
    return ConformanceCaseResult(
        name="target-provisioning",
        contract_name="operation-status-v1",
        valid=True,
        passed=not diagnostics,
        diagnostics=tuple(diagnostics),
    )


def _hermetic_snapshot_payload(control_plane: RuntimeControlPlane) -> dict[str, Any]:
    """Serialize the hermetic control-plane snapshot to its portable envelope shape."""

    return {
        "schema_version": RuntimeSnapshotEnvelope().schema_version,
        "entries": {
            address: {
                "address": entry.address,
                "domain": entry.domain.value,
                "resource_type": entry.resource_type,
                "payload": dict(entry.payload),
                "ordering_dependencies": list(entry.ordering_dependencies),
                "refresh_dependencies": list(entry.refresh_dependencies),
                "status": entry.status,
            }
            for address, entry in control_plane.snapshot.entries.items()
        },
        "orchestration_results": dict(control_plane.snapshot.orchestration_results),
        "orchestration_history": dict(control_plane.snapshot.orchestration_history),
        "evaluation_results": dict(control_plane.snapshot.evaluation_results),
        "evaluation_history": dict(control_plane.snapshot.evaluation_history),
        "participant_episode_results": dict(control_plane.snapshot.participant_episode_results),
        "participant_episode_history": {
            participant_address: list(events)
            for participant_address, events in control_plane.snapshot.participant_episode_history.items()
        },
        "participant_behavior_history": {
            participant_address: list(events)
            for participant_address, events in control_plane.snapshot.participant_behavior_history.items()
        },
        "participant_control_history": {
            participant_address: list(events)
            for participant_address, events in control_plane.snapshot.participant_control_history.items()
        },
        "participant_autonomous_execution_states": dict(control_plane.snapshot.participant_autonomous_execution_states),
        "participant_execution_services": dict(control_plane.snapshot.participant_execution_services),
        "shared_state_records": dict(control_plane.snapshot.shared_state_records),
        "shared_state_history": {
            state_address: list(records)
            for state_address, records in control_plane.snapshot.shared_state_history.items()
        },
        "joint_action_records": dict(control_plane.snapshot.joint_action_records),
        "time_management_contexts": dict(control_plane.snapshot.time_management_contexts),
        "time_model_state": (
            control_plane.snapshot.time_model_state.model_dump(mode="json")
            if control_plane.snapshot.time_model_state is not None
            else None
        ),
        "metadata": dict(control_plane.snapshot.metadata),
    }


def _hermetic_snapshot_case(control_plane: RuntimeControlPlane) -> ConformanceCaseResult:
    """Validate the post-provisioning snapshot and prove it was mutated.

    Runs the ``runtime-snapshot-v1`` schema + semantic checks on the hermetic
    snapshot and additionally requires at least one provisioning-domain entry
    (issue #606), so a target cannot pass with a schema-valid but empty
    (unmutated) snapshot.
    """

    snapshot_payload = _hermetic_snapshot_payload(control_plane)
    diagnostics = [
        *_validate_payload("runtime-snapshot-v1", snapshot_payload),
        *_semantic_diagnostics("runtime-snapshot-v1", snapshot_payload),
    ]
    has_provisioning_entry = any(
        entry.domain == RuntimeDomain.PROVISIONING for entry in control_plane.snapshot.entries.values()
    )
    if not has_provisioning_entry:
        diagnostics.append(
            _diagnostic(
                "conformance.snapshot-not-mutated",
                "runtime.snapshot.entries",
                (
                    "Hermetic snapshot carries no provisioning-domain entry after the provisioning "
                    "probe; the backend validated contracts without realizing runtime state."
                ),
            )
        )
    return ConformanceCaseResult(
        name="target-snapshot",
        contract_name="runtime-snapshot-v1",
        valid=True,
        passed=not diagnostics,
        diagnostics=tuple(diagnostics),
    )


def _target_adapter_cases(
    target: RuntimeTarget,
    profile: BackendProfileSelector,
    *,
    reference_scenario: ScenarioInput | None = None,
) -> tuple[ConformanceCaseResult, ...]:
    """Run target-adapter probes appropriate for known runtime surfaces only.

    Every known profile requires a provisioner, so target conformance always
    runs a backend-neutral provisioning probe that proves adapter-driven snapshot
    mutation (issue #606), not daemon or guest observation — provisioning-only backends included, which must not
    pass on manifest validation alone. Orchestration, evaluation, and the
    participant-episode probe additionally run for the richer runtime surfaces
    that declare those roles. For an unknown profile id we run only the
    universally-safe manifest validation case and skip the target probes, since
    their runtime contract is not known to this implementation.

    The probe drives ``reference_scenario`` when supplied, else
    ``_DEFAULT_CONFORMANCE_SCENARIO`` (issue #663). Whichever scenario is
    selected is held to adapter-level operation accounting (the #606 mutation
    guard is unchanged); the parameter only stops the probe assuming *every* backend can
    realize one hard-coded scenario.
    """

    cases: list[ConformanceCaseResult] = []
    manifest_payload = backend_manifest_payload(target.manifest)
    manifest_diags = _validate_payload("backend-manifest-v2", manifest_payload)
    cases.append(
        ConformanceCaseResult(
            name="target-manifest",
            contract_name="backend-manifest-v2",
            valid=True,
            passed=not manifest_diags,
            diagnostics=tuple(manifest_diags),
        )
    )

    known = _to_known_profile(profile)
    if known is None:
        return tuple(cases)

    scenario = _DEFAULT_CONFORMANCE_SCENARIO if reference_scenario is None else reference_scenario
    execution_plan = run_reference_processor(scenario, target.manifest).execution_plan
    control_plane = RuntimeControlPlane(
        target,
        initial_snapshot=_participant_execution_probe_snapshot(target),
    )
    cases.append(_provisioning_probe_case(control_plane, execution_plan.provisioning))
    if known != BackendCapabilityProfile.PROVISIONING_ONLY:
        if target.orchestrator is not None:
            control_plane.submit_orchestration(execution_plan.orchestration)
        if target.evaluator is not None:
            control_plane.submit_evaluation(execution_plan.evaluation)
        if target.participant_runtime is not None:
            cases.extend(
                _drive_participant_episode_probe(
                    control_plane,
                    participant_address="participant.conformance",
                )
            )
            capability = target.manifest.participant_runtime
            if capability is not None and capability.supports_autonomous_execution:
                cases.extend(_drive_participant_execution_probe(target, control_plane))
    cases.append(_hermetic_snapshot_case(control_plane))
    return tuple(cases)
