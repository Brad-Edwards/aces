"""Portable diagnostic construction for the generic libvirt driver."""

from __future__ import annotations

from raes_contracts.diagnostics import Diagnostic, Severity

_DOMAIN = "runtime"
_CODE_OPERATION_FAILED = "libvirt-backend.driver.operation-failed"
_CODE_UNAVAILABLE = "libvirt-backend.driver.unavailable"
_CODE_OWNERSHIP_CONFLICT = "libvirt-backend.driver.ownership-conflict"
_CONNECTION_ADDRESS = "runtime.libvirt.connection"

_FAILURE_MESSAGES = {
    _CODE_UNAVAILABLE: "Libvirt connection is unavailable for this backend operation.",
    _CODE_OWNERSHIP_CONFLICT: (
        "Libvirt object for '{address}' already exists under the same name but is not "
        "owned by this RAES address; refusing to converge an object this plan does not own."
    ),
}


def _failure(address: str, code: str) -> Diagnostic:
    template = _FAILURE_MESSAGES.get(code, "Libvirt operation for '{address}' did not succeed.")
    return Diagnostic(
        code=code,
        domain=_DOMAIN,
        address=address,
        message=template.format(address=address),
        severity=Severity.ERROR,
    )


__all__ = [
    "_CODE_OPERATION_FAILED",
    "_CODE_OWNERSHIP_CONFLICT",
    "_CODE_UNAVAILABLE",
    "_CONNECTION_ADDRESS",
    "_failure",
]
