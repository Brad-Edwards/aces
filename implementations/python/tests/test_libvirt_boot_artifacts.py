"""Deterministic initramfs and content-addressed kernel cache regressions."""

from __future__ import annotations

import gzip
import os
import stat
import struct
from pathlib import Path

import pytest
from raes_backend_libvirt import _initramfs
from raes_backend_libvirt._initramfs import (
    InitramfsPreflight,
    InitramfsPreflightCode,
    InitramfsToolchainError,
    atomic_write,
    builder_preflight,
    encode_newc,
    resolve_static_busybox,
)
from raes_backend_libvirt.guest_appliance import GuestObservingInitramfsBuilder
from raes_backend_libvirt.techvault_appliance import BusyboxInitramfsBuilder, copy_kernel_for_libvirt


def _write_static_elf(path: Path, *, machine: int = 62, interpreter: bool = False) -> Path:
    identity = b"\x7fELF" + bytes((2, 1, 1, 0)) + b"\0" * 8
    header = struct.pack(
        "<HHIQQQIHHHHHH",
        2,
        machine,
        1,
        0,
        64,
        0,
        0,
        64,
        56,
        1,
        0,
        0,
        0,
    )
    program_header = struct.pack("<IIQQQQQQ", 3 if interpreter else 1, 5, 0, 0, 0, 0, 0, 0)
    path.write_bytes(identity + header + program_header + b"BusyBox" * 256)
    path.chmod(0o755)
    return path


def _write_static_elf32(path: Path) -> Path:
    identity = b"\x7fELF" + bytes((1, 1, 1, 0)) + b"\0" * 8
    header = struct.pack("<HHIIIIIHHHHHH", 2, 62, 1, 0, 52, 0, 0, 52, 32, 1, 0, 0, 0)
    program_header = struct.pack("<IIIIIIII", 1, 0, 0, 0, 0, 5, 0, 0)
    path.write_bytes(identity + header + program_header)
    path.chmod(0o755)
    return path


def _domain() -> dict[str, object]:
    return {
        "name": "webapp",
        "role": "enterprise",
        "interfaces": [{"mac": "52:54:00:00:00:01", "ip": "192.0.2.10", "cidr_prefix": 24}],
        "services": [],
    }


def _parse_newc(payload: bytes) -> list[dict[str, object]]:
    offset = 0
    entries: list[dict[str, object]] = []
    while True:
        assert offset % 4 == 0
        assert payload[offset : offset + 6] == b"070701"
        fields = [int(payload[offset + 6 + index * 8 : offset + 14 + index * 8], 16) for index in range(13)]
        offset += 110
        name_size = fields[11]
        name = os.fsdecode(payload[offset : offset + name_size - 1])
        assert payload[offset + name_size - 1] == 0
        offset += name_size
        offset += -offset % 4
        size = fields[6]
        content = payload[offset : offset + size]
        offset += size
        offset += -offset % 4
        entries.append(
            {
                "name": name,
                "inode": fields[0],
                "mode": fields[1],
                "uid": fields[2],
                "gid": fields[3],
                "mtime": fields[5],
                "devmajor": fields[7],
                "devminor": fields[8],
                "content": content,
            }
        )
        if name == "TRAILER!!!":
            assert payload[offset:] == b""
            return entries


@pytest.mark.parametrize(
    ("prepare", "expected"),
    (
        (lambda path: path, InitramfsPreflightCode.NOT_FOUND),
        (
            lambda path: (path.write_text("not elf", encoding="utf-8"), path)[1],
            InitramfsPreflightCode.NOT_EXECUTABLE,
        ),
        (lambda path: _write_static_elf(path, interpreter=True), InitramfsPreflightCode.NOT_STATIC),
        (lambda path: _write_static_elf(path, machine=183), InitramfsPreflightCode.WRONG_ARCHITECTURE),
    ),
)
def test_static_busybox_preflight_is_typed(tmp_path: Path, prepare, expected: InitramfsPreflightCode) -> None:
    candidate = prepare(tmp_path / "busybox")

    assert resolve_static_busybox(candidate).code is expected


