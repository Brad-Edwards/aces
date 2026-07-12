"""Libvirt evidence-run evaluator-evidence artifact producer.

Composes existing ACES surfaces — the libvirt participant runtime (issue #614, via
the runtime control plane), the native libvirt substrate realization (issue #601),
the backend manifest, and the experiment/evaluation contracts — into one stable,
validated run artifact (``aces.libvirt.scenario-evidence-run/v1``) that carries
evaluator-facing evidence for the enterprise participant/evidence scenario.
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

import hashlib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from aces_backend_libvirt.target import create_libvirt_target
from aces_backend_libvirt.techvault_native import TechVaultNativeLibvirtDriver
from aces_runtime.control_plane import RuntimeControlPlane
from aces_runtime.manager import RuntimeManager
from aces_sdl.parser import parse_sdl_file

from aces_operations._evidence_run_artifact import EVIDENCE_RUN_SCHEMA, assemble_artifact
from aces_operations._evidence_run_types import (
    CompiledModel,
    EvidenceArtifactInputs,
    ExecutionPlan,
    ParticipantBehavior,
)
from aces_operations._evidence_run_validation import validate_libvirt_evidence_run_artifact
from aces_operations._techvault_cleanup import cleanup_native_snapshot
from aces_operations.deterministic_participant_fixtures import (
    build_participant_admission_request,
    iter_admission_pairs,
)
from aces_operations.run_artifacts import atomic_write_json_artifact, is_valid_run_id_label, run_artifact_path

__all__ = [
    "EVIDENCE_RUN_SCHEMA",
    "EvidenceCheck",
    "LibvirtEvidenceRunConfig",
    "LibvirtEvidenceRunReport",
    "run_libvirt_evidence_run",
    "validate_libvirt_evidence_run_artifact",
]

_PROOF_EPISODE_ID = "proof-ep-1"

EvidenceSourceMode = Literal["deterministic", "native-live", "guest-certified"]
_NATIVE_MODES = frozenset({"native-live", "guest-certified"})


@dataclass(frozen=True)
class EvidenceCheck:
    """One named check over the scenario-evidence production run.

    Every check is gating: it contributes to ``LibvirtEvidenceRunReport.passed``.
    There is deliberately no non-gating escape hatch — in particular, a native-live
    run that fails to realize the libvirt substrate must report ``passed=False`` so
    the mode can never claim success without actually realizing.
    """

    name: str
    passed: bool
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class LibvirtEvidenceRunConfig:
    """Runtime controls for the libvirt scenario-evidence producer."""

    evidence_source_mode: EvidenceSourceMode = "deterministic"
    connection_uri: str = "qemu:///system"


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
        try:
            native_snapshot, realize_check, unrealized_capabilities, operation_id = _realize_native_substrate(
                execution_plan, control_plane, native_driver
            )
            checks.append(realize_check)
            if native_snapshot is not None and mode == "guest-certified":
                # Native-proof boundary: only the default production driver/transport
                # (no injected factory) yields a certifying artifact. Injected fakes
                # may exercise orchestration but are marked non-certifying so their
                # evidence can never be published as a real guest certification.
                guest_observed = _guest_observed_report(native_driver, operation_id, certifying=driver_factory is None)
        finally:
            # Cleanup runs after every attempt. A realized substrate is torn down and
            # its verification recorded; a failed/unrealized attempt (the driver has
            # already rolled back) is only reported when residue actually remains, so
            # an honestly-unrealized run keeps cleanup not-applicable.
            if native_snapshot is not None:
                native_cleanup_verified, cleanup_diagnostics = _verify_native_cleanup(native_driver, native_snapshot)
                checks.append(EvidenceCheck("native_substrate_cleanup", native_cleanup_verified, cleanup_diagnostics))
            else:
                residue_ok, residue_diagnostics = _sweep_residue(native_driver)
                if not residue_ok:
                    checks.append(EvidenceCheck("native_substrate_residue", False, residue_diagnostics))

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


def _default_native_driver_factory(
    project_dir: Path, run_id: str, settings: LibvirtEvidenceRunConfig, mode: str
) -> Callable[[], TechVaultNativeLibvirtDriver]:
    """Build the default native libvirt driver factory for an operator-run native mode.

    The driver connects to a real libvirt daemon at realize time; ``guest-certified``
    selects the guest-observing driver. In CI/tests a fake driver_factory is injected
    instead, so this is never exercised without a daemon.
    """
    state_dir = project_dir / "runs" / run_id / "scenario-evidence" / "libvirt"

    def factory() -> TechVaultNativeLibvirtDriver:
        if mode == "guest-certified":
            from aces_backend_libvirt.guest_certified_driver import GuestCertifiedLibvirtDriver

            return GuestCertifiedLibvirtDriver(
                state_dir=state_dir,
                connection_uri=settings.connection_uri,
                name_prefix="aces-evidence",
            )
        return TechVaultNativeLibvirtDriver(
            state_dir=state_dir,
            connection_uri=settings.connection_uri,
            name_prefix="aces-evidence",
        )

    return factory


def _guest_observed_report(
    native_driver: TechVaultNativeLibvirtDriver, operation_id: str | None, *, certifying: bool
) -> Mapping[str, Any] | None:
    """Assemble the operation-joined, challenge-bound guest report from the driver.

    The control-plane operation id and observation timestamp are joined here, at the
    operations boundary, rather than inside the backend driver. ``certifying`` records
    whether the governed production driver was used; an injected fake driver yields a
    non-certifying report that is externally distinguishable from a real proof.
    """
    observations = getattr(native_driver, "last_guest_observations", ())
    if not observations:
        return None
    facts = getattr(native_driver, "last_guest_facts", {})
    binding = getattr(native_driver, "last_guest_binding", {})
    correlations = binding.get("correlations", {}) if isinstance(binding, Mapping) else {}
    domains = [
        {
            "address": address,
            "correlation": correlations.get(address),
            "architecture": fact.get("architecture"),
            "vcpus": fact.get("vcpus"),
            "memory_mib": fact.get("memory_mib"),
            "network": list(fact.get("interfaces", ())),
            "content": list(fact.get("content", ())),
            "accounts": list(fact.get("accounts", ())),
            "services": list(fact.get("services", ())),
        }
        for address, fact in sorted(facts.items())
        if isinstance(fact, Mapping)
    ]
    return {
        # The raw control-plane operation id is a UUID and never portable identity;
        # bind a redacted digest instead so the guest report joins the operation
        # without leaking the UUID (the redaction gate forbids raw UUIDs).
        "operation_ref": _operation_ref(operation_id),
        "observed_at": datetime.now(UTC).isoformat(),
        "certifying": certifying,
        "probe_policy": binding.get("probe_policy") if isinstance(binding, Mapping) else None,
        "challenge": binding.get("challenge") if isinstance(binding, Mapping) else None,
        "domains": domains,
    }


def _operation_ref(operation_id: str | None) -> str | None:
    if not operation_id:
        return None
    return "sha256:" + hashlib.sha256(operation_id.encode("utf-8")).hexdigest()


def _verify_native_cleanup(
    native_driver: TechVaultNativeLibvirtDriver, native_snapshot: Mapping[str, Any]
) -> tuple[bool, tuple[str, ...]]:
    """Tear down a realized substrate and verify native + guest-probe cleanup."""

    verified, diagnostics = cleanup_native_snapshot(native_driver, native_snapshot)
    if verified and getattr(native_driver, "last_guest_binding", {}):
        return False, (*diagnostics, "guest probe artifacts were not fully cleaned")
    return verified, diagnostics


def _sweep_residue(native_driver: TechVaultNativeLibvirtDriver) -> tuple[bool, tuple[str, ...]]:
    """Best-effort finally-path sweep after a failed/unrealized attempt.

    The driver rolls back on failure, so the common case leaves no residue. Any
    remaining realized address, non-empty snapshot, or residual guest binding is a
    leak and is reported so the run cannot pass.
    """
    clean = (
        not native_driver.realized_addresses()
        and native_driver.last_snapshot == {}
        and not getattr(native_driver, "last_guest_binding", {})
    )
    if clean:
        return True, ()
    residual = tuple(sorted(native_driver.realized_addresses()))
    result = native_driver.destroy(networks=residual, domains=residual)
    ok = (
        not result.diagnostics
        and not native_driver.realized_addresses()
        and native_driver.last_snapshot == {}
        and not getattr(native_driver, "last_guest_binding", {})
    )
    if ok:
        return True, ()
    diagnostics = tuple(f"{item.code} at {item.address}" for item in result.diagnostics)
    return False, diagnostics or ("residual native or guest state remains after a failed attempt",)


def _realize_native_substrate(
    execution_plan: ExecutionPlan,
    control_plane: RuntimeControlPlane,
    native_driver: TechVaultNativeLibvirtDriver | None,
) -> tuple[Mapping[str, Any] | None, EvidenceCheck, tuple[str, ...], str | None]:
    """Realize the libvirt provisioning substrate (VMs + networks) for the scenario.

    Native modes pass only when the runtime operation succeeds and the fresh driver
    report contains independently daemon-observed domains bound to the selected
    realization-envelope/configuration identity. A domain handle or planned matrix
    alone is never sufficient. Returns the control-plane operation id so the evidence
    producer can join it at this boundary.
    """
    if native_driver is None:
        return None, EvidenceCheck("native_substrate_realization", False, ("no native driver",)), (), None
    try:
        receipt = control_plane.submit_provisioning(execution_plan.provisioning)
        operation_id = str(receipt.operation_id)
        status = control_plane.get_operation(receipt.operation_id)
    except Exception:
        return None, EvidenceCheck("native_substrate_realization", False, ("native realization failed",)), (), None
    unrealized = _dedupe(
        f"{d.code}: {d.message}"
        for source in (execution_plan.diagnostics, () if status is None else status.diagnostics)
        for d in source
        if d.is_error
    )
    snapshot = native_driver.last_snapshot
    operation_succeeded = status is not None and status.state.value == "succeeded"
    realized = operation_succeeded and _snapshot_has_daemon_observations(snapshot)
    check = EvidenceCheck(
        "native_substrate_realization",
        realized,
        ()
        if realized
        else ("libvirt backend realized no native substrate for this scenario; capabilities disclosed as unrealized",),
    )
    return (snapshot if realized else None), check, unrealized, operation_id


def _dedupe(items: Iterable[str]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return tuple(seen)


def _snapshot_has_daemon_observations(snapshot: Mapping[str, Any] | None) -> bool:
    if not isinstance(snapshot, Mapping):
        return False
    domains = snapshot.get("domains", ())
    binding = snapshot.get("binding")
    return (
        snapshot.get("source") == "daemon-observed"
        and isinstance(domains, list | tuple)
        and len(domains) > 0
        and isinstance(binding, Mapping)
    )
