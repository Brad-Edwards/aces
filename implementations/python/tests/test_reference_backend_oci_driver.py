"""RUN-314: OCI driver security tests (subprocess mocked)."""

from __future__ import annotations

import subprocess

import pytest
from raes_backend_protocols.naming import provider_resource_name
from raes_contracts.realization_envelope import ObservationStrength, RealizationConcern
from raes_reference_backend.driver import ContainerSpec, NetworkSpec, ServiceSpec
from raes_reference_backend.drivers.inprocess import InProcessDriver
from raes_reference_backend.drivers.oci import ImageTrustPolicy, OciDeploymentDriver
from raes_reference_backend.envelopes import load_reference_realization_envelope


class _Recorder:
    """Records subprocess.run invocations and returns a canned result."""

    def __init__(self, *, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.calls: list[dict[str, object]] = []
        self._stdout = stdout
        self._stderr = stderr
        self._returncode = returncode

    def __call__(self, argv, **kwargs):
        self.calls.append({"argv": argv, "kwargs": kwargs})
        stdout = self._stdout
        if self._returncode == 0 and "inspect" in argv:
            name = argv[-1]
            run_call = next(
                (
                    call["argv"]
                    for call in reversed(self.calls[:-1])
                    if "run" in call["argv"]
                    and "--name" in call["argv"]
                    and call["argv"][call["argv"].index("--name") + 1] == name
                ),
                None,
            )
            if run_call is not None:
                labels = [run_call[index + 1] for index, token in enumerate(run_call[:-1]) if token == "--label"]
                workspace = next(label.split("=", 1)[1] for label in labels if label.startswith("raes.workspace="))
                address = next(label.split("=", 1)[1] for label in labels if label.startswith("raes.address="))
                native_id = self._stdout.strip().splitlines()[0]
                stdout = f"{native_id}\n{workspace}\n{address}\n/{name}\n"
        return subprocess.CompletedProcess(
            args=argv,
            returncode=self._returncode,
            stdout=stdout,
            stderr=self._stderr,
        )


def _driver(recorder: _Recorder) -> OciDeploymentDriver:
    # Allowlist the images the run-path tests use so they exercise realization;
    # the image-trust policy is covered by its own dedicated tests below.
    return OciDeploymentDriver(
        runtime="docker",
        workspace="raes-ref-test",
        runner=recorder,
        image_policy=ImageTrustPolicy(allowed_images=("img", "raes-reference/linux", "pinned-img")),
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
                image_ref="raes-reference/linux",
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


def test_oci_observe_rehydrates_owned_container_without_running_it_again() -> None:
    recorder = _Recorder(stdout="container-native-id-abc123\n")
    spec = ContainerSpec(address="provision.node.web", name="web", image_ref="img")
    first = _driver(recorder)
    assert not first.realize(networks=(), containers=(spec,)).diagnostics
    run_calls = tuple(call for call in recorder.calls if "run" in call["argv"])

    restarted = _driver(recorder)
    result = restarted.observe(containers=(spec,))

    assert not result.diagnostics
    [observation] = result.observations
    envelope = load_reference_realization_envelope("oci-container")
    assert observation.address == spec.address
    assert observation.value == "operating-system-container"
    assert observation.concern is RealizationConcern.COMPUTE_SUBSTRATE
    assert observation.source is ObservationStrength.DAEMON_OBSERVED
    assert observation.envelope_digest == envelope.digest
    assert observation.configuration_digest == envelope.configuration.configuration_digest
    assert observation.binding_verified
    assert tuple(call for call in recorder.calls if "run" in call["argv"]) == run_calls
    assert any("inspect" in call["argv"] for call in recorder.calls)


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
        workspace="raes-ref-test",
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
        workspace="raes-ref-test",
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
    runtime_name = provider_resource_name("provision.node.web", prefix="raes")
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
    assert run_argv[run_argv.index("--network") + 1] == provider_resource_name("provision.network.lan", prefix="raes")


def test_oci_joins_only_a_run_owned_target_network_namespace():
    owner_address = "provision.node.zzz-owner"
    capture_address = "provision.node.aaa-capture"
    owner_name = provider_resource_name(owner_address, prefix="raes")

    class _OwnedTargetRecorder:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def __call__(self, argv, **kwargs):
            self.calls.append({"argv": argv, "kwargs": kwargs})
            if "inspect" in argv:
                name = argv[-1]
                if name == owner_name:
                    native_id = "owner-native-id"
                    address = owner_address
                else:
                    native_id = "capture-native-id"
                    address = capture_address
                stdout = f"{native_id}\nraes-ref-test\n{address}\n/{name}\n"
            elif "run" in argv and owner_name in argv:
                stdout = "owner-native-id\n"
            else:
                stdout = "capture-native-id\n"
            return subprocess.CompletedProcess(args=argv, returncode=0, stdout=stdout, stderr="")

    recorder = _OwnedTargetRecorder()
    driver = _driver(recorder)

    result = driver.realize(
        networks=(),
        containers=(
            ContainerSpec(
                address=capture_address,
                name="capture",
                image_ref="img",
                network_namespace_target=owner_address,
            ),
            ContainerSpec(address=owner_address, name="owner", image_ref="img"),
        ),
    )

    assert not result.diagnostics
    run_calls = [call["argv"] for call in recorder.calls if "run" in call["argv"]]
    assert [argv[argv.index("--name") + 1] for argv in run_calls] == [
        owner_name,
        provider_resource_name(capture_address, prefix="raes"),
    ]
    inspect_argv = next(call["argv"] for call in recorder.calls if "inspect" in call["argv"])
    assert inspect_argv[-1] == owner_name
    capture_argv = run_calls[1]
    assert capture_argv[capture_argv.index("--network") + 1] == ("container:" + owner_name)


def test_oci_rejects_stale_realized_namespace_target_before_side_effects():
    recorder = _Recorder(stdout="owner-native-id\n")
    driver = _driver(recorder)
    owner_address = "provision.node.owner"

    owner_result = driver.realize(
        networks=(),
        containers=(ContainerSpec(address=owner_address, name="owner", image_ref="img"),),
    )
    assert not owner_result.diagnostics
    recorder.calls.clear()

    result = driver.realize(
        networks=(),
        containers=(
            ContainerSpec(
                address="provision.node.capture",
                name="capture",
                image_ref="img",
                network_namespace_target=owner_address,
            ),
        ),
    )

    assert not recorder.calls
    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "reference-backend.driver.network-namespace-target-unavailable"
    }


def test_oci_rejects_namespace_target_when_native_id_alone_mismatches():
    owner_address = "provision.node.owner"
    owner_name = provider_resource_name(owner_address, prefix="raes")

    class _MismatchedOwnershipRecorder:
        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def __call__(self, argv, **kwargs):
            self.calls.append(argv)
            if "inspect" in argv:
                stdout = f"replacement-native-id\nraes-ref-test\n{owner_address}\n/{owner_name}\n"
            else:
                stdout = "owner-native-id\n"
            return subprocess.CompletedProcess(args=argv, returncode=0, stdout=stdout, stderr="")

    recorder = _MismatchedOwnershipRecorder()
    driver = _driver(recorder)
    result = driver.realize(
        networks=(),
        containers=(
            ContainerSpec(address=owner_address, name="owner", image_ref="img"),
            ContainerSpec(
                address="provision.node.capture",
                name="capture",
                image_ref="img",
                network_namespace_target=owner_address,
            ),
        ),
    )

    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "reference-backend.driver.network-namespace-target-unavailable"
    }
    assert sum("run" in argv for argv in recorder.calls) == 1
    assert ["docker", "rm", "--force", owner_name] in recorder.calls


