"""Autonomous-execution reference context, clock/constraint binding, and time-binding checks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ._references import _resolve_section_ref
from ._types import (
    ParticipantBehaviorIssue,
    _BehaviorSpecificationReferenceContext,
)


@dataclass(frozen=True)
class _AutonomousExecutionReferenceContext:
    spec_name: str
    behavior_spec: object
    policy: object
    references: _BehaviorSpecificationReferenceContext
    participants: set[str]
    is_unresolved: Callable[[object], bool]


@dataclass(frozen=True)
class _AutonomousTimeBindings:
    clock: object | None
    progression: object | None
    cadence: object | None
    cadence_count: int


def _autonomous_issue(
    context: _AutonomousExecutionReferenceContext,
    code: str,
    ref: object,
    *,
    participant_name: str = "",
    message: str = "",
) -> ParticipantBehaviorIssue:
    return ParticipantBehaviorIssue(
        code=code,
        participant_name=participant_name,
        spec_name=context.spec_name,
        ref=str(ref),
        message=message,
    )


def _autonomous_declaration_issues(
    context: _AutonomousExecutionReferenceContext,
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    if not getattr(context.behavior_spec, "participant_refs", None):
        issues.append(
            _autonomous_issue(
                context,
                "participant.autonomous-explicit-participants-required",
                context.spec_name,
            )
        )
    required_features = {
        "action_contracts",
        "autonomous_execution",
        "behavior_history",
        "observation_boundaries",
        "temporal_contracts",
    }
    declared_features = {str(ref) for ref in getattr(context.behavior_spec, "backend_feature_support_refs", []) or []}
    for missing_feature in sorted(required_features - declared_features):
        issues.append(
            _autonomous_issue(
                context,
                "participant.autonomous-feature-requirement-missing",
                missing_feature,
            )
        )
    return issues


def _autonomous_action_issues(
    context: _AutonomousExecutionReferenceContext,
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    parent_actions = {str(ref) for ref in getattr(context.behavior_spec, "action_contract_refs", []) or []}
    action_candidates = getattr(context.policy, "action_candidates", None)
    action_refs = (
        [candidate.action_ref for candidate in action_candidates.values()]
        if action_candidates is not None
        else list(context.policy.action_order)
    )
    for action_ref in action_refs:
        if context.is_unresolved(action_ref):
            continue
        if action_ref not in parent_actions:
            issues.append(_autonomous_issue(context, "participant.autonomous-action-widens-parent", action_ref))
        for participant_name in sorted(context.participants):
            agent = context.references.agents_by_name[participant_name]
            agent_actions = {str(ref) for ref in getattr(agent, "actions", []) or []}
            if action_ref not in agent_actions:
                issues.append(
                    _autonomous_issue(
                        context,
                        "participant.autonomous-action-outside-participant",
                        action_ref,
                        participant_name=participant_name,
                    )
                )
    return issues


def _autonomous_boundary_issues(
    context: _AutonomousExecutionReferenceContext,
) -> list[ParticipantBehaviorIssue]:
    boundary_ref = context.policy.observation_boundary_ref
    if context.is_unresolved(boundary_ref):
        return []
    issues: list[ParticipantBehaviorIssue] = []
    parent_boundaries = {str(ref) for ref in getattr(context.behavior_spec, "observation_boundary_refs", []) or []}
    if boundary_ref not in parent_boundaries:
        issues.append(_autonomous_issue(context, "participant.autonomous-boundary-widens-parent", boundary_ref))
    for participant_name in sorted(context.participants):
        agent = context.references.agents_by_name[participant_name]
        agent_boundaries = {str(ref) for ref in getattr(agent, "observation_boundaries", []) or []}
        if boundary_ref not in agent_boundaries:
            issues.append(
                _autonomous_issue(
                    context,
                    "participant.autonomous-boundary-outside-participant",
                    boundary_ref,
                    participant_name=participant_name,
                )
            )
    return issues


def _autonomous_clock_binding_issues(
    context: _AutonomousExecutionReferenceContext,
) -> tuple[list[ParticipantBehaviorIssue], object | None, object | None]:
    policy = context.policy
    clock = context.references.clocks.get(policy.clock_ref)
    progression = context.references.time_progression_policies.get(policy.progression_policy_ref)
    issues: list[ParticipantBehaviorIssue] = []
    if clock is None and not context.is_unresolved(policy.clock_ref):
        issues.append(_autonomous_issue(context, "participant.autonomous-clock-unbound", policy.clock_ref))
    if progression is None and not context.is_unresolved(policy.progression_policy_ref):
        issues.append(
            _autonomous_issue(context, "participant.autonomous-progression-unbound", policy.progression_policy_ref)
        )
    elif progression is not None and getattr(progression, "clock_ref", None) != policy.clock_ref:
        issues.append(
            _autonomous_issue(
                context,
                "participant.autonomous-progression-clock-mismatch",
                policy.progression_policy_ref,
            )
        )
    return issues, clock, progression


def _autonomous_constraint_refs(
    context: _AutonomousExecutionReferenceContext,
    *,
    activity_policy: bool,
) -> list[str]:
    if activity_policy:
        return [*context.policy.work_window_refs, *context.policy.pause_window_refs]
    return list(context.policy.temporal_constraint_refs)


def _autonomous_window_subject_issues(
    context: _AutonomousExecutionReferenceContext,
    constraint_ref: str,
    constraint: object,
) -> list[ParticipantBehaviorIssue]:
    subjects = {str(ref) for ref in getattr(constraint, "subject_refs", ())}
    if context.spec_name in subjects or context.participants.issubset(subjects):
        return []
    return [
        _autonomous_issue(
            context,
            "participant.autonomous-activity-window-subject-mismatch",
            constraint_ref,
        )
    ]


def _autonomous_constraint_reference_issues(
    context: _AutonomousExecutionReferenceContext,
    constraint_ref: str,
    *,
    activity_policy: bool,
) -> tuple[list[ParticipantBehaviorIssue], object | None]:
    if context.is_unresolved(constraint_ref):
        return [], None
    constraint_name = _resolve_section_ref(
        constraint_ref,
        "temporal_constraints",
        context.references.temporal_constraints,
    )
    constraint = context.references.temporal_constraints.get(constraint_name) if constraint_name is not None else None
    if constraint is None:
        return [_autonomous_issue(context, "participant.autonomous-constraint-unbound", constraint_ref)], None

    issues: list[ParticipantBehaviorIssue] = []
    kind = getattr(getattr(constraint, "constraint_kind", None), "value", "")
    if activity_policy and kind != "window":
        issues.append(
            _autonomous_issue(
                context,
                "participant.autonomous-activity-window-kind-invalid",
                constraint_ref,
            )
        )
    if activity_policy and kind == "window":
        issues.extend(_autonomous_window_subject_issues(context, constraint_ref, constraint))
    if getattr(constraint, "clock_ref", None) != context.policy.clock_ref:
        issues.append(
            _autonomous_issue(
                context,
                "participant.autonomous-constraint-clock-mismatch",
                constraint_ref,
            )
        )
    return issues, constraint


def _autonomous_constraint_issues(
    context: _AutonomousExecutionReferenceContext,
) -> tuple[list[ParticipantBehaviorIssue], object | None, int]:
    issues: list[ParticipantBehaviorIssue] = []
    cadence = None
    cadence_count = 0
    activity_policy = getattr(context.policy, "profile", "participant-autonomous-execution/v1") in {
        "participant-autonomous-execution/v2",
        "participant-autonomous-execution/v3",
    }
    for constraint_ref in _autonomous_constraint_refs(context, activity_policy=activity_policy):
        reference_issues, constraint = _autonomous_constraint_reference_issues(
            context,
            constraint_ref,
            activity_policy=activity_policy,
        )
        issues.extend(reference_issues)
        if constraint is None:
            continue
        kind = getattr(getattr(constraint, "constraint_kind", None), "value", "")
        cadence_count += int(kind == "cadence")
        if kind == "cadence":
            cadence = constraint
    if not activity_policy and cadence_count != 1:
        issues.append(_autonomous_issue(context, "participant.autonomous-cadence-missing", context.policy.clock_ref))
    return issues, cadence, cadence_count


def _autonomous_time_binding_issues(
    context: _AutonomousExecutionReferenceContext,
) -> tuple[list[ParticipantBehaviorIssue], _AutonomousTimeBindings]:
    clock_issues, clock, progression = _autonomous_clock_binding_issues(context)
    constraint_issues, cadence, cadence_count = _autonomous_constraint_issues(context)
    bindings = _AutonomousTimeBindings(
        clock=clock,
        progression=progression,
        cadence=cadence,
        cadence_count=cadence_count,
    )
    return [*clock_issues, *constraint_issues], bindings
