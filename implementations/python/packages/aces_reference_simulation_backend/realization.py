"""Pure provisioning-plan interpretation for the reference simulation backend."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol, TypeVar

from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.planning import PlannedResource, ProvisioningPlan, RuntimeDomain

from .engine import SimulationNetworkSpec, SimulationNodeSpec, SimulationPlacementSpec

_DOMAIN = "runtime"

NODE_RESOURCE_TYPE = "node"
NETWORK_RESOURCE_TYPE = "network"
PLACEMENT_RESOURCE_TYPES = frozenset({"feature-binding", "content-placement", "account-placement"})
SUPPORTED_RESOURCE_TYPES = frozenset({NODE_RESOURCE_TYPE, NETWORK_RESOURCE_TYPE}) | PLACEMENT_RESOURCE_TYPES


class _Addressed(Protocol):
    address: str


_TAddressed = TypeVar("_TAddressed", bound=_Addressed)


@dataclass(frozen=True)
class SimulationRealization:
    """Driver-agnostic interpretation of a provisioning plan."""

    networks: tuple[SimulationNetworkSpec, ...] = ()
    nodes: tuple[SimulationNodeSpec, ...] = ()
    placements: tuple[SimulationPlacementSpec, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class _SimulationPlanInputs:
    network_specs: tuple[SimulationNetworkSpec, ...]
    node_payloads: tuple[tuple[PlannedResource, Mapping[str, object]], ...]
    placement_specs: tuple[SimulationPlacementSpec, ...]
    diagnostics: tuple[Diagnostic, ...]


def interpret_simulation_plan(plan: ProvisioningPlan) -> SimulationRealization:
    """Interpret an ACES provisioning plan as portable simulation specs."""

    collected = _collect_simulation_inputs(plan.resources.values())
    network_lookup = _network_address_lookup(collected.network_specs)
    node_specs = tuple(_node_spec(resource, payload, network_lookup) for resource, payload in collected.node_payloads)

    return SimulationRealization(
        networks=_sort_by_address(collected.network_specs),
        nodes=_sort_by_address(node_specs),
        placements=_sort_by_address(collected.placement_specs),
        diagnostics=collected.diagnostics,
    )


def _collect_simulation_inputs(resources: Iterable[PlannedResource]) -> _SimulationPlanInputs:
    diagnostics: list[Diagnostic] = []
    networks: list[SimulationNetworkSpec] = []
    nodes: list[tuple[PlannedResource, Mapping[str, object]]] = []
    placements: list[SimulationPlacementSpec] = []

    for resource in resources:
        if resource.domain != RuntimeDomain.PROVISIONING:
            continue
        payload = _mapping_payload(resource, diagnostics)
        if payload is None:
            continue
        if resource.resource_type == NETWORK_RESOURCE_TYPE:
            networks.append(_network_spec(resource, payload))
            continue
        if resource.resource_type == NODE_RESOURCE_TYPE:
            nodes.append((resource, payload))
            continue
        placements.append(_placement_spec(resource, payload))

    return _SimulationPlanInputs(
        network_specs=tuple(networks),
        node_payloads=tuple(nodes),
        placement_specs=tuple(placements),
        diagnostics=tuple(diagnostics),
    )


def _mapping_payload(resource: PlannedResource, diagnostics: list[Diagnostic]) -> Mapping[str, object] | None:
    if resource.resource_type not in SUPPORTED_RESOURCE_TYPES:
        diagnostics.append(_unsupported_resource(resource))
        return None
    if isinstance(resource.payload, Mapping):
        return resource.payload
    diagnostics.append(_invalid_payload(resource))
    return None


def _network_address_lookup(networks: Iterable[SimulationNetworkSpec]) -> dict[str, str]:
    return {key: spec.address for spec in networks for key in _network_aliases(spec)}


def _network_aliases(spec: SimulationNetworkSpec) -> tuple[str, ...]:
    return tuple(alias for alias in (spec.address, spec.name, spec.address.rsplit(".", 1)[-1]) if alias)


def _sort_by_address(items: Iterable[_TAddressed]) -> tuple[_TAddressed, ...]:
    return tuple(sorted(items, key=lambda item: item.address))


def _resource_name(resource: PlannedResource, payload: Mapping[str, object]) -> str:
    for key in ("name", "node_name"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return resource.address.rsplit(".", 1)[-1]


def _infrastructure_spec(payload: Mapping[str, object]) -> Mapping[str, object]:
    spec = payload.get("spec")
    if not isinstance(spec, Mapping):
        return {}
    infrastructure = spec.get("infrastructure")
    return infrastructure if isinstance(infrastructure, Mapping) else {}


def _network_spec(resource: PlannedResource, payload: Mapping[str, object]) -> SimulationNetworkSpec:
    return SimulationNetworkSpec(
        address=resource.address,
        name=_resource_name(resource, payload),
        labels=_network_labels(_infrastructure_spec(payload)),
    )


def _network_labels(infrastructure: Mapping[str, object]) -> dict[str, str]:
    properties = infrastructure.get("properties")
    if isinstance(properties, Mapping) and properties.get("internal") is True:
        return {"internal": "true"}
    return {}


def _node_spec(
    resource: PlannedResource,
    payload: Mapping[str, object],
    network_lookup: dict[str, str],
) -> SimulationNodeSpec:
    os_family = _string_or_default(payload.get("os_family") or payload.get("os"), "other")
    node_type = _string_or_default(payload.get("node_type") or payload.get("type"), "vm")
    return SimulationNodeSpec(
        address=resource.address,
        name=_resource_name(resource, payload),
        node_type=node_type,
        os_family=os_family,
        model_ref=_model_ref(payload, os_family),
        networks=_resolved_networks(payload, network_lookup),
    )


def _resolved_networks(payload: Mapping[str, object], network_lookup: dict[str, str]) -> tuple[str, ...]:
    return tuple(network_lookup.get(ref, ref) for ref in _network_references(payload))


def _network_references(payload: Mapping[str, object]) -> tuple[str, ...]:
    networks = _infrastructure_spec(payload).get("networks")
    if not isinstance(networks, (list, tuple)):
        return ()
    return tuple(ref for ref in networks if isinstance(ref, str) and ref)


def _placement_spec(resource: PlannedResource, payload: Mapping[str, object]) -> SimulationPlacementSpec:
    return SimulationPlacementSpec(
        address=resource.address,
        resource_type=resource.resource_type,
        name=_resource_name(resource, payload),
        target_address=_target_address(payload),
    )


def _target_address(payload: Mapping[str, object]) -> str | None:
    for key in ("target", "target_address", "node"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


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
