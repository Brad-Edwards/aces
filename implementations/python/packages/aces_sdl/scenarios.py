"""Scenario loading helpers and shared exceptions for SDL specifications."""

from __future__ import annotations

import logging
from pathlib import Path

from ._errors import SDLParseError, SDLValidationError
from ._source_profile import SDLMigrationPolicy
from .parser import parse_sdl_file
from .scenario import Scenario

log = logging.getLogger("aces.scenarios")


class ScenarioError(Exception):
    """Base exception for all scenario operations."""


class ScenarioNotFoundError(ScenarioError):
    """A scenario file or ID could not be found."""

    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f"Scenario not found: {identifier}")


class ScenarioValidationError(ScenarioError):
    """A scenario definition failed validation."""

    def __init__(self, message: str, path: Path | None = None) -> None:
        self.path = path
        self.details = message
        prefix = f"{path}: " if path else ""
        super().__init__(f"{prefix}{message}")


class ScenarioStateError(ScenarioError):
    """An invalid state transition was attempted."""


def load_scenario(
    path: Path,
    *,
    migration_policy: SDLMigrationPolicy | str = SDLMigrationPolicy.REJECT,
) -> Scenario:
    """Load and validate a scenario from a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")

    try:
        scenario = parse_sdl_file(path, migration_policy=migration_policy)
    except SDLParseError as exc:
        raise ScenarioValidationError(str(exc), path=path) from exc
    except SDLValidationError as exc:
        raise ScenarioValidationError(str(exc), path=path) from exc

    for advisory in scenario.advisories:
        log.warning("Scenario '%s' advisory: %s", scenario.name, advisory)
    for diagnostic in scenario.source_diagnostics:
        start = diagnostic.primary_range.start
        log.warning(
            "Scenario '%s' source advisory [%s] at %s:%d:%d (%s)",
            scenario.name,
            diagnostic.code,
            diagnostic.source or path,
            start.line,
            start.column,
            diagnostic.pointer or "/",
        )

    log.info("Loaded scenario '%s' from %s", scenario.name, path)
    return scenario


def find_scenarios(search_dir: Path) -> list[Path]:
    """Find all YAML scenario files in a directory (non-recursive)."""
    if not search_dir.is_dir():
        log.debug("Scenarios directory does not exist: %s", search_dir)
        return []

    paths = sorted(search_dir.glob("*.yaml"))
    log.debug("Found %d scenario files in %s", len(paths), search_dir)
    return paths
