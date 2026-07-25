"""Issue #849: typed node-to-node network namespace sharing."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from raes.nodes import RuntimeNetworkNamespace

from aces.backends.stubs import create_stub_manifest
from aces.core.runtime.compiler import compile_runtime_model
from aces.core.runtime.models import RuntimeDomain, RuntimeSnapshot, SnapshotEntry
from aces.core.runtime.planner import plan
from aces.core.sdl import (
    SDLInstantiationError,
    SDLValidationError,
    instantiate_scenario,
    parse_sdl,
    parse_sdl_file,
)


def _scenario(yaml_text: str):
    return parse_sdl(textwrap.dedent(yaml_text))


def _sharing_scenario(*, target: str = "owner", sharing_infra: str = "") -> str:
    return f"""
name: shared-network-namespace
nodes:
  owner:
    type: vm
    os: linux
  capture:
    type: vm
    os: linux
    runtime:
      container:
        namespaces:
          network:
            target_node_ref: {target}
          pid: private
{sharing_infra}
"""


def _snapshot_from_execution_plan(execution_plan) -> RuntimeSnapshot:
    entries = {
        operation.address: SnapshotEntry(
            address=operation.address,
            domain=RuntimeDomain.PROVISIONING,
            resource_type=operation.resource_type,
            payload=operation.payload,
            ordering_dependencies=operation.ordering_dependencies,
            refresh_dependencies=operation.refresh_dependencies,
            status="snapshot",
        )
        for operation in execution_plan.provisioning.operations
        if operation.action.value != "delete"
    }
    return RuntimeSnapshot(entries=entries)


def test_network_namespace_target_is_typed_and_independent_from_pid() -> None:
    scenario = _scenario(_sharing_scenario())

    namespaces = scenario.nodes["capture"].runtime.container.namespaces
    assert namespaces.network.target_node_ref == "owner"
    assert isinstance(namespaces.network, RuntimeNetworkNamespace)
    assert namespaces.pid == "private"


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ("missing", "references undefined node 'missing'"),
        ("capture", "cannot share its own network namespace"),
    ],
)
def test_network_namespace_target_must_resolve_to_another_node(target: str, message: str) -> None:
    yaml_text = _sharing_scenario(target=target)
    with pytest.raises(SDLValidationError, match=message):
        _scenario(yaml_text)


def test_network_namespace_target_must_be_a_vm_node() -> None:
    with pytest.raises(SDLValidationError, match="must reference a VM node"):
        _scenario(
            """
            name: invalid-network-namespace-owner-type
            nodes:
              owner: {type: switch}
              capture:
                type: vm
                os: linux
                runtime:
                  container:
                    namespaces:
                      network: {target_node_ref: owner}
            """
        )


def test_network_namespace_target_cannot_chain() -> None:
    with pytest.raises(SDLValidationError, match="must be a canonical namespace owner"):
        _scenario(
            """
            name: chained-network-namespace
            nodes:
              owner: {type: vm, os: linux}
              middle:
                type: vm
                os: linux
                runtime:
                  container:
                    namespaces:
                      network: {target_node_ref: owner}
              capture:
                type: vm
                os: linux
                runtime:
                  container:
                    namespaces:
                      network: {target_node_ref: middle}
            """
        )


@pytest.mark.parametrize("replicated_node", ["owner", "capture"])
def test_network_namespace_nodes_must_be_singletons(replicated_node: str) -> None:
    yaml_text = _sharing_scenario(
        sharing_infra=f"""
infrastructure:
  {replicated_node}:
    count: 2
"""
    )
    with pytest.raises(SDLValidationError, match="requires singleton source and target nodes"):
        _scenario(yaml_text)


@pytest.mark.parametrize(
    "sharing_infra",
    [
        """
infrastructure:
  lan:
    count: 1
  capture:
    links: [lan]
""",
        """
infrastructure:
  capture:
    properties: [{lan: 10.0.0.2}]
""",
        """
infrastructure:
  capture:
    acls: [{from_net: lan, to_net: lan, action: allow}]
