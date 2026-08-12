"""Bounded OCI cache admission, locking, inventory, and recovery helpers."""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import io
import json
import os
import stat
import tempfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

from .._errors import SDLParseError
from ._filesystem import (
    _iter_version_directories,
    _prune_version_directories,
    _read_version_pointer,
    _require_directory,
    _write_version_pointer,
)

_CACHE_THREAD_LOCKS: dict[str, threading.Lock] = {}
_CACHE_THREAD_LOCKS_GUARD = threading.Lock()
_CACHE_TREE_MANIFEST_NAME = ".raes-cache-tree.json"
_CACHE_TREE_SCHEMA = "raes-cache-tree/v1"
_DECOMPRESSION_CHUNK_BYTES = 1024 * 1024
_SPOOL_MEMORY_BYTES = 8 * 1024 * 1024
_WINDOWS_LOCKING = os.name == "nt"
_LOCK_DIR_FD_SUPPORTED = os.open in os.supports_dir_fd


def _limits() -> Any:
    # Keep the historical package-facade test/operator seam authoritative.
    from . import _OCI_LIMITS

    return _OCI_LIMITS


def _acquire_file_lock(handle: BinaryIO) -> None:
    """Acquire an OS-backed exclusive lock within the configured OCI timeout."""

    deadline = time.monotonic() + _limits().timeout_seconds
    while True:
        try:
            if _WINDOWS_LOCKING:
                import msvcrt

                handle.seek(0)
                if handle.read(1) == b"":
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except (BlockingIOError, OSError) as exc:
            if time.monotonic() >= deadline:
                raise SDLParseError("Timed out waiting for the OCI module cache lock") from exc
            time.sleep(0.01)


def _release_file_lock(handle: BinaryIO) -> None:
    if _WINDOWS_LOCKING:
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    """Compare stable identity fields where the platform supplies them."""

    if left.st_dev and right.st_dev and left.st_dev != right.st_dev:
        return False
    return not (left.st_ino and right.st_ino and left.st_ino != right.st_ino)


def _open_cache_lock(lock_path: Path) -> BinaryIO:
    """Open one regular lock file, anchored to a validated parent directory."""

    error_message = "Unable to open the OCI module cache lock"
    _require_directory(lock_path.parent, error_message=error_message)
    common_flags = os.O_RDWR | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    parent_descriptor = -1
    expected: os.stat_result | None = None
    try:
        parent_expected = lock_path.parent.lstat()
        if not stat.S_ISDIR(parent_expected.st_mode):
            raise SDLParseError(error_message)
        open_path: str | Path = lock_path
        open_options: dict[str, int] = {}
        parent_actual = parent_expected
        if _LOCK_DIR_FD_SUPPORTED:
            parent_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
            parent_descriptor = os.open(lock_path.parent, parent_flags)
            parent_actual = os.fstat(parent_descriptor)
            if not stat.S_ISDIR(parent_actual.st_mode) or not _same_file_identity(parent_expected, parent_actual):
                raise SDLParseError(error_message)
            open_path = lock_path.name
            open_options = {"dir_fd": parent_descriptor}
        try:
            if parent_descriptor >= 0:
                expected = os.stat(lock_path.name, dir_fd=parent_descriptor, follow_symlinks=False)
            else:
                expected = lock_path.lstat()
        except FileNotFoundError:
            try:
                descriptor = os.open(open_path, common_flags | os.O_CREAT | os.O_EXCL, 0o600, **open_options)
            except FileExistsError:
                # A concurrent first user may create the shared lock after our
                # missing-path check. Re-enter the same no-follow admission
                # path rather than turning normal contention into a failure.
                if parent_descriptor >= 0:
                    expected = os.stat(lock_path.name, dir_fd=parent_descriptor, follow_symlinks=False)
                else:
                    expected = lock_path.lstat()
                if not stat.S_ISREG(expected.st_mode):
                    raise SDLParseError(error_message) from None
                descriptor = os.open(open_path, common_flags, **open_options)
        else:
            if not stat.S_ISREG(expected.st_mode):
                raise SDLParseError(error_message)
            descriptor = os.open(open_path, common_flags, **open_options)
        actual = os.fstat(descriptor)
        if not stat.S_ISREG(actual.st_mode) or (expected is not None and not _same_file_identity(expected, actual)):
            raise SDLParseError(error_message)
        parent_after = lock_path.parent.lstat()
        if not stat.S_ISDIR(parent_after.st_mode) or not _same_file_identity(parent_actual, parent_after):
            raise SDLParseError(error_message)
        handle = os.fdopen(descriptor, "r+b")
        descriptor = -1
        return handle
    except SDLParseError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise SDLParseError(error_message) from exc
    finally:
        if parent_descriptor >= 0:
            os.close(parent_descriptor)


