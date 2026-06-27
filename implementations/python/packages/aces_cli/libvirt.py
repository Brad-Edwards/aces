"""Libvirt backend operational commands."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import typer
from aces_operations.techvault_live import validate_techvault_live

app = typer.Typer(help="Libvirt backend operations.")
techvault_app = typer.Typer(help="TechVault operational scenario checks.")
app.add_typer(techvault_app, name="techvault")

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
    skip_clean_boot: bool = typer.Option(
        False,
        "--skip-clean-boot",
        help="Record the run as non-clean without changing the native archive layout.",
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

    if not skip_clean_boot and not yes:
        typer.echo(_LIVE_WARNING)
        if not typer.confirm("Continue?", default=False):
            typer.echo("Aborted.")
            raise typer.Exit(code=0)
    resolved_run_id = run_id or datetime.now(UTC).strftime("aces_libvirt_techvault_%Y%m%dT%H%M%SZ")
    report = validate_techvault_live(
        scenario_path=scenario.resolve(),
        project_dir=project_dir.resolve(),
        run_id=resolved_run_id,
        clean_boot=not skip_clean_boot,
        connection_uri=connection_uri,
        appliance_memory_mib=appliance_memory_mib,
        boot_timeout_seconds=boot_timeout_seconds,
    )
    typer.echo(report.render())
    if not report.passed:
        raise typer.Exit(code=1)
