"""Adversarial tests for bounded pinned-tool release acquisition."""

from __future__ import annotations

import io
import queue
import socketserver
import threading
import time
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from email.message import Message
from email.utils import format_datetime
from hashlib import sha256
from http.client import IncompleteRead, RemoteDisconnected
from pathlib import Path
from tarfile import ReadError
from types import ModuleType
from urllib.error import HTTPError, URLError

import pytest
import tools.gitleaks_tool as gitleaks_tool
import tools.osv_scanner_tool as osv_scanner_tool
import tools.policy.conftest_tool as conftest_tool
import tools.release_download as release_download
import tools.vale_tool as vale_tool

RELEASE_URL = "https://github.com/errata-ai/vale/releases/download/v3.15.2/vale.tar.gz"
VALE_CANONICAL_URL = "https://github.com/vale-cli/vale/releases/download/v3.15.2/vale.tar.gz"
RELEASE_ASSET_URL = (
    "https://release-assets.githubusercontent.com/github-production-release-asset/81020247/"
    "6307b9db-05dd-4042-9bec-ffb9fe72e4e8?sig=ephemeral-secret"
)


class DownloadResponse:
    def __init__(
        self,
        payload: bytes | BaseException,
        *,
        status: int | None = 200,
        headers: object | None = None,
    ) -> None:
        self.payload = payload
        self.offset = 0
        self.status = status
        self.headers = {} if headers is None else headers
        self.read_timeouts: list[float] = []

    def __enter__(self) -> DownloadResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def getcode(self) -> int | None:
        return self.status

    def read(self, limit: int = -1) -> bytes:
        if isinstance(self.payload, BaseException):
            raise self.payload
        end = len(self.payload) if limit < 0 else self.offset + limit
        chunk = self.payload[self.offset : end]
        self.offset += len(chunk)
        return chunk

    def read1(self, limit: int = -1) -> bytes:
        return self.read(limit)

    def set_read_timeout(self, timeout: float) -> None:
        self.read_timeouts.append(timeout)


class SequenceOpener:
    def __init__(self, *results: DownloadResponse | BaseException) -> None:
        self.results = list(results)
        self.calls: list[tuple[str, float | None]] = []

    def __call__(
        self,
        url: str,
        *,
        timeout: float | None = None,
        deadline: float | None = None,
        request_timeout: float | None = None,
    ) -> DownloadResponse:
        del deadline, request_timeout
        self.calls.append((url, timeout))
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


class FakeClock:
    def __init__(self, *, wall_time: float = 0.0) -> None:
        self.elapsed = 0.0
        self.wall_start = wall_time
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.elapsed

    def wall_time(self) -> float:
        return self.wall_start + self.elapsed

    def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        self.elapsed += delay


class _ThreadingScriptServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False

    def __init__(self) -> None:
        self.scripts: queue.Queue[list[tuple[float, bytes]]] = queue.Queue()
        self.requests = 0
        super().__init__(("127.0.0.1", 0), _ScriptedResponseHandler)


class _ScriptedResponseHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        self.server.requests += 1
        request = b""
        while b"\r\n\r\n" not in request:
            chunk = self.request.recv(4096)
            if not chunk:
                return
            request += chunk
        script = self.server.scripts.get(timeout=2)
        for delay, payload in script:
            if delay:
                time.sleep(delay)
            with suppress(OSError):
                self.request.sendall(payload)


class ScriptedReleaseServer:
    def __init__(self) -> None:
        self.server = _ThreadingScriptServer()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> ScriptedReleaseServer:
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def enqueue(self, *parts: tuple[float, bytes]) -> None:
        self.server.scripts.put(list(parts))


def _local_response(
    body: bytes,
    *,
    status: str = "200 OK",
    content_length: int | None = None,
    location: str | None = None,
) -> bytes:
    length = len(body) if content_length is None else content_length
    headers = [f"HTTP/1.1 {status}", f"Content-Length: {length}", "Connection: close"]
    if location is not None:
        headers.append(f"Location: {location}")
    return ("\r\n".join((*headers, "", ""))).encode() + body


def _admit_local_server(monkeypatch: pytest.MonkeyPatch, server: ScriptedReleaseServer) -> None:
    monkeypatch.setattr(release_download, "_approved_url", lambda url: url.startswith(server.base_url))
    monkeypatch.setattr(
        release_download,
        "_approved_redirect",
        lambda source, target: source.startswith(server.base_url) and target.startswith(server.base_url),
    )


def _http_error(status: int, *, retry_after: str | None = None, body: bytes = b"secret body") -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(RELEASE_URL, status, "sensitive upstream detail", headers, io.BytesIO(body))


def _install_network(
    monkeypatch: pytest.MonkeyPatch,
    opener: SequenceOpener,
    clock: FakeClock | None = None,
) -> FakeClock:
    active_clock = FakeClock() if clock is None else clock
    monkeypatch.setattr(release_download, "_stdlib_open", opener)
    monkeypatch.setattr(release_download, "_monotonic", active_clock.monotonic)
    monkeypatch.setattr(release_download, "_wall_time", active_clock.wall_time)
    monkeypatch.setattr(release_download, "_sleep", active_clock.sleep)
    return active_clock


