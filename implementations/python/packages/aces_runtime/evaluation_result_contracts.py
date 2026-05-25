"""Evaluation result contract validation for runtime backends."""

from __future__ import annotations

from aces_processor.models import (
    Diagnostic,
    EvaluationExecutionContract,
    EvaluationExecutionState,
    EvaluationHistoryEvent,
    EvaluationHistoryEventType,
    EvaluationResultContract,
    EvaluationResultStatus,
    RuntimeDomain,
    RuntimeSnapshot,
    validate_evaluation_result,
)

from .diagnostics import _failure_diagnostic, _parse_timestamp


def evaluation_result_contract_diagnostics(
    snapshot: RuntimeSnapshot,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not isinstance(snapshot.evaluation_results, dict):
        return [
            _failure_diagnostic(
                "runtime.backend-contract-invalid",
                "runtime.apply.evaluation-results",
                "RuntimeSnapshot.evaluation_results must be a dict.",
            )
        ]
    if not isinstance(snapshot.evaluation_history, dict):
        return [
            _failure_diagnostic(
                "runtime.backend-contract-invalid",
                "runtime.apply.evaluation-history",
                "RuntimeSnapshot.evaluation_history must be a dict.",
            )
        ]

    evaluation_entries = {
        address: entry for address, entry in snapshot.entries.items() if entry.domain == RuntimeDomain.EVALUATION
    }
    observable_entries = {
        address: entry
        for address, entry in evaluation_entries.items()
        if isinstance(entry.payload, dict)
        and isinstance(entry.payload.get("result_contract"), dict)
        and isinstance(entry.payload.get("execution_contract"), dict)
    }

    missing_results = sorted(address for address in observable_entries if address not in snapshot.evaluation_results)
    if missing_results:
        diagnostics.append(
            _failure_diagnostic(
                "runtime.backend-contract-invalid",
                "runtime.apply.evaluation-results",
                ("Evaluation results must include all observable evaluation addresses: " + ", ".join(missing_results)),
            )
        )

    for evaluation_address, evaluation_result in snapshot.evaluation_results.items():
        if not isinstance(evaluation_address, str):
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    "runtime.apply.evaluation-results",
                    "Evaluation result keys must be strings.",
                )
            )
            continue
        if not isinstance(evaluation_result, dict):
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    "Evaluation results must use plain-data mapping values.",
                )
            )
            continue

        evaluation_entry = observable_entries.get(evaluation_address)
        if evaluation_entry is None:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    ("Evaluation results must correspond to an observable evaluation entry in the runtime snapshot."),
                )
            )
            continue

        payload = evaluation_entry.payload
        result_contract_payload = payload.get("result_contract") if isinstance(payload, dict) else None
        execution_contract_payload = payload.get("execution_contract") if isinstance(payload, dict) else None
        if not isinstance(result_contract_payload, dict):
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    "Evaluation snapshot payload is missing compiled result_contract.",
                )
            )
            continue
        if not isinstance(execution_contract_payload, dict):
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    "Evaluation snapshot payload is missing compiled execution_contract.",
                )
            )
            continue

        try:
            result_contract = EvaluationResultContract.from_mapping(result_contract_payload)
        except (TypeError, ValueError) as exc:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    f"Evaluation result_contract is invalid: {exc}",
                )
            )
            continue

        try:
            execution_contract = EvaluationExecutionContract.from_mapping(execution_contract_payload)
        except (TypeError, ValueError) as exc:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    f"Evaluation execution_contract is invalid: {exc}",
                )
            )
            continue

        try:
            normalized_result = EvaluationExecutionState.from_payload(evaluation_result)
        except (TypeError, ValueError) as exc:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    f"Evaluation result payload is invalid: {exc}",
                )
            )
            continue

        history_payload = snapshot.evaluation_history.get(evaluation_address)
        if history_payload is None:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    "Evaluation results must include a history stream for each observable address.",
                )
            )
            continue
        if not isinstance(history_payload, list):
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    "Evaluation history payload must be a list of event mappings.",
                )
            )
            continue
        normalized_history: list[EvaluationHistoryEvent] = []
        for event_payload in history_payload:
            try:
                normalized_history.append(EvaluationHistoryEvent.from_payload(event_payload))
            except (TypeError, ValueError) as exc:
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        evaluation_address,
                        f"Evaluation history payload is invalid: {exc}",
                    )
                )
        if normalized_history:
            previous_timestamp = None
            for event in normalized_history:
                try:
                    current_timestamp = _parse_timestamp(event.timestamp)
                except ValueError as exc:
                    diagnostics.append(
                        _failure_diagnostic(
                            "runtime.backend-contract-invalid",
                            evaluation_address,
                            f"Evaluation history event timestamp is invalid: {exc}",
                        )
                    )
                    continue
                if previous_timestamp is not None and current_timestamp < previous_timestamp:
                    diagnostics.append(
                        _failure_diagnostic(
                            "runtime.backend-contract-invalid",
                            evaluation_address,
                            "Evaluation history timestamps must be monotonic.",
                        )
                    )
                previous_timestamp = current_timestamp

        if normalized_result.state_schema_version != result_contract.state_schema_version:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    (
                        "Evaluation result schema version "
                        f"{normalized_result.state_schema_version!r} does not match "
                        f"compiled contract {result_contract.state_schema_version!r}."
                    ),
                )
            )
        if normalized_result.state_schema_version != execution_contract.state_schema_version:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    (
                        "Evaluation result schema version "
                        f"{normalized_result.state_schema_version!r} does not match "
                        f"execution contract {execution_contract.state_schema_version!r}."
                    ),
                )
            )
        violations = validate_evaluation_result(result_contract, normalized_result)
        for violation in violations:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    violation,
                )
            )

        if normalized_result.status.value not in execution_contract.allowed_statuses:
            diagnostics.append(
                _failure_diagnostic(
                    "runtime.backend-contract-invalid",
                    evaluation_address,
                    (
                        "Evaluation result status "
                        f"{normalized_result.status.value!r} is outside execution contract "
                        f"{execution_contract.allowed_statuses!r}."
                    ),
                )
            )
        if normalized_history:
            if (
                execution_contract.requires_start_event
                and normalized_history[0].event_type != EvaluationHistoryEventType.EVALUATION_STARTED
            ):
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        evaluation_address,
                        "Evaluation history must start with evaluation_started.",
                    )
                )
            for event in normalized_history:
                if event.event_type.value not in execution_contract.history_event_types:
                    diagnostics.append(
                        _failure_diagnostic(
                            "runtime.backend-contract-invalid",
                            evaluation_address,
                            (
                                "Evaluation history event type "
                                f"{event.event_type.value!r} is outside execution contract "
                                f"{execution_contract.history_event_types!r}."
                            ),
                        )
                    )
                if event.status.value not in execution_contract.allowed_statuses:
                    diagnostics.append(
                        _failure_diagnostic(
                            "runtime.backend-contract-invalid",
                            evaluation_address,
                            (
                                "Evaluation history status "
                                f"{event.status.value!r} is outside execution contract "
                                f"{execution_contract.allowed_statuses!r}."
                            ),
                        )
                    )
            expected_final_event = {
                EvaluationResultStatus.READY: EvaluationHistoryEventType.EVALUATION_READY,
                EvaluationResultStatus.FAILED: EvaluationHistoryEventType.EVALUATION_FAILED,
            }.get(normalized_result.status)
            if expected_final_event is not None and normalized_history[-1].event_type != expected_final_event:
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        evaluation_address,
                        (
                            "Evaluation result status "
                            f"{normalized_result.status.value!r} requires final history event "
                            f"{expected_final_event.value!r}."
                        ),
                    )
                )
            if normalized_result.status == EvaluationResultStatus.RUNNING and normalized_history[-1].event_type in {
                EvaluationHistoryEventType.EVALUATION_READY,
                EvaluationHistoryEventType.EVALUATION_FAILED,
            }:
                diagnostics.append(
                    _failure_diagnostic(
                        "runtime.backend-contract-invalid",
                        evaluation_address,
                        "Running evaluation results may not end history with a terminal event.",
                    )
                )

    return diagnostics
