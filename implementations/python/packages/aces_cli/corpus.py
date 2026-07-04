"""Paper demonstration corpus commands (issue #600)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import typer
from aces_operations.paper_corpus import (
    PaperCorpusConfig,
    build_paper_demonstration_corpus,
    write_paper_corpus_artifact,
)

app = typer.Typer(help="Paper demonstration corpus (cross-backend invariant ledger).")

_DEFAULT_SCENARIO = Path("examples/scenarios/paper-agent-loop.sdl.yaml")
_DEFAULT_OUTPUT = Path("examples/corpus/paper-demonstration/paper-demonstration-corpus.json")


@app.command("build")
def build(
    scenario: Path = typer.Option(
        _DEFAULT_SCENARIO,
        "--scenario",
        help="Authored paper ACES SDL scenario realized by both backends.",
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
    """Build the cross-backend paper demonstration corpus and write it to ``--output``."""
    project_dir = work_dir or Path(tempfile.mkdtemp(prefix="aces-paper-corpus-"))
    report = build_paper_demonstration_corpus(
        scenario_path=scenario.resolve(),
        project_dir=project_dir.resolve(),
        config=PaperCorpusConfig(aptl_evidence_path=aptl_evidence.resolve() if aptl_evidence else None),
    )
    if report.artifact is not None:
        written = write_paper_corpus_artifact(report.artifact, output.resolve())
        typer.echo(f"wrote corpus: {written}")
    typer.echo(report.render())
    if not report.passed:
        raise typer.Exit(code=1)
