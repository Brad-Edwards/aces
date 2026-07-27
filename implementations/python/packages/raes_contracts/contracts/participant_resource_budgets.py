"""Portable participant resource-budget intent, capacity, and runtime carriers."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import ContractModel, NonEmptyString, PrefixedDigestString
from .participant_resource_types import (
    EVENT_DISPOSITION as _EVENT_DISPOSITION,
)
from .participant_resource_types import (
    PARTICIPANT_RESOURCE_BUDGET_EVENT_SCHEMA_VERSION,
    PARTICIPANT_RESOURCE_BUDGET_POLICY_SCHEMA_VERSION,
    PARTICIPANT_RESOURCE_BUDGET_STATE_SCHEMA_VERSION,
    PARTICIPANT_RESOURCE_POOL_CAPACITY_SCHEMA_VERSION,
    ParticipantResourceAccountingMode,
    ParticipantResourceIsolationStrength,
    ParticipantResourceKind,
    ParticipantResourceOwnerKind,
    ParticipantResourceResetMode,
    participant_resource_budget_state_ref,
    participant_resource_pool_state_ref,
)
from .participant_resource_types import (
    RESOURCE_ACCOUNTING as _RESOURCE_ACCOUNTING,
)
from .participant_resource_types import (
    RESOURCE_UNIT as _RESOURCE_UNIT,
)
from .participant_resource_types import (
    require_quantity_semantics as _require_quantity_semantics,
)


class ParticipantResourceOwnerModel(ContractModel):
    owner_id: NonEmptyString
    kind: ParticipantResourceOwnerKind
    owner_ref: NonEmptyString


class ParticipantResourceQuantityModel(ContractModel):
    resource_kind: ParticipantResourceKind
    unit: NonEmptyString
    accounting_mode: ParticipantResourceAccountingMode
    meter_profile_ref: NonEmptyString
    amount: int = Field(ge=0, le=10**18)

    @model_validator(mode="after")
    def _validate_quantity(self) -> ParticipantResourceQuantityModel:
        _require_quantity_semantics(self.resource_kind, self.unit, self.accounting_mode)
        return self


class ParticipantResourceFairnessModel(ContractModel):
    policy: NonEmptyString
    priority_class: NonEmptyString
    weight: int = Field(ge=1, le=1_000_000)
    protected: bool
    borrowing: NonEmptyString
    reclaim: NonEmptyString
    max_queue_ticks: int = Field(ge=0, le=1_000_000_000)
    starvation_bound_ticks: int = Field(ge=1, le=1_000_000_000)


class ParticipantResourceBudgetDemandModel(ContractModel):
    budget_id: NonEmptyString
    owner: ParticipantResourceOwnerModel
    pool_ref: NonEmptyString
    quantity: ParticipantResourceQuantityModel
    limit: int = Field(ge=1, le=10**18)
    reservation: int = Field(ge=1, le=10**18)
    reset: ParticipantResourceResetMode
    window_ticks: int | None = Field(default=None, ge=1, le=1_000_000_000)
    parent_budget_ref: NonEmptyString | None = None
    evidence_refs: tuple[NonEmptyString, ...] = ()
    provenance: Literal["authored", "legacy_maximum"] = "authored"

    @model_validator(mode="after")
    def _validate_demand(self) -> ParticipantResourceBudgetDemandModel:
        if self.reservation > self.limit:
            raise ValueError("resource reservation cannot exceed its limit")
        windowed = self.quantity.accounting_mode == "windowed_counter"
        if windowed != (self.window_ticks is not None):
            raise ValueError("windowed resource demands require window_ticks and other modes forbid it")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("resource demand evidence_refs must be unique")
        if self.quantity.resource_kind == "storage_growth" and self.reset != "reconciled":
            raise ValueError("storage_growth resource demand requires reconciled reset")
        return self


class ParticipantResourceBudgetPolicyModel(ContractModel):
    schema_version: Literal[PARTICIPANT_RESOURCE_BUDGET_POLICY_SCHEMA_VERSION] = (
        PARTICIPANT_RESOURCE_BUDGET_POLICY_SCHEMA_VERSION
    )
    policy_id: NonEmptyString
    policy_address: NonEmptyString
    policy_digest: PrefixedDigestString
    owners: tuple[ParticipantResourceOwnerModel, ...] = Field(min_length=1)
    demands: tuple[ParticipantResourceBudgetDemandModel, ...] = Field(min_length=1)
    fairness: ParticipantResourceFairnessModel

    @model_validator(mode="after")
    def _validate_policy(self) -> ParticipantResourceBudgetPolicyModel:
        owner_ids = [owner.owner_id for owner in self.owners]
        budget_ids = [demand.budget_id for demand in self.demands]
        if len(owner_ids) != len(set(owner_ids)):
            raise ValueError("resource-budget policy owner ids must be unique")
        if len(budget_ids) != len(set(budget_ids)):
            raise ValueError("resource-budget policy budget ids must be unique")
        owners = {owner.owner_id: owner for owner in self.owners}
        demands = {demand.budget_id: demand for demand in self.demands}
        required_kinds = set(_RESOURCE_UNIT)
        actual_kinds = {demand.quantity.resource_kind for demand in self.demands}
        missing = sorted(required_kinds - actual_kinds)
        if missing:
            raise ValueError("resource-budget policy requires complete resource vector: " + ", ".join(missing))
        for demand in self.demands:
            if demand.owner.owner_id not in owners or owners[demand.owner.owner_id] != demand.owner:
                raise ValueError("resource-budget demand owner must resolve exactly in policy owners")
            if demand.parent_budget_ref is not None and demand.parent_budget_ref not in demands:
                raise ValueError("resource-budget demand parent must resolve in policy demands")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(budget_id: str) -> None:
            if budget_id in visiting:
                raise ValueError("resource-budget policy parent graph must be acyclic")
            if budget_id in visited:
                return
            visiting.add(budget_id)
            demand = demands[budget_id]
            if demand.parent_budget_ref is not None:
                parent = demands[demand.parent_budget_ref]
                if (
                    demand.quantity.resource_kind,
                    demand.quantity.unit,
                    demand.quantity.accounting_mode,
                    demand.quantity.meter_profile_ref,
                ) != (
                    parent.quantity.resource_kind,
                    parent.quantity.unit,
                    parent.quantity.accounting_mode,
                    parent.quantity.meter_profile_ref,
                ):
                    raise ValueError("resource-budget parent must use the same resource, unit, mode, and meter")
                if demand.limit > parent.limit:
                    raise ValueError("resource-budget child limit cannot exceed its parent")
                visit(demand.parent_budget_ref)
            visiting.remove(budget_id)
            visited.add(budget_id)

        for budget_id in demands:
            visit(budget_id)
        children_by_parent: dict[str, list[ParticipantResourceBudgetDemandModel]] = {}
        for demand in self.demands:
            if demand.parent_budget_ref is not None:
                children_by_parent.setdefault(demand.parent_budget_ref, []).append(demand)
        for parent_id, children in children_by_parent.items():
            if sum(child.limit for child in children) > demands[parent_id].limit:
                raise ValueError("resource-budget sibling limits cannot exceed their parent limit")
        pool_keys = [
            (
                demand.pool_ref,
                demand.owner.kind,
                demand.owner.owner_ref,
                demand.quantity.resource_kind,
                demand.quantity.unit,
                demand.quantity.accounting_mode,
                demand.quantity.meter_profile_ref,
            )
            for demand in self.demands
        ]
        if len(pool_keys) != len(set(pool_keys)):
            raise ValueError("resource-budget demands cannot alias the same canonical resource pool")
        return self


class ParticipantResourcePoolCapacityModel(ContractModel):
    schema_version: Literal[PARTICIPANT_RESOURCE_POOL_CAPACITY_SCHEMA_VERSION] = (
        PARTICIPANT_RESOURCE_POOL_CAPACITY_SCHEMA_VERSION
    )
    pool_ref: NonEmptyString
    owner_kind: ParticipantResourceOwnerKind
    owner_ref: NonEmptyString
    resource_kind: ParticipantResourceKind
    unit: NonEmptyString
    accounting_mode: ParticipantResourceAccountingMode
    meter_profile_ref: NonEmptyString
    capacity: int = Field(ge=1, le=10**18)
    tenant_isolation: ParticipantResourceIsolationStrength
    configuration_digest: PrefixedDigestString
    fairness_policy: NonEmptyString
    priority_classes: tuple[NonEmptyString, ...] = Field(min_length=1)
    borrowing: NonEmptyString
    reclaim: NonEmptyString
    max_queue_ticks: int = Field(ge=0, le=1_000_000_000)
    starvation_bound_ticks: int = Field(ge=1, le=1_000_000_000)
    protected_capacity: int = Field(ge=0, le=10**18)
    evidence_contract_ids: tuple[NonEmptyString, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_capacity(self) -> ParticipantResourcePoolCapacityModel:
        _require_quantity_semantics(self.resource_kind, self.unit, self.accounting_mode)
        if self.protected_capacity > self.capacity:
            raise ValueError("protected capacity cannot exceed configured capacity")
        if len(self.priority_classes) != len(set(self.priority_classes)):
            raise ValueError("pool priority classes must be unique")
        if len(self.evidence_contract_ids) != len(set(self.evidence_contract_ids)):
            raise ValueError("pool evidence contract ids must be unique")
        return self


class ParticipantResourceBudgetCapabilitiesModel(ContractModel):
    """Declared support plus configuration-bound logical pool capacity."""

    support_strength: Literal["unsupported", "disclosed_weak", "bounded", "exact"]
    supported_owner_kinds: list[ParticipantResourceOwnerKind] = Field(min_length=1)
    supported_resource_kinds: list[ParticipantResourceKind] = Field(min_length=1)
    supported_accounting_modes: list[ParticipantResourceAccountingMode] = Field(min_length=1)
    supported_reset_modes: list[ParticipantResourceResetMode] = Field(min_length=1)
    supported_fairness_policies: list[NonEmptyString] = Field(min_length=1)
    supported_isolation_strengths: list[ParticipantResourceIsolationStrength] = Field(min_length=1)
    configured_pools: list[ParticipantResourcePoolCapacityModel] = Field(min_length=1)
    realization_contract_ids: list[NonEmptyString] = Field(min_length=1)
    cross_range_pool_refs: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_capabilities(self) -> ParticipantResourceBudgetCapabilitiesModel:
        for field_name in (
            "supported_owner_kinds",
            "supported_resource_kinds",
            "supported_accounting_modes",
            "supported_reset_modes",
            "supported_fairness_policies",
            "supported_isolation_strengths",
            "realization_contract_ids",
            "cross_range_pool_refs",
        ):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must be unique")
        keys = [(pool.pool_ref, pool.resource_kind, pool.meter_profile_ref) for pool in self.configured_pools]
        if len(keys) != len(set(keys)):
            raise ValueError("configured pool resource entries must be unique")
        pools_by_ref = {
            pool_ref: tuple(pool for pool in self.configured_pools if pool.pool_ref == pool_ref)
            for pool_ref in self.cross_range_pool_refs
        }
        for _pool_ref, pools in pools_by_ref.items():
            if not pools:
                raise ValueError("cross-range pool ref must resolve")
            if any(pool.tenant_isolation != "tenant_partitioned" for pool in pools):
                raise ValueError("cross-range shared pools require tenant_partitioned isolation")
        for pool in self.configured_pools:
            if pool.owner_kind not in self.supported_owner_kinds:
                raise ValueError("configured pool owner kind is not declared supported")
            if pool.resource_kind not in self.supported_resource_kinds:
                raise ValueError("configured pool resource kind is not declared supported")
            if pool.accounting_mode not in self.supported_accounting_modes:
                raise ValueError("configured pool accounting mode is not declared supported")
            if pool.fairness_policy not in self.supported_fairness_policies:
                raise ValueError("configured pool fairness policy is not declared supported")
            if pool.tenant_isolation not in self.supported_isolation_strengths:
                raise ValueError("configured pool isolation strength is not declared supported")
        return self


class ParticipantResourceBudgetStateModel(ContractModel):
    schema_version: Literal[PARTICIPANT_RESOURCE_BUDGET_STATE_SCHEMA_VERSION] = (
        PARTICIPANT_RESOURCE_BUDGET_STATE_SCHEMA_VERSION
    )
    state_ref: NonEmptyString
    budget_id: NonEmptyString
    policy_address: NonEmptyString
    owner_kind: ParticipantResourceOwnerKind
    owner_ref: NonEmptyString
    pool_ref: NonEmptyString
    resource_kind: ParticipantResourceKind
    unit: NonEmptyString
    accounting_mode: ParticipantResourceAccountingMode
    meter_profile_ref: NonEmptyString
    reset: ParticipantResourceResetMode
    generation: int = Field(ge=0)
    limit: int = Field(ge=1, le=10**18)
    configured_capacity: int = Field(ge=1, le=10**18)
    reserved: int = Field(ge=0, le=10**18)
    current_use: int = Field(ge=0, le=10**18)
    cumulative_use: int = Field(ge=0, le=10**18)
    throttled: int = Field(ge=0)
    rejected: int = Field(ge=0)
    reconciliation_status: Literal["reconciled", "pending", "unreconciled"]
    last_event_ref: NonEmptyString
    evidence_refs: tuple[NonEmptyString, ...] = ()

    @model_validator(mode="after")
    def _validate_state(self) -> ParticipantResourceBudgetStateModel:
        _require_quantity_semantics(self.resource_kind, self.unit, self.accounting_mode)
        expected_ref = participant_resource_budget_state_ref(self.policy_address, self.budget_id)
        if self.state_ref != expected_ref:
            raise ValueError("resource budget state_ref must equal its canonical policy-scoped identity")
        if self.reserved + self.current_use > self.limit:
            raise ValueError("resource budget reserved and current use cannot exceed limit")
        if self.reserved + self.current_use > self.configured_capacity:
            raise ValueError("resource budget reserved and current use cannot exceed configured capacity")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("resource budget evidence refs must be unique")
        return self


class ParticipantResourceMeasurementRequirementModel(ContractModel):
    budget_state_ref: NonEmptyString
    resource_kind: ParticipantResourceKind
    unit: NonEmptyString
    meter_profile_ref: NonEmptyString
    reserved: int = Field(ge=0, le=10**18)

    @model_validator(mode="after")
    def _validate_requirement(self) -> ParticipantResourceMeasurementRequirementModel:
        expected_modes = _RESOURCE_ACCOUNTING[self.resource_kind]
        if not expected_modes:
            raise ValueError("resource measurement requires supported quantity semantics")
        if self.unit != _RESOURCE_UNIT[self.resource_kind]:
            raise ValueError("resource measurement requirement unit must match its resource kind")
        return self


class ParticipantResourceMeasurementModel(ContractModel):
    budget_state_ref: NonEmptyString
    operation_id: NonEmptyString
    execution_generation: int = Field(ge=0)
    resource_kind: ParticipantResourceKind
    unit: NonEmptyString
    meter_profile_ref: NonEmptyString
    measured: int = Field(ge=0, le=10**18)
    evidence_refs: tuple[NonEmptyString, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_measurement(self) -> ParticipantResourceMeasurementModel:
        if self.unit != _RESOURCE_UNIT[self.resource_kind]:
            raise ValueError("resource measurement unit must match its resource kind")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("resource measurement evidence refs must be unique")
        return self


class ParticipantResourcePoolAllocationModel(ContractModel):
    budget_state_ref: NonEmptyString
    policy_address: NonEmptyString
    budget_id: NonEmptyString
    generation: int = Field(ge=0)
    priority_class: NonEmptyString
    weight: int = Field(ge=1, le=1_000_000)
    protected: bool
    borrowing: NonEmptyString
    reclaim: NonEmptyString
    max_queue_ticks: int = Field(ge=0, le=1_000_000_000)
    starvation_bound_ticks: int = Field(ge=1, le=1_000_000_000)
    reserved: int = Field(ge=0, le=10**18)
    current_use: int = Field(ge=0, le=10**18)
    cumulative_use: int = Field(ge=0, le=10**18)

    @model_validator(mode="after")
    def _validate_allocation(self) -> ParticipantResourcePoolAllocationModel:
        expected_ref = participant_resource_budget_state_ref(self.policy_address, self.budget_id)
        if self.budget_state_ref != expected_ref:
            raise ValueError("pool allocation must reference its canonical policy-scoped budget state")
        return self


class ParticipantResourcePoolStateModel(ContractModel):
    """Authoritative allocation ledger for one exact physical resource pool."""

    pool_state_ref: NonEmptyString
    pool_ref: NonEmptyString
    owner_kind: ParticipantResourceOwnerKind
    owner_ref: NonEmptyString
    resource_kind: ParticipantResourceKind
    unit: NonEmptyString
    accounting_mode: ParticipantResourceAccountingMode
    meter_profile_ref: NonEmptyString
    capacity: int = Field(ge=1, le=10**18)
    protected_capacity: int = Field(ge=0, le=10**18)
    fairness_policy: NonEmptyString
    priority_classes: tuple[NonEmptyString, ...] = Field(min_length=1)
    borrowing: NonEmptyString
    reclaim: NonEmptyString
    max_queue_ticks: int = Field(ge=0, le=1_000_000_000)
    starvation_bound_ticks: int = Field(ge=1, le=1_000_000_000)
    allocations: dict[NonEmptyString, ParticipantResourcePoolAllocationModel] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_pool_state(self) -> ParticipantResourcePoolStateModel:
        _require_quantity_semantics(self.resource_kind, self.unit, self.accounting_mode)
        expected_ref = participant_resource_pool_state_ref(
            pool_ref=self.pool_ref,
            owner_kind=self.owner_kind,
            owner_ref=self.owner_ref,
            resource_kind=self.resource_kind,
            unit=self.unit,
            accounting_mode=self.accounting_mode,
            meter_profile_ref=self.meter_profile_ref,
        )
        if self.pool_state_ref != expected_ref:
            raise ValueError("pool_state_ref must equal the canonical exact-pool identity")
        if self.protected_capacity > self.capacity:
            raise ValueError("protected capacity cannot exceed physical pool capacity")
        for allocation_ref, allocation in self.allocations.items():
            if allocation_ref != allocation.budget_state_ref:
                raise ValueError("pool allocation map key must equal budget_state_ref")
            if allocation.priority_class not in self.priority_classes:
                raise ValueError("pool allocation priority class must be configured")
            if allocation.borrowing != self.borrowing or allocation.reclaim != self.reclaim:
                raise ValueError("pool allocation borrowing and reclaim must match pool authority")
            if (
                self.max_queue_ticks > allocation.max_queue_ticks
                or self.starvation_bound_ticks > allocation.starvation_bound_ticks
            ):
                raise ValueError("pool allocation fairness bounds are weaker than required")
        total = sum(
            (
                allocation.current_use + allocation.reserved
                if self.accounting_mode in {"reservable_gauge", "lease"}
                else allocation.cumulative_use + allocation.reserved
            )
            for allocation in self.allocations.values()
        )
        if total > self.capacity:
            raise ValueError("physical pool allocations cannot exceed capacity")
        return self


class ParticipantResourceBudgetEventModel(ContractModel):
    schema_version: Literal[PARTICIPANT_RESOURCE_BUDGET_EVENT_SCHEMA_VERSION] = (
        PARTICIPANT_RESOURCE_BUDGET_EVENT_SCHEMA_VERSION
    )
    event_id: NonEmptyString
    operation_id: NonEmptyString
    budget_state_ref: NonEmptyString
    budget_id: NonEmptyString
    policy_address: NonEmptyString
    owner_ref: NonEmptyString
    pool_ref: NonEmptyString
    execution_generation: int = Field(ge=0)
    transition: Literal["reserve", "commit", "release", "throttle", "reject", "reconcile"]
    disposition: Literal["reserved", "committed", "released", "throttled", "rejected", "reconciled"]
    requested: int = Field(ge=0, le=10**18)
    measured: int | None = Field(default=None, ge=0, le=10**18)
    resource_kind: ParticipantResourceKind
    unit: NonEmptyString
    meter_profile_ref: NonEmptyString
    predecessor_event_ref: NonEmptyString | None = None
    evidence_refs: tuple[NonEmptyString, ...] = ()

    @model_validator(mode="after")
    def _validate_event(self) -> ParticipantResourceBudgetEventModel:
        expected_ref = participant_resource_budget_state_ref(self.policy_address, self.budget_id)
        if self.budget_state_ref != expected_ref:
            raise ValueError("resource budget event must reference its canonical policy-scoped state")
        if self.disposition != _EVENT_DISPOSITION[self.transition]:
            raise ValueError("resource budget event disposition must match its transition")
        if self.transition == "commit" and self.measured is None:
            raise ValueError("commit events require measured resource use")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("resource budget event evidence refs must be unique")
        return self


__all__ = [
    "PARTICIPANT_RESOURCE_BUDGET_EVENT_SCHEMA_VERSION",
    "PARTICIPANT_RESOURCE_BUDGET_POLICY_SCHEMA_VERSION",
    "PARTICIPANT_RESOURCE_BUDGET_STATE_SCHEMA_VERSION",
    "PARTICIPANT_RESOURCE_POOL_CAPACITY_SCHEMA_VERSION",
    "ParticipantResourceAccountingMode",
    "ParticipantResourceBudgetDemandModel",
    "ParticipantResourceBudgetCapabilitiesModel",
    "ParticipantResourceBudgetEventModel",
    "ParticipantResourceBudgetPolicyModel",
    "ParticipantResourceBudgetStateModel",
    "ParticipantResourceFairnessModel",
    "ParticipantResourceIsolationStrength",
    "ParticipantResourceKind",
    "ParticipantResourceOwnerKind",
    "ParticipantResourceOwnerModel",
    "ParticipantResourcePoolCapacityModel",
    "ParticipantResourcePoolAllocationModel",
    "ParticipantResourcePoolStateModel",
    "ParticipantResourceMeasurementModel",
    "ParticipantResourceMeasurementRequirementModel",
    "ParticipantResourceQuantityModel",
    "ParticipantResourceResetMode",
    "participant_resource_budget_state_ref",
    "participant_resource_pool_state_ref",
]
