"""Main entry point for the RAES CLI."""

from importlib.metadata import PackageNotFoundError, version

import typer

from aces_cli import conformance, corpus, libvirt, processor, sdl

app = typer.Typer(
    name="raes",
    help="RAES SDL and runtime CLI",
    no_args_is_help=True,
)

app.add_typer(sdl.app, name="sdl")
app.add_typer(processor.app, name="processor")
app.add_typer(conformance.app, name="conformance")
app.add_typer(libvirt.app, name="libvirt")
app.add_typer(corpus.app, name="corpus")


def _version_callback(value: bool) -> None:
    if value:
        try:
            current_version = version("raes")
        except PackageNotFoundError:
            # Honest PEP 440 not-installed sentinel (GOV-901): do not report a
            # plausible-looking release when the distribution is absent.
            current_version = "0.0.0+unknown"
        typer.echo(f"raes {current_version}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """RAES SDL and runtime CLI."""
