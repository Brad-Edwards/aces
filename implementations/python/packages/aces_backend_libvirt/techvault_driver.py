"""Operational TechVault driver for the libvirt backend."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aces_contracts.diagnostics import Diagnostic, Severity

from .driver import DomainHandle, DomainSpec, DriverResult, NetworkHandle, NetworkSpec
from .techvault_profiles import ProfileSelection, select_profiles_for_nodes

_DOMAIN = "runtime"
_CODE_START_FAILED = "libvirt-backend.techvault.start-failed"
_CODE_STOP_FAILED = "libvirt-backend.techvault.stop-failed"
_CODE_PROFILE_UNRESOLVED = "libvirt-backend.techvault.profile-unresolved"
_CODE_HELPER_FAILED = "libvirt-backend.techvault.helper-failed"


@dataclass(frozen=True)
class TechVaultLifecycleResult:
    """Result returned by the TechVault lifecycle helper."""

    success: bool
    profiles: tuple[str, ...] = ()
    snapshot: dict[str, Any] = field(default_factory=dict)
    diagnostics: tuple[dict[str, str], ...] = ()
    error: str = ""


class AptlHelperRunner:
    """Run the APTL lifecycle helper in an APTL-capable environment."""

    def __init__(
        self,
        *,
        uv_executable: str = "uv",
        timeout_seconds: int = 1800,
        extra_pythonpath: tuple[Path, ...] = (),
    ) -> None:
        self._uv_executable = uv_executable
        self._timeout_seconds = timeout_seconds
        self._extra_pythonpath = extra_pythonpath

    def start(
        self,
        *,
        project_dir: Path,
        profiles: tuple[str, ...],
        clean_volumes: bool,
        scenario_path: Path | None,
    ) -> TechVaultLifecycleResult:
        args = [
            "start",
            "--project-dir",
            str(project_dir),
            "--profiles-json",
            json.dumps(list(profiles)),
        ]
        if clean_volumes:
            args.append("--clean-volumes")
        if scenario_path is not None:
            args.extend(["--scenario-path", str(scenario_path)])
        return self._run(project_dir, args)

    def stop(
        self,
        *,
        project_dir: Path,
        profiles: tuple[str, ...],
        remove_volumes: bool,
    ) -> TechVaultLifecycleResult:
        args = [
            "stop",
            "--project-dir",
            str(project_dir),
            "--profiles-json",
            json.dumps(list(profiles)),
        ]
        if remove_volumes:
            args.append("--remove-volumes")
        return self._run(project_dir, args)

    def _run(self, project_dir: Path, args: list[str]) -> TechVaultLifecycleResult:
        command = [
            self._uv_executable,
            "run",
            "--project",
            str(project_dir),
            "python",
            "-m",
            "aces_backend_libvirt._techvault_aptl_entry",
            *args,
        ]
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(str(path) for path in self._pythonpath(project_dir))
        try:
            proc = subprocess.run(
                command,
                cwd=project_dir,
                env=env,
                text=True,
                capture_output=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return TechVaultLifecycleResult(success=False, error=f"APTL helper failed: {exc}")
        if proc.returncode != 0:
            return TechVaultLifecycleResult(success=False, error=_short_error(proc.stderr or proc.stdout))
        return _decode_helper_payload(proc.stdout)

    def _pythonpath(self, project_dir: Path) -> tuple[Path, ...]:
        package_root = Path(__file__).resolve().parents[1]
        aces_source = package_root.parent / "src"
        aptl_source = project_dir / "src"
        paths = [package_root, aces_source, aptl_source, *self._extra_pythonpath]
        existing = [Path(item) for item in os.environ.get("PYTHONPATH", "").split(os.pathsep) if item]
        return tuple(path for path in [*paths, *existing] if path)


class TechVaultComposeDriver:
    """Realize TechVault's ACES provisioning surface through APTL Compose."""

    def __init__(
        self,
        *,
        project_dir: Path,
        scenario_path: Path | None = None,
        clean_boot: bool = True,
        runner: AptlHelperRunner | None = None,
    ) -> None:
        self.project_dir = project_dir
        self.scenario_path = scenario_path
        self.clean_boot = clean_boot
        self.runner = runner or AptlHelperRunner()
        self.last_selection: ProfileSelection | None = None
        self.last_snapshot: dict[str, Any] = {}
        self.last_diagnostics: tuple[dict[str, str], ...] = ()
        self._realized: set[str] = set()

    def realize(
        self,
        *,
        networks: tuple[NetworkSpec, ...],
        domains: tuple[DomainSpec, ...],
    ) -> DriverResult:
        selection = select_profiles_for_nodes(self.project_dir, (domain.name for domain in domains))
        self.last_selection = selection
        if selection.unmapped_nodes:
            return DriverResult(diagnostics=tuple(_unmapped_diagnostics(selection.unmapped_nodes)))
        result = self.runner.start(
            project_dir=self.project_dir,
            profiles=selection.profiles,
            clean_volumes=self.clean_boot,
            scenario_path=self.scenario_path,
        )
        self.last_snapshot = result.snapshot
        self.last_diagnostics = result.diagnostics
        if not result.success:
            return DriverResult(diagnostics=(_diagnostic(_CODE_START_FAILED, "runtime.techvault.start", result.error),))
        self._realized.update(spec.address for spec in networks)
        self._realized.update(spec.address for spec in domains)
        return DriverResult(
            networks=tuple(NetworkHandle(address=spec.address, realized=True) for spec in networks),
            domains=tuple(DomainHandle(address=spec.address, realized=True) for spec in domains),
        )

    def destroy(
        self,
        *,
        networks: tuple[str, ...],
        domains: tuple[str, ...],
    ) -> DriverResult:
        profiles = self.last_selection.profiles if self.last_selection is not None else ()
        result = self.runner.stop(project_dir=self.project_dir, profiles=profiles, remove_volumes=False)
        if not result.success:
            return DriverResult(diagnostics=(_diagnostic(_CODE_STOP_FAILED, "runtime.techvault.stop", result.error),))
        self._realized.difference_update(networks)
        self._realized.difference_update(domains)
        return DriverResult(
            networks=tuple(NetworkHandle(address=address, realized=False) for address in networks),
            domains=tuple(DomainHandle(address=address, realized=False) for address in domains),
        )

    def realized_addresses(self) -> frozenset[str]:
        return frozenset(self._realized)


