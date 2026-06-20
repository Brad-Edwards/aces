"""Shared operational state runtime validators for RUN-307."""

from __future__ import annotations

from collections.abc import Iterator, Mapping

from ._participant_behavior_types import _RESERVED_RUNTIME_STATE_KEYS

_SHARED_STATE_RECORDS_KEY = "runtime.snapshot.shared-state-records"
_SHARED_STATE_HISTORY_KEY = "runtime.snapshot.shared-state-history"
_METADATA_KEY = "runtime.snapshot.metadata"
_BEHAVIOR_HISTORY_KEY = "runtime.snapshot.participant-behavior-history"
_VALID_ACCESS_KINDS = frozenset({"read", "write", "read_write"})
_REQUIRED_RECORD_FIELDS = (
    "state_address",
    "state_scope",
    "state_kind",
    "ordering_basis",
    "conflict_policy",
    "provenance",
)


def iter_participant_shared_state_snapshot_violations(
    shared_state_records: object,
    shared_state_history: object,
    *,
    participant_behavior_history: object = None,
    metadata: object = None,
) -> Iterator[tuple[str, str]]:
    """Yield RUN-307 shared-state snapshot violations."""

    yield from _iter_reserved_metadata_key_violations(metadata)
    known_addresses: set[str] = set()
    yield from _iter_shared_state_records(shared_state_records, known_addresses)
    yield from _iter_shared_state_history(shared_state_history, known_addresses)
    yield from _iter_behavior_shared_state_ref_violations(participant_behavior_history, known_addresses)


def iter_participant_shared_state_history_transition_violations(
    previous_shared_state_history: object,
    next_shared_state_history: object,
) -> Iterator[tuple[str, str]]:
    """Yield append-only violations for shared-state history transitions."""

    if not isinstance(previous_shared_state_history, Mapping) or not isinstance(next_shared_state_history, Mapping):
        return
    for state_address, previous_records in previous_shared_state_history.items():
        if not isinstance(state_address, str) or not state_address or not isinstance(previous_records, list):
            continue
        next_records = next_shared_state_history.get(state_address)
        locator = f"{_SHARED_STATE_HISTORY_KEY}.{state_address}"
        if not isinstance(next_records, list):
            yield (locator, f"shared_state_history must be append-only; state {state_address!r} history was removed")
            continue
        if len(next_records) < len(previous_records):
            yield (
                locator,
                (
                    f"shared_state_history must be append-only; state {state_address!r} history shrank "
                    f"from {len(previous_records)} to {len(next_records)} records"
                ),
            )
            continue
        for index, previous_record in enumerate(previous_records):
            if next_records[index] != previous_record:
                yield (
                    f"{locator}[{index}]",
                    f"shared_state_history must be append-only; existing record at index {index} changed",
                )


def _iter_reserved_metadata_key_violations(metadata: object) -> Iterator[tuple[str, str]]:
    if metadata is None:
        return
    if not isinstance(metadata, Mapping):
        yield (_METADATA_KEY, "RuntimeSnapshot.metadata must be a mapping")
        return
    for key in sorted(_RESERVED_RUNTIME_STATE_KEYS.intersection(str(item) for item in metadata)):
        yield (
            f"{_METADATA_KEY}.{key}",
            (
                f"RuntimeSnapshot.metadata must not contain {key!r}; "
                "participant runtime state/history must use first-class snapshot fields"
            ),
        )


def _iter_shared_state_records(records: object, known_addresses: set[str]) -> Iterator[tuple[str, str]]:
    if not isinstance(records, Mapping):
        yield (_SHARED_STATE_RECORDS_KEY, "shared_state_records must be a mapping")
        return
    for outer_key, record in records.items():
        locator = f"{_SHARED_STATE_RECORDS_KEY}.{outer_key}"
        if not isinstance(outer_key, str) or not outer_key:
            yield (_SHARED_STATE_RECORDS_KEY, "shared_state_records keys must be non-empty strings")
            continue
        if not isinstance(record, Mapping):
            yield (locator, "shared state record must be a mapping")
            continue
        yield from _iter_shared_state_record_violations(locator, outer_key, record)
        known_addresses.add(outer_key)
        state_address = record.get("state_address")
        if isinstance(state_address, str) and state_address:
            known_addresses.add(state_address)


