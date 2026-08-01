"""Public payload-accessor tests for planned resources."""

from __future__ import annotations

from raes_contracts.planning import (
    PlannedResource,
    RuntimeDomain,
    planned_infrastructure_spec,
    planned_node_resources,
    planned_node_source,
    planned_node_spec,
    planned_resource_authored_name,
    planned_resource_name,
    planned_resource_payload,
)


def test_node_accessors_preserve_authored_mapping_shapes() -> None:
    source = {"name": "images/base.qcow2", "build": {"format": "qcow2"}}
    resources = {"ram": 1_073_741_824, "cpu": 2}
    infrastructure = {"networks": ["lan"], "properties": {"zone": "test"}}
    node = {"source": source, "resources": resources}
    payload = {
        "name": "web",
        "spec": {"node": node, "infrastructure": infrastructure},
    }
    resource = PlannedResource(
        address="provision.node.web",
        domain=RuntimeDomain.PROVISIONING,
        resource_type="node",
        payload=payload,
    )

    assert planned_resource_payload(resource) is payload
    assert planned_node_spec(resource) is node
    assert planned_node_source(resource) is source
    assert planned_node_resources(resource) is resources
    assert planned_infrastructure_spec(resource) is infrastructure
    assert planned_resource_authored_name(resource) == "web"
    assert planned_resource_name(resource) == "web"


def test_node_source_preserves_string_shape() -> None:
    resource = PlannedResource(
        address="provision.node.web",
        domain=RuntimeDomain.PROVISIONING,
        resource_type="node",
        payload={"spec": {"node": {"source": "registry.example/web:1"}}},
    )

    assert planned_node_source(resource) == "registry.example/web:1"


def test_missing_optional_node_fields_are_absent_and_name_falls_back_to_address() -> None:
    resource = PlannedResource(
        address="provision.node.web",
        domain=RuntimeDomain.PROVISIONING,
        resource_type="node",
        payload={},
    )

    assert planned_node_spec(resource) is None
    assert planned_node_source(resource) is None
    assert planned_node_resources(resource) is None
    assert planned_infrastructure_spec(resource) is None
    assert planned_resource_authored_name(resource) is None
    assert planned_resource_name(resource) == resource.address


def test_non_mapping_payload_is_safely_absent() -> None:
    resource = PlannedResource(
        address="provision.node.web",
        domain=RuntimeDomain.PROVISIONING,
        resource_type="node",
        payload="not-a-mapping",  # type: ignore[arg-type]
    )

    assert planned_resource_payload(resource) is None
    assert planned_node_spec(resource) is None
    assert planned_node_source(resource) is None
    assert planned_node_resources(resource) is None
    assert planned_infrastructure_spec(resource) is None
    assert planned_resource_authored_name(resource) is None
    assert planned_resource_name(resource) == resource.address


def test_node_accessors_reject_unsupported_provisioning_resource_type() -> None:
    resource = PlannedResource(
        address="provision.feature-binding.monitoring",
        domain=RuntimeDomain.PROVISIONING,
        resource_type="feature-binding",
        payload={
            "spec": {
                "node": {"source": "should-not-be-read", "resources": {"cpu": 8}},
                "infrastructure": {"networks": ["should-not-be-read"]},
            }
        },
    )

    assert planned_node_spec(resource) is None
    assert planned_node_source(resource) is None
    assert planned_node_resources(resource) is None
    assert planned_infrastructure_spec(resource) is None


def test_provisioning_accessors_reject_wrong_runtime_domain() -> None:
    resource = PlannedResource(
        address="orchestration.script.setup",
        domain=RuntimeDomain.ORCHESTRATION,
        resource_type="script",
        payload={
            "spec": {
                "node": {"source": "should-not-be-read", "resources": {"cpu": 8}},
                "infrastructure": {"networks": ["should-not-be-read"]},
            }
        },
    )

    assert planned_node_spec(resource) is None
    assert planned_node_source(resource) is None
    assert planned_node_resources(resource) is None
    assert planned_infrastructure_spec(resource) is None
