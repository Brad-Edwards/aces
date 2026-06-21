"""HTTP routes for API-408 participant retrieval views."""

from __future__ import annotations

from typing import Annotated

from aces_contracts.contracts import (
    ParticipantContextViewModel,
    ParticipantHistoryViewModel,
    ParticipantStatusViewModel,
)
from fastapi import Depends, FastAPI, HTTPException, Request

from .control_plane import RuntimeControlPlane
from .control_plane_security import ControlPlaneIdentity

_NOT_FOUND_RESPONSES = {404: {"description": "Not found"}}


def _read_identity_dependency(request: Request) -> ControlPlaneIdentity:
    return request.app.state.control_plane_api_auth.read_identity(request)


_ReadIdentity = Annotated[ControlPlaneIdentity, Depends(_read_identity_dependency)]


def register_participant_retrieval_routes(
    app: FastAPI,
    control_plane: RuntimeControlPlane,
) -> None:
    @app.get(
        "/participants/{participant_address}/status",
        responses=_NOT_FOUND_RESPONSES,
    )
    async def get_participant_status_view(
        participant_address: str,
        request: Request,
        identity: _ReadIdentity,
    ) -> ParticipantStatusViewModel:
        view = control_plane.get_participant_status_view(participant_address)
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
        responses=_NOT_FOUND_RESPONSES,
    )
    async def get_participant_history_view(
        participant_address: str,
        episode_id: str,
        request: Request,
        identity: _ReadIdentity,
    ) -> ParticipantHistoryViewModel:
        view = control_plane.get_participant_history_view(participant_address, episode_id)
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
        responses=_NOT_FOUND_RESPONSES,
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
        view = control_plane.get_participant_context_view(
            participant_address,
            view_ref=view_ref,
            episode_id=episode_id,
            derivation_basis_ref=derivation_basis_ref,
            payload_ref=payload_ref,
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
