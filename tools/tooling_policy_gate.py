"""Dependency-free launcher for the frozen development artifact policy gate."""

from __future__ import annotations

import json
import platform
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[1]
_VALIDATOR_TIMEOUT_SECONDS = 180


@dataclass(frozen=True)
class LockedManifestEntry:
    path: str
    sha256: str
    size: int


@dataclass(frozen=True)
class LockedArtifactSelection:
    artifact_id: str
    version: str
    platform_id: str
    profile_id: str
    repository: str
    release: str
    source_urls: tuple[str, ...]
    raw_manifest: tuple[LockedManifestEntry, ...]
    installed_manifest: tuple[LockedManifestEntry, ...]


def _locked_manifest_entry(value: object) -> LockedManifestEntry:
    if not isinstance(value, dict):
        raise RuntimeError("development artifact policy failed before acquisition: invalid manifest entry")
    path = value.get("path")
    digest = value.get("sha256")
    size = value.get("size")
    if not isinstance(path, str):
        raise RuntimeError("development artifact policy failed before acquisition: invalid manifest path")
    relative = PurePosixPath(path)
    if (
        path != relative.as_posix()
        or relative.is_absolute()
        or "\\" in path
        or re.match(r"^[A-Za-z]:", path)
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise RuntimeError("development artifact policy failed before acquisition: invalid manifest path")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise RuntimeError("development artifact policy failed before acquisition: invalid manifest digest")
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        raise RuntimeError("development artifact policy failed before acquisition: invalid manifest size")
    return LockedManifestEntry(path, digest, size)


def safe_tooling_cache_parent(repo_root: Path, target: Path, *, artifact_id: str) -> Path:
    """Create a fixed repository cache chain without following symlinks."""

    canonical_root = repo_root.resolve()
    try:
        parts = target.parent.relative_to(repo_root).parts
    except ValueError as exc:
        raise RuntimeError(f"{artifact_id} cache path escapes the repository") from exc
    current = canonical_root
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
            raise RuntimeError(f"unsafe {artifact_id} cache directory")
    return current


def host_platform_id() -> str:
    system = {"Linux": "linux", "Darwin": "macos"}.get(platform.system())
    machine = {
        "aarch64": "arm64",
        "amd64": "x86_64",
        "arm64": "arm64",
        "x86_64": "x86_64",
    }.get(platform.machine().lower())
    if system is None or machine is None:
        raise RuntimeError("development artifact policy does not support this host platform")
    return f"{system}-{machine}"


def _frozen_validator_command(policy_root: Path) -> list[str]:
    validator_python = policy_root / "implementations" / "python" / ".venv" / "bin" / "python"
    project_root = policy_root / "implementations" / "python"
    validator = policy_root / "tools" / "check_tooling_artifact_policy.py"
    if not validator.is_file():
        raise RuntimeError(
            "development artifact policy failed before acquisition: the frozen project validator is unavailable"
        )
    if validator_python.is_file():
        return [str(validator_python), str(validator)]
    uv_executable = shutil.which("uv")
    if (
        uv_executable is None
        or not (project_root / "pyproject.toml").is_file()
        or not (project_root / "uv.lock").is_file()
    ):
        raise RuntimeError(
            "development artifact policy failed before acquisition: the frozen project validator is unavailable"
        )
    return [
        uv_executable,
        "run",
        "--project",
        str(project_root),
        "--frozen",
        "python",
        str(validator),
    ]


def load_tooling_artifact_selection(
    *,
    artifact_id: str,
    version: str,
    platform_id: str,
    profile_id: str,
) -> LockedArtifactSelection:
    """Load one reviewed lock selection before cache lookup or acquisition."""

    policy_root = REPO_ROOT
    validator_command = _frozen_validator_command(policy_root)
    try:
        proc = subprocess.run(
            [
                *validator_command,
                "--select-artifact",
                artifact_id,
                "--version",
                version,
                "--platform-id",
                platform_id,
                "--profile-id",
                profile_id,
            ],
            cwd=policy_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=_VALIDATOR_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(
            "development artifact policy failed before acquisition: the frozen project validator could not complete"
        ) from exc
    if proc.returncode != 0:
        details = proc.stderr.strip() or "the frozen project validator rejected the selection"
        raise RuntimeError(f"development artifact policy failed before acquisition:\n{details}")
    try:
        selection = json.loads(proc.stdout)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise RuntimeError("development artifact policy failed before acquisition: invalid selection response") from exc
    if not isinstance(selection, dict):
        raise RuntimeError("development artifact policy failed before acquisition: invalid selection response")
    try:
        source = selection["source"]
        platform = selection["platform"]
        raw_manifest = tuple(_locked_manifest_entry(item) for item in platform["raw_manifest"])
        installed_manifest = tuple(_locked_manifest_entry(item) for item in platform["installed_manifest"])
        result = LockedArtifactSelection(
            artifact_id=selection["artifact_id"],
            version=selection["version"],
            platform_id=platform["platform_id"],
            profile_id=profile_id,
            repository=source["repository"],
            release=source["release"],
            source_urls=tuple(platform["source_urls"]),
            raw_manifest=raw_manifest,
            installed_manifest=installed_manifest,
        )
        selected_profile_ids = platform["profile_ids"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("development artifact policy failed before acquisition: invalid selection response") from exc
    if (
        result.artifact_id != artifact_id
        or result.version != version
        or result.platform_id != platform_id
        or result.profile_id != profile_id
        or not isinstance(selected_profile_ids, list)
        or profile_id not in selected_profile_ids
        or not result.source_urls
        or not result.raw_manifest
        or not result.installed_manifest
        or any(
            not isinstance(value, str) or not value
            for value in (
                result.platform_id,
                result.repository,
                result.release,
                *result.source_urls,
            )
        )
        or any(
            not isinstance(item.path, str) or not isinstance(item.sha256, str) or not isinstance(item.size, int)
            for item in (*result.raw_manifest, *result.installed_manifest)
        )
    ):
        raise RuntimeError("development artifact policy failed before acquisition: invalid selection response")
    return result
