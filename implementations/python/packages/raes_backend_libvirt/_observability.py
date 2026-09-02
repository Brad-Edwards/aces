"""Backend-local observability for suppressed backend failures.

The portable driver boundary deliberately collapses native errors into
value-free diagnostics. This module records bounded, non-sensitive failure
classification on the operator's side of that boundary without retaining
exception messages or tracebacks. It is silent unless the embedding application
configures logging for ``raes_backend_libvirt``.
"""

from __future__ import annotations

import logging
import re

LOGGER = logging.getLogger("raes_backend_libvirt")
_SAFE_TYPE_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def record_suppressed_failure(
    operation: str,
    exc: BaseException,
    *,
    native_code: int | None = None,
) -> None:
    """Record bounded failure classification without exception text or traceback."""

    exception_type = _SAFE_TYPE_RE.sub("-", type(exc).__name__)[:80] or "Exception"
    fields = [f"exception_type={exception_type}"]
    if isinstance(exc, OSError) and type(exc.errno) is int:
        fields.append(f"errno={exc.errno}")
    if type(native_code) is int:
        fields.append(f"native_code={native_code}")
    LOGGER.debug("%s suppressed backend failure (%s)", operation, ", ".join(fields))
