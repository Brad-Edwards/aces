"""Native ACES/libvirt live validation for TechVault scenarios."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aces_backend_libvirt.target import create_libvirt_target
from aces_backend_libvirt.techvault_native import (
    NativeLibvirtProbe,
    TechVaultNativeLibvirtDriver,
    check_native_readiness,
    expected_surface,
    native_soc_readback,
)
from aces_runtime.control_plane import RuntimeControlPlane
from aces_runtime.manager import RuntimeManager
from aces_sdl.parser import parse_sdl_file

from aces_operations.run_artifacts import (
    atomic_write_json_artifact,
    is_valid_run_id_label,
    run_artifact_path,
)

DEFAULT_EVENT_WINDOW_SECONDS = 180
DEFAULT_BOOT_TIMEOUT_SECONDS = 180
_FULL_SOC_NODES = frozenset(
    {
        "wazuh-manager",
        "wazuh-indexer",
        "wazuh-dashboard",
        "suricata",
        "misp",
        "thehive",
        "cortex",
        "shuffle-backend",
        "shuffle-frontend",
    }
)


@dataclass(frozen=True)
class LiveCheck:
    """One ACES/libvirt TechVault live check."""

    name: str
    passed: bool
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class TechVaultLiveReport:
    """Rendered outcome for the native ACES/libvirt TechVault live gate."""

    scenario: str
    output_dir: str
    run_id: str
    checks: tuple[LiveCheck, ...]
    manifest_path: str | None = None

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def render(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [f"ACES/libvirt native TechVault live gate -- scenario={self.scenario} run_id={self.run_id}: {status}"]
        for check in self.checks:
            marker = "ok" if check.passed else "FAIL"
            lines.append(f"  [{marker}] {check.name}")
            for diagnostic in check.diagnostics:
                lines.append(f"        - {diagnostic}")
        if self.manifest_path:
            lines.append(f"  manifest: {self.manifest_path}")
        return "\n".join(lines)


@dataclass(frozen=True)
class TechVaultLiveConfig:
    """Runtime controls for the native ACES/libvirt TechVault live gate."""

    clean_boot: bool = True
    event_window_seconds: int = DEFAULT_EVENT_WINDOW_SECONDS
    boot_timeout_seconds: int = DEFAULT_BOOT_TIMEOUT_SECONDS
    connection_uri: str = "qemu:///system"
    appliance_memory_mib: int = 128


def validate_techvault_live(
    *,
    scenario_path: Path,
    project_dir: Path,
    run_id: str,
    config: TechVaultLiveConfig | None = None,
    driver_factory: Callable[[], TechVaultNativeLibvirtDriver] | None = None,
    probe: NativeLibvirtProbe | None = None,
) -> TechVaultLiveReport:
    """Boot and validate a TechVault SDL through native ACES/libvirt."""

    settings = config or TechVaultLiveConfig()
    output_dir = project_dir
    checks: list[LiveCheck] = []
    manifest_path: str | None = None
    run_id_check = _check_run_id(run_id)
    checks.append(run_id_check)
    if run_id_check.passed:
        run_dir = output_dir / "runs" / run_id / "live-gate"
        driver = (
            driver_factory()
            if driver_factory
            else TechVaultNativeLibvirtDriver(
                state_dir=run_dir / "libvirt",
                connection_uri=settings.connection_uri,
                name_prefix="aces-techvault",
                appliance_memory_mib=settings.appliance_memory_mib,
                clean_existing=settings.clean_boot,
            )
        )
        target = create_libvirt_target(driver=driver, name_prefix="aces-techvault")
        scenario, plan_check = _plan_scenario(target, scenario_path)
        del scenario
        checks.append(plan_check)
        if plan_check.passed:
            boot_check = _apply_plan(target, scenario_path, driver)
            checks.append(boot_check)
            snapshot = driver.last_snapshot
            evidence: dict[str, object] = {}
            if boot_check.passed:
                checks.append(_substrate_independence_check(snapshot))
                checks.append(_surface_check(snapshot))
                readiness_check = _readiness_check(
                    snapshot, probe or NativeLibvirtProbe(), settings.boot_timeout_seconds
                )
                checks.append(readiness_check)
                checks.append(_kali_reachability_check(snapshot, probe or NativeLibvirtProbe()))
                soc_check, soc_evidence = _soc_stack_readback_check(snapshot)
                checks.append(soc_check)
                evidence.update(soc_evidence)
                checks.append(_variation_check(snapshot))
            manifest_path = _write_manifest(
                output_dir,
                run_id,
                scenario_path,
                driver,
                checks,
                evidence,
                clean_boot=settings.clean_boot,
            )
            checks.append(
                LiveCheck(
                    "run_archive_manifest",
                    manifest_path is not None,
                    () if manifest_path else ("manifest write failed",),
                )
            )
    return TechVaultLiveReport(str(scenario_path), str(output_dir), run_id, tuple(checks), manifest_path)


def _check_run_id(run_id: str) -> LiveCheck:
    if is_valid_run_id_label(run_id):
        return LiveCheck("run_id_input", True)
    return LiveCheck("run_id_input", False, ("run id must be a safe filesystem label",))


def _plan_scenario(target: object, scenario_path: Path) -> tuple[object | None, LiveCheck]:
    try:
        scenario = parse_sdl_file(scenario_path)
        execution_plan = RuntimeManager(target).plan(scenario)
    except Exception as exc:
        return None, LiveCheck("planning", False, (f"scenario planning failed: {exc}",))
    diagnostics = tuple(f"{diag.code}: {diag.message}" for diag in execution_plan.diagnostics if diag.is_error)
    if diagnostics:
        return scenario, LiveCheck("planning", False, diagnostics)
    return scenario, LiveCheck("planning", True)


def _apply_plan(target: object, scenario_path: Path, driver: TechVaultNativeLibvirtDriver) -> LiveCheck:
    passed = False
    diagnostics: tuple[str, ...] = ()
    try:
        scenario = parse_sdl_file(scenario_path)
        execution_plan = RuntimeManager(target).plan(scenario)
        control_plane = RuntimeControlPlane(target, initial_snapshot=execution_plan.base_snapshot)
        receipt = control_plane.submit_provisioning(execution_plan.provisioning)
        status = control_plane.get_operation(receipt.operation_id)
    except Exception as exc:
        diagnostics = (f"provisioning raised: {exc}",)
    else:
        if status is None:
            diagnostics = ("control plane did not record provisioning status",)
        else:
            diagnostics = tuple(f"{diag.code}: {diag.message}" for diag in status.diagnostics if diag.is_error)
            if status.state.value != "succeeded" or diagnostics:
                diagnostics = diagnostics or (f"provisioning state={status.state.value}",)
            elif not _domains(driver.last_snapshot):
                diagnostics = ("native libvirt driver returned no domain snapshot",)
            else:
                passed = True
    return LiveCheck("aces_libvirt_native_boot", passed, diagnostics)


def _substrate_independence_check(snapshot: Mapping[str, Any]) -> LiveCheck:
    substrate = snapshot.get("substrate")
    if substrate == "libvirt-qemu-initramfs" and not snapshot.get("containers"):
        return LiveCheck("independent_libvirt_substrate", True)
    return LiveCheck(
        "independent_libvirt_substrate",
        False,
        (f"unexpected substrate/snapshot shape: substrate={substrate!r}",),
    )


def _surface_check(snapshot: Mapping[str, Any]) -> LiveCheck:
    surface = expected_surface(snapshot)
    domains = surface["domains"]
    networks = surface["networks"]
    diagnostics: list[str] = []
    if not domains:
        diagnostics.append("no native domains realized")
    if not networks:
        diagnostics.append("no native networks realized")
    return LiveCheck("model_derived_native_surface", not diagnostics, tuple(diagnostics))


def _readiness_check(snapshot: Mapping[str, Any], probe: NativeLibvirtProbe, timeout_seconds: int) -> LiveCheck:
    ok, diagnostics = check_native_readiness(snapshot, probe=probe, timeout_seconds=timeout_seconds)
    return LiveCheck("native_domain_service_readiness", ok, tuple(diagnostics))


def _kali_reachability_check(snapshot: Mapping[str, Any], probe: NativeLibvirtProbe) -> LiveCheck:
    kali = _domain_by_name(snapshot, "kali")
    if kali is None:
        return LiveCheck("kali_target_network_reachability", True, ("scenario does not include kali",))
    targets = _targets_sharing_network(kali, snapshot)
    diagnostics: list[str] = []
    for target in targets:
        ip = _first_ip(target)
        if ip and not probe.ping(ip).ok:
            diagnostics.append(f"kali-shared target {target.get('name')} is not reachable at {ip}")
    return LiveCheck("kali_target_network_reachability", not diagnostics, tuple(diagnostics))


def _soc_stack_readback_check(snapshot: Mapping[str, Any]) -> tuple[LiveCheck, dict[str, object]]:
    names = {str(domain.get("name", "")) for domain in _domains(snapshot)}
    evidence = {"soc_readback": native_soc_readback(snapshot)}
    diagnostics: list[str] = []
    if _FULL_SOC_NODES.issubset(names):
        diagnostics.extend(_full_soc_diagnostics(evidence["soc_readback"]))
    return LiveCheck("native_soc_stack_readback", not diagnostics, tuple(diagnostics)), evidence


def _full_soc_diagnostics(readback: object) -> tuple[str, ...]:
    if not isinstance(readback, Mapping):
        return ("native SOC readback is not structured",)
    diagnostics: list[str] = []
    suricata = readback.get("suricata", {})
    case_mgmt = readback.get("case_management", {})
    agents = readback.get("wazuh_active_agents", ())
    if not agents:
        diagnostics.append("native Wazuh readback reported no active agents")
    diagnostics.extend(_suricata_diagnostics(suricata))
    if not _has_case_management(case_mgmt):
        diagnostics.append("native case-management readback is missing TheHive, MISP, Cortex, or Shuffle")
    return tuple(diagnostics)


def _suricata_diagnostics(suricata: object) -> tuple[str, ...]:
    if not isinstance(suricata, Mapping):
        return ("native Suricata readback is not structured",)
    diagnostics: list[str] = []
    if suricata.get("rules_loaded", 0) <= 0:
        diagnostics.append("native Suricata readback reported no loaded rules")
    if suricata.get("rules_failed", 0) != 0:
        diagnostics.append("native Suricata readback reported failed rules")
    if suricata.get("kernel_drops", 0) != 0:
        diagnostics.append("native Suricata readback reported kernel drops")
    return tuple(diagnostics)


def _has_case_management(case_mgmt: object) -> bool:
    return isinstance(case_mgmt, Mapping) and all(
        case_mgmt.get(name) for name in ("thehive", "misp", "cortex", "shuffle")
    )


def _variation_check(snapshot: Mapping[str, Any]) -> LiveCheck:
    roles = {str(domain.get("role", "")) for domain in _domains(snapshot) if domain.get("role")}
    if len(roles) >= 1 and len(_domains(snapshot)) != 30:
        return LiveCheck("scenario_variant_composability", True)
    if len(roles) >= 4:
        return LiveCheck("scenario_variant_composability", True)
    return LiveCheck("scenario_variant_composability", False, ("native surface collapsed to too few role families",))


def _write_manifest(
    output_dir: Path,
    run_id: str,
    scenario_path: Path,
    driver: TechVaultNativeLibvirtDriver,
    checks: Sequence[LiveCheck],
    evidence: Mapping[str, object],
    *,
    clean_boot: bool,
) -> str | None:
    target = run_artifact_path(output_dir, run_id, "live-gate", "manifest.json")
    payload = {
        "schema": "aces.libvirt.techvault-native-live-gate/v1",
        "scenario": {"path": str(scenario_path), "name": scenario_path.name.split(".")[0]},
        "run_id": run_id,
        "recorded_at": datetime.now(UTC).isoformat(),
        "clean_boot": clean_boot,
        "aces_libvirt": {
            "substrate": "libvirt-qemu-initramfs",
            "surface": expected_surface(driver.last_snapshot),
        },
        "validation": {
            "ok": all(check.passed for check in checks),
            "checks": [
                {"name": check.name, "ok": check.passed, "diagnostics": list(check.diagnostics)} for check in checks
            ],
        },
        "snapshot": driver.last_snapshot,
        "evidence": dict(evidence),
    }
    try:
        atomic_write_json_artifact(target, payload)
    except OSError:
        return None
    return str(target)


def _domains(snapshot: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw = snapshot.get("domains", ())
    return tuple(item for item in raw if isinstance(item, Mapping)) if isinstance(raw, list | tuple) else ()


def _domain_by_name(snapshot: Mapping[str, Any], name: str) -> Mapping[str, Any] | None:
    return next((domain for domain in _domains(snapshot) if domain.get("name") == name), None)


def _targets_sharing_network(kali: Mapping[str, Any], snapshot: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    kali_networks = {
        str(interface.get("network_address", "")) for interface in _interfaces(kali) if interface.get("network_address")
    }
    targets: list[Mapping[str, Any]] = []
    for domain in _domains(snapshot):
        if domain.get("name") == "kali":
            continue
        domain_networks = {
            str(interface.get("network_address", ""))
            for interface in _interfaces(domain)
            if interface.get("network_address")
        }
        if kali_networks & domain_networks:
            targets.append(domain)
    return targets


def _interfaces(domain: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw = domain.get("interfaces", ())
    return tuple(item for item in raw if isinstance(item, Mapping)) if isinstance(raw, list | tuple) else ()


def _first_ip(domain: Mapping[str, Any]) -> str | None:
    for interface in _interfaces(domain):
        ip = interface.get("ip")
        if isinstance(ip, str) and ip:
            return ip
    return None
