"""Self-consistency oracle for the participant-runtime trace predicates.

This file is NOT a test of a production participant-runtime subsystem. The
predicates below (`ValidTrace`, `MonotoneSequence`, `RevisionDiscipline`,
`OrderDiscipline`, `ConflictOK`, `TimeManagementOK`) have no callers under
``src/`` or ``packages/`` — they are a closed, test-local executable encoding of
the trace predicates published in the participant-runtime formal spec. The suite
checks only that the encoding *discriminates*: each predicate accepts the
legitimate variants of a spec-conforming trace and rejects a targeted violation
while the other (non-targeted) predicates continue to hold.

Spec mapping:
- `ValidTrace`, `MonotoneSequence`, `RevisionDiscipline`, and
  `OrderDiscipline`: specs/formal/participant-runtime/README.md:1265
- `ConflictOK` and `TimeManagementOK`:
  specs/formal/participant-runtime/README.md:2417

The acceptance direction is exercised only as a positive control alongside the
rejection tests (the ``*_accepts_supported_*_variants`` tests, plus the
``assert <other predicate>(mutated)`` lines inside each rejection test). A green
run here is NOT evidence that production code enforces these predicates; runtime
enforcement of participant-runtime behaviour is covered behaviourally by
``test_run_305_*``, ``test_run_306_*``, and ``test_run_311_*``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from hypothesis import given, settings
from hypothesis import strategies as st

RevisionSupport = Literal["known", "unknown", "unsupported"]
OrderStrength = Literal["display", "causal", "simultaneous", "serializable", "time-management"]
OrderBasis = Literal["wall-clock", "logical-clock", "happens-before", "scheduler", "backend-serialized"]
ConflictClass = Literal["none", "read-write", "write-write"]
ConflictPolicy = Literal["none", "serialize", "retry", "unsupported"]
IsolationClaim = Literal["none", "serializable"]
AtomicityScope = Literal["single-object", "multi-object"]
TimeMode = Literal["display", "pacing", "lookahead", "rollback", "devs", "fmi", "backend-serialized"]
TimeClaimStrength = Literal["display", "bounded", "exact"]

PROPERTY_SETTINGS = settings(max_examples=40, deadline=None)
REVISION_SUPPORT_VARIANTS: tuple[RevisionSupport, ...] = ("known", "unknown", "unsupported")
CONFLICT_VARIANTS: tuple[str, ...] = (
    "none",
    "read_write_serialize",
    "write_write_serialize",
    "write_write_retry",
    "unsupported_disclosed",
)
TIME_CONTEXT_VARIANTS: tuple[str, ...] = (
    "display",
    "backend_serialized",
    "lookahead",
    "pacing",
    "rollback",
    "devs",
    "fmi",
    "unsupported_disclosed",
)
INVALID_REVISION_VARIANTS: tuple[str, ...] = (
    "unknown_cites_prior",
    "unsupported_without_disclosure",
    "unsupported_produces_revision",
)
INVALID_CONFLICT_VARIANTS: tuple[str, ...] = (
    "retry_without_limit",
    "unsupported_exact_overclaim",
    "serializable_without_order",
)
INVALID_TIME_VARIANTS: tuple[str, ...] = (
    "lookahead_without_lookahead",
    "rollback_without_lineage",
    "unsupported_exact_overclaim",
)


@dataclass(frozen=True)
class StateRevision:
    state_address: str
    revision: int


@dataclass(frozen=True)
class StateWrite:
    state_address: str
    prior_revision: int | None
    new_revision: int | None
    new_digest: str | None
    support: RevisionSupport = "known"
    unsupported_update: bool = False


@dataclass(frozen=True)
class OrderClaim:
    strength: OrderStrength
    basis: OrderBasis | None


ORDER_CLAIM_VARIANTS: tuple[OrderClaim, ...] = (
    OrderClaim(strength="display", basis="wall-clock"),
    OrderClaim(strength="causal", basis="logical-clock"),
    OrderClaim(strength="simultaneous", basis="scheduler"),
    OrderClaim(strength="serializable", basis="backend-serialized"),
    OrderClaim(strength="time-management", basis="logical-clock"),
)


@dataclass(frozen=True)
class ParticipantEvent:
    event_id: str
    participant_address: str | None
    episode_id: str | None
    sequence_number: int | None
    state_writes: tuple[StateWrite, ...] = ()
    order_claims: tuple[OrderClaim, ...] = ()


@dataclass(frozen=True)
class AccessSet:
    event_id: str
    read_addresses: tuple[str, ...] = ()
    write_addresses: tuple[str, ...] = ()


@dataclass(frozen=True)
class JointActionRecord:
    joint_action_id: str
    member_event_ids: tuple[str, ...]
    access_sets: tuple[AccessSet, ...]
    conflict_class: ConflictClass
    conflict_policy: ConflictPolicy
    isolation: IsolationClaim
    atomicity_scope: AtomicityScope
    realized_order: tuple[str, ...] = ()
    rollback_event_ids: tuple[str, ...] = ()
    retry_limit: int | None = None
    unsupported_disclosure: bool = False
    exact_concurrency_claim: bool = False


@dataclass(frozen=True)
class TimeManagementContext:
    context_id: str
    mode: TimeMode
    claim_strength: TimeClaimStrength
    basis: OrderBasis | None
    clock_ref: str | None
    lookahead: int | None = None
    advance_by: int | None = None
    rollback_event_ids: tuple[str, ...] = ()
    unsupported_disclosure: bool = False
    backend_serialized: bool = False


@dataclass(frozen=True)
class RuntimeTrace:
    initial_revisions: tuple[StateRevision, ...]
    events: tuple[ParticipantEvent, ...]
    joint_actions: tuple[JointActionRecord, ...]
    time_contexts: tuple[TimeManagementContext, ...]


def _event_ids(trace: RuntimeTrace) -> set[str]:
    return {event.event_id for event in trace.events}


def _initial_revision_map(trace: RuntimeTrace) -> dict[str, set[int]]:
    revisions: dict[str, set[int]] = {}
    for revision in trace.initial_revisions:
        revisions.setdefault(revision.state_address, set()).add(revision.revision)
    return revisions


def _access_by_event(record: JointActionRecord) -> dict[str, AccessSet]:
    return {access.event_id: access for access in record.access_sets}


def _is_exact_permutation(values: tuple[str, ...], expected: set[str]) -> bool:
    return len(values) == len(expected) and set(values) == expected


def _actual_conflict_class(record: JointActionRecord) -> ConflictClass:
    access_sets = tuple(_access_by_event(record).values())
    read_write_conflict = False
    for left_index, left in enumerate(access_sets):
        left_reads = set(left.read_addresses)
        left_writes = set(left.write_addresses)
        for right in access_sets[left_index + 1 :]:
            right_reads = set(right.read_addresses)
            right_writes = set(right.write_addresses)
            if left_writes & right_writes:
                return "write-write"
            if (left_writes & right_reads) or (left_reads & right_writes):
                read_write_conflict = True
    return "read-write" if read_write_conflict else "none"


def _event_pair(trace: RuntimeTrace) -> tuple[str, str]:
    return (trace.events[0].event_id, trace.events[1].event_id)


def _with_first_write(trace: RuntimeTrace, write: StateWrite) -> RuntimeTrace:
    events = list(trace.events)
    events[0] = replace(events[0], state_writes=(write,))
    return replace(trace, events=tuple(events))


def with_revision_support_variant(trace: RuntimeTrace, support: RevisionSupport) -> RuntimeTrace:
    if support == "known":
        write = StateWrite(
            state_address="state.shared",
            prior_revision=0,
            new_revision=1,
            new_digest="sha256:shared:known",
        )
    elif support == "unknown":
        write = StateWrite(
            state_address="state.shared",
            prior_revision=None,
            new_revision=1,
            new_digest="sha256:shared:unknown",
            support="unknown",
        )
    else:
        write = StateWrite(
            state_address="state.shared",
            prior_revision=None,
            new_revision=None,
            new_digest=None,
            support="unsupported",
            unsupported_update=True,
        )
    return _with_first_write(trace, write)


def with_order_claim_variant(trace: RuntimeTrace, claim: OrderClaim) -> RuntimeTrace:
    events = list(trace.events)
    events[1] = replace(events[1], order_claims=(claim,))
    return replace(trace, events=tuple(events))


def with_conflict_variant(trace: RuntimeTrace, variant: str) -> RuntimeTrace:
    left_event_id, right_event_id = _event_pair(trace)
    if variant == "none":
        access_sets = (
            AccessSet(event_id=left_event_id, write_addresses=("state.shared",)),
            AccessSet(event_id=right_event_id, read_addresses=("state.other",), write_addresses=("state.local",)),
        )
        record = JointActionRecord(
            joint_action_id="joint-main",
            member_event_ids=(left_event_id, right_event_id),
            access_sets=access_sets,
            conflict_class="none",
            conflict_policy="none",
            isolation="none",
            atomicity_scope="single-object",
        )
    elif variant == "read_write_serialize":
        access_sets = (
            AccessSet(event_id=left_event_id, write_addresses=("state.shared",)),
            AccessSet(event_id=right_event_id, read_addresses=("state.shared",), write_addresses=("state.local",)),
        )
        record = JointActionRecord(
            joint_action_id="joint-main",
            member_event_ids=(left_event_id, right_event_id),
            access_sets=access_sets,
            conflict_class="read-write",
            conflict_policy="serialize",
            isolation="serializable",
            atomicity_scope="single-object",
            realized_order=(left_event_id, right_event_id),
        )
    elif variant == "write_write_serialize":
        access_sets = (
            AccessSet(event_id=left_event_id, write_addresses=("state.shared",)),
            AccessSet(event_id=right_event_id, write_addresses=("state.shared",)),
        )
        record = JointActionRecord(
            joint_action_id="joint-main",
            member_event_ids=(left_event_id, right_event_id),
            access_sets=access_sets,
            conflict_class="write-write",
            conflict_policy="serialize",
            isolation="serializable",
            atomicity_scope="multi-object",
            realized_order=(left_event_id, right_event_id),
        )
    elif variant == "write_write_retry":
        access_sets = (
            AccessSet(event_id=left_event_id, write_addresses=("state.shared",)),
            AccessSet(event_id=right_event_id, write_addresses=("state.shared",)),
        )
        record = JointActionRecord(
            joint_action_id="joint-main",
            member_event_ids=(left_event_id, right_event_id),
            access_sets=access_sets,
            conflict_class="write-write",
            conflict_policy="retry",
            isolation="none",
            atomicity_scope="single-object",
            rollback_event_ids=(left_event_id,),
            retry_limit=1,
        )
    else:
        access_sets = (
            AccessSet(event_id=left_event_id, write_addresses=("state.shared",)),
            AccessSet(event_id=right_event_id, write_addresses=("state.shared",)),
        )
        record = JointActionRecord(
            joint_action_id="joint-main",
            member_event_ids=(left_event_id, right_event_id),
            access_sets=access_sets,
            conflict_class="none",
            conflict_policy="unsupported",
            isolation="none",
            atomicity_scope="single-object",
            unsupported_disclosure=True,
            exact_concurrency_claim=False,
        )
    return replace(trace, joint_actions=(record,))


def with_time_context_variant(trace: RuntimeTrace, variant: str) -> RuntimeTrace:
    first_event_id = trace.events[0].event_id
    if variant == "display":
        context = TimeManagementContext(
            context_id="tm-main",
            mode="display",
            claim_strength="display",
            basis="wall-clock",
            clock_ref=None,
        )
    elif variant == "backend_serialized":
        context = TimeManagementContext(
            context_id="tm-main",
            mode="backend-serialized",
            claim_strength="bounded",
            basis="backend-serialized",
            clock_ref="clock.logical",
            backend_serialized=True,
        )
    elif variant == "lookahead":
        context = TimeManagementContext(
            context_id="tm-main",
            mode="lookahead",
            claim_strength="bounded",
            basis="logical-clock",
            clock_ref="clock.logical",
            lookahead=1,
        )
    elif variant == "pacing":
        context = TimeManagementContext(
            context_id="tm-main",
            mode="pacing",
            claim_strength="bounded",
            basis="logical-clock",
            clock_ref="clock.logical",
            advance_by=1,
        )
    elif variant == "rollback":
        context = TimeManagementContext(
            context_id="tm-main",
            mode="rollback",
            claim_strength="bounded",
            basis="logical-clock",
            clock_ref="clock.logical",
            rollback_event_ids=(first_event_id,),
        )
    elif variant in {"devs", "fmi"}:
        context = TimeManagementContext(
            context_id="tm-main",
            mode=variant,
            claim_strength="exact",
            basis="logical-clock",
            clock_ref="clock.logical",
        )
    else:
        context = TimeManagementContext(
            context_id="tm-main",
            mode="display",
            claim_strength="display",
            basis="logical-clock",
            clock_ref=None,
            unsupported_disclosure=True,
        )
    return replace(trace, time_contexts=(context,))


def valid_trace(trace: RuntimeTrace) -> bool:
    """Oracle for `ValidTrace(tr)` in the participant-runtime formal spec."""
    event_ids = [event.event_id for event in trace.events]
    return (
        bool(trace.events)
        and all(event_ids)
        and len(event_ids) == len(set(event_ids))
        and monotone_sequence(trace)
        and revision_discipline(trace)
        and order_discipline(trace)
        and all(conflict_ok(record, trace) for record in trace.joint_actions)
        and all(time_management_ok(context, trace) for context in trace.time_contexts)
    )


def monotone_sequence(trace: RuntimeTrace) -> bool:
    """Oracle for `MonotoneSequence(tr)` in the participant-runtime formal spec."""
    last_by_stream: dict[tuple[str, str], int] = {}
    for event in trace.events:
        participant_address = event.participant_address
        episode_id = event.episode_id
        sequence_number = event.sequence_number
        if participant_address is None and episode_id is None:
            if sequence_number is not None:
                return False
            continue
        if participant_address is None or episode_id is None or sequence_number is None:
            return False
        key = (participant_address, episode_id)
        previous = last_by_stream.get(key)
        if previous is not None and sequence_number <= previous:
            return False
        last_by_stream[key] = sequence_number
    return True


def revision_discipline(trace: RuntimeTrace) -> bool:
    """Oracle for `RevisionDiscipline(tr)` in the participant-runtime formal spec."""
    known_revisions = _initial_revision_map(trace)
    for event in trace.events:
        for write in event.state_writes:
            state_revisions = known_revisions.setdefault(write.state_address, set())
            produces_revision_or_digest = write.new_revision is not None or write.new_digest is not None

            if write.support == "known":
                if write.prior_revision is None or write.prior_revision not in state_revisions:
                    return False
                if not produces_revision_or_digest:
                    return False
            elif write.support == "unknown":
                if write.prior_revision is not None or not produces_revision_or_digest:
                    return False
            else:
                if not write.unsupported_update or produces_revision_or_digest:
                    return False

            if write.new_revision is not None:
                if write.prior_revision is not None and write.new_revision <= write.prior_revision:
                    return False
                if write.new_revision in state_revisions:
                    return False
                state_revisions.add(write.new_revision)
    return True


def order_discipline(trace: RuntimeTrace) -> bool:
    """Oracle for `OrderDiscipline(tr)` in the participant-runtime formal spec."""
    display_only_strengths = {"display"}
    for event in trace.events:
        for claim in event.order_claims:
            if claim.basis is None:
                return False
            if claim.basis == "wall-clock" and claim.strength not in display_only_strengths:
                return False
    return True


def conflict_ok(record: JointActionRecord, trace: RuntimeTrace) -> bool:
    """Oracle for `ConflictOK(j, tr)` in the participant-runtime formal spec."""
    trace_event_ids = _event_ids(trace)
    member_ids = set(record.member_event_ids)
    access_by_event = _access_by_event(record)
    actual_conflict = _actual_conflict_class(record)

    if not record.member_event_ids or not _is_exact_permutation(record.member_event_ids, member_ids):
        return False
    if not member_ids <= trace_event_ids:
        return False
    if not _is_exact_permutation(tuple(access.event_id for access in record.access_sets), member_ids):
        return False

    if record.unsupported_disclosure and record.exact_concurrency_claim:
        return False
    if not record.unsupported_disclosure and record.conflict_class != actual_conflict:
        return False
    if actual_conflict != "none" and record.conflict_class == "none" and not record.unsupported_disclosure:
        return False

    realized_order = tuple(record.realized_order)
    if realized_order and not _is_exact_permutation(realized_order, member_ids):
        return False
    if record.isolation == "serializable" and not realized_order:
        return False

    if record.conflict_policy == "serialize" and not _is_exact_permutation(realized_order, member_ids):
        return False
    if record.conflict_policy == "retry":
        if record.retry_limit is None or record.retry_limit < 0:
            return False
        if not set(record.rollback_event_ids) <= trace_event_ids:
            return False
    if record.conflict_policy == "unsupported":
        return record.unsupported_disclosure and not record.exact_concurrency_claim
    if record.conflict_policy == "none" and actual_conflict != "none":
        return False

    if record.atomicity_scope == "multi-object" and actual_conflict != "none" and not realized_order:
        return bool(record.rollback_event_ids)
    return True


def time_management_ok(context: TimeManagementContext, trace: RuntimeTrace) -> bool:
    """Oracle for `TimeManagementOK(tm, tr)` in the participant-runtime formal spec."""
    trace_event_ids = _event_ids(trace)

    if context.basis is None:
        return False
    if context.unsupported_disclosure and context.claim_strength == "exact":
        return False
    if context.basis == "wall-clock" and context.claim_strength != "display":
        return False
    if context.claim_strength in {"bounded", "exact"} and context.clock_ref is None:
        return False

    if context.mode == "backend-serialized":
        return context.backend_serialized and context.basis == "backend-serialized" and context.clock_ref is not None
    if context.mode == "lookahead":
        return context.lookahead is not None and context.lookahead >= 0 and context.clock_ref is not None
    if context.mode == "pacing":
        return context.advance_by is not None and context.advance_by > 0 and context.clock_ref is not None
    if context.mode == "rollback":
        return bool(context.rollback_event_ids) and set(context.rollback_event_ids) <= trace_event_ids
    if context.mode in {"devs", "fmi"}:
        return context.clock_ref is not None and context.basis != "wall-clock"
    return True


@st.composite
def valid_traces(draw: st.DrawFn) -> RuntimeTrace:
    stream_length = draw(st.integers(min_value=2, max_value=5))
    sequence_numbers = sorted(
        draw(
            st.lists(
                st.integers(min_value=1, max_value=200), min_size=stream_length, max_size=stream_length, unique=True
            )
        )
    )
    participant_address = draw(st.sampled_from(("participants.alpha", "participants.bravo", "participants.charlie")))
    episode_id = draw(st.sampled_from(("episodes.main", "episodes.replay")))

    event_ids = tuple(f"evt-{index}-{sequence_number}" for index, sequence_number in enumerate(sequence_numbers))
    first_event = ParticipantEvent(
        event_id=event_ids[0],
        participant_address=participant_address,
        episode_id=episode_id,
        sequence_number=sequence_numbers[0],
        state_writes=(
            StateWrite(
                state_address="state.shared",
                prior_revision=0,
                new_revision=1,
                new_digest=f"sha256:shared:{sequence_numbers[0]}",
            ),
        ),
    )
    second_event = ParticipantEvent(
        event_id=event_ids[1],
        participant_address=participant_address,
        episode_id=episode_id,
        sequence_number=sequence_numbers[1],
        state_writes=(
            StateWrite(
                state_address="state.local",
                prior_revision=0,
                new_revision=1,
                new_digest=f"sha256:local:{sequence_numbers[1]}",
            ),
        ),
        order_claims=(OrderClaim(strength="causal", basis="logical-clock"),),
    )
    tail_events = tuple(
        ParticipantEvent(
            event_id=event_ids[index],
            participant_address=participant_address,
            episode_id=episode_id,
            sequence_number=sequence_numbers[index],
        )
        for index in range(2, stream_length)
    )
    events = (first_event, second_event, *tail_events)

    trace = RuntimeTrace(
        initial_revisions=(
            StateRevision(state_address="state.shared", revision=0),
            StateRevision(state_address="state.local", revision=0),
            StateRevision(state_address="state.other", revision=0),
        ),
        events=events,
        joint_actions=(
            JointActionRecord(
                joint_action_id="joint-main",
                member_event_ids=(event_ids[0], event_ids[1]),
                access_sets=(
                    AccessSet(event_id=event_ids[0], write_addresses=("state.shared",)),
                    AccessSet(event_id=event_ids[1], read_addresses=("state.other",), write_addresses=("state.local",)),
                ),
                conflict_class="none",
                conflict_policy="none",
                isolation="none",
                atomicity_scope="single-object",
            ),
        ),
        time_contexts=(
            TimeManagementContext(
                context_id="tm-main",
                mode="backend-serialized",
                claim_strength="bounded",
                basis="backend-serialized",
                clock_ref="clock.logical",
                backend_serialized=True,
            ),
        ),
    )
    trace = with_revision_support_variant(trace, draw(st.sampled_from(REVISION_SUPPORT_VARIANTS)))
    trace = with_order_claim_variant(trace, draw(st.sampled_from(ORDER_CLAIM_VARIANTS)))
    trace = with_conflict_variant(trace, draw(st.sampled_from(CONFLICT_VARIANTS)))
    return with_time_context_variant(trace, draw(st.sampled_from(TIME_CONTEXT_VARIANTS)))


def with_sequence_regression(trace: RuntimeTrace) -> RuntimeTrace:
    events = list(trace.events)
    events[1] = replace(events[1], sequence_number=events[0].sequence_number)
    return replace(trace, events=tuple(events))


def with_revision_violation(trace: RuntimeTrace) -> RuntimeTrace:
    bad_write = StateWrite(
        state_address="state.shared",
        prior_revision=999,
        new_revision=1,
        new_digest="sha256:shared:bad-prior",
    )
    return _with_first_write(trace, bad_write)


def with_invalid_revision_support_variant(trace: RuntimeTrace, variant: str) -> RuntimeTrace:
    if variant == "unknown_cites_prior":
        write = StateWrite(
            state_address="state.shared",
            prior_revision=0,
            new_revision=1,
            new_digest="sha256:shared:unknown-bad",
            support="unknown",
        )
    elif variant == "unsupported_without_disclosure":
        write = StateWrite(
            state_address="state.shared",
            prior_revision=None,
            new_revision=None,
            new_digest=None,
            support="unsupported",
            unsupported_update=False,
        )
    else:
        write = StateWrite(
            state_address="state.shared",
            prior_revision=None,
            new_revision=1,
            new_digest="sha256:shared:unsupported-bad",
            support="unsupported",
            unsupported_update=True,
        )
    return _with_first_write(trace, write)


def with_order_violation(trace: RuntimeTrace) -> RuntimeTrace:
    events = list(trace.events)
    events[1] = replace(events[1], order_claims=(OrderClaim(strength="causal", basis="wall-clock"),))
    return replace(trace, events=tuple(events))


def with_missing_order_basis(trace: RuntimeTrace) -> RuntimeTrace:
    events = list(trace.events)
    events[1] = replace(events[1], order_claims=(OrderClaim(strength="display", basis=None),))
    return replace(trace, events=tuple(events))


def with_conflicting_concurrent_writes(trace: RuntimeTrace) -> RuntimeTrace:
    joint = trace.joint_actions[0]
    access_sets = (
        replace(joint.access_sets[0], read_addresses=(), write_addresses=("state.shared",)),
        replace(joint.access_sets[1], read_addresses=(), write_addresses=("state.shared",)),
    )
    bad_joint = replace(
        joint,
        access_sets=access_sets,
        conflict_class="none",
        conflict_policy="none",
        realized_order=(),
        unsupported_disclosure=False,
        exact_concurrency_claim=True,
    )
    return replace(trace, joint_actions=(bad_joint,))


def with_invalid_joint_action_witnesses(trace: RuntimeTrace) -> RuntimeTrace:
    joint = trace.joint_actions[0]
    duplicate_order_joint = replace(
        joint,
        conflict_policy="serialize",
        isolation="serializable",
        realized_order=(joint.member_event_ids[0], joint.member_event_ids[1], joint.member_event_ids[1]),
    )
    missing_access_joint = replace(joint, access_sets=(joint.access_sets[0],))
    return replace(trace, joint_actions=(duplicate_order_joint, missing_access_joint))


def with_invalid_conflict_policy_variant(trace: RuntimeTrace, variant: str) -> RuntimeTrace:
    left_event_id, right_event_id = _event_pair(trace)
    access_sets = (
        AccessSet(event_id=left_event_id, write_addresses=("state.shared",)),
        AccessSet(event_id=right_event_id, write_addresses=("state.shared",)),
    )
    if variant == "retry_without_limit":
        record = JointActionRecord(
            joint_action_id="joint-main",
            member_event_ids=(left_event_id, right_event_id),
            access_sets=access_sets,
            conflict_class="write-write",
            conflict_policy="retry",
            isolation="none",
            atomicity_scope="single-object",
            rollback_event_ids=(left_event_id,),
            retry_limit=None,
        )
    elif variant == "unsupported_exact_overclaim":
        record = JointActionRecord(
            joint_action_id="joint-main",
            member_event_ids=(left_event_id, right_event_id),
            access_sets=access_sets,
            conflict_class="none",
            conflict_policy="unsupported",
            isolation="none",
            atomicity_scope="single-object",
            unsupported_disclosure=True,
            exact_concurrency_claim=True,
        )
    else:
        record = JointActionRecord(
            joint_action_id="joint-main",
            member_event_ids=(left_event_id, right_event_id),
            access_sets=access_sets,
            conflict_class="write-write",
            conflict_policy="serialize",
            isolation="serializable",
            atomicity_scope="single-object",
            realized_order=(),
        )
    return replace(trace, joint_actions=(record,))


def with_time_domain_violation(trace: RuntimeTrace) -> RuntimeTrace:
    bad_context = replace(
        trace.time_contexts[0],
        claim_strength="exact",
        basis="wall-clock",
        clock_ref=None,
        backend_serialized=False,
    )
    return replace(trace, time_contexts=(bad_context,))


def with_invalid_time_context_variant(trace: RuntimeTrace, variant: str) -> RuntimeTrace:
    first_event_id = trace.events[0].event_id
    if variant == "lookahead_without_lookahead":
        context = TimeManagementContext(
            context_id="tm-main",
            mode="lookahead",
            claim_strength="bounded",
            basis="logical-clock",
            clock_ref="clock.logical",
            lookahead=None,
        )
    elif variant == "rollback_without_lineage":
        context = TimeManagementContext(
            context_id="tm-main",
            mode="rollback",
            claim_strength="bounded",
            basis="logical-clock",
            clock_ref="clock.logical",
            rollback_event_ids=(),
        )
    else:
        context = TimeManagementContext(
            context_id="tm-main",
            mode="display",
            claim_strength="exact",
            basis="logical-clock",
            clock_ref="clock.logical",
            rollback_event_ids=(first_event_id,),
            unsupported_disclosure=True,
        )
    return replace(trace, time_contexts=(context,))


@PROPERTY_SETTINGS
@given(valid_traces())
def test_valid_trace_rejects_targeted_mutations(trace: RuntimeTrace) -> None:
    assert not valid_trace(with_sequence_regression(trace))
    assert not valid_trace(with_revision_violation(trace))
    assert not valid_trace(with_order_violation(trace))
    assert not valid_trace(with_conflicting_concurrent_writes(trace))
    assert not valid_trace(with_time_domain_violation(trace))


@PROPERTY_SETTINGS
@given(valid_traces())
def test_monotone_sequence_rejects_sequence_regression(trace: RuntimeTrace) -> None:
    mutated = with_sequence_regression(trace)

    assert not monotone_sequence(mutated)
    assert revision_discipline(mutated)
    assert order_discipline(mutated)
    assert all(conflict_ok(record, mutated) for record in mutated.joint_actions)
    assert all(time_management_ok(context, mutated) for context in mutated.time_contexts)


@PROPERTY_SETTINGS
@given(valid_traces(), st.sampled_from(REVISION_SUPPORT_VARIANTS))
def test_revision_discipline_accepts_known_unknown_and_unsupported_write_support(
    trace: RuntimeTrace,
    support: RevisionSupport,
) -> None:
    mutated = with_revision_support_variant(trace, support)

    assert valid_trace(mutated)
    assert revision_discipline(mutated)


@PROPERTY_SETTINGS
@given(valid_traces())
def test_revision_discipline_rejects_unknown_prior_revision(trace: RuntimeTrace) -> None:
    mutated = with_revision_violation(trace)

    assert monotone_sequence(mutated)
    assert not revision_discipline(mutated)
    assert order_discipline(mutated)
    assert all(conflict_ok(record, mutated) for record in mutated.joint_actions)
    assert all(time_management_ok(context, mutated) for context in mutated.time_contexts)


@PROPERTY_SETTINGS
@given(valid_traces(), st.sampled_from(INVALID_REVISION_VARIANTS))
def test_revision_discipline_rejects_invalid_disclosure_specific_writes(
    trace: RuntimeTrace,
    variant: str,
) -> None:
    mutated = with_invalid_revision_support_variant(trace, variant)

    assert monotone_sequence(mutated)
    assert not revision_discipline(mutated)
    assert order_discipline(mutated)
    assert all(conflict_ok(record, mutated) for record in mutated.joint_actions)
    assert all(time_management_ok(context, mutated) for context in mutated.time_contexts)


@PROPERTY_SETTINGS
@given(valid_traces(), st.sampled_from(ORDER_CLAIM_VARIANTS))
def test_order_discipline_accepts_supported_order_claim_strengths(
    trace: RuntimeTrace,
    claim: OrderClaim,
) -> None:
    mutated = with_order_claim_variant(trace, claim)

    assert valid_trace(mutated)
    assert order_discipline(mutated)


@PROPERTY_SETTINGS
@given(valid_traces())
def test_order_discipline_rejects_wall_clock_causality(trace: RuntimeTrace) -> None:
    mutated = with_order_violation(trace)

    assert monotone_sequence(mutated)
    assert revision_discipline(mutated)
    assert not order_discipline(mutated)
    assert all(conflict_ok(record, mutated) for record in mutated.joint_actions)
    assert all(time_management_ok(context, mutated) for context in mutated.time_contexts)


@PROPERTY_SETTINGS
@given(valid_traces())
def test_order_discipline_rejects_claim_without_declared_basis(trace: RuntimeTrace) -> None:
    mutated = with_missing_order_basis(trace)

    assert monotone_sequence(mutated)
    assert revision_discipline(mutated)
    assert not order_discipline(mutated)
    assert all(conflict_ok(record, mutated) for record in mutated.joint_actions)
    assert all(time_management_ok(context, mutated) for context in mutated.time_contexts)


@PROPERTY_SETTINGS
@given(valid_traces(), st.sampled_from(CONFLICT_VARIANTS))
def test_conflict_ok_accepts_supported_conflict_policy_variants(
    trace: RuntimeTrace,
    variant: str,
) -> None:
    mutated = with_conflict_variant(trace, variant)

    assert valid_trace(mutated)
    assert all(conflict_ok(record, mutated) for record in mutated.joint_actions)


@PROPERTY_SETTINGS
@given(valid_traces())
def test_conflict_ok_rejects_undisclosed_concurrent_write_conflict(trace: RuntimeTrace) -> None:
    mutated = with_conflicting_concurrent_writes(trace)

    assert monotone_sequence(mutated)
    assert revision_discipline(mutated)
    assert order_discipline(mutated)
    assert all(not conflict_ok(record, mutated) for record in mutated.joint_actions)
    assert all(time_management_ok(context, mutated) for context in mutated.time_contexts)


@PROPERTY_SETTINGS
@given(valid_traces(), st.sampled_from(INVALID_CONFLICT_VARIANTS))
def test_conflict_ok_rejects_invalid_policy_specific_records(
    trace: RuntimeTrace,
    variant: str,
) -> None:
    mutated = with_invalid_conflict_policy_variant(trace, variant)

    assert monotone_sequence(mutated)
    assert revision_discipline(mutated)
    assert order_discipline(mutated)
    assert all(not conflict_ok(record, mutated) for record in mutated.joint_actions)
    assert all(time_management_ok(context, mutated) for context in mutated.time_contexts)


@PROPERTY_SETTINGS
@given(valid_traces())
def test_conflict_ok_rejects_joint_action_witnesses_that_are_not_exact_permutations(
    trace: RuntimeTrace,
) -> None:
    mutated = with_invalid_joint_action_witnesses(trace)

    assert monotone_sequence(mutated)
    assert revision_discipline(mutated)
    assert order_discipline(mutated)
    assert all(not conflict_ok(record, mutated) for record in mutated.joint_actions)
    assert all(time_management_ok(context, mutated) for context in mutated.time_contexts)


@PROPERTY_SETTINGS
@given(valid_traces(), st.sampled_from(TIME_CONTEXT_VARIANTS))
def test_time_management_ok_accepts_supported_time_mode_variants(
    trace: RuntimeTrace,
    variant: str,
) -> None:
    mutated = with_time_context_variant(trace, variant)

    assert valid_trace(mutated)
    assert all(time_management_ok(context, mutated) for context in mutated.time_contexts)


@PROPERTY_SETTINGS
@given(valid_traces())
def test_time_management_ok_rejects_wall_clock_exact_time_claim(trace: RuntimeTrace) -> None:
    mutated = with_time_domain_violation(trace)

    assert monotone_sequence(mutated)
    assert revision_discipline(mutated)
    assert order_discipline(mutated)
    assert all(conflict_ok(record, mutated) for record in mutated.joint_actions)
    assert all(not time_management_ok(context, mutated) for context in mutated.time_contexts)


@PROPERTY_SETTINGS
@given(valid_traces(), st.sampled_from(INVALID_TIME_VARIANTS))
def test_time_management_ok_rejects_invalid_mode_specific_contexts(
    trace: RuntimeTrace,
    variant: str,
) -> None:
    mutated = with_invalid_time_context_variant(trace, variant)

    assert monotone_sequence(mutated)
    assert revision_discipline(mutated)
    assert order_discipline(mutated)
    assert all(conflict_ok(record, mutated) for record in mutated.joint_actions)
    assert all(not time_management_ok(context, mutated) for context in mutated.time_contexts)
