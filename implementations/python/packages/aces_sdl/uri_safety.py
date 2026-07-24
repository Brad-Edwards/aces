"""Shared pure checks for secret-bearing absolute URIs."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlsplit

SECRET_QUERY_NAMES = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "credential",
        "key",
        "password",
        "secret",
        "sig",
        "signature",
        "token",
    }
)
SECRET_QUERY_FRAGMENTS = (
    "api-key",
    "api_key",
    "apikey",
    "credential",
    "password",
    "secret",
    "signature",
    "token",
)


def _secret_query_names(query: str) -> set[str]:
    query_names = {name.casefold() for name, _value in parse_qsl(query, keep_blank_values=True)}
    return {
        name
        for name in query_names
        if name in SECRET_QUERY_NAMES or any(fragment in name for fragment in SECRET_QUERY_FRAGMENTS)
    }


def unsafe_absolute_uri_reason(uri: str) -> str | None:
    """Return a bounded reason when an absolute URI is invalid or secret-bearing."""

    parsed = urlsplit(uri)
    reason = None
    if not parsed.scheme or (parsed.scheme in {"http", "https"} and not parsed.netloc):
        reason = "must be an absolute URI"
    elif parsed.username is not None or parsed.password is not None:
        reason = "must not contain credential userinfo"
    elif _secret_query_names(parsed.query):
        reason = "must not contain secret-bearing query fields"
    return reason


__all__ = ["SECRET_QUERY_FRAGMENTS", "SECRET_QUERY_NAMES", "unsafe_absolute_uri_reason"]
