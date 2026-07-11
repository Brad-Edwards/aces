"""Libvirt backend operational commands."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import typer
from aces_operations.libvirt_evidence_run import LibvirtEvidenceRunConfig, run_libvirt_evidence_run
from aces_operations.techvault_live import TechVaultLiveConfig, validate_techvault_live

app = typer.Typer(help="Libvirt backend operations.")
techvault_app = typer.Typer(help="TechVault operational scenario checks.")
app.add_typer(techvault_app, name="techvault")
evidence_app = typer.Typer(help="Scenario evaluator-evidence artifacts.")
app.add_typer(evidence_app, name="evidence")

_LIVE_WARNING = """\
This will create native libvirt/QEMU resources for the selected TechVault
scenario and write a live-gate archive under the output directory.
"""


def _noncredential_connection_uri(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.username is not None or parsed.password is not None:
        raise typer.BadParameter("connection URI must not contain credentials")
    return value


@techvault_app.command("validate-live")
def validate_live(
    scenario: Path = typer.Option(
        Path("examples/scenarios/techvault-operational.sdl.yaml"),
        "--scenario",
        help="ACES SDL scenario to boot and validate.",
    ),
    project_dir: Path = typer.Option(
        Path("."),
        "--project-dir",
        "--output-dir",
        help="Output directory for native libvirt live-gate archives.",
    ),
    run_id: str | None = typer.Option(
        None,
        "--run-id",
        help="Run id for the live-gate archive.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the native libvirt resource confirmation prompt.",
    ),
    connection_uri: str = typer.Option(
        "qemu:///system",
        "--connection-uri",
        callback=_noncredential_connection_uri,
        help="libvirt connection URI.",
    ),
) -> None:
    """Boot TechVault through native ACES/libvirt and run the live validation gate."""

    if not yes:
        typer.echo(_LIVE_WARNING)
        if not typer.confirm("Continue?", default=False):
            typer.echo("Aborted.")
            raise typer.Exit(code=0)
    resolved_run_id = run_id or datetime.now(UTC).strftime("aces_libvirt_techvault_%Y%m%dT%H%M%SZ")
    report = validate_techvault_live(
        scenario_path=scenario.resolve(),
        project_dir=project_dir.resolve(),
        run_id=resolved_run_id,
        config=TechVaultLiveConfig(
            connection_uri=connection_uri,
        ),
    )
    typer.echo(report.render())
    if not report.passed:
        raise typer.Exit(code=1)


@evidence_app.command("validate")
def validate_evidence(
    scenario: Path = typer.Option(
        Path("examples/scenarios/enterprise-participant-evidence-loop.sdl.yaml"),
        "--scenario",
        help="Reference ACES SDL scenario to produce evaluator evidence for.",
    ),
    project_dir: Path = typer.Option(
        Path("."),
        "--project-dir",
        "--output-dir",
        help="Output directory for the scenario-evidence run archive.",
    ),
    run_id: str | None = typer.Option(
        None,
        "--run-id",
        help="Run id for the scenario-evidence archive (safe filesystem label).",
    ),
    native_live: bool = typer.Option(
        False,
        "--native-live",
        help="Realize the libvirt substrate natively (requires a libvirt daemon); default is deterministic.",
    ),
    connection_uri: str = typer.Option(
        "qemu:///system",
        "--connection-uri",
        callback=_noncredential_connection_uri,
        help="libvirt connection URI (native-live only).",
    ),
) -> None:
    """Produce the libvirt evidence-run evaluator-evidence artifact for a scenario."""

    resolved_run_id = run_id or datetime.now(UTC).strftime("aces_libvirt_evidence_%Y%m%dT%H%M%SZ")
    report = run_libvirt_evidence_run(
        scenario_path=scenario.resolve(),
        project_dir=project_dir.resolve(),
        run_id=resolved_run_id,
        config=LibvirtEvidenceRunConfig(
            evidence_source_mode="native-live" if native_live else "deterministic",
            connection_uri=connection_uri,
        ),
    )
    typer.echo(report.render())
    if not report.passed:
        raise typer.Exit(code=1)
