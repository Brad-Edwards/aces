"""Shared runtime planning contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from aces_contracts.addressing import require_compiled_address
from aces_contracts.diagnostics import Diagnostic

if TYPE_CHECKING:
    from aces_contracts.contracts import RealizationEnvelopeIdentityModel


class RuntimeDomain(str, Enum):
    """Top-level runtime concern."""

    PROVISIONING = "provisioning"
    ORCHESTRATION = "orchestration"
    EVALUATION = "evaluation"
    PARTICIPANT = "participant"


PLAN_ADDRESS_ROOT_BY_DOMAIN = {
    RuntimeDomain.PROVISIONING: "provision",
    RuntimeDomain.ORCHESTRATION: "orchestration",
    RuntimeDomain.EVALUATION: "evaluation",
}
PLAN_RESOURCE_TYPES_BY_DOMAIN = {
    RuntimeDomain.PROVISIONING: frozenset(
        {"network", "node", "feature-binding", "content-placement", "account-placement"}
    ),
    RuntimeDomain.ORCHESTRATION: frozenset({"inject-binding", "inject", "event", "script", "story", "workflow"}),
    RuntimeDomain.EVALUATION: frozenset({"condition-binding", "proposition", "assertion", "objective"}),
}


def require_plan_operation_identity(domain: RuntimeDomain, address: object, resource_type: object) -> None:
    """Reject operations outside a plan endpoint's closed identity domain."""

    canonical = require_compiled_address(address)
    root = PLAN_ADDRESS_ROOT_BY_DOMAIN.get(domain)
    resource_types = PLAN_RESOURCE_TYPES_BY_DOMAIN.get(domain)
    if root is None or not canonical.startswith(f"{root}."):
        raise ValueError("Plan operation address must belong to its runtime domain")
    if not isinstance(resource_type, str) or resource_types is None or resource_type not in resource_types:
        raise ValueError("Plan operation resource_type must belong to its runtime domain")


class ChangeAction(str, Enum):
    """Planner reconciliation result for a resource."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class PlannedResource:
    """Normalized resource used by the planner and snapshot."""

    address: str
    domain: RuntimeDomain
    resource_type: str
    payload: dict[str, Any]
    ordering_dependencies: tuple[str, ...] = ()
    refresh_dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compiled_address(self.address)
        for dependency in (*self.ordering_dependencies, *self.refresh_dependencies):
            require_compiled_address(dependency, field_name="dependency address")


@dataclass(frozen=True)
class PlanOperation:
    """A reconciliation operation for a planned resource."""

    action: ChangeAction
    address: str
    resource_type: str
    payload: dict[str, Any]
    ordering_dependencies: tuple[str, ...] = ()
    refresh_dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compiled_address(self.address)
        for dependency in (*self.ordering_dependencies, *self.refresh_dependencies):
            require_compiled_address(dependency, field_name="dependency address")


class ProvisionOp(PlanOperation):
    """Provisioning reconciliation operation."""


class OrchestrationOp(PlanOperation):
    """Orchestration reconciliation operation."""


class EvaluationOp(PlanOperation):
    """Evaluation reconciliation operation."""


@dataclass(frozen=True)
class ProvisioningPlan:
    """Provisioning plan over canonical deployment resources."""

    resources: dict[str, PlannedResource] = field(default_factory=dict)
    operations: list[ProvisionOp] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    realization_envelope: RealizationEnvelopeIdentityModel | None = None

    def __post_init__(self) -> None:
        _validate_plan_addresses(self.resources, self.operations, domain=RuntimeDomain.PROVISIONING)

    @property
    def actionable_operations(self) -> list[ProvisionOp]:
        return [op for op in self.operations if op.action != ChangeAction.UNCHANGED]


@dataclass(frozen=True)
class OrchestrationPlan:
    """Resolved orchestration graph and reconciliation actions."""

    resources: dict[str, PlannedResource] = field(default_factory=dict)
    operations: list[OrchestrationOp] = field(default_factory=list)
    startup_order: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_plan_addresses(
            self.resources,
            self.operations,
            self.startup_order,
            domain=RuntimeDomain.ORCHESTRATION,
        )

    @property
    def actionable_operations(self) -> list[OrchestrationOp]:
        return [op for op in self.operations if op.action != ChangeAction.UNCHANGED]


@dataclass(frozen=True)
class EvaluationPlan:
    """Resolved evaluation graph and reconciliation actions."""

    resources: dict[str, PlannedResource] = field(default_factory=dict)
    operations: list[EvaluationOp] = field(default_factory=list)
    startup_order: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_plan_addresses(
            self.resources,
            self.operations,
            self.startup_order,
            domain=RuntimeDomain.EVALUATION,
        )

    @property
    def actionable_operations(self) -> list[EvaluationOp]:
        return [op for op in self.operations if op.action != ChangeAction.UNCHANGED]


def _validate_plan_addresses(
    resources: dict[str, PlannedResource],
    operations: list[PlanOperation],
    startup_order: list[str] | None = None,
    *,
    domain: RuntimeDomain,
) -> None:
    for map_key, resource in resources.items():
        require_compiled_address(map_key, field_name="resource map key")
        if map_key != resource.address:
            raise ValueError("Plan resource map key must equal embedded address")
        if resource.domain is not domain:
            raise ValueError("Plan resource domain must equal the plan domain")
        require_plan_operation_identity(domain, resource.address, resource.resource_type)
    operation_addresses = [operation.address for operation in operations]
    for operation in operations:
        require_plan_operation_identity(domain, operation.address, operation.resource_type)
    if len(operation_addresses) != len(set(operation_addresses)):
        raise ValueError("Plan operation addresses must be unique")
    if startup_order is None:
        return
    for address in startup_order:
        require_compiled_address(address, field_name="startup_order address")
    if len(startup_order) != len(set(startup_order)):
        raise ValueError("Plan startup_order addresses must be unique")
    unknown = set(startup_order) - set(operation_addresses)
    if unknown:
        raise ValueError("Plan startup_order must reference admitted operation addresses")


__all__ = (
    "ChangeAction",
    "EvaluationOp",
    "EvaluationPlan",
    "OrchestrationOp",
    "OrchestrationPlan",
    "PlanOperation",
    "PLAN_ADDRESS_ROOT_BY_DOMAIN",
    "PLAN_RESOURCE_TYPES_BY_DOMAIN",
    "PlannedResource",
    "ProvisionOp",
    "ProvisioningPlan",
    "RuntimeDomain",
    "require_plan_operation_identity",
)
