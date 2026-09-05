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
_SAFE_TOKEN_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_MAX_TOKEN_LENGTH = 80
_MIN_SAFE_INTEGER = -(2**31)
_MAX_SAFE_INTEGER = 2**31 - 1


def _safe_token(value: object, *, fallback: str) -> str:
    candidate = value if type(value) is str else fallback
    return _SAFE_TOKEN_RE.sub("-", candidate)[:_MAX_TOKEN_LENGTH] or fallback


def _bounded_integer(value: object) -> int | None:
    if type(value) is not int or not _MIN_SAFE_INTEGER <= value <= _MAX_SAFE_INTEGER:
        return None
    return value


def record_suppressed_failure(
    operation: str,
    exc: BaseException,
    *,
    native_code: int | None = None,
) -> None:
    """Record bounded failure classification without exception text or traceback."""

    operation_token = _safe_token(operation, fallback="operation")
    exception_type = _safe_token(type(exc).__name__, fallback="Exception")
    fields = [f"exception_type={exception_type}"]
    error_number = None
    if isinstance(exc, OSError):
        try:
            error_number = _bounded_integer(exc.errno)
        except Exception:
            error_number = None
    if error_number is not None:
        fields.append(f"errno={error_number}")
    bounded_native_code = _bounded_integer(native_code)
    if bounded_native_code is not None:
        fields.append(f"native_code={bounded_native_code}")
    try:
        LOGGER.debug("%s suppressed backend failure (%s)", operation_token, ", ".join(fields))
    except Exception:
        # Operator telemetry must never replace the portable backend outcome.
        return
