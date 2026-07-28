"""Dependency-neutral RFC 8785 (JCS) + SHA-256 canonical digest helpers.

Extracted so every closed contract shares one canonicalizer instead of minting
its own trial-plan or evidence serializer. ``canonical_contract_digest`` (in
:mod:`raes_contracts.satisfiability`) and the admitted trial-plan integrity
chain both route through here, keeping RFC 8785 canonicalization and the
``sha256:`` digest prefix identical across contracts.
"""

from __future__ import annotations

import hashlib

import rfc8785

#: A JSON value produced by ``model_dump(mode="json")`` — the only input these
#: canonicalizers accept.
JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


def canonical_json_bytes(payload: JsonValue) -> bytes:
    """Return the RFC 8785 (JCS) canonical byte encoding of a JSON-able payload."""

    return rfc8785.dumps(payload)


def canonical_json_digest(payload: JsonValue) -> str:
    """Return the ``sha256:``-prefixed JCS SHA-256 digest of a JSON-able payload.

    The payload must already be JSON-compatible (e.g. ``model_dump(mode="json")``).
    """

    return "sha256:" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
