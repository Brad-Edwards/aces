from __future__ import annotations

import platform
import shutil
import stat
import subprocess
from hashlib import sha256
from pathlib import Path

from tools.http_download import download_bytes
from tools.tool_versions import OSV_SCANNER_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]

# Exit codes osv-scanner uses for a scan that ran successfully:
#   0 -> packages found, no vulnerabilities/findings
#   1 -> packages found, vulnerabilities/findings present (advisory here)
# Any other code (e.g. 127 general error, 128 no packages found) indicates a
# scanner or setup failure that must be surfaced, not silently swallowed.
# See https://google.github.io/osv-scanner/output/#return-codes
OSV_ADVISORY_EXIT_CODES = frozenset({0, 1})


def _release_base_url(version: str = OSV_SCANNER_VERSION) -> str:
    return f"https://github.com/google/osv-scanner/releases/download/v{version}"


def _release_asset_name(version: str = OSV_SCANNER_VERSION) -> str:
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


def _checksums_asset_name(_version: str = OSV_SCANNER_VERSION) -> str:
    return "osv-scanner_SHA256SUMS"


def osv_scanner_binary_path(repo_root: Path = REPO_ROOT, *, version: str = OSV_SCANNER_VERSION) -> Path:
    return repo_root / ".cache" / "raes-sdl" / "tooling" / "osv-scanner" / version / "osv-scanner"


def _expected_checksum(checksums_text: str, asset_name: str) -> str | None:
    for line in checksums_text.splitlines():
        checksum, _, name = line.partition("  ")
        if name.strip() == asset_name:
            return checksum.strip()
    return None


def ensure_osv_scanner(repo_root: Path = REPO_ROOT, *, version: str = OSV_SCANNER_VERSION) -> Path:
    binary_path = osv_scanner_binary_path(repo_root, version=version)
    if binary_path.exists():
        return binary_path

    binary_path.parent.mkdir(parents=True, exist_ok=True)
    asset_name = _release_asset_name(version)
    base_url = _release_base_url(version)
    asset_url = f"{base_url}/{asset_name}"
    checksums_url = f"{base_url}/{_checksums_asset_name(version)}"

    checksums_text = download_bytes(checksums_url, description="osv-scanner checksums").decode("utf-8")

    expected_checksum = _expected_checksum(checksums_text, asset_name)
    if not expected_checksum:
        raise RuntimeError(f"missing checksum for osv-scanner asset {asset_name}")

    binary_bytes = download_bytes(asset_url, description="osv-scanner")

    actual_checksum = sha256(binary_bytes).hexdigest()
    if actual_checksum != expected_checksum:
        raise RuntimeError(
            f"osv-scanner checksum mismatch for {asset_name}: expected {expected_checksum}, got {actual_checksum}"
        )

    # Atomic-ish install: write to a sibling temp path, chmod, then move into place.
    tmp_path = binary_path.with_suffix(".download")
    tmp_path.write_bytes(binary_bytes)
    tmp_path.chmod(tmp_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    shutil.move(tmp_path, binary_path)

    return binary_path


def run_osv_scanner(lockfile: Path, report_path: Path, *, binary: Path) -> int:
    """Scan a single lockfile and write the JSON report, returning the exit code.

    OSV-Scanner writes the machine-readable report to stdout under
    ``--format json`` and progress/logging to stderr, so redirecting stdout to
    ``report_path`` captures a clean JSON document. The caller decides whether a
    given exit code is advisory (see ``OSV_ADVISORY_EXIT_CODES``) or fatal.
    """
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("wb") as report_file:
        completed = subprocess.run(  # noqa: S603 - trusted, checksum-verified binary; fixed argv
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
