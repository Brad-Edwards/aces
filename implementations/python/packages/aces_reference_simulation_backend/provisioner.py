"""Reference simulation provisioner: portable snapshots plus engine state."""

from __future__ import annotations

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.planning import ChangeAction, ProvisioningPlan, RuntimeDomain
from aces_contracts.runtime_state import ApplyResult, RuntimeSnapshot, SnapshotEntry

from .engine import SimulationEngine
from .realization import SimulationRealization, interpret_simulation_plan


class ReferenceSimulationProvisioner:
    """Provisioner that realizes plans through an injected simulation engine."""

    def __init__(self, engine: SimulationEngine) -> None:
        self._engine = engine

    @staticmethod
    def validate(plan: ProvisioningPlan) -> list[Diagnostic]:
        realization = interpret_simulation_plan(plan)
        return list(realization.diagnostics)

    def apply(self, plan: ProvisioningPlan, snapshot: RuntimeSnapshot) -> ApplyResult:
        realization = interpret_simulation_plan(plan)
        diagnostics: list[Diagnostic] = list(realization.diagnostics)
        if any(diagnostic.is_error for diagnostic in diagnostics):
            return ApplyResult(success=False, snapshot=snapshot, diagnostics=diagnostics)

        entries = dict(snapshot.entries)
        changed_addresses: list[str] = []
        delete_addresses: list[str] = []

        for op in plan.operations:
            if op.action == ChangeAction.DELETE:
                entries.pop(op.address, None)
                changed_addresses.append(op.address)
                delete_addresses.append(op.address)
                continue
            status = "unchanged" if op.action == ChangeAction.UNCHANGED else "simulated"
            entries[op.address] = SnapshotEntry(
                address=op.address,
                domain=RuntimeDomain.PROVISIONING,
                resource_type=op.resource_type,
                payload=op.payload,
                ordering_dependencies=op.ordering_dependencies,
                refresh_dependencies=op.refresh_dependencies,
                status=status,
            )
            if op.action != ChangeAction.UNCHANGED:
                changed_addresses.append(op.address)

        diagnostics.extend(self._drive(plan, realization, delete_addresses))
        if any(diagnostic.is_error for diagnostic in diagnostics):
            return ApplyResult(success=False, snapshot=snapshot, diagnostics=diagnostics)

        metadata = _simulation_metadata(snapshot, self._engine)
        return ApplyResult(
            success=True,
            snapshot=snapshot.with_entries(entries, metadata=metadata),
            diagnostics=diagnostics,
            changed_addresses=changed_addresses,
            details={"reference_simulation": dict(metadata["reference_simulation"])},
        )

    def _drive(
        self,
        plan: ProvisioningPlan,
        realization: SimulationRealization,
        delete_addresses: list[str],
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        active = {op.address for op in plan.operations if op.action in {ChangeAction.CREATE, ChangeAction.UPDATE}}
        networks = tuple(spec for spec in realization.networks if spec.address in active)
        nodes = tuple(spec for spec in realization.nodes if spec.address in active)
        placements = tuple(spec for spec in realization.placements if spec.address in active)
        if networks or nodes or placements:
            result = self._engine.realize(networks=networks, nodes=nodes, placements=placements)
            diagnostics.extend(result.diagnostics)
        if delete_addresses:
            result = self._engine.destroy(addresses=tuple(delete_addresses))
            diagnostics.extend(result.diagnostics)
        return diagnostics


def _simulation_metadata(snapshot: RuntimeSnapshot, engine: SimulationEngine) -> dict[str, object]:
    metadata = dict(snapshot.metadata)
    metadata["reference_simulation"] = {
        "backend": "reference-simulation",
        "engine": "in-process-discrete",
        "clock": "simulation_tick",
        "tick": engine.tick(),
        "event_count": engine.event_count(),
        "realized_resource_count": len(engine.realized_addresses()),
    }
    return metadata
