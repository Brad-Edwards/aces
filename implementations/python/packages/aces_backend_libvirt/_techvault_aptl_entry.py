"""Subprocess entry point for TechVault's APTL lifecycle setup.

This module is intentionally invoked in an APTL-capable Python environment by
``TechVaultComposeDriver``. It runs APTL's setup lifecycle without calling
APTL's own ACES handoff, so the parent ACES/libvirt provisioning path remains
the scenario driver.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class _LifecycleResult(Protocol):
    success: bool
    error: str


class _Backend(Protocol):
    def start(self, profiles: list[str]) -> _LifecycleResult: ...


class _Snapshot(Protocol):
    def to_dict(self) -> dict[str, object]: ...


class _StartContext(Protocol):
    backend: _Backend | None
    selected_profiles: set[str]
    snapshot: _Snapshot | None
    diagnostics: list[object]


class _ContextFactory(Protocol):
    def __call__(self, *, project_dir: Path, skip_seed: bool, scenario_path: Path | None) -> _StartContext: ...


class _StopLab(Protocol):
    def __call__(self, *, remove_volumes: bool, project_dir: Path) -> _LifecycleResult: ...


class _LifecycleStep(Protocol):
    __name__: str

    def __call__(self, ctx: _StartContext) -> _LifecycleResult | None: ...


@dataclass(frozen=True)
class _LifecycleConfig:
    context_factory: _ContextFactory
    stop_lab: _StopLab
    project_dir: Path
    profiles: list[str]
    scenario_path_raw: str
    clean_volumes: bool
    setup_steps: tuple[_LifecycleStep, ...]
    readiness_steps: tuple[_LifecycleStep, ...]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TechVault APTL lifecycle actions for ACES/libvirt.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start")
    start.add_argument("--project-dir", required=True)
    start.add_argument("--profiles-json", required=True)
    start.add_argument("--scenario-path", default="")
    start.add_argument("--clean-volumes", action="store_true")
    stop = subparsers.add_parser("stop")
    stop.add_argument("--project-dir", required=True)
    stop.add_argument("--profiles-json", required=True)
    stop.add_argument("--remove-volumes", action="store_true")
    args = parser.parse_args()

    if args.command == "start":
        _print(_start(args))
    elif args.command == "stop":
        _print(_stop(args))


def _start(args: argparse.Namespace) -> dict[str, Any]:
    from aptl.core.lab import (
        _LabStartContext,
        _step_capture_snapshot,
        _step_check_bind_mounts,
        _step_check_sysreqs,
        _step_ensure_ssh_keys,
        _step_generate_certs,
        _step_generate_soc_certs,
        _step_load_config,
        _step_load_env,
        _step_pull_images,
        _step_seed_suricata_volumes,
        _step_sync_credentials,
        _step_test_ssh,
        _step_wait_for_services,
        stop_lab,
    )

    project_dir = Path(args.project_dir)
    profiles = _profiles(args.profiles_json)
    setup_steps: tuple[_LifecycleStep, ...] = (
        _step_load_env,
        _step_load_config,
        _step_ensure_ssh_keys,
        _step_check_sysreqs,
        _step_sync_credentials,
        _step_seed_suricata_volumes,
        _step_generate_certs,
        _step_generate_soc_certs,
        _step_check_bind_mounts,
        _step_pull_images,
    )
    readiness_steps = (_step_wait_for_services, _step_test_ssh, _step_capture_snapshot)
    ctx, payload = _start_lifecycle(
        _LifecycleConfig(
            context_factory=_LabStartContext,
            stop_lab=stop_lab,
            project_dir=project_dir,
            profiles=profiles,
            scenario_path_raw=args.scenario_path,
            clean_volumes=args.clean_volumes,
            setup_steps=setup_steps,
            readiness_steps=readiness_steps,
        )
    )
    if payload is None:
        assert ctx is not None
        payload = _success_payload(ctx, profiles)
    return payload


def _start_lifecycle(config: _LifecycleConfig) -> tuple[_StartContext | None, dict[str, Any] | None]:
    ctx: _StartContext | None = None
    payload = _clean_start_state(
        clean_volumes=config.clean_volumes, stop_lab=config.stop_lab, project_dir=config.project_dir
    )
    if payload is None:
        scenario_path = Path(config.scenario_path_raw) if config.scenario_path_raw else None
        ctx = config.context_factory(project_dir=config.project_dir, skip_seed=False, scenario_path=scenario_path)
        payload = _run_steps(ctx, config.setup_steps)
    if payload is None:
        assert ctx is not None
        payload = _start_compose(ctx, config.profiles)
    if payload is None:
        assert ctx is not None
        payload = _run_readiness(ctx, config.profiles, config.readiness_steps)
    return ctx, payload


def _clean_start_state(*, clean_volumes: bool, stop_lab: _StopLab, project_dir: Path) -> dict[str, Any] | None:
    payload: dict[str, Any] | None = None
    if clean_volumes:
        stop_result = stop_lab(remove_volumes=True, project_dir=project_dir)
        if not stop_result.success:
            payload = _failure(f"clean-state cleanup failed: {stop_result.error}")
    return payload


def _start_compose(ctx: _StartContext, profiles: list[str]) -> dict[str, Any] | None:
    assert ctx.backend is not None
    result = ctx.backend.start(profiles)
    if not result.success and "soc" in profiles:
        time.sleep(60)
        result = ctx.backend.start(profiles)
    payload = None if result.success else _failure(f"compose start failed: {result.error}")
    return payload


def _run_readiness(
    ctx: _StartContext,
    profiles: list[str],
    readiness_steps: tuple[_LifecycleStep, ...],
) -> dict[str, Any] | None:
    ctx.selected_profiles = set(profiles)
    return _run_steps(ctx, readiness_steps)


def _success_payload(ctx: _StartContext, profiles: list[str]) -> dict[str, Any]:
    snapshot = ctx.snapshot.to_dict() if ctx.snapshot is not None else {}
    return {
        "success": True,
        "profiles": profiles,
        "snapshot": snapshot,
        "diagnostics": [_diagnostic_payload(diag) for diag in ctx.diagnostics],
    }


def _stop(args: argparse.Namespace) -> dict[str, Any]:
    from aptl.core.lab import _get_backend, find_config, load_config

    project_dir = Path(args.project_dir)
    profiles = _profiles(args.profiles_json)
    config_path = find_config(project_dir)
    config = load_config(config_path) if config_path is not None else None
    backend = _get_backend(project_dir, config)
    result = backend.stop(profiles, remove_volumes=args.remove_volumes)
    if not result.success:
        return _failure(result.error or "compose stop failed")
    return {"success": True, "profiles": profiles, "snapshot": {}, "diagnostics": []}


def _run_steps(ctx: _StartContext, steps: tuple[_LifecycleStep, ...]) -> dict[str, Any] | None:
    for step in steps:
        result = step(ctx)
        if result is not None and not result.success:
            return _failure(result.error or f"{step.__name__} failed")
    return None


def _profiles(raw: str) -> list[str]:
    value = json.loads(raw)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError("--profiles-json must be a JSON list of non-empty strings")
    return value


def _failure(error: str) -> dict[str, Any]:
    return {"success": False, "error": error, "profiles": [], "snapshot": {}, "diagnostics": []}


def _diagnostic_payload(diag: object) -> dict[str, str]:
    return {
        "step": str(getattr(diag, "step", "")),
        "impact": str(getattr(getattr(diag, "impact", ""), "value", "")),
        "severity": str(getattr(getattr(diag, "severity", ""), "value", "")),
        "message": str(getattr(diag, "message", "")),
        "component": str(getattr(diag, "component", "")),
    }


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
