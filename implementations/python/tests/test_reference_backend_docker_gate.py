"""Policy regressions for optional versus release-required Docker integration."""

from __future__ import annotations

import subprocess
from typing import NoReturn

import pytest
import test_reference_backend_docker_integration as docker_integration

_REVIEWED_ALPINE_DIGEST = "sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc"
_RUNTIME = "docker"


def test_docker_integration_uses_the_reviewed_multiarch_digest() -> None:
    expected_image = f"docker.io/library/alpine@{_REVIEWED_ALPINE_DIGEST}"

    assert expected_image == docker_integration._IMAGE


def test_optional_docker_integration_skips_without_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(docker_integration._REQUIRED_MODE_ENV, raising=False)
    monkeypatch.setattr(docker_integration, "_available_runtime", lambda: None)

    with pytest.raises(pytest.skip.Exception, match="no container runtime"):
        docker_integration._require_container_runtime()


def test_required_docker_integration_fails_without_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(docker_integration._REQUIRED_MODE_ENV, "1")
    monkeypatch.setattr(docker_integration, "_available_runtime", lambda: None)

    with pytest.raises(pytest.fail.Exception, match="required real-container release gate unavailable"):
        docker_integration._require_container_runtime()


@pytest.mark.parametrize("required", [False, True])
def test_image_pull_failure_skips_only_when_optional(
    monkeypatch: pytest.MonkeyPatch,
    required: bool,
) -> None:
    monkeypatch.setenv(docker_integration._REQUIRED_MODE_ENV, "1" if required else "0")
    monkeypatch.setattr(docker_integration, "_available_runtime", lambda: _RUNTIME)
    monkeypatch.setattr(
        docker_integration.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1),
    )
    expected = pytest.fail.Exception if required else pytest.skip.Exception

    with pytest.raises(expected, match="integration image is not available"):
        docker_integration._require_container_runtime()


@pytest.mark.parametrize("required", [False, True])
def test_image_pull_exception_skips_only_when_optional(
    monkeypatch: pytest.MonkeyPatch,
    required: bool,
) -> None:
    monkeypatch.setenv(docker_integration._REQUIRED_MODE_ENV, "1" if required else "0")
    monkeypatch.setattr(docker_integration, "_available_runtime", lambda: _RUNTIME)

    def fail_pull(*_args, **_kwargs) -> NoReturn:
        raise OSError("runtime invocation failed")

    monkeypatch.setattr(docker_integration.subprocess, "run", fail_pull)
    expected = pytest.fail.Exception if required else pytest.skip.Exception

    with pytest.raises(expected, match="image pull failed"):
        docker_integration._require_container_runtime()


def test_required_docker_integration_accepts_successful_pull(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(docker_integration._REQUIRED_MODE_ENV, "1")
    monkeypatch.setattr(docker_integration, "_available_runtime", lambda: _RUNTIME)
    monkeypatch.setattr(
        docker_integration.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0),
    )

    expected_runtime = _RUNTIME
    actual_runtime = docker_integration._require_container_runtime()

    assert expected_runtime == actual_runtime


def test_invalid_required_mode_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(docker_integration._REQUIRED_MODE_ENV, "yes")
    monkeypatch.setattr(docker_integration, "_available_runtime", lambda: _RUNTIME)

    with pytest.raises(pytest.fail.Exception, match="must be exactly 0 or 1"):
        docker_integration._require_container_runtime()