def test_static_busybox_is_injectable_and_path_discoverable(tmp_path: Path) -> None:
    candidate = _write_static_elf(tmp_path / "busybox")

    injected = resolve_static_busybox(candidate)
    discovered = resolve_static_busybox(None, search_path=str(tmp_path))

    assert injected.code is InitramfsPreflightCode.READY
    assert injected.executable == candidate.resolve()
    assert discovered == injected


def test_static_busybox_preflight_covers_discovery_and_file_shapes(tmp_path: Path) -> None:
    relative = resolve_static_busybox(Path("relative-busybox"))
    undiscovered = resolve_static_busybox(None, search_path=str(tmp_path / "empty"))
    directory = tmp_path / "busybox-dir"
    directory.mkdir()
    regular_directory = resolve_static_busybox(directory)
    invalid = tmp_path / "invalid-elf"
    invalid.write_bytes(b"not an elf" * 8)
    invalid.chmod(0o755)

    assert relative.code is InitramfsPreflightCode.NOT_ABSOLUTE
    assert undiscovered.code is InitramfsPreflightCode.NOT_FOUND
    assert regular_directory.code is InitramfsPreflightCode.NOT_REGULAR
    assert resolve_static_busybox(invalid).code is InitramfsPreflightCode.NOT_ELF
    assert resolve_static_busybox(_write_static_elf32(tmp_path / "busybox32")).code is InitramfsPreflightCode.READY


def test_failed_preflight_and_invalid_builder_preflight_are_typed() -> None:
    failure = InitramfsPreflight(InitramfsPreflightCode.NOT_FOUND)

    with pytest.raises(InitramfsToolchainError, match="not-found") as raised:
        failure.require_executable()
    with pytest.raises(TypeError, match="InitramfsPreflight"):
        builder_preflight(type("InvalidBuilder", (), {"preflight": lambda self: "ready"})())

    assert raised.value.preflight is failure


@pytest.mark.parametrize("kind", ("invalid-ident", "invalid-class", "missing-program-header", "truncated"))
def test_malformed_elf_program_tables_are_rejected(tmp_path: Path, kind: str) -> None:
    path = tmp_path / kind
    if kind == "invalid-ident":
        path.write_bytes(b"x" * 64)
    elif kind == "invalid-class":
        path.write_bytes(b"\x7fELF" + bytes((0, 1, 1, 0)) + b"\0" * 56)
    else:
        identity = b"\x7fELF" + bytes((2, 1, 1, 0)) + b"\0" * 8
        phnum = 0 if kind == "missing-program-header" else 1
        header = struct.pack("<HHIQQQIHHHHHH", 2, 62, 1, 0, 64, 0, 0, 64, 56, phnum, 0, 0, 0)
        path.write_bytes(identity + header)
    path.chmod(0o755)

    assert resolve_static_busybox(path).code is InitramfsPreflightCode.NOT_ELF


def test_static_elf_preflight_maps_open_failure_to_typed_result(tmp_path: Path) -> None:
    assert _initramfs._static_elf_preflight(tmp_path, expected_machine=62) is InitramfsPreflightCode.NOT_FOUND


@pytest.mark.parametrize("builder_type", (BusyboxInitramfsBuilder, GuestObservingInitramfsBuilder))
def test_initramfs_builds_are_byte_identical_and_have_zero_gzip_mtime(tmp_path: Path, builder_type) -> None:
    busybox = _write_static_elf(tmp_path / "busybox")
    builder = builder_type(busybox_path=busybox)

    first = builder.build(domain=_domain(), target=tmp_path / "first.cpio.gz")
    os.utime(busybox, ns=(9_000_000_000, 9_000_000_000))
    second = builder.build(domain=_domain(), target=tmp_path / "second.cpio.gz")

    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes()[4:8] == b"\0\0\0\0"
    assert first.read_bytes()[9] == 255


