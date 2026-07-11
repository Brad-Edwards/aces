"""Fail-closed concern admission for the bounded TechVault appliance mode."""

from __future__ import annotations

import ipaddress
from collections.abc import Mapping

from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.planning import ChangeAction, ProvisioningPlan
from aces_contracts.realization_envelope import (
    BackendRealizationEnvelopeModel,
    ObservationStrength,
    RealizationConcern,
)

from ._payload import (
    ACCOUNT_PLACEMENT_RESOURCE_TYPE,
    CONTENT_PLACEMENT_RESOURCE_TYPE,
    NETWORK_RESOURCE_TYPE,
    NODE_RESOURCE_TYPE,
)
from .driver import DomainSpec, DriverResult, NetworkSpec, RealizationObservation
from .realization import (
    _image_ref,
    _infrastructure_spec,
    _memory_mib,
    _node_resources,
    _resource_name,
    _services,
    _vcpus,
)
from .techvault_matrix import runtime_name

_DOMAIN = "runtime"
_CODE_ACL_UNSUPPORTED = "libvirt-backend.techvault.acl-unsupported"
_CODE_GUEST_PLACEMENT_UNSUPPORTED = "libvirt-backend.techvault.guest-placement-unsupported"
_CODE_IMAGE_UNSUPPORTED = "libvirt-backend.techvault.image-unsupported"
_CODE_METADATA_UNSUPPORTED = "libvirt-backend.techvault.metadata-unsupported"
_CODE_NETWORK_EXACTNESS = "libvirt-backend.techvault.network-exactness-required"
_CODE_NAME_UNSUPPORTED = "libvirt-backend.techvault.name-unsupported"
_CODE_OBSERVATION_MISMATCH = "libvirt-backend.techvault.observation-mismatch"
_CODE_OBSERVATION_MISSING = "libvirt-backend.techvault.observation-missing"
_CODE_RESOURCE_OUT_OF_ENVELOPE = "libvirt-backend.techvault.resource-out-of-envelope"
_CODE_SERVICE_UNSUPPORTED = "libvirt-backend.techvault.service-unsupported"
_CODE_TRANSACTION_UNSUPPORTED = "libvirt-backend.techvault.transaction-unsupported"
_CODE_UPDATE_UNSUPPORTED = "libvirt-backend.techvault.update-unsupported"

_GUEST_PLACEMENTS = frozenset(
    {
        ACCOUNT_PLACEMENT_RESOURCE_TYPE,
        CONTENT_PLACEMENT_RESOURCE_TYPE,
        "feature-binding",
    }
)


def techvault_admission_diagnostics(
    plan: ProvisioningPlan,
    envelope: BackendRealizationEnvelopeModel,
    *,
    name_prefix: str,
) -> list[Diagnostic]:
    """Reject every TechVault concern that cannot be applied and observed exactly.

    Direct provisioning-plan submission does not carry compiler-only explicitness
    metadata, so each concrete value is binding at this boundary. Validation is
    intentionally pure and runs before snapshot reconciliation or driver IO.
    """

    diagnostics: list[Diagnostic] = []
    planned_names: list[tuple[str, str]] = []
    mutations = [operation for operation in plan.operations if operation.action is not ChangeAction.UNCHANGED]
    if len(mutations) > 1 and any(operation.action is ChangeAction.DELETE for operation in mutations):
        diagnostics.append(
            _diagnostic(
                _CODE_TRANSACTION_UNSUPPORTED,
                "runtime.libvirt.transaction",
                "TechVault plans cannot combine deletion with another mutation without a verified restore path.",
            )
        )
    for operation in plan.operations:
        payload = operation.payload
        if (
            operation.action is not ChangeAction.DELETE
            and isinstance(payload, Mapping)
            and operation.resource_type in {NETWORK_RESOURCE_TYPE, NODE_RESOURCE_TYPE}
        ):
            planned_names.append((operation.address, _resource_name(operation, payload)))
        if operation.action in {ChangeAction.DELETE, ChangeAction.UNCHANGED}:
            continue
        if operation.action is ChangeAction.UPDATE:
            diagnostics.append(
                _diagnostic(
                    _CODE_UPDATE_UNSUPPORTED,
                    operation.address,
                    "TechVault appliance updates are not supported without a verified native restore path.",
                )
            )
            continue
        if not isinstance(payload, Mapping):
            continue
        if operation.resource_type in _GUEST_PLACEMENTS:
            diagnostics.append(
                _diagnostic(
                    _CODE_GUEST_PLACEMENT_UNSUPPORTED,
                    operation.address,
                    "TechVault appliance guest placements are unsupported and cannot be silently omitted.",
                )
            )
        elif operation.resource_type == NODE_RESOURCE_TYPE:
            diagnostics.extend(_node_diagnostics(operation.address, payload, envelope))
        elif operation.resource_type == NETWORK_RESOURCE_TYPE:
            diagnostics.extend(_network_diagnostics(operation.address, payload))
    diagnostics.extend(_native_name_diagnostics(planned_names, name_prefix))
    return diagnostics


