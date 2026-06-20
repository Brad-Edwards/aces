"""Pure interpretation of provisioning plans for the reference backend.

``interpret_provisioning_plan`` maps an ACES ``ProvisioningPlan`` into a
driver-agnostic :class:`Realization` of portable network/container specs
plus placement records, with diagnostics for unsupported resource types or
malformed payloads. It is pure (no driver, no IO) so the provisioner can
validate a plan without realizing it, and so the driver layer can be
swapped without touching interpretation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.planning import PlannedResource, ProvisioningPlan, RuntimeDomain

from .driver import ContainerSpec, NetworkSpec

_DOMAIN = "runtime"

NODE_RESOURCE_TYPE = "node"
NETWORK_RESOURCE_TYPE = "network"
PLACEMENT_RESOURCE_TYPES = frozenset({"feature-binding", "content-placement", "account-placement"})
SUPPORTED_RESOURCE_TYPES = frozenset({NODE_RESOURCE_TYPE, NETWORK_RESOURCE_TYPE}) | PLACEMENT_RESOURCE_TYPES


@dataclass(frozen=True)
class PlacementRealization:
    """Portable record of a placement resource bound to a target address."""

    address: str
    resource_type: str
    name: str
    target_address: str | None


@dataclass(frozen=True)
class Realization:
    """Driver-agnostic interpretation of a provisioning plan."""

    networks: tuple[NetworkSpec, ...] = ()
    containers: tuple[ContainerSpec, ...] = ()
    placements: tuple[PlacementRealization, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()


def interpret_provisioning_plan(plan: ProvisioningPlan) -> Realization:
    """Interpret an ACES provisioning plan as a portable realization.

    Networks are interpreted before nodes so a container's network references
    (authored by name or address) resolve to the network resource *address* —
    the single portable key the driver maps to a runtime network name. This
    keeps ``ContainerSpec.networks`` address-keyed end to end, consistent with
    the rest of the address-keyed runtime model.
    """

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
    containers = [_container_spec(resource, payload, network_lookup) for resource, payload in node_resources]
    placements = [_placement(resource, payload) for resource, payload in placement_resources]

    return Realization(
        networks=tuple(sorted(networks, key=lambda spec: spec.address)),
        containers=tuple(sorted(containers, key=lambda spec: spec.address)),
        placements=tuple(sorted(placements, key=lambda item: item.address)),
        diagnostics=tuple(diagnostics),
    )


def _network_address_lookup(networks: list[NetworkSpec]) -> dict[str, str]:
    """Map every handle a node might reference a network by to its address."""

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


def _network_spec(resource: PlannedResource, payload: Mapping[str, object]) -> NetworkSpec:
    infrastructure = _infrastructure_spec(payload)
    properties = infrastructure.get("properties")
    labels: dict[str, str] = {}
    if isinstance(properties, Mapping) and properties.get("internal") is True:
        labels["internal"] = "true"
    return NetworkSpec(
        address=resource.address,
        name=_resource_name(resource, payload),
        labels=labels,
    )


def _container_spec(
    resource: PlannedResource,
    payload: Mapping[str, object],
    network_lookup: dict[str, str],
) -> ContainerSpec:
    infrastructure = _infrastructure_spec(payload)
    networks = infrastructure.get("networks")
    references: tuple[str, ...] = ()
    if isinstance(networks, (list, tuple)):
        references = tuple(str(ref) for ref in networks if isinstance(ref, str) and ref)
    # Resolve each authored reference (by name or address) to the network
    # resource address; pass unresolved references through unchanged so the
    # contract stays total even when a node names a network not in this plan.
    network_addresses = tuple(network_lookup.get(ref, ref) for ref in references)
    image_ref = _image_ref(payload)
    return ContainerSpec(
        address=resource.address,
        name=_resource_name(resource, payload),
        image_ref=image_ref,
        networks=network_addresses,
    )


def _image_ref(payload: Mapping[str, object]) -> str:
    spec = payload.get("spec")
    if isinstance(spec, Mapping):
        node = spec.get("node")
        if isinstance(node, Mapping):
            source = node.get("source")
            if isinstance(source, str) and source:
                return source
            if isinstance(source, Mapping):
                name = source.get("name")
                if isinstance(name, str) and name:
                    return name
    os_family = payload.get("os_family")
    if isinstance(os_family, str) and os_family:
        return f"aces-reference/{os_family}"
    return "aces-reference/base"


def _placement(resource: PlannedResource, payload: Mapping[str, object]) -> PlacementRealization:
    target = payload.get("target") or payload.get("target_address") or payload.get("node")
    target_address = target if isinstance(target, str) and target else None
    return PlacementRealization(
        address=resource.address,
        resource_type=resource.resource_type,
        name=_resource_name(resource, payload),
        target_address=target_address,
    )


def _unsupported_resource(resource: PlannedResource) -> Diagnostic:
    return Diagnostic(
        code="reference-backend.realization.unsupported-resource",
        domain=_DOMAIN,
        address=resource.address,
        message=(
            f"Reference backend does not realize provisioning resource type "
            f"'{resource.resource_type}' for '{resource.address}'."
        ),
        severity=Severity.ERROR,
    )


def _invalid_payload(resource: PlannedResource) -> Diagnostic:
    return Diagnostic(
        code="reference-backend.realization.invalid-payload",
        domain=_DOMAIN,
        address=resource.address,
        message=(
            f"Reference backend expected provisioning resource '{resource.address}' "
            f"of type '{resource.resource_type}' to carry a mapping payload."
        ),
        severity=Severity.ERROR,
    )
