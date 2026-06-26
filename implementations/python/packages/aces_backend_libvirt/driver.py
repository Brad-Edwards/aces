"""Portable driver boundary for the libvirt/QEMU provisioning backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from aces_contracts.diagnostics import Diagnostic


@dataclass(frozen=True)
class NetworkSpec:
    """Portable libvirt network intent derived from an ACES resource."""

    address: str
    name: str
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DomainSpec:
    """Portable libvirt domain intent derived from an ACES node resource."""

    address: str
    name: str
    image_ref: str | None
    memory_mib: int = 512
    vcpus: int = 1
    networks: tuple[str, ...] = ()
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
class DriverResult:
    """Aggregate portable result from a libvirt driver call."""

    networks: tuple[NetworkHandle, ...] = ()
    domains: tuple[DomainHandle, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()


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
