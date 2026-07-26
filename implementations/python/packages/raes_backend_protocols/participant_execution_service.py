"""Typed participant execution-service readback."""

from __future__ import annotations

from raes_contracts.contracts.participant_execution import ParticipantExecutionServiceStateModel
from raes_contracts.runtime_state import RuntimeSnapshot


def participant_execution_state(
    execution_scope_ref: str,
    snapshot: RuntimeSnapshot,
) -> ParticipantExecutionServiceStateModel:
    """Read backend-observed state without synthesizing lifecycle success."""

    payload = snapshot.participant_execution_services.get(execution_scope_ref)
    if payload is None:
        raise ValueError("participant execution scope is not configured")
    return ParticipantExecutionServiceStateModel.model_validate(payload)


__all__ = ["participant_execution_state"]
