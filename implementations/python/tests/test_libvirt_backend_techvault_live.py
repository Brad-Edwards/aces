"""ACES/libvirt TechVault live-gate orchestration."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime

from aces_backend_libvirt.techvault_driver import TechVaultComposeDriver, TechVaultLifecycleResult
from aces_operations.techvault_live import validate_techvault_live


class _Runner:
    def __init__(self) -> None:
        self.start_calls = 0

    def start(self, *, project_dir, profiles, clean_volumes, scenario_path):
        self.start_calls += 1
        return TechVaultLifecycleResult(
            success=True,
            profiles=profiles,
            snapshot={
                "containers": [
                    {
                        "name": "aptl-kali",
                        "status": "Up 1 second (healthy)",
                        "health": "healthy",
                        "networks": {"aptl-dmz": "172.20.1.20"},
                    },
                    {
                        "name": "aptl-webapp",
                        "status": "Up 1 second (healthy)",
                        "health": "healthy",
                        "networks": {"aptl-dmz": "172.20.1.10"},
                    },
                ]
            },
        )

    def stop(self, *, project_dir, profiles, remove_volumes):
        return TechVaultLifecycleResult(success=True, profiles=profiles)


class _Probe:
    def __init__(self) -> None:
        self.commands: list[tuple[str, tuple[str, ...]]] = []

    def exec(self, container, cmd, timeout=30):
        self.commands.append((container, tuple(cmd)))
        if container == "aptl-wazuh-manager":
            return subprocess.CompletedProcess(
                cmd,
                0,
                """
ID: 000, Name: wazuh.manager (server), IP: 127.0.0.1, Active/Local
ID: 001, Name: aptl-dns-agent, IP: any, Active
ID: 002, Name: aptl-fileshare-agent, IP: any, Active
ID: 003, Name: aptl-ad-agent, IP: any, Active
ID: 004, Name: aptl-webapp-agent, IP: any, Active
ID: 005, Name: aptl-suricata-agent, IP: any, Active
ID: 006, Name: aptl-db-agent, IP: any, Active
ID: 007, Name: ns1.techvault.local, IP: any, Active
""",
                "",
            )
        if container == "aptl-suricata":
            stats = {
                "event_type": "stats",
                "stats": {
                    "capture": {"kernel_packets": 10, "kernel_drops": 0},
                    "detect": {"engines": [{"rules_loaded": 42, "rules_failed": 0}]},
                },
            }
            return subprocess.CompletedProcess(cmd, 0, json.dumps(stats) + "\n", "")
        if cmd and cmd[0] == "ping":
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 1, "", "")


def test_validate_techvault_live_applies_scenario_and_records_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr("aces_operations.techvault_live.time.sleep", lambda _seconds: None)
    monkeypatch.setattr(
        "aces_operations.techvault_live._suricata_eve",
        lambda _probe, _start, _end: [{"timestamp": datetime.now(UTC).isoformat(), "event_type": "alert"}],
    )
    monkeypatch.setattr("aces_operations.techvault_live._wazuh_alerts", lambda _probe, _start, _end: [])
    _write_project_fixture(tmp_path)
    scenario = tmp_path / "mini-techvault.sdl.yaml"
    scenario.write_text(
        """
name: mini-techvault
nodes:
  dmz-net:
    type: switch
  kali:
    type: vm
    os: linux
    resources: {ram: 512 MiB, cpu: 1}
  webapp:
    type: vm
    os: linux
    resources: {ram: 512 MiB, cpu: 1}
infrastructure:
  dmz-net:
    properties: {cidr: 172.20.1.0/24, gateway: 172.20.1.1, internal: true}
  kali:
    links: [dmz-net]
  webapp:
    links: [dmz-net]
""",
        encoding="utf-8",
    )
    runner = _Runner()

    def _driver_factory():
        return TechVaultComposeDriver(project_dir=tmp_path, scenario_path=scenario, runner=runner)

    report = validate_techvault_live(
        scenario_path=scenario,
        project_dir=tmp_path,
        run_id="unit-live",
        driver_factory=_driver_factory,
        probe=_Probe(),
        event_window_seconds=1,
    )

    assert report.passed, report.render()
    assert runner.start_calls == 1
    manifest = tmp_path / "runs" / "unit-live" / "live-gate" / "manifest.json"
    assert manifest.exists()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["validation"]["ok"] is True
    assert payload["aces_libvirt"]["selected_profiles"] == ["kali", "enterprise", "otel"]


def _write_project_fixture(tmp_path):
    (tmp_path / "aptl.json").write_text(
        '{"containers": {"kali": true, "enterprise": true, "soc": false}}',
        encoding="utf-8",
    )
    (tmp_path / "docker-compose.yml").write_text(
        """
services:
  kali:
    profiles: ["kali"]
    container_name: aptl-kali
  webapp:
    profiles: ["enterprise"]
    container_name: aptl-webapp
""",
        encoding="utf-8",
    )
