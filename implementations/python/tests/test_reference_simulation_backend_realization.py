"""RUN-315: pure plan interpretation for the reference simulation backend."""

from __future__ import annotations

from aces_contracts.diagnostics import Severity
from aces_contracts.planning import (
    ChangeAction,
    PlannedResource,
    ProvisioningPlan,
    ProvisionOp,
    RuntimeDomain,
)
from aces_reference_simulation_backend import SimulationRealization, interpret_simulation_plan


def _node_resource(address: str, name: str, os_family: str = "linux") -> PlannedResource:
    return PlannedResource(
        address=address,
        domain=RuntimeDomain.PROVISIONING,
        resource_type="node",
        payload={
            "name": name,
            "node_name": name,
            "node_type": "vm",
            "os_family": os_family,
            "spec": {"node": {}, "infrastructure": {"networks": ["lan"]}},
        },
    )


def _network_resource(address: str, name: str) -> PlannedResource:
    return PlannedResource(
        address=address,
        domain=RuntimeDomain.PROVISIONING,
        resource_type="network",
        payload={"name": name, "spec": {"infrastructure": {"properties": {"internal": True}}}},
    )


def _placement_resource(address: str, target: str) -> PlannedResource:
    return PlannedResource(
        address=address,
        domain=RuntimeDomain.PROVISIONING,
        resource_type="content-placement",
        payload={"name": "payload", "target": target},
    )


def _plan(*resources: PlannedResource) -> ProvisioningPlan:
    return ProvisioningPlan(
        resources={resource.address: resource for resource in resources},
        operations=[
            ProvisionOp(
                action=ChangeAction.CREATE,
                address=resource.address,
                resource_type=resource.resource_type,
                payload=resource.payload,
            )
            for resource in resources
        ],
    )


def test_interpret_maps_networks_nodes_and_placements_to_simulation_specs():
    plan = _plan(
        _network_resource("provision.network.lan", "lan"),
        _node_resource("provision.node.web", "web"),
        _placement_resource("provision.content.payload", "provision.node.web"),
    )

    realization = interpret_simulation_plan(plan)

    assert isinstance(realization, SimulationRealization)
    assert [spec.address for spec in realization.networks] == ["provision.network.lan"]
    assert [spec.address for spec in realization.nodes] == ["provision.node.web"]
    assert realization.nodes[0].networks == ("provision.network.lan",)
    assert realization.nodes[0].model_ref == "aces-simulation/linux"
    assert [spec.target_address for spec in realization.placements] == ["provision.node.web"]
    assert not realization.diagnostics


def test_interpret_preserves_plan_pinned_node_source_as_model_ref():
    resource = _node_resource("provision.node.web", "web")
    resource.payload["spec"]["node"]["source"] = {"name": "sim-models/web:v1"}

    realization = interpret_simulation_plan(_plan(resource))

    assert realization.nodes[0].model_ref == "sim-models/web:v1"


def test_interpret_diagnoses_unsupported_resource_type():
    bad = PlannedResource(
        address="provision.mystery.x",
        domain=RuntimeDomain.PROVISIONING,
        resource_type="mystery-resource",
        payload={"name": "x"},
    )

    realization = interpret_simulation_plan(_plan(bad))

    assert {diag.code for diag in realization.diagnostics} == {"reference-simulation.realization.unsupported-resource"}
    assert all(diag.severity == Severity.ERROR for diag in realization.diagnostics)


def test_interpret_diagnostics_never_leak_payload_internals():
    secret = "simulation-token-value"
    bad = PlannedResource(
        address="provision.node.web",
        domain=RuntimeDomain.PROVISIONING,
        resource_type="node",
        payload=secret,  # type: ignore[arg-type]
    )

    realization = interpret_simulation_plan(ProvisioningPlan(resources={bad.address: bad}))

    assert realization.diagnostics
    for diagnostic in realization.diagnostics:
        assert secret not in diagnostic.message
