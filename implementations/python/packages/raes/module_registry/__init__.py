"""Registry-aware SDL module resolution and publishing.

This package is a thin facade over cohesive subdomains:

* :mod:`._constants` - lockfile / trust-policy / OCI-layout names and schema versions.
* :mod:`._cache` - bounded gzip admission, safe locks, tree integrity, and recovery.
* :mod:`._filesystem` - durable immutable-version and pointer transactions.
* :mod:`._digests` - digest and version-matching helpers.
* :mod:`.models` - Pydantic policy/lock models, the resolved-module DTO, and lockfile persistence.
* :mod:`.signing` - Ed25519 signature payloads and trusted-signer verification.
* :mod:`.resolution` - local/locked/OCI import resolution orchestration.
* :mod:`.publishing` - OCI-layout publishing.

The package facade remains the compatibility and injection surface for OCI
transport and archive limits. Network reads and tar-member validation live here;
the cache submodule dynamically reads ``raes.module_registry._OCI_LIMITS`` and
the facade re-exports its private test seams. This preserves the historical
``test_sdl_module_registry.py`` patch behavior while keeping every source module
below the repository size cap.
"""

from __future__ import annotations

import json
import os
import tarfile
import time
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

# The submodule imports below are this package's public re-export surface, plus
# the private ``_sha256_digest`` / ``_signable_payload`` / ``_verify_signatures``
# seams the pre-split module exposed for tests. They are deliberately NOT narrowed
# by an ``__all__``: the single-file module had none, so adding one would change
# the legacy ``from raes.module_registry import *`` semantics. F401 is ignored for
# this facade in pyproject.toml - the "unused import" claim is false for re-exports.
from .._errors import SDLParseError
from .._source_profile import SDLSourceParseOptions
from ..scenario import ImportDecl, ModuleDescriptor, Scenario
from ._archive import _expected_cache_tree_manifest
from ._cache import (
    _CACHE_THREAD_LOCKS,
    _CACHE_THREAD_LOCKS_GUARD,
    _CACHE_TREE_MANIFEST_NAME,
    _CACHE_TREE_SCHEMA,
    _DECOMPRESSION_CHUNK_BYTES,
    _SPOOL_MEMORY_BYTES,
    _acquire_file_lock,
    _bounded_gzip_tar_stream,
    _cache_entry_lock,
    _cache_tree_entries,
    _cache_tree_manifest,
    _canonical_json_bytes,
    _hash_cache_file,
    _open_cache_lock,
    _read_cache_manifest_bytes,
    _recover_cache_root,
    _release_file_lock,
    _same_file_identity,
    _trusted_entry_projection,
    _validated_cache_root,
    _write_cache_tree_manifest,
)
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
from ._filesystem import (
    _install_version_directory,
    _iter_version_directories,
    _new_version_stage,
    _prepare_versioned_slot,
    _prune_version_directories,
    _read_version_pointer,
    _remove_path,
    _require_directory,
    _write_version_pointer,
)
from ._verified_sources import _cache_source_result, _VerifiedSourceBundle
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
    max_tar_stream_bytes: int = 320 * 1024 * 1024
    max_gzip_expansion_ratio: int = 1024
    max_tree_depth: int = 256


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
        with urlopen(request, timeout=_OCI_LIMITS.timeout_seconds) as response:
            payload = _read_capped(response, url=url, max_bytes=limit)
    except URLError as exc:
        raise SDLParseError(f"Failed to fetch OCI metadata from {url}") from exc
    return _decode_json_object(payload, context=f"OCI metadata from {url}")


def _decode_json_object(payload: bytes, *, context: str) -> dict[str, Any]:
    """Decode attacker-controlled JSON behind one stable, bounded error surface."""

    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SDLParseError(f"{context} is not valid UTF-8 JSON") from exc
    if not isinstance(decoded, dict):
        raise SDLParseError(f"{context} must be a JSON object")
    return decoded


