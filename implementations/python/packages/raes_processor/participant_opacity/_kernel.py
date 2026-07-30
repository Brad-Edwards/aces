"""Shared SEM-231 information-cell kernel for bounded and model-check lanes."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol


class OpacityKernelPoint(Protocol):
    """Minimum safe point projection consumed by the opacity kernel."""

    ordinal: int
    strategy_ref: str
    order_ref: str
    secret_holds: bool
    initial_information_key: str
    observation_key: str
    memory_key: str
    release_state_key: str
    coalition_fusion_key: str | None


OpacityCellKey = tuple[str, str, str, str, str | None, str, str]
OpacityCellKeyFunction = Callable[[OpacityKernelPoint], OpacityCellKey]


@dataclass(frozen=True)
class OpacityKernelResult:
    """Complete one-sided scan over one canonical reachable point carrier."""

    checked_points: int
    checked_secret_points: int
    counterexample_actual_ordinal: int | None
    counterexample_cell_size: int | None


def information_cell_key(point: OpacityKernelPoint) -> OpacityCellKey:
    """Derive the complete observer information cell from governed coordinates."""

    return (
        point.initial_information_key,
        point.observation_key,
        point.memory_key,
        point.release_state_key,
        point.coalition_fusion_key,
        point.strategy_ref,
        point.order_ref,
    )


def evaluate_opacity_kernel(
    points: Iterable[OpacityKernelPoint],
    *,
    cell_key: OpacityCellKeyFunction = information_cell_key,
) -> OpacityKernelResult:
    """Check every secret point and retain the lowest canonical failure."""

    canonical_points = tuple(sorted(points, key=lambda point: point.ordinal))
    cells: dict[OpacityCellKey, tuple[OpacityKernelPoint, ...]] = {}
    for point in canonical_points:
        key = cell_key(point)
        cells[key] = (*cells.get(key, ()), point)

    secret_points = tuple(point for point in canonical_points if point.secret_holds)
    counterexample_actual_ordinal: int | None = None
    counterexample_cell_size: int | None = None
    for actual in secret_points:
        cell = cells[cell_key(actual)]
        if any(not candidate.secret_holds for candidate in cell):
            continue
        if counterexample_actual_ordinal is None:
            counterexample_actual_ordinal = actual.ordinal
            counterexample_cell_size = len(cell)

    return OpacityKernelResult(
        checked_points=len(canonical_points),
        checked_secret_points=len(secret_points),
        counterexample_actual_ordinal=counterexample_actual_ordinal,
        counterexample_cell_size=counterexample_cell_size,
    )


__all__ = (
    "OpacityCellKey",
    "OpacityKernelPoint",
    "OpacityKernelResult",
    "evaluate_opacity_kernel",
    "information_cell_key",
)