""",
    ],
)
def test_network_namespace_sharer_rejects_independent_infrastructure(sharing_infra: str) -> None:
    yaml_text = _sharing_scenario(sharing_infra=sharing_infra)
    with pytest.raises(SDLValidationError, match="cannot declare independent infrastructure network state"):
        _scenario(yaml_text)


@pytest.mark.parametrize(
    "network_state",
    [
        "endpoints: [{network: lan}]",
        "published_ports: [{container_port: 443, host_port: 8443}]",
    ],
)
def test_network_namespace_sharer_rejects_independent_runtime_network_state(network_state: str) -> None:
    yaml_text = _sharing_scenario().replace(
        "          pid: private",
        f"""          pid: private
      network:
        {network_state}""",
    )
    yaml_text += """
infrastructure:
  lan:
    properties: {cidr: 10.0.0.0/24, gateway: 10.0.0.1}
"""

    with pytest.raises(SDLValidationError, match="cannot declare independent runtime network state"):
        _scenario(yaml_text)


def test_instantiation_revalidates_network_namespace_target() -> None:
    authored = parse_sdl(
        textwrap.dedent(
            """
            name: parameterized-network-namespace
            variables:
              target:
                type: string
                required: true
            nodes:
              owner: {type: vm, os: linux}
              capture:
                type: vm
                os: linux
                runtime:
                  container:
                    namespaces:
                      network: {target_node_ref: "${target}"}
            """
        ),
    )

    assert instantiate_scenario(authored, {"target": "owner"}).nodes["capture"].runtime is not None
    with pytest.raises(SDLInstantiationError, match="references undefined node 'missing'"):
        instantiate_scenario(authored, {"target": "missing"})


def test_compiler_resolves_network_namespace_owner_and_dependencies() -> None:
    model = compile_runtime_model(_scenario(_sharing_scenario()))

    capture = model.node_deployments["provision.node.capture"]
    assert capture.network_namespace_target == "provision.node.owner"
    assert "provision.node.owner" in capture.ordering_dependencies
    assert "provision.node.owner" in capture.refresh_dependencies


def test_planner_orders_and_refreshes_network_namespace_dependents() -> None:
    manifest = create_stub_manifest()
    initial = plan(
        compile_runtime_model(_scenario(_sharing_scenario())),
        manifest,
        RuntimeSnapshot(),
    )
    create_order = [operation.address for operation in initial.provisioning.operations]
    assert create_order.index("provision.node.owner") < create_order.index("provision.node.capture")

    snapshot = _snapshot_from_execution_plan(initial)
    changed_owner = _sharing_scenario().replace(
        "    os: linux\n  capture:", "    os: linux\n    description: changed\n  capture:"
    )
    refreshed = plan(compile_runtime_model(_scenario(changed_owner)), manifest, snapshot)
    actions = {operation.address: operation.action.value for operation in refreshed.provisioning.operations}
    assert actions["provision.node.owner"] == "update"
    assert actions["provision.node.capture"] == "update"

    deleted = plan(compile_runtime_model(_scenario("name: empty")), manifest, snapshot)
    delete_order = [
        operation.address for operation in deleted.provisioning.operations if operation.action.value == "delete"
    ]
    assert delete_order.index("provision.node.capture") < delete_order.index("provision.node.owner")


def test_composition_rewrites_network_namespace_target(tmp_path: Path) -> None:
    imported = tmp_path / "shared.yaml"
    imported.write_text(
        textwrap.dedent(
            """
            name: shared
            version: 1.0.0
            module:
              id: aces/shared
              version: 1.0.0
              exports:
                nodes: [owner, capture]
            nodes:
              owner: {type: vm, os: linux}
              capture:
                type: vm
                os: linux
                runtime:
                  container:
                    namespaces:
                      network: {target_node_ref: nodes.owner}
            """
        ),
        encoding="utf-8",
    )
    root = tmp_path / "root.yaml"
    root.write_text(
        """name: root
imports:
  - path: shared.yaml
    namespace: shared
    version: 1.0.0
""",
        encoding="utf-8",
    )

    scenario = parse_sdl_file(root)

    target = scenario.nodes["shared.capture"].runtime.container.namespaces.network.target_node_ref
    assert target == "nodes.shared.owner"