def test_repository_newc_encoder_normalizes_metadata_and_links(tmp_path: Path) -> None:
    busybox = _write_static_elf(tmp_path / "busybox")
    archive = BusyboxInitramfsBuilder(busybox_path=busybox).build(
        domain=_domain(), target=tmp_path / "appliance.cpio.gz"
    )

    entries = _parse_newc(gzip.decompress(archive.read_bytes()))
    by_name = {str(entry["name"]): entry for entry in entries}

    assert [entry["name"] for entry in entries[:-1]] == sorted(entry["name"] for entry in entries[:-1])
    assert entries[-1]["name"] == "TRAILER!!!"
    assert stat.S_IFMT(int(by_name["bin"]["mode"])) == stat.S_IFDIR
    assert stat.S_IMODE(int(by_name["bin"]["mode"])) == 0o755
    assert stat.S_IFMT(int(by_name["bin/busybox"]["mode"])) == stat.S_IFREG
    assert stat.S_IMODE(int(by_name["bin/busybox"]["mode"])) == 0o700
    assert stat.S_IFMT(int(by_name["bin/sh"]["mode"])) == stat.S_IFLNK
    assert by_name["bin/sh"]["content"] == b"busybox"
    assert all(entry[field] == 0 for entry in entries for field in ("uid", "gid", "mtime", "devmajor", "devminor"))
    assert [entry["inode"] for entry in entries] == list(range(1, len(entries) + 1))


def test_guest_initramfs_skips_malformed_content_entries(tmp_path: Path) -> None:
    busybox = _write_static_elf(tmp_path / "busybox")
    domain = {**_domain(), "content": ["not-a-mapping", {"path": "/etc/marker", "content": "ok"}]}
    archive = GuestObservingInitramfsBuilder(busybox_path=busybox).build(
        domain=domain, target=tmp_path / "guest.cpio.gz"
    )

    entries = _parse_newc(gzip.decompress(archive.read_bytes()))
    by_name = {str(entry["name"]): entry for entry in entries}

    assert by_name["etc/raes/guest/files/1"]["content"] == b"ok"
    assert by_name["etc/raes/guest/content"]["content"] == b"/etc/marker|0644|1\n"


def test_newc_encoder_rejects_non_root_and_special_members(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be a directory"):
        encode_newc(tmp_path / "missing")
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO creation is unavailable")
    os.mkfifo(tmp_path / "unsupported")

    with pytest.raises(ValueError, match="unsupported initramfs member"):
        encode_newc(tmp_path)


def test_atomic_write_failure_removes_staged_file_and_preserves_target(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "artifact"
    target.write_bytes(b"previous")
    monkeypatch.setattr(_initramfs.os, "replace", lambda *_args: (_ for _ in ()).throw(OSError("blocked")))

    with pytest.raises(OSError, match="blocked"):
        atomic_write(target, b"replacement", mode=0o644)

    assert target.read_bytes() == b"previous"
    assert list(tmp_path.glob(".artifact.*")) == []


def test_kernel_cache_replaces_same_mtime_different_content_atomically(tmp_path: Path) -> None:
    source = tmp_path / "source-kernel"
    target = tmp_path / "cache" / "kernel"
    source.write_bytes(b"old kernel")
    copy_kernel_for_libvirt(source, target)
    original_mtime = source.stat().st_mtime_ns
    source.write_bytes(b"new kernel")
    os.utime(source, ns=(original_mtime, original_mtime))

    copy_kernel_for_libvirt(source, target)

    assert target.read_bytes() == b"new kernel"
    assert stat.S_IMODE(target.stat().st_mode) == 0o644


def test_kernel_cache_reuses_equal_content_without_replacing_inode(tmp_path: Path) -> None:
    source = tmp_path / "source-kernel"
    target = tmp_path / "cache" / "kernel"
    source.write_bytes(b"same kernel")
    copy_kernel_for_libvirt(source, target)
    inode = target.stat().st_ino

    copy_kernel_for_libvirt(source, target)

    assert target.stat().st_ino == inode


def test_kernel_cache_failure_preserves_previous_complete_target(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source-kernel"
    target = tmp_path / "cache" / "kernel"
    source.write_bytes(b"replacement")
    target.parent.mkdir()
    target.write_bytes(b"known good")
    actual_digest = _initramfs._file_digest
    monkeypatch.setattr(
        _initramfs,
        "_file_digest",
        lambda path: "stale-source-digest" if Path(path) == source else actual_digest(Path(path)),
    )

    with pytest.raises(RuntimeError, match="source changed"):
        copy_kernel_for_libvirt(source, target)

    assert target.read_bytes() == b"known good"
    assert list(target.parent.glob(f".{target.name}.*")) == []