@pytest.mark.parametrize(
    "url",
    [
        RELEASE_URL,
        "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/checksums.txt",
        "https://github.com/google/osv-scanner/releases/download/v2.4.0/osv-scanner_linux_amd64",
        "https://github.com/open-policy-agent/conftest/releases/download/v0.65.0/checksums.txt",
    ],
)
def test_only_expected_github_release_families_are_approved(url: str) -> None:
    assert release_download._approved_url(url)


def test_redirect_policy_admits_only_the_current_github_release_chain() -> None:
    assert release_download._approved_redirect(RELEASE_URL, VALE_CANONICAL_URL)
    assert release_download._approved_redirect(VALE_CANONICAL_URL, RELEASE_ASSET_URL)
    assert release_download._approved_redirect(
        "https://github.com/google/osv-scanner/releases/download/v2.4.0/osv-scanner_linux_amd64",
        RELEASE_ASSET_URL,
    )
    assert not release_download._approved_url(RELEASE_ASSET_URL)
    assert "ephemeral-secret" not in release_download._display_url(RELEASE_ASSET_URL)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (RELEASE_URL, "http://release-assets.githubusercontent.com/github-production-release-asset/1/x?sig=x"),
        (RELEASE_URL, "https://evil.example/github-production-release-asset/1/x?sig=x"),
        (
            RELEASE_URL,
            "https://release-assets.githubusercontent.com/github-production-release-asset/1/not-a-uuid?sig=x",
        ),
        (
            RELEASE_URL,
            "https://release-assets.githubusercontent.com/github-production-release-asset/1/"
            "6307b9db-05dd-4042-9bec-ffb9fe72e4e8",
        ),
        (RELEASE_URL, "https://github.com/vale-cli/vale/releases/download/v3.15.2/different.tar.gz"),
        (RELEASE_URL, "/relative/release-asset"),
        (RELEASE_ASSET_URL, RELEASE_ASSET_URL),
    ],
)
def test_redirect_policy_rejects_scheme_origin_path_and_transition_escape(source: str, target: str) -> None:
    assert not release_download._approved_redirect(source, target)


