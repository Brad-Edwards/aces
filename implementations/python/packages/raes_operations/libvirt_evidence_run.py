"""Libvirt evidence-run evaluator-evidence artifact producer.

Composes existing RAES surfaces — the libvirt participant runtime (issue #614, via
the runtime control plane), the native libvirt substrate realization (issue #601),
the backend manifest, and the experiment/evaluation contracts — into one stable,
validated run artifact (``raes.libvirt.scenario-evidence-run/v1``) that carries
evaluator-facing evidence for the enterprise participant/evidence scenario.
The artifact is a local proof-artifact wrapper that embeds validated
published-contract payloads and bounded summaries; it is NOT a new published
contract.

ADR-036 module boundary: ``raes_operations`` orchestrates the libvirt backend only
through ``raes_backend_libvirt.target`` / ``raes_backend_libvirt.techvault_native``,
the ``raes_runtime`` control plane / manager, ``raes.parser``, and
``raes_contracts``. It never imports the processor or backend internals; the
compiled runtime model is read from ``ExecutionPlan.model`` (a runtime-layer
output). Deep processor-iterator validation of the participant proof is performed
by the issue #614 test suite, not by this shipped producer.

Two honestly-disclosed evidence-source modes:

* ``deterministic`` (default, no libvirt daemon — used by tests / CI): participant
  lifecycle proof + compiled topology + structural negative-boundary evidence + an
  evaluator-only declaration of defensive evidence channels; no SOC state is
  observed.
* ``native-live`` (operator-run; injected/default native driver):
  additionally realizes only the bounded VM/network substrate that passes the
  TechVault concern-admission gate and records independently daemon-observed fields.
  Guest content, accounts, features, ACLs, services, and SOC state are rejected or
  disclosed as not observed; orchestration/evaluation remain separate planes.

Artifact assembly lives in ``_evidence_run_artifact`` and validation in
``_evidence_run_validation`` (kept separate for the ADR-015 source-size cap).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from raes.parser import parse_sdl_file
from raes_backend_libvirt.target import create_libvirt_target
from raes_backend_libvirt.techvault_native import TechVaultNativeLibvirtDriver
from raes_runtime.control_plane import RuntimeControlPlane
from raes_runtime.manager import RuntimeManager

from raes_operations._evidence_run_artifact import EVIDENCE_RUN_SCHEMA, assemble_artifact
from raes_operations._evidence_run_native import _default_native_driver_factory, _run_native_mode
from raes_operations._evidence_run_types import (
    CompiledModel,
    EvidenceArtifactInputs,
    EvidenceCheck,
    LibvirtEvidenceRunConfig,
    ParticipantBehavior,
)
from raes_operations._evidence_run_validation import validate_libvirt_evidence_run_artifact
from raes_operations.deterministic_participant_fixtures import (
    build_participant_admission_request,
    iter_admission_pairs,
)
from raes_operations.run_artifacts import atomic_write_json_artifact, is_valid_run_id_label, run_artifact_path

__all__ = [
    "EVIDENCE_RUN_SCHEMA",
    "EvidenceCheck",
    "LibvirtEvidenceRunConfig",
    "LibvirtEvidenceRunReport",
    "run_libvirt_evidence_run",
    "validate_libvirt_evidence_run_artifact",
]

_PROOF_EPISODE_ID = "proof-ep-1"

_NATIVE_MODES = frozenset({"native-live", "guest-certified"})


@dataclass(frozen=True)
class LibvirtEvidenceRunReport:
    """Rendered outcome for the libvirt scenario-evidence producer."""

    scenario: str
    run_id: str
    output_dir: str
    evidence_source_mode: str
    checks: tuple[EvidenceCheck, ...]
    artifact: dict[str, Any] | None = None
    artifact_path: str | None = None

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def render(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [
            f"libvirt scenario evidence -- scenario={self.scenario} run_id={self.run_id} "
            f"mode={self.evidence_source_mode}: {status}"
        ]
        for check in self.checks:
            marker = "ok" if check.passed else "FAIL"
            lines.append(f"  [{marker}] {check.name}")
            for diagnostic in check.diagnostics:
                lines.append(f"        - {diagnostic}")
        if self.artifact_path:
            lines.append(f"  artifact: {self.artifact_path}")
        return "\n".join(lines)


def run_libvirt_evidence_run(
    *,
    scenario_path: Path,
    project_dir: Path,
    run_id: str,
    config: LibvirtEvidenceRunConfig | None = None,
    driver_factory: Callable[[], TechVaultNativeLibvirtDriver] | None = None,
) -> LibvirtEvidenceRunReport:
    """Produce the libvirt scenario evaluator-evidence artifact for ``scenario_path``."""
    settings = config or LibvirtEvidenceRunConfig()
    mode = settings.evidence_source_mode
    checks: list[EvidenceCheck] = []

    run_id_ok = is_valid_run_id_label(run_id)
    checks.append(
        EvidenceCheck("run_id_input", run_id_ok, () if run_id_ok else ("run id must be a safe filesystem label",))
    )
    if not run_id_ok:
        return LibvirtEvidenceRunReport(scenario_path.name, run_id, str(project_dir), mode, tuple(checks))

    native_driver: TechVaultNativeLibvirtDriver | None = None
    if mode in _NATIVE_MODES:
        native_driver = (driver_factory or _default_native_driver_factory(project_dir, run_id, settings, mode))()

    try:
        target = create_libvirt_target(participant_runtime=True, driver=native_driver)
        execution_plan = RuntimeManager(target).plan(parse_sdl_file(scenario_path))
        control_plane = RuntimeControlPlane(target)
    except Exception:
        checks.append(EvidenceCheck("scenario_plan", False, ("failed to plan scenario",)))
        return LibvirtEvidenceRunReport(scenario_path.name, run_id, str(project_dir), mode, tuple(checks))

    model = execution_plan.model
    proof = _run_participant_lifecycle(model, control_plane)
    checks.append(EvidenceCheck("participant_action_proof", proof["lifecycle_clean"], tuple(proof["diagnostics"])))

    native_snapshot: Mapping[str, Any] | None = None
    native_cleanup_verified: bool | None = None
    unrealized_capabilities: tuple[str, ...] = ()
    guest_observed: Mapping[str, Any] | None = None
    if mode in _NATIVE_MODES and native_driver is not None:
        native_snapshot, native_cleanup_verified, unrealized_capabilities, guest_observed = _run_native_mode(
            mode, execution_plan, control_plane, native_driver, driver_factory, checks
        )

    inputs = EvidenceArtifactInputs(
        scenario_path=scenario_path,
        run_id=run_id,
        recorded_at=datetime.now(UTC).isoformat(),
        mode=mode,
        model=model,
        manifest=execution_plan.manifest,
        proof=proof,
        native_snapshot=native_snapshot,
        native_cleanup_verified=native_cleanup_verified,
        unrealized_capabilities=unrealized_capabilities,
        guest_observed=guest_observed,
    )
    artifact, artifact_path = _finalize_artifact(inputs, project_dir, checks)
    return LibvirtEvidenceRunReport(
        scenario_path.name, run_id, str(project_dir), mode, tuple(checks), artifact, artifact_path
    )


def _finalize_artifact(
    inputs: EvidenceArtifactInputs, project_dir: Path, checks: list[EvidenceCheck]
) -> tuple[dict[str, Any], str | None]:
    """Assemble, validate, and (fail-closed) persist the artifact, appending the gating checks."""
    artifact = assemble_artifact(inputs)
    violations = validate_libvirt_evidence_run_artifact(artifact)
    checks.append(EvidenceCheck("artifact_contract_validation", not violations, tuple(violations)))
    artifact_path, write_check = _persist_artifact(project_dir, inputs.run_id, artifact, violations)
    checks.append(write_check)
    return artifact, artifact_path


def _persist_artifact(
    project_dir: Path, run_id: str, artifact: Mapping[str, Any], violations: list[str]
) -> tuple[str | None, EvidenceCheck]:
    """Persist the artifact only when it is contract-valid.

    Fail closed: a redaction/contract-invalid artifact is never written, so forbidden
    content the validator detected can never reach the artifact path.
    """
    if violations:
        return None, EvidenceCheck("artifact_write", False, ("artifact not written: contract validation failed",))
    try:
        target_path = run_artifact_path(project_dir, run_id, "scenario-evidence", "libvirt-scenario-evidence-run.json")
        atomic_write_json_artifact(target_path, artifact)
    except OSError:
        return None, EvidenceCheck("artifact_write", False, ("artifact write failed",))
    return str(target_path), EvidenceCheck("artifact_write", True)


def _run_participant_lifecycle(model: CompiledModel, control_plane: RuntimeControlPlane) -> dict[str, Any]:
    """Drive the libvirt participant episode lifecycle via the runtime control plane.

    Records the lifecycle outcome (all receipts accepted), the admitted actions,
    and the terminal snapshot. Deep behavior-history/episode invariant validation
    is the processor-layer test suite's job (issue #614), not this producer's.
    """
    diagnostics: list[str] = []
    admitted: list[str] = []
    for behavior_address, behavior in model.participant_behaviors.items():
        episode_admitted, episode_diagnostics = _run_behavior_episode(model, control_plane, behavior_address, behavior)
        admitted.extend(episode_admitted)
        diagnostics.extend(episode_diagnostics)

    snapshot = control_plane.get_snapshot().snapshot
    return {
        "lifecycle_clean": not diagnostics,
        "diagnostics": diagnostics,
        "admitted_action_addresses": admitted,
        "snapshot": snapshot,
    }


def _run_behavior_episode(
    model: CompiledModel,
    control_plane: RuntimeControlPlane,
    behavior_address: str,
    behavior: ParticipantBehavior,
) -> tuple[list[str], list[str]]:
    """Run one participant behavior's episode (init -> admit actions -> terminate).

    Returns ``(admitted_action_addresses, diagnostics)``; a non-empty diagnostics
    list means some receipt was rejected.
    """
    init_receipt = control_plane.initialize_participant_episode(behavior_address, episode_id=_PROOF_EPISODE_ID)
    if not init_receipt.accepted:
        return [], [f"initialize rejected for {behavior_address}"]
    boundary_address = behavior.observation_boundary_addresses[0] if behavior.observation_boundary_addresses else None
    if boundary_address is None:
        control_plane.terminate_participant_episode(behavior_address)
        return [], [f"no observation boundary for {behavior_address}"]

    admitted: list[str] = []
    diagnostics: list[str] = []
    for action_address, action_instance_id in iter_admission_pairs(behavior, model.observation_boundaries):
        admitted_address, diagnostic = _admit_one_action(
            model, control_plane, behavior, behavior_address, boundary_address, action_address, action_instance_id
        )
        if admitted_address is not None:
            admitted.append(admitted_address)
        if diagnostic is not None:
            diagnostics.append(diagnostic)

    term_receipt = control_plane.terminate_participant_episode(behavior_address)
    if not term_receipt.accepted:
        diagnostics.append(f"terminate rejected for {behavior_address}")
    return admitted, diagnostics


def _admit_one_action(
    model: CompiledModel,
    control_plane: RuntimeControlPlane,
    behavior: ParticipantBehavior,
    behavior_address: str,
    boundary_address: str,
    action_address: str,
    action_instance_id: str,
) -> tuple[str | None, str | None]:
    """Admit one participant action; return ``(admitted_address_or_None, diagnostic_or_None)``."""
    contract = model.action_contracts.get(action_address)
    if contract is None:
        return None, None
    try:
        request = build_participant_admission_request(
            behavior_address=behavior_address,
            action_address=action_address,
            action_instance_id=action_instance_id,
            boundary_address=boundary_address,
            contract=contract,
        )
    except (TypeError, ValueError) as exc:
        return None, f"invalid admission for {behavior_address}/{action_address}: {exc}"
    accepted = control_plane.admit_participant_action(behavior, request).accepted
    return (
        action_address if accepted else None,
        None if accepted else f"admit rejected for {behavior_address}/{action_address}",
    )
