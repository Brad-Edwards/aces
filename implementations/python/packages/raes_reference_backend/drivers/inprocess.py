"""Hermetic in-process driver (default) for the reference backend.

Records the realize/destroy operations it is asked to perform and
synthesizes portable handles. No subprocess, no container runtime, no IO --
so it is safe in CI and in the default conformance/apply path. It keeps a
private ledger of recorded ops (for test assertions) and a private set of
realized RAES addresses; neither leaks into any portable artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.realization_envelope import ObservationStrength, RealizationConcern
from raes_contracts.realization_observation import RealizationObservation

from raes_reference_backend.driver import (
    ContainerHandle,
    ContainerSpec,
    DriverResult,
    NetworkHandle,
    NetworkSpec,
)
from raes_reference_backend.envelopes import load_reference_realization_envelope


@dataclass(frozen=True)
class RecordedOp:
    """A recorded driver operation (test/inspection only, not portable)."""

    verb: str
    kind: str
    address: str


@dataclass
class InProcessDriver:
    """Hermetic driver that records ops and synthesizes portable handles."""

    driver_mode = "in-process-emulation"

    recorded_ops: list[RecordedOp] = field(default_factory=list)
    _realized: set[str] = field(default_factory=set)

    def realize(
        self,
        *,
        networks: tuple[NetworkSpec, ...],
        containers: tuple[ContainerSpec, ...],
    ) -> DriverResult:
        unsupported = tuple(spec for spec in containers if spec.network_namespace_target)
        if unsupported:
            return DriverResult(
                diagnostics=tuple(
                    Diagnostic(
                        code="reference-backend.driver.network-namespace-unsupported",
                        domain="runtime",
                        address=spec.address,
                        message=(
                            f"The in-process driver cannot realize the network namespace requirement "
                            f"for '{spec.address}'."
                        ),
                        severity=Severity.ERROR,
                    )
                    for spec in unsupported
                )
            )
        network_handles: list[NetworkHandle] = []
        for spec in networks:
            self.recorded_ops.append(RecordedOp(verb="realize", kind="network", address=spec.address))
            self._realized.add(spec.address)
            network_handles.append(NetworkHandle(address=spec.address, realized=True))
        container_handles: list[ContainerHandle] = []
        for spec in containers:
            self.recorded_ops.append(RecordedOp(verb="realize", kind="container", address=spec.address))
            self._realized.add(spec.address)
            container_handles.append(ContainerHandle(address=spec.address, realized=True))
        return DriverResult(
            networks=tuple(network_handles),
            containers=tuple(container_handles),
            observations=tuple(
                _substrate_observation(spec.address, sequence=index) for index, spec in enumerate(containers)
            ),
        )

    def destroy(
        self,
        *,
        networks: tuple[str, ...],
        containers: tuple[str, ...],
    ) -> DriverResult:
        container_handles: list[ContainerHandle] = []
        for address in containers:
            self.recorded_ops.append(RecordedOp(verb="destroy", kind="container", address=address))
            self._realized.discard(address)
            container_handles.append(ContainerHandle(address=address, realized=False))
        network_handles: list[NetworkHandle] = []
        for address in networks:
            self.recorded_ops.append(RecordedOp(verb="destroy", kind="network", address=address))
            self._realized.discard(address)
            network_handles.append(NetworkHandle(address=address, realized=False))
        return DriverResult(
            networks=tuple(network_handles),
            containers=tuple(container_handles),
        )

    def observe(self, *, containers: tuple[ContainerSpec, ...]) -> DriverResult:
        """Read the current in-process ledger without recording a mutation."""

        missing = tuple(spec.address for spec in containers if spec.address not in self._realized)
        if missing:
            return DriverResult(
                diagnostics=tuple(
                    Diagnostic(
                        code="reference-backend.driver.compute-substrate-unobserved",
                        domain="runtime",
                        address=address,
                        message=f"In-process runtime did not observe an existing resource for '{address}'.",
                        severity=Severity.ERROR,
                    )
                    for address in missing
                )
            )
        return DriverResult(
            observations=tuple(
                _substrate_observation(spec.address, sequence=index) for index, spec in enumerate(containers)
            )
        )

    def realized_addresses(self) -> frozenset[str]:
        return frozenset(self._realized)


def _substrate_observation(address: str, *, sequence: int) -> RealizationObservation:
    envelope = load_reference_realization_envelope(InProcessDriver.driver_mode)
    return RealizationObservation(
        address=address,
        field_path="compute-substrate",
        concern=RealizationConcern.COMPUTE_SUBSTRATE,
        source=ObservationStrength.DRIVER_REPORTED,
        value="x-openrae:in-process-emulation",
        envelope_digest=envelope.digest,
        configuration_digest=envelope.configuration.configuration_digest,
        observer_version="reference-in-process/v1",
        sequence=sequence,
        binding_verified=True,
    )
