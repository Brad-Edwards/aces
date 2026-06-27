"""ACES CLI wiring for libvirt operations."""

from __future__ import annotations

from dataclasses import dataclass

from aces_cli.main import app
from typer.testing import CliRunner


@dataclass(frozen=True)
class _Report:
    passed: bool = True

    def render(self) -> str:
        return "live ok"


def test_libvirt_techvault_validate_live_cli_invokes_gate(monkeypatch, tmp_path):
    calls: list[dict[str, object]] = []

    def _validate(**kwargs):
        calls.append(kwargs)
        return _Report()

    monkeypatch.setattr("aces_cli.libvirt.validate_techvault_live", _validate)
    scenario = tmp_path / "scenario.sdl.yaml"
    scenario.write_text("name: cli\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "libvirt",
            "techvault",
            "validate-live",
            "--scenario",
            str(scenario),
            "--project-dir",
            str(tmp_path),
            "--run-id",
            "cli-run",
            "--skip-clean-boot",
            "--connection-uri",
            "qemu:///session",
            "--appliance-memory-mib",
            "96",
            "--boot-timeout-seconds",
            "7",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "live ok" in result.output
    assert calls == [
        {
            "scenario_path": scenario.resolve(),
            "project_dir": tmp_path.resolve(),
            "run_id": "cli-run",
            "clean_boot": False,
            "connection_uri": "qemu:///session",
            "appliance_memory_mib": 96,
            "boot_timeout_seconds": 7,
        }
    ]
