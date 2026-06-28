"""Participant runtime control-plane operations."""

from __future__ import annotations

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.participant_binding import ParticipantActionAdmissionRequest
from aces_contracts.participant_episode import (
    ParticipantEpisodeInitializeRequest,
    ParticipantEpisodeResetRequest,
    ParticipantEpisodeRestartRequest,
    ParticipantEpisodeTerminalReason,
    ParticipantEpisodeTerminateRequest,
)
from aces_contracts.planning import RuntimeDomain
from aces_contracts.runtime_state import OperationReceipt
from aces_processor.models import ParticipantBehaviorRuntime

from .control_plane_execution import execute_participant_action

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


def _participant_binding_diagnostics(
    participant_behavior: object,
    *,
    admission_request: object,
    admission_fields: dict[str, object],
) -> tuple[ParticipantActionAdmissionRequest | None, list[Diagnostic]]:
    address = _participant_binding_address(participant_behavior)
    if not isinstance(participant_behavior, ParticipantBehaviorRuntime):
        return None, [
            _participant_binding_diagnostic(
                address,
                "participant_behavior must be a compiled ParticipantBehaviorRuntime",
            )
        ]
    request, diagnostics = _participant_admission_request(
        participant_behavior,
        admission_request=admission_request,
        admission_fields=admission_fields,
    )
    if diagnostics:
        return None, diagnostics
    diagnostics.extend(_participant_binding_request_diagnostics(participant_behavior, request))
    return (request if not diagnostics else None), diagnostics


def _participant_admission_request(
    participant_behavior: ParticipantBehaviorRuntime,
    *,
    admission_request: object,
    admission_fields: dict[str, object],
) -> tuple[ParticipantActionAdmissionRequest | None, list[Diagnostic]]:
    address = _participant_binding_address(participant_behavior)
    if admission_request is not None:
        return _explicit_participant_admission_request(address, admission_request, admission_fields)
    field_diagnostics = _participant_binding_field_diagnostics(participant_behavior, admission_fields)
    if field_diagnostics:
        return None, field_diagnostics
    return _participant_admission_request_from_fields(participant_behavior, admission_fields)


def _explicit_participant_admission_request(
    address: str,
    admission_request: object,
    admission_fields: dict[str, object],
) -> tuple[ParticipantActionAdmissionRequest | None, list[Diagnostic]]:
    if admission_fields:
        return None, [
            _participant_binding_diagnostic(
                address,
                "admission_request cannot be combined with admission keyword fields",
            )
        ]
    return _validated_participant_admission_request(address, admission_request)


def _participant_admission_request_from_fields(
    participant_behavior: ParticipantBehaviorRuntime,
    admission_fields: dict[str, object],
) -> tuple[ParticipantActionAdmissionRequest | None, list[Diagnostic]]:
    address = _participant_binding_address(participant_behavior)
    try:
        return (
            ParticipantActionAdmissionRequest(
                participant_address=participant_behavior.address,
                **admission_fields,
            ),
            [],
        )
    except (TypeError, ValueError) as exc:
        return None, [_participant_binding_diagnostic(address, str(exc))]


def _validated_participant_admission_request(
    address: str,
    admission_request: object,
) -> tuple[ParticipantActionAdmissionRequest | None, list[Diagnostic]]:
    if isinstance(admission_request, ParticipantActionAdmissionRequest):
        return admission_request, []
    return None, [
        _participant_binding_diagnostic(
            address,
            "admission_request must be a ParticipantActionAdmissionRequest",
        )
    ]


def _participant_binding_field_diagnostics(
    participant_behavior: ParticipantBehaviorRuntime,
    admission_fields: dict[str, object],
) -> list[Diagnostic]:
    address = _participant_binding_address(participant_behavior)
    diagnostics: list[Diagnostic] = []
    action_contract_address = admission_fields.get("action_contract_address")
    if (
        isinstance(action_contract_address, str)
        and action_contract_address not in participant_behavior.action_contract_addresses
    ):
        diagnostics.append(
            _participant_binding_diagnostic(
                address,
                (
                    f"action_contract_address {action_contract_address!r} is not declared by compiled "
                    f"participant behavior {participant_behavior.address!r}"
                ),
            )
        )
    observation_boundary_address = admission_fields.get("observation_boundary_address")
    if (
        isinstance(observation_boundary_address, str)
        and observation_boundary_address not in participant_behavior.observation_boundary_addresses
    ):
        diagnostics.append(
            _participant_binding_diagnostic(
                address,
                (
                    f"observation_boundary_address {observation_boundary_address!r} is not declared by compiled "
                    f"participant behavior {participant_behavior.address!r}"
                ),
            )
        )
    return diagnostics