def techvault_observation_diagnostics(
    *,
    networks: tuple[NetworkSpec, ...],
    domains: tuple[DomainSpec, ...],
    result: DriverResult,
) -> list[Diagnostic]:
    """Require complete daemon readback; driver handles alone prove nothing."""

    expected = _expected_observations(networks=networks, domains=domains)
    observed: dict[tuple[str, str, RealizationConcern], list[RealizationObservation]] = {}
    for item in result.observations:
        observed.setdefault(_observation_key(item), []).append(item)
    missing_by_address: set[str] = set()
    mismatched_by_address: set[str] = set()
    for key, expected_value in expected.items():
        candidates = observed.get(key, [])
        if not candidates or any(item.source is not ObservationStrength.DAEMON_OBSERVED for item in candidates):
            missing_by_address.add(key[0])
        elif (
            len(candidates) != 1
            or type(candidates[0].value) is not type(expected_value)
            or candidates[0].value != expected_value
        ):
            mismatched_by_address.add(key[0])
    diagnostics = [
        _diagnostic(
            _CODE_OBSERVATION_MISSING,
            address,
            "TechVault driver did not return complete daemon observations for the requested concern inventory.",
        )
        for address in sorted(missing_by_address)
    ]
    diagnostics.extend(
        _diagnostic(
            _CODE_OBSERVATION_MISMATCH,
            address,
            "TechVault daemon observations do not match the exact requested concern values.",
        )
        for address in sorted(mismatched_by_address - missing_by_address)
    )
    return diagnostics


def techvault_spec_diagnostics(
    *,
    networks: tuple[NetworkSpec, ...],
    domains: tuple[DomainSpec, ...],
    envelope: BackendRealizationEnvelopeModel,
    name_prefix: str,
) -> list[Diagnostic]:
    """Apply the same concern gate to callers that invoke the driver directly."""

    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_name_diagnostics(networks, domains, name_prefix))
    network_addresses = {spec.address for spec in networks}
    for spec in networks:
        diagnostics.extend(_network_spec_diagnostics(spec))
    for spec in domains:
        configuration = envelope.configuration
        if not _within(
            spec.memory_mib, configuration.memory_mib.minimum, configuration.memory_mib.maximum
        ) or not _within(spec.vcpus, configuration.vcpus.minimum, configuration.vcpus.maximum):
            diagnostics.append(
                _diagnostic(
                    _CODE_RESOURCE_OUT_OF_ENVELOPE,
                    spec.address,
                    "TechVault appliance resource values must be inside the governed envelope and are never clamped.",
                )
            )
        if spec.image_ref is not None:
            diagnostics.append(
                _diagnostic(
                    _CODE_IMAGE_UNSUPPORTED,
                    spec.address,
                    "TechVault appliance mode cannot honor a requested image and refuses image substitution.",
                )
            )
        if spec.services:
            diagnostics.append(
                _diagnostic(
                    _CODE_SERVICE_UNSUPPORTED,
                    spec.address,
                    "TechVault appliance mode does not realize declared guest services.",
                )
            )
        cloud_init = spec.cloud_init
        if cloud_init is not None and (
            cloud_init.hostname not in {None, spec.name}
            or cloud_init.users
            or cloud_init.write_files
            or cloud_init.packages
            or cloud_init.runcmd
        ):
            diagnostics.append(
                _diagnostic(
                    _CODE_GUEST_PLACEMENT_UNSUPPORTED,
                    spec.address,
                    "TechVault appliance mode does not realize cloud-init guest placements.",
                )
            )
        if spec.labels:
            diagnostics.append(
                _diagnostic(
                    _CODE_METADATA_UNSUPPORTED,
                    spec.address,
                    "TechVault appliance mode does not consume unbound domain metadata.",
                )
            )
        if spec.network_acls:
            diagnostics.append(
                _diagnostic(
                    _CODE_ACL_UNSUPPORTED,
                    spec.address,
                    "TechVault appliance mode does not realize declared network ACLs.",
                )
            )
        if any(address not in network_addresses for address in spec.networks):
            diagnostics.append(_network_exactness_diagnostic(spec.address))
    diagnostics.extend(_network_capacity_diagnostics(networks, domains))
    return diagnostics