def _iter_shared_state_history(history: object, known_addresses: set[str]) -> Iterator[tuple[str, str]]:
    if not isinstance(history, Mapping):
        yield (_SHARED_STATE_HISTORY_KEY, "shared_state_history must be a mapping")
        return
    for outer_key, records in history.items():
        locator = f"{_SHARED_STATE_HISTORY_KEY}.{outer_key}"
        if not isinstance(outer_key, str) or not outer_key:
            yield (_SHARED_STATE_HISTORY_KEY, "shared_state_history keys must be non-empty strings")
            continue
        if not isinstance(records, list):
            yield (locator, "shared_state_history entries must be lists")
            continue
        known_addresses.add(outer_key)
        for index, record in enumerate(records):
            record_locator = f"{locator}[{index}]"
            if not isinstance(record, Mapping):
                yield (record_locator, "shared state history record must be a mapping")
                continue
            yield from _iter_shared_state_record_violations(record_locator, outer_key, record)
            state_address = record.get("state_address")
            if isinstance(state_address, str) and state_address:
                known_addresses.add(state_address)


def _iter_shared_state_record_violations(
    locator: str,
    expected_address: str,
    record: Mapping[object, object],
) -> Iterator[tuple[str, str]]:
    missing = [field for field in _REQUIRED_RECORD_FIELDS if not _non_empty_string(record.get(field))]
    if missing:
        yield (locator, "shared state record is missing required fields: " + ", ".join(missing))
        return

    state_address = record["state_address"]
    if state_address != expected_address:
        yield (
            locator,
            f"shared state record outer key {expected_address!r} does not match state_address {state_address!r}",
        )

    if not (_non_empty_string(record.get("revision")) or _non_empty_string(record.get("digest"))):
        yield (locator, "shared state record requires revision or digest")

    accesses = record.get("accesses", [])
    if not isinstance(accesses, list):
        yield (locator, "shared state record accesses must be a list")
        return
    for index, access in enumerate(accesses):
        access_locator = f"{locator}.accesses[{index}]"
        if not isinstance(access, Mapping):
            yield (access_locator, "shared state access must be a mapping")
            continue
        yield from _iter_shared_state_access_violations(access_locator, state_address, access)


def _iter_shared_state_access_violations(
    locator: str,
    record_address: object,
    access: Mapping[object, object],
) -> Iterator[tuple[str, str]]:
    state_address = access.get("state_address")
    if not _non_empty_string(state_address):
        yield (locator, "shared state access state_address must be a non-empty string")
    elif state_address != record_address:
        yield (locator, f"shared state access state_address {state_address!r} does not match record state_address")

    access_kind = access.get("access_kind")
    if access_kind not in _VALID_ACCESS_KINDS:
        yield (locator, f"shared state access_kind {access_kind!r} is not supported")
        return
    if access_kind in {"read", "read_write"} and not (
        _non_empty_string(access.get("read_revision")) or _non_empty_string(access.get("read_digest"))
    ):
        yield (locator, "shared state read access requires read_revision or read_digest")
    if access_kind in {"write", "read_write"} and not (
        _non_empty_string(access.get("write_revision")) or _non_empty_string(access.get("write_digest"))
    ):
        yield (locator, "shared state write access requires write_revision or write_digest")


def _iter_behavior_shared_state_ref_violations(
    participant_behavior_history: object,
    known_addresses: set[str],
) -> Iterator[tuple[str, str]]:
    if participant_behavior_history is None or not isinstance(participant_behavior_history, Mapping):
        return
    for participant_address, history in participant_behavior_history.items():
        if not isinstance(participant_address, str) or not isinstance(history, list):
            continue
        for index, event in enumerate(history):
            if not isinstance(event, Mapping):
                continue
            refs = event.get("shared_state_refs", [])
            if not isinstance(refs, list):
                continue
            for ref in refs:
                if isinstance(ref, str) and ref and ref not in known_addresses:
                    yield (
                        f"{_BEHAVIOR_HISTORY_KEY}.{participant_address}[{index}].shared_state_refs",
                        (
                            f"participant behavior shared_state_refs entry {ref!r} does not resolve to "
                            "shared_state_records or shared_state_history"
                        ),
                    )


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


__all__ = (
    "iter_participant_shared_state_history_transition_violations",
    "iter_participant_shared_state_snapshot_violations",
)
