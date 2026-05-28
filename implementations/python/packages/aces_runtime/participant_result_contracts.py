"""Participant episode result contract validation for runtime backends."""

from __future__ import annotations

from aces_contracts.diagnostics import Diagnostic
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