def _participant_binding_request_diagnostics(
    participant_behavior: ParticipantBehaviorRuntime,
    request: ParticipantActionAdmissionRequest | None,
) -> list[Diagnostic]:
    if request is None:
        return []
    address = _participant_binding_address(participant_behavior)
    diagnostics: list[Diagnostic] = []
    if request.participant_address != participant_behavior.address:
        diagnostics.append(
            _participant_binding_diagnostic(
                address,
                "admission_request participant_address must match the compiled participant behavior address",
            )
        )
    if request.action_contract_address not in participant_behavior.action_contract_addresses:
        diagnostics.append(
            _participant_binding_diagnostic(
                address,
                (
                    f"action_contract_address {request.action_contract_address!r} is not declared by compiled "
                    f"participant behavior {participant_behavior.address!r}"
                ),
            )
        )
    if request.observation_boundary_address not in participant_behavior.observation_boundary_addresses:
        diagnostics.append(
            _participant_binding_diagnostic(
                address,
                (
                    f"observation_boundary_address {request.observation_boundary_address!r} "
                    "is not declared by compiled "
                    f"participant behavior {participant_behavior.address!r}"
                ),
            )
        )
    return diagnostics


class ParticipantControlMixin:
    """Participant runtime methods for the shared runtime control plane."""

    def initialize_participant_episode(
        self,
        participant_address: str,
        *,
        episode_id: str | None = None,
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        if self._target.participant_runtime is None:
            return self._reject_submission(
                domain=RuntimeDomain.PARTICIPANT,
                message=_NO_PARTICIPANT_RUNTIME_MESSAGE,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        request = ParticipantEpisodeInitializeRequest(
            participant_address=participant_address,
            episode_id=episode_id,
        )
        return execute_participant_action(
            self,
            method=self._target.participant_runtime.initialize,
            request=request,
            address=f"runtime.control-plane.participant.{participant_address}.initialize",
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )

    def reset_participant_episode(
        self,
        participant_address: str,
        *,
        episode_id: str | None = None,
        reason: str = "reset by operator",
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        if self._target.participant_runtime is None:
            return self._reject_submission(
                domain=RuntimeDomain.PARTICIPANT,
                message=_NO_PARTICIPANT_RUNTIME_MESSAGE,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        request = ParticipantEpisodeResetRequest(
            participant_address=participant_address,
            episode_id=episode_id,
            reason=reason,
        )
        return execute_participant_action(
            self,
            method=self._target.participant_runtime.reset,
            request=request,
            address=f"runtime.control-plane.participant.{participant_address}.reset",
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )

    def restart_participant_episode(
        self,
        participant_address: str,
        *,
        episode_id: str | None = None,
        reason: str = "restarted by operator",
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        if self._target.participant_runtime is None:
            return self._reject_submission(
                domain=RuntimeDomain.PARTICIPANT,
                message=_NO_PARTICIPANT_RUNTIME_MESSAGE,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        request = ParticipantEpisodeRestartRequest(
            participant_address=participant_address,
            episode_id=episode_id,
            reason=reason,
        )
        return execute_participant_action(
            self,
            method=self._target.participant_runtime.restart,
            request=request,
            address=f"runtime.control-plane.participant.{participant_address}.restart",
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )

    def terminate_participant_episode(
        self,
        participant_address: str,
        *,
        terminal_reason: ParticipantEpisodeTerminalReason = ParticipantEpisodeTerminalReason.INTERRUPTED,
        detail: str = "terminated by operator",
        idempotency_key: str = "",
        request_fingerprint: str = "",
    ) -> OperationReceipt:
        if self._target.participant_runtime is None:
            return self._reject_submission(
                domain=RuntimeDomain.PARTICIPANT,
                message=_NO_PARTICIPANT_RUNTIME_MESSAGE,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        request = ParticipantEpisodeTerminateRequest(
            participant_address=participant_address,
            terminal_reason=terminal_reason,
            detail=detail,
        )
        return execute_participant_action(
            self,
            method=self._target.participant_runtime.terminate,
            request=request,
            address=f"runtime.control-plane.participant.{participant_address}.terminate",
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )

    def admit_participant_action(
        self,
        participant_behavior: ParticipantBehaviorRuntime,
        admission_request: ParticipantActionAdmissionRequest | None = None,
        *,
        idempotency_key: str = "",
        request_fingerprint: str = "",
        **admission_fields: object,
    ) -> OperationReceipt:
        if self._target.participant_runtime is None:
            return self._reject_submission(
                domain=RuntimeDomain.PARTICIPANT,
                message=_NO_PARTICIPANT_RUNTIME_MESSAGE,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        request, diagnostics = _participant_binding_diagnostics(
            participant_behavior,
            admission_request=admission_request,
            admission_fields=admission_fields,
        )
        if diagnostics:
            return self._reject_diagnostics(
                domain=RuntimeDomain.PARTICIPANT,
                diagnostics=diagnostics,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        assert request is not None
        return execute_participant_action(
            self,
            method=self._target.participant_runtime.admit_action,
            request=request,
            address=f"runtime.control-plane.participant.{request.participant_address}.admit-action",
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )
