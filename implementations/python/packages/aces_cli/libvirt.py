"""Libvirt backend operational commands."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import typer
from aces_operations.libvirt_paper_evidence import LibvirtPaperEvidenceConfig, run_libvirt_paper_evidence
from aces_operations.techvault_live import TechVaultLiveConfig, validate_techvault_live

app = typer.Typer(help="Libvirt backend operations.")
techvault_app = typer.Typer(help="TechVault operational scenario checks.")
app.add_typer(techvault_app, name="techvault")
paper_app = typer.Typer(help="Paper-proof evaluator-evidence artifacts.")
app.add_typer(paper_app, name="paper")

_LIVE_WARNING = """\
This will create native libvirt/QEMU resources for the selected TechVault
scenario and write a live-gate archive under the output directory.
"""


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
        help="libvirt connection URI.",
    ),
    appliance_memory_mib: int = typer.Option(
        128,
        "--appliance-memory-mib",
        min=64,
        help="Memory per generated TechVault appliance VM.",
    ),
    boot_timeout_seconds: int = typer.Option(
        180,
        "--boot-timeout-seconds",
        min=1,
        help="Maximum native appliance readiness wait.",
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
            appliance_memory_mib=appliance_memory_mib,
            boot_timeout_seconds=boot_timeout_seconds,
        ),
    )
    typer.echo(report.render())
    if not report.passed:
        raise typer.Exit(code=1)


@paper_app.command("validate-evidence")
def validate_evidence(
    scenario: Path = typer.Option(
        Path("examples/scenarios/paper-agent-loop.sdl.yaml"),
        "--scenario",
        help="Paper ACES SDL scenario to produce evaluator evidence for.",
    ),
    project_dir: Path = typer.Option(
        Path("."),
        "--project-dir",
        "--output-dir",
        help="Output directory for the paper-evidence run archive.",
    ),
    run_id: str | None = typer.Option(
        None,
        "--run-id",
        help="Run id for the paper-evidence archive (safe filesystem label).",
    ),
    native_live: bool = typer.Option(
        False,
        "--native-live",
        help="Realize the libvirt substrate natively (requires a libvirt daemon); default is deterministic.",
    ),
    connection_uri: str = typer.Option(
        "qemu:///system",
        "--connection-uri",
        help="libvirt connection URI (native-live only).",
    ),
) -> None:
    """Produce the libvirt paper-proof evaluator-evidence artifact for a scenario."""

    resolved_run_id = run_id or datetime.now(UTC).strftime("aces_libvirt_paper_%Y%m%dT%H%M%SZ")
    report = run_libvirt_paper_evidence(
        scenario_path=scenario.resolve(),
        project_dir=project_dir.resolve(),
        run_id=resolved_run_id,
        config=LibvirtPaperEvidenceConfig(
            evidence_source_mode="native-live" if native_live else "deterministic",
            connection_uri=connection_uri,
        ),
    )
    typer.echo(report.render())
    if not report.passed:
        raise typer.Exit(code=1)
