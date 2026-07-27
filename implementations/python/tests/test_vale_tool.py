"""Tests for the pinned repository-local Vale installer."""

from __future__ import annotations

import io
import sys
import tarfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.vale_tool as vale_tool  # noqa: E402


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Linux", "x86_64", "vale_3.15.2_Linux_64-bit.tar.gz"),
        ("Linux", "aarch64", "vale_3.15.2_Linux_arm64.tar.gz"),
        ("Darwin", "x86_64", "vale_3.15.2_macOS_64-bit.tar.gz"),
        ("Darwin", "arm64", "vale_3.15.2_macOS_arm64.tar.gz"),
    ],
)
def test_vale_release_asset_matches_supported_platform(
    monkeypatch: pytest.MonkeyPatch,
    system: str,
    machine: str,
    expected: str,
) -> None:
    monkeypatch.setattr("platform.system", lambda: system)
    monkeypatch.setattr("platform.machine", lambda: machine)

    assert vale_tool._release_asset_name("3.15.2") == expected


def test_vale_binary_uses_versioned_repository_cache(tmp_path: Path) -> None:
    assert vale_tool.vale_binary_path(tmp_path, version="3.15.2") == (
        tmp_path / ".cache" / "raes-sdl" / "tooling" / "vale" / "3.15.2" / "vale"
    )


def test_vale_assets_have_repository_pinned_checksums() -> None:
    assert vale_tool.VALE_ARCHIVE_SHA256 == {
        "vale_3.15.2_Linux_64-bit.tar.gz": "fc72e64454d6bd7af91905d4faebbf411bae3eec17bb572f4101311212bc0d9e",
        "vale_3.15.2_Linux_arm64.tar.gz": "e8240a3304e2c07b0476d30423f241a80296865cf6d2b78b128fb7e4e14cbb69",
        "vale_3.15.2_macOS_64-bit.tar.gz": "5d56b292f1612758f6d9e8d735dd739aec4e475830d0ba8c1e0ef7d8f08fa198",
        "vale_3.15.2_macOS_arm64.tar.gz": "d3f613ff9226935ace08895fc8557206f309cdbd3a81881d86b6ab5b8b408757",
    }


def test_vale_rejects_an_asset_without_a_repository_pin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(vale_tool, "_release_asset_name", lambda _version: "vale_unpinned.tar.gz")

    with pytest.raises(RuntimeError, match="no repository-pinned checksum"):
        vale_tool.ensure_vale(tmp_path, version="3.15.2")


def test_vale_extraction_rejects_archive_without_root_binary(tmp_path: Path) -> None:
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w:gz") as archive:
        info = tarfile.TarInfo("../vale")
        body = b"unsafe"
        info.size = len(body)
        archive.addfile(info, io.BytesIO(body))

    with pytest.raises(RuntimeError, match="root vale binary"):
        vale_tool._extract_binary(payload.getvalue(), tmp_path / "vale")
