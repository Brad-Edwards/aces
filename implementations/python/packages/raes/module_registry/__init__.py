"""Registry-aware SDL module resolution and publishing.

This package is a thin facade over cohesive subdomains:

* :mod:`._constants` - lockfile / trust-policy / OCI-layout names and schema versions.
* :mod:`._digests` - digest and version-matching helpers.
* :mod:`.models` - Pydantic policy/lock models, the resolved-module DTO, and lockfile persistence.
* :mod:`.signing` - Ed25519 signature payloads and trusted-signer verification.
* :mod:`.resolution` - local/locked/OCI import resolution orchestration.
* :mod:`.publishing` - OCI-layout publishing.

The OCI transport and archive-safety security boundary (URL fetch with an explicit
timeout, capped reads, and tar-member validation before extraction) is defined in
this module rather than a submodule on purpose. ``test_sdl_module_registry.py``
patches ``raes.module_registry.urlopen`` and ``raes.module_registry._OCI_LIMITS`` on
the package object, and a Python function resolves such globals from the module
where it is *defined*. Keeping these seams defined here preserves that patch
behavior for the request and archive paths without modifying the tests; the
resolution orchestrator reaches them through a function-local ``from . import``.
"""

from __future__ import annotations

import io
import json
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

# The submodule imports below are this package's public re-export surface, plus
# the private ``_sha256_digest`` / ``_signable_payload`` / ``_verify_signatures``
# seams the pre-split module exposed for tests. They are deliberately NOT narrowed
# by an ``__all__``: the single-file module had none, so adding one would change
# the legacy ``from raes.module_registry import *`` semantics. F401 is ignored for
# this facade in pyproject.toml - the "unused import" claim is false for re-exports.
from .._errors import SDLParseError
from ..scenario import ImportDecl, ModuleDescriptor, Scenario
from ._constants import (
    LOCKFILE_NAME,
    LOCKFILE_SCHEMA_VERSION,
    OCI_BUNDLE_MEDIA_TYPE,
    OCI_CONFIG_MEDIA_TYPE,
    OCI_LAYOUT_MEDIA_TYPE,
    OCI_LAYOUT_SCHEMA_VERSION,
    TRUST_POLICY_NAME,
    TRUST_POLICY_SCHEMA_VERSION,
)
from ._digests import _sha256_digest
from .models import (
    Lockfile,
    LockRecord,
    RegistryTrustPolicy,
    ResolvedModule,
    TrustPolicy,
    load_lockfile,
    load_trust_policy,
    write_lockfile,
)
from .publishing import publish_module_to_oci_layout
from .resolution import resolve_import, resolve_lock_records
from .signing import _signable_payload, _verify_signatures

_HTTP_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class _OCIResourceLimits:
    """Bounds for remote OCI fetches and bundle extraction (issue #12).

    The OCI import path pulls attacker-influenceable bytes from allowlisted
    registries; without caps a compromised registry, mirror, or oversized module
    can exhaust process memory (buffering an unbounded response) or disk/CPU
    (extracting an unbounded bundle). Compressed-download limits are kept separate
    from extracted-archive limits because a small gzip can expand into a large tar
    payload. This is the single extensibility seam: operator-tunable overrides
    should later extend ``RegistryTrustPolicy`` and merge with these defaults,
    rather than threading limit arguments through parser/compiler/runtime/CLI.
    """

    timeout_seconds: int = _HTTP_TIMEOUT_SECONDS
    max_metadata_bytes: int = 8 * 1024 * 1024
    max_bundle_bytes: int = 128 * 1024 * 1024
    max_bundle_members: int = 8192
    max_member_bytes: int = 64 * 1024 * 1024
    max_total_bytes: int = 256 * 1024 * 1024


_OCI_LIMITS = _OCIResourceLimits()


class _CappableResponse(Protocol):
    """Minimal HTTP-response surface the bounded reader depends on.

    Structural view of ``http.client.HTTPResponse`` (the ``urlopen`` return) so the
    reader is typed without a bare ``Any``: it only needs a size-capped ``read`` and,
    optionally, response headers for the advisory Content-Length pre-check.
    """

    def read(self, amt: int = ..., /) -> bytes: ...


