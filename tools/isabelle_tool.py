from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.tool_versions import ISABELLE_VERSION  # noqa: E402

ISABELLE_ARCHIVE_NAME = f"Isabelle{ISABELLE_VERSION}_linux.tar.gz"
ISABELLE_SESSION = "Participant_Opacity"
ISABELLE_SESSION_RELATIVE_PATH = Path("specs/formal/participant-semantics/isabelle")
ISABELLE_LOCALE = "C.UTF-8"
ISABELLE_BUILD_TIMEOUT_SECONDS = 600
ISABELLE_OUTPUT_LIMIT_BYTES = 64 * 1024
ISABELLE_FILE_LIMIT_BYTES = 4 * 1024 * 1024 * 1024
ISABELLE_PROCESS_ADDRESS_SPACE_LIMIT_MIB = 32768
ISABELLE_JAVA_MAX_HEAP_MIB = 2048
ISABELLE_ML_MAX_HEAP_MIB = 2048
ISABELLE_SANDBOX_HOME = Path("/opt/isabelle")
ISABELLE_SANDBOX_SESSION_ROOT = Path("/workspace/session")
ISABELLE_SANDBOX_STATE_ROOT = Path("/state")
ISABELLE_SYSTEM_RUNTIME_PATHS = (
    Path("/usr/bin"),
    Path("/usr/lib"),
    Path("/usr/lib64"),
    Path("/usr/share/locale"),
    Path("/usr/share/fontconfig"),
    Path("/usr/share/fonts"),
    Path("/usr/share/zoneinfo"),
    Path("/lib"),
    Path("/lib64"),
    Path("/etc/fonts"),
    Path("/etc/ld.so.cache"),
    Path("/var/cache/fontconfig"),
)
ISABELLE_REQUIRED_FONTCONFIG_PATHS = (
    Path("/etc/fonts"),
    Path("/usr/share/fonts"),
)
ISABELLE_FONTCONFIG_LIST = Path("/usr/bin/fc-list")
ISABELLE_FONTCONFIG_QUERY_TIMEOUT_SECONDS = 10
_DOWNLOAD_CHUNK_BYTES = 1024 * 1024


class IsabelleToolError(RuntimeError):
    """A bounded operational failure from the pinned proof tool."""


