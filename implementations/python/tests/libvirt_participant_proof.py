"""Address-driven structural proof driver for the libvirt participant runtime.

``run_libvirt_participant_proof`` loads an SDL file, compiles the runtime model,
runs the RUN-311 episode lifecycle and one action admission per declared behavior
via ``LibvirtParticipantRuntime`` with the deterministic domain adapter, then
validates the resulting snapshot against the episode-snapshot and behavior-history
invariants.

This driver requires no live libvirt daemon; it is suitable for CI pipelines and
conformance proofs. It lives in the tests layer because it composes the processor
validation iterators with the libvirt backend runtime, a cross-layer composition
the ADR-036 module boundaries reserve for tests. The deterministic
manifest/selection/action-result/admission fixtures are shared with the shipped
scenario-evidence producer via ``aces_operations.deterministic_participant_fixtures``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aces_backend_libvirt.manifest import create_libvirt_manifest
from aces_backend_libvirt.participant_runtime import LibvirtParticipantRuntime
from aces_backend_libvirt.provisioner import LibvirtProvisioner
from aces_operations.deterministic_participant_fixtures import (
    build_participant_admission_request,
    iter_admission_pairs,
)
from aces_processor.compiler import compile_runtime_model
from aces_processor.models import (
    iter_participant_behavior_history_violations,
    iter_participant_episode_snapshot_violations,
)
from aces_runtime.control_plane import RuntimeControlPlane
from aces_runtime.registry import RuntimeTarget
from libvirt_participant_fixtures import NullLibvirtDriver
from raes.parser import parse_sdl


@dataclass(frozen=True)
class LibvirtParticipantProofResult:
    """Result of a structural libvirt participant proof run."""

    errors: tuple[str, ...] = ()
    episode_snapshot_violations: tuple[tuple[str, str], ...] = ()
    behavior_history_violations: tuple[tuple[str, str], ...] = ()


def run_libvirt_participant_proof(sdl_path: Path) -> LibvirtParticipantProofResult:
    """Run a structural proof of the libvirt participant runtime against ``sdl_path``.

    Loads the SDL file, compiles the runtime model, creates a
    ``LibvirtParticipantRuntime`` target (no live libvirt daemon), then for each
    declared behavior initializes a participant episode, admits one action per
    declared action contract, and terminates the episode. Validates the resulting
    snapshot via ``iter_participant_episode_snapshot_violations`` and
    ``iter_participant_behavior_history_violations``.

    Returns a ``LibvirtParticipantProofResult`` with empty tuple fields on success.
    Any structural violation or exception is surfaced in the result rather than
    raised, so callers can report the full set of proof failures.
    """
    try:
        sdl = parse_sdl(sdl_path.read_text())
        runtime_model = compile_runtime_model(sdl)
    except Exception as exc:  # noqa: BLE001
        return LibvirtParticipantProofResult(errors=(f"failed to load/compile SDL: {exc}",))

    manifest = create_libvirt_manifest(participant_runtime=True)
    target = RuntimeTarget(
        name=manifest.name,
        manifest=manifest,
        provisioner=LibvirtProvisioner(NullLibvirtDriver()),
        participant_runtime=LibvirtParticipantRuntime(),
    )
    control_plane = RuntimeControlPlane(target)

    errors: list[str] = []

    for behavior_address, behavior in runtime_model.participant_behaviors.items():
        init_receipt = control_plane.initialize_participant_episode(behavior_address, episode_id="proof-ep-1")
        if not init_receipt.accepted:
            errors.append(f"initialize_participant_episode rejected for {behavior_address!r}")
            continue

        boundary_address = (
            behavior.observation_boundary_addresses[0] if behavior.observation_boundary_addresses else None
        )
        if boundary_address is None:
            errors.append(f"no observation boundary declared for behavior {behavior_address!r}")
            control_plane.terminate_participant_episode(behavior_address)
            continue

        for action_address, action_instance_id in iter_admission_pairs(behavior, runtime_model.observation_boundaries):
            contract = runtime_model.action_contracts.get(action_address)
            if contract is None:
                continue
            try:
                admission_request = build_participant_admission_request(
                    behavior_address=behavior_address,
                    action_address=action_address,
                    action_instance_id=action_instance_id,
                    boundary_address=boundary_address,
                    contract=contract,
                )
            except (TypeError, ValueError) as exc:
                errors.append(f"invalid admission request for {behavior_address!r}/{action_address!r}: {exc}")
                continue

            admit_receipt = control_plane.admit_participant_action(behavior, admission_request)
            if not admit_receipt.accepted:
                errors.append(f"admit_participant_action rejected for {behavior_address!r}/{action_address!r}")

        term_receipt = control_plane.terminate_participant_episode(behavior_address)
        if not term_receipt.accepted:
            errors.append(f"terminate_participant_episode rejected for {behavior_address!r}")

    snapshot = control_plane.get_snapshot().snapshot
    episode_violations = tuple(
        iter_participant_episode_snapshot_violations(
            snapshot.participant_episode_results,
            snapshot.participant_episode_history,
        )
    )
    behavior_violations: list[tuple[str, str]] = []
    for behavior_address in runtime_model.participant_behaviors:
        bh = snapshot.participant_behavior_history.get(behavior_address, [])
        behavior_violations.extend(
            iter_participant_behavior_history_violations(
                bh,
                action_contracts=runtime_model.action_contracts,
                observation_boundaries=runtime_model.observation_boundaries,
                participant_episode_history=snapshot.participant_episode_history.get(behavior_address, []),
                expected_participant_address=behavior_address,
            )
        )

    return LibvirtParticipantProofResult(
        errors=tuple(errors),
        episode_snapshot_violations=episode_violations,
        behavior_history_violations=tuple(behavior_violations),
    )
