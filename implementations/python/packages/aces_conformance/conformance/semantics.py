"""Semantic-diagnostic dispatch and fixture-case gating."""

from __future__ import annotations

from typing import Any

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
    payload: Any,
    state_model: Any,
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
    payload: Any,
    event_model: Any,
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


def _participant_behavior_stream_diagnostics(contract_name: str, payload: Any) -> list[Diagnostic]:
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


def _semantic_diagnostics(contract_name: str, payload: Any) -> list[Diagnostic]:
    if contract_name == "workflow-result-envelope-v1":
        return _state_semantic_diagnostics(
            contract_name,
            payload,
            WorkflowExecutionState,
            "workflow result semantics are invalid",
        )
    if contract_name == "evaluation-result-envelope-v1":
        return _state_semantic_diagnostics(
            contract_name,
            payload,
            EvaluationExecutionState,
            "evaluation result semantics are invalid",
        )
    if contract_name == "participant-episode-state-envelope-v1":
        return _state_semantic_diagnostics(
            contract_name,
            payload,
            ParticipantEpisodeExecutionState,
            "participant episode state semantics are invalid",
        )
    if contract_name == "participant-episode-history-event-stream-v1":
        return _event_stream_semantic_diagnostics(
            contract_name,
            payload,
            ParticipantEpisodeHistoryEvent,
            "participant episode history payload must be a list",
            "participant episode history event semantics are invalid",
        )
    if contract_name == "participant-behavior-history-event-stream-v1":
        return _participant_behavior_stream_diagnostics(contract_name, payload)
    if contract_name == "experiment-run-v1":
        return list(observability_evidence_conformance_diagnostics(payload))
    if contract_name != "runtime-snapshot-v1":
        return []
    return _runtime_snapshot_semantic_diagnostics(payload)


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