@contextlib.contextmanager
def _cache_entry_lock(lock_path: Path) -> Iterator[None]:
    from . import _acquire_file_lock, _open_cache_lock, _release_file_lock

    lock_key = str(lock_path.absolute())
    with _CACHE_THREAD_LOCKS_GUARD:
        thread_lock = _CACHE_THREAD_LOCKS.setdefault(lock_key, threading.Lock())
    with thread_lock:
        handle = _open_cache_lock(lock_path)
        acquired = False
        try:
            _acquire_file_lock(handle)
            acquired = True
            yield
        finally:
            if acquired:
                _release_file_lock(handle)
            handle.close()


@contextlib.contextmanager
def _bounded_gzip_tar_stream(bundle_bytes: bytes) -> Iterator[BinaryIO]:
    """Decode a complete gzip stream behind absolute and ratio bounds."""

    limits = _limits()
    absolute_limit = limits.max_tar_stream_bytes
    ratio_limit = len(bundle_bytes) * limits.max_gzip_expansion_ratio
    if absolute_limit < 0 or limits.max_gzip_expansion_ratio < 0:
        raise SDLParseError("OCI gzip expansion limits must be non-negative")
    total = 0
    with (
        tempfile.SpooledTemporaryFile(max_size=_SPOOL_MEMORY_BYTES, mode="w+b") as stream,
        gzip.GzipFile(fileobj=io.BytesIO(bundle_bytes), mode="rb") as decoded,
    ):
        while True:
            remaining = min(absolute_limit - total, ratio_limit - total)
            read_size = min(_DECOMPRESSION_CHUNK_BYTES, max(1, remaining + 1))
            chunk = decoded.read(read_size)
            if not chunk:
                break
            total += len(chunk)
            if total > absolute_limit:
                raise SDLParseError(f"OCI bundle uncompressed tar stream exceeds the {absolute_limit}-byte limit")
            if total > ratio_limit:
                raise SDLParseError("OCI bundle gzip expansion exceeds the configured compressed-to-uncompressed ratio")
            stream.write(chunk)
        stream.seek(0)
        yield stream


def _hash_cache_file(path: Path, expected: os.stat_result) -> tuple[int, str]:
    """Hash one regular file without following a last-component symlink."""

    if expected.st_size > _limits().max_member_bytes:
        raise SDLParseError("OCI module cache tree failed integrity validation")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SDLParseError("OCI module cache tree failed integrity validation") from exc
    digest = hashlib.sha256()
    total = 0
    try:
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            actual = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(actual.st_mode)
                or not _same_file_identity(expected, actual)
                or actual.st_size != expected.st_size
                or stat.S_IMODE(actual.st_mode) != stat.S_IMODE(expected.st_mode)
            ):
                raise SDLParseError("OCI module cache tree failed integrity validation")
            while chunk := handle.read(_DECOMPRESSION_CHUNK_BYTES):
                total += len(chunk)
                if total > _limits().max_member_bytes:
                    raise SDLParseError("OCI module cache tree failed integrity validation")
                digest.update(chunk)
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise SDLParseError("OCI module cache tree failed integrity validation") from exc
    if total != expected.st_size:
        raise SDLParseError("OCI module cache tree failed integrity validation")
    return total, f"sha256:{digest.hexdigest()}"


