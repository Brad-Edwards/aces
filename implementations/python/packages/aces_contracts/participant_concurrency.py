"""RUN-308 participant concurrency runtime validators."""

from __future__ import annotations

from collections.abc import Iterator, Mapping

Violation = tuple[str, str]

_JOINT_ACTION_RECORDS_KEY = "runtime.snapshot.joint-action-records"
_TIME_CONTEXTS_KEY = "runtime.snapshot.time-management-contexts"


def iter_participant_concurrency_snapshot_violations(
    joint_action_records: object,
    time_management_contexts: object,
    *,
    participant_behavior_history: object = None,
    shared_state_records: object = None,
    shared_state_history: object = None,
) -> Iterator[Violation]:
    """Yield RUN-308 snapshot violations for joint action/time records."""

    known_event_refs = _known_behavior_event_refs(participant_behavior_history)
    known_state_refs = _known_shared_state_refs(shared_state_records, shared_state_history)
    known_time_context_refs = _known_mapping_keys(time_management_contexts)
    known_time_contexts = time_management_contexts if isinstance(time_management_contexts, Mapping) else {}
    violations: list[Violation] = []
    violations.extend(
        _joint_action_records_violations(
            joint_action_records,
            known_event_refs=known_event_refs,
            known_state_refs=known_state_refs,
            known_time_context_refs=known_time_context_refs,
            known_time_contexts=known_time_contexts,
        )
    )
    violations.extend(_time_contexts_violations(time_management_contexts, known_event_refs=known_event_refs))
    return iter(violations)


def iter_participant_concurrency_transition_violations(
    previous_joint_action_records: object,
    next_joint_action_records: object,
    previous_time_management_contexts: object,
    next_time_management_contexts: object,
) -> Iterator[Violation]:
    """Yield append-only violations for RUN-308 concurrency records."""

    yield from _append_only_mapping_violations(
        "joint_action_records",
        _JOINT_ACTION_RECORDS_KEY,
        previous_joint_action_records,
        next_joint_action_records,
    )
    yield from _append_only_mapping_violations(
        "time_management_contexts",
        _TIME_CONTEXTS_KEY,
        previous_time_management_contexts,
        next_time_management_contexts,
    )


def _known_behavior_event_refs(participant_behavior_history: object) -> set[str]:
    refs: set[str] = set()
    if not isinstance(participant_behavior_history, Mapping):
        return refs
    for history in participant_behavior_history.values():
        if not isinstance(history, list):
            continue
        for event in history:
            if not isinstance(event, Mapping):
                continue
            for field_name in ("event_id", "action_instance_id"):
                ref = event.get(field_name)
                if isinstance(ref, str) and ref:
                    refs.add(ref)
    return refs


def _known_shared_state_refs(shared_state_records: object, shared_state_history: object) -> set[str]:
    refs: set[str] = set()
    for candidate in (shared_state_records, shared_state_history):
        if isinstance(candidate, Mapping):
            refs.update(str(key) for key in candidate if isinstance(key, str) and key)
    return refs


def _known_mapping_keys(candidate: object) -> set[str]:
    if not isinstance(candidate, Mapping):
        return set()
    return {str(key) for key in candidate if isinstance(key, str) and key}


def _joint_action_records_violations(
    records: object,
    *,
    known_event_refs: set[str],
    known_state_refs: set[str],
    known_time_context_refs: set[str],
    known_time_contexts: Mapping[object, object],
) -> list[Violation]:
    violations: list[Violation] = []
    if not isinstance(records, Mapping):
        return [(_JOINT_ACTION_RECORDS_KEY, "joint_action_records must be a mapping")]
    for outer_key, record in records.items():
        locator = f"{_JOINT_ACTION_RECORDS_KEY}.{outer_key}"
        if not isinstance(outer_key, str) or not outer_key:
            violations.append((_JOINT_ACTION_RECORDS_KEY, "joint_action_records keys must be non-empty strings"))
        elif not isinstance(record, Mapping):
            violations.append((locator, "joint action record must be a mapping"))
        else:
            violations.extend(
                _joint_action_record_violations(
                    locator,
                    outer_key,
                    record,
                    known_event_refs=known_event_refs,
                    known_state_refs=known_state_refs,
                    known_time_context_refs=known_time_context_refs,
                    known_time_contexts=known_time_contexts,
                )
            )
    return violations


