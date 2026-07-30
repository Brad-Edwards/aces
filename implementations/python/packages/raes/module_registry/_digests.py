"""Digest and version-matching helpers for module resolution."""

from __future__ import annotations

import hashlib
import json

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

# Canonical prefix for the SHA-256 digests used throughout module resolution and
# publishing (manifest / config / bundle / content digests).
_SHA256_PREFIX = "sha256:"


def _sha256_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _descriptor_digest(exports: dict[str, list[str]]) -> str:
    return _sha256_digest(json.dumps(exports, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _normalize_exact_or_range(version: str) -> SpecifierSet | None:
    value = (version or "*").strip()
    if value in {"", "*"}:
        return None
    if any(token in value for token in "<>!=~"):
        return SpecifierSet(value)
    return SpecifierSet(f"=={value}")


def _satisfies_version(actual: str, requested: str) -> bool:
    spec = _normalize_exact_or_range(requested)
    if spec is None:
        return True
    try:
        version = Version(actual)
    except InvalidVersion:
        return actual == requested
    return version in spec
