"""Ownership-safe native resource lookup and removal for TechVault."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from raes_backend_libvirt._observability import LOGGER as _LOGGER
from raes_backend_libvirt._observability import NATIVE_FAILURE_LOG as _NATIVE_FAILURE_LOG

from .drivers.libvirt import _error_code, _existing_uuid, _raes_uuid
from .techvault_matrix import runtime_name


class NativeOwnershipConflict(Exception):
    """A native name is not owned by the requested RAES address."""


@dataclass(frozen=True)
class NativeResolution:
    native: object | None
    name: str | None


def resolve_native(
    connection: object,
    lookup_method: str,
    list_method: str,
    address: str,
    *,
    known_name: str | None,
    name_prefix: str,
) -> NativeResolution | None:
    lookup = getattr(connection, lookup_method, None)
    if not callable(lookup):
        return None
    if known_name is None:
        return _resolve_by_uuid(connection, list_method, address, name_prefix)
    return _resolve_by_name(connection, lookup, list_method, address, known_name)


def _resolve_by_uuid(
    connection: object,
    list_method: str,
    address: str,
    name_prefix: str,
) -> NativeResolution | None:
    native_items = _list_native(connection, list_method)
    resolved: NativeResolution | None = None
    if native_items is not None:
        owned = [item for item in native_items if _existing_uuid(item) == _raes_uuid(address)]
        if not owned:
            fallback_name = runtime_name(name_prefix, address)
            if any(_native_name(item) == fallback_name for item in native_items):
                raise NativeOwnershipConflict(address)
            resolved = NativeResolution(native=None, name=None)
        elif len(owned) == 1:
            name = _native_name(owned[0])
            if name:
                resolved = NativeResolution(native=owned[0], name=name)
    return resolved


def _resolve_by_name(
    connection: object,
    lookup: Callable[[str], object],
    list_method: str,
    address: str,
    name: str,
) -> NativeResolution | None:
    resolved: NativeResolution | None = None
    try:
        native = lookup(name)
    except KeyError:
        resolved = _resolve_verified_absence(connection, list_method, address)
    except Exception as exc:
        if _error_code(exc) in {42, 43}:
            resolved = _resolve_verified_absence(connection, list_method, address)
    else:
        resolved = NativeResolution(native=native, name=name)
    return resolved


def _resolve_verified_absence(
    connection: object,
    list_method: str,
    address: str,
) -> NativeResolution | None:
    native_items = _list_native(connection, list_method)
    if native_items is None or any(_existing_uuid(item) == _raes_uuid(address) for item in native_items):
        return None
    return NativeResolution(native=None, name=None)


def verify_native_removed(
    connection: object,
    list_method: str,
    address: str,
    name: str | None,
) -> bool:
    native_items = _list_native(connection, list_method)
    return native_items is not None and not any(
        _native_name(item) == name or _existing_uuid(item) == _raes_uuid(address) for item in native_items
    )


def deactivate_and_undefine(native: object) -> bool:
    return _invoke_native_action(native, "destroy", {42, 43, 55}) and _invoke_native_action(
        native,
        "undefine",
        {42, 43},
    )


def _invoke_native_action(native: object, method_name: str, tolerated_codes: set[int]) -> bool:
    method = getattr(native, method_name, None)
    if not callable(method):
        return False
    try:
        method()
    except Exception as exc:
        return _error_code(exc) in tolerated_codes
    return True


def _list_native(connection: object, method_name: str) -> tuple[object, ...] | None:
    method = getattr(connection, method_name, None)
    if not callable(method):
        return None
    try:
        native = method()
    except Exception as exc:
        _LOGGER.debug(_NATIVE_FAILURE_LOG, "_list_native", exc_info=exc)
        return None
    return tuple(native) if isinstance(native, list | tuple) else None


def _native_name(native: object) -> str:
    method = getattr(native, "name", None)
    if not callable(method):
        return ""
    try:
        value = method()
    except Exception as exc:
        _LOGGER.debug(_NATIVE_FAILURE_LOG, "_native_name", exc_info=exc)
        return ""
    return value if isinstance(value, str) else ""


__all__ = [
    "NativeOwnershipConflict",
    "NativeResolution",
    "deactivate_and_undefine",
    "resolve_native",
    "verify_native_removed",
]