def isabelle_cache_root(repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / ".cache" / "raes-sdl" / "tooling"


def isabelle_archive_path(repo_root: Path = REPO_ROOT) -> Path:
    return isabelle_cache_root(repo_root) / "archives" / ISABELLE_ARCHIVE_NAME


def isabelle_home(repo_root: Path = REPO_ROOT) -> Path:
    return isabelle_cache_root(repo_root) / "isabelle" / f"Isabelle{ISABELLE_VERSION}"


def _installation_marker(repo_root: Path = REPO_ROOT) -> Path:
    return isabelle_home(repo_root).parent / f"Isabelle{ISABELLE_VERSION}.archive.sha256"


def _reject_unsafe_cache_directory(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise IsabelleToolError("unsafe Isabelle cache directory")


def _write_installation_marker(path: Path, digest: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=".isabelle-marker-", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(f"{digest}\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_DOWNLOAD_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_archive(path: Path, *, expected_sha256: str, expected_size: int) -> None:
    try:
        status = path.lstat()
    except OSError as exc:
        raise IsabelleToolError("pinned Isabelle archive is unavailable") from exc
    if not stat.S_ISREG(status.st_mode) or status.st_size != expected_size or _sha256_file(path) != expected_sha256:
        raise IsabelleToolError("pinned Isabelle archive checksum or size mismatch")


def _download_archive_from_url(
    url: str,
    temporary_path: Path,
    *,
    expected_sha256: str,
    expected_size: int,
) -> None:
    digest = hashlib.sha256()
    total = 0
    response = urlopen(url, timeout=60)  # noqa: S310 - allowlisted official Isabelle release URLs
    with response, temporary_path.open("wb") as output:
        for chunk in iter(lambda: response.read(_DOWNLOAD_CHUNK_BYTES), b""):
            total += len(chunk)
            if total > expected_size:
                raise IsabelleToolError("download exceeded its declared size")
            digest.update(chunk)
            output.write(chunk)
    if total != expected_size or digest.hexdigest() != expected_sha256:
        raise IsabelleToolError("download checksum or size mismatch")


def _download_archive(
    path: Path,
    *,
    source_urls: tuple[str, ...],
    expected_sha256: str,
    expected_size: int,
) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=".isabelle-", suffix=".download", dir=path.parent)
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    failures: list[str] = []
    for url in source_urls:
        temporary_path.unlink(missing_ok=True)
        try:
            _download_archive_from_url(
                url,
                temporary_path,
                expected_sha256=expected_sha256,
                expected_size=expected_size,
            )
        except (HTTPError, URLError, TimeoutError, OSError, IsabelleToolError) as exc:
            failures.append(f"{url}: {type(exc).__name__}")
            continue
        temporary_path.replace(path)
        return
    temporary_path.unlink(missing_ok=True)
    raise IsabelleToolError(f"pinned Isabelle download failed from all official mirrors ({'; '.join(failures)})")


def _extract_archive(archive_path: Path, destination: Path, *, installed_path: str) -> None:
    expected_root = f"Isabelle{ISABELLE_VERSION}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="isabelle-extract-", dir=destination.parent) as temporary:
        temporary_root = Path(temporary)
        try:
            with tarfile.open(archive_path, mode="r:gz") as archive:
                top_levels = {Path(member.name).parts[0] for member in archive.getmembers() if Path(member.name).parts}
                if top_levels != {expected_root}:
                    raise IsabelleToolError("pinned Isabelle archive has an unexpected root")
                try:
                    installed_member = archive.getmember(installed_path)
                except KeyError as exc:
                    raise IsabelleToolError("pinned Isabelle archive lacks its locked executable") from exc
                if not installed_member.isfile():
                    raise IsabelleToolError("pinned Isabelle locked executable is not a regular archive member")
                archive.extractall(temporary_root, filter="data")
        except (OSError, tarfile.TarError) as exc:
            raise IsabelleToolError("pinned Isabelle archive extraction failed") from exc
        extracted = temporary_root / expected_root
        binary = extracted / "bin" / "isabelle"
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise IsabelleToolError("pinned Isabelle archive lacks its executable")
        if destination.exists():
            shutil.rmtree(destination)
        extracted.replace(destination)


def acquire_isabelle(repo_root: Path = REPO_ROOT) -> Path:
    """Acquire and checksum-verify the pinned development-only distribution."""

    from tools.tooling_policy_gate import (
        load_tooling_artifact_selection,
        safe_tooling_cache_parent,
    )

    selection = load_tooling_artifact_selection(
        artifact_id="isabelle",
        version=ISABELLE_VERSION,
        platform_id="linux-x86_64",
        profile_id="proof-linux-x86_64",
    )
    if len(selection.raw_manifest) != 1 or len(selection.installed_manifest) != 1:
        raise IsabelleToolError("Isabelle lock selection must contain one raw archive and installed executable")
    raw = selection.raw_manifest[0]
    installed = selection.installed_manifest[0]
    if platform.system() != "Linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        raise IsabelleToolError("the pinned Isabelle proof tool supports Linux x86_64 only")
    requested_archive_path = isabelle_archive_path(repo_root)
    archive_path = (
        safe_tooling_cache_parent(repo_root, requested_archive_path, artifact_id="Isabelle")
        / requested_archive_path.name
    )
    home = isabelle_home(repo_root)
    safe_tooling_cache_parent(repo_root, home, artifact_id="Isabelle")
    _reject_unsafe_cache_directory(home)
    if not archive_path.exists():
        _download_archive(
            archive_path,
            source_urls=selection.source_urls,
            expected_sha256=raw.sha256,
            expected_size=raw.size,
        )
    _verify_archive(archive_path, expected_sha256=raw.sha256, expected_size=raw.size)
    try:
        installed_relative_path = Path(installed.path).relative_to(f"Isabelle{ISABELLE_VERSION}")
    except ValueError as exc:
        raise IsabelleToolError("Isabelle installed manifest escapes the selected distribution") from exc
    binary = home / installed_relative_path
    if not binary.is_file():
        _extract_archive(archive_path, home, installed_path=installed.path)
    try:
        binary_status = binary.lstat()
    except OSError as exc:
        raise IsabelleToolError("pinned Isabelle executable is unavailable") from exc
    if (
        not stat.S_ISREG(binary_status.st_mode)
        or binary_status.st_size != installed.size
        or _sha256_file(binary) != installed.sha256
        or not os.access(binary, os.X_OK)
    ):
        raise IsabelleToolError("pinned Isabelle executable differs from the reviewed lock manifest")
    marker = _installation_marker(repo_root)
    _write_installation_marker(marker, raw.sha256)
    return home


def require_isabelle(repo_root: Path = REPO_ROOT) -> Path:
    """Resolve a previously acquired distribution without any network access."""

    from tools.tooling_policy_gate import (
        load_tooling_artifact_selection,
        safe_tooling_cache_parent,
    )

    selection = load_tooling_artifact_selection(
        artifact_id="isabelle",
        version=ISABELLE_VERSION,
        platform_id="linux-x86_64",
        profile_id="proof-linux-x86_64",
    )
    if len(selection.raw_manifest) != 1 or len(selection.installed_manifest) != 1:
        raise IsabelleToolError("Isabelle lock selection must contain one raw archive and installed executable")
    raw = selection.raw_manifest[0]
    installed = selection.installed_manifest[0]
    home = isabelle_home(repo_root)
    safe_tooling_cache_parent(repo_root, home, artifact_id="Isabelle")
    _reject_unsafe_cache_directory(home)
    marker = _installation_marker(repo_root)
    try:
        installed_relative_path = Path(installed.path).relative_to(f"Isabelle{ISABELLE_VERSION}")
    except ValueError as exc:
        raise IsabelleToolError("Isabelle installed manifest escapes the selected distribution") from exc
    binary = home / installed_relative_path
    try:
        if not stat.S_ISREG(marker.lstat().st_mode):
            raise IsabelleToolError("pinned Isabelle installation marker or executable is invalid")
        installed_digest = marker.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise IsabelleToolError("pinned Isabelle is not acquired; run the acquire command first") from exc
    try:
        binary_status = binary.lstat()
    except OSError as exc:
        raise IsabelleToolError("pinned Isabelle installation marker or executable is invalid") from exc
    if (
        installed_digest != raw.sha256
        or not stat.S_ISREG(binary_status.st_mode)
        or binary_status.st_size != installed.size
        or _sha256_file(binary) != installed.sha256
        or not os.access(binary, os.X_OK)
    ):
        raise IsabelleToolError("pinned Isabelle installation marker or executable is invalid")
    return home


def _proof_process_limits() -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(
        resource.RLIMIT_CPU,
        (ISABELLE_BUILD_TIMEOUT_SECONDS, ISABELLE_BUILD_TIMEOUT_SECONDS),
    )
    resource.setrlimit(resource.RLIMIT_FSIZE, (ISABELLE_FILE_LIMIT_BYTES, ISABELLE_FILE_LIMIT_BYTES))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    address_space_bytes = ISABELLE_PROCESS_ADDRESS_SPACE_LIMIT_MIB * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (address_space_bytes, address_space_bytes))


def _read_bounded_output(path: Path) -> str:
    with path.open("rb") as stream:
        payload = stream.read(ISABELLE_OUTPUT_LIMIT_BYTES + 1)
    if len(payload) > ISABELLE_OUTPUT_LIMIT_BYTES:
        raise IsabelleToolError("Isabelle build output exceeded the verification bound")
    return payload.decode("utf-8", errors="replace")


def expected_isabelle_result() -> dict[str, object]:
    result: dict[str, object] = {
        "prover": "Isabelle/HOL",
        "prover_version": f"Isabelle{ISABELLE_VERSION}",
        "session": ISABELLE_SESSION,
        "result": "kernel-checked",
        "network": "blocked-by-bubblewrap-network-namespace",
        "filesystem": "allowlisted-runtime-session-and-private-state-only",
        "locale": ISABELLE_LOCALE,
        "platform_boundary": "linux-x86_64",
    }
    encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    result["result_digest"] = f"sha256:{hashlib.sha256(encoded).hexdigest()}"
    return result


def _proof_sandbox_command(
    *,
    bwrap: Path,
    home: Path,
    session_root: Path,
    state_root: Path,
) -> list[str]:
    """Build the fixed proof sandbox without exposing the host root or home."""

    command = [
        str(bwrap),
        "--unshare-net",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--die-with-parent",
        "--new-session",
        "--clearenv",
        "--dir",
        "/opt",
        "--dir",
        "/workspace",
        "--dir",
        "/usr",
        "--dir",
        "/usr/share",
        "--dir",
        "/etc",
        "--dir",
        "/var",
        "--dir",
        "/var/cache",
    ]
    for runtime_path in ISABELLE_SYSTEM_RUNTIME_PATHS:
        if runtime_path.exists():
            command.extend(("--ro-bind", str(runtime_path), str(runtime_path)))
    command.extend(
        (
            "--ro-bind",
            str(home),
            str(ISABELLE_SANDBOX_HOME),
            "--ro-bind",
            str(session_root),
            str(ISABELLE_SANDBOX_SESSION_ROOT),
            "--bind",
            str(state_root),
            str(ISABELLE_SANDBOX_STATE_ROOT),
            "--dev",
            "/dev",
            "--proc",
            "/proc",
            "--tmpfs",
            "/tmp",  # noqa: S108 - private bubblewrap tmpfs, not a shared host path
            "--chdir",
            "/workspace",
            "--setenv",
            "PATH",
            "/usr/bin",
            "--setenv",
            "HOME",
            "/state/user",
            "--setenv",
            "USER_HOME",
            "/state/user",
            "--setenv",
            "ISABELLE_HOME_USER",
            "/state/isabelle-user",
            "--setenv",
            "LANG",
            ISABELLE_LOCALE,
            "--setenv",
            "LC_ALL",
            ISABELLE_LOCALE,
            "--setenv",
            "TZ",
            "UTC",
            str(ISABELLE_SANDBOX_HOME / "bin" / "isabelle"),
            "build",
            "-o",
            "threads=2",
            "-o",
            "timeout=300",
            "-D",
            str(ISABELLE_SANDBOX_SESSION_ROOT),
        )
    )
    return command


def _fontconfig_has_fonts(font_list: Path = ISABELLE_FONTCONFIG_LIST) -> bool:
    """Return whether the fixed host fontconfig tool finds an installed font."""

    if not font_list.is_file() or not os.access(font_list, os.X_OK):
        return False
    try:
        completed = subprocess.run(
            [str(font_list), "--format=%{file}\\n"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=ISABELLE_FONTCONFIG_QUERY_TIMEOUT_SECONDS,
            env={"LANG": ISABELLE_LOCALE, "LC_ALL": ISABELLE_LOCALE},
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0 and bool(completed.stdout.strip())


def _require_fontconfig_runtime(
    paths: tuple[Path, ...] = ISABELLE_REQUIRED_FONTCONFIG_PATHS,
    *,
    font_query: Callable[[], bool] = _fontconfig_has_fonts,
) -> None:
    """Fail before sandbox entry when the pinned prover's font runtime is absent."""

    if any(not path.is_dir() for path in paths) or not font_query():
        raise IsabelleToolError("fontconfig runtime is required for offline proof replay")


def _bubblewrap_setup_failed(output: str) -> bool:
    """Return whether bubblewrap failed before the fixed prover could start."""

    return output.lstrip().startswith("bwrap:")


def run_isabelle_build(repo_root: Path = REPO_ROOT) -> dict[str, object]:
    """Kernel-check the fixed session in a network-isolated, bounded process."""

    home = require_isabelle(repo_root)
    bwrap = Path("/usr/bin/bwrap")
    if not bwrap.is_file():
        raise IsabelleToolError("bubblewrap is required to enforce offline proof replay")
    _require_fontconfig_runtime()
    session_root = (repo_root / ISABELLE_SESSION_RELATIVE_PATH).resolve()
    if not session_root.is_dir() or repo_root.resolve() not in session_root.parents:
        raise IsabelleToolError("the fixed Isabelle session root is unavailable")

    with tempfile.TemporaryDirectory(prefix="isabelle-proof-") as temporary:
        state_root = Path(temporary).resolve()
        output_path = state_root / "build-output.log"
        user_home = state_root / "user"
        isabelle_user = state_root / "isabelle-user"
        user_home.mkdir()
        isabelle_user.mkdir()
        (isabelle_user / "etc").mkdir()
        (isabelle_user / "etc" / "settings").write_text(
            f'ISABELLE_TOOL_JAVA_OPTIONS="-Djava.awt.headless=true -Xms256m -Xmx{ISABELLE_JAVA_MAX_HEAP_MIB}m -Xss8m"\n'
            f'ML_OPTIONS="--minheap 256 --maxheap {ISABELLE_ML_MAX_HEAP_MIB}"\n',
            encoding="ascii",
        )
        command = _proof_sandbox_command(
            bwrap=bwrap,
            home=home,
            session_root=session_root,
            state_root=state_root,
        )
        try:
            with output_path.open("wb") as output:
                completed = subprocess.run(  # noqa: S603 - fixed checksum-verified tool and argv
                    command,
                    cwd=repo_root,
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=ISABELLE_BUILD_TIMEOUT_SECONDS,
                    env={},
                    preexec_fn=_proof_process_limits,
                )
        except subprocess.TimeoutExpired as exc:
            raise IsabelleToolError("Isabelle proof replay exceeded its wall-time bound") from exc
        output = _read_bounded_output(output_path)
        if completed.returncode != 0:
            if _bubblewrap_setup_failed(output):
                raise IsabelleToolError("bubblewrap network isolation is unavailable for offline proof replay")
            failure_tail = output.strip()[-4096:]
            detail = f":\n{failure_tail}" if failure_tail else ""
            raise IsabelleToolError(f"Isabelle kernel rejected the fixed proof session{detail}")
        if "Unfinished session(s)" in output or f"Finished {ISABELLE_SESSION}" not in output:
            raise IsabelleToolError("Isabelle build did not report a finished proof session")

    return expected_isabelle_result()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Acquire or replay the pinned participant-opacity proof tool.")
    parser.add_argument("command", choices=("acquire", "verify"))
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.command == "acquire":
            acquire_isabelle()
            print(f"acquired Isabelle{ISABELLE_VERSION}")
        else:
            print(json.dumps(run_isabelle_build(), ensure_ascii=False, sort_keys=True))
    except IsabelleToolError as exc:
        print(f"isabelle-tool: {exc}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
