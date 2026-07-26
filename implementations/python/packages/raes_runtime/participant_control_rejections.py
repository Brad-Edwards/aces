"""Ordered rejection rules for RUN-310 supervisory mediation."""

from __future__ import annotations

from raes_processor.models import (
    MixedControlControllerStateRuntime,
    MixedControlTransitionRuntime,
    ParticipantBehaviorSpecificationRuntime,
)

from .participant_control_intents import ParticipantControlIntent

_ORDER_STRATEGY = "total-effective-order"


def participant_control_rejection_reason(
    specification: ParticipantBehaviorSpecificationRuntime,
    transition: MixedControlTransitionRuntime,
    state: MixedControlControllerStateRuntime,
    intent: ParticipantControlIntent,
    *,
    current_state: str,
    current_revision: int,
    target_rejection_reason: str | None,
) -> str | None:
    """Return the first rejection in the lifecycle's binding order."""

    checks = (
        _order_strategy_rejection(specification),
        _intent_policy_rejection(specification, intent),
        _state_revision_rejection(transition, intent, current_state, current_revision),
        _transition_policy_rejection(specification, transition),
        target_rejection_reason,
        _authority_status_rejection(state),
        _authority_window_rejection(state, transition),
    )
    return next((reason for reason in checks if reason is not None), None)


def _order_strategy_rejection(
    specification: ParticipantBehaviorSpecificationRuntime,
) -> str | None:
    return None if specification.mixed_control_order_strategy == _ORDER_STRATEGY else "unsupported-order-strategy"


def _intent_policy_rejection(
    specification: ParticipantBehaviorSpecificationRuntime,
    intent: ParticipantControlIntent,
) -> str | None:
    return None if intent.policy_revision == specification.mixed_control_policy_revision else "stale-policy"


def _state_revision_rejection(
    transition: MixedControlTransitionRuntime,
    intent: ParticipantControlIntent,
    current_state: str,
    current_revision: int,
) -> str | None:
    matches_current_state = (
        intent.expected_state_revision == current_revision
        and transition.expected_state_revision == current_revision
        and transition.from_state_address == current_state
    )
    return None if matches_current_state else "stale-state"


def _transition_policy_rejection(
    specification: ParticipantBehaviorSpecificationRuntime,
    transition: MixedControlTransitionRuntime,
) -> str | None:
    return None if transition.policy_revision == specification.mixed_control_policy_revision else "stale-policy"


def _authority_status_rejection(state: MixedControlControllerStateRuntime) -> str | None:
    return None if state.authority_status == "active" else "revoked-authority"


def _authority_window_rejection(
    state: MixedControlControllerStateRuntime,
    transition: MixedControlTransitionRuntime,
) -> str | None:
    state_is_current = state.valid_from_order <= transition.effective_order <= state.valid_until_order
    transition_is_current = transition.valid_from_order <= transition.effective_order <= transition.valid_until_order
    return None if state_is_current and transition_is_current else "late-authority"


__all__ = ("participant_control_rejection_reason",)
