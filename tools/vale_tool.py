from __future__ import annotations

import io
import platform
import shutil
import stat
import tarfile
from hashlib import sha256
from pathlib import Path
from urllib.error import URLError

from tools.release_download import ReleaseDownloadError
from tools.release_download import retrying_urlopen as urlopen
from tools.tool_versions import VALE_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]

VALE_ARCHIVE_SHA256 = {
    "vale_3.15.2_Linux_64-bit.tar.gz": "fc72e64454d6bd7af91905d4faebbf411bae3eec17bb572f4101311212bc0d9e",
    "vale_3.15.2_Linux_arm64.tar.gz": "e8240a3304e2c07b0476d30423f241a80296865cf6d2b78b128fb7e4e14cbb69",
    "vale_3.15.2_macOS_64-bit.tar.gz": "5d56b292f1612758f6d9e8d735dd739aec4e475830d0ba8c1e0ef7d8f08fa198",
    "vale_3.15.2_macOS_arm64.tar.gz": "d3f613ff9226935ace08895fc8557206f309cdbd3a81881d86b6ab5b8b408757",
}


def _release_base_url(version: str = VALE_VERSION) -> str:
    return f"https://github.com/errata-ai/vale/releases/download/v{version}"


def _release_asset_name(version: str = VALE_VERSION) -> str:
    system = platform.system()
    machine = platform.machine().lower()
    arch_map = {
        "x86_64": "64-bit",
        "amd64": "64-bit",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    platform_map = {
        "Linux": "Linux",
        "Darwin": "macOS",
    }
    arch = arch_map.get(machine)
    platform_name = platform_map.get(system)
    if arch is None:
        raise RuntimeError(f"unsupported Vale architecture: {machine}")
    if platform_name is None:
        raise RuntimeError(f"unsupported Vale platform: {system}")
    return f"vale_{version}_{platform_name}_{arch}.tar.gz"


def vale_binary_path(repo_root: Path = REPO_ROOT, *, version: str = VALE_VERSION) -> Path:
    return repo_root / ".cache" / "raes-sdl" / "tooling" / "vale" / version / "vale"


def _extract_binary(archive_bytes: bytes, binary_path: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        try:
            member = archive.getmember("vale")
        except KeyError as exc:
            raise RuntimeError("Vale archive does not contain a root vale binary") from exc
        if not member.isfile():
            raise RuntimeError("Vale archive root vale member is not a regular file")
        extracted = archive.extractfile(member)
        if extracted is None:
            raise RuntimeError("Vale archive root vale binary cannot be read")
        binary_bytes = extracted.read()

    binary_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = binary_path.with_suffix(".download")
    temporary_path.write_bytes(binary_bytes)
    temporary_path.chmod(temporary_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    shutil.move(temporary_path, binary_path)


def ensure_vale(repo_root: Path = REPO_ROOT, *, version: str = VALE_VERSION) -> Path:
    binary_path = vale_binary_path(repo_root, version=version)
    if binary_path.exists():
        return binary_path

    asset_name = _release_asset_name(version)
    expected = VALE_ARCHIVE_SHA256.get(asset_name)
    if expected is None:
        raise RuntimeError(f"no repository-pinned checksum for Vale asset {asset_name}")
    base_url = _release_base_url(version)
    asset_url = f"{base_url}/{asset_name}"
    try:
        with urlopen(asset_url) as response:  # noqa: S310 - pinned HTTPS release asset
            archive_bytes = response.read()
    except (URLError, ReleaseDownloadError) as exc:
        raise RuntimeError(f"failed to download Vale from {asset_url}: {exc}") from exc
    actual = sha256(archive_bytes).hexdigest()
    if actual != expected:
        raise RuntimeError(f"Vale checksum mismatch for {asset_name}: expected {expected}, got {actual}")

    _extract_binary(archive_bytes, binary_path)
    return binary_path
