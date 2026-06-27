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
from collections.abc import Callable
from pathlib import Path
from typing import Any


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
    payload: dict[str, Any] | None = None
    if args.clean_volumes:
        stop_result = stop_lab(remove_volumes=True, project_dir=project_dir)
        if not stop_result.success:
            payload = _failure(f"clean-state cleanup failed: {stop_result.error}")

    if payload is None:
        scenario_path = Path(args.scenario_path) if args.scenario_path else None
        ctx = _LabStartContext(project_dir=project_dir, skip_seed=False, scenario_path=scenario_path)
        setup_steps: tuple[Callable[[Any], Any], ...] = (
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
        setup_failure = _run_steps(ctx, setup_steps)
        if setup_failure is not None:
            payload = setup_failure

    if payload is None:
        assert ctx.backend is not None
        result = ctx.backend.start(profiles)
        if not result.success and "soc" in profiles:
            time.sleep(60)
            result = ctx.backend.start(profiles)
        if not result.success:
            payload = _failure(f"compose start failed: {result.error}")

    if payload is None:
        ctx.selected_profiles = set(profiles)
        readiness_failure = _run_steps(ctx, (_step_wait_for_services, _step_test_ssh, _step_capture_snapshot))
        if readiness_failure is not None:
            payload = readiness_failure

    if payload is None:
        snapshot = ctx.snapshot.to_dict() if ctx.snapshot is not None else {}
        payload = {
            "success": True,
            "profiles": profiles,
            "snapshot": snapshot,
            "diagnostics": [_diagnostic_payload(diag) for diag in ctx.diagnostics],
        }
    return payload


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


def _run_steps(ctx: object, steps: tuple[Callable[[Any], Any], ...]) -> dict[str, Any] | None:
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
