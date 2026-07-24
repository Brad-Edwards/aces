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


def unsafe_absolute_uri_reason(uri: str) -> str | None:
    """Return a bounded reason when an absolute URI is invalid or secret-bearing."""

    parsed = urlsplit(uri)
    if not parsed.scheme or (parsed.scheme in {"http", "https"} and not parsed.netloc):
        return "must be an absolute URI"
    if parsed.username is not None or parsed.password is not None:
        return "must not contain credential userinfo"
    query_names = {name.casefold() for name, _value in parse_qsl(parsed.query, keep_blank_values=True)}
    secret_names = {
        name
        for name in query_names
        if name in SECRET_QUERY_NAMES or any(fragment in name for fragment in SECRET_QUERY_FRAGMENTS)
    }
    if secret_names:
        return "must not contain secret-bearing query fields"
    return None


__all__ = ["SECRET_QUERY_FRAGMENTS", "SECRET_QUERY_NAMES", "unsafe_absolute_uri_reason"]
