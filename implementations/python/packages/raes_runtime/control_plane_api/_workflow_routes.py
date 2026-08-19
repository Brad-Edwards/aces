"""Workflow cancellation and timeout-reconciliation routes for the control-plane app."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from raes_contracts.contracts import OperationReceiptModel, WorkflowCancellationRequestModel

from ..control_plane import RuntimeControlPlane
from ..control_plane_api_models import _request_fingerprint
from ._auth import _MutatingIdentity
from ._offload import _control_plane_calls
from ._responses import _CONFLICT_RESPONSES, _receipt_response


def _register_workflow_routes(
    app: FastAPI,
    control_plane: RuntimeControlPlane,
) -> None:
    @app.post("/workflows/{workflow_address}/cancel", responses=_CONFLICT_RESPONSES)
    async def cancel_workflow(
        workflow_address: str,
        request: Request,
        identity: _MutatingIdentity,
        cancellation: WorkflowCancellationRequestModel | None = None,
    ) -> OperationReceiptModel:
        payload = cancellation or WorkflowCancellationRequestModel()
        calls = _control_plane_calls(request)
        try:
            receipt = await calls.mutate(
                control_plane.cancel_workflow,
                workflow_address,
                run_id=payload.run_id,
                reason=payload.reason,
                idempotency_key=request.headers.get("idempotency-key", ""),
                request_fingerprint=_request_fingerprint(
                    request,
                    getattr(request.state, "raw_body", b""),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        await calls.run(
            control_plane.record_audit,
            action="cancel_workflow",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
            operation_id=receipt.operation_id,
        )
        return _receipt_response(receipt)

    @app.post("/workflows/reconcile-timeouts", responses=_CONFLICT_RESPONSES)
    async def reconcile_timeouts(
        request: Request,
        identity: _MutatingIdentity,
    ) -> OperationReceiptModel:
        calls = _control_plane_calls(request)
        try:
            receipt = await calls.mutate(
                control_plane.reconcile_workflow_timeouts,
                idempotency_key=request.headers.get("idempotency-key", ""),
                request_fingerprint=_request_fingerprint(
                    request,
                    getattr(request.state, "raw_body", b""),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        await calls.run(
            control_plane.record_audit,
            action="reconcile_workflow_timeouts",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
            operation_id=receipt.operation_id,
        )
        return _receipt_response(receipt)
