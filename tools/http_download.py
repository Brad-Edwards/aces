"""Bounded resilient downloads for checksum-pinned repository tools."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

_RETRY_DELAYS_SECONDS = (1.0, 2.0, 4.0, 8.0)
_RETRYABLE_HTTP_STATUS = frozenset({408, 429, 500, 502, 503, 504})


class _Response(Protocol):
    def __enter__(self) -> _Response: ...

    def __exit__(self, *args: object) -> None: ...

    def read(self) -> bytes: ...


def _open_https(url: str, *, timeout: float) -> _Response:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("repository-tool downloads require an absolute HTTPS URL")
    request = Request(url, headers={"User-Agent": "RAES-pinned-tool-installer"})
    return build_opener().open(request, timeout=timeout)


def download_bytes(
    url: str,
    *,
    description: str,
    attempts: int = 5,
    timeout_seconds: float = 60,
    _opener: Callable[..., _Response] | None = None,
    _sleeper: Callable[[float], None] | None = None,
) -> bytes:
    """Download bytes with bounded retries for transient transport failures."""

    if attempts < 1:
        raise ValueError("download attempts must be positive")
    opener = _opener or _open_https
    sleeper = _sleeper or time.sleep
    last_error: BaseException | None = None
    for attempt in range(attempts):
        try:
            with opener(url, timeout=timeout_seconds) as response:
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code not in _RETRYABLE_HTTP_STATUS:
                break
        except OSError as exc:
            last_error = exc
        if attempt + 1 < attempts:
            sleeper(_RETRY_DELAYS_SECONDS[min(attempt, len(_RETRY_DELAYS_SECONDS) - 1)])

    assert last_error is not None
    raise RuntimeError(
        f"failed to download {description} from {url} after {attempt + 1} attempt(s): {type(last_error).__name__}"
    ) from last_error


__all__ = ["download_bytes"]
