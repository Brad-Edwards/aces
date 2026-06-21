"""HTTP request guards for the runtime control-plane API."""

from __future__ import annotations

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .control_plane import RuntimeControlPlane

_REQUEST_TOO_LARGE_DETAIL = "request too large"
_INVALID_CONTENT_LENGTH_DETAIL = "invalid content-length"


async def request_size_guard_response(
    control_plane: RuntimeControlPlane,
    request: Request,
    *,
    max_request_bytes: int,
) -> Response | None:
    guard_response = _content_length_guard_response(
        control_plane,
        request,
        max_request_bytes=max_request_bytes,
    )
    if guard_response is not None:
        return guard_response
    return await _body_size_guard_response(
        control_plane,
        request,
        max_request_bytes=max_request_bytes,
    )


def _content_length_guard_response(
    control_plane: RuntimeControlPlane,
    request: Request,
    *,
    max_request_bytes: int,
) -> JSONResponse | None:
    content_length = request.headers.get("content-length")
    if content_length is None:
        return None
    try:
        content_length_value = int(content_length)
    except ValueError:
        return _invalid_content_length_response(control_plane, request)
    if content_length_value > max_request_bytes:
        return _request_too_large_response(control_plane, request)
    return None


async def _body_size_guard_response(
    control_plane: RuntimeControlPlane,
    request: Request,
    *,
    max_request_bytes: int,
) -> JSONResponse | None:
    body = await request.body()
    if len(body) > max_request_bytes:
        return _request_too_large_response(control_plane, request)
    request.state.raw_body = body
    return None


def _request_too_large_response(
    control_plane: RuntimeControlPlane,
    request: Request,
) -> JSONResponse:
    control_plane.record_audit(
        action=request.method,
        identity="anonymous",
        allowed=False,
        target=str(request.url.path),
        reason=_REQUEST_TOO_LARGE_DETAIL,
    )
    return JSONResponse(status_code=413, content={"detail": _REQUEST_TOO_LARGE_DETAIL})


def _invalid_content_length_response(
    control_plane: RuntimeControlPlane,
    request: Request,
) -> JSONResponse:
    control_plane.record_audit(
        action=request.method,
        identity="anonymous",
        allowed=False,
        target=str(request.url.path),
        reason=_INVALID_CONTENT_LENGTH_DETAIL,
    )
    return JSONResponse(status_code=400, content={"detail": _INVALID_CONTENT_LENGTH_DETAIL})
