"""ACES CLI wiring for libvirt operations."""

from __future__ import annotations

from dataclasses import dataclass

from raes_cli.main import app
from raes_operations.libvirt_evidence_run import LibvirtEvidenceRunConfig
from raes_operations.techvault_live import TechVaultLiveConfig
from typer.testing import CliRunner


@dataclass(frozen=True)
class _Report:
    passed: bool = True

    def render(self) -> str:
        return "live ok" if self.passed else "live failed"


def test_libvirt_techvault_validate_live_cli_invokes_gate(monkeypatch, tmp_path):
    calls: list[dict[str, object]] = []

    def _validate(**kwargs):
        calls.append(kwargs)
        return _Report()

    monkeypatch.setattr("raes_cli.libvirt.validate_techvault_live", _validate)
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
            "--yes",
            "--connection-uri",
            "qemu:///session",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "live ok" in result.output
    assert calls == [
        {
            "scenario_path": scenario.resolve(),
            "project_dir": tmp_path.resolve(),
            "run_id": "cli-run",
            "config": TechVaultLiveConfig(
                connection_uri="qemu:///session",
            ),
        }
    ]


def test_libvirt_techvault_validate_live_cli_returns_failure_exit(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "raes_cli.libvirt.validate_techvault_live",
        lambda **_kwargs: _Report(passed=False),
    )
    scenario = tmp_path / "scenario.sdl.yaml"
    scenario.write_text("name: cli\n", encoding="utf-8")

    result = CliRunner().invoke(
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
            "--yes",
        ],
    )

    assert result.exit_code == 1
    assert "live failed" in result.output


def test_libvirt_techvault_cli_has_no_unbound_memory_override(monkeypatch, tmp_path):
    calls: list[dict[str, object]] = []

    def _validate(**kwargs):
        calls.append(kwargs)
        return _Report()

    monkeypatch.setattr("raes_cli.libvirt.validate_techvault_live", _validate)
    scenario = tmp_path / "scenario.sdl.yaml"
    scenario.write_text("name: cli\n", encoding="utf-8")

    result = CliRunner().invoke(
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
            "--yes",
            "--appliance-memory-mib",
            "96",
        ],
    )

    assert result.exit_code == 2
    assert calls == []


def test_libvirt_techvault_guest_certify_cli_invokes_evidence_run(monkeypatch, tmp_path):
    calls: list[dict[str, object]] = []

    def _run(**kwargs):
        calls.append(kwargs)
        return _Report()

    monkeypatch.setattr("raes_cli.libvirt.run_libvirt_evidence_run", _run)
    scenario = tmp_path / "scenario.sdl.yaml"
    scenario.write_text("name: cli\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "libvirt",
            "techvault",
            "guest-certify",
            "--scenario",
            str(scenario),
            "--project-dir",
            str(tmp_path),
            "--run-id",
            "gc-cli",
            "--yes",
            "--connection-uri",
            "qemu:///system",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "scenario_path": scenario.resolve(),
            "project_dir": tmp_path.resolve(),
            "run_id": "gc-cli",
            "config": LibvirtEvidenceRunConfig(
                evidence_source_mode="guest-certified",
                connection_uri="qemu:///system",
            ),
        }
    ]


def test_libvirt_techvault_guest_certify_cli_returns_failure_exit(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "raes_cli.libvirt.run_libvirt_evidence_run",
        lambda **_kwargs: _Report(passed=False),
    )
    scenario = tmp_path / "scenario.sdl.yaml"
    scenario.write_text("name: cli\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["libvirt", "techvault", "guest-certify", "--scenario", str(scenario), "--project-dir", str(tmp_path), "--yes"],
    )

    assert result.exit_code == 1


def test_libvirt_techvault_guest_certify_cli_rejects_credentials(monkeypatch, tmp_path):
    calls: list[dict[str, object]] = []
    monkeypatch.setattr("raes_cli.libvirt.run_libvirt_evidence_run", lambda **kwargs: calls.append(kwargs))
    scenario = tmp_path / "scenario.sdl.yaml"
    scenario.write_text("name: cli\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "libvirt",
            "techvault",
            "guest-certify",
            "--scenario",
            str(scenario),
            "--yes",
            "--connection-uri",
            "qemu+ssh://operator:credential@example/system",
        ],
    )

    assert result.exit_code == 2
    assert calls == []


def test_libvirt_techvault_cli_rejects_connection_uri_credentials(monkeypatch, tmp_path):
    calls: list[dict[str, object]] = []
    monkeypatch.setattr("raes_cli.libvirt.validate_techvault_live", lambda **kwargs: calls.append(kwargs))
    scenario = tmp_path / "scenario.sdl.yaml"
    scenario.write_text("name: cli\n", encoding="utf-8")

    result = CliRunner().invoke(
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
            "--yes",
            "--connection-uri",
            "qemu+ssh://operator:credential@example/system",
        ],
    )

    assert result.exit_code == 2
    assert calls == []
