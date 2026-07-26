"""Reference participant runtime: RUN-311 episode lifecycle transitions.

Each control method advances the current ``participant_episode_results``
entry in lockstep with append-only history events, so the resulting
snapshot always satisfies ``iter_participant_episode_snapshot_violations``:
identity is stable across resets/restarts, history is append-only, and the
current result is the head of the history chain. Independent of the stub.
"""

from __future__ import annotations

from raes_backend_protocols.participant_runtime_base import BaseParticipantRuntime


class ReferenceParticipantRuntime(BaseParticipantRuntime):
    """In-process participant runtime driving RUN-311 transitions.

    Delegates the full episode lifecycle to ``BaseParticipantRuntime``. No
    domain side-effects are injected — this runtime is intended for reference
    and testing use where no real infrastructure is required.
    """
