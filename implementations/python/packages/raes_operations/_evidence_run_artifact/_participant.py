"""Participant-proof and terminal-observation section builders for the evidence artifact."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from raes_operations._evidence_run_types import (
    TerminalSnapshot,
)


def _participant_proof_section(proof: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = proof["snapshot"]
    episodes = {addr: _redact_episode_state(state) for addr, state in snapshot.participant_episode_results.items()}
    return {
        "runtime": "libvirt-deterministic-participant-runtime",
        "lifecycle_clean": proof["lifecycle_clean"],
        "diagnostics": list(proof["diagnostics"]),
        "admitted_action_addresses": list(proof["admitted_action_addresses"]),
        "episode_states": episodes,
        # The participant runtime never received any visible/disclosed refs: the
        # admission surface exposes nothing of the internal or evaluator state.
        "participant_visible_refs": [],
        "participant_disclosed_refs": [],
        "structural_validation_note": (
            "Deep behavior-history and episode-snapshot invariant validation is performed by the issue #614 "
            "participant-runtime test suite (processor-layer iterators); this artifact records the libvirt "
            "participant-runtime lifecycle outcome."
        ),
    }


def _redact_episode_state(state: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        return {}
    keep = (
        "state_schema_version",
        "participant_address",
        "episode_id",
        "sequence_number",
        "status",
        "terminal_reason",
        "last_control_action",
    )
    return {key: state.get(key) for key in keep if key in state}


def _terminal_observation_section(snapshot: TerminalSnapshot) -> dict[str, Any]:
    behavior_history = {
        addr: _redact_behavior_history(events) for addr, events in snapshot.participant_behavior_history.items()
    }
    return {
        "form": "participant-projected-history",
        "taxonomy": {
            "taxonomy_id": "raes-behavioral-relations",
            "taxonomy_revision": "rev8",
            "non_claimed_relation_ids": [
                "participant-projected-history-equivalence",
                "epistemic-indistinguishability",
                "alternating-strategic-equivalence",
            ],
        },
        "observation_projection": {
            "subject": "the participant addressed by each behavior-history stream",
            "policy_ref": "participant-observation-boundary",
            "policy_revision": "participant-observation-envelope/v1",
            "redaction_scope": "Only the fields retained by _redact_behavior_history are disclosed.",
            "order_treatment": "Recorded participant sequence order is preserved.",
            "simultaneity_treatment": "No simultaneity equivalence is inferred from the serialized order.",
        },
        "evidence_boundary": (
            "The terminal snapshot's named participant behavior-history streams for this single run; "
            "no second execution or universal trace set is compared."
        ),
        "disclosure": (
            "The libvirt participant runtime emits a behavior-history event stream rather than a standalone SEM-210 "
            "observation envelope; the terminal participant view is reported as a bounded participant projection."
        ),
        "explicit_non_claims": [
            "This single projected record does not establish participant-projected-history-equivalence.",
            "It does not establish epistemic or strategic equivalence.",
        ],
        "behavior_history": behavior_history,
    }


def _redact_behavior_history(events: Sequence[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(events, Sequence):
        return out
    for event in events:
        if not isinstance(event, Mapping):
            continue
        out.append(
            {
                "event_type": event.get("event_type"),
                "action_instance_id": event.get("action_instance_id"),
                "action_contract_address": event.get("action_contract_address"),
                "observation_boundary_address": event.get("observation_boundary_address"),
            }
        )
    return out
