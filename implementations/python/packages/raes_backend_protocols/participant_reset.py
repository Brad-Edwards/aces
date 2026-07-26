"""Atomic batch-reset support for the in-memory participant runtime."""

from __future__ import annotations

from copy import deepcopy
from typing import Protocol

from raes_contracts.diagnostics import Diagnostic
from raes_contracts.participant_episode import ParticipantEpisodeResetRequest
from raes_contracts.runtime_state import ApplyResult, RuntimeSnapshot


class _AtomicResetRuntime(Protocol):
    _results: dict[str, dict[str, object]]
    _history: dict[str, list[dict[str, object]]]
    _episode_counter: dict[str, int]

    def reset(
        self,
        request: ParticipantEpisodeResetRequest,
        snapshot: RuntimeSnapshot,
    ) -> ApplyResult: ...


def reset_many_atomically(
    runtime: _AtomicResetRuntime,
    requests: tuple[ParticipantEpisodeResetRequest, ...],
    snapshot: RuntimeSnapshot,
) -> ApplyResult:
    """Apply all participant resets, restoring native state on any failure."""

    addresses = [request.participant_address for request in requests]
    if len(addresses) != len(set(addresses)):
        return ApplyResult(
            success=False,
            snapshot=snapshot,
            diagnostics=[
                Diagnostic(
                    code="runtime.participant-runtime.rejected",
                    domain="runtime",
                    address="runtime.participant-runtime",
                    message="coordinated reset participant addresses must be unique",
                )
            ],
        )
    checkpoint = (
        deepcopy(runtime._results),
        deepcopy(runtime._history),
        deepcopy(runtime._episode_counter),
    )
    working = snapshot
    diagnostics: list[Diagnostic] = []
    changed: list[str] = []
    try:
        for request in requests:
            result = runtime.reset(request, working)
            diagnostics.extend(result.diagnostics)
            if not result.success:
                runtime._results, runtime._history, runtime._episode_counter = checkpoint
                return ApplyResult(success=False, snapshot=snapshot, diagnostics=diagnostics)
            working = result.snapshot
            changed.extend(result.changed_addresses)
    except Exception:
        runtime._results, runtime._history, runtime._episode_counter = checkpoint
        raise
    return ApplyResult(
        success=True,
        snapshot=working,
        diagnostics=diagnostics,
        changed_addresses=list(dict.fromkeys(changed)),
    )
