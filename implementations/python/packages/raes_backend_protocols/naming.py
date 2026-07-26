"""Deterministic provider-name derivation from compiler-owned addresses."""

from __future__ import annotations

import hashlib
import re

from raes_contracts.addressing import require_compiled_address

_UNSAFE_PROVIDER_NAME = re.compile(r"[^a-z0-9_.-]+", re.ASCII)
_DIGEST_LENGTH = 12


def provider_resource_name(
    address: str,
    *,
    prefix: str = "",
    maximum_length: int = 63,
) -> str:
    """Return a bounded readable name whose suffix commits to *address*."""

    require_compiled_address(address)
    if isinstance(maximum_length, bool) or not isinstance(maximum_length, int) or maximum_length < 16:
        raise ValueError("provider resource name maximum_length must be an integer >= 16")
    digest = hashlib.sha256(address.encode("utf-8")).hexdigest()[:_DIGEST_LENGTH]
    readable = _UNSAFE_PROVIDER_NAME.sub("-", address.lower()).strip("-._") or "resource"
    safe_prefix = _UNSAFE_PROVIDER_NAME.sub("-", prefix.lower()).strip("-._")
    if safe_prefix:
        readable = f"{safe_prefix}-{readable}"
    suffix = f"-{digest}"
    readable_budget = maximum_length - len(suffix)
    head = readable[:readable_budget].rstrip("-._") or "resource"[:readable_budget]
    return f"{head}{suffix}"


__all__ = ["provider_resource_name"]