def _cache_tree_entries(root: Path) -> list[dict[str, Any]]:
    """Return a canonical, bounded inventory of a cache version's extracted tree."""

    limits = _limits()
    if limits.max_bundle_members < 0 or limits.max_tree_depth < 0:
        raise SDLParseError("OCI module cache tree failed integrity validation")
    entries: list[dict[str, Any]] = []
    total_bytes = 0
    pending: list[tuple[Path, PurePosixPath, int]] = [(root, PurePosixPath("."), 0)]
    entry_limit = limits.max_bundle_members + 1
    while pending:
        path, relative, depth = pending.pop()
        if depth > limits.max_tree_depth:
            raise SDLParseError("OCI module cache tree failed integrity validation")
        try:
            before = path.lstat()
        except OSError as exc:
            raise SDLParseError("OCI module cache tree failed integrity validation") from exc
        mode = stat.S_IMODE(before.st_mode)
        relative_name = relative.as_posix()
        if stat.S_ISLNK(before.st_mode):
            raise SDLParseError("OCI module cache tree failed integrity validation")
        if stat.S_ISREG(before.st_mode):
            size, digest = _hash_cache_file(path, before)
            total_bytes += size
            if total_bytes > limits.max_total_bytes:
                raise SDLParseError("OCI module cache tree failed integrity validation")
            entries.append({"digest": digest, "mode": mode, "path": relative_name, "size": size, "type": "file"})
            continue
        if not stat.S_ISDIR(before.st_mode):
            raise SDLParseError("OCI module cache tree failed integrity validation")
        entries.append({"mode": mode, "path": relative_name, "type": "directory"})
        try:
            children: list[Path] = []
            with os.scandir(path) as iterator:
                for child in iterator:
                    children.append(Path(child.path))
                    if len(entries) + len(pending) + len(children) > entry_limit:
                        raise SDLParseError("OCI module cache tree failed integrity validation")
            children.sort(key=lambda child: child.name)
            after = path.lstat()
        except OSError as exc:
            raise SDLParseError("OCI module cache tree failed integrity validation") from exc
        if (
            not stat.S_ISDIR(after.st_mode)
            or not _same_file_identity(before, after)
            or stat.S_IMODE(after.st_mode) != mode
        ):
            raise SDLParseError("OCI module cache tree failed integrity validation")
        for child in reversed(children):
            if relative == PurePosixPath(".") and child.name == _CACHE_TREE_MANIFEST_NAME:
                continue
            child_relative = PurePosixPath(child.name) if relative == PurePosixPath(".") else relative / child.name
            pending.append((child, child_relative, depth + 1))
    return entries


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _cache_tree_manifest(*, root: Path, content_digest: str, root_file: str) -> dict[str, Any]:
    entries = _cache_tree_entries(root)
    return {
        "content_digest": content_digest,
        "entries": entries,
        "root_file": root_file,
        "schema": _CACHE_TREE_SCHEMA,
        "tree_digest": f"sha256:{hashlib.sha256(_canonical_json_bytes(entries)).hexdigest()}",
    }


def _write_cache_tree_manifest(*, root: Path, content_digest: str, root_file: str) -> None:
    manifest_path = root / _CACHE_TREE_MANIFEST_NAME
    if manifest_path.exists() or manifest_path.is_symlink():
        raise SDLParseError("OCI module bundle contains a reserved cache metadata path")
    manifest_bytes = _canonical_json_bytes(
        _cache_tree_manifest(root=root, content_digest=content_digest, root_file=root_file)
    )
    if len(manifest_bytes) > _limits().max_metadata_bytes:
        raise SDLParseError("OCI module cache integrity manifest exceeds the metadata limit")
    try:
        manifest_path.write_bytes(manifest_bytes)
    except OSError as exc:
        raise SDLParseError("Unable to write the OCI module cache integrity manifest") from exc


def _read_cache_manifest_bytes(path: Path) -> bytes:
    """Read a small regular manifest without following a last-component link."""

    try:
        expected = path.lstat()
    except OSError as exc:
        raise SDLParseError("OCI module cache tree failed integrity validation") from exc
    if not stat.S_ISREG(expected.st_mode):
        raise SDLParseError("OCI module cache tree failed integrity validation")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            actual = os.fstat(handle.fileno())
            if not stat.S_ISREG(actual.st_mode) or not _same_file_identity(expected, actual):
                raise SDLParseError("OCI module cache tree failed integrity validation")
            payload = handle.read(_limits().max_metadata_bytes + 1)
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise SDLParseError("OCI module cache tree failed integrity validation") from exc
    if len(payload) > _limits().max_metadata_bytes:
        raise SDLParseError("OCI module cache tree failed integrity validation")
    return payload


