"""Snapshot and transition invariants for ACT-604 information-state history."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from .contracts import (
    ParticipantInformationStateContextResolver,
    ParticipantInformationStateRecordModel,
    validate_participant_information_state_resolved_context,
)

Violation = tuple[str, str]


def iter_participant_information_state_snapshot_violations(
    information_state_history: object,
    *,
    information_state_context_resolver: ParticipantInformationStateContextResolver | None = None,
    context_scope: object | None = None,
    trusted_history: Mapping[str, list[dict[str, Any]]] | None = None,
) -> Iterator[Violation]:
    """Yield fixed-message violations for one first-class snapshot history."""

    address = "runtime.snapshot.information-state-history"
    if not isinstance(information_state_history, Mapping):
        yield address, "information_state_history must be a mapping"
        return

    known_event_ids: set[str] = set()
    known_state_refs: set[str] = set()
    trusted = trusted_history or {}
    for participant_address, raw_records in information_state_history.items():
        participant_path = f"{address}.{participant_address}"
        if not isinstance(participant_address, str) or not participant_address:
            yield address, "information_state_history keys must be non-empty strings"
            continue
        if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes, bytearray)):
            yield participant_path, "information_state_history entries must be lists"
            continue

        participant_prior_refs: set[str] = set()
        for index, raw_record in enumerate(raw_records):
            record_path = f"{participant_path}[{index}]"
            if not isinstance(raw_record, Mapping):
                yield record_path, "information-state history record must be a mapping"
                continue
            try:
                record = ParticipantInformationStateRecordModel.model_validate(raw_record)
            except ValidationError:
                yield record_path, "information-state history record failed contract validation"
                continue
            if record.participant_address != participant_address:
                yield record_path, ("information-state history map key must equal embedded participant_address")
            if record.event_id in known_event_ids:
                yield record_path, "information-state history event_id values must be unique"
            known_event_ids.add(record.event_id)
            if record.information_state_ref in known_state_refs:
                yield record_path, "information_state_ref values must be unique across snapshot history"
            known_state_refs.add(record.information_state_ref)

            missing_predecessors = sorted(set(record.predecessor_information_state_refs) - participant_prior_refs)
            if missing_predecessors:
                yield (
                    record_path,
                    ("predecessor_information_state_refs must resolve to earlier participant history records"),
                )
            if (
                record.supersedes_information_state_ref is not None
                and record.supersedes_information_state_ref not in participant_prior_refs
            ):
                yield (
                    record_path,
                    ("supersedes_information_state_ref must resolve to an earlier participant history record"),
                )
            participant_prior_refs.add(record.information_state_ref)
            trusted_records = trusted.get(participant_address, [])
            # The transition gate below this snapshot pass proves the exact
            # prior prefix. Contextual re-resolution is required only for the
            # newly appended suffix; a rewritten prefix is rejected by that
            # append-only gate before the apply result can be accepted.
            if index < len(trusted_records):
                continue
            if information_state_context_resolver is None:
                yield record_path, "participant information-state context resolver is required"
                continue
            try:
                validate_participant_information_state_resolved_context(
                    record,
                    information_state_context_resolver,
                    context_scope,
                )
            except (TypeError, ValueError):
                yield record_path, "information-state contextual validation failed"


def iter_participant_information_state_history_transition_violations(
    previous_history: Mapping[str, list[dict[str, Any]]],
    next_history: Mapping[str, list[dict[str, Any]]],
) -> Iterator[Violation]:
    """Require durable information-state histories to preserve an exact prefix."""

    address = "runtime.snapshot.information-state-history"
    for participant_address, previous_records in previous_history.items():
        participant_path = f"{address}.{participant_address}"
        if participant_address not in next_history:
            yield participant_path, "information-state history was removed"
            continue
        next_records = next_history[participant_address]
        if len(next_records) < len(previous_records):
            yield participant_path, ("information_state_history shrank and must be append-only")
            continue
        if next_records[: len(previous_records)] != previous_records:
            yield participant_path, "information_state_history must be append-only"


__all__ = (
    "iter_participant_information_state_history_transition_violations",
    "iter_participant_information_state_snapshot_violations",
)
