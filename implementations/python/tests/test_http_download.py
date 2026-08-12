"""Tests for bounded repository-tool downloads."""

from __future__ import annotations

from http.client import RemoteDisconnected
from urllib.error import HTTPError

import pytest
from tools.http_download import download_bytes


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def test_download_retries_transient_disconnects_with_bounded_backoff() -> None:
    calls = 0
    delays: list[float] = []

    def opener(_url: str, *, timeout: float) -> _Response:
        nonlocal calls
        calls += 1
        assert timeout == 60
        if calls < 3:
            raise RemoteDisconnected("transient release-asset disconnect")
        return _Response(b"verified asset")

    assert (
        download_bytes(
            "https://example.invalid/pinned-tool",
            description="pinned tool",
            _opener=opener,
            _sleeper=delays.append,
        )
        == b"verified asset"
    )
    assert calls == 3
    assert delays == [0.25, 1.0]


def test_download_does_not_retry_non_transient_http_status() -> None:
    calls = 0

    def opener(url: str, *, timeout: float) -> _Response:
        nonlocal calls
        calls += 1
        raise HTTPError(url, 404, "not found", {}, None)

    with pytest.raises(RuntimeError, match=r"after 1 attempt\(s\): HTTPError"):
        download_bytes(
            "https://example.invalid/missing-tool",
            description="missing tool",
            _opener=opener,
            _sleeper=lambda _delay: None,
        )
    assert calls == 1
