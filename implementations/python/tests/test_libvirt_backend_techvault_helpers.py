"""Helper coverage for the ACES/libvirt TechVault live path."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import types
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aces_backend_libvirt import _techvault_aptl_entry as aptl_entry
from aces_backend_libvirt.techvault_driver import _decode_helper_payload
from aces_operations import techvault_live as live


@dataclass(frozen=True)
class _Result:
    success: bool
    error: str = ""


class _Snapshot:
    def to_dict(self):
        return {"containers": [{"name": "aptl-kali"}]}


class _Backend:
    def __init__(self, outcomes: list[_Result] | None = None) -> None:
        self.outcomes = outcomes or [_Result(True)]
        self.start_calls: list[tuple[str, ...]] = []
        self.stop_calls: list[dict[str, object]] = []

    def start(self, profiles):
        self.start_calls.append(tuple(profiles))
        return self.outcomes.pop(0)

    def stop(self, profiles, *, remove_volumes):
        self.stop_calls.append({"profiles": tuple(profiles), "remove_volumes": remove_volumes})
        return _Result(True)


def test_aptl_entry_start_runs_setup_retry_and_snapshot(monkeypatch, tmp_path):
    backend = _Backend([_Result(False, "warming"), _Result(True)])
    lab = _install_fake_aptl_lab(monkeypatch, backend=backend)
    monkeypatch.setattr(aptl_entry.time, "sleep", lambda _seconds: None)
    args = argparse.Namespace(
        project_dir=str(tmp_path),
        profiles_json=json.dumps(["soc", "kali"]),
        clean_volumes=True,
        scenario_path=str(tmp_path / "scenario.sdl.yaml"),
    )

    payload = aptl_entry._start(args)

    assert payload["success"] is True
    assert payload["profiles"] == ["soc", "kali"]
    assert payload["snapshot"] == {"containers": [{"name": "aptl-kali"}]}
    assert backend.start_calls == [("soc", "kali"), ("soc", "kali")]
    assert lab.stop_calls == [{"remove_volumes": True, "project_dir": tmp_path}]
    assert payload["diagnostics"] == [
        {
            "step": "wait",
            "impact": "readiness",
            "severity": "info",
            "message": "settled",
            "component": "wazuh",
        }
    ]


def test_aptl_entry_start_reports_cleanup_failure(monkeypatch, tmp_path):
    lab = _install_fake_aptl_lab(monkeypatch, stop_result=_Result(False, "volumes busy"))
    args = argparse.Namespace(
        project_dir=str(tmp_path),
        profiles_json=json.dumps(["soc"]),
        clean_volumes=True,
        scenario_path="",
    )

    payload = aptl_entry._start(args)

    assert payload["success"] is False
    assert payload["error"] == "clean-state cleanup failed: volumes busy"
    assert lab.contexts == []


def test_aptl_entry_stop_uses_backend(monkeypatch, tmp_path):
    backend = _Backend()
    _install_fake_aptl_lab(monkeypatch, backend=backend)
    args = argparse.Namespace(
        project_dir=str(tmp_path),
        profiles_json=json.dumps(["wazuh"]),
        remove_volumes=True,
    )

    payload = aptl_entry._stop(args)

    assert payload == {"success": True, "profiles": ["wazuh"], "snapshot": {}, "diagnostics": []}
    assert backend.stop_calls == [{"profiles": ("wazuh",), "remove_volumes": True}]


def test_decode_helper_payload_handles_invalid_and_valid_results():
    assert _decode_helper_payload("").error == "APTL helper produced no JSON result."
    assert _decode_helper_payload("not-json").error == "APTL helper produced invalid JSON."
    assert _decode_helper_payload("[]").error == "APTL helper JSON result was not an object."

    result = _decode_helper_payload(
        "noise\n"
        + json.dumps(
            {
                "success": True,
                "profiles": ["wazuh", "soc"],
                "snapshot": {"containers": []},
                "diagnostics": [{"message": "ok"}, "skip"],
            }
        )
    )

    assert result.success is True
    assert result.profiles == ("wazuh", "soc")
    assert result.snapshot == {"containers": []}
    assert result.diagnostics == ({"message": "ok"},)


def test_live_gate_helper_branches(monkeypatch):
    assert live._check_run_id("safe-run").passed
    assert not live._check_run_id("../bad").passed
    assert "FAIL" in live.TechVaultLiveReport("scenario", "project", "run", (live.LiveCheck("x", False),)).render()
    assert live._entry_time("") == datetime.min.replace(tzinfo=UTC)
    assert live._entry_time("not-a-time") == datetime.min.replace(tzinfo=UTC)
    assert live._entry_time("2026-06-27T04:10:16Z").tzinfo == UTC
    assert live._json_lines('{"a": 1}\nnot-json\n[]\n') == [{"a": 1}]
    assert live._nested_mapping({"a": [{"b": 2}]}, ("a", 0)) == {"b": 2}
    assert live._nested_mapping({"a": []}, ("a", 1)) == {}
    assert live._int_value(3) == 3
    assert live._int_value("3") == 0
    monkeypatch.setattr(live.time, "sleep", lambda _seconds: None)


def test_shared_targets_reports_missing_and_success_cases():
    assert live._shared_targets({}) == (None, [], ["Kali container not present"])
    kali_no_networks = {"containers": [{"name": "aptl-kali", "networks": {}}]}
    assert live._shared_targets(kali_no_networks) == (
        {"name": "aptl-kali", "networks": {}},
        [],
        ["Kali container has no network attachments"],
    )
    success = {
        "containers": [
            {"name": "aptl-kali", "networks": {"red": "10.0.0.2"}},
            {"name": "aptl-webapp", "networks": {"red": "10.0.0.10"}},
        ]
    }
    assert live._shared_targets(success) == (
        {"name": "aptl-kali", "networks": {"red": "10.0.0.2"}},
        [("aptl-webapp", "10.0.0.10")],
        [],
    )


def test_soc_stack_readback_reports_missing_agents_and_suricata_failures(monkeypatch):
    class Probe:
        def exec(self, container, cmd, timeout=30):
            if container == "aptl-wazuh-manager":
                return subprocess.CompletedProcess(cmd, 0, "ID: 000, Name: wazuh.manager (server), Active/Local\n", "")
            stats = {
                "event_type": "stats",
                "stats": {
                    "capture": {"kernel_packets": 10, "kernel_drops": 1},
                    "detect": {"engines": [{"rules_loaded": 0, "rules_failed": 1}]},
                },
            }
            return subprocess.CompletedProcess(cmd, 0, json.dumps(stats) + "\n", "")

    monkeypatch.setattr(live.time, "sleep", lambda _seconds: None)

    check, evidence = live._soc_stack_readback_check(Probe())

    assert not check.passed
    assert any("missing active Wazuh agents" in item for item in check.diagnostics)
    assert "Suricata did not report loaded rules" in check.diagnostics
    assert "Suricata reported failed rules: 1" in check.diagnostics
    assert "Suricata reported kernel drops: 1" in check.diagnostics
    assert evidence["soc_readback"]["suricata"]["rules_failed"] == 1


def test_apply_plan_reports_missing_operation(monkeypatch, tmp_path):
    class Manager:
        def __init__(self, target):
            self.target = target

        def plan(self, scenario):
            return types.SimpleNamespace(base_snapshot=object(), provisioning=object())

    class ControlPlane:
        def __init__(self, target, *, initial_snapshot):
            self.target = target
            self.initial_snapshot = initial_snapshot

        def submit_provisioning(self, provisioning):
            return types.SimpleNamespace(operation_id="op")

        def get_operation(self, operation_id):
            return None

    monkeypatch.setattr(live, "parse_sdl_file", lambda _path: object())
    monkeypatch.setattr(live, "RuntimeManager", Manager)
    monkeypatch.setattr(live, "RuntimeControlPlane", ControlPlane)
    driver = types.SimpleNamespace(last_snapshot={})

    check = live._apply_plan(object(), tmp_path / "scenario.sdl.yaml", driver)

    assert not check.passed
    assert check.diagnostics == ("control plane did not record provisioning status",)


def _install_fake_aptl_lab(
    monkeypatch,
    *,
    backend: _Backend | None = None,
    stop_result: _Result | None = None,
):
    backend = backend or _Backend()
    stop_result = stop_result or _Result(True)
    lab = types.ModuleType("aptl.core.lab")
    lab.stop_calls = []
    lab.contexts = []

    class _Value:
        def __init__(self, value: str) -> None:
            self.value = value

    class _Diag:
        step = "wait"
        impact = _Value("readiness")
        severity = _Value("info")
        message = "settled"
        component = "wazuh"

    class _Context:
        def __init__(self, *, project_dir: Path, skip_seed: bool, scenario_path: Path | None) -> None:
            self.project_dir = project_dir
            self.skip_seed = skip_seed
            self.scenario_path = scenario_path
            self.backend = backend
            self.snapshot = _Snapshot()
            self.diagnostics = [_Diag()]
            self.selected_profiles: set[str] = set()
            lab.contexts.append(self)

    def stop_lab(*, remove_volumes: bool, project_dir: Path):
        lab.stop_calls.append({"remove_volumes": remove_volumes, "project_dir": project_dir})
        return stop_result

    def step(_ctx):
        return None

    lab._LabStartContext = _Context
    lab._step_load_env = step
    lab._step_load_config = step
    lab._step_ensure_ssh_keys = step
    lab._step_check_sysreqs = step
    lab._step_sync_credentials = step
    lab._step_seed_suricata_volumes = step
    lab._step_generate_certs = step
    lab._step_generate_soc_certs = step
    lab._step_check_bind_mounts = step
    lab._step_pull_images = step
    lab._step_wait_for_services = step
    lab._step_test_ssh = step
    lab._step_capture_snapshot = step
    lab.stop_lab = stop_lab
    lab.find_config = lambda _project_dir: None
    lab.load_config = lambda _path: object()
    lab._get_backend = lambda _project_dir, _config: backend

    aptl = types.ModuleType("aptl")
    core = types.ModuleType("aptl.core")
    aptl.core = core
    core.lab = lab
    monkeypatch.setitem(sys.modules, "aptl", aptl)
    monkeypatch.setitem(sys.modules, "aptl.core", core)
    monkeypatch.setitem(sys.modules, "aptl.core.lab", lab)
    return lab
