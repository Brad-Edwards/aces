"""Portable driver boundary for the libvirt/QEMU provisioning backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.realization_envelope import ObservationStrength, RealizationConcern

from .cloudinit import CloudInitSpec


@dataclass(frozen=True)
class NetworkSpec:
    """Portable libvirt network intent derived from an ACES resource."""

    address: str
    name: str
    cidr: str | None = None
    gateway: str | None = None
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ServiceSpec:
    """Portable service listener intent derived from an ACES node resource."""

    name: str
    port: int
    protocol: str = "tcp"


@dataclass(frozen=True)
class NetworkAcl:
    """Portable network access-control rule realized as a libvirt nwfilter rule."""

    name: str
    # action is "accept" | "drop"; direction is "in" | "out" | "inout";
    # protocol is "tcp" | "udp" | "all".
    action: str
    direction: str
    protocol: str
    src_cidr: str | None = None
    dst_cidr: str | None = None
    ports: tuple[int, ...] = ()


@dataclass(frozen=True)
class DomainSpec:
    """Portable libvirt domain intent derived from an ACES node resource."""

    address: str
    name: str
    image_ref: str | None
    memory_mib: int = 512
    vcpus: int = 1
    networks: tuple[str, ...] = ()
    services: tuple[ServiceSpec, ...] = ()
    cloud_init: CloudInitSpec | None = None
    network_acls: tuple[NetworkAcl, ...] = ()
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class NetworkHandle:
    """Portable realization result for a network."""

    address: str
    realized: bool = True


@dataclass(frozen=True)
class DomainHandle:
    """Portable realization result for a domain."""

    address: str
    realized: bool = True


@dataclass(frozen=True)
class RealizationObservation:
    """Bounded typed readback for one realized concern field."""

    address: str
    field_path: str
    concern: RealizationConcern
    source: ObservationStrength
    value: object


@dataclass(frozen=True)
class DriverResult:
    """Aggregate portable result from a libvirt driver call."""

    networks: tuple[NetworkHandle, ...] = ()
    domains: tuple[DomainHandle, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    observations: tuple[RealizationObservation, ...] = ()


class LibvirtDriver(Protocol):
    """Host-process boundary for libvirt realization."""

    def realize(
        self,
        *,
        networks: tuple[NetworkSpec, ...],
        domains: tuple[DomainSpec, ...],
    ) -> DriverResult:
        """Realize the requested networks and domains."""
        ...

    def destroy(
        self,
        *,
        networks: tuple[str, ...],
        domains: tuple[str, ...],
    ) -> DriverResult:
        """Destroy resources by ACES address."""
        ...

    def realized_addresses(self) -> frozenset[str]:
        """Return ACES addresses currently known as realized."""
        ...
