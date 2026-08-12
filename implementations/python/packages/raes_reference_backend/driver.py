"""Portable driver boundary for the reference emulation backend (RUN-314).

The ``DeploymentDriver`` protocol is the host-process / emulator boundary.
Specs describe what to realize in portable RAES terms; handles describe
what was realized in portable RAES terms. No spec or handle carries a
container/VM/network id, host path, environment, credential, argv, or any
backend-native repr -- only references, digests, and labels that are safe
to surface in a snapshot, diagnostic, or conformance report.

Drivers return ``Diagnostic`` values and handles; they never raise a
backend-specific exception hierarchy. Programmer errors (a malformed call
from inside this package) may raise ordinary exceptions, which the runtime
adapter (`_call_backend_apply`) converts into diagnostics at the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.realization_observation import RealizationObservation


@dataclass(frozen=True)
class NetworkSpec:
    """Portable description of a network to realize.

    ``address`` is the RAES resource address. ``labels`` carries only
    non-sensitive classification labels (e.g. ``{"internal": "true"}``).
    """

    address: str
    name: str
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ServiceSpec:
    """Portable authored service descriptor carried to a deployment driver.

    The descriptor identifies a node-local transport binding. Its presence
    does not authorize traffic, publish a host port, or prove that a listener
    exists. Drivers may inspect it when declaring service support, but must not
    infer reachability from it.
    """

    port: int
    protocol: str
    name: str = ""


@dataclass(frozen=True)
class ContainerSpec:
    """Portable description of a container to realize.

    ``image_ref`` is a portable image reference (a name/tag or digest), not
    a pulled local image id. ``networks`` are RAES network resource
    addresses. ``services`` preserves authored node-local transport binding
    descriptors without granting reachability or host publication. ``labels``
    carries only non-sensitive classification labels.
    """

    address: str
    name: str
    image_ref: str
    networks: tuple[str, ...] = ()
    labels: dict[str, str] = field(default_factory=dict)
    services: tuple[ServiceSpec, ...] = ()
    network_namespace_target: str = ""


@dataclass(frozen=True)
class NetworkHandle:
    """Portable result of realizing a network.

    Carries the RAES ``address`` and a ``realized`` flag only. A real driver
    must NOT place the backend-native network id here.
    """

    address: str
    realized: bool = True


@dataclass(frozen=True)
class ContainerHandle:
    """Portable result of realizing a container.

    Carries the RAES ``address`` and a ``realized`` flag only. A real driver
    must NOT place the backend-native container id, inspect payload, or host
    path here.
    """

    address: str
    realized: bool = True


@dataclass(frozen=True)
class DriverResult:
    """Aggregate portable result of a realize/destroy call."""

    networks: tuple[NetworkHandle, ...] = ()
    containers: tuple[ContainerHandle, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    observations: tuple[RealizationObservation, ...] = ()


class DeploymentDriver(Protocol):
    """Host-process boundary for realizing a portable deployment.

    Implementations realize networks then containers, and destroy
    containers then networks. All inputs and outputs are portable; the
    concrete implementation owns any backend-native bookkeeping privately.
    """

    def realize(
        self,
        *,
        networks: tuple[NetworkSpec, ...],
        containers: tuple[ContainerSpec, ...],
    ) -> DriverResult:
        """Realize the given networks and containers; return portable handles."""
        ...

    def destroy(
        self,
        *,
        networks: tuple[str, ...],
        containers: tuple[str, ...],
    ) -> DriverResult:
        """Destroy the realized resources for the given RAES addresses."""
        ...

    def observe(self, *, containers: tuple[ContainerSpec, ...]) -> DriverResult:
        """Read existing containers without mutating their native state."""
        ...

    def realized_addresses(self) -> frozenset[str]:
        """Return the set of RAES addresses currently realized by this driver."""
        ...
