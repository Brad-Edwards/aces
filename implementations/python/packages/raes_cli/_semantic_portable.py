"""Portable-contract phase adapters for the semantic CLI."""

from __future__ import annotations

from typing import Any

from raes_conformance.conformance import (
    contract_payload_root,
    contract_validation_strength,
    validate_contract_payload,
)
from raes_contracts.diagnostics import diagnostic_payload
from raes_contracts.json_ingress import StrictJsonIngressError, parse_bounded_json

from ._semantic_result import (
    CommandDiagnostic,
    CommandStatus,
    SemanticCommandResult,
    command_diagnostic,
    command_result,
)

PORTABLE_MAX_BYTES = 8 * 1024 * 1024


def execute_portable(
    operation: str,
    contract_id: str,
    raw: bytes,
) -> SemanticCommandResult:
    """Dispatch a portable artifact only to its owning phase operation."""

    root = contract_payload_root(contract_id)
    if root is None:
        return command_result(
            operation,
            status=CommandStatus.USAGE,
            contract_id=None,
            diagnostics=(
                command_diagnostic(
                    "cli.selector",
                    "cli",
                    "The contract selector is not supported.",
                ),
            ),
        )
    if operation == "parse" or operation not in {
        "validate",
        "inspect",
        "conformance",
    }:
        return command_result(
            operation,
            status=CommandStatus.UNSUPPORTED,
            contract_id=contract_id,
            diagnostics=(
                command_diagnostic(
                    "cli.operation-unsupported",
                    "cli",
                    "The selected operation is not defined for this contract.",
                ),
            ),
        )
    try:
        payload = parse_bounded_json(raw, max_bytes=PORTABLE_MAX_BYTES, root=root)
    except StrictJsonIngressError as exc:
        return command_result(
            operation,
            status=CommandStatus.INVALID,
            contract_id=contract_id,
            diagnostics=(
                command_diagnostic(
                    f"json.{exc.code}",
                    "json-ingress",
                    "Portable JSON input was rejected.",
                ),
            ),
        )
    owning_diagnostics = validate_contract_payload(contract_id, payload)
    diagnostics = tuple(CommandDiagnostic(**diagnostic_payload(item)) for item in owning_diagnostics)
    status = CommandStatus.INVALID if any(item.is_error for item in owning_diagnostics) else CommandStatus.SUCCESS
    summary = _phase_summary(operation, root, payload, status)
    return command_result(
        operation,
        status=status,
        contract_id=contract_id,
        payload=summary,
        diagnostics=diagnostics,
        validation_strength=contract_validation_strength(contract_id),
    )


def _phase_summary(
    operation: str,
    root: str,
    payload: dict[str, Any] | list[Any],
    status: CommandStatus,
) -> dict[str, Any]:
    if operation == "validate":
        return {
            "phase": "contract-admission",
            "root_type": root,
            "member_count": len(payload),
            "admitted": status is CommandStatus.SUCCESS,
        }
    if operation == "inspect":
        summary: dict[str, Any] = {
            "phase": "inspection",
            "root_type": root,
            "member_count": len(payload),
        }
        if isinstance(payload, dict):
            summary["members"] = sorted(payload)
        else:
            summary["item_count"] = len(payload)
        return summary
    return {
        "phase": "contract-conformance",
        "root_type": root,
        "check": "registered-contract",
        "passed": status is CommandStatus.SUCCESS,
    }
