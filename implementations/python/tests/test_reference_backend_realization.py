"""RUN-314: pure plan interpretation tests for the reference backend."""

from __future__ import annotations

import pytest
from raes_contracts.planning import (
    ChangeAction,
    PlannedResource,
    ProvisioningPlan,
    ProvisionOp,
    RuntimeDomain,
)
from raes_reference_backend import interpret_provisioning_plan
from raes_reference_backend.driver import ServiceSpec
from raes_reference_backend.realization import Realization


def _node_resource(
    address: str,
    name: str,
    os_family: str = "linux",
    *,
    services: list[dict[str, object]] | None = None,
    network_namespace_target: str = "",
) -> PlannedResource:
    return PlannedResource(
        address=address,
        domain=RuntimeDomain.PROVISIONING,
        resource_type="node",
        payload={
            "name": name,
            "node_name": name,
            "node_type": "vm",
            "os_family": os_family,
            "network_namespace_target": network_namespace_target,
            "spec": {
                "node": {"services": services or []},
                "infrastructure": {"networks": ["lan"]},
            },
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


def test_interpret_preserves_named_and_unnamed_service_descriptors():
    plan = _plan(
        _node_resource(
            "provision.node.web",
            "web",
            services=[
                {"port": 80, "protocol": "tcp", "name": "http"},
                {"port": 5000, "protocol": "sctp", "name": ""},
            ],
        )
    )

    realization = interpret_provisioning_plan(plan)

    assert realization.containers[0].services == (
        ServiceSpec(port=80, protocol="tcp", name="http"),
        ServiceSpec(port=5000, protocol="sctp", name=""),
    )
    assert not realization.diagnostics


def test_interpret_rejects_malformed_service_without_leaking_payload():
    sentinel = "TOKEN-LEAK-SENTINEL-XYZ"
    plan = _plan(
        _node_resource(
            "provision.node.web",
            "web",
            services=[{"port": sentinel, "protocol": "tcp", "name": "http"}],
        )
    )

    realization = interpret_provisioning_plan(plan)

    codes = {diagnostic.code for diagnostic in realization.diagnostics}
    assert "reference-backend.realization.service-invalid" in codes
    assert all(sentinel not in diagnostic.message for diagnostic in realization.diagnostics)


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


def test_interpret_carries_canonical_network_namespace_target_and_orders_owner_first():
    plan = _plan(
        _node_resource(
            "provision.node.aaa-capture",
            "aaa-capture",
            network_namespace_target="provision.node.zzz-owner",
        ),
        _node_resource("provision.node.zzz-owner", "zzz-owner"),
    )

    realization = interpret_provisioning_plan(plan)

    assert [spec.address for spec in realization.containers] == [
        "provision.node.zzz-owner",
        "provision.node.aaa-capture",
    ]
    assert realization.containers[1].network_namespace_target == "provision.node.zzz-owner"


def test_interpret_passes_through_unresolved_network_reference():
    """An authored reference to a network not in this plan is passed through
    unchanged so the contract stays total."""

    plan = _plan(_node_resource("provision.node.web", "web"))  # references "lan", no network resource

    realization = interpret_provisioning_plan(plan)

    assert realization.containers[0].networks == ("lan",)


def test_interpret_does_not_guess_network_from_address_tail():
    network = _network_resource("provision.network.shared.lan", "shared.lan")
    plan = _plan(_node_resource("provision.node.web", "web"), network)

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


def test_plan_rejects_unsupported_resource_type_before_interpretation():
    bad = PlannedResource(
        address="provision.mystery.x",
        domain=RuntimeDomain.PROVISIONING,
        resource_type="mystery-resource",
        payload={"name": "x"},
    )
    with pytest.raises(ValueError, match="resource_type must belong"):
        _plan(bad)


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
