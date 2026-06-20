"""RUN-315: simulation provisioner apply via the control plane."""

from __future__ import annotations

import textwrap

from aces_contracts.planning import ChangeAction, PlannedResource, ProvisioningPlan, ProvisionOp, RuntimeDomain
from aces_reference_simulation_backend import (
    InProcessSimulationEngine,
    create_reference_simulation_backend_components,
    create_reference_simulation_backend_manifest,
)

from aces.core.runtime.control_plane import RuntimeControlPlane
from aces.core.runtime.manager import RuntimeManager
from aces.core.runtime.registry import RuntimeTarget
from aces.core.sdl import parse_sdl

_SCENARIO = """
name: sim-provisioner
nodes:
  web:
    type: vm
    os: linux
    resources: {ram: 1 gib, cpu: 1}
"""


def _target_with_engine(engine: InProcessSimulationEngine) -> RuntimeTarget:
    manifest = create_reference_simulation_backend_manifest()
    components = create_reference_simulation_backend_components(manifest=manifest, engine=engine)
    return RuntimeTarget(
        name="reference-simulation",
        manifest=manifest,
        provisioner=components.provisioner,
        orchestrator=components.orchestrator,
        evaluator=components.evaluator,
        participant_runtime=components.participant_runtime,
    )


def _provisioning_plan(target: RuntimeTarget) -> ProvisioningPlan:
    manager = RuntimeManager(target)
    execution_plan = manager.plan(parse_sdl(textwrap.dedent(_SCENARIO)))
    return execution_plan.provisioning


def test_apply_via_control_plane_records_entries_and_drives_engine():
    engine = InProcessSimulationEngine()
    target = _target_with_engine(engine)
    plan = _provisioning_plan(target)

    control_plane = RuntimeControlPlane(target)
    receipt = control_plane.submit_provisioning(plan)
    status = control_plane.get_operation(receipt.operation_id)

    assert status is not None
    assert status.state.value == "succeeded"
    snapshot = control_plane.snapshot
    assert "provision.node.web" in snapshot.entries
    assert snapshot.entries["provision.node.web"].status == "simulated"
    assert "provision.node.web" in engine.realized_addresses()
    assert snapshot.metadata["reference_simulation"]["clock"] == "simulation_tick"
    assert snapshot.metadata["reference_simulation"]["tick"] >= 1


def test_apply_handles_delete_and_unchanged_without_leaking_engine_state():
    engine = InProcessSimulationEngine()
    target = _target_with_engine(engine)
    plan = _provisioning_plan(target)
    control_plane = RuntimeControlPlane(target)
    control_plane.submit_provisioning(plan)

    delete_plan = ProvisioningPlan(
        operations=[
            ProvisionOp(
                action=ChangeAction.DELETE,
                address="provision.node.web",
                resource_type="node",
                payload={},
            )
        ]
    )
    receipt = control_plane.submit_provisioning(delete_plan)
    status = control_plane.get_operation(receipt.operation_id)

    assert status is not None and status.state.value == "succeeded"
    assert "provision.node.web" not in control_plane.snapshot.entries
    assert "provision.node.web" not in engine.realized_addresses()
    rendered = repr(control_plane.snapshot.entries)
    for forbidden in ("InProcessSimulationEngine", "native_id", "simulation-token", "engine_state"):
        assert forbidden not in rendered


def test_validate_surfaces_realization_diagnostics_without_driving_engine():
    engine = InProcessSimulationEngine()
    target = _target_with_engine(engine)
    bad_plan = ProvisioningPlan(
        resources={
            "provision.mystery.x": PlannedResource(
                address="provision.mystery.x",
                domain=RuntimeDomain.PROVISIONING,
                resource_type="mystery",
                payload={"name": "x"},
            )
        }
    )

    diagnostics = target.provisioner.validate(bad_plan)

    assert any(diag.code == "reference-simulation.realization.unsupported-resource" for diag in diagnostics)
    assert not engine.realized_addresses()
