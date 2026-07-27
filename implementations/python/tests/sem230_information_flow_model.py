"""Test-local bounded model for SEM-230.

This is falsification evidence for a finite domain, not production enforcement
and not a proof of universal noninterference.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class Label(str, Enum):
    PROPOSAL = "proposal"
    APPROVAL = "approval"
    DENIAL = "denial"
    DIRECTION = "direction"
    INTERVENTION = "intervention"
    HANDOFF = "handoff"
    OVERRIDE = "override"
    CANCELLATION = "cancellation"
    ADMISSION = "admission"
    REJECTION = "rejection"
    ATTEMPT = "attempt"
    RESULT = "result"
    DISCLOSURE = "disclosure"
    WITHHOLDING = "withholding"
    CONCEALMENT = "concealment"
    REVOCATION = "revocation"
    TRANSFORMATION = "transformation"
    POLICY_CHANGE = "policy-change"
    EVIDENCE = "evidence"
    AUDIT = "audit"


class CrossingKind(str, Enum):
    DISCLOSURE = "disclosure"
    CONCEALMENT = "concealment"
    REVOCATION = "revocation"
    TRANSFORMATION = "transformation"


class Decision(str, Enum):
    DISCLOSED = "disclosed"
    WITHHELD = "withheld"


class ParticipantMemoryScope(str, Enum):
    EPISODE_LOCAL_RESET = "episode_local_reset"
    PERSISTENT_ACROSS_EPISODES = "persistent_across_episodes"


@dataclass(frozen=True)
class ProjectionPolicyDecision:
    policy_id: str
    revision: str
    decision_ref: str
    decision_cut_ref: str
    visible_low_refs: frozenset[str]
    permitted_declassifications: frozenset[str]


@dataclass(frozen=True)
class Crossing:
    participant: str
    audience: str
    order: int
    kind: CrossingKind
    label: Label
    source_ref: str
    value: str
    policy_revision: str
    policy_decision_ref: str
    decision_cut_ref: str
    authorized: bool
    admitted: bool
    visible: bool
    marking_authorized: bool
    declassification_authorized: bool
    backend_supported: bool
    transformation_valid: bool


def _exact_policy_decision(
    crossing: Crossing,
    policy_decisions: tuple[ProjectionPolicyDecision, ...],
) -> ProjectionPolicyDecision | None:
    matches = [
        decision
        for decision in policy_decisions
        if decision.decision_cut_ref == crossing.decision_cut_ref
        and decision.decision_ref == crossing.policy_decision_ref
        and decision.revision == crossing.policy_revision
    ]
    if len(matches) > 1:
        raise ValueError("policy authority returned multiple decisions for one exact state cut")
    return matches[0] if matches else None


def decide_crossing(
    crossing: Crossing,
    policy_decisions: tuple[ProjectionPolicyDecision, ...],
) -> Decision:
    """Apply the bounded model's independent, deny-first crossing gates."""

    policy = _exact_policy_decision(crossing, policy_decisions)
    if policy is None:
        return Decision.WITHHELD
    if crossing.kind in {CrossingKind.CONCEALMENT, CrossingKind.REVOCATION}:
        return Decision.WITHHELD
    independent_gates = (
        crossing.authorized,
        crossing.admitted,
        crossing.visible,
        crossing.marking_authorized,
        crossing.backend_supported,
        crossing.transformation_valid,
    )
    if not all(independent_gates):
        return Decision.WITHHELD
    if crossing.source_ref in policy.visible_low_refs:
        return Decision.DISCLOSED
    if crossing.declassification_authorized and crossing.source_ref in policy.permitted_declassifications:
        return Decision.DISCLOSED
    return Decision.WITHHELD


def project_history(
    crossings: tuple[Crossing, ...],
    policy_decisions: tuple[ProjectionPolicyDecision, ...],
    *,
    participant: str,
    audience: str,
) -> tuple[tuple[int, str, str], ...]:
    """Project append-only visible occurrence identities in declared order."""

    visible: list[tuple[int, str, str]] = []
    for crossing in sorted(crossings, key=lambda candidate: candidate.order):
        if crossing.participant != participant or crossing.audience != audience:
            continue
        if decide_crossing(crossing, policy_decisions) is Decision.DISCLOSED:
            visible.append((crossing.order, crossing.source_ref, crossing.value))
    return tuple(visible)


def policy_noninterference_holds(
    *,
    left_runs: tuple[tuple[Crossing, ...], ...],
    right_runs: tuple[tuple[Crossing, ...], ...],
    policy_decisions: tuple[ProjectionPolicyDecision, ...],
    participant: str,
    audience: str,
) -> bool:
    """Compare finite support sets after the same policy projection.

    Callers supply low-equivalent bounded runs with the same admitted low input
    and permitted declassification schedules. This helper compares only the
    resulting support sets; it does not universalize beyond those runs.
    """

    left_support = {
        project_history(
            run,
            policy_decisions,
            participant=participant,
            audience=audience,
        )
        for run in left_runs
    }
    right_support = {
        project_history(
            run,
            policy_decisions,
            participant=participant,
            audience=audience,
        )
        for run in right_runs
    }
    return left_support == right_support


ProjectedHistory = tuple[tuple[int, str, str], ...]
ParticipantStrategy = Callable[[ProjectedHistory], str]


def participant_information_state(
    current_episode_history: ProjectedHistory,
    *,
    prior_delivered_history: ProjectedHistory,
    memory_scope: ParticipantMemoryScope,
    memory_reset_authority_ref: str | None,
) -> ProjectedHistory:
    """Apply the declared memory scope without equating reset with forgetting."""

    if memory_scope is ParticipantMemoryScope.EPISODE_LOCAL_RESET:
        if memory_reset_authority_ref is None:
            raise ValueError("episode_local_reset requires authoritative reset of every visible memory channel")
        return current_episode_history
    if memory_reset_authority_ref is not None:
        raise ValueError("persistent memory scope must not claim a reset authority")
    return (*prior_delivered_history, *current_episode_history)


def reactive_policy_noninterference_holds(
    *,
    left_runs: tuple[tuple[Crossing, ...], ...],
    right_runs: tuple[tuple[Crossing, ...], ...],
    policy_decisions: tuple[ProjectionPolicyDecision, ...],
    participant: str,
    audience: str,
    strategies: tuple[ParticipantStrategy, ...],
    prior_delivered_history: ProjectedHistory = (),
    memory_scope: ParticipantMemoryScope,
    memory_reset_authority_ref: str | None,
) -> bool:
    """Compare finite projected-history/choice supports for adaptive strategies.

    This quantifies only over the supplied finite run and strategy classes. It
    is bounded falsification evidence, not a universal proof.
    """

    def support(runs: tuple[tuple[Crossing, ...], ...], strategy: ParticipantStrategy):
        outcomes: set[tuple[ProjectedHistory, str]] = set()
        for run in runs:
            projected = project_history(
                run,
                policy_decisions,
                participant=participant,
                audience=audience,
            )
            information_state = participant_information_state(
                projected,
                prior_delivered_history=prior_delivered_history,
                memory_scope=memory_scope,
                memory_reset_authority_ref=memory_reset_authority_ref,
            )
            outcomes.add((information_state, strategy(information_state)))
        return outcomes

    return all(support(left_runs, strategy) == support(right_runs, strategy) for strategy in strategies)
