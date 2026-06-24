"""RUN-308 participant concurrency time-management validators."""

from __future__ import annotations

from collections.abc import Mapping

Violation = tuple[str, str]

TIME_CONTEXTS_KEY = "runtime.snapshot.time-management-contexts"


def time_contexts_violations(contexts: object, *, known_event_refs: set[str]) -> list[Violation]:
    violations: list[Violation] = []
    if not isinstance(contexts, Mapping):
        return [(TIME_CONTEXTS_KEY, "time_management_contexts must be a mapping")]
    for outer_key, context in contexts.items():
        locator = f"{TIME_CONTEXTS_KEY}.{outer_key}"
        if not isinstance(outer_key, str) or not outer_key:
            violations.append((TIME_CONTEXTS_KEY, "time_management_contexts keys must be non-empty strings"))
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
    violations.extend(_time_context_identity_violations(locator, outer_key, context.get("context_id")))

    mode = context.get("mode")
    claim_strength = context.get("claim_strength")
    basis = context.get("basis")
    clock_ref = context.get("clock_ref")
    unsupported = context.get("unsupported_disclosure") is True
    violations.extend(
        _time_context_claim_violations(
            locator,
            claim_strength=claim_strength,
            basis=basis,
            clock_ref=clock_ref,
            unsupported=unsupported,
        )
    )
    violations.extend(
        _time_context_mode_violations(
            locator,
            context,
            mode=mode,
            basis=basis,
            clock_ref=clock_ref,
            unsupported=unsupported,
            known_event_refs=known_event_refs,
        )
    )
    return violations


def _time_context_identity_violations(locator: str, outer_key: str, context_id: object) -> list[Violation]:
    if not isinstance(context_id, str) or not context_id:
        return [(locator, "time management context requires context_id")]
    if context_id != outer_key:
        return [(locator, f"time management context key {outer_key!r} does not match context_id")]
    return []


def _time_context_claim_violations(
    locator: str,
    *,
    claim_strength: object,
    basis: object,
    clock_ref: object,
    unsupported: bool,
) -> list[Violation]:
    violations: list[Violation] = []
    if unsupported and claim_strength == "exact":
        violations.append((locator, "unsupported time-management disclosure cannot carry an exact claim"))
    if basis == "wall_clock_only" and claim_strength != "display":
        violations.append((locator, "wall_clock_only time basis supports display claims only"))
    if claim_strength in {"bounded", "exact"} and not isinstance(clock_ref, str):
        violations.append((locator, "bounded or exact time-management claims require clock_ref"))
    return violations


def _time_context_mode_violations(
    locator: str,
    context: Mapping[object, object],
    *,
    mode: object,
    basis: object,
    clock_ref: object,
    unsupported: bool,
    known_event_refs: set[str],
) -> list[Violation]:
    violations: list[Violation] = []
    if mode == "backend_serialized" and _invalid_backend_serialized_context(context, basis, clock_ref):
        violations.append((locator, "backend_serialized mode requires serialized_backend_order basis and clock_ref"))
    if mode == "lookahead" and not isinstance(context.get("lookahead"), int):
        violations.append((locator, "lookahead mode requires lookahead"))
    if mode == "pacing" and not isinstance(context.get("advance_by"), int):
        violations.append((locator, "pacing mode requires advance_by"))
    if mode == "rollback":
        violations.extend(
            _rollback_time_context_violations(
                locator,
                context.get("rollback_event_refs", []),
                known_event_refs=known_event_refs,
            )
        )
    if mode in {"devs", "fmi"} and (not isinstance(clock_ref, str) or basis == "wall_clock_only"):
        violations.append((locator, "devs and fmi modes require a non-wall-clock basis and clock_ref"))
    if mode == "unsupported" and not unsupported:
        violations.append((locator, "unsupported time-management mode requires unsupported_disclosure"))
    return violations


def _invalid_backend_serialized_context(
    context: Mapping[object, object],
    basis: object,
    clock_ref: object,
) -> bool:
    return not (
        context.get("backend_serialized") is True and basis == "serialized_backend_order" and isinstance(clock_ref, str)
    )


def _rollback_time_context_violations(
    locator: str,
    rollback_refs: object,
    *,
    known_event_refs: set[str],
) -> list[Violation]:
    if not isinstance(rollback_refs, list) or not rollback_refs:
        return [(locator, "rollback mode requires rollback_event_refs")]
    return [
        (locator, f"rollback_event_ref {ref!r} does not resolve")
        for ref in rollback_refs
        if isinstance(ref, str) and ref and ref not in known_event_refs
    ]


__all__ = ("TIME_CONTEXTS_KEY", "time_contexts_violations")
