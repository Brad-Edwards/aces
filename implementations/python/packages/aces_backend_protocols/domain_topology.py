"""Portable compiled identity-domain topology binding."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aces_contracts.addressing import require_compiled_address
from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.planning import ChangeAction, RuntimeDomain

if TYPE_CHECKING:
    from aces_contracts.planning import PlannedResource, PlanOperation, ProvisioningPlan
    from aces_contracts.runtime_state import RuntimeSnapshot, SnapshotEntry

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


def _snapshot_resources(snapshot: RuntimeSnapshot | None) -> dict[str, _MaterializedResource]:
    resources: dict[str, _MaterializedResource] = {}
    if snapshot is None:
        return resources
    for entry in snapshot.entries.values():
        materialized = _materialize_snapshot_entry(entry)
        if materialized is not None:
            resources[entry.address] = materialized
    return resources


def _materialize_snapshot_entry(entry: SnapshotEntry) -> _MaterializedResource | None:
    if entry.domain is not RuntimeDomain.PROVISIONING or not isinstance(entry.payload, Mapping):
        return None
    return _MaterializedResource(
        address=entry.address,
        resource_type=entry.resource_type,
        payload=entry.payload,
        ordering_dependencies=entry.ordering_dependencies,
        refresh_dependencies=entry.refresh_dependencies,
    )


def _materialize_planned_resource(resource: PlannedResource) -> _MaterializedResource | None:
    if resource.domain is not RuntimeDomain.PROVISIONING or not isinstance(resource.payload, Mapping):
        return None
    return _MaterializedResource(
        address=resource.address,
        resource_type=resource.resource_type,
        payload=resource.payload,
        ordering_dependencies=resource.ordering_dependencies,
        refresh_dependencies=resource.refresh_dependencies,
    )


def _materialize_operation(operation: PlanOperation) -> _MaterializedResource | None:
    if not isinstance(operation.payload, Mapping):
        return None
    return _MaterializedResource(
        address=operation.address,
        resource_type=operation.resource_type,
        payload=operation.payload,
        ordering_dependencies=operation.ordering_dependencies,
        refresh_dependencies=operation.refresh_dependencies,
    )


def _materialized_resources(
    plan: ProvisioningPlan,
    snapshot: RuntimeSnapshot | None,
) -> dict[str, _MaterializedResource]:
    resources = _snapshot_resources(snapshot)
    for resource in plan.resources.values():
        materialized = _materialize_planned_resource(resource)
        if materialized is not None:
            resources[resource.address] = materialized
    for operation in plan.operations:
        if operation.action is ChangeAction.DELETE:
            resources.pop(operation.address, None)
            continue
        materialized = _materialize_operation(operation)
        if materialized is not None:
            resources[operation.address] = materialized
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
    binding: DomainTopologyBinding | None = None
    diagnostic: Diagnostic | None = None
    if raw is not None:
        if not isinstance(raw, Mapping):
            diagnostic = _diagnostic(
                "provisioning.domain-topology.binding-invalid",
                resource.address,
                "Domain topology binding must be a typed mapping.",
            )
        else:
            try:
                binding = DomainTopologyBinding.from_mapping(raw)
            except ValueError as error:
                diagnostic = _diagnostic(
                    "provisioning.domain-topology.binding-invalid",
                    resource.address,
                    f"Domain topology binding is invalid: {error}.",
                )
    return binding, diagnostic


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


def _collect_bindings(
    resources: Mapping[str, _MaterializedResource],
    supported_domain_profiles: frozenset[str] | None,
) -> tuple[dict[str, DomainTopologyBinding], list[Diagnostic]]:
    bindings: dict[str, DomainTopologyBinding] = {}
    diagnostics: list[Diagnostic] = []
    for address, resource in resources.items():
        binding, diagnostic = _parse_binding(resource)
        if diagnostic is not None:
            diagnostics.append(diagnostic)
        elif binding is None:
            if resource.resource_type == "account-placement" and _account_spn(resource):
                diagnostics.append(
                    _diagnostic(
                        "provisioning.domain-topology.spn-binding-missing",
                        address,
                        "An account placement carrying an SPN requires an explicit domain topology binding.",
                    )
                )
        elif resource.resource_type not in {"node", "account-placement"}:
            diagnostics.append(
                _diagnostic(
                    "provisioning.domain-topology.carrier-invalid",
                    address,
                    "Domain topology bindings may appear only on node and account-placement resources.",
                )
            )
        else:
            bindings[address] = binding
            if supported_domain_profiles is not None and binding.profile not in supported_domain_profiles:
                diagnostics.append(
                    _diagnostic(
                        "provisioner.unsupported-domain-profile",
                        address,
                        f"Provisioner does not support identity-domain profile '{binding.profile}'.",
                    )
                )
    return bindings, diagnostics


def _domain_definition_diagnostics(bindings: Mapping[str, DomainTopologyBinding]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
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
    return diagnostics


def _bindings_for_resource_type(
    bindings: Mapping[str, DomainTopologyBinding],
    resources: Mapping[str, _MaterializedResource],
    resource_type: str,
) -> dict[str, DomainTopologyBinding]:
    return {
        address: binding for address, binding in bindings.items() if resources[address].resource_type == resource_type
    }


def _controller_matches_domain(
    controller: DomainTopologyBinding | None,
    binding: DomainTopologyBinding,
) -> bool:
    return (
        controller is not None
        and controller.role == "controller"
        and _binding_core(controller) == _binding_core(binding)
    )


def _node_binding_diagnostics(
    resources: Mapping[str, _MaterializedResource],
    node_bindings: Mapping[str, DomainTopologyBinding],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
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
            if not _controller_matches_domain(node_bindings.get(controller_address), binding):
                diagnostics.append(
                    _diagnostic(
                        "provisioning.domain-topology.controller-unbound",
                        address,
                        f"Controller address '{controller_address}' does not resolve to a controller for "
                        f"domain '{binding.domain_id}'.",
                    )
                )
        missing_dependencies = set(binding.controller_addresses) - set(resource.ordering_dependencies)
        if binding.role == "member" and missing_dependencies:
            diagnostics.append(
                _diagnostic(
                    "provisioning.domain-topology.controller-dependency-missing",
                    address,
                    "A member node must order after every selected domain controller.",
                )
            )
    return diagnostics


def _account_binding_diagnostics(
    resources: Mapping[str, _MaterializedResource],
    node_bindings: Mapping[str, DomainTopologyBinding],
    account_bindings: Mapping[str, DomainTopologyBinding],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for address, binding in account_bindings.items():
        target_address = _account_target(resources[address])
        if node_bindings.get(target_address) != binding:
            diagnostics.append(
                _diagnostic(
                    "provisioning.domain-topology.account-node-mismatch",
                    address,
                    "An account domain binding must exactly match its target node's domain binding.",
                )
            )
    return diagnostics


def _authority_account_is_valid(
    binding: DomainTopologyBinding,
    authority: DomainTopologyBinding | None,
    authority_resource: _MaterializedResource | None,
) -> bool:
    authority_target = _account_target(authority_resource) if authority_resource is not None else ""
    return (
        authority is not None
        and _binding_core(authority) == _binding_core(binding)
        and authority.role == "controller"
        and authority_target in binding.controller_addresses
    )


def _authority_account_diagnostics(
    resources: Mapping[str, _MaterializedResource],
    node_bindings: Mapping[str, DomainTopologyBinding],
    account_bindings: Mapping[str, DomainTopologyBinding],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for address, binding in node_bindings.items():
        authority_address = binding.authority_account_address
        if not _authority_account_is_valid(
            binding,
            account_bindings.get(authority_address),
            resources.get(authority_address),
        ):
            diagnostics.append(
                _diagnostic(
                    "provisioning.domain-topology.authority-account-invalid",
                    address,
                    "The domain authority account must resolve to an account placement on one of its controllers.",
                )
            )
    return diagnostics


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
    bindings, diagnostics = _collect_bindings(resources, supported_domain_profiles)
    diagnostics.extend(_domain_definition_diagnostics(bindings))

    node_bindings = _bindings_for_resource_type(bindings, resources, "node")
    account_bindings = _bindings_for_resource_type(bindings, resources, "account-placement")
    diagnostics.extend(_node_binding_diagnostics(resources, node_bindings))
    diagnostics.extend(_account_binding_diagnostics(resources, node_bindings, account_bindings))
    diagnostics.extend(_authority_account_diagnostics(resources, node_bindings, account_bindings))

    return _dedupe_diagnostics(diagnostics)


__all__ = [
    "DOMAIN_NODE_ROLES",
    "DomainTopologyBinding",
    "domain_topology_plan_diagnostics",
    "domain_topology_profile",
]
