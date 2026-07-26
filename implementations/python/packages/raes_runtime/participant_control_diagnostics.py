"""Shared participant control-plane diagnostic construction."""

from __future__ import annotations

from raes_contracts.diagnostics import Diagnostic

_NO_PARTICIPANT_RUNTIME_MESSAGE = "Target does not provide a participant runtime."
_PARTICIPANT_BINDING_REJECTED = "runtime.participant-binding.rejected"


def _participant_binding_address(participant_behavior: object) -> str:
    address = getattr(participant_behavior, "address", None)
    return address if isinstance(address, str) and address else "runtime.control-plane.participant-binding"


def _participant_binding_diagnostic(address: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=_PARTICIPANT_BINDING_REJECTED,
        domain="runtime",
        address=address,
        message=message,
    )
