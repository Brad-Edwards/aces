"""Descriptor-bound immutable SDL sources for verified OCI cache trees."""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from .._errors import SDLParseError
from .._source_profile import SDLSourceParseOptions
from ..scenario import ImportDecl
from ._cache import _same_file_identity

if TYPE_CHECKING:
    from ..parser import SDLSourceDocument

_CACHE_INTEGRITY_ERROR = "OCI module cache tree failed integrity validation"


@dataclass(frozen=True)
class _VerifiedSourceBundle:
    """One immutable in-memory view of a verified OCI SDL import graph."""

    cache_root: Path
    documents: Mapping[str, SDLSourceDocument]

    def resolve_local(self, *, base_dir: Path, relative: str) -> tuple[Path, SDLSourceDocument]:
        base_relative = _cache_relative_path(self.cache_root, base_dir)
        target = _normalize_bundle_path(base_relative, relative)
        document = self.documents.get(target)
        if document is None:
            raise SDLParseError(f"Imported SDL file not found: {relative}")
        return self.cache_root.joinpath(*PurePosixPath(target).parts), document

    def identity_path(self, path: Path) -> Path:
        """Return a lexical cache identity without consulting mutable paths."""

        relative = _cache_relative_path(self.cache_root, path)
        return self.cache_root.joinpath(*PurePosixPath(relative).parts)


def _cache_relative_path(cache_root: Path, path: Path) -> str:
    root = cache_root.absolute()
    candidate = path.absolute()
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise SDLParseError("Local import path escapes the verified OCI module cache") from exc
    return relative.as_posix() or "."


def _local_resolved_source(import_path: Path, base_dir: Path, *, lexical: bool = False) -> str:
    """Return one portable lock identity, without resolving admitted cache paths.

    Local lock identities are checkout-independent POSIX paths. Ordinary local
    files retain canonical filesystem resolution, while a descriptor-bound OCI
    source uses only its already-confined lexical identity.
    """

    anchor = base_dir.absolute() if lexical else base_dir.resolve()
    return Path(os.path.relpath(import_path, anchor)).as_posix()


def _normalize_bundle_path(base_relative: str, relative: str) -> str:
    normalized = relative.replace("\\", "/")
    candidate = PurePosixPath(normalized)
    if (
        not normalized
        or "\x00" in normalized
        or candidate.is_absolute()
        or (candidate.parts and len(candidate.parts[0]) == 2 and candidate.parts[0][1] == ":")
    ):
        raise SDLParseError(f"Local import path escapes base directory: {relative!r}")
    parts = [] if base_relative == "." else list(PurePosixPath(base_relative).parts)
    for part in candidate.parts:
        if part == "..":
            if not parts:
                raise SDLParseError(f"Local import path escapes base directory: {relative!r}")
            parts.pop()
        else:
            parts.append(part)
    if not parts:
        raise SDLParseError(f"Local import path escapes base directory: {relative!r}")
    return PurePosixPath(*parts).as_posix()


def _read_verified_cache_source(
    path: Path,
    *,
    expected_entry: dict[str, Any],
    source_options: SDLSourceParseOptions,
) -> SDLSourceDocument:
    """Read and authenticate exact source bytes through one no-follow descriptor."""

    expected_size = expected_entry["size"]
    expected_mode = expected_entry["mode"]
    descriptor = -1
    try:
        before = path.lstat()
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size != expected_size
            or stat.S_IMODE(before.st_mode) != expected_mode
        ):
            raise SDLParseError(_CACHE_INTEGRITY_ERROR)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            opened = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(opened.st_mode)
                or not _same_file_identity(before, opened)
                or opened.st_size != expected_size
                or stat.S_IMODE(opened.st_mode) != expected_mode
            ):
                raise SDLParseError(_CACHE_INTEGRITY_ERROR)
            digest = hashlib.sha256()
            captured = bytearray()
            byte_count = 0
            capture_limit = source_options.limits.max_input_bytes + 1
            while chunk := source.read(1024 * 1024):
                byte_count += len(chunk)
                digest.update(chunk)
                remaining = max(capture_limit - len(captured), 0)
                captured.extend(chunk[:remaining])
            after = os.fstat(source.fileno())
        if (
            not _same_file_identity(opened, after)
            or after.st_size != expected_size
            or stat.S_IMODE(after.st_mode) != expected_mode
        ):
            raise SDLParseError(_CACHE_INTEGRITY_ERROR)
    except SDLParseError:
        raise
    except OSError as exc:
        raise SDLParseError(_CACHE_INTEGRITY_ERROR) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    if byte_count != expected_size or f"sha256:{digest.hexdigest()}" != expected_entry["digest"]:
        raise SDLParseError(_CACHE_INTEGRITY_ERROR)

    from ..parser import _source_document_from_bytes

    return _source_document_from_bytes(bytes(captured), path=path, limits=source_options.limits)


def _read_verified_source_bundle(
    *,
    cache_root: Path,
    expected_manifest: dict[str, Any],
    root_relative: PurePosixPath,
    source_options: SDLSourceParseOptions,
) -> _VerifiedSourceBundle:
    """Capture the complete reachable local SDL graph before releasing its lock."""

    from ..parser import _load_normalized_data

    entries = {
        entry["path"]: entry
        for entry in expected_manifest["entries"]
        if isinstance(entry, dict) and entry.get("type") == "file"
    }
    pending = [root_relative.as_posix()]
    documents: dict[str, SDLSourceDocument] = {}
    while pending:
        relative = pending.pop()
        if relative in documents:
            continue
        entry = entries.get(relative)
        if entry is None:
            raise SDLParseError(f"Imported SDL file not found: {relative}")
        path = cache_root.joinpath(*PurePosixPath(relative).parts)
        document = _read_verified_cache_source(
            path,
            expected_entry=entry,
            source_options=source_options,
        )
        documents[relative] = document
        payload = _load_normalized_data(
            document.text,
            path=path,
            source_format=source_options.source_format,
            migration_policy=source_options.migration_policy,
            limits=source_options.limits,
        )
        raw_imports = payload.get("imports", [])
        if not isinstance(raw_imports, list):
            raise SDLParseError("Imported SDL unit is structurally invalid", path=path)
        for raw_import in raw_imports:
            try:
                import_decl = ImportDecl.model_validate(raw_import)
            except ValidationError as exc:
                raise SDLParseError("Imported SDL unit is structurally invalid", path=path) from exc
            source = import_decl.normalized_source
            if source.startswith("local:"):
                parent = PurePosixPath(relative).parent.as_posix()
                pending.append(_normalize_bundle_path(parent, source.removeprefix("local:")))
    return _VerifiedSourceBundle(
        cache_root=cache_root.absolute(),
        documents=MappingProxyType(dict(sorted(documents.items()))),
    )


def _cache_source_result(
    root: Path,
    *,
    expected_manifest: dict[str, Any],
    root_relative: PurePosixPath,
    source_options: SDLSourceParseOptions | None,
) -> Path | _VerifiedSourceBundle:
    if source_options is None:
        return root
    cache_root = root
    for _part in root_relative.parts:
        cache_root = cache_root.parent
    return _read_verified_source_bundle(
        cache_root=cache_root,
        expected_manifest=expected_manifest,
        root_relative=root_relative,
        source_options=source_options,
    )


__all__ = ["_VerifiedSourceBundle"]
