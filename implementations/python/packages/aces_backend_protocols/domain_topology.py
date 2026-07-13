"""Portable compiled identity-domain topology binding."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aces_contracts.addressing import require_compiled_address
from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.planning import ChangeAction, RuntimeDomain

if TYPE_CHECKING:
    from aces_contracts.planning import ProvisioningPlan
    from aces_contracts.runtime_state import RuntimeSnapshot

DOMAIN_NODE_ROLES = frozenset({"controller", "member"})


def domain_topology_profile(payload: Mapping[str, object]) -> str:
    """Return the concrete domain profile carried by a resource payload."""

    binding = payload.get("domain_topology")
    if not isinstance(binding, Mapping):
        return ""
    profile = binding.get("profile")
    return profile if isinstance(profile, str) else ""


@dataclass(frozen=True)
class DomainTopologyBinding:
    """Normalized domain realization intent attached to a plan resource."""

    domain_id: str
    profile: str
    dns_name: str
    netbios_name: str
    authority_account_address: str
    role: str
    controller_addresses: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in ("domain_id", "profile", "dns_name", "netbios_name"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"DomainTopologyBinding.{field_name} must be non-empty")
        require_compiled_address(
            self.authority_account_address,
            field_name="DomainTopologyBinding.authority_account_address",
        )
        if self.role not in DOMAIN_NODE_ROLES:
            raise ValueError("DomainTopologyBinding.role must be 'controller' or 'member'")
        if not self.controller_addresses:
            raise ValueError("DomainTopologyBinding.controller_addresses must not be empty")
        if len(self.controller_addresses) != len(set(self.controller_addresses)):
            raise ValueError("DomainTopologyBinding.controller_addresses must be unique")
        for address in self.controller_addresses:
            require_compiled_address(address, field_name="DomainTopologyBinding.controller_addresses")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> DomainTopologyBinding:
        """Parse the plain-data plan carrier into its typed representation."""

        controller_addresses = payload.get("controller_addresses", ())
        if isinstance(controller_addresses, (str, bytes, Mapping)):
            raise ValueError("DomainTopologyBinding.controller_addresses must be a sequence")
        try:
            controllers = tuple(str(value) for value in controller_addresses)
        except TypeError as error:
            raise ValueError("DomainTopologyBinding.controller_addresses must be a sequence") from error
        return cls(
            domain_id=str(payload.get("domain_id", "")),
            profile=str(payload.get("profile", "")),
            dns_name=str(payload.get("dns_name", "")),
            netbios_name=str(payload.get("netbios_name", "")),
            authority_account_address=str(payload.get("authority_account_address", "")),
            role=str(payload.get("role", "")),
            controller_addresses=controllers,
        )


@dataclass(frozen=True)
class _MaterializedResource:
    address: str
    resource_type: str
    payload: Mapping[str, object]
    ordering_dependencies: tuple[str, ...]
    refresh_dependencies: tuple[str, ...]


def _materialized_resources(
    plan: ProvisioningPlan,
    snapshot: RuntimeSnapshot | None,
) -> dict[str, _MaterializedResource]:
    resources: dict[str, _MaterializedResource] = {}
    if snapshot is not None:
        for entry in snapshot.entries.values():
            if entry.domain is not RuntimeDomain.PROVISIONING or not isinstance(entry.payload, Mapping):
                continue
            resources[entry.address] = _MaterializedResource(
                address=entry.address,
                resource_type=entry.resource_type,
                payload=entry.payload,
                ordering_dependencies=entry.ordering_dependencies,
                refresh_dependencies=entry.refresh_dependencies,
            )
    for resource in plan.resources.values():
        if resource.domain is not RuntimeDomain.PROVISIONING or not isinstance(resource.payload, Mapping):
            continue
        resources[resource.address] = _MaterializedResource(
            address=resource.address,
            resource_type=resource.resource_type,
            payload=resource.payload,
            ordering_dependencies=resource.ordering_dependencies,
            refresh_dependencies=resource.refresh_dependencies,
        )
    for operation in plan.operations:
        if operation.action is ChangeAction.DELETE:
            resources.pop(operation.address, None)
            continue
        if not isinstance(operation.payload, Mapping):
            continue
        resources[operation.address] = _MaterializedResource(
            address=operation.address,
            resource_type=operation.resource_type,
            payload=operation.payload,
            ordering_dependencies=operation.ordering_dependencies,
            refresh_dependencies=operation.refresh_dependencies,
        )
    return resources


def _diagnostic(code: str, address: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        domain="provisioning",
        address=address,
        message=message,
        severity=Severity.ERROR,
    )


def _parse_binding(
    resource: _MaterializedResource,
) -> tuple[DomainTopologyBinding | None, Diagnostic | None]:
    raw = resource.payload.get("domain_topology")
    if raw is None:
        return None, None
    if not isinstance(raw, Mapping):
        return None, _diagnostic(
            "provisioning.domain-topology.binding-invalid",
            resource.address,
            "Domain topology binding must be a typed mapping.",
        )
    try:
        return DomainTopologyBinding.from_mapping(raw), None
    except ValueError as error:
        return None, _diagnostic(
            "provisioning.domain-topology.binding-invalid",
            resource.address,
            f"Domain topology binding is invalid: {error}.",
        )


def _binding_core(binding: DomainTopologyBinding) -> tuple[str, str, str, str, str]:
    return (
        binding.domain_id,
        binding.profile,
        binding.dns_name,
        binding.netbios_name,
        binding.authority_account_address,
    )


def _account_spn(resource: _MaterializedResource) -> str:
    spec = resource.payload.get("spec")
    if not isinstance(spec, Mapping):
        return ""
    spn = spec.get("spn")
    return spn if isinstance(spn, str) else ""


def _account_target(resource: _MaterializedResource) -> str:
    target = resource.payload.get("target_address")
    return target if isinstance(target, str) else ""


def _dedupe_diagnostics(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    deduped: dict[tuple[str, str, str], Diagnostic] = {}
    for diagnostic in diagnostics:
        deduped.setdefault((diagnostic.code, diagnostic.address or "", diagnostic.message), diagnostic)
    return list(deduped.values())


def domain_topology_plan_diagnostics(
    plan: ProvisioningPlan,
    *,
    snapshot: RuntimeSnapshot | None = None,
    supported_domain_profiles: frozenset[str] | None = None,
) -> list[Diagnostic]:
    """Validate domain topology over resources, non-delete ops, and snapshot.

    Operations override same-address resources and admitted snapshot entries,
    matching the materialized state that a direct control-plane submission asks
    a provisioner to realize.
    """

    resources = _materialized_resources(plan, snapshot)
    diagnostics: list[Diagnostic] = []
    bindings: dict[str, DomainTopologyBinding] = {}
    for address, resource in resources.items():
        binding, diagnostic = _parse_binding(resource)
        if diagnostic is not None:
            diagnostics.append(diagnostic)
            continue
        if binding is None:
            if resource.resource_type == "account-placement" and _account_spn(resource):
                diagnostics.append(
                    _diagnostic(
                        "provisioning.domain-topology.spn-binding-missing",
                        address,
                        "An account placement carrying an SPN requires an explicit domain topology binding.",
                    )
                )
            continue
        if resource.resource_type not in {"node", "account-placement"}:
            diagnostics.append(
                _diagnostic(
                    "provisioning.domain-topology.carrier-invalid",
                    address,
                    "Domain topology bindings may appear only on node and account-placement resources.",
                )
            )
            continue
        bindings[address] = binding
        if supported_domain_profiles is not None and binding.profile not in supported_domain_profiles:
            diagnostics.append(
                _diagnostic(
                    "provisioner.unsupported-domain-profile",
                    address,
                    f"Provisioner does not support identity-domain profile '{binding.profile}'.",
                )
            )

    domain_cores: dict[str, tuple[str, str, str, str, str]] = {}
    for address, binding in bindings.items():
        core = _binding_core(binding)
        previous = domain_cores.setdefault(binding.domain_id, core)
        if previous != core:
            diagnostics.append(
                _diagnostic(
                    "provisioning.domain-topology.domain-definition-conflict",
                    address,
                    f"Domain topology bindings disagree on the definition of domain '{binding.domain_id}'.",
                )
            )

    node_bindings = {
        address: binding for address, binding in bindings.items() if resources[address].resource_type == "node"
    }
    account_bindings = {
        address: binding
        for address, binding in bindings.items()
        if resources[address].resource_type == "account-placement"
    }

    for address, binding in node_bindings.items():
        resource = resources[address]
        if binding.role == "controller" and address not in binding.controller_addresses:
            diagnostics.append(
                _diagnostic(
                    "provisioning.domain-topology.controller-self-missing",
                    address,
                    "A controller binding must include its own node address among the domain controllers.",
                )
            )
        for controller_address in binding.controller_addresses:
            controller = node_bindings.get(controller_address)
            if (
                controller is None
                or controller.role != "controller"
                or _binding_core(controller) != _binding_core(binding)
            ):
                diagnostics.append(
                    _diagnostic(
                        "provisioning.domain-topology.controller-unbound",
                        address,
                        f"Controller address '{controller_address}' does not resolve to a controller for "
                        f"domain '{binding.domain_id}'.",
                    )
                )
        if binding.role == "member":
            missing_dependencies = set(binding.controller_addresses) - set(resource.ordering_dependencies)
            if missing_dependencies:
                diagnostics.append(
                    _diagnostic(
                        "provisioning.domain-topology.controller-dependency-missing",
                        address,
                        "A member node must order after every selected domain controller.",
                    )
                )

    for address, binding in account_bindings.items():
        target_address = _account_target(resources[address])
        target_binding = node_bindings.get(target_address)
        if target_binding is None or target_binding != binding:
            diagnostics.append(
                _diagnostic(
                    "provisioning.domain-topology.account-node-mismatch",
                    address,
                    "An account domain binding must exactly match its target node's domain binding.",
                )
            )

    for address, binding in node_bindings.items():
        authority = account_bindings.get(binding.authority_account_address)
        authority_resource = resources.get(binding.authority_account_address)
        authority_target = _account_target(authority_resource) if authority_resource is not None else ""
        if (
            authority is None
            or _binding_core(authority) != _binding_core(binding)
            or authority.role != "controller"
            or authority_target not in binding.controller_addresses
        ):
            diagnostics.append(
                _diagnostic(
                    "provisioning.domain-topology.authority-account-invalid",
                    address,
                    "The domain authority account must resolve to an account placement on one of its controllers.",
                )
            )

    return _dedupe_diagnostics(diagnostics)


__all__ = [
    "DOMAIN_NODE_ROLES",
    "DomainTopologyBinding",
    "domain_topology_plan_diagnostics",
    "domain_topology_profile",
]
