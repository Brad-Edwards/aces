"""Libvirt paper-proof evaluator-evidence artifact producer.

Composes existing ACES surfaces — the libvirt participant runtime (issue #614, via
the runtime control plane), the native libvirt substrate realization (issue #601),
the backend manifest, and the experiment/evaluation contracts — into one stable,
validated run artifact (``aces.libvirt.paper-evidence-run/v1``) that carries
evaluator-facing evidence for the paper enterprise participant/evidence scenario.
The artifact is a local proof-artifact wrapper that embeds validated
published-contract payloads and bounded summaries; it is NOT a new published
contract.

ADR-036 module boundary: ``aces_operations`` orchestrates the libvirt backend only
through ``aces_backend_libvirt.target`` / ``aces_backend_libvirt.techvault_native``,
the ``aces_runtime`` control plane / manager, ``aces_sdl.parser``, and
``aces_contracts``. It never imports the processor or backend internals; the
compiled runtime model is read from ``ExecutionPlan.model`` (a runtime-layer
output). Deep processor-iterator validation of the participant proof is performed
by the issue #614 test suite, not by this shipped producer.

Two honestly-disclosed evidence-source modes:

* ``deterministic`` (default, no libvirt daemon — used by tests / CI): participant
  lifecycle proof + compiled topology + structural negative-boundary evidence + an
  evaluator-only translated SOC-readback record explicitly marked as not upstream
  Wazuh.
* ``native-live`` (operator-run; injected/default native driver + probe):
  additionally realizes the libvirt VM/network substrate and records the native
  topology and native SOC readback. The libvirt backend declares no content-type
  support, so the scenario's content/orchestration/evaluation planes are not
  backend-realized; those are disclosed as ``unrealized_capabilities``, not faked.

Artifact assembly lives in ``_paper_evidence_artifact`` and validation in
``_paper_evidence_validation`` (kept separate for the ADR-015 source-size cap).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from aces_backend_libvirt.target import create_libvirt_target
from aces_backend_libvirt.techvault_native import NativeLibvirtProbe, TechVaultNativeLibvirtDriver
from aces_runtime.control_plane import RuntimeControlPlane
from aces_runtime.manager import RuntimeManager
from aces_sdl.parser import parse_sdl_file

from aces_operations._paper_evidence_artifact import EVIDENCE_RUN_SCHEMA, assemble_artifact
from aces_operations._paper_evidence_types import (
    CompiledModel,
    EvidenceArtifactInputs,
    ExecutionPlan,
    ParticipantBehavior,
)
from aces_operations._paper_evidence_validation import validate_libvirt_paper_evidence_artifact
from aces_operations.deterministic_participant_fixtures import (
    build_participant_admission_request,
    iter_admission_pairs,
)
from aces_operations.run_artifacts import atomic_write_json_artifact, is_valid_run_id_label, run_artifact_path

__all__ = [
    "EVIDENCE_RUN_SCHEMA",
    "EvidenceCheck",
    "LibvirtPaperEvidenceConfig",
    "LibvirtPaperEvidenceReport",
    "run_libvirt_paper_evidence",
    "validate_libvirt_paper_evidence_artifact",
]

_PROOF_EPISODE_ID = "proof-ep-1"

EvidenceSourceMode = Literal["deterministic", "native-live"]


@dataclass(frozen=True)
class EvidenceCheck:
    """One named check over the paper-evidence production run.

    Every check is gating: it contributes to ``LibvirtPaperEvidenceReport.passed``.
    There is deliberately no non-gating escape hatch — in particular, a native-live
    run that fails to realize the libvirt substrate must report ``passed=False`` so
    the mode can never claim success without actually realizing.
    """

    name: str
    passed: bool
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class LibvirtPaperEvidenceConfig:
    """Runtime controls for the libvirt paper-evidence producer."""

    evidence_source_mode: EvidenceSourceMode = "deterministic"
    connection_uri: str = "qemu:///system"
    boot_timeout_seconds: int = 180
    appliance_memory_mib: int = 128
    clean_boot: bool = True


@dataclass(frozen=True)
class LibvirtPaperEvidenceReport:
    """Rendered outcome for the libvirt paper-evidence producer."""

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
            f"libvirt paper evidence -- scenario={self.scenario} run_id={self.run_id} "
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


def run_libvirt_paper_evidence(
    *,
    scenario_path: Path,
    project_dir: Path,
    run_id: str,
    config: LibvirtPaperEvidenceConfig | None = None,
    driver_factory: Callable[[], TechVaultNativeLibvirtDriver] | None = None,
    probe: NativeLibvirtProbe | None = None,
) -> LibvirtPaperEvidenceReport:
    """Produce the libvirt paper evaluator-evidence artifact for ``scenario_path``."""
    settings = config or LibvirtPaperEvidenceConfig()
    mode = settings.evidence_source_mode
    checks: list[EvidenceCheck] = []

    run_id_ok = is_valid_run_id_label(run_id)
    checks.append(
        EvidenceCheck("run_id_input", run_id_ok, () if run_id_ok else ("run id must be a safe filesystem label",))
    )
    if not run_id_ok:
        return LibvirtPaperEvidenceReport(scenario_path.name, run_id, str(project_dir), mode, tuple(checks))

    native_driver: TechVaultNativeLibvirtDriver | None = None
    if mode == "native-live":
        native_driver = (driver_factory or _default_native_driver_factory(project_dir, run_id, settings))()

    try:
        target = create_libvirt_target(participant_runtime=True, driver=native_driver)
        execution_plan = RuntimeManager(target).plan(parse_sdl_file(scenario_path))
        control_plane = RuntimeControlPlane(target)
    except Exception as exc:
        checks.append(EvidenceCheck("scenario_plan", False, (f"failed to plan scenario: {exc}",)))
        return LibvirtPaperEvidenceReport(scenario_path.name, run_id, str(project_dir), mode, tuple(checks))

    model = execution_plan.model
    proof = _run_participant_lifecycle(model, control_plane)
    checks.append(EvidenceCheck("participant_action_proof", proof["lifecycle_clean"], tuple(proof["diagnostics"])))

    native_snapshot: Mapping[str, Any] | None = None
    unrealized_capabilities: tuple[str, ...] = ()
    if mode == "native-live":
        native_snapshot, realize_check, unrealized_capabilities = _realize_native_substrate(
            execution_plan, control_plane, native_driver
        )
        checks.append(realize_check)

    inputs = EvidenceArtifactInputs(
        scenario_path=scenario_path,
        run_id=run_id,
        recorded_at=datetime.now(UTC).isoformat(),
        mode=mode,
        model=model,
        manifest=execution_plan.manifest,
        proof=proof,
        native_snapshot=native_snapshot,
        probe=probe if mode == "native-live" else None,
        unrealized_capabilities=unrealized_capabilities,
    )
    artifact, artifact_path = _finalize_artifact(inputs, project_dir, checks)
    return LibvirtPaperEvidenceReport(
        scenario_path.name, run_id, str(project_dir), mode, tuple(checks), artifact, artifact_path
    )


def _finalize_artifact(
    inputs: EvidenceArtifactInputs, project_dir: Path, checks: list[EvidenceCheck]
) -> tuple[dict[str, Any], str | None]:
    """Assemble, validate, and (fail-closed) persist the artifact, appending the gating checks."""
    artifact = assemble_artifact(inputs)
    violations = validate_libvirt_paper_evidence_artifact(artifact)
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
        target_path = run_artifact_path(project_dir, run_id, "paper-evidence", "libvirt-paper-evidence-run.json")
        atomic_write_json_artifact(target_path, artifact)
    except OSError as exc:
        return None, EvidenceCheck("artifact_write", False, (f"artifact write failed: {exc}",))
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
    admit_receipt = control_plane.admit_participant_action(behavior, request)
    if admit_receipt.accepted:
        return action_address, None
    return None, f"admit rejected for {behavior_address}/{action_address}"


def _default_native_driver_factory(
    project_dir: Path, run_id: str, settings: LibvirtPaperEvidenceConfig
) -> Callable[[], TechVaultNativeLibvirtDriver]:
    """Build the default native libvirt driver factory for operator-run native-live mode.

    Mirrors the TechVault live gate: the driver connects to a real libvirt daemon at
    realize time. In CI/tests a fake driver_factory is injected instead, so this is
    never exercised without a daemon.
    """
    state_dir = project_dir / "runs" / run_id / "paper-evidence" / "libvirt"

    def factory() -> TechVaultNativeLibvirtDriver:
        return TechVaultNativeLibvirtDriver(
            state_dir=state_dir,
            connection_uri=settings.connection_uri,
            name_prefix="aces-paper",
            appliance_memory_mib=settings.appliance_memory_mib,
            clean_existing=settings.clean_boot,
        )

    return factory


def _realize_native_substrate(
    execution_plan: ExecutionPlan,
    control_plane: RuntimeControlPlane,
    native_driver: TechVaultNativeLibvirtDriver | None,
) -> tuple[Mapping[str, Any] | None, EvidenceCheck, tuple[str, ...]]:
    """Realize the libvirt provisioning substrate (VMs + networks) for the scenario.

    The libvirt backend realizes the provisioning substrate only; the paper scenario
    additionally declares content/orchestration/evaluation that this backend does
    not realize. Those are returned as ``unrealized_capabilities`` (disclosed in the
    artifact). The check is gating and passes only when the native driver realized at
    least one domain — native-live must never report success without realizing. A
    scenario the libvirt backend cannot provision (e.g. the paper scenario's content
    plane) therefore fails native-live and surfaces its unrealized capabilities,
    rather than silently passing.
    """
    if native_driver is None:
        return None, EvidenceCheck("native_substrate_realization", False, ("no native driver",)), ()
    try:
        receipt = control_plane.submit_provisioning(execution_plan.provisioning)
        status = control_plane.get_operation(receipt.operation_id)
    except Exception as exc:
        return None, EvidenceCheck("native_substrate_realization", False, (f"native realization raised: {exc}",)), ()
    unrealized = _dedupe(
        f"{d.code}: {d.message}"
        for source in (execution_plan.diagnostics, () if status is None else status.diagnostics)
        for d in source
        if d.is_error
    )
    snapshot = native_driver.last_snapshot
    realized = _snapshot_has_domains(snapshot)
    check = EvidenceCheck(
        "native_substrate_realization",
        realized,
        ()
        if realized
        else ("libvirt backend realized no native substrate for this scenario; capabilities disclosed as unrealized",),
    )
    return (snapshot if realized else None), check, unrealized


def _dedupe(items: Iterable[str]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return tuple(seen)


def _snapshot_has_domains(snapshot: Mapping[str, Any] | None) -> bool:
    if not isinstance(snapshot, Mapping):
        return False
    domains = snapshot.get("domains", ())
    return isinstance(domains, list | tuple) and len(domains) > 0
