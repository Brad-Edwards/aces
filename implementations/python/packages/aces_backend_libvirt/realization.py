"""Pure interpretation of provisioning plans for the libvirt backend."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.planning import PlannedResource, ProvisioningPlan, RuntimeDomain

from .driver import DomainSpec, NetworkSpec, ServiceSpec

_DOMAIN = "runtime"
NODE_RESOURCE_TYPE = "node"
NETWORK_RESOURCE_TYPE = "network"
SUPPORTED_RESOURCE_TYPES = frozenset({NODE_RESOURCE_TYPE, NETWORK_RESOURCE_TYPE})


@dataclass(frozen=True)
class Realization:
    """Driver-neutral libvirt realization intent."""

    networks: tuple[NetworkSpec, ...] = ()
    domains: tuple[DomainSpec, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()


def interpret_provisioning_plan(plan: ProvisioningPlan) -> Realization:
    """Interpret an ACES provisioning plan as portable libvirt intent."""

    diagnostics: list[Diagnostic] = []
    network_resources: list[tuple[PlannedResource, Mapping[str, object]]] = []
    node_resources: list[tuple[PlannedResource, Mapping[str, object]]] = []

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
        else:
            node_resources.append((resource, payload))

    networks = [_network_spec(resource, payload) for resource, payload in network_resources]
    network_lookup = _network_address_lookup(networks)
    domains = [_domain_spec(resource, payload, network_lookup) for resource, payload in node_resources]

    return Realization(
        networks=tuple(sorted(networks, key=lambda spec: spec.address)),
        domains=tuple(sorted(domains, key=lambda spec: spec.address)),
        diagnostics=tuple(diagnostics),
    )


def _network_address_lookup(networks: list[NetworkSpec]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for spec in networks:
        for key in (spec.address, spec.name, spec.address.rsplit(".", 1)[-1]):
            if key:
                lookup[key] = spec.address
    return lookup


def _network_spec(resource: PlannedResource, payload: Mapping[str, object]) -> NetworkSpec:
    infrastructure = _infrastructure_spec(payload)
    properties = infrastructure.get("properties")
    labels: dict[str, str] = {}
    if isinstance(properties, Mapping) and properties.get("internal") is True:
        labels["internal"] = "true"
    cidr = properties.get("cidr") if isinstance(properties, Mapping) else None
    gateway = properties.get("gateway") if isinstance(properties, Mapping) else None
    return NetworkSpec(
        address=resource.address,
        name=_resource_name(resource, payload),
        cidr=cidr if isinstance(cidr, str) and cidr else None,
        gateway=gateway if isinstance(gateway, str) and gateway else None,
        labels=labels,
    )


def _domain_spec(
    resource: PlannedResource,
    payload: Mapping[str, object],
    network_lookup: dict[str, str],
) -> DomainSpec:
    infrastructure = _infrastructure_spec(payload)
    references = _network_refs(infrastructure)
    network_addresses = tuple(network_lookup.get(ref, ref) for ref in references)
    resources = _node_resources(payload)
    return DomainSpec(
        address=resource.address,
        name=_resource_name(resource, payload),
        image_ref=_image_ref(payload),
        memory_mib=_memory_mib(resources.get("ram")),
        vcpus=_vcpus(resources.get("cpu")),
        networks=network_addresses,
        services=_services(payload),
    )


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


def _network_refs(infrastructure: Mapping[str, object]) -> tuple[str, ...]:
    for field_name in ("networks", "links"):
        raw = infrastructure.get(field_name)
        if isinstance(raw, (list, tuple)):
            return tuple(ref for ref in raw if isinstance(ref, str) and ref)
    return ()


def _node_resources(payload: Mapping[str, object]) -> Mapping[str, object]:
    spec = payload.get("spec")
    node = spec.get("node") if isinstance(spec, Mapping) else None
    resources = node.get("resources") if isinstance(node, Mapping) else None
    return resources if isinstance(resources, Mapping) else {}


def _services(payload: Mapping[str, object]) -> tuple[ServiceSpec, ...]:
    spec = payload.get("spec")
    node = spec.get("node") if isinstance(spec, Mapping) else None
    raw_services = node.get("services") if isinstance(node, Mapping) else None
    if not isinstance(raw_services, list | tuple):
        return ()
    services: list[ServiceSpec] = []
    for item in raw_services:
        service = _service(item)
        if service is not None:
            services.append(service)
    return tuple(sorted(services, key=lambda service: (service.protocol, service.port, service.name)))


def _service(raw: object) -> ServiceSpec | None:
    service: ServiceSpec | None = None
    if isinstance(raw, Mapping):
        name = raw.get("name")
        port = raw.get("port")
        protocol = raw.get("protocol", "tcp")
        if isinstance(name, str) and name and isinstance(port, int | float) and int(port) > 0:
            normalized_protocol = protocol.lower() if isinstance(protocol, str) and protocol else "tcp"
            if normalized_protocol not in {"tcp", "udp"}:
                normalized_protocol = "tcp"
            service = ServiceSpec(name=name, port=int(port), protocol=normalized_protocol)
    return service


def _memory_mib(raw: object) -> int:
    if isinstance(raw, int | float) and raw > 0:
        # Planner payloads carry RAM in bytes. Tiny synthetic values are
        # treated as MiB to keep hand-authored unit plans ergonomic.
        if raw >= 1024 * 1024:
            return max(128, int((raw + 1024 * 1024 - 1) // (1024 * 1024)))
        return max(128, int(raw))
    return 512


def _vcpus(raw: object) -> int:
    if isinstance(raw, int | float) and raw > 0:
        return max(1, int(raw))
    return 1


def _image_ref(payload: Mapping[str, object]) -> str | None:
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


def _unsupported_resource(resource: PlannedResource) -> Diagnostic:
    return Diagnostic(
        code="libvirt-backend.realization.unsupported-resource",
        domain=_DOMAIN,
        address=resource.address,
        message=(
            "Libvirt backend does not realize provisioning resource type "
            f"'{resource.resource_type}' for '{resource.address}'."
        ),
        severity=Severity.ERROR,
    )


def _invalid_payload(resource: PlannedResource) -> Diagnostic:
    return Diagnostic(
        code="libvirt-backend.realization.invalid-payload",
        domain=_DOMAIN,
        address=resource.address,
        message=(
            f"Libvirt backend expected provisioning resource '{resource.address}' "
            f"of type '{resource.resource_type}' to carry a mapping payload."
        ),
        severity=Severity.ERROR,
    )
