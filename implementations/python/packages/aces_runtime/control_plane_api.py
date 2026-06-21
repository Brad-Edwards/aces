"""Reference HTTP/JSON adapter for the runtime control plane."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Annotated

from aces_contracts.contracts import (
    EvaluationPlanModel,
    OperationReceiptModel,
    OperationStatusModel,
    OrchestrationPlanModel,
    ProvisioningPlanModel,
    RuntimeSnapshotEnvelopeModel,
    WorkflowCancellationRequestModel,
)
from aces_contracts.participant_episode import ParticipantEpisodeTerminalReason
from aces_contracts.runtime_state import OperationReceipt
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from .control_plane import RuntimeControlPlane
from .control_plane_api_guards import request_size_guard_response
from .control_plane_api_models import (
    _evaluation_plan,
    _operation_status_model,
    _orchestration_plan,
    _ParticipantInitializeBody,
    _ParticipantResetBody,
    _ParticipantRestartBody,
    _ParticipantTerminateBody,
    _provisioning_plan,
    _request_fingerprint,
    _snapshot_model,
)
from .control_plane_api_participant_retrieval import register_participant_retrieval_routes
from .control_plane_security import (
    ControlPlaneIdentity,
    ControlPlaneRole,
    ControlPlaneSecurityConfig,
)

_CONFLICT_RESPONSES = {409: {"description": "Conflict"}}
_NOT_FOUND_RESPONSES = {404: {"description": "Not found"}}
_BAD_REQUEST_CONFLICT_RESPONSES = {
    400: {"description": "Bad request"},
    409: {"description": "Conflict"},
}


class _ControlPlaneApiAuth:
    def __init__(
        self,
        control_plane: RuntimeControlPlane,
        security: ControlPlaneSecurityConfig,
    ) -> None:
        self._control_plane = control_plane
        self._security = security

    def mutating_identity(self, request: Request) -> ControlPlaneIdentity:
        identity = self._authenticated_identity(request)
        return self._authorize(
            identity,
            roles={ControlPlaneRole.BACKEND, ControlPlaneRole.OPERATOR},
            request=request,
        )

    def read_identity(self, request: Request) -> ControlPlaneIdentity:
        identity = self._authenticated_identity(request)
        return self._authorize(
            identity,
            roles={
                ControlPlaneRole.BACKEND,
                ControlPlaneRole.OPERATOR,
                ControlPlaneRole.AUDITOR,
            },
            request=request,
        )

    def _authenticated_identity(self, request: Request) -> ControlPlaneIdentity:
        try:
            return self._authenticate_request(request)
        except HTTPException as exc:
            self._record_denial(request, str(exc.detail))
            raise

    def _authenticate_request(self, request: Request) -> ControlPlaneIdentity:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            identity = self._security.bearer_tokens.get(token)
            if identity is not None:
                return identity
        if not self._security.trust_proxy_identity_headers:
            raise HTTPException(status_code=401, detail="trusted proxy identity headers are not enabled")
        identity_name = request.headers.get(self._security.identity_header, "")
        verified = request.headers.get(self._security.verified_header, "").lower()
        if self._security.require_verified_identity and verified != "true":
            raise HTTPException(status_code=401, detail="verified client identity required")
        identity = self._security.trusted_identities.get(identity_name)
        if identity is None:
            raise HTTPException(status_code=401, detail="unknown client identity")
        if identity.target_name and identity.target_name != self._control_plane.target_name:
            raise HTTPException(status_code=403, detail="identity is not authorized for this target")
        return identity

    def _authorize(
        self,
        identity: ControlPlaneIdentity,
        *,
        roles: set[ControlPlaneRole],
        request: Request,
    ) -> ControlPlaneIdentity:
        if not identity.roles.isdisjoint(roles):
            return identity
        self._control_plane.record_audit(
            action=request.method,
            identity=identity.identity,
            allowed=False,
            target=str(request.url.path),
            reason="forbidden",
        )
        raise HTTPException(status_code=403, detail="forbidden")

    def _record_denial(self, request: Request, reason: str) -> None:
        self._control_plane.record_audit(
            action=request.method,
            identity="anonymous",
            allowed=False,
            target=str(request.url.path),
            reason=reason,
        )


def _mutating_identity_dependency(request: Request) -> ControlPlaneIdentity:
    return request.app.state.control_plane_api_auth.mutating_identity(request)


def _read_identity_dependency(request: Request) -> ControlPlaneIdentity:
    return request.app.state.control_plane_api_auth.read_identity(request)


_MutatingIdentity = Annotated[ControlPlaneIdentity, Depends(_mutating_identity_dependency)]
_ReadIdentity = Annotated[ControlPlaneIdentity, Depends(_read_identity_dependency)]


def create_control_plane_app(
    control_plane: RuntimeControlPlane,
    *,
    security: ControlPlaneSecurityConfig | None = None,
) -> FastAPI:
    """Create a reference HTTP/JSON control-plane app."""

    security = security or ControlPlaneSecurityConfig.strict_defaults()
    app = FastAPI(
        title="ACES Runtime Control Plane",
        version="0.1.0",
        description="Reference HTTP/JSON adapter over the repo-owned runtime control plane.",
    )
    app.state.control_plane_api_auth = _ControlPlaneApiAuth(control_plane, security)
    _install_request_guards(app, control_plane, security)
    _register_operation_routes(app, control_plane)
    _register_workflow_routes(app, control_plane)
    _register_participant_episode_routes(app, control_plane)
    register_participant_retrieval_routes(app, control_plane)
    return app


def _install_request_guards(
    app: FastAPI,
    control_plane: RuntimeControlPlane,
    security: ControlPlaneSecurityConfig,
) -> None:
    @app.middleware("http")
    async def _limit_request_size(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        guard_response = await request_size_guard_response(
            control_plane,
            request,
            max_request_bytes=security.max_request_bytes,
        )
        if guard_response is not None:
            return guard_response
        return await call_next(request)

    @app.exception_handler(Exception)
    async def _redacted_errors(request: Request, exc: Exception) -> JSONResponse:
        control_plane.record_audit(
            action=request.method,
            identity="anonymous",
            allowed=False,
            target=str(request.url.path),
            reason=f"internal-error:{type(exc).__name__}",
        )
        return JSONResponse(status_code=500, content={"detail": "internal server error"})


def _register_operation_routes(
    app: FastAPI,
    control_plane: RuntimeControlPlane,
) -> None:
    _register_operation_submission_routes(app, control_plane)
    _register_operation_read_routes(app, control_plane)


def _register_operation_submission_routes(
    app: FastAPI,
    control_plane: RuntimeControlPlane,
) -> None:
    @app.post("/operations/provisioning", responses=_CONFLICT_RESPONSES)
    async def submit_provisioning(
        request: Request,
        plan: ProvisioningPlanModel,
        identity: _MutatingIdentity,
    ) -> OperationReceiptModel:
        try:
            receipt = control_plane.submit_provisioning(
                _provisioning_plan(plan),
                idempotency_key=request.headers.get("idempotency-key", ""),
                request_fingerprint=_request_fingerprint(
                    request,
                    getattr(request.state, "raw_body", b""),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        control_plane.record_audit(
            action="submit_provisioning",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
            operation_id=receipt.operation_id,
        )
        return _receipt_response(receipt)

    @app.post("/operations/orchestration", responses=_CONFLICT_RESPONSES)
    async def submit_orchestration(
        request: Request,
        plan: OrchestrationPlanModel,
        identity: _MutatingIdentity,
    ) -> OperationReceiptModel:
        try:
            receipt = control_plane.submit_orchestration(
                _orchestration_plan(plan),
                idempotency_key=request.headers.get("idempotency-key", ""),
                request_fingerprint=_request_fingerprint(
                    request,
                    getattr(request.state, "raw_body", b""),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        control_plane.record_audit(
            action="submit_orchestration",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
            operation_id=receipt.operation_id,
        )
        return _receipt_response(receipt)

    @app.post("/operations/evaluation", responses=_CONFLICT_RESPONSES)
    async def submit_evaluation(
        request: Request,
        plan: EvaluationPlanModel,
        identity: _MutatingIdentity,
    ) -> OperationReceiptModel:
        try:
            receipt = control_plane.submit_evaluation(
                _evaluation_plan(plan),
                idempotency_key=request.headers.get("idempotency-key", ""),
                request_fingerprint=_request_fingerprint(
                    request,
                    getattr(request.state, "raw_body", b""),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        control_plane.record_audit(
            action="submit_evaluation",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
            operation_id=receipt.operation_id,
        )
        return _receipt_response(receipt)


def _register_operation_read_routes(
    app: FastAPI,
    control_plane: RuntimeControlPlane,
) -> None:
    @app.get("/operations/{operation_id}", responses=_NOT_FOUND_RESPONSES)
    async def get_operation(
        operation_id: str,
        request: Request,
        identity: _ReadIdentity,
    ) -> OperationStatusModel:
        status = control_plane.get_operation(operation_id)
        if status is None:
            raise HTTPException(status_code=404, detail=f"Unknown operation: {operation_id}")
        control_plane.record_audit(
            action="get_operation",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
            operation_id=operation_id,
        )
        return _operation_status_model(status)

    @app.get("/snapshot")
    async def get_snapshot(
        request: Request,
        identity: _ReadIdentity,
    ) -> RuntimeSnapshotEnvelopeModel:
        control_plane.record_audit(
            action="get_snapshot",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
        )
        return _snapshot_model(control_plane.get_snapshot())


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
        try:
            receipt = control_plane.cancel_workflow(
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
        control_plane.record_audit(
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
        try:
            receipt = control_plane.reconcile_workflow_timeouts(
                idempotency_key=request.headers.get("idempotency-key", ""),
                request_fingerprint=_request_fingerprint(
                    request,
                    getattr(request.state, "raw_body", b""),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        control_plane.record_audit(
            action="reconcile_workflow_timeouts",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
            operation_id=receipt.operation_id,
        )
        return _receipt_response(receipt)


def _register_participant_episode_routes(
    app: FastAPI,
    control_plane: RuntimeControlPlane,
) -> None:
    _register_participant_episode_start_routes(app, control_plane)
    _register_participant_episode_end_routes(app, control_plane)


def _register_participant_episode_start_routes(
    app: FastAPI,
    control_plane: RuntimeControlPlane,
) -> None:
    @app.post(
        "/participants/{participant_address}/episodes/initialize",
        responses=_CONFLICT_RESPONSES,
    )
    async def initialize_participant_episode(
        participant_address: str,
        request: Request,
        identity: _MutatingIdentity,
        body: _ParticipantInitializeBody | None = None,
    ) -> OperationReceiptModel:
        payload = body or _ParticipantInitializeBody()
        try:
            receipt = control_plane.initialize_participant_episode(
                participant_address,
                episode_id=payload.episode_id,
                idempotency_key=request.headers.get("idempotency-key", ""),
                request_fingerprint=_request_fingerprint(
                    request,
                    getattr(request.state, "raw_body", b""),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        control_plane.record_audit(
            action="initialize_participant_episode",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
            operation_id=receipt.operation_id,
        )
        return _receipt_response(receipt)

    @app.post(
        "/participants/{participant_address}/episodes/reset",
        responses=_CONFLICT_RESPONSES,
    )
    async def reset_participant_episode(
        participant_address: str,
        request: Request,
        identity: _MutatingIdentity,
        body: _ParticipantResetBody | None = None,
    ) -> OperationReceiptModel:
        payload = body or _ParticipantResetBody()
        try:
            receipt = control_plane.reset_participant_episode(
                participant_address,
                episode_id=payload.episode_id,
                reason=payload.reason,
                idempotency_key=request.headers.get("idempotency-key", ""),
                request_fingerprint=_request_fingerprint(
                    request,
                    getattr(request.state, "raw_body", b""),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        control_plane.record_audit(
            action="reset_participant_episode",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
            operation_id=receipt.operation_id,
        )
        return _receipt_response(receipt)


def _register_participant_episode_end_routes(
    app: FastAPI,
    control_plane: RuntimeControlPlane,
) -> None:
    @app.post(
        "/participants/{participant_address}/episodes/restart",
        responses=_CONFLICT_RESPONSES,
    )
    async def restart_participant_episode(
        participant_address: str,
        request: Request,
        identity: _MutatingIdentity,
        body: _ParticipantRestartBody | None = None,
    ) -> OperationReceiptModel:
        payload = body or _ParticipantRestartBody()
        try:
            receipt = control_plane.restart_participant_episode(
                participant_address,
                episode_id=payload.episode_id,
                reason=payload.reason,
                idempotency_key=request.headers.get("idempotency-key", ""),
                request_fingerprint=_request_fingerprint(
                    request,
                    getattr(request.state, "raw_body", b""),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        control_plane.record_audit(
            action="restart_participant_episode",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
            operation_id=receipt.operation_id,
        )
        return _receipt_response(receipt)

    @app.post(
        "/participants/{participant_address}/episodes/terminate",
        responses=_BAD_REQUEST_CONFLICT_RESPONSES,
    )
    async def terminate_participant_episode(
        participant_address: str,
        request: Request,
        identity: _MutatingIdentity,
        body: _ParticipantTerminateBody | None = None,
    ) -> OperationReceiptModel:
        payload = body or _ParticipantTerminateBody()
        try:
            terminal_reason = ParticipantEpisodeTerminalReason(payload.terminal_reason)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid terminal_reason: {exc}") from exc
        try:
            receipt = control_plane.terminate_participant_episode(
                participant_address,
                terminal_reason=terminal_reason,
                detail=payload.detail,
                idempotency_key=request.headers.get("idempotency-key", ""),
                request_fingerprint=_request_fingerprint(
                    request,
                    getattr(request.state, "raw_body", b""),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        control_plane.record_audit(
            action="terminate_participant_episode",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
            operation_id=receipt.operation_id,
        )
        return _receipt_response(receipt)


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
