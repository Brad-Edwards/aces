"""Trusted OCI archive inventory derived without extracting filesystem content."""

from __future__ import annotations

import hashlib
import tarfile
from pathlib import PurePosixPath
from typing import Any

from .._errors import SDLParseError
from ._cache import _CACHE_TREE_SCHEMA, _DECOMPRESSION_CHUNK_BYTES, _canonical_json_bytes


def _limits() -> Any:
    from . import _OCI_LIMITS

    return _OCI_LIMITS


def _filtered_file_mode(mode: int) -> int:
    """Return the regular-file mode produced by the mandatory PEP 706 data filter."""

    filtered = mode & 0o755
    if not filtered & 0o100:
        filtered &= ~0o111
    return filtered | 0o600


def _expected_cache_tree_manifest(
    *,
    tar: tarfile.TarFile,
    members: list[tarfile.TarInfo],
    content_digest: str,
    root_file: str,
) -> dict[str, Any]:
    """Hash a verified tar into the platform-neutral cache integrity inventory."""

    nodes: dict[str, dict[str, Any]] = {".": {"path": ".", "type": "directory"}}
    entry_limit = _limits().max_bundle_members + 1
    for member in members:
        relative = PurePosixPath(member.name)
        if relative == PurePosixPath("."):
            if not member.isdir():
                raise SDLParseError("OCI bundle cannot replace the cache tree root")
            continue
        for parent in reversed(relative.parents):
            if parent == PurePosixPath("."):
                continue
            parent_name = parent.as_posix()
            existing = nodes.get(parent_name)
            if existing is not None and existing["type"] != "directory":
                raise SDLParseError("OCI bundle contains conflicting file and directory paths")
            nodes[parent_name] = {"path": parent_name, "type": "directory"}
        relative_name = relative.as_posix()
        existing = nodes.get(relative_name)
        if member.isdir():
            if existing is not None and existing["type"] != "directory":
                raise SDLParseError("OCI bundle contains conflicting file and directory paths")
            nodes[relative_name] = {"path": relative_name, "type": "directory"}
        else:
            if existing is not None:
                raise SDLParseError("OCI bundle contains conflicting file and directory paths")
            extracted = tar.extractfile(member)
            if extracted is None:
                raise SDLParseError("Unable to read a regular file from the OCI module bundle")
            digest = hashlib.sha256()
            size = 0
            with extracted:
                while chunk := extracted.read(_DECOMPRESSION_CHUNK_BYTES):
                    size += len(chunk)
                    if size > member.size:
                        raise SDLParseError("OCI bundle member payload exceeds its declared size")
                    digest.update(chunk)
            if size != member.size:
                raise SDLParseError("OCI bundle member payload is shorter than its declared size")
            nodes[relative_name] = {
                "digest": f"sha256:{digest.hexdigest()}",
                "mode": _filtered_file_mode(member.mode),
                "path": relative_name,
                "size": size,
                "type": "file",
            }
        if len(nodes) > entry_limit:
            raise SDLParseError("OCI bundle exceeds the bounded extracted-tree entry limit")
    entries = [nodes[name] for name in sorted(nodes, key=lambda name: PurePosixPath(name).parts)]
    manifest = {
        "content_digest": content_digest,
        "entries": entries,
        "root_file": root_file,
        "schema": _CACHE_TREE_SCHEMA,
        "tree_digest": f"sha256:{hashlib.sha256(_canonical_json_bytes(entries)).hexdigest()}",
    }
    if len(_canonical_json_bytes(manifest)) > _limits().max_metadata_bytes:
        raise SDLParseError("OCI module cache integrity manifest exceeds the metadata limit")
    return manifest
