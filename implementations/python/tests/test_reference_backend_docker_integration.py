"""RUN-314: opt-in real-container integration test.

Marked ``@pytest.mark.docker`` so it is excluded from the default hermetic
suite (``addopts = -m 'not fuzz and not integration and not docker'``).
Run it explicitly with ``pytest -m docker`` / ``nox -s integration_docker``.
It also self-skips cleanly when no container runtime is available, so an
accidental ``-m docker`` run on a runtime-less host does not fail.
"""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import pytest
from raes import parse_sdl
from raes_conformance.conformance import (
    BackendCapabilityProfile,
    run_target_conformance,
)
from raes_reference_backend import create_reference_backend_target
from raes_reference_backend.drivers.oci import ImageTrustPolicy, OciDeploymentDriver
from raes_runtime.control_plane import RuntimeControlPlane
from raes_runtime.manager import RuntimeManager

pytestmark = pytest.mark.docker

_IMAGE = "docker.io/library/alpine:3.20"
_SCENARIO = f"""
name: ref-docker
nodes:
  web:
    type: vm
    os: linux
    source: {_IMAGE}
    resources: {{ram: 1 gib, cpu: 1}}
"""


def _available_runtime() -> str | None:
    for runtime in ("docker", "podman"):
        if shutil.which(runtime) is None:
            continue
        try:
            completed = subprocess.run(
                [runtime, "info"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if completed.returncode == 0:
            return runtime
    return None


@pytest.fixture(scope="module")
def container_runtime() -> str:
    runtime = _available_runtime()
    if runtime is None:
        pytest.skip("no container runtime (docker/podman) available")
    # Pre-pull the integration image; skip (not fail) if the host is offline
    # or the registry is unreachable, so the test only runs when it can.
    try:
        completed = subprocess.run(
            [runtime, "pull", _IMAGE],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        pytest.skip("container runtime present but image pull failed")
    if completed.returncode != 0:
        pytest.skip("integration image is not available (offline registry?)")
    return runtime


def test_real_container_provision_inventory_and_teardown(container_runtime: str):
    workspace = "raes-ref-it"
    # The scenario pins an explicit image source, so the operator allowlists it
    # through the image-trust policy (plan-pinned tags are rejected by default).
    driver = OciDeploymentDriver(
        runtime=container_runtime,
        workspace=workspace,
        image_policy=ImageTrustPolicy(allowed_images=(_IMAGE,)),
    )
    target = create_reference_backend_target(driver=driver)

    manager = RuntimeManager(target)
    execution_plan = manager.plan(parse_sdl(textwrap.dedent(_SCENARIO)))

    control_plane = RuntimeControlPlane(target)
    try:
        receipt = control_plane.submit_provisioning(execution_plan.provisioning)
        status = control_plane.get_operation(receipt.operation_id)
        assert status is not None and status.state.value == "succeeded"
        # The driver records realization against the real runtime; the portable
        # snapshot shows the realized node.
        assert "provision.node.web" in control_plane.snapshot.entries
        assert "provision.node.web" in driver.realized_addresses()
    finally:
        driver.destroy(networks=(), containers=("provision.node.web",))


def test_real_driver_conformance_passes(container_runtime: str):
    driver = OciDeploymentDriver(
        runtime=container_runtime,
        workspace="raes-ref-it-conf",
        image_policy=ImageTrustPolicy(default_image=_IMAGE),
    )
    target = create_reference_backend_target(driver=driver)

    try:
        report = run_target_conformance(target)

        assert report.profile == BackendCapabilityProfile.FULL_REMOTE_CONTROL_PLANE
        assert report.passed is True, [
            diagnostic.message for case in report.cases if not case.passed for diagnostic in case.diagnostics
        ]
    finally:
        driver.destroy(networks=(), containers=("provision.node.vm",))
