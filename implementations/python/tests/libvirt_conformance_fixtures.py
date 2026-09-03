"""Daemon-free libvirt driver double for hermetic conformance (issue #606).

``RecordingLibvirtDriver`` implements the :class:`LibvirtDriver` protocol and
*confirms* realization (returns ``realized=True`` handles) while recording the
RAES addresses it was asked to realize/destroy. Injecting it via
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

from raes_backend_libvirt.driver import (
    DomainHandle,
    DomainSpec,
    DriverResult,
    NetworkHandle,
    NetworkSpec,
)
from raes_backend_libvirt.envelopes import load_libvirt_realization_envelope
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.realization_envelope import ObservationStrength, RealizationConcern
from raes_contracts.realization_observation import RealizationObservation


@dataclass(frozen=True)
class RecordedOp:
    """A recorded driver operation (test/inspection only, never portable)."""

    verb: str
    kind: str
    address: str


def daemon_compute_substrate_observations(
    domains: tuple[DomainSpec, ...],
) -> tuple[RealizationObservation, ...]:
    """Model independent libvirt daemon readback in hermetic driver doubles."""

    envelope = load_libvirt_realization_envelope("generic")
    return tuple(
        RealizationObservation(
            address=spec.address,
            field_path="compute-substrate",
            concern=RealizationConcern.COMPUTE_SUBSTRATE,
            source=ObservationStrength.DAEMON_OBSERVED,
            value="virtual-machine",
            envelope_digest=envelope.digest,
            configuration_digest=envelope.configuration.configuration_digest,
            observer_version="hermetic-libvirt-daemon/v1",
            sequence=index,
            binding_verified=True,
        )
        for index, spec in enumerate(domains)
    )


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
        return DriverResult(
            networks=tuple(network_handles),
            domains=tuple(domain_handles),
            observations=daemon_compute_substrate_observations(domains),
        )

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

    def observe(self, *, domains: tuple[DomainSpec, ...]) -> DriverResult:
        """Model observation-only daemon readback for already realized domains."""

        observed = tuple(spec for spec in domains if spec.address in self._realized)
        missing = tuple(spec for spec in domains if spec.address not in self._realized)
        for spec in observed:
            self.recorded_ops.append(RecordedOp(verb="observe", kind="domain", address=spec.address))
        return DriverResult(
            domains=tuple(DomainHandle(address=spec.address, realized=True) for spec in observed),
            diagnostics=tuple(
                Diagnostic(
                    code="libvirt-backend.driver.compute-substrate-unobserved",
                    domain="runtime",
                    address=spec.address,
                    message=f"Hermetic libvirt daemon did not observe '{spec.address}'.",
                )
                for spec in missing
            ),
            observations=daemon_compute_substrate_observations(observed),
        )

    def realized_addresses(self) -> frozenset[str]:
        return frozenset(self._realized)
