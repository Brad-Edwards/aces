"""RUN-314: OCI driver security tests (subprocess mocked)."""

from __future__ import annotations

import subprocess

import pytest
from aces_backend_protocols.naming import provider_resource_name
from aces_reference_backend.driver import ContainerSpec, NetworkSpec, ServiceSpec
from aces_reference_backend.drivers.oci import ImageTrustPolicy, OciDeploymentDriver


class _Recorder:
    """Records subprocess.run invocations and returns a canned result."""

    def __init__(self, *, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.calls: list[dict[str, object]] = []
        self._stdout = stdout
        self._stderr = stderr
        self._returncode = returncode

    def __call__(self, argv, **kwargs):
        self.calls.append({"argv": argv, "kwargs": kwargs})
        return subprocess.CompletedProcess(
            args=argv,
            returncode=self._returncode,
            stdout=self._stdout,
            stderr=self._stderr,
        )


def _driver(recorder: _Recorder) -> OciDeploymentDriver:
    # Allowlist the images the run-path tests use so they exercise realization;
    # the image-trust policy is covered by its own dedicated tests below.
    return OciDeploymentDriver(
        runtime="docker",
        workspace="aces-ref-test",
        runner=recorder,
        image_policy=ImageTrustPolicy(allowed_images=("img", "aces-reference/linux", "pinned-img")),
    )


def test_container_spec_preserves_legacy_positional_labels_argument():
    labels = {"environment": "test"}

    spec = ContainerSpec("provision.node.web", "web", "img", (), labels)

    assert spec.labels is labels
    assert spec.services == ()


def test_oci_realize_uses_fixed_argv_list_never_shell():
    recorder = _Recorder(stdout="container-native-id-abc123\n")
    driver = _driver(recorder)

    driver.realize(
        networks=(NetworkSpec(address="provision.network.lan", name="lan"),),
        containers=(
            ContainerSpec(
                address="provision.node.web",
                name="web",
                image_ref="aces-reference/linux",
                networks=("provision.network.lan",),
            ),
        ),
    )

    assert recorder.calls
    for call in recorder.calls:
        assert isinstance(call["argv"], list)
        assert all(isinstance(token, str) for token in call["argv"])
        assert call["kwargs"].get("shell") is not True
        assert "shell" not in call["kwargs"] or call["kwargs"]["shell"] is False


def test_oci_realize_sets_bounded_timeout():
    recorder = _Recorder(stdout="id\n")
    driver = _driver(recorder)

    driver.realize(
        networks=(),
        containers=(ContainerSpec(address="provision.node.web", name="web", image_ref="img"),),
    )

    for call in recorder.calls:
        timeout = call["kwargs"].get("timeout")
        assert isinstance(timeout, (int, float))
        assert 0 < timeout <= 600


def test_oci_handles_never_carry_native_ids():
    recorder = _Recorder(stdout="DEADBEEF-native-container-id\n", stderr="secret-daemon-detail")
    driver = _driver(recorder)

    result = driver.realize(
        networks=(NetworkSpec(address="provision.network.lan", name="lan"),),
        containers=(ContainerSpec(address="provision.node.web", name="web", image_ref="img"),),
    )

    for handle in result.containers:
        assert handle.address == "provision.node.web"
        assert "DEADBEEF" not in repr(handle)
    for handle in result.networks:
        assert handle.address == "provision.network.lan"


def test_oci_failure_diagnostic_does_not_leak_native_output():
    sentinel = "TOKEN-LEAK-SENTINEL-XYZ"
    recorder = _Recorder(stdout="", stderr=sentinel, returncode=1)
    driver = _driver(recorder)

    result = driver.realize(
        networks=(),
        containers=(ContainerSpec(address="provision.node.web", name="web", image_ref="img"),),
    )

    assert result.diagnostics
    for diag in result.diagnostics:
        assert sentinel not in diag.message


def test_oci_no_tokens_in_argv():
    recorder = _Recorder(stdout="id\n")
    driver = OciDeploymentDriver(
        runtime="docker",
        workspace="aces-ref-test",
        runner=recorder,
        image_policy=ImageTrustPolicy(allowed_images=("img",)),
    )

    driver.realize(
        networks=(),
        containers=(ContainerSpec(address="provision.node.web", name="web", image_ref="img"),),
    )

    assert recorder.calls
    for call in recorder.calls:
        flat = " ".join(call["argv"])
        assert "token" not in flat.lower()
        assert "password" not in flat.lower()


def test_oci_timeout_becomes_diagnostic_not_raise():
    def _timeout_runner(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout", 1))

    driver = OciDeploymentDriver(
        runtime="docker",
        workspace="aces-ref-test",
        runner=_timeout_runner,
        image_policy=ImageTrustPolicy(allowed_images=("img",)),
    )

    result = driver.realize(
        networks=(),
        containers=(ContainerSpec(address="provision.node.web", name="web", image_ref="img"),),
    )

    assert result.diagnostics
    codes = {diag.code for diag in result.diagnostics}
    assert "reference-backend.driver.timeout" in codes


def test_oci_rejects_unknown_runtime():
    with pytest.raises(ValueError):
        OciDeploymentDriver(runtime="rm -rf /", workspace="ws")


def test_oci_destroy_removes_by_the_name_realize_used():
    """Destroy uses the canonical-address-derived name created by realize."""

    recorder = _Recorder(stdout="id\n")
    driver = _driver(recorder)

    driver.realize(
        networks=(),
        containers=(ContainerSpec(address="provision.node.web", name="pinned-web-name", image_ref="img"),),
    )
    recorder.calls.clear()
    driver.destroy(networks=(), containers=("provision.node.web",))

    rm_calls = [call["argv"] for call in recorder.calls]
    runtime_name = provider_resource_name("provision.node.web", prefix="aces")
    assert rm_calls == [["docker", "rm", "--force", runtime_name]]


def test_oci_attaches_container_to_requested_networks():
    """A planned container/network relationship must be honored: the run argv
    attaches the container to every requested network."""

    recorder = _Recorder(stdout="id\n")
    driver = _driver(recorder)

    driver.realize(
        networks=(NetworkSpec(address="provision.network.lan", name="lan"),),
        containers=(
            ContainerSpec(
                address="provision.node.web",
                name="web",
                image_ref="img",
                # The portable spec carries the network *address*; the driver
                # resolves it to the runtime name ("lan") it created.
                networks=("provision.network.lan",),
            ),
        ),
    )

    run_argv = next(call["argv"] for call in recorder.calls if "run" in call["argv"])
    assert "--network" in run_argv
    assert run_argv[run_argv.index("--network") + 1] == provider_resource_name("provision.network.lan", prefix="aces")


def test_oci_service_descriptors_do_not_publish_host_ports():
    recorder = _Recorder(stdout="id\n")
    driver = _driver(recorder)

    driver.realize(
        networks=(),
        containers=(
            ContainerSpec(
                address="provision.node.web",
                name="web",
                image_ref="img",
                services=(ServiceSpec(port=8443, protocol="tcp", name="https"),),
            ),
        ),
    )

    run_argv = next(call["argv"] for call in recorder.calls if "run" in call["argv"])
    assert "--publish" not in run_argv
    assert "-p" not in run_argv
    assert "8443" not in run_argv


def test_oci_rejects_plan_pinned_image_without_allowlist():
    """Image-trust boundary: a plan-pinned tag that is not allowlisted, not the
    operator default, and not digest-pinned must NOT be run."""

    recorder = _Recorder(stdout="id\n")
    driver = OciDeploymentDriver(runtime="docker", workspace="ws", runner=recorder)

    result = driver.realize(
        networks=(),
        containers=(ContainerSpec(address="provision.node.web", name="web", image_ref="evil.example/x:latest"),),
    )

    assert not any("run" in call["argv"] for call in recorder.calls)
    codes = {diag.code for diag in result.diagnostics}
    assert "reference-backend.driver.image-not-allowed" in codes
    for diag in result.diagnostics:
        assert "evil.example" not in diag.message


def test_oci_allows_digest_pinned_image():
    """A digest-pinned ref is a trust anchor and is realized by default."""

    recorder = _Recorder(stdout="id\n")
    driver = OciDeploymentDriver(runtime="docker", workspace="ws", runner=recorder)

    digest = "docker.io/library/alpine@sha256:" + "a" * 64
    result = driver.realize(
        networks=(),
        containers=(ContainerSpec(address="provision.node.web", name="web", image_ref=digest),),
    )

    assert not result.diagnostics
    run_argv = next(call["argv"] for call in recorder.calls if "run" in call["argv"])
    assert digest in run_argv


def test_oci_rolls_back_realized_resources_on_partial_failure():
    """Transactional boundary: when the container fails after the network was
    created, the successful network is destroyed so no orphan is left behind."""

    class _FailContainer:
        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def __call__(self, argv, **kwargs):
            self.calls.append(argv)
            # network create + network rm succeed; the container run fails.
            rc = 1 if "run" in argv else 0
            return subprocess.CompletedProcess(args=argv, returncode=rc, stdout="", stderr="")

    runner = _FailContainer()
    driver = OciDeploymentDriver(
        runtime="docker", workspace="ws", runner=runner, image_policy=ImageTrustPolicy(allowed_images=("img",))
    )

    result = driver.realize(
        networks=(NetworkSpec(address="provision.network.lan", name="lan"),),
        containers=(ContainerSpec(address="provision.node.web", name="web", image_ref="img"),),
    )

    assert result.diagnostics  # the failure is surfaced
    assert result.networks == ()  # no resource is reported as realized
    assert result.containers == ()
    # The successfully-created network was rolled back.
    assert [
        "docker",
        "network",
        "rm",
        provider_resource_name("provision.network.lan", prefix="aces"),
    ] in runner.calls
    assert driver.realized_addresses() == frozenset()
