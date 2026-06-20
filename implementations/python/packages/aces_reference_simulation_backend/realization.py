"""Pure provisioning-plan interpretation for the reference simulation backend."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.planning import PlannedResource, ProvisioningPlan, RuntimeDomain

from .engine import SimulationNetworkSpec, SimulationNodeSpec, SimulationPlacementSpec

_DOMAIN = "runtime"

NODE_RESOURCE_TYPE = "node"
NETWORK_RESOURCE_TYPE = "network"
PLACEMENT_RESOURCE_TYPES = frozenset({"feature-binding", "content-placement", "account-placement"})
SUPPORTED_RESOURCE_TYPES = frozenset({NODE_RESOURCE_TYPE, NETWORK_RESOURCE_TYPE}) | PLACEMENT_RESOURCE_TYPES


@dataclass(frozen=True)
class SimulationRealization:
    """Driver-agnostic interpretation of a provisioning plan."""

    networks: tuple[SimulationNetworkSpec, ...] = ()
    nodes: tuple[SimulationNodeSpec, ...] = ()
    placements: tuple[SimulationPlacementSpec, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()


def interpret_simulation_plan(plan: ProvisioningPlan) -> SimulationRealization:
    """Interpret an ACES provisioning plan as portable simulation specs."""

    diagnostics: list[Diagnostic] = []
    network_resources: list[tuple[PlannedResource, Mapping[str, object]]] = []
    node_resources: list[tuple[PlannedResource, Mapping[str, object]]] = []
    placement_resources: list[tuple[PlannedResource, Mapping[str, object]]] = []

    for resource in plan.resources.values():
        if resource.domain != RuntimeDomain.PROVISIONING:
            continue
        if resource.resource_type not in SUPPORTED_RESOURCE_TYPES:
            diagnostics.append(_unsupported_resource(resource))
            continue
        payload = resource.payload
        if not isinstance(payload, Mapping):
            diagnostics.append(_invalid_payload(resource))
            continue
        if resource.resource_type == NETWORK_RESOURCE_TYPE:
            network_resources.append((resource, payload))
        elif resource.resource_type == NODE_RESOURCE_TYPE:
            node_resources.append((resource, payload))
        else:
            placement_resources.append((resource, payload))

    networks = [_network_spec(resource, payload) for resource, payload in network_resources]
    network_lookup = _network_address_lookup(networks)
    nodes = [_node_spec(resource, payload, network_lookup) for resource, payload in node_resources]
    placements = [_placement_spec(resource, payload) for resource, payload in placement_resources]

    return SimulationRealization(
        networks=tuple(sorted(networks, key=lambda spec: spec.address)),
        nodes=tuple(sorted(nodes, key=lambda spec: spec.address)),
        placements=tuple(sorted(placements, key=lambda spec: spec.address)),
        diagnostics=tuple(diagnostics),
    )


def _network_address_lookup(networks: list[SimulationNetworkSpec]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for spec in networks:
        for key in (spec.address, spec.name, spec.address.rsplit(".", 1)[-1]):
            if key:
                lookup[key] = spec.address
    return lookup


def _resource_name(resource: PlannedResource, payload: Mapping[str, object]) -> str:
    name = payload.get("name") or payload.get("node_name")
    if isinstance(name, str) and name:
        return name
    return resource.address.rsplit(".", 1)[-1]


def _infrastructure_spec(payload: Mapping[str, object]) -> Mapping[str, object]:
    spec = payload.get("spec")
    if not isinstance(spec, Mapping):
        return {}
    infrastructure = spec.get("infrastructure")
    return infrastructure if isinstance(infrastructure, Mapping) else {}


def _network_spec(resource: PlannedResource, payload: Mapping[str, object]) -> SimulationNetworkSpec:
    infrastructure = _infrastructure_spec(payload)
    properties = infrastructure.get("properties")
    labels: dict[str, str] = {}
    if isinstance(properties, Mapping) and properties.get("internal") is True:
        labels["internal"] = "true"
    return SimulationNetworkSpec(address=resource.address, name=_resource_name(resource, payload), labels=labels)


def _node_spec(
    resource: PlannedResource,
    payload: Mapping[str, object],
    network_lookup: dict[str, str],
) -> SimulationNodeSpec:
    infrastructure = _infrastructure_spec(payload)
    networks = infrastructure.get("networks")
    references: tuple[str, ...] = ()
    if isinstance(networks, (list, tuple)):
        references = tuple(str(ref) for ref in networks if isinstance(ref, str) and ref)
    network_addresses = tuple(network_lookup.get(ref, ref) for ref in references)
    os_family = _string_or_default(payload.get("os_family") or payload.get("os"), "other")
    node_type = _string_or_default(payload.get("node_type") or payload.get("type"), "vm")
    return SimulationNodeSpec(
        address=resource.address,
        name=_resource_name(resource, payload),
        node_type=node_type,
        os_family=os_family,
        model_ref=_model_ref(payload, os_family),
        networks=network_addresses,
    )


def _placement_spec(resource: PlannedResource, payload: Mapping[str, object]) -> SimulationPlacementSpec:
    target = payload.get("target") or payload.get("target_address") or payload.get("node")
    target_address = target if isinstance(target, str) and target else None
    return SimulationPlacementSpec(
        address=resource.address,
        resource_type=resource.resource_type,
        name=_resource_name(resource, payload),
        target_address=target_address,
    )


def _model_ref(payload: Mapping[str, object], os_family: str) -> str:
    source = _node_source(payload)
    if source:
        return source
    return f"aces-simulation/{os_family}"


def _node_source(payload: Mapping[str, object]) -> str | None:
    spec = payload.get("spec")
    node = spec.get("node") if isinstance(spec, Mapping) else None
    source = node.get("source") if isinstance(node, Mapping) else None
    if isinstance(source, str) and source:
        return source
    if isinstance(source, Mapping):
        name = source.get("name")
        if isinstance(name, str) and name:
            return name
    return None


def _string_or_default(value: object, default: str) -> str:
    return value if isinstance(value, str) and value else default


def _unsupported_resource(resource: PlannedResource) -> Diagnostic:
    return Diagnostic(
        code="reference-simulation.realization.unsupported-resource",
        domain=_DOMAIN,
        address=resource.address,
        message=(
            f"Reference simulation backend does not realize provisioning resource type "
            f"'{resource.resource_type}' for '{resource.address}'."
        ),
        severity=Severity.ERROR,
    )


def _invalid_payload(resource: PlannedResource) -> Diagnostic:
    return Diagnostic(
        code="reference-simulation.realization.invalid-payload",
        domain=_DOMAIN,
        address=resource.address,
        message=(
            f"Reference simulation backend expected provisioning resource '{resource.address}' "
            f"of type '{resource.resource_type}' to carry a mapping payload."
        ),
        severity=Severity.ERROR,
    )