def _joint_action_record_violations(
    locator: str,
    outer_key: str,
    record: Mapping[object, object],
    *,
    known_event_refs: set[str],
    known_state_refs: set[str],
    known_time_context_refs: set[str],
    known_time_contexts: Mapping[object, object],
) -> list[Violation]:
    violations: list[Violation] = []
    joint_id = record.get("joint_action_set_id")
    if not isinstance(joint_id, str) or not joint_id:
        violations.append((locator, "joint action record requires joint_action_set_id"))
    elif joint_id != outer_key:
        violations.append((locator, f"joint action record key {outer_key!r} does not match joint_action_set_id"))

    member_refs = record.get("member_event_refs")
    access_sets = record.get("access_sets")
    if not isinstance(member_refs, list) or not member_refs:
        violations.append((locator, "joint action member_event_refs must be a non-empty list"))
        member_ref_set: set[str] = set()
    elif any(not isinstance(ref, str) or not ref for ref in member_refs):
        violations.append((locator, "joint action member_event_refs entries must be non-empty strings"))
        member_ref_set = {ref for ref in member_refs if isinstance(ref, str) and ref}
    elif len(set(member_refs)) != len(member_refs):
        violations.append((locator, "joint action member_event_refs must be unique"))
        member_ref_set = set(member_refs)
    else:
        member_ref_set = set(member_refs)
        missing = sorted(member_ref_set - known_event_refs)
        for ref in missing:
            violations.append((locator, f"joint action member_event_ref {ref!r} does not resolve to behavior history"))

    access_event_refs, access_violations = _joint_action_access_violations(
        locator,
        access_sets,
        known_state_refs=known_state_refs,
    )
    violations.extend(access_violations)
    if member_ref_set and not _exact_string_set(access_event_refs, member_ref_set):
        violations.append((locator, "joint action access_sets must cover member_event_refs exactly once"))

    realized_order = record.get("realized_order", [])
    if not isinstance(realized_order, list):
        violations.append((locator, "joint action realized_order must be a list"))
    elif member_ref_set and realized_order and not _exact_string_set(realized_order, member_ref_set):
        violations.append((locator, "joint action realized_order must be an exact permutation of member_event_refs"))

    conflict_policy = record.get("conflict_policy")
    conflict_class = record.get("conflict_class")
    unsupported = record.get("unsupported_disclosure") is True
    exact_claim = record.get("exact_concurrency_claim") is True
    actual_conflict = _actual_conflict(access_sets)
    violations.extend(
        _joint_action_conflict_violations(
            locator,
            conflict_class=conflict_class,
            conflict_policy=conflict_policy,
            actual_conflict=actual_conflict,
            realized_order=realized_order,
            unsupported=unsupported,
            exact_claim=exact_claim,
            retry_limit=record.get("retry_limit"),
            rollback_event_refs=record.get("rollback_event_refs", []),
            atomicity_scope=record.get("atomicity_scope"),
            isolation_guarantee=record.get("isolation_guarantee"),
        )
    )

    time_context_ref = record.get("time_management_context_ref")
    if isinstance(time_context_ref, str) and time_context_ref:
        if time_context_ref not in known_time_context_refs:
            violations.append((locator, f"time_management_context_ref {time_context_ref!r} does not resolve"))
        elif exact_claim:
            time_context = known_time_contexts.get(time_context_ref)
            if isinstance(time_context, Mapping) and time_context.get("claim_strength") != "exact":
                violations.append((locator, "exact concurrency claims require exact time-management context"))
    elif exact_claim:
        violations.append((locator, "exact concurrency claims require time_management_context_ref"))
    return violations


