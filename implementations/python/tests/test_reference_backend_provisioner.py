"""RUN-314: provisioner apply via the control plane."""

from __future__ import annotations

import textwrap

import pytest
from aces_contracts.planning import (
    ChangeAction,
    PlannedResource,
    ProvisioningPlan,
    ProvisionOp,
    RuntimeDomain,
)
from aces_reference_backend import (
    create_reference_backend_components,
    create_reference_backend_manifest,
)
from aces_reference_backend.drivers.inprocess import InProcessDriver

from aces.core.runtime.control_plane import RuntimeControlPlane
from aces.core.runtime.manager import RuntimeManager
from aces.core.runtime.registry import RuntimeTarget
from aces.core.sdl import parse_sdl

_SCENARIO = """
name: ref-provisioner
nodes:
  web:
    type: vm
    os: linux
    resources: {ram: 1 gib, cpu: 1}
"""


def _target_with_driver(driver: InProcessDriver) -> RuntimeTarget:
    manifest = create_reference_backend_manifest()
    components = create_reference_backend_components(manifest=manifest, driver=driver)
    return RuntimeTarget(
        name="reference-emulation",
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


def test_apply_via_control_plane_records_entries_and_drives_driver():
    driver = InProcessDriver()
    target = _target_with_driver(driver)
    plan = _provisioning_plan(target)

    control_plane = RuntimeControlPlane(target)
    receipt = control_plane.submit_provisioning(plan)
    status = control_plane.get_operation(receipt.operation_id)

    assert status is not None
    assert status.state.value == "succeeded"
    snapshot = control_plane.snapshot
    assert "provision.node.web" in snapshot.entries
    assert snapshot.entries["provision.node.web"].status == "applied"
    # The driver was actually invoked to realize the container.
    realized = [op for op in driver.recorded_ops if op.verb == "realize" and op.kind == "container"]
    assert any(op.address == "provision.node.web" for op in realized)


def test_apply_handles_delete_and_unchanged():
    driver = InProcessDriver()
    target = _target_with_driver(driver)
    plan = _provisioning_plan(target)
    control_plane = RuntimeControlPlane(target)
    control_plane.submit_provisioning(plan)

    # Now submit a DELETE for the realized node.
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
    destroyed = [op for op in driver.recorded_ops if op.verb == "destroy" and op.kind == "container"]
    assert any(op.address == "provision.node.web" for op in destroyed)


def test_unchanged_op_keeps_entry_without_driver_realize():
    driver = InProcessDriver()
    target = _target_with_driver(driver)
    unchanged_plan = ProvisioningPlan(
        resources={
            "provision.node.web": PlannedResource(
                address="provision.node.web",
                domain=RuntimeDomain.PROVISIONING,
                resource_type="node",
                payload={"name": "web", "node_type": "vm", "os_family": "linux"},
            )
        },
        operations=[
            ProvisionOp(
                action=ChangeAction.UNCHANGED,
                address="provision.node.web",
                resource_type="node",
                payload={"name": "web", "node_type": "vm", "os_family": "linux"},
            )
        ],
    )
    control_plane = RuntimeControlPlane(target)
    control_plane.submit_provisioning(unchanged_plan)

    entry = control_plane.snapshot.entries["provision.node.web"]
    assert entry.status == "unchanged"
    assert not [op for op in driver.recorded_ops if op.verb == "realize"]


def test_snapshot_payload_carries_only_portable_facts():
    driver = InProcessDriver()
    target = _target_with_driver(driver)
    plan = _provisioning_plan(target)
    control_plane = RuntimeControlPlane(target)
    control_plane.submit_provisioning(plan)

    snapshot = control_plane.snapshot
    # The realized snapshot entry preserves the planned payload (portable) and
    # never embeds a backend-native container id, host path, or daemon repr.
    entry = snapshot.entries["provision.node.web"]
    rendered = repr(entry.payload)
    for forbidden in ("docker", "podman", "container_id", "/var/run", "sha256:", "InProcessDriver"):
        assert forbidden not in rendered


def test_invalid_resource_type_is_rejected_before_provisioner_validation():
    driver = InProcessDriver()
    _target_with_driver(driver)

    with pytest.raises(ValueError, match="resource_type must belong"):
        ProvisioningPlan(
            resources={
                "provision.mystery.x": PlannedResource(
                    address="provision.mystery.x",
                    domain=RuntimeDomain.PROVISIONING,
                    resource_type="mystery",
                    payload={"name": "x"},
                )
            }
        )
    assert not driver.recorded_ops
