"""Pure interpretation of provisioning plans for the libvirt backend.

Maps an RAES :class:`ProvisioningPlan` into a driver-neutral :class:`Realization`
of portable network/domain specs. Node resources become libvirt domains; network
resources become libvirt networks; and placement resources are bound to their
target domains. Content, account, and feature placements contribute to cloud-init:

- ``account-placement`` → cloud-init ``users`` (groups, shell, home, disabled,
  auth_method) plus ``/etc/aliases.d`` (mail) and ``/etc/raes/spn`` (spn) files;
- ``content-placement`` → cloud-init ``write_files`` (file/text) or ``runcmd``
  and a descriptor file (dataset/directory/source-backed);
- ``feature-binding`` → cloud-init ``packages``/``runcmd`` (service) or a
  descriptor file (artifact/configuration).

The module is pure (no driver, no IO): the provisioner validates a plan without
realizing it, and the driver renders seed media from the same data.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from raes_backend_protocols.capabilities import ProvisionerCapabilities
from raes_backend_protocols.naming import provider_resource_name
from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.planning import (
    PlannedResource,
    PlanOperation,
    ProvisioningPlan,
    RuntimeDomain,
    planned_infrastructure_spec,
    planned_node_resources,
    planned_node_source,
    planned_node_spec,
    planned_resource_authored_name,
    planned_resource_payload,
)

from ._payload import (
    ACCOUNT_PLACEMENT_RESOURCE_TYPE,
    CONTENT_PLACEMENT_RESOURCE_TYPE,
    DOMAIN_CONTROLLER_PLACEMENT_RESOURCE_TYPE,
    NETWORK_RESOURCE_TYPE,
    NODE_RESOURCE_TYPE,
    SUPPORTED_RESOURCE_TYPES,
    _os_family,
    _spec,
    _str,
)
from .acls import realize_node_acls
from .capability_envelope import capability_envelope_diagnostics
from .cloudinit import CloudInitFile, CloudInitSpec, CloudInitUser, safe_path_component
from .dialects import GuestDialect, GuestEmit, dialect_for
from .driver import DomainSpec, NetworkAcl, NetworkSpec, ServiceSpec
from .manifest import LIBVIRT_PROVISIONER_CAPABILITIES

_DOMAIN = "runtime"
_NETWORK_NAMESPACE_UNSUPPORTED = "libvirt-backend.network-namespace-unsupported"


@dataclass(frozen=True)
class Realization:
    """Driver-neutral libvirt realization intent."""

    networks: tuple[NetworkSpec, ...] = ()
    domains: tuple[DomainSpec, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    # placement address -> the node (domain) address its cloud-init contributes to.
    # Lets the provisioner realize a domain when a placement targeting it changes,
    # even if the node itself is UNCHANGED.
    placement_targets: dict[str, str] = field(default_factory=dict)


@dataclass
class _CloudInitAccumulator:
    """Mutable per-domain cloud-init contributions, aggregated across placements."""

    users: list[CloudInitUser] = field(default_factory=list)
    write_files: list[CloudInitFile] = field(default_factory=list)
    packages: list[str] = field(default_factory=list)
    runcmd: list[tuple[str, ...]] = field(default_factory=list)

    def build(self, *, hostname: str) -> CloudInitSpec:
        return CloudInitSpec(
            hostname=hostname,
            users=tuple(sorted(self.users, key=lambda user: user.name)),
            write_files=tuple(sorted(self.write_files, key=lambda file: file.path)),
            packages=tuple(dict.fromkeys(self.packages)),
            runcmd=tuple(self.runcmd),
        )


def interpret_provisioning_plan(
    plan: ProvisioningPlan,
    *,
    provisioner_capabilities: ProvisionerCapabilities | None = None,
) -> Realization:
    """Interpret an RAES provisioning plan as portable libvirt intent.

    ``provisioner_capabilities`` is the backend capability envelope every plan
    term is validated against; it defaults to the libvirt manifest's declared
    envelope so a term outside it (an ungoverned/extension node type, OS family,
    content type, or account feature the backend does not realize) yields a
    blocking typed diagnostic instead of a silent or partial realization
    (issue #605).
    """

    capabilities = provisioner_capabilities or LIBVIRT_PROVISIONER_CAPABILITIES
    diagnostics: list[Diagnostic] = list(capability_envelope_diagnostics(plan, capabilities))
    network_resources, node_resources, placement_resources = _collect_supported_resources(plan, diagnostics)

    networks = [_network_spec(resource) for resource, _ in network_resources]
    network_lookup = _network_address_lookup(networks)
    cidr_lookup = _network_cidr_lookup(networks)
    node_lookup = _node_address_lookup(node_resources)
    node_addresses = {resource.address for resource, _ in node_resources}
    node_os = {resource.address: _os_family(payload) for resource, payload in node_resources}
    cloud_init, placement_diagnostics, placement_targets = _aggregate_cloud_init(
        placement_resources, node_lookup, node_os, node_addresses
    )
    diagnostics.extend(placement_diagnostics)
    acls: dict[str, tuple[NetworkAcl, ...]] = {}
    for resource, _payload in node_resources:
        infrastructure = planned_infrastructure_spec(resource) or {}
        node_acls, acl_diagnostics = realize_node_acls(resource, infrastructure.get("acls"), cidr_lookup)
        acls[resource.address] = node_acls
        diagnostics.extend(acl_diagnostics)
    domains = [_domain_spec(resource, network_lookup, cloud_init, acls) for resource, _ in node_resources]

    return Realization(
        networks=tuple(sorted(networks, key=lambda spec: spec.address)),
        domains=tuple(sorted(domains, key=lambda spec: spec.address)),
        diagnostics=tuple(diagnostics),
        placement_targets=placement_targets,
    )


def _collect_supported_resources(
    plan: ProvisioningPlan,
    diagnostics: list[Diagnostic],
) -> tuple[
    list[tuple[PlannedResource, Mapping[str, object]]],
    list[tuple[PlannedResource, Mapping[str, object]]],
    list[tuple[PlannedResource, Mapping[str, object]]],
]:
    network_resources: list[tuple[PlannedResource, Mapping[str, object]]] = []
    node_resources: list[tuple[PlannedResource, Mapping[str, object]]] = []
    placement_resources: list[tuple[PlannedResource, Mapping[str, object]]] = []
    for resource in sorted(plan.resources.values(), key=lambda item: item.address):
        payload = _supported_resource_payload(resource, diagnostics)
        if payload is None:
            continue
        if resource.resource_type == NETWORK_RESOURCE_TYPE:
            network_resources.append((resource, payload))
        elif resource.resource_type == NODE_RESOURCE_TYPE:
            node_resources.append((resource, payload))
            if payload.get("network_namespace_target"):
                diagnostics.append(_network_namespace_unsupported(resource.address))
        else:
            placement_resources.append((resource, payload))
    return network_resources, node_resources, placement_resources


def _supported_resource_payload(
    resource: PlannedResource,
    diagnostics: list[Diagnostic],
) -> Mapping[str, object] | None:
    if resource.domain != RuntimeDomain.PROVISIONING:
        return None
    if resource.resource_type not in SUPPORTED_RESOURCE_TYPES:
        diagnostics.append(_unsupported_resource(resource))
        return None
    payload = planned_resource_payload(resource)
    if payload is None:
        diagnostics.append(_invalid_payload(resource))
    return payload


def _network_address_lookup(networks: list[NetworkSpec]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for spec in networks:
        for key in (spec.address, spec.name):
            if key:
                lookup[key] = spec.address
    return lookup


def _network_spec(resource: PlannedResource) -> NetworkSpec:
    infrastructure = planned_infrastructure_spec(resource) or {}
    raw_properties = infrastructure.get("properties")
    properties = raw_properties if isinstance(raw_properties, Mapping) else {}
    labels: dict[str, str] = {}
    internal = properties.get("internal")
    if isinstance(internal, bool):
        labels["internal"] = str(internal).lower()
    return NetworkSpec(
        address=resource.address,
        name=_resource_name(resource),
        cidr=_optional_str(properties.get("cidr")),
        gateway=_optional_str(properties.get("gateway")),
        labels=labels,
    )


def _optional_str(value: object) -> str | None:
    text = _str(value)
    return text or None


def _node_address_lookup(
    node_resources: list[tuple[PlannedResource, Mapping[str, object]]],
) -> dict[str, str]:
    """Map every handle a placement might reference a node by to its address."""

    lookup: dict[str, str] = {}
    for resource, _payload in node_resources:
        name = _resource_name(resource)
        for key in (resource.address, name):
            if key:
                lookup[key] = resource.address
    return lookup


def _aggregate_cloud_init(
    placement_resources: list[tuple[PlannedResource, Mapping[str, object]]],
    node_lookup: dict[str, str],
    node_os: dict[str, str],
    node_addresses: set[str],
) -> tuple[dict[str, _CloudInitAccumulator], list[Diagnostic], dict[str, str]]:
    """Fold each placement into its target domain's cloud-init contributions.

    Service and mail realization is routed through the target node's OS dialect
    so a Windows or BSD guest gets its native mechanism, not a Linux primitive.

    A placement whose target cannot be resolved to a node in this plan is *not*
    silently dropped: it yields an ERROR diagnostic so apply fails closed rather
    than reporting success while leaving the placement unrealized.

    Also returns a ``placement address -> node address`` map so the provisioner
    can realize a domain whose cloud-init changed because a placement changed.
    """

    accumulators: dict[str, _CloudInitAccumulator] = {}
    diagnostics: list[Diagnostic] = []
    placement_targets: dict[str, str] = {}
    for resource, payload in placement_resources:
        target = _placement_target(payload, node_lookup)
        if target is None or target not in node_addresses:
            diagnostics.append(_unbound_placement(resource, target))
            continue
        placement_targets[resource.address] = target
        dialect = dialect_for(node_os.get(target, ""))
        accumulator = accumulators.setdefault(target, _CloudInitAccumulator())
        if resource.resource_type == ACCOUNT_PLACEMENT_RESOURCE_TYPE:
            _realize_account(accumulator, payload, dialect)
        elif resource.resource_type == CONTENT_PLACEMENT_RESOURCE_TYPE:
            _realize_content(accumulator, resource, payload)
        elif resource.resource_type == DOMAIN_CONTROLLER_PLACEMENT_RESOURCE_TYPE:
            # This generic carrier intentionally emits no provider- or
            # product-specific bootstrap commands.
            pass
        else:
            _realize_feature(accumulator, resource, payload, dialect)
    return accumulators, diagnostics, placement_targets


def _merge_emit(accumulator: _CloudInitAccumulator, emit: GuestEmit) -> None:
    accumulator.packages.extend(emit.packages)
    accumulator.write_files.extend(emit.write_files)
    accumulator.runcmd.extend(emit.runcmd)


def _placement_target(payload: Mapping[str, object], node_lookup: dict[str, str]) -> str | None:
    for key in ("target_address", "node_address", "target_node", "node_name", "node", "target"):
        ref = payload.get(key)
        if isinstance(ref, str) and ref:
            return node_lookup.get(ref, ref)
    return None


def _realize_account(accumulator: _CloudInitAccumulator, payload: Mapping[str, object], dialect: GuestDialect) -> None:
    spec = _spec(payload)
    username = _str(spec.get("username")) or _str(payload.get("account_name")) or _str(payload.get("name"))
    if not username:
        return
    groups = tuple(str(group) for group in spec.get("groups", ()) if isinstance(group, str) and group)
    disabled = _truthy(spec.get("disabled"))
    # A disabled account installs no usable credential; otherwise key material is
    # the only credential we render, so password login is always locked.
    ssh_keys = () if disabled else _ssh_authorized_keys(spec)
    # Fail closed on credentials: we never provision a password, so lock_passwd
    # stays True for every account. Unlocking a password account without a hash
    # would leave a known (often privileged) username reachable with no secret —
    # potentially a blank-password login. Key-based auth still works via the
    # rendered authorized keys, which do not require an unlocked password.
    accumulator.users.append(
        CloudInitUser(
            name=username,
            groups=groups,
            shell=_str(spec.get("shell")),
            home=_str(spec.get("home")),
            lock_passwd=True,
            ssh_authorized_keys=ssh_keys,
        )
    )
    mail = _str(spec.get("mail"))
    if mail:
        _merge_emit(accumulator, dialect.mail_alias(username, mail))
    spn = _str(spec.get("spn"))
    if spn:
        # A real Kerberos SPN needs an AD/realm join; absent a domain, the
        # portable maximum is a host-side principal descriptor the guest can join with.
        safe_user = safe_path_component(username, fallback="user")
        accumulator.write_files.append(
            CloudInitFile(path=f"/etc/raes/spn/{safe_user}", content=f"{spn}\n", permissions="0600")
        )


def _realize_content(
    accumulator: _CloudInitAccumulator,
    resource: PlannedResource,
    payload: Mapping[str, object],
) -> None:
    spec = _spec(payload)
    content_type = _str(spec.get("type"))
    if content_type == "file":
        path = _str(spec.get("path"))
        if not path:
            return
        text = spec.get("text")
        if isinstance(text, str):
            accumulator.write_files.append(CloudInitFile(path=path, content=text))
        else:
            accumulator.runcmd.append(("mkdir", "-p", _dirname(path)))
            accumulator.write_files.append(_content_descriptor(resource, payload, path))
    elif content_type == "directory":
        destination = _str(spec.get("destination"))
        if not destination:
            return
        accumulator.runcmd.append(("mkdir", "-p", destination))
        accumulator.write_files.append(_content_descriptor(resource, payload, destination))
    elif content_type == "dataset":
        accumulator.write_files.append(_content_descriptor(resource, payload, None))


def _realize_feature(
    accumulator: _CloudInitAccumulator,
    resource: PlannedResource,
    payload: Mapping[str, object],
    dialect: GuestDialect,
) -> None:
    spec = _spec(payload)
    template = spec.get("template")
    template = template if isinstance(template, Mapping) else {}
    feature_type = _str(template.get("type"))
    source = template.get("source")
    package = _str(source.get("name")) if isinstance(source, Mapping) else ""
    name = _resource_name(resource)
    if feature_type == "service" and package:
        _merge_emit(accumulator, dialect.enable_feature(package))
    else:
        destination = _str(template.get("destination"))
        if destination:
            accumulator.runcmd.append(("mkdir", "-p", _dirname(destination)))
        accumulator.write_files.append(
            CloudInitFile(
                path=f"/etc/raes/features/{safe_path_component(name, fallback='feature')}.json",
                content=_descriptor_body({"feature": name, "type": feature_type, "destination": destination}),
                permissions="0644",
            )
        )


def _content_descriptor(
    resource: PlannedResource,
    payload: Mapping[str, object],
    location: str | None,
) -> CloudInitFile:
    spec = _spec(payload)
    name = _resource_name(resource)
    descriptor = {
        "content": name,
        "type": _str(spec.get("type")),
        "location": location or "",
    }
    safe_name = safe_path_component(name, fallback="content")
    return CloudInitFile(path=f"/etc/raes/content/{safe_name}.json", content=_descriptor_body(descriptor))


def _descriptor_body(descriptor: Mapping[str, object]) -> str:
    return json.dumps(dict(descriptor), indent=2, sort_keys=True) + "\n"


def _domain_spec(
    resource: PlannedResource,
    network_lookup: dict[str, str],
    cloud_init: dict[str, _CloudInitAccumulator],
    acls: dict[str, tuple[NetworkAcl, ...]],
) -> DomainSpec:
    infrastructure = planned_infrastructure_spec(resource) or {}
    references = _network_refs(infrastructure)
    network_addresses = tuple(network_lookup.get(ref, ref) for ref in references)
    resources = planned_node_resources(resource) or {}
    name = _resource_name(resource)
    accumulator = cloud_init.get(resource.address, _CloudInitAccumulator())
    return DomainSpec(
        address=resource.address,
        name=name,
        image_ref=_planned_node_image_ref(resource),
        memory_mib=_memory_mib(resources.get("ram")),
        vcpus=_vcpus(resources.get("cpu")),
        networks=network_addresses,
        services=_planned_node_services(resource),
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


def _resource_name(
    resource: PlannedResource | PlanOperation,
    payload: Mapping[str, object] | None = None,
) -> str:
    if isinstance(resource, PlannedResource):
        name = planned_resource_authored_name(resource)
    else:
        operation_payload = payload or {}
        raw_name = operation_payload.get("name") or operation_payload.get("node_name")
        name = raw_name if isinstance(raw_name, str) and raw_name else None
    if name is not None:
        return name
    return provider_resource_name(resource.address, prefix="raes")


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


def _planned_node_services(resource: PlannedResource) -> tuple[ServiceSpec, ...]:
    node = planned_node_spec(resource)
    raw_services = node.get("services") if node is not None else None
    if not isinstance(raw_services, list | tuple):
        return ()
    services = [service for item in raw_services if (service := _service(item)) is not None]
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


def _planned_node_image_ref(resource: PlannedResource) -> str | None:
    source = planned_node_source(resource)
    if isinstance(source, str):
        return source
    if isinstance(source, Mapping):
        name = source.get("name")
        if isinstance(name, str) and name:
            return name
    return None


def _ssh_authorized_keys(spec: Mapping[str, object]) -> tuple[str, ...]:
    """Collect any authorized SSH keys the account placement carries."""

    keys: list[str] = []
    for key in ("ssh_authorized_keys", "ssh_keys", "authorized_keys"):
        raw = spec.get(key)
        if isinstance(raw, str) and raw:
            keys.append(raw)
        elif isinstance(raw, list | tuple):
            keys.extend(entry for entry in raw if isinstance(entry, str) and entry)
        if keys:
            break
    return tuple(keys)


def _truthy(value: object) -> bool:
    return value is True


def _dirname(path: str) -> str:
    head = path.rsplit("/", 1)[0]
    return head or "/"


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


def _network_namespace_unsupported(address: str) -> Diagnostic:
    return Diagnostic(
        code=_NETWORK_NAMESPACE_UNSUPPORTED,
        domain=_DOMAIN,
        address=address,
        message=(f"Libvirt backend cannot realize exact container network namespace sharing for '{address}'."),
        severity=Severity.ERROR,
    )


def _unbound_placement(resource: PlannedResource, target: str | None) -> Diagnostic:
    detail = (
        "carries no resolvable target node reference"
        if target is None
        else f"names target node '{target}', which is not present in this plan"
    )
    return Diagnostic(
        code="libvirt-backend.realization.unbound-placement",
        domain=_DOMAIN,
        address=resource.address,
        message=(
            f"Libvirt backend cannot realize placement '{resource.address}' of type "
            f"'{resource.resource_type}': it {detail}."
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