def _decode_helper_payload(stdout: str) -> TechVaultLifecycleResult:
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        return TechVaultLifecycleResult(success=False, error="APTL helper produced no JSON result.")
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError:
        return TechVaultLifecycleResult(success=False, error="APTL helper produced invalid JSON.")
    if not isinstance(payload, dict):
        return TechVaultLifecycleResult(success=False, error="APTL helper JSON result was not an object.")
    profiles = payload.get("profiles", ())
    diagnostics = payload.get("diagnostics", ())
    return TechVaultLifecycleResult(
        success=payload.get("success") is True,
        profiles=tuple(str(item) for item in profiles) if isinstance(profiles, list) else (),
        snapshot=payload.get("snapshot") if isinstance(payload.get("snapshot"), dict) else {},
        diagnostics=tuple(item for item in diagnostics if isinstance(item, dict)) if isinstance(diagnostics, list) else (),
        error=str(payload.get("error", "")),
    )


def _unmapped_diagnostics(nodes: tuple[str, ...]) -> list[Diagnostic]:
    return [
        _diagnostic(
            _CODE_PROFILE_UNRESOLVED,
            f"runtime.techvault.node.{node}",
            f"TechVault node '{node}' does not map to an APTL Compose profile.",
        )
        for node in nodes
    ]


def _diagnostic(code: str, address: str, message: str) -> Diagnostic:
    return Diagnostic(code=code, domain=_DOMAIN, address=address, message=message, severity=Severity.ERROR)


def _short_error(raw: str) -> str:
    stripped = " ".join(raw.split())
    return stripped[:1000] if stripped else _CODE_HELPER_FAILED
