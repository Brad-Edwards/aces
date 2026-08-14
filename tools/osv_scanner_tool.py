from __future__ import annotations

import os
import platform
import stat
import subprocess
import tempfile
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from tools.http_download import download_bytes
from tools.tool_versions import OSV_SCANNER_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]

# Exit codes osv-scanner uses for scan results. Any other code (for example,
# 127 for a general error or 128 when no packages were found) is a scanner or
# setup failure, not a vulnerability result.
# See https://google.github.io/osv-scanner/output/#return-codes
OSV_CLEAN_EXIT_CODE = 0
OSV_FINDINGS_EXIT_CODE = 1
_MAX_BINARY_BYTES = 256 * 1024 * 1024
_DOWNLOAD_TIMEOUT_SECONDS = 60

OSV_SCANNER_SHA256 = {
    "2.4.0": {
        "osv-scanner_darwin_amd64": "088119325156321c34c456ac3703d6013538fd71cbac82b891ab34db491e4d66",
        "osv-scanner_darwin_arm64": "9ca3185ad63e9ab54f7cb90f46a7362be02d80e37f0123d095a54355ea202f5d",
        "osv-scanner_linux_amd64": "15314940c10d26af9c6649f150b8a47c1262e8fc7e17b1d1029b0e479e8ed8a0",
        "osv-scanner_linux_arm64": "44e580752910f0ff36ec99aff59af20f65df1e859aa31e5605a8f0d055b496e9",
    }
}


class OSVScanOutcome(StrEnum):
    CLEAN = "clean"
    FINDINGS = "findings"
    SCANNER_ERROR = "scanner-error"


def classify_osv_exit_code(exit_code: int) -> OSVScanOutcome:
    """Classify a scanner result without conflating findings with tool errors."""
    if exit_code == OSV_CLEAN_EXIT_CODE:
        return OSVScanOutcome.CLEAN
    if exit_code == OSV_FINDINGS_EXIT_CODE:
        return OSVScanOutcome.FINDINGS
    return OSVScanOutcome.SCANNER_ERROR


def _release_base_url(version: str = OSV_SCANNER_VERSION) -> str:
    return f"https://github.com/google/osv-scanner/releases/download/v{version}"


def _release_asset_name() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    platform_map = {
        "Linux": "linux",
        "Darwin": "darwin",
    }
    arch = arch_map.get(machine)
    platform_name = platform_map.get(system)
    if arch is None:
        raise RuntimeError(f"unsupported osv-scanner architecture: {machine}")
    if platform_name is None:
        raise RuntimeError(f"unsupported osv-scanner platform: {system}")
    # OSV-Scanner publishes plain, per-platform binaries (no archive), e.g.
    # `osv-scanner_linux_amd64`.
    return f"osv-scanner_{platform_name}_{arch}"


def osv_scanner_binary_path(repo_root: Path = REPO_ROOT, *, version: str = OSV_SCANNER_VERSION) -> Path:
    return repo_root / ".cache" / "raes-sdl" / "tooling" / "osv-scanner" / version / "osv-scanner"


def _sha256_path(path: Path) -> str:
    """Hash one bounded regular file without following its final component."""

    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > _MAX_BINARY_BYTES:
        raise OSError("cached scanner is not a bounded regular file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOINHERIT", 0)
    descriptor = os.open(path, flags)
    digest = sha256()
    total = 0
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(before, opened):
            raise OSError("cached scanner changed while it was opened")
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            if total > _MAX_BINARY_BYTES:
                raise OSError("cached scanner exceeds the size bound")
            digest.update(chunk)
    after = path.lstat()
    if total != opened.st_size or not stat.S_ISREG(after.st_mode) or not os.path.samestat(opened, after):
        raise OSError("cached scanner changed while it was hashed")
    return digest.hexdigest()


