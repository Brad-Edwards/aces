"""Cross-backend evidence corpus commands (issue #600)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import typer
from aces_operations.cross_backend_corpus import (
    CrossBackendCorpusConfig,
    build_cross_backend_corpus,
    write_cross_backend_corpus_artifact,
)

app = typer.Typer(help="Cross-backend evidence corpus (invariant ledger).")

_DEFAULT_SCENARIO = Path("examples/scenarios/enterprise-participant-evidence-loop.sdl.yaml")
# The canonical published corpus lives in Brad-Edwards/research, not in this repo, so
# the default output is a working-directory file to be published from there.
_DEFAULT_OUTPUT = Path("cross-backend-evidence-corpus.json")


@app.command("build")
def build(
    scenario: Path = typer.Option(
        _DEFAULT_SCENARIO,
        "--scenario",
        help="Authored reference RAES SDL scenario realized by both backends.",
    ),
    output: Path = typer.Option(
        _DEFAULT_OUTPUT,
        "--output",
        help="Path to write the corpus artifact.",
    ),
    aptl_evidence: Path | None = typer.Option(
        None,
        "--aptl-evidence",
        help="Optional operator-supplied APTL evidence export; its allowlisted portable fields replace the "
        "documented-shape summary. No APTL-private data is imported.",
    ),
    work_dir: Path | None = typer.Option(
        None,
        "--work-dir",
        help="Working directory for the intermediate libvirt run archive (default: a temp directory).",
    ),
) -> None:
    """Build the cross-backend evidence corpus and write it to ``--output``."""
    project_dir = work_dir or Path(tempfile.mkdtemp(prefix="aces-cross-backend-corpus-"))
    report = build_cross_backend_corpus(
        scenario_path=scenario.resolve(),
        project_dir=project_dir.resolve(),
        config=CrossBackendCorpusConfig(aptl_evidence_path=aptl_evidence.resolve() if aptl_evidence else None),
    )
    if report.artifact is not None:
        written = write_cross_backend_corpus_artifact(report.artifact, output.resolve())
        typer.echo(f"wrote corpus: {written}")
    typer.echo(report.render())
    if not report.passed:
        raise typer.Exit(code=1)
