"""Network/node spec construction and payload projection for plan realization."""

from __future__ import annotations

from collections.abc import Mapping

from raes_contracts.planning import PlannedResource

from ..driver import DomainSpec, NetworkAcl, NetworkSpec, ServiceSpec
from ._cloud_init import _CloudInitAccumulator
from ._common import _resource_name


def _network_address_lookup(networks: list[NetworkSpec]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for spec in networks:
        for key in (spec.address, spec.name):
            if key:
                lookup[key] = spec.address
    return lookup


def _network_spec(resource: PlannedResource, payload: Mapping[str, object]) -> NetworkSpec:
    infrastructure = _infrastructure_spec(payload)
    properties = infrastructure.get("properties")
    labels: dict[str, str] = {}
    if isinstance(properties, Mapping) and isinstance(properties.get("internal"), bool):
        labels["internal"] = "true" if properties["internal"] else "false"
    cidr = properties.get("cidr") if isinstance(properties, Mapping) else None
    gateway = properties.get("gateway") if isinstance(properties, Mapping) else None
    return NetworkSpec(
        address=resource.address,
        name=_resource_name(resource, payload),
        cidr=cidr if isinstance(cidr, str) and cidr else None,
        gateway=gateway if isinstance(gateway, str) and gateway else None,
        labels=labels,
    )


def _node_address_lookup(
    node_resources: list[tuple[PlannedResource, Mapping[str, object]]],
) -> dict[str, str]:
    """Map every handle a placement might reference a node by to its address."""

    lookup: dict[str, str] = {}
    for resource, payload in node_resources:
        name = _resource_name(resource, payload)
        for key in (resource.address, name):
            if key:
                lookup[key] = resource.address
    return lookup


def _domain_spec(
    resource: PlannedResource,
    payload: Mapping[str, object],
    network_lookup: dict[str, str],
    cloud_init: dict[str, _CloudInitAccumulator],
    acls: dict[str, tuple[NetworkAcl, ...]],
) -> DomainSpec:
    infrastructure = _infrastructure_spec(payload)
    references = _network_refs(infrastructure)
    network_addresses = tuple(network_lookup.get(ref, ref) for ref in references)
    resources = _node_resources(payload)
    name = _resource_name(resource, payload)
    accumulator = cloud_init.get(resource.address, _CloudInitAccumulator())
    return DomainSpec(
        address=resource.address,
        name=name,
        image_ref=_image_ref(payload),
        memory_mib=_memory_mib(resources.get("ram")),
        vcpus=_vcpus(resources.get("cpu")),
        networks=network_addresses,
        services=_services(payload),
        cloud_init=accumulator.build(hostname=name),
        network_acls=acls.get(resource.address, ()),
    )


def _network_cidr_lookup(networks: list[NetworkSpec]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for spec in networks:
        if not spec.cidr:
            continue
        for key in (spec.address, spec.name):
            if key:
                lookup[key] = spec.cidr
    return lookup


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