def test_oci_rejects_unknown_network_namespace_target_before_side_effects():
    recorder = _Recorder(stdout="id\n")
    driver = _driver(recorder)

    result = driver.realize(
        networks=(NetworkSpec(address="provision.network.lan", name="lan"),),
        containers=(
            ContainerSpec(
                address="provision.node.capture",
                name="capture",
                image_ref="img",
                network_namespace_target="provision.node.not-owned",
            ),
        ),
    )

    assert not recorder.calls
    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "reference-backend.driver.network-namespace-target-unavailable"
    }


def test_oci_rejects_network_namespace_target_with_independent_networks():
    recorder = _Recorder(stdout="id\n")
    driver = _driver(recorder)

    result = driver.realize(
        networks=(NetworkSpec(address="provision.network.lan", name="lan"),),
        containers=(
            ContainerSpec(address="provision.node.owner", name="owner", image_ref="img"),
            ContainerSpec(
                address="provision.node.capture",
                name="capture",
                image_ref="img",
                networks=("provision.network.lan",),
                network_namespace_target="provision.node.owner",
            ),
        ),
    )

    assert not recorder.calls
    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "reference-backend.driver.network-namespace-conflict"
    }


def test_oci_rejects_self_referential_network_namespace_target():
    recorder = _Recorder(stdout="id\n")
    driver = _driver(recorder)
    address = "provision.node.capture"

    result = driver.realize(
        networks=(),
        containers=(
            ContainerSpec(
                address=address,
                name="capture",
                image_ref="img",
                network_namespace_target=address,
            ),
        ),
    )

    assert not recorder.calls
    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "reference-backend.driver.network-namespace-target-unavailable"
    }


def test_inprocess_driver_rejects_network_namespace_sharing_without_recording_ops():
    driver = InProcessDriver()

    result = driver.realize(
        networks=(),
        containers=(
            ContainerSpec(address="provision.node.owner", name="owner", image_ref="img"),
            ContainerSpec(
                address="provision.node.capture",
                name="capture",
                image_ref="img",
                network_namespace_target="provision.node.owner",
            ),
        ),
    )

    assert not driver.recorded_ops
    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "reference-backend.driver.network-namespace-unsupported"
    }


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
        provider_resource_name("provision.network.lan", prefix="raes"),
    ] in runner.calls
    assert driver.realized_addresses() == frozenset()