def _trusted_entry_projection(entries: list[Any]) -> list[dict[str, Any]]:
    """Project a local inventory onto properties determined by bundle bytes."""

    projected: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise SDLParseError("OCI module cache tree failed integrity validation")
        if entry.get("type") == "directory":
            projected.append({"path": entry["path"], "type": "directory"})
        elif entry.get("type") == "file" and all(
            isinstance(entry.get(field), field_type)
            for field, field_type in (("digest", str), ("mode", int), ("size", int))
        ):
            projected.append(
                {
                    "digest": entry["digest"],
                    "mode": entry["mode"],
                    "path": entry["path"],
                    "size": entry["size"],
                    "type": "file",
                }
            )
        else:
            raise SDLParseError("OCI module cache tree failed integrity validation")
    return projected


def _validated_cache_root(
    *,
    version: Path,
    expected_manifest: dict[str, Any],
    root_relative: PurePosixPath,
) -> Path | None:
    """Return the root only when it matches inventory derived from verified bytes."""

    try:
        if not isinstance(expected_manifest, dict) or set(expected_manifest) != {
            "content_digest",
            "entries",
            "root_file",
            "schema",
            "tree_digest",
        }:
            return None
        if expected_manifest["schema"] != _CACHE_TREE_SCHEMA or not isinstance(expected_manifest["entries"], list):
            return None
        if expected_manifest["tree_digest"] != (
            f"sha256:{hashlib.sha256(_canonical_json_bytes(expected_manifest['entries'])).hexdigest()}"
        ):
            return None
        expected_entries = _trusted_entry_projection(expected_manifest["entries"])
        raw = _read_cache_manifest_bytes(version / _CACHE_TREE_MANIFEST_NAME)
        manifest = json.loads(raw.decode("utf-8"))
        if not isinstance(manifest, dict) or set(manifest) != {
            "content_digest",
            "entries",
            "root_file",
            "schema",
            "tree_digest",
        }:
            return None
        if raw != _canonical_json_bytes(manifest):
            return None
        if manifest["schema"] != _CACHE_TREE_SCHEMA or not isinstance(manifest["entries"], list):
            return None
        if any(manifest[field] != expected_manifest[field] for field in ("content_digest", "root_file", "schema")):
            return None
        entries = _cache_tree_entries(version)
        if manifest["entries"] != entries:
            return None
        expected_tree_digest = f"sha256:{hashlib.sha256(_canonical_json_bytes(entries)).hexdigest()}"
        if manifest["tree_digest"] != expected_tree_digest:
            return None
        if _trusted_entry_projection(entries) != expected_entries:
            return None
        root_path = version.joinpath(*root_relative.parts)
        if (
            root_path.is_symlink()
            or not root_path.is_file()
            or not root_path.resolve(strict=True).is_relative_to(version.resolve(strict=True))
        ):
            return None
        return root_path
    except (OSError, UnicodeError, json.JSONDecodeError, SDLParseError):
        return None


def _recover_cache_root(
    *,
    slot: Path,
    versions: Path,
    expected_content_digest: str,
    expected_manifest: dict[str, Any],
    root_relative: PurePosixPath,
) -> Path | None:
    """Find a valid current/orphan version and repair its pointer when needed."""

    current = _read_version_pointer(slot=slot)
    candidates: list[Path] = []
    if current is not None:
        candidates.append(versions / current)
    digest_prefix = expected_content_digest.removeprefix("sha256:") + "-"
    for version in _iter_version_directories(
        versions,
        error_message="Unable to inspect OCI module cache versions",
    ):
        if version.name.startswith(digest_prefix) and version not in candidates:
            candidates.append(version)
    for version in candidates[:64]:
        root = _validated_cache_root(
            version=version,
            expected_manifest=expected_manifest,
            root_relative=root_relative,
        )
        if root is None:
            continue
        _prune_version_directories(
            versions=versions,
            retain_names={version.name, *(() if current is None else (current,))},
            error_message="Unable to prune stale OCI module cache versions",
        )
        if current != version.name:
            _write_version_pointer(
                slot=slot,
                version_name=version.name,
                error_message="Unable to commit the OCI module cache pointer atomically",
            )
        return root
    return None
