"""Semantic-diagnostic dispatch and fixture-case gating."""

from __future__ import annotations

from collections.abc import Callable

from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.evaluation import EvaluationExecutionState
from aces_contracts.participant_episode import (
    ParticipantEpisodeExecutionState,
    ParticipantEpisodeHistoryEvent,
)
from aces_contracts.workflow import WorkflowExecutionState
from aces_processor.models import ParticipantBehaviorHistoryEvent

from aces_conformance.conformance.diagnostics import _SEMANTIC_INVALID_DIAGNOSTIC_CODE, _diagnostic
from aces_conformance.conformance.observability import observability_evidence_conformance_diagnostics
from aces_conformance.conformance.snapshot_semantics import (
    _participant_behavior_history_diagnostics,
    _runtime_snapshot_semantic_diagnostics,
)
from aces_conformance.conformance.validators import _SEMANTIC_CONTEXT_REQUIRED_CONTRACTS, _validate_payload


def _state_semantic_diagnostics(
    contract_name: str,
    payload: object,
    state_model: type,
    invalid_message: str,
) -> list[Diagnostic]:
    try:
        state_model.from_payload(payload)
    except (TypeError, ValueError) as exc:
        return [
            _diagnostic(
                _SEMANTIC_INVALID_DIAGNOSTIC_CODE,
                contract_name,
                f"{invalid_message}: {exc}",
            )
        ]
    return []


def _event_stream_semantic_diagnostics(
    contract_name: str,
    payload: object,
    event_model: type,
    payload_type_message: str,
    invalid_message: str,
) -> list[Diagnostic]:
    if not isinstance(payload, list):
        return [
            _diagnostic(
                _SEMANTIC_INVALID_DIAGNOSTIC_CODE,
                contract_name,
                payload_type_message,
            )
        ]

    diagnostics: list[Diagnostic] = []
    for index, event in enumerate(payload):
        try:
            event_model.from_payload(event)
        except (TypeError, ValueError) as exc:
            diagnostics.append(
                _diagnostic(
                    _SEMANTIC_INVALID_DIAGNOSTIC_CODE,
                    f"{contract_name}[{index}]",
                    f"{invalid_message}: {exc}",
                )
            )
    return diagnostics


def _participant_behavior_stream_diagnostics(contract_name: str, payload: object) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if isinstance(payload, list):
        for index, event in enumerate(payload):
            try:
                ParticipantBehaviorHistoryEvent.from_payload(event)
            except (TypeError, ValueError) as exc:
                diagnostics.append(
                    _diagnostic(
                        _SEMANTIC_INVALID_DIAGNOSTIC_CODE,
                        f"{contract_name}[{index}]",
                        f"participant behavior history event semantics are invalid: {exc}",
                    )
                )
    diagnostics.extend(_participant_behavior_history_diagnostics(contract_name, payload))
    return diagnostics


_SEMANTIC_DISPATCH: dict[str, Callable[[str, object], list[Diagnostic]]] = {
    "workflow-result-envelope-v1": lambda name, payload: _state_semantic_diagnostics(
        name, payload, WorkflowExecutionState, "workflow result semantics are invalid"
    ),
    "evaluation-result-envelope-v1": lambda name, payload: _state_semantic_diagnostics(
        name, payload, EvaluationExecutionState, "evaluation result semantics are invalid"
    ),
    "participant-episode-state-envelope-v1": lambda name, payload: _state_semantic_diagnostics(
        name, payload, ParticipantEpisodeExecutionState, "participant episode state semantics are invalid"
    ),
    "participant-episode-history-event-stream-v1": lambda name, payload: _event_stream_semantic_diagnostics(
        name,
        payload,
        ParticipantEpisodeHistoryEvent,
        "participant episode history payload must be a list",
        "participant episode history event semantics are invalid",
    ),
    "participant-behavior-history-event-stream-v1": _participant_behavior_stream_diagnostics,
    "experiment-run-v1": lambda name, payload: list(observability_evidence_conformance_diagnostics(payload)),
    "runtime-snapshot-v1": lambda name, payload: _runtime_snapshot_semantic_diagnostics(payload),
}


def _semantic_diagnostics(contract_name: str, payload: object) -> list[Diagnostic]:
    handler = _SEMANTIC_DISPATCH.get(contract_name)
    if handler is None:
        return []
    return handler(contract_name, payload)


def _fixture_case_diagnostics(contract_name: str, payload: object) -> list[Diagnostic]:
    """Schema-gate first; only run semantic analysis on a schema-valid payload.

    Semantic checks (for example ``_runtime_snapshot_semantic_diagnostics``)
    deserialize the payload through its closed-world contract model and assume it
    is already schema-valid. Running them on a schema-invalid fixture would raise
    instead of reporting a diagnostic, so a schema failure short-circuits.
    """

    schema_diagnostics = _validate_payload(contract_name, payload)
    if schema_diagnostics:
        return schema_diagnostics
    if contract_name in _SEMANTIC_CONTEXT_REQUIRED_CONTRACTS:
        return [
            Diagnostic(
                code="conformance.semantic-context-required",
                domain="conformance",
                address="#",
                message=(
                    "full associated-artifact conformance requires a concrete parent and bounded byte readers; "
                    "the generic fixture runner establishes structural validity only"
                ),
                severity=Severity.ERROR,
            )
        ]
    return _semantic_diagnostics(contract_name, payload)
