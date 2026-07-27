"""Admission checks for participant resource-budget vectors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .backend_manifest import BackendManifest
    from .capabilities import ParticipantRuntimeCapabilities


class ResourceDemand(Protocol):
    budget_id: str
    owner_kind: str
    owner_address: str
    pool_ref: str
    resource_kind: str
    unit: str
    accounting_mode: str
    meter_profile_ref: str
    limit: int
    reservation: int
    reset: str
    parent_budget_ref: str | None


class ResourceFairness(Protocol):
    policy: str
    priority_class: str
    protected: bool
    borrowing: str
    reclaim: str
    max_queue_ticks: int
    starvation_bound_ticks: int


class ResourceGovernedPolicy(Protocol):
    address: str
    profile: str
    resource_demands: tuple[ResourceDemand, ...]
    resource_fairness: ResourceFairness


def participant_resource_budget_gaps(
    manifest: BackendManifest,
    capability: ParticipantRuntimeCapabilities,
    policies: tuple[ResourceGovernedPolicy, ...],
) -> list[str]:
    """Return atomic capacity, accounting, isolation, and fairness gaps."""

    governed = tuple(policy for policy in policies if policy.profile == "participant-autonomous-execution/v3")
    if not governed:
        return []
    budgets = capability.resource_budgets
    if budgets is None:
        return ["participant-autonomous-execution/v3 requires resource-budget capabilities"]
    gaps: list[str] = []
    if budgets.support_strength not in {"bounded", "exact"}:
        gaps.append(
            "participant resource budgets require bounded or exact support; "
            f"backend declares {budgets.support_strength}"
        )
    required_manifest_contracts = {
        "participant-resource-budget-policy-v1",
        "participant-resource-pool-capacity-v1",
        "participant-resource-budget-state-v1",
        "participant-resource-budget-event-v1",
    }
    missing_manifest_contracts = sorted(required_manifest_contracts - manifest.supported_contract_versions)
    if missing_manifest_contracts:
        gaps.append("participant resource budgets missing manifest contracts: " + ", ".join(missing_manifest_contracts))
    required_contracts = {
        "participant-resource-budget-state-v1",
        "participant-resource-budget-event-v1",
    }
    missing_contracts = sorted(required_contracts - budgets.realization_contract_ids)
    if missing_contracts:
        gaps.append("participant resource budgets missing realization contracts: " + ", ".join(missing_contracts))
    aggregate_limits: dict[tuple[str, ...], int] = {}
    aggregate_protected_limits: dict[tuple[str, ...], int] = {}
    pools_by_key: dict[tuple[str, ...], object] = {}
    for policy in governed:
        fairness = policy.resource_fairness
        if fairness.policy not in budgets.supported_fairness_policies:
            gaps.append(f"unsupported participant resource fairness policy: {fairness.policy}")
        policy_pool_keys: set[tuple[str, ...]] = set()
        demands_by_id = {demand.budget_id: demand for demand in policy.resource_demands}
        children_by_parent: dict[str, list[ResourceDemand]] = {}
        for demand in policy.resource_demands:
            if demand.parent_budget_ref is not None:
                children_by_parent.setdefault(demand.parent_budget_ref, []).append(demand)
        for parent_id, children in children_by_parent.items():
            parent = demands_by_id.get(parent_id)
            if parent is None or sum(child.limit for child in children) > parent.limit:
                gaps.append(
                    f"participant resource budget parent {parent_id} is missing or overcommitted by child limits"
                )
        for demand in policy.resource_demands:
            unsupported: list[str] = []
            if demand.owner_kind not in budgets.supported_owner_kinds:
                unsupported.append(f"owner kind {demand.owner_kind}")
            if demand.resource_kind not in budgets.supported_resource_kinds:
                unsupported.append(f"resource kind {demand.resource_kind}")
            if demand.accounting_mode not in budgets.supported_accounting_modes:
                unsupported.append(f"accounting mode {demand.accounting_mode}")
            if demand.reset not in budgets.supported_reset_modes:
                unsupported.append(f"reset mode {demand.reset}")
            if unsupported:
                gaps.append(f"participant resource budget {demand.budget_id} unsupported: " + ", ".join(unsupported))
                continue
            exact = tuple(
                pool
                for pool in budgets.configured_pools
                if pool.pool_ref == demand.pool_ref
                and pool.owner_kind == demand.owner_kind
                and pool.owner_ref == demand.owner_address
                and pool.resource_kind == demand.resource_kind
                and pool.unit == demand.unit
                and pool.accounting_mode == demand.accounting_mode
                and pool.meter_profile_ref == demand.meter_profile_ref
            )
            if not exact:
                gaps.append(
                    "participant resource budget "
                    f"{demand.budget_id} ({demand.resource_kind}) has no exact configured "
                    "owner/unit/accounting/meter capacity"
                )
                continue
            pool = exact[0]
            pool_key = (
                pool.pool_ref,
                pool.owner_kind,
                pool.owner_ref,
                pool.resource_kind,
                pool.unit,
                pool.accounting_mode,
                pool.meter_profile_ref,
            )
            if pool_key in policy_pool_keys:
                gaps.append(f"participant policy {policy.address} aliases canonical resource pool {pool.pool_ref}")
                continue
            policy_pool_keys.add(pool_key)
            pools_by_key[pool_key] = pool
            aggregate_limits[pool_key] = aggregate_limits.get(pool_key, 0) + demand.limit
            if fairness.protected:
                aggregate_protected_limits[pool_key] = aggregate_protected_limits.get(pool_key, 0) + demand.limit
            if pool.capacity < demand.limit:
                gaps.append(
                    "participant resource budget "
                    f"{demand.budget_id} ({demand.resource_kind}) requires capacity "
                    f"{demand.limit}; configured capacity is {pool.capacity}"
                )
            if pool.fairness_policy != fairness.policy:
                gaps.append(
                    "participant resource budget "
                    f"{demand.budget_id} ({demand.resource_kind}) requires fairness "
                    f"{fairness.policy}; configured pool declares {pool.fairness_policy}"
                )
            if fairness.priority_class not in pool.priority_classes:
                gaps.append(
                    "participant resource budget "
                    f"{demand.budget_id} ({demand.resource_kind}) requires priority class "
                    f"{fairness.priority_class}"
                )
            if pool.borrowing != fairness.borrowing or pool.reclaim != fairness.reclaim:
                gaps.append(
                    "participant resource budget "
                    f"{demand.budget_id} ({demand.resource_kind}) fairness borrowing/reclaim "
                    "does not match configured pool"
                )
            if (
                pool.max_queue_ticks > fairness.max_queue_ticks
                or pool.starvation_bound_ticks > fairness.starvation_bound_ticks
            ):
                gaps.append(
                    "participant resource budget "
                    f"{demand.budget_id} ({demand.resource_kind}) configured fairness "
                    "queue/starvation bounds are weaker than required"
                )
            if fairness.protected and pool.protected_capacity < demand.reservation:
                gaps.append(
                    f"participant resource budget {demand.budget_id} ({demand.resource_kind}) lacks protected capacity"
                )
    for pool_key, required in aggregate_limits.items():
        pool = pools_by_key[pool_key]
        if required > pool.capacity:
            gaps.append(
                f"participant resource pool {pool.pool_ref} aggregate policy limits require "
                f"{required}; configured capacity is {pool.capacity}"
            )
        protected = aggregate_protected_limits.get(pool_key, 0)
        if protected > pool.protected_capacity:
            gaps.append(
                f"participant resource pool {pool.pool_ref} protected policy limits require "
                f"{protected}; configured protected capacity is {pool.protected_capacity}"
            )
    return gaps


__all__ = ["participant_resource_budget_gaps"]
