"""Backward-compatible ACES namespace."""

# Single source of truth for the version (#684). tools/release.py bumps this from
# the pending towncrier changelog fragments; hatchling reads it via the
# [tool.hatch.version] `path` source. Do not hand-edit outside a release.
__version__ = "0.17.0"

__all__ = ["__version__"]
