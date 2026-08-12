"""Bounded offload for synchronous control-plane work."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

_P = ParamSpec("_P")
_T = TypeVar("_T")


class _ControlPlaneCallExecutor:
    """Keep blocking calls off the event loop and serialize target mutation.

    FastAPI/AnyIO owns the bounded worker pool. The async lock admits only one
    target-mutating call at a time without consuming worker threads while other
    mutations wait. Read and audit calls may still use separate workers, so a
    slow backend does not prevent status or authentication requests.
    """

    def __init__(self, *, max_pending_mutations: int) -> None:
        if max_pending_mutations <= 0:
            raise ValueError("max_pending_mutations must be positive")
        self._mutation_lock = asyncio.Lock()
        self._max_pending_mutations = max_pending_mutations
        self._pending_mutations = 0

    async def run(
        self,
        call: Callable[_P, _T],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> _T:
        return await run_in_threadpool(call, *args, **kwargs)

    async def mutate(
        self,
        call: Callable[_P, _T],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> _T:
        if self._pending_mutations >= self._max_pending_mutations:
            raise HTTPException(
                status_code=503,
                detail="control-plane mutation queue is full",
                headers={"Retry-After": "1"},
            )
        self._pending_mutations += 1
        try:
            async with self._mutation_lock:
                return await self.run(call, *args, **kwargs)
        finally:
            self._pending_mutations -= 1


def _control_plane_calls(request: Request) -> _ControlPlaneCallExecutor:
    executor = getattr(request.app.state, "control_plane_call_executor", None)
    if not isinstance(executor, _ControlPlaneCallExecutor):
        raise RuntimeError("control-plane call executor is not configured")
    return executor


__all__ = ("_ControlPlaneCallExecutor", "_control_plane_calls")
