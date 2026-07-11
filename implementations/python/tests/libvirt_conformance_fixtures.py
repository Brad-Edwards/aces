"""Daemon-free libvirt driver double for hermetic conformance (issue #606).

``RecordingLibvirtDriver`` implements the :class:`LibvirtDriver` protocol and
*confirms* realization (returns ``realized=True`` handles) while recording the
ACES addresses it was asked to realize/destroy. Injecting it via
``create_libvirt_target(driver=...)`` exercises the real ``LibvirtProvisioner``
path -- plan validation, capability-envelope checks, snapshot reconciliation,
``_drive`` dispatch, and the unconfirmed-realization guard -- with no libvirt
daemon, so ``run_target_conformance`` can prove real snapshot mutation in the
hermetic verification graph. The real libvirt/QEMU daemon path stays covered by
the out-of-band real-daemon smoke.

This is deliberately NOT a no-op driver: a no-op returns unconfirmed handles,
which the provisioner reports as ``libvirt-backend.driver.unconfirmed-realization``
errors -- so it could never serve as the conformance realization proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aces_backend_libvirt.driver import (
    DomainHandle,
    DomainSpec,
    DriverResult,
    NetworkHandle,
    NetworkSpec,
)


@dataclass(frozen=True)
class RecordedOp:
    """A recorded driver operation (test/inspection only, never portable)."""

    verb: str
    kind: str
    address: str


@dataclass
class RecordingLibvirtDriver:
    """Hermetic libvirt driver that confirms realization and records ops."""

    driver_mode = "generic"

    recorded_ops: list[RecordedOp] = field(default_factory=list)
    _realized: set[str] = field(default_factory=set)

    def realize(
        self,
        *,
        networks: tuple[NetworkSpec, ...],
        domains: tuple[DomainSpec, ...],
    ) -> DriverResult:
        network_handles: list[NetworkHandle] = []
        for spec in networks:
            self.recorded_ops.append(RecordedOp(verb="realize", kind="network", address=spec.address))
            self._realized.add(spec.address)
            network_handles.append(NetworkHandle(address=spec.address, realized=True))
        domain_handles: list[DomainHandle] = []
        for spec in domains:
            self.recorded_ops.append(RecordedOp(verb="realize", kind="domain", address=spec.address))
            self._realized.add(spec.address)
            domain_handles.append(DomainHandle(address=spec.address, realized=True))
        return DriverResult(networks=tuple(network_handles), domains=tuple(domain_handles))

    def destroy(
        self,
        *,
        networks: tuple[str, ...],
        domains: tuple[str, ...],
    ) -> DriverResult:
        domain_handles: list[DomainHandle] = []
        for address in domains:
            self.recorded_ops.append(RecordedOp(verb="destroy", kind="domain", address=address))
            self._realized.discard(address)
            domain_handles.append(DomainHandle(address=address, realized=False))
        network_handles: list[NetworkHandle] = []
        for address in networks:
            self.recorded_ops.append(RecordedOp(verb="destroy", kind="network", address=address))
            self._realized.discard(address)
            network_handles.append(NetworkHandle(address=address, realized=False))
        return DriverResult(networks=tuple(network_handles), domains=tuple(domain_handles))

    def realized_addresses(self) -> frozenset[str]:
        return frozenset(self._realized)
