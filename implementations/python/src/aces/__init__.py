"""Backward-compatible ACES namespace."""

from aces._compat import package_version

# Derived from the installed distribution metadata. The version source of truth
# is `[project] version` in pyproject.toml, bumped by release-please (#684).
__version__ = package_version("aces-sdl", default="0.1.0")

__all__ = ["__version__"]
