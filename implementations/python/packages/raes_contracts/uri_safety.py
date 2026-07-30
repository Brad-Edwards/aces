"""Dependency-neutral validation for inert, secret-safe absolute URI fields."""

from __future__ import annotations

from collections.abc import Collection
from urllib.parse import parse_qsl, urlsplit

_SECRET_QUERY_NAMES = frozenset(
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
_SECRET_QUERY_FRAGMENTS = (
    "api-key",
    "api_key",
    "apikey",
    "credential",
    "password",
    "secret",
    "signature",
    "token",
)


def _is_absolute_uri(scheme: str, netloc: str) -> bool:
    return bool(scheme) and (scheme not in {"http", "https"} or bool(netloc))


def _has_secret_query_field(query: str) -> bool:
    query_names = {name.casefold() for name, _value in parse_qsl(query, keep_blank_values=True)}
    return any(
        name in _SECRET_QUERY_NAMES or any(fragment in name for fragment in _SECRET_QUERY_FRAGMENTS)
        for name in query_names
    )


def validate_safe_absolute_uri(
    uri: str,
    *,
    field_name: str,
    forbidden_schemes: Collection[str] = (),
    forbid_fragment: bool = False,
) -> None:
    """Reject relative or credential-bearing URIs without dereferencing them."""

    parsed = urlsplit(uri)
    scheme = parsed.scheme.casefold()
    if not _is_absolute_uri(scheme, parsed.netloc):
        raise ValueError(f"{field_name} must be an absolute URI")
    if scheme in {value.casefold() for value in forbidden_schemes}:
        raise ValueError(f"{field_name} uses a forbidden URI scheme")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{field_name} must not contain credential userinfo")
    if forbid_fragment and parsed.fragment:
        raise ValueError(f"{field_name} must not contain a fragment")
    if _has_secret_query_field(parsed.query):
        raise ValueError(f"{field_name} must not contain secret-bearing query fields")


__all__ = ["validate_safe_absolute_uri"]