def test_redirect_policy_rejects_malformed_or_oversized_location_text() -> None:
    assert not release_download._approved_url("https://github.com/\x00tool")
    assert not release_download._approved_canonical_vale_url("\x00")
    assert not release_download._approved_release_asset_url("x" * 20_000)


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/errata-ai/vale/releases/download/v3/vale",
        "https://example.com/errata-ai/vale/releases/download/v3/vale",
        "https://github.com:443/errata-ai/vale/releases/download/v3/vale",
        "https://github.com:invalid/errata-ai/vale/releases/download/v3/vale",
        "https://user@github.com/errata-ai/vale/releases/download/v3/vale",
        "https://github.com/errata-ai/vale/releases/download/v3/vale?token=secret",
        "https://github.com/errata-ai/vale/releases/download/v3/vale#fragment",
        "https://github.com/errata-ai/vale/releases/download/v3\\vale",
        "https://github.com/errata-ai/vale/releases/download/v3/%2e%2e/vale",
        "https://github.com/errata-ai/vale/releases/download/../vale",
        "https://github.com/unknown/tool/releases/download/v1/tool",
    ],
)
def test_unapproved_or_ambiguous_urls_fail_before_network(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
) -> None:
    opener = SequenceOpener(AssertionError("unapproved URL reached the network"))
    _install_network(monkeypatch, opener)

    with pytest.raises(release_download.ReleaseDownloadError, match="not an approved pinned-tool origin"):
        release_download.retrying_urlopen(url)

    assert opener.calls == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_attempts": 0},
        {"request_timeout_seconds": 0},
        {"total_timeout_seconds": 0},
        {"maximum_response_bytes": 0},
        {"initial_backoff_seconds": -1},
        {"maximum_backoff_seconds": -1},
        {"maximum_retry_after_seconds": -1},
        {"maximum_redirects": -1},
    ],
)
def test_retry_policy_rejects_unbounded_or_negative_configuration(overrides: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        release_download.ReleaseRetryPolicy(**overrides)


def test_success_uses_one_finite_request_and_returns_a_context_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = SequenceOpener(DownloadResponse(b"reviewed payload"))
    clock = _install_network(monkeypatch, opener)

    with release_download.retrying_urlopen(RELEASE_URL) as response:
        assert response.read() == b"reviewed payload"

    assert opener.calls == [(RELEASE_URL, 60.0)]
    assert clock.sleeps == []


def test_stdlib_open_installs_deadline_handlers_and_disables_automatic_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = DownloadResponse(b"payload")
    observed: dict[str, object] = {}

    class FakeOpener:
        def __init__(self, *handlers: object) -> None:
            observed["handlers"] = tuple(type(handler).__name__ for handler in handlers)

        def open(self, url: str, *, timeout: float) -> DownloadResponse:
            observed.update(url=url, timeout=timeout)
            return response

    monkeypatch.setattr(release_download, "build_opener", FakeOpener)

    assert release_download._stdlib_open(RELEASE_URL, timeout=12) is response
    assert observed == {
        "handlers": ("_NoRedirectHandler", "_DeadlineHTTPHandler", "_DeadlineHTTPSHandler"),
        "url": RELEASE_URL,
        "timeout": 12,
    }


def test_http_408_429_and_5xx_retry_with_retry_after_then_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = SequenceOpener(
        DownloadResponse(b"do not use", status=503, headers={"Retry-After": "2"}),
        _http_error(408),
        DownloadResponse(b"reviewed payload"),
    )
    clock = _install_network(monkeypatch, opener)

    assert release_download.retrying_urlopen(RELEASE_URL).read() == b"reviewed payload"

    assert len(opener.calls) == 3
    assert clock.sleeps == [2.0, 2.0]


def test_approved_redirect_hops_do_not_read_redirect_bodies(monkeypatch: pytest.MonkeyPatch) -> None:
    redirect = DownloadResponse(
        b"redirect body must remain unread",
        status=302,
        headers={"Location": RELEASE_ASSET_URL, "Content-Length": "30"},
    )
    final = DownloadResponse(b"reviewed", headers={"Content-Length": "8"})
    opener = SequenceOpener(redirect, final)
    _install_network(monkeypatch, opener)

    assert release_download.retrying_urlopen(RELEASE_URL).read() == b"reviewed"
    assert len(opener.calls) == 2
    assert redirect.offset == 0
    assert redirect.read_timeouts == []


@pytest.mark.parametrize(
    ("response", "diagnostic"),
    [
        (DownloadResponse(b"", status=302), "missing or ambiguous Location"),
        (DownloadResponse(b"", status=304), "unsupported redirect status 304"),
        (
            DownloadResponse(b"", status=302, headers={"Location": "https://evil.example/tool"}),
            "unapproved redirect target",
        ),
        (DownloadResponse(b"", status=302, headers={"Location": RELEASE_URL}), "redirect cycle"),
    ],
)
def test_invalid_redirects_fail_once_without_reading_their_bodies(
    monkeypatch: pytest.MonkeyPatch,
    response: DownloadResponse,
    diagnostic: str,
) -> None:
    opener = SequenceOpener(response, DownloadResponse(b"not reached"))
    clock = _install_network(monkeypatch, opener)

    with pytest.raises(release_download.ReleaseDownloadError, match=diagnostic):
        release_download.retrying_urlopen(RELEASE_URL)

    assert len(opener.calls) == 1
    assert response.offset == 0
    assert clock.sleeps == []


def test_duplicate_redirect_location_fails_closed_without_following(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = Message()
    headers["Location"] = RELEASE_ASSET_URL
    headers["Location"] = "https://evil.example/asset"
    response = DownloadResponse(b"not read", status=302, headers=headers)
    opener = SequenceOpener(response, DownloadResponse(b"not reached"))
    _install_network(monkeypatch, opener)

    with pytest.raises(release_download.ReleaseDownloadError, match="missing or ambiguous Location"):
        release_download.retrying_urlopen(RELEASE_URL)

    assert len(opener.calls) == 1
    assert response.offset == 0


def test_redirect_hop_limit_fails_closed_before_following(monkeypatch: pytest.MonkeyPatch) -> None:
    redirect = DownloadResponse(b"", status=302, headers={"Location": RELEASE_ASSET_URL})
    opener = SequenceOpener(redirect, DownloadResponse(b"not reached"))
    _install_network(monkeypatch, opener)
    policy = release_download.ReleaseRetryPolicy(maximum_redirects=0)

    with pytest.raises(release_download.ReleaseDownloadError, match="redirect-hop limit"):
        release_download.retrying_urlopen(RELEASE_URL, policy=policy)

    assert len(opener.calls) == 1


def test_http_date_retry_after_is_honored_and_capped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 8, 12, tzinfo=UTC)
    retry_at = format_datetime(now + timedelta(seconds=120), usegmt=True)
    opener = SequenceOpener(_http_error(429, retry_after=retry_at), DownloadResponse(b"ok"))
    clock = _install_network(monkeypatch, opener, FakeClock(wall_time=now.timestamp()))
    policy = release_download.ReleaseRetryPolicy(maximum_retry_after_seconds=7)

    assert release_download.retrying_urlopen(RELEASE_URL, policy=policy).read() == b"ok"
    assert clock.sleeps == [7]


def test_retry_after_cannot_consume_or_extend_the_total_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = SequenceOpener(_http_error(503, retry_after="999"), DownloadResponse(b"not reached"))
    clock = _install_network(monkeypatch, opener)
    policy = release_download.ReleaseRetryPolicy(
        total_timeout_seconds=3,
        maximum_retry_after_seconds=10,
    )

    with pytest.raises(release_download.ReleaseDownloadError, match="exhausted 1 bounded attempts"):
        release_download.retrying_urlopen(RELEASE_URL, policy=policy)

    assert len(opener.calls) == 1
    assert clock.sleeps == []


def test_transient_exhaustion_has_an_exact_attempt_bound_and_sanitized_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = SequenceOpener(
        TimeoutError("token=first"),
        TimeoutError("token=second"),
        TimeoutError("token=third"),
    )
    clock = _install_network(monkeypatch, opener)

    with pytest.raises(release_download.ReleaseDownloadError) as raised:
        release_download.retrying_urlopen(RELEASE_URL)

    assert len(opener.calls) == 3
    assert clock.sleeps == [1.0, 2.0]
    assert str(raised.value).endswith("exhausted 3 bounded attempts: transport timeout")
    assert "token=" not in str(raised.value)


@pytest.mark.parametrize(
    "failure",
    [
        URLError(TimeoutError("timeout detail")),
        URLError(RemoteDisconnected("disconnect detail")),
        ConnectionResetError("reset detail"),
        BrokenPipeError("pipe detail"),
        IncompleteRead(b"partial", 20),
    ],
)
def test_transport_failures_from_open_or_read_are_retryable(
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
) -> None:
    opener = SequenceOpener(DownloadResponse(failure), DownloadResponse(b"complete"))
    clock = _install_network(monkeypatch, opener)

    assert release_download.retrying_urlopen(RELEASE_URL).read() == b"complete"
    assert len(opener.calls) == 2
    assert clock.sleeps == [1.0]


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 499, 600])
def test_non_retryable_http_statuses_fail_once_without_exposing_body(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    opener = SequenceOpener(_http_error(status, retry_after="1", body=b"credential=do-not-log"))
    clock = _install_network(monkeypatch, opener)

    with pytest.raises(release_download.ReleaseDownloadError) as raised:
        release_download.retrying_urlopen(RELEASE_URL)

    assert len(opener.calls) == 1
    assert clock.sleeps == []
    assert str(raised.value).endswith(f"failed without retry: HTTP {status}")
    assert "credential" not in str(raised.value)


def test_non_timeout_url_error_is_not_retried_or_leaked(monkeypatch: pytest.MonkeyPatch) -> None:
    opener = SequenceOpener(URLError(OSError("dns response with secret")))
    _install_network(monkeypatch, opener)

    with pytest.raises(release_download.ReleaseDownloadError, match="non-retryable URL error") as raised:
        release_download.retrying_urlopen(RELEASE_URL)

    assert len(opener.calls) == 1
    assert "secret" not in str(raised.value)


def test_response_size_failure_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    opener = SequenceOpener(DownloadResponse(b"oversized"), DownloadResponse(b"not reached"))
    clock = _install_network(monkeypatch, opener)
    policy = release_download.ReleaseRetryPolicy(maximum_response_bytes=4)

    with pytest.raises(release_download.ReleaseDownloadSizeError, match="4-byte response limit"):
        release_download.retrying_urlopen(RELEASE_URL, policy=policy)

    assert len(opener.calls) == 1
    assert clock.sleeps == []


def test_declared_length_early_eof_is_retried_from_the_original_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = SequenceOpener(
        DownloadResponse(b"partial", headers={"Content-Length": "8"}),
        DownloadResponse(b"complete", headers={"Content-Length": "8"}),
    )
    clock = _install_network(monkeypatch, opener)

    assert release_download.retrying_urlopen(RELEASE_URL).read() == b"complete"
    assert len(opener.calls) == 2
    assert clock.sleeps == [1.0]


@pytest.mark.parametrize(
    ("headers", "diagnostic"),
    [
        ({"Content-Length": "not-a-number"}, "invalid Content-Length"),
        ({"Content-Length": "9" * 21}, "invalid Content-Length"),
        ({"Content-Length": "4, 5"}, "conflicting Content-Length"),
        ({"Content-Length": "4", "Transfer-Encoding": "chunked"}, "unsupported transfer framing"),
        ({"Transfer-Encoding": "gzip"}, "unsupported transfer framing"),
    ],
)
def test_ambiguous_response_framing_is_not_retried(
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
    diagnostic: str,
) -> None:
    response = DownloadResponse(b"body", headers=headers)
    opener = SequenceOpener(response, DownloadResponse(b"not reached"))
    clock = _install_network(monkeypatch, opener)

    with pytest.raises(release_download.ReleaseDownloadError, match=diagnostic):
        release_download.retrying_urlopen(RELEASE_URL)

    assert len(opener.calls) == 1
    assert response.offset == 0
    assert clock.sleeps == []


def test_duplicate_transfer_encoding_is_rejected_without_body_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = Message()
    headers["Transfer-Encoding"] = "chunked"
    headers["Transfer-Encoding"] = "chunked"
    response = DownloadResponse(b"body", headers=headers)
    opener = SequenceOpener(response, DownloadResponse(b"not reached"))
    _install_network(monkeypatch, opener)

    with pytest.raises(release_download.ReleaseDownloadError, match="unsupported transfer framing"):
        release_download.retrying_urlopen(RELEASE_URL)

    assert len(opener.calls) == 1
    assert response.offset == 0


def test_chunked_response_without_content_length_uses_the_bounded_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = SequenceOpener(DownloadResponse(b"body", headers={"Transfer-Encoding": "chunked"}))
    _install_network(monkeypatch, opener)

    assert release_download.retrying_urlopen(RELEASE_URL).read() == b"body"


def test_response_without_deadline_capable_transport_fails_closed() -> None:
    class NoDeadlineControl:
        headers: dict[str, str] = {}

        def read1(self, _size: int) -> bytes:
            return b""

    response = NoDeadlineControl()
    deadline = time.monotonic() + 1
    with pytest.raises(release_download.ReleaseDownloadError, match="cannot enforce the download deadline"):
        release_download._read_response_body(
            response,
            deadline=deadline,
            request_timeout=1,
            maximum_bytes=1,
        )


def test_deadline_raw_reader_enforces_transport_contract_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FakeClock()
    monkeypatch.setattr(release_download, "_monotonic", clock.monotonic)

    class Raw:
        def __init__(self, result: object = 2) -> None:
            self.result = result
            self.closed = False

        def readinto(self, buffer: bytearray) -> object:
            buffer[:2] = b"ok"
            return self.result

        def fileno(self) -> int:
            return 17

        def close(self) -> None:
            self.closed = True

    class Transport:
        def __init__(self) -> None:
            self.timeouts: list[float] = []

        def settimeout(self, timeout: float) -> None:
            self.timeouts.append(timeout)

    raw = Raw()
    transport = Transport()
    reader = release_download._DeadlineRawReader(
        raw,
        transport,
        deadline=1,
        request_timeout=0.5,
    )
    buffer = bytearray(2)

    assert reader.readable()
    assert reader.readinto(buffer) == 2
    assert buffer == b"ok"
    assert reader.fileno() == 17
    assert transport.timeouts == [0.5]
    reader.close()
    reader.close()
    assert raw.closed

    without_timeout = release_download._DeadlineRawReader(
        Raw(),
        object(),
        deadline=1,
        request_timeout=0.5,
    )
    with pytest.raises(release_download.ReleaseDownloadError, match="cannot enforce"):
        without_timeout.readinto(bytearray(2))

    class NoReader:
        def close(self) -> None:
            pass

    without_reader = release_download._DeadlineRawReader(
        NoReader(),
        Transport(),
        deadline=1,
        request_timeout=0.5,
    )
    with pytest.raises(release_download.ReleaseDownloadError, match="not readable"):
        without_reader.readinto(bytearray(2))

    invalid_count = release_download._DeadlineRawReader(
        Raw("invalid"),
        Transport(),
        deadline=1,
        request_timeout=0.5,
    )
    with pytest.raises(release_download.ReleaseDownloadError, match="invalid byte count"):
        invalid_count.readinto(bytearray(2))


def test_deadline_socket_wraps_binary_readers_and_delegates_other_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FakeClock()
    monkeypatch.setattr(release_download, "_monotonic", clock.monotonic)

    class Raw(io.RawIOBase):
        def readable(self) -> bool:
            return True

        def readinto(self, _buffer: object) -> int:
            return 0

    class Transport:
        marker = "delegated"

        def __init__(self) -> None:
            self.calls: list[tuple[str, int | None, dict[str, object]]] = []

        def makefile(
            self,
            mode: str,
            buffering: int | None = None,
            **kwargs: object,
        ) -> object:
            self.calls.append((mode, buffering, kwargs))
            return Raw() if mode == "rb" else io.BytesIO()

        def settimeout(self, _timeout: float) -> None:
            pass

    transport = Transport()
    wrapped = release_download._DeadlineSocket(
        transport,
        deadline=1,
        request_timeout=0.5,
    )

    assert wrapped.marker == "delegated"
    delegated = wrapped.makefile("wb", 8)
    assert isinstance(delegated, io.BytesIO)
    unbuffered = wrapped.makefile("rb", 0)
    assert isinstance(unbuffered, release_download._DeadlineRawReader)
    unbuffered.close()
    buffered = wrapped.makefile("rb", 16)
    assert isinstance(buffered, io.BufferedReader)
    buffered.close()
    assert transport.calls == [
        ("wb", 8, {}),
        ("rb", 0, {}),
        ("rb", 0, {}),
    ]


def test_deadline_connections_cover_empty_sockets_tunnels_and_https_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Transport:
        def close(self) -> None:
            pass

    http_connection = release_download._DeadlineHTTPConnection(
        "example.test",
        deadline=1,
        request_timeout=0.5,
    )
    monkeypatch.setattr(
        release_download.http_client.HTTPConnection,
        "connect",
        lambda connection: setattr(connection, "sock", None),
    )
    http_connection.connect()
    assert http_connection.sock is None

    https_connection = release_download._DeadlineHTTPSConnection(
        "example.test",
        deadline=1,
        request_timeout=0.5,
    )
    tunnel_sockets: list[object] = []

    def observe_tunnel(connection: object) -> None:
        tunnel_sockets.append(connection.sock)

    monkeypatch.setattr(
        release_download.http_client.HTTPSConnection,
        "_tunnel",
        observe_tunnel,
    )
    https_connection.sock = None
    https_connection._tunnel()
    transport = Transport()
    https_connection.sock = transport
    https_connection._tunnel()
    assert isinstance(tunnel_sockets[1], release_download._DeadlineSocket)
    assert https_connection.sock is transport

    def close_tunnel(connection: object) -> None:
        connection.sock = None

    monkeypatch.setattr(
        release_download.http_client.HTTPSConnection,
        "_tunnel",
        close_tunnel,
    )
    https_connection.sock = transport
    https_connection._tunnel()
    assert https_connection.sock is None

    monkeypatch.setattr(
        release_download.http_client.HTTPSConnection,
        "connect",
        lambda connection: setattr(connection, "sock", transport),
    )
    https_connection.connect()
    assert isinstance(https_connection.sock, release_download._DeadlineSocket)
    monkeypatch.setattr(
        release_download.http_client.HTTPSConnection,
        "connect",
        lambda connection: setattr(connection, "sock", None),
    )
    https_connection.connect()
    assert https_connection.sock is None

    handler = release_download._DeadlineHTTPSHandler(deadline=1, request_timeout=0.5)
    response = DownloadResponse(b"")
    observed: dict[str, object] = {}

    def fake_do_open(factory: object, request: object, **kwargs: object) -> DownloadResponse:
        observed.update(factory=factory, request=request, kwargs=kwargs)
        connection = factory("example.test", timeout=0.5)
        assert isinstance(connection, release_download._DeadlineHTTPSConnection)
        return response

    monkeypatch.setattr(handler, "do_open", fake_do_open)
    request = object()
    assert handler.https_open(request) is response
    assert observed["request"] is request
    assert observed["kwargs"] == {"context": handler._context}


def test_bounded_reader_falls_back_to_read_and_rejects_invalid_readers() -> None:
    class ReadOnly:
        def read(self, _size: int) -> bytes:
            return b"ok"

    class NonBytesReader:
        def read1(self, _size: int) -> str:
            return "not bytes"

    class OverBoundReader:
        def read1(self, size: int) -> bytes:
            return b"x" * (size + 1)

    non_bytes_reader = NonBytesReader()
    over_bound_reader = OverBoundReader()
    assert release_download._read_chunk(ReadOnly(), 2) == b"ok"
    with pytest.raises(release_download.ReleaseDownloadError, match="not readable"):
        release_download._read_chunk(object(), 2)
    with pytest.raises(release_download.ReleaseDownloadError, match="did not return bytes"):
        release_download._read_chunk(non_bytes_reader, 2)
    with pytest.raises(release_download.ReleaseDownloadError, match="requested read bound"):
        release_download._read_chunk(over_bound_reader, 2)


def test_oversized_declared_length_fails_before_body_read(monkeypatch: pytest.MonkeyPatch) -> None:
    response = DownloadResponse(b"body", headers={"Content-Length": "5"})
    opener = SequenceOpener(response)
    _install_network(monkeypatch, opener)
    policy = release_download.ReleaseRetryPolicy(maximum_response_bytes=4)

    with pytest.raises(release_download.ReleaseDownloadSizeError, match="declared 5 bytes"):
        release_download.retrying_urlopen(RELEASE_URL, policy=policy)

    assert response.offset == 0


def test_trickle_body_cannot_extend_the_total_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FakeClock()

    class TrickleResponse(DownloadResponse):
        def read1(self, limit: int = -1) -> bytes:
            clock.elapsed += 0.06
            return super().read1(min(limit, 1))

    opener = SequenceOpener(TrickleResponse(b"ab", headers={"Content-Length": "2"}))
    _install_network(monkeypatch, opener, clock)
    policy = release_download.ReleaseRetryPolicy(max_attempts=1, total_timeout_seconds=0.1)

    with pytest.raises(release_download.ReleaseDownloadError, match="transport timeout"):
        release_download.retrying_urlopen(RELEASE_URL, policy=policy)

    assert len(opener.calls) == 1
    assert clock.elapsed == pytest.approx(0.12)


def test_header_read_cannot_cross_the_total_deadline_and_follow_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FakeClock()
    response = DownloadResponse(
        b"not read",
        status=302,
        headers={"Location": RELEASE_ASSET_URL},
    )

    class DelayedOpener(SequenceOpener):
        def __call__(
            self,
            url: str,
            *,
            timeout: float | None = None,
            deadline: float | None = None,
            request_timeout: float | None = None,
        ) -> DownloadResponse:
            result = super().__call__(
                url,
                timeout=timeout,
                deadline=deadline,
                request_timeout=request_timeout,
            )
            clock.elapsed += 0.11
            return result

    opener = DelayedOpener(response, DownloadResponse(b"not reached"))
    _install_network(monkeypatch, opener, clock)
    policy = release_download.ReleaseRetryPolicy(
        max_attempts=1,
        request_timeout_seconds=1,
        total_timeout_seconds=0.1,
    )

    with pytest.raises(release_download.ReleaseDownloadError, match="transport timeout"):
        release_download.retrying_urlopen(RELEASE_URL, policy=policy)

    assert len(opener.calls) == 1
    assert response.offset == 0


def test_local_server_early_eof_retries_and_never_returns_partial_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with ScriptedReleaseServer() as server:
        _admit_local_server(monkeypatch, server)
        server.enqueue((0, _local_response(b"partial", content_length=8)))
        server.enqueue((0, _local_response(b"complete", content_length=8)))
        policy = release_download.ReleaseRetryPolicy(
            max_attempts=2,
            request_timeout_seconds=0.5,
            total_timeout_seconds=1,
            initial_backoff_seconds=0,
            maximum_backoff_seconds=0,
        )

        assert release_download.retrying_urlopen(f"{server.base_url}/asset", policy=policy).read() == b"complete"
        assert server.server.requests == 2


def test_local_server_redirect_body_is_not_drained_before_next_hop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with ScriptedReleaseServer() as server:
        _admit_local_server(monkeypatch, server)
        final_url = f"{server.base_url}/final"
        redirect_headers = _local_response(
            b"",
            status="302 Found",
            content_length=1_000_000,
            location=final_url,
        )
        server.enqueue((0, redirect_headers), (1, b"x" * 1024))
        server.enqueue((0, _local_response(b"final")))
        policy = release_download.ReleaseRetryPolicy(
            request_timeout_seconds=0.25,
            total_timeout_seconds=1,
        )

        result = release_download.retrying_urlopen(f"{server.base_url}/redirect", policy=policy).read()

        assert result == b"final"
        assert server.server.requests == 2


def test_local_server_trickle_read_is_cut_off_by_total_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with ScriptedReleaseServer() as server:
        _admit_local_server(monkeypatch, server)
        server.enqueue(
            (0, _local_response(b"a", content_length=3)),
            (0.08, b"b"),
            (0.08, b"c"),
        )
        policy = release_download.ReleaseRetryPolicy(
            max_attempts=1,
            request_timeout_seconds=1,
            total_timeout_seconds=0.12,
        )

        with pytest.raises(release_download.ReleaseDownloadError, match="transport timeout"):
            release_download.retrying_urlopen(f"{server.base_url}/trickle", policy=policy)

        assert server.server.requests == 1


def test_local_server_trickled_redirect_headers_are_cut_off_by_total_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with ScriptedReleaseServer() as server:
        _admit_local_server(monkeypatch, server)
        final_url = f"{server.base_url}/final"
        response = _local_response(
            b"",
            status="302 Found",
            location=final_url,
        )
        pieces = [response[index : index + 10] for index in range(0, len(response), 10)]
        server.enqueue(*((0 if index == 0 else 0.04, piece) for index, piece in enumerate(pieces)))
        policy = release_download.ReleaseRetryPolicy(
            max_attempts=1,
            request_timeout_seconds=0.08,
            total_timeout_seconds=0.12,
        )

        started = time.monotonic()
        with pytest.raises(release_download.ReleaseDownloadError, match="transport timeout"):
            release_download.retrying_urlopen(f"{server.base_url}/redirect", policy=policy)
        elapsed = time.monotonic() - started

        assert elapsed < 0.3
        assert server.server.requests == 1


def test_local_server_trickled_chunk_trailer_is_cut_off_by_total_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with ScriptedReleaseServer() as server:
        _admit_local_server(monkeypatch, server)
        prefix = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n1\r\na\r\n0\r\n"
        trailer = b"X-Review: " + (b"x" * 80) + b"\r\n\r\n"
        trailer_pieces = [trailer[index : index + 10] for index in range(0, len(trailer), 10)]
        server.enqueue(
            (0, prefix),
            *((0.04, piece) for piece in trailer_pieces),
        )
        policy = release_download.ReleaseRetryPolicy(
            max_attempts=1,
            request_timeout_seconds=0.08,
            total_timeout_seconds=0.12,
        )

        started = time.monotonic()
        with pytest.raises(release_download.ReleaseDownloadError, match="transport timeout"):
            release_download.retrying_urlopen(f"{server.base_url}/chunked", policy=policy)
        elapsed = time.monotonic() - started

        assert elapsed < 0.3
        assert server.server.requests == 1


def test_malformed_status_line_is_sanitized_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with ScriptedReleaseServer() as server:
        _admit_local_server(monkeypatch, server)
        server.enqueue((0, b"credential=do-not-log\r\n\r\n"))
        policy = release_download.ReleaseRetryPolicy(
            max_attempts=2,
            request_timeout_seconds=0.5,
            total_timeout_seconds=1,
        )

        with pytest.raises(
            release_download.ReleaseDownloadError,
            match="invalid HTTP response",
        ) as raised:
            release_download.retrying_urlopen(f"{server.base_url}/malformed", policy=policy)

        assert "credential" not in str(raised.value)
        assert server.server.requests == 1


def test_invalid_per_call_timeout_fails_before_network(monkeypatch: pytest.MonkeyPatch) -> None:
    opener = SequenceOpener(AssertionError("invalid timeout reached the network"))
    _install_network(monkeypatch, opener)

    with pytest.raises(ValueError, match="timeout must be positive"):
        release_download.retrying_urlopen(RELEASE_URL, timeout=0)

    assert opener.calls == []


def test_retry_after_parser_rejects_ambiguous_values() -> None:
    assert release_download._retry_after_seconds({}, now=0) is None
    assert release_download._retry_after_seconds(object(), now=0) is None
    assert release_download._retry_after_seconds({"Retry-After": object()}, now=0) is None
    assert release_download._retry_after_seconds({"Retry-After": "x" * 129}, now=0) is None
    assert release_download._retry_after_seconds({"Retry-After": "not-a-date"}, now=0) is None
    assert release_download._retry_after_seconds({"Retry-After": "7"}, now=0) == 7
    naive_date = "Wed, 12 Aug 2026 00:00:00"
    expected = datetime(2026, 8, 12, tzinfo=UTC).timestamp()
    assert release_download._retry_after_seconds({"Retry-After": naive_date}, now=0) == expected


def test_response_status_falls_back_to_getcode_or_none() -> None:
    class GetCodeOnly:
        def getcode(self) -> int:
            return 204

    assert release_download._response_status(GetCodeOnly()) == 204
    assert release_download._response_status(object()) is None


def test_unknown_failure_kind_has_a_stable_fallback() -> None:
    assert release_download._failure_kind(ValueError("sensitive detail")) == "download failure"


def test_expired_total_deadline_makes_no_network_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    opener = SequenceOpener(AssertionError("expired deadline reached the network"))
    _install_network(monkeypatch, opener)
    moments = iter((0.0, release_download.DEFAULT_RELEASE_RETRY_POLICY.total_timeout_seconds))
    monkeypatch.setattr(release_download, "_monotonic", lambda: next(moments))

    with pytest.raises(release_download.ReleaseDownloadError, match="exhausted 0 bounded attempts: total timeout"):
        release_download.retrying_urlopen(RELEASE_URL)

    assert opener.calls == []


def test_all_checksum_verified_release_installers_share_the_retry_boundary() -> None:
    assert conftest_tool.urlopen is release_download.retrying_urlopen
    assert vale_tool.urlopen is release_download.retrying_urlopen
    assert gitleaks_tool.urlopen is release_download.retrying_urlopen
    assert osv_scanner_tool.urlopen is release_download.retrying_urlopen


@pytest.mark.parametrize(
    ("tool", "ensure", "diagnostic"),
    [
        (conftest_tool, conftest_tool.ensure_conftest, "failed to download conftest"),
        (vale_tool, vale_tool.ensure_vale, "failed to download Vale"),
        (gitleaks_tool, gitleaks_tool.ensure_gitleaks, "failed to download gitleaks"),
        (osv_scanner_tool, osv_scanner_tool.ensure_osv_scanner, "failed to download osv-scanner"),
    ],
)
@pytest.mark.parametrize(
    "detail",
    [
        "exhausted 3 bounded attempts: HTTP 503",
        "failed without retry: HTTP 404",
    ],
)
def test_installers_wrap_retry_failures_with_tool_specific_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tool: ModuleType,
    ensure: Callable[[Path], Path],
    diagnostic: str,
    detail: str,
) -> None:
    calls = 0

    def fail(_url: str, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise release_download.ReleaseDownloadError(detail)

    monkeypatch.setattr(tool, "urlopen", fail)

    with pytest.raises(RuntimeError, match=diagnostic) as raised:
        ensure(tmp_path)

    assert calls == 1
    assert detail in str(raised.value)


@pytest.mark.parametrize(
    ("tool", "ensure", "asset_name", "diagnostic"),
    [
        (
            conftest_tool,
            conftest_tool.ensure_conftest,
            conftest_tool._release_asset_name,
            "failed to download conftest from",
        ),
        (
            gitleaks_tool,
            gitleaks_tool.ensure_gitleaks,
            gitleaks_tool._release_asset_name,
            "failed to download gitleaks from",
        ),
    ],
)
def test_checksum_metadata_installers_wrap_asset_stage_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tool: ModuleType,
    ensure: Callable[[Path], Path],
    asset_name: Callable[[], str],
    diagnostic: str,
) -> None:
    checksum_metadata = f"{'0' * 64}  {asset_name()}\n".encode()
    detail = "exhausted 3 bounded attempts: HTTP 503"
    opener = SequenceOpener(
        DownloadResponse(checksum_metadata),
        DownloadResponse(release_download.ReleaseDownloadError(detail)),
    )
    monkeypatch.setattr(tool, "urlopen", opener)

    with pytest.raises(RuntimeError, match=diagnostic) as raised:
        ensure(tmp_path)

    assert len(opener.calls) == 2
    assert detail in str(raised.value)


def test_checksum_mismatch_is_not_retried(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    opener = SequenceOpener(DownloadResponse(b"corrupt archive"), DownloadResponse(b"not reached"))
    clock = _install_network(monkeypatch, opener)

    with pytest.raises(RuntimeError, match="Vale checksum mismatch"):
        vale_tool.ensure_vale(tmp_path)

    assert len(opener.calls) == 1
    assert clock.sleeps == []


def test_archive_type_failure_after_valid_digest_is_not_retried(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = b"not a tar archive"
    asset_name = vale_tool._release_asset_name()
    monkeypatch.setattr(vale_tool, "VALE_ARCHIVE_SHA256", {asset_name: sha256(payload).hexdigest()})
    opener = SequenceOpener(DownloadResponse(payload), DownloadResponse(b"not reached"))
    clock = _install_network(monkeypatch, opener)

    with pytest.raises(ReadError, match="not a gzip file"):
        vale_tool.ensure_vale(tmp_path)

    assert len(opener.calls) == 1
    assert clock.sleeps == []