def _safe_cache_parent(repo_root: Path, binary_path: Path) -> Path:
    """Create the fixed cache chain without following repository-local symlinks."""

    root = repo_root.resolve()
    try:
        parts = binary_path.parent.relative_to(repo_root).parts
    except ValueError as exc:
        raise RuntimeError("osv-scanner cache path escapes the repository") from exc
    current = root
    for part in parts:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            try:
                current.mkdir()
                continue
            except FileExistsError:
                mode = current.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise RuntimeError(f"unsafe osv-scanner cache directory: {current}")
    return current


def _validated_cache_hit(binary_path: Path, expected_checksum: str) -> bool:
    try:
        mode = binary_path.lstat().st_mode
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(mode):
        binary_path.unlink()
        return False
    if not stat.S_ISREG(mode):
        raise RuntimeError(f"unsafe osv-scanner cache entry: {binary_path} is not a regular file")
    try:
        actual_checksum = _sha256_path(binary_path)
    except OSError as exc:
        raise RuntimeError(f"failed to validate cached osv-scanner at {binary_path}") from exc
    try:
        final_mode = binary_path.lstat().st_mode
    except OSError as exc:
        raise RuntimeError(f"failed to validate cached osv-scanner at {binary_path}") from exc
    valid = stat.S_ISREG(final_mode) and actual_checksum == expected_checksum and bool(final_mode & stat.S_IXUSR)
    if not valid:
        binary_path.unlink()
    return valid


def _install_binary(binary_path: Path, binary_bytes: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{binary_path.name}.",
        suffix=".download",
        dir=binary_path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(binary_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.chmod(0o755)
        os.replace(temporary_path, binary_path)
        directory_descriptor = os.open(binary_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        temporary_path.unlink(missing_ok=True)


def ensure_osv_scanner(repo_root: Path = REPO_ROOT, *, version: str = OSV_SCANNER_VERSION) -> Path:
    asset_name = _release_asset_name()
    expected_checksum = OSV_SCANNER_SHA256.get(version, {}).get(asset_name)
    if expected_checksum is None:
        raise RuntimeError(f"no repository-pinned checksum for osv-scanner asset {asset_name}")
    requested_path = osv_scanner_binary_path(repo_root, version=version)
    binary_path = _safe_cache_parent(repo_root, requested_path) / requested_path.name
    if _validated_cache_hit(binary_path, expected_checksum):
        return binary_path

    base_url = _release_base_url(version)
    asset_url = f"{base_url}/{asset_name}"
    if not asset_url.startswith("https://github.com/google/osv-scanner/releases/download/"):
        raise RuntimeError(f"unsafe osv-scanner release URL: {asset_url}")

    binary_bytes = download_bytes(
        asset_url,
        description="osv-scanner",
        timeout_seconds=_DOWNLOAD_TIMEOUT_SECONDS,
        max_bytes=_MAX_BINARY_BYTES,
    )
    if len(binary_bytes) > _MAX_BINARY_BYTES:
        raise RuntimeError(f"osv-scanner asset {asset_name} exceeds the download limit")

    actual_checksum = sha256(binary_bytes).hexdigest()
    if actual_checksum != expected_checksum:
        raise RuntimeError(
            f"osv-scanner checksum mismatch for {asset_name}: expected {expected_checksum}, got {actual_checksum}"
        )

    _install_binary(binary_path, binary_bytes)

    return binary_path


def run_osv_scanner(lockfile: Path, report_path: Path, *, binary: Path) -> int:
    """Scan a single lockfile and write the JSON report, returning the exit code.

    OSV-Scanner writes the machine-readable report to stdout under
    ``--format json`` and progress/logging to stderr, so redirecting stdout to
    ``report_path`` captures a clean JSON document. The caller classifies the
    result with :func:`classify_osv_exit_code` and applies repository policy.
    """
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("wb") as report_file:
        completed = subprocess.run(  # noqa: S603  # trusted, checksum-verified binary; fixed argv
            [
                str(binary),
                "scan",
                "source",
                "--lockfile",
                str(lockfile),
                "--format",
                "json",
            ],
            stdout=report_file,
            check=False,
        )
    return completed.returncode