def _joint_action_access_violations(
    locator: str,
    access_sets: object,
    *,
    known_state_refs: set[str],
) -> tuple[list[str], list[Violation]]:
    event_refs: list[str] = []
    violations: list[Violation] = []
    if not isinstance(access_sets, list) or not access_sets:
        return event_refs, [(locator, "joint action access_sets must be a non-empty list")]
    for index, access in enumerate(access_sets):
        access_locator = f"{locator}.access_sets[{index}]"
        if not isinstance(access, Mapping):
            violations.append((access_locator, "joint action access set must be a mapping"))
            continue
        event_ref = access.get("member_event_ref")
        if not isinstance(event_ref, str) or not event_ref:
            violations.append((access_locator, "joint action access set requires member_event_ref"))
        else:
            event_refs.append(event_ref)
        for field_name in ("shared_state_read_refs", "shared_state_write_refs"):
            values = access.get(field_name, [])
            if not isinstance(values, list):
                violations.append((access_locator, f"{field_name} must be a list"))
                continue
            for state_ref in values:
                if not isinstance(state_ref, str) or not state_ref:
                    violations.append((access_locator, f"{field_name} entries must be non-empty strings"))
                elif state_ref not in known_state_refs:
                    violations.append((access_locator, f"{field_name} entry {state_ref!r} does not resolve"))
    return event_refs, violations


def _joint_action_conflict_violations(
    locator: str,
    *,
    conflict_class: object,
    conflict_policy: object,
    actual_conflict: str,
    realized_order: object,
    unsupported: bool,
    exact_claim: bool,
    retry_limit: object,
    rollback_event_refs: object,
    atomicity_scope: object,
    isolation_guarantee: object,
) -> list[Violation]:
    violations: list[Violation] = []
    has_realized_order = isinstance(realized_order, list) and bool(realized_order)
    if unsupported and exact_claim:
        violations.append((locator, "unsupported concurrency disclosure cannot carry an exact concurrency claim"))
    if conflict_policy == "unsupported":
        if not unsupported or exact_claim:
            violations.append(
                (locator, "unsupported conflict_policy requires unsupported_disclosure and no exact claim")
            )
        return violations
    if not unsupported and conflict_class != actual_conflict:
        violations.append((locator, "joint action conflict_class must match declared access-set conflicts"))
    if conflict_class == "none" and actual_conflict != "none":
        violations.append((locator, "joint action conflict_class cannot be none when access sets conflict"))
    if isolation_guarantee == "serializable" and not has_realized_order:
        violations.append((locator, "serializable joint action isolation requires realized_order"))
    if conflict_policy == "serialize" and not has_realized_order:
        violations.append((locator, "serialize conflict_policy requires realized_order"))
    if conflict_policy == "retry" and (not isinstance(retry_limit, int) or not rollback_event_refs):
        violations.append((locator, "retry conflict_policy requires retry_limit and rollback_event_refs"))
    if conflict_policy == "none" and actual_conflict != "none":
        violations.append((locator, "none conflict_policy is only valid when access sets do not conflict"))
    if (
        atomicity_scope == "multi_object"
        and actual_conflict != "none"
        and not (has_realized_order or rollback_event_refs)
    ):
        violations.append(
            (locator, "multi_object conflicting joint actions require realized_order or rollback_event_refs")
        )
    return violations


def _time_contexts_violations(contexts: object, *, known_event_refs: set[str]) -> list[Violation]:
    violations: list[Violation] = []
    if not isinstance(contexts, Mapping):
        return [(_TIME_CONTEXTS_KEY, "time_management_contexts must be a mapping")]
    for outer_key, context in contexts.items():
        locator = f"{_TIME_CONTEXTS_KEY}.{outer_key}"
        if not isinstance(outer_key, str) or not outer_key:
            violations.append((_TIME_CONTEXTS_KEY, "time_management_contexts keys must be non-empty strings"))
        elif not isinstance(context, Mapping):
            violations.append((locator, "time management context must be a mapping"))
        else:
            violations.extend(_time_context_violations(locator, outer_key, context, known_event_refs=known_event_refs))
    return violations


