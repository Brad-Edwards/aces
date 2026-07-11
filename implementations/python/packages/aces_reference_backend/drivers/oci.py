"""OCI deployment driver (docker/podman) for the reference backend.

Security boundary (binding guardrails, issue #197 preflight):

- Every host-process invocation uses a FIXED argv list -- never a shell
  string, never ``shell=True``. The container runtime name is validated
  against a closed allowlist so it can never carry an injected command.
- Every invocation has a bounded ``timeout``; a timeout becomes a portable
  diagnostic, not an escaped exception.
- No tokens, passwords, credentials, or host environment ever appear in
  argv.
- Backend-native output (container ids, daemon inspect payloads, raw
  stderr) is consumed privately and NEVER placed into the returned portable
  handles or diagnostics. Diagnostics carry the ACES address and a fixed
  message only.

The actual subprocess call is the only impure leaf; it is injected as
``runner`` so tests exercise the full argv/timeout/redaction logic without
a real daemon, and the real default runner line is marked ``# pragma: no
cover``.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass

from aces_backend_protocols.naming import provider_resource_name
from aces_contracts.diagnostics import Diagnostic, Severity

from aces_reference_backend.driver import (
    ContainerHandle,
    ContainerSpec,
    DriverResult,
    NetworkHandle,
    NetworkSpec,
)

_DOMAIN = "runtime"
_ALLOWED_RUNTIMES = frozenset({"docker", "podman"})
_DEFAULT_TIMEOUT_SECONDS = 120

_CODE_TIMEOUT = "reference-backend.driver.timeout"
_CODE_RUNTIME_UNAVAILABLE = "reference-backend.driver.runtime-unavailable"
_CODE_COMMAND_FAILED = "reference-backend.driver.command-failed"
_CODE_IMAGE_NOT_ALLOWED = "reference-backend.driver.image-not-allowed"

_KIND_TO_CODE = {
    "timeout": _CODE_TIMEOUT,
    "runtime-missing": _CODE_RUNTIME_UNAVAILABLE,
    "command-failed": _CODE_COMMAND_FAILED,
}

Runner = Callable[..., subprocess.CompletedProcess]


def _default_runner(argv: list[str], **kwargs) -> subprocess.CompletedProcess:
    # The real subprocess call is the impure IO leaf; tests inject a fake
    # runner, and coverage excludes this function (see pyproject exclude_also).
    return subprocess.run(argv, **kwargs)


@dataclass(frozen=True)
class ImageTrustPolicy:
    """Operator policy deciding which container images may be realized.

    A plan author controls ``spec.image_ref`` (via ``node.source``) and ``run``
    pulls+executes it; fixed argv stops shell injection but is not an image
    trust boundary. Only the operator ``default_image``, an explicit
    ``allowed_images`` entry, or a digest-pinned ref (``...@sha256:...``) is
    permitted, so plan submission cannot become arbitrary-image code execution.
    """

    default_image: str | None = None
    allowed_images: tuple[str, ...] = ()
    allow_digest_pinned: bool = True

    def image_for(self, image_ref: str) -> str:
        # A configured default overrides the synthesized ``aces-reference/*``
        # placeholder so an image-less plan can still realize against a registry.
        if self.default_image and image_ref.startswith("aces-reference/"):
            return self.default_image
        return image_ref

    def permits(self, image: str) -> bool:
        if self.default_image is not None and image == self.default_image:
            return True
        if image in self.allowed_images:
            return True
        return self.allow_digest_pinned and "@sha256:" in image


_DEFAULT_IMAGE_POLICY = ImageTrustPolicy()


class OciDeploymentDriver:
    """Realize portable specs against a real container runtime."""

    def __init__(
        self,
        *,
        runtime: str = "docker",
        workspace: str,
        runner: Runner | None = None,
        timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
        keep_alive: tuple[str, ...] = ("sleep", "3600"),
        image_policy: ImageTrustPolicy = _DEFAULT_IMAGE_POLICY,
    ) -> None:
        if runtime not in _ALLOWED_RUNTIMES:
            raise ValueError(f"Unsupported container runtime; allowed: {sorted(_ALLOWED_RUNTIMES)}.")
        if not workspace or not workspace.strip():
            raise ValueError("OciDeploymentDriver requires a non-empty workspace label.")
        if not 0 < timeout_seconds <= 600:
            raise ValueError("OciDeploymentDriver timeout_seconds must be in (0, 600].")
        self._runtime = runtime
        self._workspace = workspace
        self._runner = runner or _default_runner
        self._timeout = timeout_seconds
        self._keep_alive = tuple(keep_alive)
        self._image_policy = image_policy
        self._realized: set[str] = set()
        # ACES address -> the runtime object name realize() used, so destroy()
        # removes exactly what was created even when a payload pinned an
        # explicit name that differs from the address's last segment.
        self._names: dict[str, str] = {}

    def _label_args(self) -> list[str]:
        return ["--label", f"aces.workspace={self._workspace}"]

    def _run(self, argv: list[str]) -> tuple[bool, str | None]:
        """Run a fixed argv; return (success, failure_kind).

        Native stdout/stderr is consumed but never returned to the caller --
        only a coarse, fixed failure-kind string used to pick a diagnostic.
        """

        try:
            completed = self._runner(
                argv,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, "timeout"
        except FileNotFoundError:
            return False, "runtime-missing"
        kind = None if completed.returncode == 0 else "command-failed"
        return kind is None, kind

    def realize(
        self,
        *,
        networks: tuple[NetworkSpec, ...],
        containers: tuple[ContainerSpec, ...],
    ) -> DriverResult:
        diagnostics: list[Diagnostic] = []
        network_handles: list[NetworkHandle] = []
        for spec in networks:
            runtime_name = provider_resource_name(spec.address, prefix="aces")
            argv = [self._runtime, "network", "create", *self._label_args(), runtime_name]
            ok, kind = self._run(argv)
            if ok:
                self._realized.add(spec.address)
                self._names[spec.address] = runtime_name
                network_handles.append(NetworkHandle(address=spec.address, realized=True))
            else:
                diagnostics.append(self._failure(spec.address, kind))
        container_handles: list[ContainerHandle] = []
        for spec in containers:
            runtime_name = provider_resource_name(spec.address, prefix="aces")
            image = self._image_policy.image_for(spec.image_ref)
            if not self._image_policy.permits(image):
                diagnostics.append(self._image_rejected(spec.address))
                continue
            argv = [
                self._runtime,
                "run",
                "--detach",
                "--rm",
                *self._label_args(),
                "--name",
                runtime_name,
                # Attach the container to every requested network (created above
                # in this same realize() call) so planned topology is honored,
                # not silently left on the runtime default network. spec.networks
                # carries network resource addresses; resolve each to the runtime
                # name this driver actually created.
                *self._network_args(spec.networks),
                image,
                # Fixed keep-alive so generic images do not exit immediately.
                # Pure argv tokens -- never a shell string.
                *self._keep_alive,
            ]
            ok, kind = self._run(argv)
            if ok:
                self._realized.add(spec.address)
                self._names[spec.address] = runtime_name
                container_handles.append(ContainerHandle(address=spec.address, realized=True))
            else:
                diagnostics.append(self._failure(spec.address, kind))
        result = DriverResult(
            networks=tuple(network_handles),
            containers=tuple(container_handles),
            diagnostics=tuple(diagnostics),
        )
        # Transactional boundary: if any resource failed, roll back the ones
        # that succeeded so a partial realize never leaves an orphan runtime
        # resource behind a failed operation.
        if result.diagnostics:
            self._rollback(network_handles, container_handles)
            return DriverResult(diagnostics=result.diagnostics)
        return result

    def _network_args(self, network_addresses: tuple[str, ...]) -> list[str]:
        args: list[str] = []
        for address in network_addresses:
            args.extend(("--network", self._name_for(address)))
        return args

    def _rollback(
        self,
        networks: list[NetworkHandle],
        containers: list[ContainerHandle],
    ) -> None:
        realized_containers = tuple(handle.address for handle in containers if handle.realized)
        realized_networks = tuple(handle.address for handle in networks if handle.realized)
        if realized_containers or realized_networks:
            self.destroy(networks=realized_networks, containers=realized_containers)

    def _name_for(self, address: str) -> str:
        return self._names.get(address, provider_resource_name(address, prefix="aces"))

    def destroy(
        self,
        *,
        networks: tuple[str, ...],
        containers: tuple[str, ...],
    ) -> DriverResult:
        diagnostics: list[Diagnostic] = []
        container_handles: list[ContainerHandle] = []
        for address in containers:
            argv = [self._runtime, "rm", "--force", self._name_for(address)]
            ok, kind = self._run(argv)
            if ok:
                # Only forget the resource once it is actually gone; a failed
                # teardown stays tracked so a retry can reconcile it.
                self._realized.discard(address)
                self._names.pop(address, None)
            else:
                diagnostics.append(self._failure(address, kind))
            container_handles.append(ContainerHandle(address=address, realized=not ok))
        network_handles: list[NetworkHandle] = []
        for address in networks:
            argv = [self._runtime, "network", "rm", self._name_for(address)]
            ok, kind = self._run(argv)
            if ok:
                self._realized.discard(address)
                self._names.pop(address, None)
            else:
                diagnostics.append(self._failure(address, kind))
            network_handles.append(NetworkHandle(address=address, realized=not ok))
        return DriverResult(
            networks=tuple(network_handles),
            containers=tuple(container_handles),
            diagnostics=tuple(diagnostics),
        )

    def realized_addresses(self) -> frozenset[str]:
        return frozenset(self._realized)

    @staticmethod
    def _failure(address: str, kind: str | None) -> Diagnostic:
        code = _KIND_TO_CODE.get(kind or "command-failed", _CODE_COMMAND_FAILED)
        message = {
            _CODE_TIMEOUT: f"Container runtime operation for '{address}' exceeded the bounded timeout.",
            _CODE_RUNTIME_UNAVAILABLE: f"Container runtime is unavailable for '{address}'.",
            _CODE_COMMAND_FAILED: f"Container runtime operation for '{address}' did not succeed.",
        }[code]
        return Diagnostic(code=code, domain=_DOMAIN, address=address, message=message, severity=Severity.ERROR)

    @staticmethod
    def _image_rejected(address: str) -> Diagnostic:
        # The rejected image ref is plan-controlled; keep it out of the message
        # so the diagnostic never echoes attacker-chosen content.
        return Diagnostic(
            code=_CODE_IMAGE_NOT_ALLOWED,
            domain=_DOMAIN,
            address=address,
            message=(
                f"Container image for '{address}' is not permitted by the driver image-trust policy; "
                "configure default_image, allowed_images, or a digest-pinned ref."
            ),
            severity=Severity.ERROR,
        )
