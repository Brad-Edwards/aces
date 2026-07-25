"""Backward-compatible SDL namespace."""

from aces._compat import reexport as _reexport

_reexport(globals(), "raes")

del _reexport
