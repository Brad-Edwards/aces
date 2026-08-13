"""Compatibility entry point for governed pinned-tool release downloads.

The retry, redirect, deadline, framing, and response-size policy has one owner:
``tools.release_download``.  This module preserves the ``download_bytes`` API
introduced with the repository-tool installers while delegating every network
request to that boundary.
"""

from __future__ import annotations

from dataclasses import replace

from tools.release_download import (
    DEFAULT_RELEASE_RETRY_POLICY,
    ReleaseDownloadError,
    ReleaseRetryPolicy,
    retrying_urlopen,
)


def _compatibility_policy(*, attempts: int, max_bytes: int | None) -> ReleaseRetryPolicy:
    if attempts < 1:
        raise ValueError("download attempts must be positive")
    if max_bytes is not None and max_bytes < 0:
        raise ValueError("download size bound must be non-negative")
    response_bound = DEFAULT_RELEASE_RETRY_POLICY.maximum_response_bytes
    if max_bytes is not None:
        # The governed policy requires a positive transport bound.  A caller's
        # zero-byte bound is enforced immediately after the bounded read.
        response_bound = min(response_bound, max(1, max_bytes))
    return replace(
        DEFAULT_RELEASE_RETRY_POLICY,
        max_attempts=min(attempts, DEFAULT_RELEASE_RETRY_POLICY.max_attempts),
        maximum_response_bytes=response_bound,
    )


def download_bytes(
    url: str,
    *,
    description: str,
    attempts: int = DEFAULT_RELEASE_RETRY_POLICY.max_attempts,
    timeout_seconds: float = 60,
    max_bytes: int | None = None,
) -> bytes:
    """Return bytes acquired through the single governed release boundary."""

    policy = _compatibility_policy(attempts=attempts, max_bytes=max_bytes)
    if timeout_seconds <= 0:
        raise ValueError("download timeout must be positive")
    request_timeout = min(timeout_seconds, DEFAULT_RELEASE_RETRY_POLICY.request_timeout_seconds)
    try:
        with retrying_urlopen(url, timeout=request_timeout, policy=policy) as response:
            payload = response.read()
    except ReleaseDownloadError as exc:
        raise RuntimeError(f"failed to download {description}: {exc}") from exc
    if max_bytes is not None and len(payload) > max_bytes:
        raise RuntimeError(f"{description} exceeds the download limit")
    return payload


__all__ = ["download_bytes"]
