"""Deterministic initramfs encoding and BusyBox toolchain preflight."""

from __future__ import annotations

import gzip
import hashlib
import os
import shutil
import stat
import struct
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import BinaryIO

from raes_backend_libvirt._observability import LOGGER as _LOGGER
from raes_backend_libvirt._observability import NATIVE_FAILURE_LOG as _NATIVE_FAILURE_LOG

_NEWC_MAGIC = b"070701"
_NEWC_TRAILER = "TRAILER!!!"
_ELF_MACHINE_X86_64 = 62
_PT_INTERP = 3


class InitramfsPreflightCode(str, Enum):
    """Stable outcomes for an appliance executable preflight."""

    READY = "ready"
    NOT_FOUND = "not-found"
    NOT_ABSOLUTE = "not-absolute"
    NOT_REGULAR = "not-regular"
    NOT_EXECUTABLE = "not-executable"
    NOT_ELF = "not-elf"
    WRONG_ARCHITECTURE = "wrong-architecture"
    NOT_STATIC = "not-static"


@dataclass(frozen=True)
class InitramfsPreflight:
    """Typed result of resolving the executable embedded in an initramfs."""

    code: InitramfsPreflightCode
    executable: Path | None = None

    @property
    def ready(self) -> bool:
        return self.code is InitramfsPreflightCode.READY

    def require_executable(self) -> Path:
        if not self.ready or self.executable is None:
            raise InitramfsToolchainError(self)
        return self.executable


class InitramfsToolchainError(RuntimeError):
    """Raised when a builder is invoked after a failed typed preflight."""

    def __init__(self, preflight: InitramfsPreflight) -> None:
        self.preflight = preflight
        super().__init__(f"initramfs toolchain preflight failed: {preflight.code.value}")


@dataclass(frozen=True)
class _ElfProgramHeaders:
    offset: int
    entry_size: int
    count: int
    minimum_entry_size: int
    byte_order: str


def resolve_static_busybox(
    configured: Path | None,
    *,
    search_path: str | None = None,
    expected_elf_machine: int = _ELF_MACHINE_X86_64,
) -> InitramfsPreflight:
    """Resolve an injected or PATH-discovered static target BusyBox executable."""

    candidate, code = _busybox_candidate(configured, search_path=search_path)
    if candidate is not None:
        try:
            candidate = candidate.resolve(strict=True)
        except OSError:
            code = InitramfsPreflightCode.NOT_FOUND
        else:
            code = _busybox_file_preflight(candidate, expected_elf_machine=expected_elf_machine)
    executable = candidate if code is InitramfsPreflightCode.READY else None
    assert code is not None
    return InitramfsPreflight(code, executable)


def _busybox_candidate(
    configured: Path | None, *, search_path: str | None
) -> tuple[Path | None, InitramfsPreflightCode | None]:
    if configured is None:
        discovered = shutil.which("busybox", path=search_path)
        candidate = Path(discovered) if discovered is not None else None
        code = None if candidate is not None else InitramfsPreflightCode.NOT_FOUND
    else:
        candidate = Path(configured)
        code = None if candidate.is_absolute() else InitramfsPreflightCode.NOT_ABSOLUTE
        if code is not None:
            candidate = None
    return candidate, code


def _busybox_file_preflight(candidate: Path, *, expected_elf_machine: int) -> InitramfsPreflightCode:
    if not candidate.is_file():
        code = InitramfsPreflightCode.NOT_REGULAR
    elif not os.access(candidate, os.R_OK | os.X_OK):
        code = InitramfsPreflightCode.NOT_EXECUTABLE
    else:
        code = _static_elf_preflight(candidate, expected_machine=expected_elf_machine)
    return code


def builder_preflight(builder: object) -> InitramfsPreflight:
    """Run an optional typed preflight, preserving injected custom builders."""

    preflight = getattr(builder, "preflight", None)
    if not callable(preflight):
        return InitramfsPreflight(InitramfsPreflightCode.READY)
    result = preflight()
    if not isinstance(result, InitramfsPreflight):
        raise TypeError("initramfs builder preflight must return InitramfsPreflight")
    return result


def encode_newc(root: Path) -> bytes:
    """Encode ``root`` as canonical Linux ``newc`` without host archive tools."""

    root = Path(root)
    if not root.is_dir():
        raise ValueError("initramfs root must be a directory")
    archive = bytearray()
    paths = sorted(root.rglob("*"), key=lambda path: os.fsencode(path.relative_to(root).as_posix()))
    for inode, path in enumerate(paths, start=1):
        relative = path.relative_to(root).as_posix()
        metadata = path.lstat()
        mode = stat.S_IFMT(metadata.st_mode) | stat.S_IMODE(metadata.st_mode)
        if stat.S_ISREG(mode):
            payload = path.read_bytes()
        elif stat.S_ISLNK(mode):
            mode = stat.S_IFLNK | 0o777
            payload = os.fsencode(os.readlink(path))
        elif stat.S_ISDIR(mode):
            mode = stat.S_IFDIR | 0o755
            payload = b""
        else:
            raise ValueError(f"unsupported initramfs member type: {relative!r}")
        _append_newc_entry(archive, relative, payload, inode=inode, mode=mode)
    _append_newc_entry(archive, _NEWC_TRAILER, b"", inode=len(paths) + 1, mode=0)
    return bytes(archive)


def deterministic_gzip(payload: bytes, *, compresslevel: int = 6) -> bytes:
    """Return gzip bytes with a fixed timestamp and platform-neutral OS byte."""

    compressed = bytearray(gzip.compress(payload, compresslevel=compresslevel, mtime=0))
    compressed[9] = 255
    return bytes(compressed)