def _time_context_violations(
    locator: str,
    outer_key: str,
    context: Mapping[object, object],
    *,
    known_event_refs: set[str],
) -> list[Violation]:
    violations: list[Violation] = []
    context_id = context.get("context_id")
    if not isinstance(context_id, str) or not context_id:
        violations.append((locator, "time management context requires context_id"))
    elif context_id != outer_key:
        violations.append((locator, f"time management context key {outer_key!r} does not match context_id"))

    mode = context.get("mode")
    claim_strength = context.get("claim_strength")
    basis = context.get("basis")
    clock_ref = context.get("clock_ref")
    unsupported = context.get("unsupported_disclosure") is True
    if unsupported and claim_strength == "exact":
        violations.append((locator, "unsupported time-management disclosure cannot carry an exact claim"))
    if basis == "wall_clock_only" and claim_strength != "display":
        violations.append((locator, "wall_clock_only time basis supports display claims only"))
    if claim_strength in {"bounded", "exact"} and not isinstance(clock_ref, str):
        violations.append((locator, "bounded or exact time-management claims require clock_ref"))
    if mode == "backend_serialized" and (
        context.get("backend_serialized") is not True
        or basis != "serialized_backend_order"
        or not isinstance(clock_ref, str)
    ):
        violations.append((locator, "backend_serialized mode requires serialized_backend_order basis and clock_ref"))
    if mode == "lookahead" and not isinstance(context.get("lookahead"), int):
        violations.append((locator, "lookahead mode requires lookahead"))
    if mode == "pacing" and not isinstance(context.get("advance_by"), int):
        violations.append((locator, "pacing mode requires advance_by"))
    rollback_refs = context.get("rollback_event_refs", [])
    if mode == "rollback":
        if not isinstance(rollback_refs, list) or not rollback_refs:
            violations.append((locator, "rollback mode requires rollback_event_refs"))
        else:
            for ref in rollback_refs:
                if isinstance(ref, str) and ref and ref not in known_event_refs:
                    violations.append((locator, f"rollback_event_ref {ref!r} does not resolve"))
    if mode in {"devs", "fmi"} and (not isinstance(clock_ref, str) or basis == "wall_clock_only"):
        violations.append((locator, "devs and fmi modes require a non-wall-clock basis and clock_ref"))
    if mode == "unsupported" and not unsupported:
        violations.append((locator, "unsupported time-management mode requires unsupported_disclosure"))
    return violations


def _actual_conflict(access_sets: object) -> str:
    if not isinstance(access_sets, list):
        return "none"
    read_write_conflict = False
    for left_index, left in enumerate(access_sets):
        if not isinstance(left, Mapping):
            continue
        left_reads = _string_set(left.get("shared_state_read_refs", []))
        left_writes = _write_refs(left)
        for right in access_sets[left_index + 1 :]:
            if not isinstance(right, Mapping):
                continue
            right_reads = _string_set(right.get("shared_state_read_refs", []))
            right_writes = _write_refs(right)
            if left_writes & right_writes:
                return "write_write"
            if (left_writes & right_reads) or (left_reads & right_writes):
                read_write_conflict = True
    return "read_write" if read_write_conflict else "none"


def _write_refs(access: Mapping[object, object]) -> set[str]:
    refs = _string_set(access.get("shared_state_write_refs", []))
    refs.update(f"resource:{ref}" for ref in _string_set(access.get("exclusive_resource_refs", [])))
    return refs


def _string_set(values: object) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {value for value in values if isinstance(value, str) and value}


def _exact_string_set(values: object, expected: set[str]) -> bool:
    return isinstance(values, list) and len(values) == len(expected) and set(values) == expected


def _append_only_mapping_violations(
    field_name: str,
    address_prefix: str,
    previous_records: object,
    next_records: object,
) -> Iterator[Violation]:
    if not isinstance(previous_records, Mapping) or not isinstance(next_records, Mapping):
        return
    for record_id, previous_record in previous_records.items():
        if not isinstance(record_id, str) or not record_id:
            continue
        locator = f"{address_prefix}.{record_id}"
        if record_id not in next_records:
            yield (locator, f"{field_name} must be append-only; record {record_id!r} was removed")
        elif next_records[record_id] != previous_record:
            yield (locator, f"{field_name} must be append-only; record {record_id!r} changed")


__all__ = (
    "iter_participant_concurrency_snapshot_violations",
    "iter_participant_concurrency_transition_violations",
)
