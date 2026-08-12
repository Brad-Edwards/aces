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
    response: JSONResponse | None = None
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            content_length_value = int(content_length)
        except ValueError:
            response = _invalid_content_length_response(control_plane, request)
        else:
            if content_length_value > max_request_bytes:
                response = _request_too_large_response(control_plane, request)
    return response


async def _body_size_guard_response(
    control_plane: RuntimeControlPlane,
    request: Request,
    *,
    max_request_bytes: int,
) -> JSONResponse | None:
    # Accumulate the body incrementally and stop as soon as the running total
    # exceeds the limit. Buffering via ``request.body()`` would read the whole
    # payload first, so a request without a declared ``content-length`` (e.g.
    # ``Transfer-Encoding: chunked``) bypasses ``_content_length_guard_response``
    # and could exhaust memory before any size check runs.
    body = bytearray()
    async for chunk in request.stream():
        # Measure before copying: a single oversized chunk would otherwise be
        # appended in full before the limit is consulted.
        if len(body) + len(chunk) > max_request_bytes:
            return _request_too_large_response(control_plane, request)
        body.extend(chunk)
    accepted_body = bytes(body)
    # Streaming consumes the receive channel, so seed Starlette's body cache the
    # way ``Request.body()`` would. Route handlers and FastAPI's own body parsing
    # then still see the payload instead of an exhausted stream: Starlette's own
    # ``_CachedRequest.wrapped_receive`` replays ``_body`` to the inner app, which
    # is the framework's hook for middleware that consumes the body, and there is
    # no public equivalent.
    request._body = accepted_body  # NOSONAR - documented Starlette body-cache hook, no public equivalent
    request.state.raw_body = accepted_body
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
