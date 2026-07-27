"""Atomic initialization and reservation of participant resource budgets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from raes_contracts.contracts.participant_resource_budgets import (
    ParticipantResourceBudgetEventModel,
    ParticipantResourceBudgetStateModel,
    ParticipantResourcePoolStateModel,
    participant_resource_budget_state_ref,
    participant_resource_pool_state_ref,
)
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot

from .participant_resource_pool_ledger import (
    can_reserve as pool_can_reserve,
)
from .participant_resource_pool_ledger import (
    ensure_allocation,
    new_pool_state,
    pool_state_ref,
)
from .participant_resource_pool_ledger import (
    reserve as reserve_pool_allocation,
)


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


class ResourceFairness(Protocol):
    priority_class: str
    weight: int
    protected: bool
    borrowing: str
    reclaim: str
    max_queue_ticks: int
    starvation_bound_ticks: int


class ResourcePolicy(Protocol):
    address: str
    resource_demands: tuple[ResourceDemand, ...]
    resource_fairness: ResourceFairness


class ResourcePool(Protocol):
    pool_ref: str
    owner_kind: str
    owner_ref: str
    resource_kind: str
    unit: str
    accounting_mode: str
    meter_profile_ref: str
    capacity: int
    protected_capacity: int
    fairness_policy: str
    priority_classes: tuple[str, ...]
    borrowing: str
    reclaim: str
    max_queue_ticks: int
    starvation_bound_ticks: int


class ResourceCapabilities(Protocol):
    configured_pools: tuple[ResourcePool, ...]


def _diagnostic(code: str, policy_address: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        domain="participant-runtime",
        address=f"/participant_resource_budgets/{policy_address}",
        message=message,
    )


def _state(payload: Mapping[str, object]) -> ParticipantResourceBudgetStateModel:
    return ParticipantResourceBudgetStateModel.model_validate(payload)


def _pool_state(payload: Mapping[str, object]) -> ParticipantResourcePoolStateModel:
    return ParticipantResourcePoolStateModel.model_validate(payload)


def _payload(
    model: ParticipantResourceBudgetStateModel
    | ParticipantResourcePoolStateModel
    | ParticipantResourceBudgetEventModel,
) -> dict[str, object]:
    return model.model_dump(mode="json")


def _matching_pool(demand: ResourceDemand, capabilities: ResourceCapabilities) -> ResourcePool | None:
    return next(
        (
            pool
            for pool in capabilities.configured_pools
            if pool.pool_ref == demand.pool_ref
            and pool.owner_kind == demand.owner_kind
            and pool.owner_ref == demand.owner_address
            and pool.resource_kind == demand.resource_kind
            and pool.unit == demand.unit
            and pool.accounting_mode == demand.accounting_mode
            and pool.meter_profile_ref == demand.meter_profile_ref
        ),
        None,
    )


def initialize_participant_resource_budgets(
    snapshot: RuntimeSnapshot,
    policies: Sequence[ResourcePolicy],
    capabilities: ResourceCapabilities,
    *,
    execution_generation: int,
) -> ApplyResult:
    """Materialize policy budgets and authoritative physical-pool allocations."""

    states = dict(snapshot.participant_resource_budget_states)
    pool_states = dict(snapshot.participant_resource_pool_states)
    for policy in policies:
        for demand in policy.resource_demands:
            pool = _matching_pool(demand, capabilities)
            if pool is None:
                return ApplyResult(
                    success=False,
                    snapshot=snapshot,
                    diagnostics=[
                        _diagnostic(
                            "runtime.participant-resource-capacity-missing",
                            policy.address,
                            f"no exact configured capacity matches resource budget {demand.budget_id}",
                        )
                    ],
                )
            if policy.resource_fairness.protected and pool.protected_capacity < demand.reservation:
                return ApplyResult(
                    success=False,
                    snapshot=snapshot,
                    diagnostics=[
                        _diagnostic(
                            "runtime.participant-resource-protected-capacity-missing",
                            policy.address,
                            f"resource budget {demand.budget_id} lacks its protected reservation",
                        )
                    ],
                )
            state_ref = participant_resource_budget_state_ref(policy.address, demand.budget_id)
            existing = states.get(state_ref)
            if existing is not None:
                current = _state(existing)
                if current.generation != execution_generation:
                    return ApplyResult(
                        success=False,
                        snapshot=snapshot,
                        diagnostics=[
                            _diagnostic(
                                "runtime.participant-resource-state-conflict",
                                policy.address,
                                f"resource budget {demand.budget_id} already has incompatible state",
                            )
                        ],
                    )
                continue
            budget_state = ParticipantResourceBudgetStateModel(
                state_ref=state_ref,
                budget_id=demand.budget_id,
                policy_address=policy.address,
                owner_kind=demand.owner_kind,
                owner_ref=demand.owner_address,
                pool_ref=demand.pool_ref,
                resource_kind=demand.resource_kind,
                unit=demand.unit,
                accounting_mode=demand.accounting_mode,
                meter_profile_ref=demand.meter_profile_ref,
                reset=demand.reset,
                generation=execution_generation,
                limit=demand.limit,
                configured_capacity=pool.capacity,
                reserved=0,
                current_use=0,
                cumulative_use=0,
                throttled=0,
                rejected=0,
                reconciliation_status="reconciled",
                last_event_ref=f"initial:{state_ref}",
            )
            states[state_ref] = _payload(budget_state)
            exact_pool_ref = pool_state_ref(pool)
            existing_pool = pool_states.get(exact_pool_ref)
            physical_pool = new_pool_state(pool) if existing_pool is None else _pool_state(existing_pool)
            try:
                physical_pool = ensure_allocation(
                    physical_pool,
                    budget_state,
                    fairness=policy.resource_fairness,
                )
            except ValueError as exc:
                return ApplyResult(
                    success=False,
                    snapshot=snapshot,
                    diagnostics=[
                        _diagnostic(
                            "runtime.participant-resource-pool-conflict",
                            policy.address,
                            str(exc),
                        )
                    ],
                )
            pool_states[exact_pool_ref] = _payload(physical_pool)
    return ApplyResult(
        success=True,
        snapshot=snapshot.with_entries(
            dict(snapshot.entries),
            participant_resource_budget_states=states,
            participant_resource_pool_states=pool_states,
        ),
    )


def _reservation_event_id(operation_id: str, state_ref: str) -> str:
    return f"{operation_id}:{state_ref}:reserve"


def _used_capacity(state: ParticipantResourceBudgetStateModel) -> int:
    if state.accounting_mode in {"reservable_gauge", "lease"}:
        return state.current_use + state.reserved
    return state.cumulative_use + state.reserved


def _pool_ref_for_state(state: ParticipantResourceBudgetStateModel) -> str:
    return participant_resource_pool_state_ref(
        pool_ref=state.pool_ref,
        owner_kind=state.owner_kind,
        owner_ref=state.owner_ref,
        resource_kind=state.resource_kind,
        unit=state.unit,
        accounting_mode=state.accounting_mode,
        meter_profile_ref=state.meter_profile_ref,
    )


def _throttled_result(
    snapshot: RuntimeSnapshot,
    states: dict[str, dict[str, object]],
    pool_states: dict[str, dict[str, object]],
    events: dict[str, dict[str, object]],
    *,
    policy: ResourcePolicy,
    demand: ResourceDemand,
    current: ParticipantResourceBudgetStateModel,
    operation_id: str,
    execution_generation: int,
    amount: int,
    budget_available: bool,
) -> ApplyResult:
    event_id = f"{operation_id}:{current.state_ref}:throttle"
    states[current.state_ref] = _payload(
        current.model_copy(
            update={
                "throttled": current.throttled + 1,
                "last_event_ref": event_id,
            }
        )
    )
    events[event_id] = _payload(
        ParticipantResourceBudgetEventModel(
            event_id=event_id,
            operation_id=operation_id,
            budget_state_ref=current.state_ref,
            budget_id=demand.budget_id,
            policy_address=policy.address,
            owner_ref=current.owner_ref,
            pool_ref=current.pool_ref,
            execution_generation=execution_generation,
            transition="throttle",
            disposition="throttled",
            requested=amount,
            resource_kind=current.resource_kind,
            unit=current.unit,
            meter_profile_ref=current.meter_profile_ref,
            predecessor_event_ref=current.last_event_ref,
        )
    )
    return ApplyResult(
        success=False,
        snapshot=snapshot.with_entries(
            dict(snapshot.entries),
            participant_resource_budget_states=states,
            participant_resource_pool_states=pool_states,
            participant_resource_budget_events=events,
        ),
        diagnostics=[
            _diagnostic(
                "runtime.participant-resource-throttled",
                policy.address,
                (
                    f"resource budget {demand.budget_id} has insufficient "
                    f"{'logical budget' if not budget_available else 'shared pool'} capacity"
                ),
            )
        ],
    )


def reserve_participant_resources(
    snapshot: RuntimeSnapshot,
    policy: ResourcePolicy,
    *,
    operation_id: str,
    execution_generation: int,
    requested_quantities: Mapping[str, int] | None = None,
) -> ApplyResult:
    """Reserve a policy's complete resource vector or reserve none of it."""

    events = dict(snapshot.participant_resource_budget_events)
    state_refs = [
        participant_resource_budget_state_ref(policy.address, demand.budget_id) for demand in policy.resource_demands
    ]
    event_ids = [_reservation_event_id(operation_id, state_ref) for state_ref in state_refs]
    if event_ids and all(event_id in events for event_id in event_ids):
        return ApplyResult(success=True, snapshot=snapshot)
    states = dict(snapshot.participant_resource_budget_states)
    pool_states = dict(snapshot.participant_resource_pool_states)
    checked: list[
        tuple[
            ResourceDemand,
            ParticipantResourceBudgetStateModel,
            ParticipantResourcePoolStateModel,
            int,
        ]
    ] = []
    for demand, state_ref in zip(policy.resource_demands, state_refs, strict=True):
        raw = states.get(state_ref)
        if raw is None:
            return ApplyResult(
                success=False,
                snapshot=snapshot,
                diagnostics=[
                    _diagnostic(
                        "runtime.participant-resource-state-missing",
                        policy.address,
                        f"resource budget {demand.budget_id} was not initialized",
                    )
                ],
            )
        current = _state(raw)
        if current.generation != execution_generation:
            return ApplyResult(
                success=False,
                snapshot=snapshot,
                diagnostics=[
                    _diagnostic(
                        "runtime.participant-resource-stale-generation",
                        policy.address,
                        (
                            f"resource budget {demand.budget_id} is generation {current.generation}; "
                            f"request is generation {execution_generation}"
                        ),
                    )
                ],
            )
        amount = (
            requested_quantities.get(demand.budget_id, demand.reservation)
            if requested_quantities is not None
            else demand.reservation
        )
        if amount < 0:
            raise ValueError("requested participant resource quantities must be non-negative")
        exact_pool_ref = _pool_ref_for_state(current)
        raw_pool = pool_states.get(exact_pool_ref)
        if raw_pool is None:
            return ApplyResult(
                success=False,
                snapshot=snapshot,
                diagnostics=[
                    _diagnostic(
                        "runtime.participant-resource-pool-state-missing",
                        policy.address,
                        f"physical pool for resource budget {demand.budget_id} was not initialized",
                    )
                ],
            )
        physical_pool = _pool_state(raw_pool)
        budget_available = _used_capacity(current) + amount <= min(
            current.limit,
            current.configured_capacity,
        )
        if not budget_available or not pool_can_reserve(physical_pool, state_ref, amount):
            return _throttled_result(
                snapshot,
                states,
                pool_states,
                events,
                policy=policy,
                demand=demand,
                current=current,
                operation_id=operation_id,
                execution_generation=execution_generation,
                amount=amount,
                budget_available=budget_available,
            )
        checked.append((demand, current, physical_pool, amount))
    for demand, current, physical_pool, amount in checked:
        event_id = _reservation_event_id(operation_id, current.state_ref)
        event = ParticipantResourceBudgetEventModel(
            event_id=event_id,
            operation_id=operation_id,
            budget_state_ref=current.state_ref,
            budget_id=demand.budget_id,
            policy_address=policy.address,
            owner_ref=current.owner_ref,
            pool_ref=current.pool_ref,
            execution_generation=execution_generation,
            transition="reserve",
            disposition="reserved",
            requested=amount,
            resource_kind=current.resource_kind,
            unit=current.unit,
            meter_profile_ref=current.meter_profile_ref,
            predecessor_event_ref=current.last_event_ref,
        )
        states[current.state_ref] = _payload(
            current.model_copy(
                update={
                    "reserved": current.reserved + amount,
                    "last_event_ref": event_id,
                }
            )
        )
        pool_states[physical_pool.pool_state_ref] = _payload(
            reserve_pool_allocation(physical_pool, current.state_ref, amount)
        )
        events[event_id] = _payload(event)
    return ApplyResult(
        success=True,
        snapshot=snapshot.with_entries(
            dict(snapshot.entries),
            participant_resource_budget_states=states,
            participant_resource_pool_states=pool_states,
            participant_resource_budget_events=events,
        ),
    )


__all__ = (
    "initialize_participant_resource_budgets",
    "reserve_participant_resources",
)
