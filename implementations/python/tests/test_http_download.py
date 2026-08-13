"""Compatibility tests for governed repository-tool downloads."""

from __future__ import annotations

import io

import pytest
import tools.http_download as http_download
from tools.release_download import DEFAULT_RELEASE_RETRY_POLICY, ReleaseDownloadError, ReleaseRetryPolicy

RELEASE_URL = "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_checksums.txt"


def test_download_bytes_delegates_to_the_governed_release_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def governed_open(url: str, *, timeout: float, policy: ReleaseRetryPolicy) -> io.BytesIO:
        observed.update(url=url, timeout=timeout, policy=policy)
        return io.BytesIO(b"verified asset")

    monkeypatch.setattr(http_download, "retrying_urlopen", governed_open)

    assert http_download.download_bytes(RELEASE_URL, description="gitleaks checksums") == b"verified asset"
    assert observed["url"] == RELEASE_URL
    assert observed["timeout"] == 60
    policy = observed["policy"]
    assert isinstance(policy, ReleaseRetryPolicy)
    assert policy.max_attempts == DEFAULT_RELEASE_RETRY_POLICY.max_attempts
    assert policy.maximum_response_bytes == DEFAULT_RELEASE_RETRY_POLICY.maximum_response_bytes


def test_download_bytes_preserves_explicit_attempt_timeout_and_size_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def governed_open(url: str, *, timeout: float, policy: ReleaseRetryPolicy) -> io.BytesIO:
        observed.update(url=url, timeout=timeout, policy=policy)
        return io.BytesIO(b"four")

    monkeypatch.setattr(http_download, "retrying_urlopen", governed_open)

    assert (
        http_download.download_bytes(
            RELEASE_URL,
            description="gitleaks checksums",
            attempts=2,
            timeout_seconds=12,
            max_bytes=4,
        )
        == b"four"
    )
    assert observed["url"] == RELEASE_URL
    assert observed["timeout"] == 12
    policy = observed["policy"]
    assert isinstance(policy, ReleaseRetryPolicy)
    assert policy.max_attempts == 2
    assert policy.maximum_response_bytes == 4


def test_download_bytes_caps_legacy_options_at_the_governed_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def governed_open(url: str, *, timeout: float, policy: ReleaseRetryPolicy) -> io.BytesIO:
        observed.update(url=url, timeout=timeout, policy=policy)
        return io.BytesIO(b"verified asset")

    monkeypatch.setattr(http_download, "retrying_urlopen", governed_open)

    assert (
        http_download.download_bytes(
            RELEASE_URL,
            description="gitleaks checksums",
            attempts=99,
            timeout_seconds=999,
            max_bytes=DEFAULT_RELEASE_RETRY_POLICY.maximum_response_bytes + 1,
        )
        == b"verified asset"
    )
    assert observed["timeout"] == DEFAULT_RELEASE_RETRY_POLICY.request_timeout_seconds
    policy = observed["policy"]
    assert isinstance(policy, ReleaseRetryPolicy)
    assert policy.max_attempts == DEFAULT_RELEASE_RETRY_POLICY.max_attempts
    assert policy.maximum_response_bytes == DEFAULT_RELEASE_RETRY_POLICY.maximum_response_bytes


@pytest.mark.parametrize(
    "options",
    [
        {"attempts": 0},
        {"max_bytes": -1},
        {"timeout_seconds": 0},
    ],
)
def test_download_bytes_rejects_invalid_compatibility_options_before_network(
    monkeypatch: pytest.MonkeyPatch,
    options: dict[str, int],
) -> None:
    monkeypatch.setattr(
        http_download,
        "retrying_urlopen",
        lambda *_args, **_kwargs: pytest.fail("invalid options reached the governed downloader"),
    )

    with pytest.raises(ValueError):
        http_download.download_bytes(RELEASE_URL, description="gitleaks checksums", **options)


def test_download_bytes_preserves_a_zero_byte_caller_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def governed_open(_url: str, *, timeout: float, policy: ReleaseRetryPolicy) -> io.BytesIO:
        observed.update(timeout=timeout, policy=policy)
        return io.BytesIO(b"x")

    monkeypatch.setattr(http_download, "retrying_urlopen", governed_open)

    with pytest.raises(RuntimeError, match="gitleaks checksums exceeds the download limit"):
        http_download.download_bytes(RELEASE_URL, description="gitleaks checksums", max_bytes=0)

    policy = observed["policy"]
    assert isinstance(policy, ReleaseRetryPolicy)
    assert policy.maximum_response_bytes == 1


def test_download_bytes_wraps_only_the_stable_governed_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail = "release download exhausted 3 bounded attempts: HTTP 503"

    def fail(_url: str, **_kwargs: object) -> io.BytesIO:
        raise ReleaseDownloadError(detail)

    monkeypatch.setattr(http_download, "retrying_urlopen", fail)

    with pytest.raises(RuntimeError, match="failed to download gitleaks checksums") as raised:
        http_download.download_bytes(RELEASE_URL, description="gitleaks checksums")

    assert detail in str(raised.value)