def _declared_content_length(response: _CappableResponse) -> int | None:
    """Return a validated Content-Length, or ``None`` when the header is absent.

    Content-Length is advisory and attacker-controlled, so it is only ever used to
    reject early - never to size a buffer or to substitute for counting the bytes
    actually read.
    """
    headers = getattr(response, "headers", None)
    raw = headers.get("Content-Length") if headers is not None else None
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise SDLParseError(f"OCI response declares an invalid Content-Length: {raw!r}") from exc
    if value < 0:
        raise SDLParseError(f"OCI response declares a negative Content-Length: {value}")
    return value


def _read_capped(response: _CappableResponse, *, url: str, max_bytes: int) -> bytes:
    """Read at most ``max_bytes`` from ``response``, failing closed if exceeded.

    Rejecting an oversized advisory ``Content-Length`` avoids even starting the
    read; the authoritative check reads ``max_bytes + 1`` so the in-memory buffer
    stays bounded and a registry cannot force the resolver to buffer an unbounded
    blob. Messages name the limit and the safe URL only - never the body.
    """
    declared = _declared_content_length(response)
    if declared is not None and declared > max_bytes:
        raise SDLParseError(
            f"OCI response from {url} declares Content-Length {declared} bytes, exceeding the {max_bytes}-byte limit"
        )
    data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise SDLParseError(f"OCI response from {url} exceeds the {max_bytes}-byte limit")
    return data


def _json_request(url: str, *, headers: dict[str, str] | None = None, max_bytes: int | None = None) -> dict[str, Any]:
    request = Request(url, headers=headers or {})
    limit = _OCI_LIMITS.max_metadata_bytes if max_bytes is None else max_bytes
    try:
        with urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            return json.loads(_read_capped(response, url=url, max_bytes=limit).decode("utf-8"))
    except (URLError, json.JSONDecodeError) as exc:
        raise SDLParseError(f"Failed to fetch OCI metadata from {url}: {exc}") from exc


def _bytes_request(url: str, *, headers: dict[str, str] | None = None, max_bytes: int | None = None) -> bytes:
    request = Request(url, headers=headers or {})
    limit = _OCI_LIMITS.max_metadata_bytes if max_bytes is None else max_bytes
    try:
        with urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            return _read_capped(response, url=url, max_bytes=limit)
    except URLError as exc:
        raise SDLParseError(f"Failed to fetch OCI blob from {url}: {exc}") from exc


def _oci_cache_dir(base_dir: Path) -> Path:
    return base_dir / ".raes" / "module-cache"


def _validate_tar_member_shape(
    member: tarfile.TarInfo,
    *,
    dest: Path,
    resolved_dest: Path,
    seen_paths: set[str],
    limits: _OCIResourceLimits,
) -> None:
    """Fail closed on an unsafe or oversized single tar member (issues #12/#13).

    Rejects path traversal, symlinks, hard links, special files, and duplicate
    normalized paths, and enforces the per-member extracted-size cap. Records the
    member's normalized path in ``seen_paths`` so a later duplicate is caught.
    """
    member_path = (dest / member.name).resolve()
    if not member_path.is_relative_to(resolved_dest):
        raise SDLParseError(f"Path traversal detected in OCI bundle tar member: {member.name!r}")
    if member.issym() or member.islnk():
        raise SDLParseError(f"Links are not allowed in OCI bundle tar: {member.name!r}")
    if not (member.isfile() or member.isdir()):
        raise SDLParseError(f"Unsupported tar member type in OCI bundle: {member.name!r}")
    normalized = member_path.as_posix()
    if normalized in seen_paths:
        raise SDLParseError(f"Duplicate tar member path in OCI bundle: {member.name!r}")
    seen_paths.add(normalized)
    # Account by the logical member size so a sparse or padded member cannot
    # understate the bytes it will extract.
    if member.isfile() and member.size > limits.max_member_bytes:
        raise SDLParseError(
            f"OCI bundle member {member.name!r} exceeds the {limits.max_member_bytes}-byte per-member limit"
        )


