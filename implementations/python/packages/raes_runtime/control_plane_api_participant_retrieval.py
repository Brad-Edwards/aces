"""HTTP routes for API-408 participant retrieval views."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, TypeVar

from fastapi import Depends, FastAPI, HTTPException, Request
from raes_contracts.contracts import (
    ParticipantContextViewModel,
    ParticipantHistoryViewModel,
    ParticipantStatusViewModel,
)

from .control_plane import RuntimeControlPlane
from .control_plane_security import ControlPlaneIdentity, ParticipantAudienceSubjectBinding

_NOT_FOUND_RESPONSES = {404: {"description": "Not found"}}
_GOVERNED_VIEW_RESPONSES = {
    **_NOT_FOUND_RESPONSES,
    403: {"description": "Forbidden"},
    409: {"description": "Participant projection conflict"},
}
_ViewT = TypeVar("_ViewT")


def _read_identity_dependency(request: Request) -> ControlPlaneIdentity:
    return request.app.state.control_plane_api_auth.read_identity(request)


_ReadIdentity = Annotated[ControlPlaneIdentity, Depends(_read_identity_dependency)]


def register_participant_retrieval_routes(
    app: FastAPI,
    control_plane: RuntimeControlPlane,
) -> None:
    @app.get(
        "/participants/{participant_address}/status",
        responses=_GOVERNED_VIEW_RESPONSES,
    )
    async def get_participant_status_view(
        participant_address: str,
        request: Request,
        identity: _ReadIdentity,
    ) -> ParticipantStatusViewModel:
        audience_binding = _require_governed_audience_candidate(control_plane, identity, participant_address)
        view = _governed_view(
            lambda: control_plane.get_participant_status_view(
                participant_address,
                identity=identity,
                audience_binding=audience_binding,
                idempotency_key=request.headers.get("idempotency-key", ""),
            )
        )
        if view is None:
            raise HTTPException(status_code=404, detail=f"Unknown participant: {participant_address}")
        control_plane.record_audit(
            action="get_participant_status_view",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
        )
        return view

    @app.get(
        "/participants/{participant_address}/episodes/{episode_id}/history",
        responses=_GOVERNED_VIEW_RESPONSES,
    )
    async def get_participant_history_view(
        participant_address: str,
        episode_id: str,
        request: Request,
        identity: _ReadIdentity,
    ) -> ParticipantHistoryViewModel:
        audience_binding = _require_governed_audience_candidate(control_plane, identity, participant_address)
        view = _governed_view(
            lambda: control_plane.get_participant_history_view(
                participant_address,
                episode_id,
                identity=identity,
                audience_binding=audience_binding,
                idempotency_key=request.headers.get("idempotency-key", ""),
            )
        )
        if view is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown participant episode: {participant_address}/{episode_id}",
            )
        control_plane.record_audit(
            action="get_participant_history_view",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
        )
        return view

    @app.get(
        "/participants/{participant_address}/context",
        responses=_GOVERNED_VIEW_RESPONSES,
    )
    async def get_participant_context_view(
        participant_address: str,
        view_ref: str,
        request: Request,
        identity: _ReadIdentity,
        episode_id: str | None = None,
        derivation_basis_ref: str | None = None,
        payload_ref: str | None = None,
    ) -> ParticipantContextViewModel:
        audience_binding = _require_governed_audience_candidate(control_plane, identity, participant_address)
        view = _governed_view(
            lambda: control_plane.get_participant_context_view(
                participant_address,
                view_ref=view_ref,
                episode_id=episode_id,
                derivation_basis_ref=derivation_basis_ref,
                payload_ref=payload_ref,
                identity=identity,
                audience_binding=audience_binding,
                idempotency_key=request.headers.get("idempotency-key", ""),
            )
        )
        if view is None:
            raise HTTPException(status_code=404, detail=f"Unknown participant: {participant_address}")
        control_plane.record_audit(
            action="get_participant_context_view",
            identity=identity.identity,
            allowed=True,
            target=str(request.url.path),
        )
        return view


def _require_governed_audience_candidate(
    control_plane: RuntimeControlPlane,
    identity: ControlPlaneIdentity,
    participant_address: str,
) -> ParticipantAudienceSubjectBinding | None:
    if getattr(control_plane, "_crossing_policy_resolver", None) is None:
        return None
    matches = tuple(
        binding
        for binding in identity.participant_audience_subjects
        if binding.participant_address == participant_address
    )
    if not matches:
        raise HTTPException(status_code=403, detail="forbidden")
    if len(matches) != 1:
        raise HTTPException(status_code=409, detail="participant audience binding is ambiguous")
    return matches[0]


def _governed_view(resolve: Callable[[], _ViewT]) -> _ViewT:
    try:
        return resolve()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="forbidden") from exc
    except ValueError as exc:
        detail = (
            "participant view crossing evidence is unavailable"
            if str(exc) == "participant view crossing evidence is unavailable"
            else "participant projection conflict"
        )
        raise HTTPException(status_code=409, detail=detail) from exc
