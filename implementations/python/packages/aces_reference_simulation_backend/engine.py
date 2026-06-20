"""Hermetic in-process simulation engine boundary for RUN-315.

The engine is intentionally small: it records simulated resources and a
monotonic simulation tick, but it never exposes native simulator ids or
private state through snapshots, diagnostics, or manifest payloads. Future
simulator adapters can implement the same protocol and remain behind the
registry config seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from aces_contracts.diagnostics import Diagnostic


@dataclass(frozen=True)
class SimulationNetworkSpec:
    """Portable description of a simulated network."""

    address: str
    name: str
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulationNodeSpec:
    """Portable description of a simulated node."""

    address: str
    name: str
    node_type: str
    os_family: str
    model_ref: str
    networks: tuple[str, ...] = ()
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulationPlacementSpec:
    """Portable description of a simulated content/account/feature binding."""

    address: str
    resource_type: str
    name: str
    target_address: str | None


@dataclass(frozen=True)
class SimulationEvent:
    """A private engine event recorded for tests and inspection only."""

    tick: int
    verb: str
    kind: str
    address: str


@dataclass(frozen=True)
class SimulationResult:
    """Aggregate result of a simulation engine operation."""

    events: tuple[SimulationEvent, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()


class SimulationEngine(Protocol):
    """Protocol for simulator adapters behind the reference target."""

    def realize(
        self,
        *,
        networks: tuple[SimulationNetworkSpec, ...],
        nodes: tuple[SimulationNodeSpec, ...],
        placements: tuple[SimulationPlacementSpec, ...],
    ) -> SimulationResult:
        """Realize the given portable simulation specs."""
        ...

    def destroy(self, *, addresses: tuple[str, ...]) -> SimulationResult:
        """Destroy simulated resources for the given ACES addresses."""
        ...

    def realized_addresses(self) -> frozenset[str]:
        """Return currently realized ACES addresses."""
        ...

    def tick(self) -> int:
        """Return the current simulation tick."""
        ...

    def event_count(self) -> int:
        """Return the number of recorded simulation events."""
        ...


@dataclass
class InProcessSimulationEngine:
    """Deterministic, no-IO simulation engine used by default."""

    events: list[SimulationEvent] = field(default_factory=list)
    _realized: dict[str, str] = field(default_factory=dict)
    _tick: int = 0

    def realize(
        self,
        *,
        networks: tuple[SimulationNetworkSpec, ...],
        nodes: tuple[SimulationNodeSpec, ...],
        placements: tuple[SimulationPlacementSpec, ...],
    ) -> SimulationResult:
        events: list[SimulationEvent] = []
        for spec in networks:
            events.append(self._record("realize", "network", spec.address))
        for spec in nodes:
            events.append(self._record("realize", "node", spec.address))
        for spec in placements:
            events.append(self._record("realize", spec.resource_type, spec.address))
        return SimulationResult(events=tuple(events))

    def destroy(self, *, addresses: tuple[str, ...]) -> SimulationResult:
        events: list[SimulationEvent] = []
        for address in addresses:
            kind = self._realized.pop(address, "resource")
            events.append(self._record("destroy", kind, address, realize=False))
        return SimulationResult(events=tuple(events))

    def realized_addresses(self) -> frozenset[str]:
        return frozenset(self._realized)

    def tick(self) -> int:
        return self._tick

    def event_count(self) -> int:
        return len(self.events)

    def _record(self, verb: str, kind: str, address: str, *, realize: bool = True) -> SimulationEvent:
        self._tick += 1
        if realize:
            self._realized[address] = kind
        event = SimulationEvent(tick=self._tick, verb=verb, kind=kind, address=address)
        self.events.append(event)
        return event
