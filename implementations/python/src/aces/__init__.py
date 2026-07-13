"""Backward-compatible ACES namespace."""

from aces._compat import package_version

# Derived from the installed distribution metadata. The version source of truth
# is `[project] version` in pyproject.toml, bumped by release-please (#684). The
# not-installed fallback is the honest PEP 440 sentinel `0.0.0+unknown`
# (GOV-901): an uninstalled namespace must not imply a real released version.
__version__ = package_version("aces-sdl", default="0.0.0+unknown")

__all__ = ["__version__"]
