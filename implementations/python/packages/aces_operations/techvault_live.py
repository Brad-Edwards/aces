"""ACES/libvirt live validation for the TechVault operational scenario."""

from __future__ import annotations

import json
import re
import subprocess
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aces_backend_libvirt.target import create_libvirt_target
from aces_backend_libvirt.techvault_driver import TechVaultComposeDriver
from aces_backend_libvirt.techvault_profiles import normalize_identifier
from aces_runtime.control_plane import RuntimeControlPlane
from aces_runtime.manager import RuntimeManager
from aces_sdl.parser import parse_sdl_file

DEFAULT_EVENT_WINDOW_SECONDS = 180
_KALI_CONTAINER = "aptl-kali"
_POLL_STEP_SECONDS = 10
_SOC_READBACK_WINDOW_SECONDS = 180
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_NON_TRAFFIC_EVENT_TYPES = frozenset({"stats"})
_REQUIRED_WAZUH_AGENTS = frozenset(
    {
        "wazuh.manager",
        "aptl-dns-agent",
        "aptl-fileshare-agent",
        "aptl-ad-agent",
        "aptl-webapp-agent",
        "aptl-suricata-agent",
        "aptl-db-agent",
        "ns1.techvault.local",
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
    """Rendered outcome for the ACES/libvirt TechVault live gate."""

    scenario: str
    project_dir: str
    run_id: str
    checks: tuple[LiveCheck, ...]
    manifest_path: str | None = None

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def render(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [f"ACES/libvirt TechVault live gate -- scenario={self.scenario} run_id={self.run_id}: {status}"]
        for check in self.checks:
            marker = "ok" if check.passed else "FAIL"
            lines.append(f"  [{marker}] {check.name}")
            for diagnostic in check.diagnostics:
                lines.append(f"        - {diagnostic}")
        if self.manifest_path:
            lines.append(f"  manifest: {self.manifest_path}")
        return "\n".join(lines)


class DockerProbe:
    """Local Docker probes used by the TechVault live gate."""

    def exec(self, container: str, cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker", "exec", container, *cmd],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )


def validate_techvault_live(
    *,
    scenario_path: Path,
    project_dir: Path,
    run_id: str,
    clean_boot: bool = True,
    event_window_seconds: int = DEFAULT_EVENT_WINDOW_SECONDS,
    driver_factory: Callable[[], TechVaultComposeDriver] | None = None,
    probe: DockerProbe | None = None,
) -> TechVaultLiveReport:
    """Boot and validate TechVault through ACES/libvirt."""

    checks: list[LiveCheck] = []
    run_id_check = _check_run_id(run_id)
    checks.append(run_id_check)
    if not run_id_check.passed:
        return TechVaultLiveReport(str(scenario_path), str(project_dir), run_id, tuple(checks))

    driver = (
        driver_factory()
        if driver_factory
        else TechVaultComposeDriver(
            project_dir=project_dir,
            scenario_path=scenario_path,
            clean_boot=clean_boot,
        )
    )
    target = create_libvirt_target(driver=driver, name_prefix="techvault-live")
    scenario, plan_check = _plan_scenario(target, scenario_path)
    del scenario
    checks.append(plan_check)
    if not plan_check.passed:
        return TechVaultLiveReport(str(scenario_path), str(project_dir), run_id, tuple(checks))

    boot_check = _apply_plan(target, scenario_path, driver)
    checks.append(boot_check)
    snapshot = driver.last_snapshot
    if not boot_check.passed:
        manifest_path = _write_manifest(project_dir, run_id, scenario_path, driver, checks, {})
        return TechVaultLiveReport(str(scenario_path), str(project_dir), run_id, tuple(checks), manifest_path)

    checks.append(_readiness_check(snapshot, driver))
    docker_probe = probe or DockerProbe()
    checks.append(_kali_reachability_check(snapshot, docker_probe))
    evidence: dict[str, object] = {}
    telemetry_check, evidence = _telemetry_check(snapshot, docker_probe, event_window_seconds)
    checks.append(telemetry_check)
    soc_check, soc_evidence = _soc_stack_readback_check(docker_probe)
    checks.append(soc_check)
    evidence.update(soc_evidence)
    checks.append(_variation_check(driver))
    manifest_path = _write_manifest(project_dir, run_id, scenario_path, driver, checks, evidence)
    checks.append(
        LiveCheck(
            "run_archive_manifest", manifest_path is not None, () if manifest_path else ("manifest write failed",)
        )
    )
    return TechVaultLiveReport(str(scenario_path), str(project_dir), run_id, tuple(checks), manifest_path)


def _check_run_id(run_id: str) -> LiveCheck:
    if _RUN_ID_RE.match(run_id):
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


def _apply_plan(target: object, scenario_path: Path, driver: TechVaultComposeDriver) -> LiveCheck:
    try:
        scenario = parse_sdl_file(scenario_path)
        execution_plan = RuntimeManager(target).plan(scenario)
        control_plane = RuntimeControlPlane(target, initial_snapshot=execution_plan.base_snapshot)
        receipt = control_plane.submit_provisioning(execution_plan.provisioning)
        status = control_plane.get_operation(receipt.operation_id)
    except Exception as exc:
        return LiveCheck("aces_libvirt_driven_boot", False, (f"provisioning raised: {exc}",))
    if status is None:
        return LiveCheck("aces_libvirt_driven_boot", False, ("control plane did not record provisioning status",))
    diagnostics = tuple(f"{diag.code}: {diag.message}" for diag in status.diagnostics if diag.is_error)
    if status.state.value != "succeeded" or diagnostics:
        return LiveCheck(
            "aces_libvirt_driven_boot", False, diagnostics or (f"provisioning state={status.state.value}",)
        )
    if not driver.last_snapshot.get("containers"):
        return LiveCheck("aces_libvirt_driven_boot", False, ("driver returned no post-boot container snapshot",))
    return LiveCheck("aces_libvirt_driven_boot", True)


def _readiness_check(snapshot: Mapping[str, Any], driver: TechVaultComposeDriver) -> LiveCheck:
    containers = _containers(snapshot)
    if not containers:
        return LiveCheck("defensive_stack_readiness", False, ("no containers in snapshot",))
    by_alias = _container_alias_index(containers)
    diagnostics: list[str] = []
    nodes = sorted((driver.last_selection.mapped_nodes if driver.last_selection else {}).keys())
    for node in nodes:
        container = _find_container_for_node(by_alias, node)
        if container is None:
            diagnostics.append(f"no running container matched ACES node {node!r}")
            continue
        status = str(container.get("status", ""))
        health = str(container.get("health", ""))
        if "Up" not in status:
            diagnostics.append(f"{container.get('name')} is not running: {status}")
        if health == "unhealthy":
            diagnostics.append(f"{container.get('name')} is unhealthy")
    return LiveCheck("defensive_stack_readiness", not diagnostics, tuple(diagnostics))


def _kali_reachability_check(snapshot: Mapping[str, Any], probe: DockerProbe) -> LiveCheck:
    kali, targets, diagnostics = _shared_targets(snapshot)
    del kali
    if diagnostics:
        return LiveCheck("kali_reachability", False, tuple(diagnostics))
    failed: list[str] = []
    for name, ip in targets:
        result = probe.exec(_KALI_CONTAINER, ["ping", "-c", "1", "-W", "2", ip], timeout=15)
        if result.returncode != 0:
            failed.append(f"Kali cannot reach {name} ({ip})")
    return LiveCheck("kali_reachability", not failed, tuple(failed))


def _telemetry_check(
    snapshot: Mapping[str, Any],
    probe: DockerProbe,
    event_window_seconds: int,
) -> tuple[LiveCheck, dict[str, object]]:
    _kali, targets, diagnostics = _shared_targets(snapshot)
    if diagnostics:
        return LiveCheck("telemetry_evidence_path", False, tuple(diagnostics)), {}
    start = _now()
    _generate_event(probe, targets)
    eve: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    for _ in range(max(1, event_window_seconds // _POLL_STEP_SECONDS)):
        time.sleep(_POLL_STEP_SECONDS)
        end = _now()
        eve = _suricata_eve(probe, start, end)
        alerts = _wazuh_alerts(probe, start, end)
        if any(_is_traffic_event(entry) for entry in eve) or alerts:
            break
    evidence = {
        "telemetry": {
            "window": [start.isoformat(), _now().isoformat()],
            "suricata_event_types": dict(Counter(str(entry.get("event_type", "unknown")) for entry in eve)),
            "suricata_traffic_event_count": sum(1 for entry in eve if _is_traffic_event(entry)),
            "wazuh_alert_count": len(alerts),
        }
    }
    if evidence["telemetry"]["suricata_traffic_event_count"] + len(alerts) < 1:  # type: ignore[index, operator]
        return LiveCheck(
            "telemetry_evidence_path", False, ("no traffic-derived Suricata event or Wazuh alert observed",)
        ), evidence
    return LiveCheck("telemetry_evidence_path", True), evidence


def _variation_check(driver: TechVaultComposeDriver) -> LiveCheck:
    selection = driver.last_selection
    if selection is None or len(set(selection.mapped_nodes.values())) < 2:
        return LiveCheck("scenario_variation", False, ("fewer than two distinct profile mappings were realized",))
    return LiveCheck("scenario_variation", True)


def _soc_stack_readback_check(probe: DockerProbe) -> tuple[LiveCheck, dict[str, object]]:
    diagnostics: list[str] = []
    agents = _wait_for_wazuh_agents(probe)
    missing_agents = sorted(_REQUIRED_WAZUH_AGENTS - set(agents))
    if missing_agents:
        diagnostics.append("missing active Wazuh agents: " + ", ".join(missing_agents))
    suricata = _suricata_runtime_summary(probe)
    if suricata.get("rules_loaded", 0) <= 0:
        diagnostics.append("Suricata did not report loaded rules")
    if suricata.get("rules_failed", 0) != 0:
        diagnostics.append(f"Suricata reported failed rules: {suricata.get('rules_failed')}")
    if suricata.get("kernel_drops", 0) != 0:
        diagnostics.append(f"Suricata reported kernel drops: {suricata.get('kernel_drops')}")
    evidence = {"soc_readback": {"wazuh_active_agents": agents, "suricata": suricata}}
    return LiveCheck("soc_stack_readback", not diagnostics, tuple(diagnostics)), evidence


def _wait_for_wazuh_agents(probe: DockerProbe) -> tuple[str, ...]:
    agents: tuple[str, ...] = ()
    for _ in range(max(1, _SOC_READBACK_WINDOW_SECONDS // _POLL_STEP_SECONDS)):
        agents = _wazuh_active_agents(probe)
        if _REQUIRED_WAZUH_AGENTS.issubset(agents):
            return agents
        time.sleep(_POLL_STEP_SECONDS)
    return agents


def _wazuh_active_agents(probe: DockerProbe) -> tuple[str, ...]:
    result = probe.exec("aptl-wazuh-manager", ["/var/ossec/bin/agent_control", "-l"], timeout=30)
    if result.returncode != 0:
        return ()
    active: list[str] = []
    for line in result.stdout.splitlines():
        if "Active" not in line:
            continue
        marker = "Name:"
        if marker not in line:
            continue
        name = line.split(marker, 1)[1].split(",", 1)[0].strip()
        name = name.removesuffix(" (server)")
        if name:
            active.append(name)
    return tuple(sorted(set(active)))


def _suricata_runtime_summary(probe: DockerProbe) -> dict[str, int]:
    result = probe.exec("aptl-suricata", ["tail", "-n", "5000", "/var/log/suricata/eve.json"], timeout=30)
    if result.returncode != 0:
        return {}
    entries = _json_lines(result.stdout)
    stats_entries = [entry for entry in entries if entry.get("event_type") == "stats"]
    latest_stats = stats_entries[-1] if stats_entries else {}
    capture = _nested_mapping(latest_stats, ("stats", "capture"))
    engine = _nested_mapping(latest_stats, ("stats", "detect", "engines", 0))
    return {
        "events": len(entries),
        "alerts": sum(1 for entry in entries if entry.get("event_type") == "alert"),
        "stats": len(stats_entries),
        "kernel_packets": _int_value(capture.get("kernel_packets")),
        "kernel_drops": _int_value(capture.get("kernel_drops")),
        "rules_loaded": _int_value(engine.get("rules_loaded")),
        "rules_failed": _int_value(engine.get("rules_failed")),
    }


def _shared_targets(snapshot: Mapping[str, Any]) -> tuple[Mapping[str, Any] | None, list[tuple[str, str]], list[str]]:
    containers = _containers(snapshot)
    kali = next((container for container in containers if container.get("name") == _KALI_CONTAINER), None)
    if kali is None:
        return None, [], ["Kali container not present"]
    kali_networks = set(_networks(kali))
    if not kali_networks:
        return kali, [], ["Kali container has no network attachments"]
    targets: list[tuple[str, str]] = []
    for container in containers:
        if container.get("name") == _KALI_CONTAINER:
            continue
        shared = kali_networks & set(_networks(container))
        for network in sorted(shared):
            ip = _networks(container).get(network)
            if ip:
                targets.append((str(container.get("name", "?")), str(ip)))
                break
    if not targets:
        return kali, [], ["no containers share a network with Kali"]
    return kali, targets, []


def _generate_event(probe: DockerProbe, targets: list[tuple[str, str]]) -> None:
    first_ip = targets[0][1]
    probe.exec(_KALI_CONTAINER, ["nmap", "-Pn", "-T4", "-p", "22,80,443,445", first_ip], timeout=120)
    for _name, ip in targets[:3]:
        for _attempt in range(3):
            probe.exec(
                _KALI_CONTAINER,
                [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "ConnectTimeout=3",
                    "-p",
                    "22",
                    f"aces-live-gate-invalid@{ip}",
                    "true",
                ],
                timeout=15,
            )


def _suricata_eve(probe: DockerProbe, start: datetime, end: datetime) -> list[dict[str, Any]]:
    result = probe.exec("aptl-suricata", ["cat", "/var/log/suricata/eve.json"], timeout=30)
    if result.returncode != 0:
        return []
    return [
        entry for entry in _json_lines(result.stdout) if start <= _entry_time(str(entry.get("timestamp", ""))) <= end
    ]


def _wazuh_alerts(probe: DockerProbe, start: datetime, end: datetime) -> list[dict[str, Any]]:
    result = probe.exec("aptl-wazuh-manager", ["tail", "-n", "5000", "/var/ossec/logs/alerts/alerts.json"], timeout=30)
    if result.returncode != 0:
        return []
    return [
        entry for entry in _json_lines(result.stdout) if start <= _entry_time(str(entry.get("timestamp", ""))) <= end
    ]


def _json_lines(raw: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line in raw.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def _nested_mapping(root: Mapping[str, Any], path: tuple[str | int, ...]) -> Mapping[str, Any]:
    value: object = root
    for part in path:
        if isinstance(part, int):
            if not isinstance(value, list) or len(value) <= part:
                return {}
            value = value[part]
        else:
            if not isinstance(value, Mapping):
                return {}
            value = value.get(part, {})
    return value if isinstance(value, Mapping) else {}


def _int_value(raw: object) -> int:
    return raw if isinstance(raw, int) else 0


def _entry_time(raw: str) -> datetime:
    if not raw:
        return datetime.min.replace(tzinfo=UTC)
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _is_traffic_event(entry: object) -> bool:
    return isinstance(entry, dict) and str(entry.get("event_type", "")) not in _NON_TRAFFIC_EVENT_TYPES


def _containers(snapshot: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    containers = snapshot.get("containers", ())
    return (
        tuple(container for container in containers if isinstance(container, Mapping))
        if isinstance(containers, list)
        else ()
    )


def _networks(container: Mapping[str, Any]) -> Mapping[str, str]:
    networks = container.get("networks", {})
    return networks if isinstance(networks, Mapping) else {}


def _container_alias_index(containers: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    aliases: dict[str, Mapping[str, Any]] = {}
    for container in containers:
        name = str(container.get("name", ""))
        for alias in {normalize_identifier(name), normalize_identifier(name).removeprefix("aptl-")}:
            if alias:
                aliases[alias] = container
    return aliases


def _find_container_for_node(by_alias: Mapping[str, Mapping[str, Any]], node: str) -> Mapping[str, Any] | None:
    normalized = normalize_identifier(node)
    return by_alias.get(normalized) or by_alias.get(f"aptl-{normalized}")


def _write_manifest(
    project_dir: Path,
    run_id: str,
    scenario_path: Path,
    driver: TechVaultComposeDriver,
    checks: Sequence[LiveCheck],
    evidence: Mapping[str, object],
) -> str | None:
    target = project_dir / "runs" / run_id / "live-gate" / "manifest.json"
    payload = {
        "schema": "aces.libvirt.techvault-live-gate/v1",
        "scenario": {"path": str(scenario_path), "name": scenario_path.name.split(".")[0]},
        "run_id": run_id,
        "aces_libvirt": {
            "selected_profiles": list(driver.last_selection.profiles if driver.last_selection else ()),
            "mapped_nodes": driver.last_selection.mapped_nodes if driver.last_selection else {},
            "helper_diagnostics": list(driver.last_diagnostics),
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
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        return None
    return str(target)


def _now() -> datetime:
    return datetime.now(UTC)
