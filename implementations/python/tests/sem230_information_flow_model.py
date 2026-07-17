"""Test-local bounded model for SEM-230.

This is falsification evidence for a finite domain, not production enforcement
and not a proof of universal noninterference.
"""

from __future__ import annotations

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


@dataclass(frozen=True)
class PolicyRevision:
    policy_id: str
    revision: str
    effective_order: int
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
    authorized: bool
    admitted: bool
    visible: bool
    marking_authorized: bool
    declassification_authorized: bool
    backend_supported: bool
    transformation_valid: bool


def _effective_policy(
    order: int,
    policies: tuple[PolicyRevision, ...],
) -> PolicyRevision | None:
    eligible = [policy for policy in policies if policy.effective_order <= order]
    return max(eligible, key=lambda policy: policy.effective_order, default=None)


def decide_crossing(
    crossing: Crossing,
    policies: tuple[PolicyRevision, ...],
) -> Decision:
    """Apply the bounded model's independent, deny-first crossing gates."""

    policy = _effective_policy(crossing.order, policies)
    if policy is None or crossing.policy_revision != policy.revision:
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
    policies: tuple[PolicyRevision, ...],
    *,
    participant: str,
    audience: str,
) -> tuple[tuple[int, str, str], ...]:
    """Project append-only visible occurrence identities in declared order."""

    visible: list[tuple[int, str, str]] = []
    for crossing in sorted(crossings, key=lambda candidate: candidate.order):
        if crossing.participant != participant or crossing.audience != audience:
            continue
        if decide_crossing(crossing, policies) is Decision.DISCLOSED:
            visible.append((crossing.order, crossing.source_ref, crossing.value))
    return tuple(visible)


def policy_noninterference_holds(
    *,
    left_runs: tuple[tuple[Crossing, ...], ...],
    right_runs: tuple[tuple[Crossing, ...], ...],
    policies: tuple[PolicyRevision, ...],
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
            policies,
            participant=participant,
            audience=audience,
        )
        for run in left_runs
    }
    right_support = {
        project_history(
            run,
            policies,
            participant=participant,
            audience=audience,
        )
        for run in right_runs
    }
    return left_support == right_support
