"""Address-driven structural proof driver for the libvirt participant runtime.

``run_libvirt_participant_proof`` loads an SDL file, compiles the runtime model,
runs the RUN-311 episode lifecycle and one action admission per declared behavior
via ``LibvirtParticipantRuntime`` with the deterministic domain adapter, then
validates the resulting snapshot against the episode-snapshot and behavior-history
invariants.

This driver requires no live libvirt daemon; it is suitable for CI pipelines
and conformance proofs. The ``DeterministicParticipantDomainAdapter`` is used
throughout; live domain execution requires a custom adapter. The deterministic
participant manifest/selection/action-result fixtures are shared with the
acceptance tests in ``libvirt_participant_fixtures``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aces_backend_libvirt.manifest import create_libvirt_manifest
from aces_backend_libvirt.participant_runtime import LibvirtParticipantRuntime
from aces_backend_libvirt.provisioner import LibvirtProvisioner
from aces_contracts.contracts import ParticipantActionResultModel
from aces_contracts.participant_binding import ParticipantActionAdmissionRequest
from aces_processor.compiler import compile_runtime_model
from aces_processor.models import (
    ParticipantActionContractRuntime,
    _contract_uses_sem211_action_results,
    iter_participant_behavior_history_violations,
    iter_participant_episode_snapshot_violations,
)
from aces_runtime.control_plane import RuntimeControlPlane
from aces_runtime.registry import RuntimeTarget
from aces_sdl.parser import parse_sdl
from libvirt_participant_fixtures import (
    NullLibvirtDriver,
    build_action_result,
    build_implementation_manifest,
    build_implementation_selection,
)


@dataclass(frozen=True)
class LibvirtParticipantProofResult:
    """Result of a structural libvirt participant proof run."""

    errors: tuple[str, ...] = ()
    episode_snapshot_violations: tuple[tuple[str, str], ...] = ()
    behavior_history_violations: tuple[tuple[str, str], ...] = ()


def _build_action_result(
    *,
    participant_address: str,
    episode_id: str,
    action_instance_id: str,
    action_contract_address: str,
    contract: ParticipantActionContractRuntime,
) -> ParticipantActionResultModel | None:
    """Build a succeeded action_result, or None when the contract has no SEM-211 classes.

    Delegates the body to the shared ``build_action_result`` fixture; this wrapper
    only adds the SEM-211 applicability gate, which depends on the compiled
    contract object rather than the raw spec dict.
    """
    if not _contract_uses_sem211_action_results(contract):
        return None
    return build_action_result(
        participant_address=participant_address,
        episode_id=episode_id,
        action_instance_id=action_instance_id,
        action_contract_address=action_contract_address,
        contract_spec=contract.spec,
    )


def run_libvirt_participant_proof(sdl_path: Path) -> LibvirtParticipantProofResult:
    """Run a structural proof of the libvirt participant runtime against ``sdl_path``.

    Loads the SDL file, compiles the runtime model, creates a
    ``LibvirtParticipantRuntime`` target (no live libvirt daemon), then for
    each declared behavior:

    1. Initializes a participant episode.
    2. Admits one action per declared action contract.
    3. Terminates the episode.

    Validates the resulting snapshot via
    ``iter_participant_episode_snapshot_violations`` and
    ``iter_participant_behavior_history_violations``.

    Returns a ``LibvirtParticipantProofResult`` with empty tuple fields on
    success. Any structural violation or exception is surfaced in the result
    rather than raised, so callers can report the full set of proof failures.
    """
    try:
        sdl = parse_sdl(sdl_path.read_text())
        runtime_model = compile_runtime_model(sdl)
    except Exception as exc:  # noqa: BLE001
        return LibvirtParticipantProofResult(errors=(f"failed to load/compile SDL: {exc}",))

    manifest = create_libvirt_manifest(participant_runtime=True)
    participant_runtime = LibvirtParticipantRuntime()
    target = RuntimeTarget(
        name=manifest.name,
        manifest=manifest,
        provisioner=LibvirtProvisioner(NullLibvirtDriver()),
        participant_runtime=participant_runtime,
    )
    control_plane = RuntimeControlPlane(target)

    proof_manifest = build_implementation_manifest()

    errors: list[str] = []

    for behavior_address, behavior in runtime_model.participant_behaviors.items():
        # Initialize the episode
        init_receipt = control_plane.initialize_participant_episode(behavior_address, episode_id="proof-ep-1")
        if not init_receipt.accepted:
            errors.append(f"initialize_participant_episode rejected for {behavior_address!r}")
            continue

        # Collect action_instance_ids required by view transition anchors across all observation
        # boundaries for this behavior.  The behavior-history validator checks that every
        # view-transition anchor (action_instance_id + observation_emitted) resolves to a real
        # OBSERVATION_EMITTED event in the behavior history.  We must therefore use those exact
        # IDs when building our proof admissions rather than synthetic generated ones.
        required_action_instance_ids: list[str] = []
        for ba in behavior.observation_boundary_addresses:
            boundary = runtime_model.observation_boundaries.get(ba)
            if boundary is not None:
                for vt in boundary.view_transitions:
                    if isinstance(vt, dict):
                        aid: str | None = vt.get("action_instance_id")
                    else:
                        aid = getattr(vt, "action_instance_id", None)
                    if aid and aid not in required_action_instance_ids:
                        required_action_instance_ids.append(aid)

        # Build (action_address, action_instance_id) pairs to admit.
        # When view transitions impose specific IDs, pair each with the first action contract
        # (the boundary validator doesn't distinguish contracts by ID — it only checks the event
        # stream for matching OBSERVATION_EMITTED events).
        # Fall back to one-per-contract with generated IDs when no anchors exist.
        first_action_address = next(iter(behavior.action_contract_addresses), None)
        if required_action_instance_ids and first_action_address is not None:
            admission_pairs: list[tuple[str, str]] = [
                (first_action_address, aid) for aid in required_action_instance_ids
            ]
        else:
            admission_pairs = [
                (addr, f"proof-action-{i + 1:04d}") for i, addr in enumerate(behavior.action_contract_addresses)
            ]

        # Admit one action per (action_address, action_instance_id) pair
        for action_address, action_instance_id in admission_pairs:
            contract = runtime_model.action_contracts.get(action_address)
            if contract is None:
                continue

            episode_id = "proof-ep-1"
            snapshot = control_plane.get_snapshot().snapshot
            current = snapshot.participant_episode_results.get(behavior_address)
            if current is not None and isinstance(current, dict) and current.get("episode_id"):
                episode_id = str(current["episode_id"])

            action_result = _build_action_result(
                participant_address=behavior_address,
                episode_id=episode_id,
                action_instance_id=action_instance_id,
                action_contract_address=action_address,
                contract=contract,
            )
            selection = build_implementation_selection(behavior_address)

            boundary_address = (
                behavior.observation_boundary_addresses[0] if behavior.observation_boundary_addresses else None
            )
            if boundary_address is None:
                errors.append(f"no observation boundary declared for behavior {behavior_address!r}")
                continue

            try:
                admission_request = ParticipantActionAdmissionRequest(
                    participant_address=behavior_address,
                    action_contract_address=action_address,
                    observation_boundary_address=boundary_address,
                    action_instance_id=action_instance_id,
                    implementation_manifest=proof_manifest,
                    implementation_selection=selection,
                    visible_refs=(),
                    disclosed_refs=(),
                    evidence_refs=(),
                    observation_boundary_evidence_refs=(),
                    action_result=action_result,
                )
            except (TypeError, ValueError) as exc:
                errors.append(f"invalid admission request for {behavior_address!r}/{action_address!r}: {exc}")
                continue

            admit_receipt = control_plane.admit_participant_action(behavior, admission_request)
            if not admit_receipt.accepted:
                errors.append(f"admit_participant_action rejected for {behavior_address!r}/{action_address!r}")

        # Terminate the episode
        term_receipt = control_plane.terminate_participant_episode(behavior_address)
        if not term_receipt.accepted:
            errors.append(f"terminate_participant_episode rejected for {behavior_address!r}")

    # Validate the final snapshot
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
