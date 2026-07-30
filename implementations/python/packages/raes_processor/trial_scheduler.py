"""Deterministic batch-trial scheduling over the one-entry realization seam (SCE-006).

This is the repository-owned, schedule-independent handoff an orchestrator (APTL, or
any other coordinator) uses to run an admitted trial plan. It is an outer
coordinator over :func:`realize_admitted_trial_entry`: it may only choose
placement, deterministic order, bounded parallelism, timeouts, cancellation, and
cleanup (SVR-031). It never composes SDL, selects a variation, draws randomness,
allocates a ``run_id``, interprets factors, or scores.

:func:`plan_batch_schedule` is pure. It validates and integrity-checks the
*complete* admitted plan before exposing any entry, derives the canonical
dispatch order from the plan's ``trial-coordinate-v1`` coordinates, and reports
the *admitted parallelism ceiling* -- the maximum concurrency the sealed plan's
own embedded isolation proof authorizes (one when there is no such proof). It
deliberately does NOT decide the effective concurrency: proving live,
non-overlapping, currently-owned range/host/port/storage/lock/secret leases is
the downstream allocator's responsibility, and a non-empty tuple of caller
reference strings is not proof of any of that. The allocator decides an
effective bound no greater than the ceiling and records it, with its live lease
evidence, in a :class:`BatchExecutionReceiptModel` via
:func:`build_batch_execution_receipt`; that receipt records the allocator's
decision rather than authorizing it.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypeVar

from raes_contracts.admitted_trial_plan_ingress import revalidate_admitted_trial_plan
from raes_contracts.contracts import (
    AdmittedTrialPlanModel,
    BatchExecutionReceiptModel,
    validate_scheduler_isolation_proof,
)
from raes_contracts.contracts.trial_cleanup import TrialOutcome
from raes_contracts.contracts.trial_coordinate_order import CANONICAL_ORDER_POLICY_ID, canonical_entry_order

_T = TypeVar("_T")


@dataclass(frozen=True)
class ScheduledEntry:
    """One admitted entry at its canonical dispatch position."""

    plan_entry_id: str
    run_id: str
    dispatch_ordinal: int


@dataclass(frozen=True)
class BatchSchedule:
    """A deterministic, schedule-independent dispatch decision for one plan.

    ``admitted_parallelism_ceiling`` is the maximum concurrency the sealed plan's
    embedded isolation proof authorizes (one by default). The effective bound
    actually run is the downstream allocator's decision, no greater than this
    ceiling; it is not decided here.
    """

    plan_id: str
    plan_digest: str
    scheduling_policy_id: str
    admitted_parallelism_ceiling: int
    isolation_proof_ref: str | None
    entries: tuple[ScheduledEntry, ...]


def plan_batch_schedule(plan: AdmittedTrialPlanModel) -> BatchSchedule:
    """Compute the canonical dispatch order and admitted parallelism ceiling.

    The complete plan is revalidated before any per-entry consumption. The
    ceiling comes only from the plan's *embedded* isolation proof -- which the
    sealed ``plan_digest`` binds to the plan -- so a caller cannot inject a
    standalone or replayed proof to widen it. Serial (ceiling one) is the default
    whenever the plan carries no bounded-parallelism proof.
    """

    admitted = revalidate_admitted_trial_plan(plan)
    order = canonical_entry_order(admitted)
    scheduled = tuple(
        ScheduledEntry(plan_entry_id=entry_id, run_id=admitted.entries[entry_id].run_id, dispatch_ordinal=index)
        for index, entry_id in enumerate(order)
    )
    ceiling = 1
    proof_ref: str | None = None
    proof = admitted.isolation_proof
    if proof is not None:
        validate_scheduler_isolation_proof(admitted, proof)
        if proof.requested_parallelism > 1:
            ceiling = min(proof.requested_parallelism, len(scheduled))
            proof_ref = proof.proof_id
    return BatchSchedule(
        plan_id=admitted.plan_id,
        plan_digest=admitted.plan_digest,
        scheduling_policy_id=CANONICAL_ORDER_POLICY_ID,
        admitted_parallelism_ceiling=ceiling,
        isolation_proof_ref=proof_ref,
        entries=scheduled,
    )


def dispatch_batch_schedule(schedule: BatchSchedule, *, realize: Callable[[str], _T]) -> list[_T]:
    """Commit dispatch decisions in canonical order over the one-entry seam.

    One serialized coordinator calls ``realize`` once per scheduled entry, in
    canonical dispatch order, even when the caller's transport runs the resulting
    work concurrently (SVR-031). ``realize`` is the caller's binding to
    :func:`realize_admitted_trial_entry` (or an equivalent one-entry executor);
    live leasing and concurrent execution remain the caller's responsibility.
    Results are returned in dispatch order.
    """

    return [realize(entry.plan_entry_id) for entry in schedule.entries]


def build_batch_execution_receipt(
    schedule: BatchSchedule,
    plan_entry_id: str,
    *,
    receipt_id: str,
    execution_attempt_id: str,
    trial_outcome: TrialOutcome,
    cleanup_receipt_ref: str,
    effective_parallelism: int = 1,
    lease_evidence_refs: Sequence[str] = (),
    isolation_proof_ref: str | None = None,
    operation_refs: Sequence[str] = (),
    attempt_deadline: str | None = None,
) -> BatchExecutionReceiptModel:
    """Record one attempt's evidence, binding it to this schedule's decision.

    ``effective_parallelism`` and ``lease_evidence_refs`` are the downstream
    allocator's decision and its live lease evidence; the effective bound cannot
    exceed the schedule's admitted ceiling. For a bounded-parallel attempt the
    isolation proof reference defaults to the schedule's admitted proof.
    """

    scheduled = next((entry for entry in schedule.entries if entry.plan_entry_id == plan_entry_id), None)
    if scheduled is None:
        raise ValueError("plan_entry_id is not part of the batch schedule")
    if effective_parallelism > schedule.admitted_parallelism_ceiling:
        raise ValueError("effective_parallelism cannot exceed the schedule's admitted parallelism ceiling")
    parallel = effective_parallelism > 1
    if parallel and isolation_proof_ref is None:
        isolation_proof_ref = schedule.isolation_proof_ref
    return BatchExecutionReceiptModel(
        receipt_id=receipt_id,
        plan_id=schedule.plan_id,
        plan_digest=schedule.plan_digest,
        plan_entry_id=plan_entry_id,
        run_id=scheduled.run_id,
        execution_attempt_id=execution_attempt_id,
        dispatch_ordinal=scheduled.dispatch_ordinal,
        scheduling_policy_id=schedule.scheduling_policy_id,
        effective_parallelism=effective_parallelism,
        isolation_proof_ref=isolation_proof_ref if parallel else None,
        lease_evidence_refs=list(lease_evidence_refs) if parallel else [],
        attempt_deadline=attempt_deadline,
        trial_outcome=trial_outcome,
        operation_refs=list(operation_refs),
        cleanup_receipt_ref=cleanup_receipt_ref,
    )


__all__ = [
    "BatchSchedule",
    "CANONICAL_ORDER_POLICY_ID",
    "ScheduledEntry",
    "build_batch_execution_receipt",
    "dispatch_batch_schedule",
    "plan_batch_schedule",
]
