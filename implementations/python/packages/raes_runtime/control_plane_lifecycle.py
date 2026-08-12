"""Lifecycle admission for public runtime-control-plane calls."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from functools import wraps
from threading import Condition, RLock, local
from typing import Any, Self, TypeVar, cast

_F = TypeVar("_F", bound=Callable[..., Any])


def runtime_owned(method: _F) -> _F:
    """Keep one public call admitted until its reads or effects are complete."""

    @wraps(method)
    def guarded(control_plane: Any, *args: Any, **kwargs: Any) -> Any:
        runtime_call = getattr(control_plane, "_runtime_call", None)
        if not callable(runtime_call):
            return method(control_plane, *args, **kwargs)
        with runtime_call():
            return method(control_plane, *args, **kwargs)

    guarded.__runtime_owned__ = True
    return cast(_F, guarded)


class RuntimeLifecycleMixin:
    """Drain admitted calls before releasing process-scoped authority."""

    _lifecycle_condition: Condition
    _lifecycle_local: local
    _active_runtime_calls: int
    _closing: bool
    _closed: bool
    _runtime_lease: object | None

    def _initialize_runtime_lifecycle(self) -> None:
        self._lifecycle_condition = Condition(RLock())
        self._lifecycle_local = local()
        self._active_runtime_calls = 0
        self._closing = False
        self._closed = False
        self._runtime_lease = None

    @runtime_owned
    def __enter__(self) -> Self:
        self._assert_runtime_owner()
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self.close()

    def __del__(self) -> None:
        with suppress(Exception):
            self.close()

    def close(self) -> None:
        """Release this control plane's process-scoped runtime authority."""

        condition = getattr(self, "_lifecycle_condition", None)
        if condition is None:
            self._close_runtime_lease()
            return
        with condition:
            if self._closed:
                return
            if getattr(self._lifecycle_local, "depth", 0):
                raise RuntimeError("cannot close a runtime control plane from one of its active calls")
            if self._closing:
                condition.wait_for(lambda: self._closed)
                return
            self._closing = True
            try:
                condition.wait_for(lambda: self._active_runtime_calls == 0)
            except BaseException:
                self._closing = False
                condition.notify_all()
                raise
            try:
                self._close_runtime_lease()
            finally:
                self._closed = True
                self._closing = False
                condition.notify_all()

    def _close_runtime_lease(self) -> None:
        lease = getattr(self, "_runtime_lease", None)
        close = getattr(lease, "close", None)
        try:
            if callable(close):
                close()
        finally:
            self._runtime_lease = None

    @contextmanager
    def _runtime_call(self) -> Iterator[None]:
        condition = self._lifecycle_condition
        with condition:
            if self._closed or self._closing:
                raise RuntimeError("runtime control plane is closed")
            lease = self._runtime_lease
            assert_owner = getattr(lease, "assert_owner", None)
            if callable(assert_owner):
                assert_owner()
            self._active_runtime_calls += 1
            self._lifecycle_local.depth = getattr(self._lifecycle_local, "depth", 0) + 1
        try:
            yield
        finally:
            with condition:
                self._lifecycle_local.depth -= 1
                self._active_runtime_calls -= 1
                if self._active_runtime_calls == 0:
                    condition.notify_all()

    def _assert_runtime_owner(self) -> None:
        if self._closed:
            raise RuntimeError("runtime control plane is closed")
        lease = self._runtime_lease
        assert_owner = getattr(lease, "assert_owner", None)
        if callable(assert_owner):
            assert_owner()


__all__ = ("RuntimeLifecycleMixin", "runtime_owned")
