"""Cross-object validation helpers for trial cleanup contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class CleanupObligationLike(Protocol):
    obligation_id: str
    boundary_refs: list[str]
    action_kind: str
    triggers: list[str]
    requirement: str
    idempotency: str


class RetryPolicyLike(Protocol):
    after_effect_policy: str
    reset_obligation_refs: list[str]


def validate_reset_retry_obligations(
    cleanup_obligations: Mapping[str, CleanupObligationLike], retry_policy: RetryPolicyLike
) -> None:
    """Require reset retry policies to identify executable, scope-complete resets."""

    obligation_ids = set(cleanup_obligations)
    unknown_reset_refs = sorted(set(retry_policy.reset_obligation_refs) - obligation_ids)
    if unknown_reset_refs:
        raise ValueError(f"retry policy references unknown reset obligations: {', '.join(unknown_reset_refs)}")
    if retry_policy.after_effect_policy != "reset":
        return

    reset_obligations = [cleanup_obligations[obligation_id] for obligation_id in retry_policy.reset_obligation_refs]
    invalid_reset_refs = sorted(
        obligation.obligation_id
        for obligation in reset_obligations
        if obligation.action_kind != "reset"
        or "retry" not in obligation.triggers
        or obligation.requirement != "required"
    )
    if invalid_reset_refs:
        raise ValueError(
            "reset retry policy references obligations that are not required reset actions triggered by retry: "
            f"{', '.join(invalid_reset_refs)}"
        )

    affected_boundaries = {
        boundary_ref
        for obligation in cleanup_obligations.values()
        if obligation.idempotency != "idempotent"
        for boundary_ref in obligation.boundary_refs
    }
    reset_boundaries = {boundary_ref for obligation in reset_obligations for boundary_ref in obligation.boundary_refs}
    uncovered_boundaries = sorted(affected_boundaries - reset_boundaries)
    if uncovered_boundaries:
        raise ValueError(
            f"reset retry obligations do not cover non-idempotent effect boundaries: {', '.join(uncovered_boundaries)}"
        )
