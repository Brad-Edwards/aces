"""Bounded acquisition for checksum-pinned GitHub Release tooling."""

from __future__ import annotations

import io
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC
from email.utils import parsedate_to_datetime
from http.client import IncompleteRead, RemoteDisconnected
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.parse import SplitResult, urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

_APPROVED_RELEASE_PATH_PREFIXES = (
    "/errata-ai/vale/releases/download/",
    "/gitleaks/gitleaks/releases/download/",
    "/google/osv-scanner/releases/download/",
    "/open-policy-agent/conftest/releases/download/",
)
_VALE_LEGACY_PATH_PREFIX = "/errata-ai/vale/releases/download/"
_VALE_CANONICAL_PATH_PREFIX = "/vale-cli/vale/releases/download/"
_RELEASE_ASSET_PATH = re.compile(
    r"^/github-production-release-asset/[0-9]+/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECT_LOCATION_CHARS = 16 * 1024
_READ_CHUNK_BYTES = 64 * 1024


class ReleaseDownloadError(RuntimeError):
    """A fail-closed release acquisition failure with a stable diagnostic."""


class ReleaseDownloadSizeError(ReleaseDownloadError):
    """A release response exceeded its repository-defined byte bound."""


@dataclass(frozen=True)
class ReleaseRetryPolicy:
    """Deterministic request, retry, and response bounds for release assets."""

    max_attempts: int = 3
    request_timeout_seconds: float = 60.0
    total_timeout_seconds: float = 190.0
    initial_backoff_seconds: float = 1.0
    maximum_backoff_seconds: float = 4.0
    maximum_retry_after_seconds: float = 10.0
    maximum_response_bytes: int = 256 * 1024 * 1024
    maximum_redirects: int = 3

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        positive_values = (
            self.request_timeout_seconds,
            self.total_timeout_seconds,
            self.maximum_response_bytes,
        )
        if any(value <= 0 for value in positive_values):
            raise ValueError(
                "request, total-time, and response bounds must be positive"
            )
        delay_values = (
            self.initial_backoff_seconds,
            self.maximum_backoff_seconds,
            self.maximum_retry_after_seconds,
        )
        if any(value < 0 for value in delay_values):
            raise ValueError("retry delays must not be negative")
        if self.maximum_redirects < 0:
            raise ValueError("maximum_redirects must not be negative")


DEFAULT_RELEASE_RETRY_POLICY = ReleaseRetryPolicy()

_monotonic = time.monotonic
_sleep = time.sleep
_wall_time = time.time


class _ReturnedHttpError(Exception):
    """An HTTP error response returned by a non-standard opener."""

    def __init__(self, status: int, headers: object) -> None:
        self.status = status
        self.headers = headers


@dataclass(frozen=True)
class _RedirectHop:
    location: str


class _NoRedirectHandler(HTTPRedirectHandler):
    """Return redirect headers without following or draining their bodies."""

    def _return_response(
        self,
        _request: object,
        response: BinaryIO,
        _code: int,
        _message: str,
        _headers: object,
    ) -> BinaryIO:
        return response

    http_error_301 = _return_response
    http_error_302 = _return_response
    http_error_303 = _return_response
    http_error_307 = _return_response
    http_error_308 = _return_response


@dataclass(frozen=True)
class _AttemptFailure:
    kind: str
    retryable: bool
    retry_after_seconds: float | None


def _parsed_url_with_port(url: str) -> tuple[SplitResult, int | None] | None:
    if (
        not isinstance(url, str)
        or len(url) > _MAX_REDIRECT_LOCATION_CHARS
        or any(ord(char) < 32 for char in url)
    ):
        return None
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (TypeError, ValueError):
        return None
    return parsed, port


def _approved_authority(parsed: SplitResult, port: int | None) -> bool:
    return not (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    )


def _safe_release_path(path: str) -> bool:
    path_parts = path.split("/")
    normalized_path = path.lower()
    return (
        "\\" not in path
        and "%" not in normalized_path
        and all(part not in {".", ".."} for part in path_parts)
    )


def _approved_release_path(path: str) -> bool:
    return _safe_release_path(path) and any(
        path.startswith(prefix) for prefix in _APPROVED_RELEASE_PATH_PREFIXES
    )


def _approved_url(url: str) -> bool:
    parsed_with_port = _parsed_url_with_port(url)
    if parsed_with_port is None:
        return False
    parsed, port = parsed_with_port
    return _approved_authority(parsed, port) and _approved_release_path(parsed.path)


def _approved_canonical_vale_url(url: str) -> bool:
    parsed_with_port = _parsed_url_with_port(url)
    if parsed_with_port is None:
        return False
    parsed, port = parsed_with_port
    return (
        _approved_authority(parsed, port)
        and _safe_release_path(parsed.path)
        and parsed.path.startswith(_VALE_CANONICAL_PATH_PREFIX)
    )


def _approved_release_asset_url(url: str) -> bool:
    parsed_with_port = _parsed_url_with_port(url)
    if parsed_with_port is None:
        return False
    parsed, port = parsed_with_port
    return (
        parsed.scheme == "https"
        and parsed.hostname == "release-assets.githubusercontent.com"
        and port is None
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
        and bool(parsed.query)
        and _RELEASE_ASSET_PATH.fullmatch(parsed.path) is not None
    )


def _approved_vale_relocation(source_url: str, target_url: str) -> bool:
    source = urlsplit(source_url)
    target = urlsplit(target_url)
    if not source.path.startswith(_VALE_LEGACY_PATH_PREFIX):
        return False
    source_suffix = source.path.removeprefix("/errata-ai/vale")
    target_suffix = target.path.removeprefix("/vale-cli/vale")
    return _approved_canonical_vale_url(target_url) and source_suffix == target_suffix


def _approved_redirect(source_url: str, target_url: str) -> bool:
    if _approved_vale_relocation(source_url, target_url):
        return True
    source_is_github_release = _approved_url(
        source_url
    ) or _approved_canonical_vale_url(source_url)
    return source_is_github_release and _approved_release_asset_url(target_url)


def _display_url(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.hostname or 'unapproved-host'}{parsed.path}"


def _response_status(response: object) -> int | None:
    status = getattr(response, "status", None)
    if status is None:
        getcode = getattr(response, "getcode", None)
        status = getcode() if callable(getcode) else None
    return status if isinstance(status, int) else None


def _header_value(headers: object, name: str) -> str | None:
    get = getattr(headers, "get", None)
    if not callable(get):
        return None
    value = get(name)
    return value if isinstance(value, str) else None


def _http_date_delay(value: str, *, now: float) -> float | None:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return max(0.0, parsed.timestamp() - now)


def _retry_after_seconds(headers: object, *, now: float) -> float | None:
    value = _header_value(headers, "Retry-After")
    if value is None or len(value) > 128:
        return None
    value = value.strip()
    if value.isascii() and value.isdecimal():
        return float(value)
    return _http_date_delay(value, now=now)


def _http_status(exc: BaseException) -> int | None:
    if isinstance(exc, HTTPError):
        return exc.code
    if isinstance(exc, _ReturnedHttpError):
        return exc.status
    return None


def _http_headers(exc: BaseException) -> object | None:
    if isinstance(exc, HTTPError):
        return exc.headers
    if isinstance(exc, _ReturnedHttpError):
        return exc.headers
    return None


def _transport_reason(exc: BaseException) -> BaseException:
    if isinstance(exc, URLError) and isinstance(exc.reason, BaseException):
        return exc.reason
    return exc


def _is_retryable(exc: BaseException) -> bool:
    status = _http_status(exc)
    if status is not None:
        return status in {408, 429} or 500 <= status <= 599
    reason = _transport_reason(exc)
    return isinstance(
        reason,
        (TimeoutError, ConnectionError, IncompleteRead),
    )


def _failure_kind(exc: BaseException) -> str:
    status = _http_status(exc)
    if status is not None:
        kind = f"HTTP {status}"
    else:
        reason = _transport_reason(exc)
        kind = "download failure"
        if isinstance(reason, TimeoutError):
            kind = "transport timeout"
        elif isinstance(reason, RemoteDisconnected):
            kind = "remote disconnect"
        elif isinstance(reason, IncompleteRead):
            kind = "incomplete response"
        elif isinstance(reason, ConnectionError):
            kind = "connection failure"
        elif isinstance(exc, URLError):
            kind = "non-retryable URL error"
    return kind


def _classified_failure(exc: BaseException) -> _AttemptFailure:
    headers = _http_headers(exc)
    retry_after = (
        None if headers is None else _retry_after_seconds(headers, now=_wall_time())
    )
    return _AttemptFailure(
        kind=_failure_kind(exc),
        retryable=_is_retryable(exc),
        retry_after_seconds=retry_after,
    )


def _retry_delay(
    failure: _AttemptFailure, *, failed_attempt: int, policy: ReleaseRetryPolicy
) -> float:
    if failure.retry_after_seconds is not None:
        return min(failure.retry_after_seconds, policy.maximum_retry_after_seconds)
    exponential = policy.initial_backoff_seconds * (2 ** (failed_attempt - 1))
    return min(exponential, policy.maximum_backoff_seconds)


def _stdlib_open(url: str, *, timeout: float) -> BinaryIO:
    return build_opener(_NoRedirectHandler()).open(url, timeout=timeout)


def _remaining_timeout(*, deadline: float, request_timeout: float) -> float:
    remaining = deadline - _monotonic()
    if remaining <= 0:
        raise TimeoutError("release download deadline expired")
    return min(request_timeout, remaining)


def _header_values(headers: object, name: str) -> tuple[str, ...]:
    get_all = getattr(headers, "get_all", None)
    if callable(get_all):
        values = get_all(name, [])
        return tuple(value for value in values if isinstance(value, str))
    value = _header_value(headers, name)
    return () if value is None else (value,)


def _declared_content_length(headers: object) -> int | None:
    tokens = tuple(
        token.strip()
        for value in _header_values(headers, "Content-Length")
        for token in value.split(",")
    )
    if not tokens:
        return None
    if any(
        len(token) > 20 or not token.isascii() or not token.isdecimal()
        for token in tokens
    ):
        raise ReleaseDownloadError("release response has an invalid Content-Length")
    lengths = {int(token) for token in tokens}
    if len(lengths) != 1:
        raise ReleaseDownloadError(
            "release response has conflicting Content-Length values"
        )
    return lengths.pop()


def _validate_transfer_encoding(headers: object, declared_length: int | None) -> None:
    tokens = tuple(
        token.strip().lower()
        for value in _header_values(headers, "Transfer-Encoding")
        for token in value.split(",")
    )
    if not tokens:
        return
    if tokens != ("chunked",) or declared_length is not None:
        raise ReleaseDownloadError(
            "release response has an unsupported transfer framing"
        )


def _response_timeout_setter(response: object) -> Callable[[float], object] | None:
    explicit_setter = getattr(response, "set_read_timeout", None)
    if callable(explicit_setter):
        return explicit_setter
    buffered = getattr(response, "fp", None)
    raw = getattr(buffered, "raw", None)
    transport = getattr(raw, "_sock", None)
    setter = getattr(transport, "settimeout", None)
    return setter if callable(setter) else None


def _set_response_timeout(response: object, timeout: float) -> None:
    setter = _response_timeout_setter(response)
    if setter is None:
        raise ReleaseDownloadError(
            "release response transport cannot enforce the download deadline"
        )
    setter(timeout)


def _read_chunk(response: object, size: int) -> bytes:
    read = getattr(response, "read1", None)
    if not callable(read):
        read = getattr(response, "read", None)
    if not callable(read):
        raise ReleaseDownloadError("release response body is not readable")
    chunk = read(size)
    if not isinstance(chunk, bytes):
        raise ReleaseDownloadError("release response body did not return bytes")
    if len(chunk) > size:
        raise ReleaseDownloadError(
            "release response body exceeded its requested read bound"
        )
    return chunk


def _next_read_size(
    *, payload_size: int, declared_length: int | None, maximum_bytes: int
) -> int:
    remaining_capacity = maximum_bytes - payload_size
    if declared_length is None:
        return min(_READ_CHUNK_BYTES, remaining_capacity + 1)
    return min(_READ_CHUNK_BYTES, declared_length - payload_size)


def _read_response_body(
    response: object,
    *,
    deadline: float,
    request_timeout: float,
    maximum_bytes: int,
) -> bytes:
    headers = getattr(response, "headers", {})
    declared_length = _declared_content_length(headers)
    _validate_transfer_encoding(headers, declared_length)
    if declared_length is not None and declared_length > maximum_bytes:
        raise ReleaseDownloadSizeError(
            f"release response declared {declared_length} bytes, above the {maximum_bytes}-byte limit"
        )

    payload = bytearray()
    while declared_length is None or len(payload) < declared_length:
        read_size = _next_read_size(
            payload_size=len(payload),
            declared_length=declared_length,
            maximum_bytes=maximum_bytes,
        )
        timeout = _remaining_timeout(deadline=deadline, request_timeout=request_timeout)
        _set_response_timeout(response, timeout)
        chunk = _read_chunk(response, read_size)
        _remaining_timeout(deadline=deadline, request_timeout=request_timeout)
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > maximum_bytes:
            raise ReleaseDownloadSizeError(
                f"release response exceeded the {maximum_bytes}-byte response limit"
            )

    if declared_length is not None and len(payload) != declared_length:
        raise IncompleteRead(bytes(payload), declared_length - len(payload))
    return bytes(payload)


def _request_hop(
    url: str,
    *,
    deadline: float,
    request_timeout: float,
    maximum_bytes: int,
) -> bytes | _RedirectHop:
    timeout = _remaining_timeout(deadline=deadline, request_timeout=request_timeout)
    with _stdlib_open(url, timeout=timeout) as response:
        _remaining_timeout(deadline=deadline, request_timeout=request_timeout)
        status = _response_status(response)
        if status in _REDIRECT_STATUSES:
            locations = _header_values(getattr(response, "headers", {}), "Location")
            if len(locations) != 1:
                raise ReleaseDownloadError(
                    "release redirect has a missing or ambiguous Location header"
                )
            return _RedirectHop(locations[0])
        if status is not None and 300 <= status <= 399:
            raise ReleaseDownloadError(
                f"release response used unsupported redirect status {status}"
            )
        if status is not None and status >= 400:
            raise _ReturnedHttpError(status, getattr(response, "headers", {}))
        return _read_response_body(
            response,
            deadline=deadline,
            request_timeout=request_timeout,
            maximum_bytes=maximum_bytes,
        )


def _download_once(
    url: str,
    *,
    deadline: float,
    request_timeout: float,
    policy: ReleaseRetryPolicy,
) -> bytes:
    current_url = url
    visited = {url}
    redirects_followed = 0
    while True:
        outcome = _request_hop(
            current_url,
            deadline=deadline,
            request_timeout=request_timeout,
            maximum_bytes=policy.maximum_response_bytes,
        )
        if isinstance(outcome, bytes):
            return outcome
        if redirects_followed >= policy.maximum_redirects:
            raise ReleaseDownloadError(
                "release download exceeded the approved redirect-hop limit"
            )
        target_url = outcome.location
        if target_url in visited:
            raise ReleaseDownloadError("release download encountered a redirect cycle")
        if not _approved_redirect(current_url, target_url):
            raise ReleaseDownloadError(
                "release download encountered an unapproved redirect target"
            )
        visited.add(target_url)
        current_url = target_url
        redirects_followed += 1


def _download_attempt(
    url: str,
    *,
    deadline: float,
    request_timeout: float,
    policy: ReleaseRetryPolicy,
) -> bytes | _AttemptFailure:
    try:
        return _download_once(
            url,
            deadline=deadline,
            request_timeout=request_timeout,
            policy=policy,
        )
    except (
        URLError,
        TimeoutError,
        ConnectionError,
        IncompleteRead,
        _ReturnedHttpError,
    ) as exc:
        failure = _classified_failure(exc)
        if isinstance(exc, HTTPError):
            exc.close()
        return failure


def _wait_for_retry(
    failure: _AttemptFailure,
    *,
    failed_attempt: int,
    deadline: float,
    policy: ReleaseRetryPolicy,
) -> bool:
    delay = _retry_delay(failure, failed_attempt=failed_attempt, policy=policy)
    if delay >= deadline - _monotonic():
        return False
    _sleep(delay)
    return True


def retrying_urlopen(
    url: str,
    *,
    timeout: float | None = None,
    policy: ReleaseRetryPolicy = DEFAULT_RELEASE_RETRY_POLICY,
) -> BinaryIO:
    """Download one approved release URL into a bounded in-memory response.

    Only transient transport failures and HTTP 408, 429, and 5xx responses are
    retried. Validation remains in each caller, so digest, archive, signature,
    type, and identity failures cannot trigger another network attempt.
    """

    if not _approved_url(url):
        raise ReleaseDownloadError(
            "release download URL is not an approved pinned-tool origin"
        )
    request_timeout = policy.request_timeout_seconds if timeout is None else timeout
    if request_timeout <= 0:
        raise ValueError("timeout must be positive")

    deadline = _monotonic() + policy.total_timeout_seconds
    attempts_made = 0
    last_failure = "total timeout"
    for next_attempt in range(1, policy.max_attempts + 1):
        remaining = deadline - _monotonic()
        if remaining <= 0:
            break
        attempts_made = next_attempt
        outcome = _download_attempt(
            url,
            deadline=deadline,
            request_timeout=request_timeout,
            policy=policy,
        )
        if isinstance(outcome, bytes):
            return io.BytesIO(outcome)
        last_failure = outcome.kind
        if not outcome.retryable:
            raise ReleaseDownloadError(
                f"release download from {_display_url(url)} failed without retry: {last_failure}"
            ) from None
        if attempts_made < policy.max_attempts and not _wait_for_retry(
            outcome,
            failed_attempt=attempts_made,
            deadline=deadline,
            policy=policy,
        ):
            break

    raise ReleaseDownloadError(
        f"release download from {_display_url(url)} exhausted {attempts_made} bounded attempts: {last_failure}"
    ) from None