def _name_diagnostics(
    networks: tuple[NetworkSpec, ...],
    domains: tuple[DomainSpec, ...],
    name_prefix: str,
) -> list[Diagnostic]:
    return _native_name_diagnostics([(spec.address, spec.name) for spec in (*networks, *domains)], name_prefix)


def _native_name_diagnostics(names: list[tuple[str, str]], name_prefix: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    native_names: set[str] = set()
    for address, name in names:
        exact_name = f"{name_prefix}-{name}" if name_prefix else name
        selected_name = runtime_name(name_prefix, address, name)
        if not name or selected_name != exact_name or selected_name in native_names:
            diagnostics.append(
                _diagnostic(
                    _CODE_NAME_UNSUPPORTED,
                    address,
                    "TechVault native names must be unique, libvirt-safe, and realizable without normalization.",
                )
            )
        native_names.add(selected_name)
    return diagnostics


def _network_capacity_diagnostics(
    networks: tuple[NetworkSpec, ...],
    domains: tuple[DomainSpec, ...],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for spec in networks:
        if not spec.cidr or not spec.gateway:
            continue
        try:
            network = ipaddress.ip_network(spec.cidr, strict=True)
            gateway = ipaddress.ip_address(spec.gateway)
        except ValueError:
            continue
        if not isinstance(network, ipaddress.IPv4Network):
            continue
        attachment_count = sum(spec.address in domain.networks for domain in domains)
        candidates = [network.network_address + offset for offset in range(10, 10 + attachment_count)]
        if any(
            candidate not in network or candidate == network.broadcast_address or candidate == gateway
            for candidate in candidates
        ):
            diagnostics.append(_network_exactness_diagnostic(spec.address))
    return diagnostics


def _network_spec_diagnostics(spec: NetworkSpec) -> list[Diagnostic]:
    if (
        not spec.cidr
        or not spec.gateway
        or set(spec.labels) != {"internal"}
        or spec.labels.get("internal") not in {"true", "false"}
    ):
        return [_network_exactness_diagnostic(spec.address)]
    try:
        network = ipaddress.ip_network(spec.cidr, strict=True)
        gateway = ipaddress.ip_address(spec.gateway)
    except ValueError:
        return [_network_exactness_diagnostic(spec.address)]
    if (
        not isinstance(network, ipaddress.IPv4Network)
        or gateway not in network
        or gateway in {network.network_address, network.broadcast_address}
    ):
        return [_network_exactness_diagnostic(spec.address)]
    return []


def _expected_observations(
    *,
    networks: tuple[NetworkSpec, ...],
    domains: tuple[DomainSpec, ...],
) -> dict[tuple[str, str, RealizationConcern], object]:
    expected: dict[tuple[str, str, RealizationConcern], object] = {}
    for spec in networks:
        expected[(spec.address, "exists", RealizationConcern.TOPOLOGY)] = True
        expected[(spec.address, "cidr", RealizationConcern.NETWORK)] = spec.cidr
        expected[(spec.address, "gateway", RealizationConcern.NETWORK)] = spec.gateway
        expected[(spec.address, "internal", RealizationConcern.NETWORK)] = spec.labels.get("internal") == "true"
        expected[(spec.address, "forward-mode", RealizationConcern.NETWORK)] = (
            "none" if spec.labels.get("internal") == "true" else "nat"
        )
    for spec in domains:
        expected[(spec.address, "exists", RealizationConcern.TOPOLOGY)] = True
        expected[(spec.address, "architecture", RealizationConcern.ARCHITECTURE)] = "x86_64"
        expected[(spec.address, "image-policy", RealizationConcern.IMAGE)] = "generated-initramfs-appliance"
        expected[(spec.address, "memory-mib", RealizationConcern.RESOURCE_ALLOCATION)] = spec.memory_mib
        expected[(spec.address, "vcpus", RealizationConcern.RESOURCE_ALLOCATION)] = spec.vcpus
        expected[(spec.address, "network-attachments", RealizationConcern.NETWORK)] = tuple(spec.networks)
    return expected


def _observation_key(observation: RealizationObservation) -> tuple[str, str, RealizationConcern]:
    return observation.address, observation.field_path, observation.concern


def _node_diagnostics(
    address: str,
    payload: Mapping[str, object],
    envelope: BackendRealizationEnvelopeModel,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    configuration = envelope.configuration
    resources = _node_resources(payload)
    memory_mib = _memory_mib(resources.get("ram"))
    vcpus = _vcpus(resources.get("cpu"))
    if not _within(memory_mib, configuration.memory_mib.minimum, configuration.memory_mib.maximum) or not _within(
        vcpus, configuration.vcpus.minimum, configuration.vcpus.maximum
    ):
        diagnostics.append(
            _diagnostic(
                _CODE_RESOURCE_OUT_OF_ENVELOPE,
                address,
                "TechVault appliance resource values must be inside the governed envelope and are never clamped.",
            )
        )
    if _image_ref(payload) is not None:
        diagnostics.append(
            _diagnostic(
                _CODE_IMAGE_UNSUPPORTED,
                address,
                "TechVault appliance mode cannot honor a requested image and refuses image substitution.",
            )
        )
    if _services(payload):
        diagnostics.append(
            _diagnostic(
                _CODE_SERVICE_UNSUPPORTED,
                address,
                "TechVault appliance mode does not realize declared guest services.",
            )
        )
    acls = _infrastructure_spec(payload).get("acls")
    if isinstance(acls, list | tuple) and acls:
        diagnostics.append(
            _diagnostic(
                _CODE_ACL_UNSUPPORTED,
                address,
                "TechVault appliance mode does not realize declared network ACLs.",
            )
        )
    return diagnostics


def _network_diagnostics(address: str, payload: Mapping[str, object]) -> list[Diagnostic]:
    properties = _infrastructure_spec(payload).get("properties")
    if not isinstance(properties, Mapping):
        return [_network_exactness_diagnostic(address)]
    cidr = properties.get("cidr")
    gateway = properties.get("gateway")
    internal = properties.get("internal")
    if not isinstance(cidr, str) or not isinstance(gateway, str) or not isinstance(internal, bool):
        return [_network_exactness_diagnostic(address)]
    try:
        network = ipaddress.ip_network(cidr, strict=True)
        parsed_gateway = ipaddress.ip_address(gateway)
    except ValueError:
        return [_network_exactness_diagnostic(address)]
    if (
        not isinstance(network, ipaddress.IPv4Network)
        or parsed_gateway not in network
        or parsed_gateway in {network.network_address, network.broadcast_address}
    ):
        return [_network_exactness_diagnostic(address)]
    return []


def _within(value: int, minimum: int, maximum: int | None) -> bool:
    return value >= minimum and (maximum is None or value <= maximum)


def _network_exactness_diagnostic(address: str) -> Diagnostic:
    return _diagnostic(
        _CODE_NETWORK_EXACTNESS,
        address,
        "TechVault appliance networks require explicit valid IPv4 CIDR, gateway, and internal values.",
    )


def _diagnostic(code: str, address: str, message: str) -> Diagnostic:
    return Diagnostic(code=code, domain=_DOMAIN, address=address, message=message, severity=Severity.ERROR)


__all__ = [
    "techvault_admission_diagnostics",
    "techvault_observation_diagnostics",
    "techvault_spec_diagnostics",
]
