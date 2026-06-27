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
This will stop the target TechVault lab and remove Compose-managed volumes
before booting it again through the ACES/libvirt provisioning path.
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
        help="TechVault/APTL project directory that owns docker-compose.yml.",
    ),
    run_id: str | None = typer.Option(
        None,
        "--run-id",
        help="Run id for the live-gate archive.",
    ),
    skip_clean_boot: bool = typer.Option(
        False,
        "--skip-clean-boot",
        help="Validate/start without the destructive stop -v cleanup.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the destructive-clean-boot confirmation prompt.",
    ),
) -> None:
    """Boot TechVault through ACES/libvirt and run the live validation gate."""

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
    )
    typer.echo(report.render())
    if not report.passed:
        raise typer.Exit(code=1)
