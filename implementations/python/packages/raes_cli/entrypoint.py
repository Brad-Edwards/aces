"""Lightweight installed-console entry point for the RAES CLI."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version

_NOT_INSTALLED_VERSION = "0.0.0+unknown"
_VERSION_ARGUMENTS = frozenset({"--version", "-V"})


def _distribution_version() -> str:
    """Return the governed distribution version or its honest sentinel."""

    try:
        return version("raes")
    except PackageNotFoundError:
        return _NOT_INSTALLED_VERSION


def main() -> None:
    """Handle exact version probes without importing the full command graph."""

    arguments = sys.argv[1:]
    if len(arguments) == 1 and arguments[0] in _VERSION_ARGUMENTS:
        print(f"raes {_distribution_version()}")
        return

    from raes_cli.main import app

    app()
