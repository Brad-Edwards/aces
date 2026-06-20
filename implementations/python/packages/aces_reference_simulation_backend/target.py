"""Runtime target construction + registry registration for RUN-315."""

from __future__ import annotations

from aces_backend_protocols.capabilities import BackendManifest
from aces_runtime.registry import BackendRegistry, RuntimeTarget, RuntimeTargetComponents

from .engine import InProcessSimulationEngine, SimulationEngine
from .evaluator import ReferenceSimulationEvaluator
from .manifest import REFERENCE_SIMULATION_BACKEND_NAME, create_reference_simulation_backend_manifest
from .orchestrator import ReferenceSimulationOrchestrator
from .participant_runtime import ReferenceSimulationParticipantRuntime
from .provisioner import ReferenceSimulationProvisioner


def create_reference_simulation_backend_components(
    *,
    manifest: BackendManifest,
    engine: SimulationEngine | None = None,
    **config,
) -> RuntimeTargetComponents:
    """Build reference simulation backend components for a manifest."""

    del config
    simulation_engine = engine if engine is not None else InProcessSimulationEngine()
    return RuntimeTargetComponents(
        provisioner=ReferenceSimulationProvisioner(simulation_engine),
        orchestrator=ReferenceSimulationOrchestrator() if manifest.has_orchestrator else None,
        evaluator=ReferenceSimulationEvaluator() if manifest.has_evaluator else None,
        participant_runtime=(ReferenceSimulationParticipantRuntime() if manifest.has_participant_runtime else None),
    )


def create_reference_simulation_backend_target(**config) -> RuntimeTarget:
    """Return a fully configured reference simulation backend target."""

    manifest = create_reference_simulation_backend_manifest(**config)
    components = create_reference_simulation_backend_components(manifest=manifest, **config)
    return RuntimeTarget(
        name=REFERENCE_SIMULATION_BACKEND_NAME,
        manifest=manifest,
        provisioner=components.provisioner,
        orchestrator=components.orchestrator,
        evaluator=components.evaluator,
        participant_runtime=components.participant_runtime,
    )


def register_reference_simulation_backend(registry: BackendRegistry) -> None:
    """Register the reference simulation backend descriptor on ``registry``."""

    registry.register(
        REFERENCE_SIMULATION_BACKEND_NAME,
        create_reference_simulation_backend_manifest,
        create_reference_simulation_backend_components,
    )
