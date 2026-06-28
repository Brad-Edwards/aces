"""Participant runtime control-plane operations."""

from __future__ import annotations

from aces_contracts.contracts import (
    ParticipantActionResultModel,
    ParticipantImplementationManifestModel,
    ParticipantImplementationSelectionModel,
)
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
    implementation_manifest: ParticipantImplementationManifestModel,
    implementation_selection: ParticipantImplementationSelectionModel,
    action_contract_address: str,
    observation_boundary_address: str,
) -> list[Diagnostic]:
    address = _participant_binding_address(participant_behavior)
    diagnostics: list[Diagnostic] = []
    if not isinstance(participant_behavior, ParticipantBehaviorRuntime):
        return [
            _participant_binding_diagnostic(
                address,
                "participant_behavior must be a compiled ParticipantBehaviorRuntime",
            )
        ]
    if action_contract_address not in participant_behavior.action_contract_addresses:
        diagnostics.append(
            _participant_binding_diagnostic(
                address,
                (
                    f"action_contract_address {action_contract_address!r} is not declared by compiled "
                    f"participant behavior {participant_behavior.address!r}"
                ),
            )
        )
    if observation_boundary_address not in participant_behavior.observation_boundary_addresses:
        diagnostics.append(
            _participant_binding_diagnostic(
                address,
                (
                    f"observation_boundary_address {observation_boundary_address!r} is not declared by compiled "
                    f"participant behavior {participant_behavior.address!r}"
                ),
            )
        )
    if not isinstance(implementation_manifest, ParticipantImplementationManifestModel):
        diagnostics.append(
            _participant_binding_diagnostic(
                address,
                "implementation_manifest must be a ParticipantImplementationManifestModel",
            )
        )
    if not isinstance(implementation_selection, ParticipantImplementationSelectionModel):
        diagnostics.append(
            _participant_binding_diagnostic(
                address,
                "implementation_selection must be a ParticipantImplementationSelectionModel",
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
        *,
        implementation_manifest: ParticipantImplementationManifestModel,
        implementation_selection: ParticipantImplementationSelectionModel,
        action_contract_address: str,
        observation_boundary_address: str,
        action_instance_id: str,
        observation_boundary_evidence_refs: tuple[str, ...] = (),
        evidence_refs: tuple[str, ...] = (),
        visible_refs: tuple[str, ...] = (),
        disclosed_refs: tuple[str, ...] = (),
        action_result: ParticipantActionResultModel | None = None,
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
        diagnostics = _participant_binding_diagnostics(
            participant_behavior,
            implementation_manifest=implementation_manifest,
            implementation_selection=implementation_selection,
            action_contract_address=action_contract_address,
            observation_boundary_address=observation_boundary_address,
        )
        if diagnostics:
            return self._reject_diagnostics(
                domain=RuntimeDomain.PARTICIPANT,
                diagnostics=diagnostics,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        try:
            request = ParticipantActionAdmissionRequest(
                participant_address=participant_behavior.address,
                action_contract_address=action_contract_address,
                observation_boundary_address=observation_boundary_address,
                action_instance_id=action_instance_id,
                implementation_manifest=implementation_manifest,
                implementation_selection=implementation_selection,
                evidence_refs=evidence_refs,
                visible_refs=visible_refs,
                disclosed_refs=disclosed_refs,
                observation_boundary_evidence_refs=observation_boundary_evidence_refs,
                action_result=action_result,
            )
        except (TypeError, ValueError) as exc:
            return self._reject_diagnostics(
                domain=RuntimeDomain.PARTICIPANT,
                diagnostics=[
                    _participant_binding_diagnostic(
                        _participant_binding_address(participant_behavior),
                        str(exc),
                    )
                ],
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
        return execute_participant_action(
            self,
            method=self._target.participant_runtime.admit_action,
            request=request,
            address=f"runtime.control-plane.participant.{participant_behavior.address}.admit-action",
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )
