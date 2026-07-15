"""Observation-boundary view-relation timeline compilation helpers."""

from typing import Any

_VISIBLE_VIEW_DISPOSITIONS = frozenset({"observable", "discovered", "inferred", "disclosed", "deceptive"})


def _initial_view_relation(*, view_rules: list[Any]) -> dict[str, str]:
    view_relation: dict[str, str] = {}
    for rule in view_rules:
        if not isinstance(rule, dict):
            continue
        information_ref = rule.get("information_ref")
        disposition = rule.get("disposition")
        if not information_ref or not disposition:
            continue
        ref = str(information_ref)
        view_relation[ref] = str(disposition)
    return view_relation


def _view_relation_refs(view_relation: dict[str, str], dispositions: set[str] | frozenset[str]) -> tuple[str, ...]:
    return tuple(ref for ref, disposition in sorted(view_relation.items()) if disposition in dispositions)


def _view_relation_snapshot(
    *,
    transition_id: str,
    effective_from: str,
    effective_order: int,
    view_relation: dict[str, str],
    transition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = {
        "transition_id": transition_id,
        "effective_from": effective_from,
        "effective_order": effective_order,
        "view_relation": dict(sorted(view_relation.items())),
        "visible_refs": _view_relation_refs(view_relation, _VISIBLE_VIEW_DISPOSITIONS),
        "hidden_refs": _view_relation_refs(view_relation, {"hidden"}),
        "evidence_only_refs": _view_relation_refs(view_relation, {"evidence_only"}),
        "disclosed_refs": _view_relation_refs(view_relation, {"disclosed"}),
        "discovered_refs": _view_relation_refs(view_relation, {"discovered"}),
        "inferred_refs": _view_relation_refs(view_relation, {"inferred"}),
        "concealed_refs": _view_relation_refs(view_relation, {"concealed"}),
        "deceptive_refs": _view_relation_refs(view_relation, {"deceptive"}),
    }
    if transition is not None:
        snapshot.update(
            {
                "transition_kind": str(transition.get("transition_kind") or ""),
                "information_ref": str(transition.get("information_ref") or ""),
                "history_event_type": str(transition.get("history_event_type") or ""),
                "action_instance_id": (
                    str(transition.get("action_instance_id"))
                    if transition.get("action_instance_id") is not None
                    else ""
                ),
            }
        )
    return snapshot


def _ordered_view_transitions(view_transitions: list[Any]) -> tuple[dict[str, Any], ...]:
    return tuple(
        sorted(
            (dict(transition) for transition in view_transitions if isinstance(transition, dict)),
            key=lambda transition: int(transition.get("effective_order", 0)),
        )
    )


def _compile_view_relation_timeline(
    *,
    view_rules: list[Any],
    view_transitions: list[Any],
) -> tuple[dict[str, Any], ...]:
    view_relation = _initial_view_relation(view_rules=view_rules)
    timeline: list[dict[str, Any]] = [
        _view_relation_snapshot(
            transition_id="initial",
            effective_from="initial",
            effective_order=-1,
            view_relation=view_relation,
        )
    ]
    for transition in _ordered_view_transitions(view_transitions):
        information_ref = transition.get("information_ref")
        to_disposition = transition.get("to_disposition")
        if not information_ref or not to_disposition:
            continue
        view_relation[str(information_ref)] = str(to_disposition)
        timeline.append(
            _view_relation_snapshot(
                transition_id=str(transition.get("transition_id") or ""),
                effective_from=str(transition.get("effective_from") or ""),
                effective_order=int(transition.get("effective_order", 0)),
                view_relation=view_relation,
                transition=transition,
            )
        )
    return tuple(timeline)