def _safe_tar_members(
    tar: tarfile.TarFile,
    dest: Path,
) -> list[tarfile.TarInfo]:
    """Validate every tar member before extraction (fail closed).

    The OCI bundle bytes are attacker-controlled even after registry allowlisting,
    digest pinning, and signature verification, so this validation is the
    filesystem-write boundary for module import resolution. It must hold on every
    supported runtime, not just on Python 3.12+ where ``extractall(filter="data")``
    is available, because the PEP 706 ``filter`` keyword was backported only in
    Python 3.11.4 while the project supports ``>=3.11``. Validation therefore
    matches the ``data`` filter's guarantees: reject path traversal, symlinks,
    hard links, and special files, and strip setuid/setgid/sticky bits.

    It is also the resource-exhaustion boundary (issue #12): the archive member
    count, per-member extracted size, and total extracted bytes are bounded by
    ``_OCI_LIMITS`` and duplicate normalized paths are rejected, so a malicious or
    oversized bundle cannot exhaust disk or CPU during extraction.
    """
    limits = _OCI_LIMITS
    safe: list[tarfile.TarInfo] = []
    resolved_dest = dest.resolve()
    seen_paths: set[str] = set()
    total_bytes = 0
    # Iterate lazily rather than materialising ``tar.getmembers()`` so a bundle that
    # declares an unbounded member list, or expands into an unbounded extraction, is
    # rejected as soon as a cap is crossed - before the remainder of the archive is
    # decompressed (issue #12).
    for member_count, member in enumerate(tar, start=1):
        if member_count > limits.max_bundle_members:
            raise SDLParseError(f"OCI bundle exceeds the maximum of {limits.max_bundle_members} archive members")
        _validate_tar_member_shape(
            member,
            dest=dest,
            resolved_dest=resolved_dest,
            seen_paths=seen_paths,
            limits=limits,
        )
        if member.isfile():
            total_bytes += member.size
            if total_bytes > limits.max_total_bytes:
                raise SDLParseError(f"OCI bundle exceeds the {limits.max_total_bytes}-byte total extraction limit")
        # Drop setuid/setgid/sticky bits.
        member.mode &= 0o777
        safe.append(member)
    return safe


def _extract_bundle_to_cache(
    *,
    bundle_bytes: bytes,
    manifest_digest: str,
    root_file: str,
    base_dir: Path,
) -> Path:
    cache_dir = _oci_cache_dir(base_dir) / manifest_digest
    if ".." in Path(root_file).parts or Path(root_file).is_absolute():
        raise SDLParseError(f"Invalid OCI root_file path: {root_file!r}")
    resolved_cache = cache_dir.resolve()
    root_path = cache_dir / root_file
    if not root_path.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(bundle_bytes), mode="r:gz") as tar:
            # Validate every member up front so the security property is identical on
            # all supported runtimes and never depends on the runtime's tarfile filter
            # support. ``filter="data"`` is applied as defense in depth where available
            # (Python 3.11.4+/3.12+); on 3.11.0–3.11.3 the keyword is absent and the
            # already-validated members are the guarantee. No path falls back to an
            # unfiltered ``tar.extractall(cache_dir)``.
            safe_members = _safe_tar_members(tar, cache_dir)
            try:
                tar.extractall(cache_dir, members=safe_members, filter="data")
            # Python 3.11.0–3.11.3 lack the PEP 706 filter keyword.
            except TypeError:
                tar.extractall(cache_dir, members=safe_members)
    # Enforce the root-file containment contract on EVERY return path, including
    # the cache-hit fast path: a stale cache (e.g. one populated by an earlier
    # unsafe extractor) could hold a symlink or a non-regular file at root_file
    # that resolves outside the digest cache. Validating here fails closed
    # regardless of whether extraction ran this call.
    if not root_path.is_file() or not root_path.resolve().is_relative_to(resolved_cache):
        raise SDLParseError(f"Resolved OCI module bundle is missing declared root file '{root_file}'")
    return root_path
