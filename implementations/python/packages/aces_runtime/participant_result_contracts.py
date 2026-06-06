"""Participant runtime result contract validation for runtime backends."""

from __future__ import annotations

from aces_contracts.diagnostics import Diagnostic
from aces_contracts.participant_behavior import (
    iter_participant_behavior_snapshot_violations,
    iter_participant_runtime_history_transition_violations,
)
from aces_contracts.participant_episode import iter_participant_episode_snapshot_violations
from aces_contracts.runtime_state import RuntimeSnapshot

from .diagnostics import _failure_diagnostic


def participant_episode_contract_diagnostics(
    snapshot: RuntimeSnapshot,
) -> list[Diagnostic]:
    """Validate participant-episode snapshot data against RUN-311 invariants.

    Delegates to ``iter_participant_episode_snapshot_violations`` so the
    manager apply path and the conformance semantic-check path share one
    source of truth for every invariant, and wraps each violation in a
    ``runtime.backend-contract-invalid`` diagnostic.
    """

    return [
        _failure_diagnostic("runtime.backend-contract-invalid", address, message)
        for address, message in iter_participant_episode_snapshot_violations(
            snapshot.participant_episode_results,
            snapshot.participant_episode_history,
        )
    ]


def participant_runtime_state_contract_diagnostics(
    snapshot: RuntimeSnapshot,
) -> list[Diagnostic]:
    """Validate RUN-305 participant state/history snapshot data.

    This combines the RUN-311 episode chain invariants with the RUN-305
    behavior-history snapshot integrity checks so backend apply results cannot
    persist participant histories whose public map shape, identity keys, event
    types, episode references, or metadata boundary are invalid.
    """

    violations = [
        *iter_participant_episode_snapshot_violations(
            snapshot.participant_episode_results,
            snapshot.participant_episode_history,
        ),
        *iter_participant_behavior_snapshot_violations(
            snapshot.participant_behavior_history,
            participant_episode_results=snapshot.participant_episode_results,
            participant_episode_history=snapshot.participant_episode_history,
            metadata=snapshot.metadata,
        ),
    ]
    return [
        _failure_diagnostic("runtime.backend-contract-invalid", address, message) for address, message in violations
    ]


def participant_runtime_history_transition_diagnostics(
    previous_snapshot: RuntimeSnapshot,
    next_snapshot: RuntimeSnapshot,
) -> list[Diagnostic]:
    """Validate append-only participant history preservation across an apply."""

    return [
        _failure_diagnostic("runtime.backend-contract-invalid", address, message)
        for address, message in iter_participant_runtime_history_transition_violations(
            previous_snapshot.participant_episode_history,
            next_snapshot.participant_episode_history,
            previous_snapshot.participant_behavior_history,
            next_snapshot.participant_behavior_history,
        )
    ]
