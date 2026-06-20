"""Reference simulation backend (RUN-315).

A concrete reference backend implementing the standard backend protocol roles
through a hermetic in-process simulation engine. It publishes capability through
``BackendManifest`` and registers on ``BackendRegistry`` as
``reference-simulation``.
"""

from __future__ import annotations

from .engine import (
    InProcessSimulationEngine,
    SimulationEngine,
    SimulationEvent,
    SimulationNetworkSpec,
    SimulationNodeSpec,
    SimulationPlacementSpec,
    SimulationResult,
)
from .manifest import REFERENCE_SIMULATION_BACKEND_NAME, create_reference_simulation_backend_manifest
from .provisioner import ReferenceSimulationProvisioner
from .realization import SimulationRealization, interpret_simulation_plan
from .target import (
    create_reference_simulation_backend_components,
    create_reference_simulation_backend_target,
    register_reference_simulation_backend,
)

__all__ = [
    "REFERENCE_SIMULATION_BACKEND_NAME",
    "InProcessSimulationEngine",
    "ReferenceSimulationProvisioner",
    "SimulationEngine",
    "SimulationEvent",
    "SimulationNetworkSpec",
    "SimulationNodeSpec",
    "SimulationPlacementSpec",
    "SimulationRealization",
    "SimulationResult",
    "create_reference_simulation_backend_components",
    "create_reference_simulation_backend_manifest",
    "create_reference_simulation_backend_target",
    "interpret_simulation_plan",
    "register_reference_simulation_backend",
]
