"""Shared response-code declarations and the operation-receipt response builder."""

from __future__ import annotations

from dataclasses import asdict

from raes_contracts.contracts import OperationReceiptModel
from raes_contracts.runtime_state import OperationReceipt

_CONFLICT_RESPONSES = {409: {"description": "Conflict"}}
_NOT_FOUND_RESPONSES = {404: {"description": "Not found"}}
_BAD_REQUEST_CONFLICT_RESPONSES = {
    400: {"description": "Bad request"},
    409: {"description": "Conflict"},
}


def _receipt_response(receipt: OperationReceipt) -> OperationReceiptModel:
    return OperationReceiptModel.model_validate(
        {
            "schema_version": receipt.schema_version,
            "operation_id": receipt.operation_id,
            "domain": receipt.domain.value,
            "submitted_at": receipt.submitted_at,
            "accepted": receipt.accepted,
            "diagnostics": [asdict(diag) for diag in receipt.diagnostics],
        }
    )
