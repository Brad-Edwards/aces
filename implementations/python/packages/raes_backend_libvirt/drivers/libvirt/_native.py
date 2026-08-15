"""Native libvirt adapter helpers for the libvirt/QEMU deployment driver.

Low-level libvirt-facing seams shared by the deployment driver and the TechVault
native modules: stable error-code classification, deterministic per-address and
nwfilter-owner UUIDs, ownership readback, and the lookup/stop primitives that
keep the define/convergence path (:func:`_lookup`) distinct from the fail-closed
teardown path (:func:`_find_native`).
"""

from __future__ import annotations

import importlib
import re
import uuid
from collections.abc import Callable
from typing import Protocol, cast

from raes_backend_libvirt._observability import LOGGER as _LOGGER
from raes_backend_libvirt._observability import NATIVE_FAILURE_LOG as _NATIVE_FAILURE_LOG

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
# Fixed namespace for deriving a per-address libvirt UUID. The UUID proves an
# existing host object was realized by RAES for *this* address, so convergence
# never destroys a foreign or another-address object that merely shares a name.
_RAES_UUID_NAMESPACE = uuid.UUID("af20aedd-47bd-5870-b3f8-2f1baebde508")

# libvirt signals a missing object with a stable VIR_ERR_NO_* code (part of its
# public C ABI) on ``libvirtError.get_error_code()``. Idempotent teardown treats
# only these as "already absent"; every other libvirtError — connection loss,
# permission denial, an ambiguous or internal lookup failure — stays a fail-closed
# diagnostic that preserves the snapshot for retry (issue #604 guardrail:
# "do not treat every libvirt lookup exception as not found").
_VIR_ERR_NO_DOMAIN = 42
_VIR_ERR_NO_NETWORK = 43
# Raised by destroy() on an object that is not running; stopping an already-stopped
# object is a benign no-op on the teardown path, distinct from a permission/internal
# stop failure that must fail closed.
_VIR_ERR_OPERATION_INVALID = 55
_ABSENCE_ERROR_CODES: frozenset[int] = frozenset({_VIR_ERR_NO_DOMAIN, _VIR_ERR_NO_NETWORK})


class _OwnershipConflict(Exception):
    """An existing host object at this name is not the RAES object for this address."""


class _NativeLookupError(Exception):
    """A libvirt lookup failed for a reason other than the object being absent."""


def _error_code(exc: BaseException) -> int | None:
    """Return a libvirtError's ``get_error_code()`` as an int, or None otherwise.

    A non-libvirt exception (no ``get_error_code``), or one whose code is not an
    int, yields None so callers treat it as an unclassified real failure.
    """

    getter = getattr(exc, "get_error_code", None)
    if not callable(getter):
        return None
    try:
        code = getter()
    except Exception as exc:
        _LOGGER.debug(_NATIVE_FAILURE_LOG, "_error_code", exc_info=exc)
        return None
    return code if isinstance(code, int) else None


def _is_absence_error(exc: BaseException) -> bool:
    """Return True when ``exc`` is a libvirt "no such object" error.

    Absence is an idempotent teardown success. A non-libvirt exception, or a
    libvirtError with any other code, is a real failure and returns False.
    """

    return _error_code(exc) in _ABSENCE_ERROR_CODES


def _raes_uuid(address: str) -> str:
    return str(uuid.uuid5(_RAES_UUID_NAMESPACE, address))


def _filter_owner_uuid(address: str) -> str:
    """Owner UUID for a domain's nwfilter (namespaced so it never equals the domain UUID)."""

    return str(uuid.uuid5(_RAES_UUID_NAMESPACE, f"nwfilter:{address}"))


class _NativeResource(Protocol):
    def create(self) -> None: ...

    def destroy(self) -> None: ...

    def undefine(self) -> None: ...


def _existing_uuid(native: object) -> str | None:
    """Return an existing object's UUID string, or None when it cannot be read.

    A missing/unreadable UUID is treated as "not ours" by the caller, so an
    object we cannot prove ownership of is never destroyed.
    """

    reader = getattr(native, "UUIDString", None)
    if reader is None:
        return None
    try:
        return reader()
    except Exception as exc:
        _LOGGER.debug(_NATIVE_FAILURE_LOG, "_existing_uuid", exc_info=exc)
        return None


class _LibvirtModule(Protocol):
    def open(self, connection_uri: str) -> object | None: ...


Connector = Callable[[str], object | None]


def _default_connector(connection_uri: str) -> object | None:
    libvirt = cast(_LibvirtModule, importlib.import_module("libvirt"))
    return libvirt.open(connection_uri)


def _call_libvirt(connection: object, method_name: str, payload: str) -> _NativeResource:
    method = cast(Callable[[str], _NativeResource], getattr(connection, method_name))
    return method(payload)


def _lookup(connection: object, method_name: str, name: str) -> object | None:
    """Return an existing native resource by name, or None when absent.

    Any lookup failure (not-found or otherwise) returns None so the caller
    attempts a define; a genuine define-time conflict is then surfaced as a
    redacted diagnostic rather than a duplicate resource.
    """

    method = getattr(connection, method_name, None)
    if method is None:
        return None
    try:
        return method(name)
    except Exception as exc:
        _LOGGER.debug(_NATIVE_FAILURE_LOG, "_lookup", exc_info=exc)
        return None


def _stop_native(native: object) -> None:
    """Stop a running native object before it is undefined.

    Stopping an object that is already inactive is a benign no-op (libvirt raises
    ``VIR_ERR_OPERATION_INVALID``), and one that has already vanished is absent;
    either lets teardown proceed to ``undefine()``. Any other stop failure —
    permission, internal — propagates so teardown fails closed instead of
    undefining (and dropping the snapshot entry for) a still-running resource
    (issue #604: permission and unconfirmed teardown failures must fail closed).
    """

    try:
        cast(_NativeResource, native).destroy()
    except Exception as exc:
        code = _error_code(exc)
        if code == _VIR_ERR_OPERATION_INVALID or code in _ABSENCE_ERROR_CODES:
            return
        raise


def _find_native(connection: object, method_name: str, name: str) -> object | None:
    """Return an existing native resource by name, or None when genuinely absent.

    Unlike :func:`_lookup`, this distinguishes idempotent absence from a real
    lookup failure: a libvirt "no such object" error maps to None, while a
    connection/permission/internal lookup failure is raised as
    :class:`_NativeLookupError` so teardown fails closed and preserves the snapshot for
    retry rather than falsely reporting the object gone (issue #604).
    """

    method = getattr(connection, method_name, None)
    if method is None:
        return None
    try:
        return method(name)
    except Exception as exc:
        if _is_absence_error(exc):
            return None
        raise _NativeLookupError(method_name) from exc


def _safe_name(candidate: str, *, fallback: str, prefix: str) -> str:
    raw = candidate.strip() or fallback.strip() or "resource"
    normalized = _SAFE_NAME_RE.sub("-", raw).strip("-._")
    if not normalized:
        normalized = _SAFE_NAME_RE.sub("-", fallback).strip("-._") or "resource"
    prefixed = f"{prefix}-{normalized}" if prefix else normalized
    return prefixed[:63].strip("-._") or "resource"