def _bytes_request(url: str, *, headers: dict[str, str] | None = None, max_bytes: int | None = None) -> bytes:
    request = Request(url, headers=headers or {})
    limit = _OCI_LIMITS.max_metadata_bytes if max_bytes is None else max_bytes
    try:
        with urlopen(request, timeout=_OCI_LIMITS.timeout_seconds) as response:
            return _read_capped(response, url=url, max_bytes=limit)
    except URLError as exc:
        raise SDLParseError(f"Failed to fetch OCI blob from {url}") from exc


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
    pure_name = PurePosixPath(member.name)
    source_name = member.name.removesuffix("/") if member.isdir() else member.name
    if (
        not member.name
        or "\\" in member.name
        or pure_name.is_absolute()
        or ".." in pure_name.parts
        or source_name != pure_name.as_posix()
        or (pure_name.parts and len(pure_name.parts[0]) == 2 and pure_name.parts[0][1] == ":")
    ):
        raise SDLParseError(f"Path traversal detected in OCI bundle tar member: {member.name!r}")
    member_path = (dest / member.name).resolve()
    if not member_path.is_relative_to(resolved_dest):
        raise SDLParseError(f"Path traversal detected in OCI bundle tar member: {member.name!r}")
    relative_path = member_path.relative_to(resolved_dest)
    if len(relative_path.parts) > limits.max_tree_depth:
        raise SDLParseError(
            f"OCI bundle member {member.name!r} exceeds the {limits.max_tree_depth}-component path-depth limit"
        )
    if member_path == (dest / _CACHE_TREE_MANIFEST_NAME).resolve():
        raise SDLParseError("OCI module bundle contains a reserved cache metadata path")
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
    filesystem-write boundary for module import resolution. It complements the
    mandatory PEP 706 ``data`` filter: reject path traversal, symlinks, hard
    links, and special files, and strip setuid/setgid/sticky bits. A runtime that
    lacks the filter fails closed instead of using unfiltered extraction.

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
    content_digest: str | None = None,
    root_file: str,
    base_dir: Path,
    source_options: SDLSourceParseOptions | None = None,
) -> Path | _VerifiedSourceBundle:
    if (
        not manifest_digest
        or manifest_digest in {".", ".."}
        or "/" in manifest_digest
        or "\\" in manifest_digest
        or "\x00" in manifest_digest
    ):
        raise SDLParseError("Invalid OCI manifest digest cache key")
    root_relative = PurePosixPath(root_file)
    if (
        not root_file
        or "\\" in root_file
        or "\x00" in root_file
        or ".." in root_relative.parts
        or root_relative.is_absolute()
        or root_relative == PurePosixPath(".")
        or root_file != root_relative.as_posix()
        or (root_relative.parts and len(root_relative.parts[0]) == 2 and root_relative.parts[0][1] == ":")
    ):
        raise SDLParseError(f"Invalid OCI root_file path: {root_file!r}")
    actual_content_digest = f"sha256:{_sha256_digest(bundle_bytes)}"
    expected_content_digest = content_digest or actual_content_digest
    if expected_content_digest != actual_content_digest:
        raise SDLParseError("OCI module bundle does not match its expected content digest")

    cache_root = _oci_cache_dir(base_dir)
    cache_error = "Unable to create the OCI module cache"
    _require_directory(cache_root.parent, error_message=cache_error)
    _require_directory(cache_root, error_message=cache_error)
    cache_slot = cache_root / manifest_digest
    lock_path = cache_root / ".locks" / f"{manifest_digest}.lock"

    with _cache_entry_lock(lock_path):
        versions = _prepare_versioned_slot(
            slot=cache_slot,
            error_message="Unable to prepare the OCI module cache entry",
        )
        try:
            with (
                _bounded_gzip_tar_stream(bundle_bytes) as tar_stream,
                tarfile.open(fileobj=tar_stream, mode="r:") as tar,
            ):
                # The complete uncompressed stream is admitted before ``tarfile``
                # parses its first header. Member validation and the standard data
                # filter then provide independent filesystem-write defenses.
                safe_members = _safe_tar_members(tar, versions / ".inventory")
                expected_manifest = _expected_cache_tree_manifest(
                    tar=tar,
                    members=safe_members,
                    content_digest=expected_content_digest,
                    root_file=root_file,
                )
                expected_root = next(
                    (entry for entry in expected_manifest["entries"] if entry["path"] == root_relative.as_posix()),
                    None,
                )
                if expected_root is None or expected_root["type"] != "file":
                    raise SDLParseError(f"Resolved OCI module bundle is missing declared root file '{root_file}'")
                hit = _recover_cache_root(
                    slot=cache_slot,
                    versions=versions,
                    expected_content_digest=expected_content_digest,
                    expected_manifest=expected_manifest,
                    root_relative=root_relative,
                )
                if hit is not None:
                    return _cache_source_result(
                        hit,
                        expected_manifest=expected_manifest,
                        root_relative=root_relative,
                        source_options=source_options,
                    )
                staging = _new_version_stage(
                    versions=versions,
                    error_message="Unable to stage the OCI module cache entry",
                )
                try:
                    try:
                        tar.extractall(staging, members=safe_members, filter="data")
                    except TypeError as exc:
                        raise SDLParseError("Safe OCI tar extraction requires Python 3.11.4 or newer") from exc
                    staged_root = staging.joinpath(*root_relative.parts)
                    if (
                        staged_root.is_symlink()
                        or not staged_root.is_file()
                        or not staged_root.resolve(strict=True).is_relative_to(staging.resolve(strict=True))
                    ):
                        raise SDLParseError(f"Resolved OCI module bundle is missing declared root file '{root_file}'")
                    prior_version = _read_version_pointer(slot=cache_slot)
                    _write_cache_tree_manifest(
                        root=staging,
                        content_digest=expected_content_digest,
                        root_file=root_file,
                    )
                    staged_validation = _validated_cache_root(
                        version=staging,
                        expected_manifest=expected_manifest,
                        root_relative=root_relative,
                    )
                    if staged_validation is None:
                        raise SDLParseError("Staged OCI module cache entry failed validation")
                    version_name = f"{actual_content_digest.removeprefix('sha256:')}-{uuid4().hex}"
                    installed = _install_version_directory(
                        staged=staging,
                        versions=versions,
                        version_name=version_name,
                        error_message="Unable to commit the OCI module cache entry atomically",
                    )
                    committed = _validated_cache_root(
                        version=installed,
                        expected_manifest=expected_manifest,
                        root_relative=root_relative,
                    )
                    if committed is None:
                        raise SDLParseError("Committed OCI module cache entry failed validation")
                    _prune_version_directories(
                        versions=versions,
                        retain_names={version_name, *(() if prior_version is None else (prior_version,))},
                        error_message="Unable to prune stale OCI module cache versions",
                    )
                    _write_version_pointer(
                        slot=cache_slot,
                        version_name=version_name,
                        error_message="Unable to commit the OCI module cache pointer atomically",
                    )
                    return _cache_source_result(
                        committed,
                        expected_manifest=expected_manifest,
                        root_relative=root_relative,
                        source_options=source_options,
                    )
                finally:
                    _remove_path(staging)
        except (EOFError, OSError, tarfile.TarError, zlib.error) as exc:
            raise SDLParseError("OCI module bundle is not a valid gzip-compressed tar archive") from exc
