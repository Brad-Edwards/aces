"""RUN-314: pure plan interpretation tests for the reference backend."""

from __future__ import annotations

from aces_contracts.diagnostics import Severity
from aces_contracts.planning import (
    ChangeAction,
    PlannedResource,
    ProvisioningPlan,
    ProvisionOp,
    RuntimeDomain,
)
from aces_reference_backend import interpret_provisioning_plan
from aces_reference_backend.realization import Realization


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


def test_interpret_maps_nodes_to_container_specs():
    plan = _plan(_node_resource("provision.node.web", "web"))

    realization = interpret_provisioning_plan(plan)

    assert isinstance(realization, Realization)
    assert [spec.address for spec in realization.containers] == ["provision.node.web"]
    assert realization.containers[0].name == "web"
    assert not realization.diagnostics


def test_interpret_maps_networks_to_network_specs():
    plan = _plan(_network_resource("provision.network.lan", "lan"))

    realization = interpret_provisioning_plan(plan)

    assert [spec.address for spec in realization.networks] == ["provision.network.lan"]
    assert realization.networks[0].name == "lan"
    assert realization.networks[0].labels.get("internal") == "true"


def test_interpret_resolves_container_network_references_to_addresses():
    """A node that references a network by name must yield the network's
    resource address in ContainerSpec.networks, so the driver has the single
    portable key it maps to a runtime network name."""

    plan = _plan(
        _node_resource("provision.node.web", "web"),  # infrastructure.networks == ["lan"]
        _network_resource("provision.network.lan", "lan"),
    )

    realization = interpret_provisioning_plan(plan)

    assert realization.containers[0].networks == ("provision.network.lan",)


def test_interpret_passes_through_unresolved_network_reference():
    """An authored reference to a network not in this plan is passed through
    unchanged so the contract stays total."""

    plan = _plan(_node_resource("provision.node.web", "web"))  # references "lan", no network resource

    realization = interpret_provisioning_plan(plan)

    assert realization.containers[0].networks == ("lan",)


def test_interpret_records_placement_resources():
    placement = PlannedResource(
        address="provision.content.payload",
        domain=RuntimeDomain.PROVISIONING,
        resource_type="content-placement",
        payload={"name": "payload", "target": "provision.node.web"},
    )
    plan = _plan(_node_resource("provision.node.web", "web"), placement)

    realization = interpret_provisioning_plan(plan)

    assert [p.address for p in realization.placements] == ["provision.content.payload"]
    assert realization.placements[0].resource_type == "content-placement"


def test_interpret_diagnoses_unsupported_resource_type():
    bad = PlannedResource(
        address="provision.mystery.x",
        domain=RuntimeDomain.PROVISIONING,
        resource_type="mystery-resource",
        payload={"name": "x"},
    )
    plan = _plan(bad)

    realization = interpret_provisioning_plan(plan)

    assert realization.diagnostics
    codes = {diag.code for diag in realization.diagnostics}
    assert "reference-backend.realization.unsupported-resource" in codes
    assert all(diag.severity == Severity.ERROR for diag in realization.diagnostics)


def test_interpret_diagnoses_invalid_node_payload():
    bad = PlannedResource(
        address="provision.node.web",
        domain=RuntimeDomain.PROVISIONING,
        resource_type="node",
        payload="not-a-mapping",  # type: ignore[arg-type]
    )
    plan = ProvisioningPlan(resources={bad.address: bad})

    realization = interpret_provisioning_plan(plan)

    codes = {diag.code for diag in realization.diagnostics}
    assert "reference-backend.realization.invalid-payload" in codes


def test_interpret_diagnostics_never_leak_payload_internals():
    # An invalid payload diagnostic must reference the address/type, not echo
    # the raw payload value.
    secret = "s3cr3t-token-value"
    bad = PlannedResource(
        address="provision.node.web",
        domain=RuntimeDomain.PROVISIONING,
        resource_type="node",
        payload=secret,  # type: ignore[arg-type]
    )
    plan = ProvisioningPlan(resources={bad.address: bad})

    realization = interpret_provisioning_plan(plan)

    for diag in realization.diagnostics:
        assert secret not in diag.message