def atomic_write(path: Path, payload: bytes, *, mode: int) -> Path:
    """Durably stage ``payload`` beside ``path`` and atomically replace it."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except BaseException as exc:
        _LOGGER.debug(_NATIVE_FAILURE_LOG, "atomic_write", exc_info=exc)
        temporary.unlink(missing_ok=True)
        raise
    return path


def atomic_copy_by_digest(source: Path, target: Path, *, mode: int) -> Path:
    """Reuse equal content or atomically replace ``target`` from ``source``."""

    source = Path(source)
    target = Path(target)
    source_digest = _file_digest(source)
    if target.exists() and not target.is_symlink() and target.is_file():
        if _file_digest(target) == source_digest:
            os.chmod(target, mode)
            return target
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    staged_digest = hashlib.sha256()
    try:
        with source.open("rb") as input_stream, os.fdopen(descriptor, "wb") as output_stream:
            while chunk := input_stream.read(1024 * 1024):
                output_stream.write(chunk)
                staged_digest.update(chunk)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        if staged_digest.hexdigest() != source_digest:
            raise RuntimeError("kernel source changed while staging the libvirt cache")
        os.chmod(temporary, mode)
        os.replace(temporary, target)
        _fsync_directory(target.parent)
    except BaseException as exc:
        _LOGGER.debug(_NATIVE_FAILURE_LOG, "atomic_copy_by_digest", exc_info=exc)
        temporary.unlink(missing_ok=True)
        raise
    return target


def _static_elf_preflight(path: Path, *, expected_machine: int) -> InitramfsPreflightCode:
    try:
        with path.open("rb") as stream:
            header = stream.read(64)
            layout, code = _elf_program_headers(header, expected_machine=expected_machine)
            if layout is not None:
                code = _program_header_preflight(stream, layout)
    except OSError:
        code = InitramfsPreflightCode.NOT_FOUND
    assert code is not None
    return code


def _elf_program_headers(
    header: bytes, *, expected_machine: int
) -> tuple[_ElfProgramHeaders | None, InitramfsPreflightCode | None]:
    layout = None
    code = None
    if len(header) < 52 or header[:4] != b"\x7fELF" or header[6] != 1:
        code = InitramfsPreflightCode.NOT_ELF
    else:
        elf_class = header[4]
        byte_order = header[5]
        if elf_class not in {1, 2} or byte_order not in {1, 2} or (elf_class == 2 and len(header) < 58):
            code = InitramfsPreflightCode.NOT_ELF
        else:
            endian = "<" if byte_order == 1 else ">"
            machine = struct.unpack_from(f"{endian}H", header, 18)[0]
            if machine != expected_machine:
                code = InitramfsPreflightCode.WRONG_ARCHITECTURE
            else:
                layout = _program_header_layout(header, elf_class=elf_class, byte_order=endian)
    return layout, code


def _program_header_layout(header: bytes, *, elf_class: int, byte_order: str) -> _ElfProgramHeaders:
    if elf_class == 1:
        offset = struct.unpack_from(f"{byte_order}I", header, 28)[0]
        entry_size = struct.unpack_from(f"{byte_order}H", header, 42)[0]
        count = struct.unpack_from(f"{byte_order}H", header, 44)[0]
        minimum_entry_size = 32
    else:
        offset = struct.unpack_from(f"{byte_order}Q", header, 32)[0]
        entry_size = struct.unpack_from(f"{byte_order}H", header, 54)[0]
        count = struct.unpack_from(f"{byte_order}H", header, 56)[0]
        minimum_entry_size = 56
    return _ElfProgramHeaders(
        offset=offset,
        entry_size=entry_size,
        count=count,
        minimum_entry_size=minimum_entry_size,
        byte_order=byte_order,
    )


def _program_header_preflight(stream: BinaryIO, layout: _ElfProgramHeaders) -> InitramfsPreflightCode:
    if layout.count < 1 or layout.count > 1024 or layout.entry_size < layout.minimum_entry_size:
        return InitramfsPreflightCode.NOT_ELF
    stream.seek(layout.offset)
    code = InitramfsPreflightCode.READY
    for _ in range(layout.count):
        entry = stream.read(layout.entry_size)
        if len(entry) != layout.entry_size:
            code = InitramfsPreflightCode.NOT_ELF
            break
        if struct.unpack_from(f"{layout.byte_order}I", entry)[0] == _PT_INTERP:
            code = InitramfsPreflightCode.NOT_STATIC
            break
    return code


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _append_newc_entry(archive: bytearray, name: str, payload: bytes, *, inode: int, mode: int) -> None:
    encoded_name = os.fsencode(name)
    fields = (
        inode,
        mode,
        0,  # uid
        0,  # gid
        2 if stat.S_ISDIR(mode) else 1,
        0,  # mtime
        len(payload),
        0,  # devmajor
        0,  # devminor
        0,  # rdevmajor
        0,  # rdevminor
        len(encoded_name) + 1,
        0,  # check
    )
    archive.extend(_NEWC_MAGIC)
    archive.extend("".join(f"{value:08x}" for value in fields).encode("ascii"))
    archive.extend(encoded_name)
    archive.append(0)
    _align_four(archive)
    archive.extend(payload)
    _align_four(archive)


def _align_four(payload: bytearray) -> None:
    payload.extend(b"\0" * (-len(payload) % 4))


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


__all__ = [
    "InitramfsPreflight",
    "InitramfsPreflightCode",
    "InitramfsToolchainError",
    "atomic_copy_by_digest",
    "atomic_write",
    "builder_preflight",
    "deterministic_gzip",
    "encode_newc",
    "resolve_static_busybox",
]
