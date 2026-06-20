"""Hermetic in-process driver (default) for the reference backend.

Records the realize/destroy operations it is asked to perform and
synthesizes portable handles. No subprocess, no container runtime, no IO --
so it is safe in CI and in the default conformance/apply path. It keeps a
private ledger of recorded ops (for test assertions) and a private set of
realized ACES addresses; neither leaks into any portable artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aces_reference_backend.driver import (
    ContainerHandle,
    ContainerSpec,
    DriverResult,
    NetworkHandle,
    NetworkSpec,
)


@dataclass(frozen=True)
class RecordedOp:
    """A recorded driver operation (test/inspection only, not portable)."""

    verb: str
    kind: str
    address: str


@dataclass
class InProcessDriver:
    """Hermetic driver that records ops and synthesizes portable handles."""

    recorded_ops: list[RecordedOp] = field(default_factory=list)
    _realized: set[str] = field(default_factory=set)

    def realize(
        self,
        *,
        networks: tuple[NetworkSpec, ...],
        containers: tuple[ContainerSpec, ...],
    ) -> DriverResult:
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

    def realized_addresses(self) -> frozenset[str]:
        return frozenset(self._realized)
