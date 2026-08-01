"""Atomic participant-history state cuts for RUN-319 crossings."""

from __future__ import annotations

import hashlib
import json

from raes_contracts.runtime_state import RuntimeSnapshot


def expected_participant_history_heads(
    snapshot: RuntimeSnapshot,
    participant_address: str,
) -> dict[str, str | None]:
    """Bind every retained participant history that may affect observation."""

    def head(history: dict[str, list[dict[str, object]]]) -> str | None:
        events = history.get(participant_address, ())
        if not events:
            return None
        value = events[-1].get("event_id")
        if isinstance(value, str) and value:
            return value
        encoded = json.dumps(events[-1], sort_keys=True, separators=(",", ":"), default=str).encode()
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"

    return {
        f"participant_episode_history:{participant_address}": head(snapshot.participant_episode_history),
        f"participant_behavior_history:{participant_address}": head(snapshot.participant_behavior_history),
        f"participant_control_history:{participant_address}": head(snapshot.participant_control_history),
        f"participant_crossing_history:{participant_address}": head(snapshot.participant_crossing_history),
    }


__all__ = ["expected_participant_history_heads"]
