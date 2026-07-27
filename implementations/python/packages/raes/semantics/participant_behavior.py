"""Name-level participant behavior semantics (SEM-208/209/210)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ..participant_behavior_specification import tool_affordance_reference


@dataclass(frozen=True)
class ParticipantBehaviorReference:
    """Normalized reference from an agent to a behavior contract artifact."""

    participant_name: str
    reference_kind: str
    raw: str
    canonical_name: str


@dataclass(frozen=True)
class ParticipantBehaviorIssue:
    """Machine-readable participant behavior consistency issue."""

    code: str
    participant_name: str
    ref: str
    action_name: str = ""
    boundary_name: str = ""
    transition_id: str = ""
    spec_name: str = ""
    message: str = ""


@dataclass(frozen=True)
class ParticipantBehaviorAnalysis:
    """Result of analyzing participant behavior references."""

    references: tuple[ParticipantBehaviorReference, ...] = ()
    issues: tuple[ParticipantBehaviorIssue, ...] = ()

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)


@dataclass(frozen=True)
class _BehaviorSpecificationReferenceContext:
    participant_names: set[str]
    participant_roles_by_agent: Mapping[str, str]
    action_names: set[str]
    observation_boundary_names: set[str]
    outcome_rule_names: set[str]
    agents_by_name: Mapping[str, object]
    action_contracts: Mapping[str, object]
    observation_boundaries: Mapping[str, object]
    clocks: Mapping[str, object]
    time_progression_policies: Mapping[str, object]
    temporal_constraints: Mapping[str, object]
    objectives: Mapping[str, object]

    @property
    def participant_roles(self) -> set[str]:
        return set(self.participant_roles_by_agent.values())


def _action_references_for_agent(
    *,
    participant_name: str,
    action_names: list[object],
    action_contracts: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[list[ParticipantBehaviorReference], list[ParticipantBehaviorIssue]]:
    references: list[ParticipantBehaviorReference] = []
    issues: list[ParticipantBehaviorIssue] = []
    for action_name in action_names:
        if is_unresolved(action_name):
            continue
        if action_contracts and action_name not in action_contracts:
            issues.append(
                ParticipantBehaviorIssue(
                    code="participant.action-contract-unbound",
                    participant_name=participant_name,
                    ref=str(action_name),
                )
            )
            continue
        if action_name in action_contracts:
            references.append(
                ParticipantBehaviorReference(
                    participant_name=participant_name,
                    reference_kind="action_contract",
                    raw=str(action_name),
                    canonical_name=str(action_name),
                )
            )
    return references, issues


def _observation_boundary_references_for_agent(
    *,
    participant_name: str,
    boundary_names: list[object],
    observation_boundaries: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> tuple[list[ParticipantBehaviorReference], list[ParticipantBehaviorIssue]]:
    references: list[ParticipantBehaviorReference] = []
    issues: list[ParticipantBehaviorIssue] = []
    for boundary_name in boundary_names:
        if is_unresolved(boundary_name):
            continue
        if boundary_name not in observation_boundaries:
            issues.append(
                ParticipantBehaviorIssue(
                    code="participant.observation-boundary-unbound",
                    participant_name=participant_name,
                    ref=str(boundary_name),
                )
            )
            continue
        references.append(
            ParticipantBehaviorReference(
                participant_name=participant_name,
                reference_kind="observation_boundary",
                raw=str(boundary_name),
                canonical_name=str(boundary_name),
            )
        )
    return references, issues


def _interaction_references_for_action_contracts(
    *,
    action_contracts: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    for action_name, action_contract in action_contracts.items():
        for interaction in getattr(action_contract, "interactions", []) or []:
            for related_action in getattr(interaction, "related_actions", []) or []:
                if is_unresolved(related_action):
                    continue
                if related_action not in action_contracts:
                    issues.append(
                        ParticipantBehaviorIssue(
                            code="participant.interaction-action-unbound",
                            participant_name="",
                            action_name=str(action_name),
                            ref=str(related_action),
                        )
                    )
    return issues


def _observation_boundary_declared_refs(observation_boundary: object) -> set[str]:
    refs: set[str] = set()
    refs.update(str(ref) for ref in getattr(observation_boundary, "observable_refs", []) or [])
    refs.update(str(ref) for ref in getattr(observation_boundary, "hidden_refs", []) or [])
    refs.update(str(ref) for ref in getattr(observation_boundary, "evidence_refs", []) or [])
    return refs


def _observation_boundary_evidence_refs(observation_boundary: object) -> set[str]:
    return {str(ref) for ref in getattr(observation_boundary, "evidence_refs", []) or []}


def _is_bound_reference(
    ref: object,
    *,
    declared_refs: set[str],
    is_unresolved: Callable[[object], bool],
) -> bool:
    return is_unresolved(ref) or str(ref) in declared_refs


def _view_rule_visibility_issues(
    *,
    boundary_name: str,
    boundary: object,
    declared_refs: set[str],
    evidence_refs: set[str],
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    for rule in getattr(boundary, "view_rules", []) or []:
        information_ref = getattr(rule, "information_ref", "")
        if not _is_bound_reference(information_ref, declared_refs=declared_refs, is_unresolved=is_unresolved):
            issues.append(
                ParticipantBehaviorIssue(
                    code="participant.view-rule-ref-unbound",
                    participant_name="",
                    boundary_name=boundary_name,
                    ref=str(information_ref),
                )
            )
        for evidence_ref in getattr(rule, "evidence_refs", []) or []:
            if not _is_bound_reference(evidence_ref, declared_refs=evidence_refs, is_unresolved=is_unresolved):
                issues.append(
                    ParticipantBehaviorIssue(
                        code="participant.view-rule-evidence-unbound",
                        participant_name="",
                        boundary_name=boundary_name,
                        ref=str(evidence_ref),
                    )
                )
    return issues


def _view_transition_visibility_issues(
    *,
    boundary_name: str,
    boundary: object,
    declared_refs: set[str],
    evidence_refs: set[str],
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    for transition in getattr(boundary, "view_transitions", []) or []:
        information_ref = getattr(transition, "information_ref", "")
        transition_id = str(getattr(transition, "transition_id", ""))
        if not _is_bound_reference(information_ref, declared_refs=declared_refs, is_unresolved=is_unresolved):
            issues.append(
                ParticipantBehaviorIssue(
                    code="participant.view-transition-ref-unbound",
                    participant_name="",
                    boundary_name=boundary_name,
                    transition_id=transition_id,
                    ref=str(information_ref),
                )
            )
        for evidence_ref in getattr(transition, "evidence_refs", []) or []:
            if not _is_bound_reference(evidence_ref, declared_refs=evidence_refs, is_unresolved=is_unresolved):
                issues.append(
                    ParticipantBehaviorIssue(
                        code="participant.view-transition-evidence-unbound",
                        participant_name="",
                        boundary_name=boundary_name,
                        transition_id=transition_id,
                        ref=str(evidence_ref),
                    )
                )
    return issues


def _visibility_issues_for_observation_boundaries(
    *,
    observation_boundaries: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    for boundary_name, boundary in observation_boundaries.items():
        declared_refs = _observation_boundary_declared_refs(boundary)
        evidence_refs = _observation_boundary_evidence_refs(boundary)
        issues.extend(
            _view_rule_visibility_issues(
                boundary_name=str(boundary_name),
                boundary=boundary,
                declared_refs=declared_refs,
                evidence_refs=evidence_refs,
                is_unresolved=is_unresolved,
            )
        )
        issues.extend(
            _view_transition_visibility_issues(
                boundary_name=str(boundary_name),
                boundary=boundary,
                declared_refs=declared_refs,
                evidence_refs=evidence_refs,
                is_unresolved=is_unresolved,
            )
        )

    return issues


def _behavior_mode_issue(*, spec_name: str, behavior_mode: object) -> ParticipantBehaviorIssue | None:
    if not behavior_mode:
        return None
    try:
        from raes_contracts.controlled_vocabularies import validate_controlled_vocabulary_scope_values

        validate_controlled_vocabulary_scope_values("behavior_specifications.behavior_mode", [str(behavior_mode)])
    except ValueError as exc:
        return ParticipantBehaviorIssue(
            code="participant.behavior-spec-mode-ungoverned",
            participant_name="",
            spec_name=spec_name,
            ref=str(behavior_mode),
            message=str(exc),
        )
    return None


def _backend_feature_support_issue(*, spec_name: str, feature_ref: object) -> ParticipantBehaviorIssue | None:
    try:
        from raes_contracts.controlled_vocabularies import validate_controlled_vocabulary_value

        validation_errors: list[str] = []
        for vocabulary_id in (
            "participant-runtime-behavior-features",
            "participant-runtime-interaction-features",
        ):
            try:
                validate_controlled_vocabulary_value(vocabulary_id, str(feature_ref))
                return None
            except ValueError as exc:
                validation_errors.append(str(exc))
    except ValueError as exc:
        validation_errors = [str(exc)]
    return ParticipantBehaviorIssue(
        code="participant.behavior-spec-feature-ungoverned",
        participant_name="",
        spec_name=spec_name,
        ref=str(feature_ref),
        message="; ".join(validation_errors),
    )


def _evidence_contract_issue(*, spec_name: str, evidence_contract_ref: object) -> ParticipantBehaviorIssue | None:
    from raes_contracts.manifest_authority import (
        BACKEND_SUPPORTED_CONTRACT_IDS,
        PARTICIPANT_IMPLEMENTATION_SUPPORTED_CONTRACT_IDS,
        PROCESSOR_SUPPORTED_CONTRACT_IDS,
    )

    allowed_contract_ids = frozenset(
        [
            *BACKEND_SUPPORTED_CONTRACT_IDS,
            *PARTICIPANT_IMPLEMENTATION_SUPPORTED_CONTRACT_IDS,
            *PROCESSOR_SUPPORTED_CONTRACT_IDS,
        ]
    )
    if str(evidence_contract_ref) in allowed_contract_ids:
        return None
    return ParticipantBehaviorIssue(
        code="participant.behavior-spec-evidence-contract-unbound",
        participant_name="",
        spec_name=spec_name,
        ref=str(evidence_contract_ref),
        message="evidence_contract_refs must reference published processor, backend, or participant contracts",
    )


def _behavior_specification_named_ref_issues(
    *,
    spec_name: str,
    refs: list[object],
    known_names: set[str],
    code: str,
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    for ref in refs:
        if is_unresolved(ref):
            continue
        if str(ref) not in known_names:
            issues.append(
                ParticipantBehaviorIssue(
                    code=code,
                    participant_name="",
                    spec_name=spec_name,
                    ref=str(ref),
                )
            )
    return issues


def _behavior_specification_reference_issues(
    *,
    spec_name: str,
    behavior_spec: object,
    reference_context: _BehaviorSpecificationReferenceContext,
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    reference_sets = (
        (
            list(getattr(behavior_spec, "participant_refs", []) or []),
            reference_context.participant_names,
            "participant.behavior-spec-participant-unbound",
        ),
        (
            list(getattr(behavior_spec, "participant_role_refs", []) or []),
            reference_context.participant_roles,
            "participant.behavior-spec-role-unbound",
        ),
        (
            list(getattr(behavior_spec, "action_contract_refs", []) or []),
            reference_context.action_names,
            "participant.behavior-spec-action-unbound",
        ),
        (
            list(getattr(behavior_spec, "observation_boundary_refs", []) or []),
            reference_context.observation_boundary_names,
            "participant.behavior-spec-observation-boundary-unbound",
        ),
        (
            list(getattr(behavior_spec, "outcome_interpretation_rule_refs", []) or []),
            reference_context.outcome_rule_names,
            "participant.behavior-spec-outcome-rule-unbound",
        ),
    )
    issues: list[ParticipantBehaviorIssue] = []
    for refs, known_names, code in reference_sets:
        issues.extend(
            _behavior_specification_named_ref_issues(
                spec_name=spec_name,
                refs=refs,
                known_names=known_names,
                code=code,
                is_unresolved=is_unresolved,
            )
        )
    return issues


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


def _autonomous_progression_issues(
    context: _AutonomousExecutionReferenceContext,
    bindings: _AutonomousTimeBindings,
) -> list[ParticipantBehaviorIssue]:
    policy = context.policy
    progression_mode = getattr(getattr(bindings.progression, "advancement_mode", None), "value", "")
    clock_authority = getattr(getattr(bindings.clock, "authority_kind", None), "value", "")
    issues: list[ParticipantBehaviorIssue] = []
    if progression_mode == "externally_paced":
        issues.append(
            _autonomous_issue(
                context,
                "participant.autonomous-progression-driver-unsupported",
                policy.progression_policy_ref,
            )
        )
    if progression_mode in {"real_time", "dilated"} and clock_authority != "runtime":
        issues.append(
            _autonomous_issue(context, "participant.autonomous-clock-authority-unsupported", policy.clock_ref)
        )
    if bindings.cadence_count == 1 and bindings.cadence is not None:
        start = getattr(bindings.cadence, "start", None)
        start_tick = getattr(start, "tick", 0) if start is not None else 0
        if not isinstance(start_tick, int) or start_tick < 0:
            issues.append(
                _autonomous_issue(
                    context,
                    "participant.autonomous-cadence-unreachable",
                    policy.progression_policy_ref,
                )
            )
    issues.extend(_autonomous_stepped_cadence_issues(context, bindings, progression_mode))
    return issues


def _activity_timing_unreachable(
    policy: object,
    step_ticks: object,
) -> bool:
    minimum_ticks = policy.timing.minimum_ticks
    maximum_ticks = policy.timing.maximum_ticks
    return not (isinstance(step_ticks, int) and not minimum_ticks % step_ticks and not maximum_ticks % step_ticks)


def _cadence_unreachable(bindings: _AutonomousTimeBindings, step_ticks: object) -> bool:
    cadence_ticks = getattr(bindings.cadence, "cadence_ticks", None)
    start = getattr(bindings.cadence, "start", None)
    start_tick = getattr(start, "tick", 0) if start is not None else 0
    return not (
        isinstance(step_ticks, int)
        and isinstance(cadence_ticks, int)
        and start_tick >= 0
        and not start_tick % step_ticks
        and not cadence_ticks % step_ticks
    )


def _autonomous_stepped_issue_code(
    context: _AutonomousExecutionReferenceContext,
    bindings: _AutonomousTimeBindings,
) -> str | None:
    step_ticks = getattr(bindings.progression, "step_ticks", None)
    activity_policy = getattr(context.policy, "profile", "participant-autonomous-execution/v1") in {
        "participant-autonomous-execution/v2",
        "participant-autonomous-execution/v3",
    }
    if activity_policy and _activity_timing_unreachable(context.policy, step_ticks):
        return "participant.autonomous-activity-timing-unreachable"
    if (
        not activity_policy
        and bindings.cadence_count == 1
        and bindings.cadence is not None
        and _cadence_unreachable(bindings, step_ticks)
    ):
        return "participant.autonomous-cadence-unreachable"
    return None


def _autonomous_stepped_cadence_issues(
    context: _AutonomousExecutionReferenceContext,
    bindings: _AutonomousTimeBindings,
    progression_mode: str,
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    if progression_mode == "stepped":
        issue_code = _autonomous_stepped_issue_code(
            context,
            bindings,
        )
        if issue_code is not None:
            issues.append(
                _autonomous_issue(
                    context,
                    issue_code,
                    context.policy.progression_policy_ref,
                )
            )
    return issues


def _autonomous_non_evaluated_issues(
    context: _AutonomousExecutionReferenceContext,
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    for participant_name in sorted(context.participants):
        role = context.references.participant_roles_by_agent.get(participant_name, "")
        if role != "green":
            issues.append(
                _autonomous_issue(
                    context,
                    "participant.autonomous-non-evaluated-role-not-green",
                    role,
                    participant_name=participant_name,
                )
            )
        has_objective = any(
            getattr(objective, "agent", None) == participant_name
            for objective in context.references.objectives.values()
        )
        if has_objective:
            issues.append(
                _autonomous_issue(
                    context,
                    "participant.autonomous-non-evaluated-objective-authority",
                    participant_name,
                    participant_name=participant_name,
                )
            )
    has_widened_authority = getattr(context.behavior_spec, "outcome_interpretation_rule_refs", None) or getattr(
        context.behavior_spec, "authority_scope_refs", None
    )
    if has_widened_authority:
        issues.append(
            _autonomous_issue(
                context,
                "participant.autonomous-non-evaluated-authority-widening",
                context.spec_name,
            )
        )
    return issues


def _autonomous_declared_authority_issues(
    context: _AutonomousExecutionReferenceContext,
) -> list[ParticipantBehaviorIssue]:
    authority = context.policy.evaluation_authority
    issues: list[ParticipantBehaviorIssue] = []
    for objective_ref in authority.objective_refs:
        if context.is_unresolved(objective_ref):
            continue
        objective_name = _resolve_section_ref(objective_ref, "objectives", context.references.objectives)
        if objective_name is None:
            issues.append(
                _autonomous_issue(
                    context,
                    "participant.autonomous-evaluation-objective-unbound",
                    objective_ref,
                )
            )
    unsupported_authority_refs = (
        ("proof_producer_refs", authority.proof_producer_refs),
        ("score_authority_refs", authority.score_authority_refs),
        ("receipt_authority_refs", authority.receipt_authority_refs),
    )
    for field_name, refs in unsupported_authority_refs:
        for ref in refs:
            if not context.is_unresolved(ref):
                issues.append(
                    _autonomous_issue(
                        context,
                        "participant.autonomous-evaluation-authority-namespace-unsupported",
                        ref,
                        message=field_name,
                    )
                )
    return issues


def _autonomous_evaluation_issues(
    context: _AutonomousExecutionReferenceContext,
) -> list[ParticipantBehaviorIssue]:
    authority_mode = getattr(context.policy.evaluation_authority.mode, "value", "")
    if authority_mode == "none":
        return _autonomous_non_evaluated_issues(context)
    if authority_mode == "declared":
        return _autonomous_declared_authority_issues(context)
    return []


def _autonomous_execution_reference_issues(
    *,
    spec_name: str,
    behavior_spec: object,
    reference_context: _BehaviorSpecificationReferenceContext,
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    policy = getattr(behavior_spec, "autonomous_execution", None)
    if policy is None:
        return []
    context = _AutonomousExecutionReferenceContext(
        spec_name=spec_name,
        behavior_spec=behavior_spec,
        policy=policy,
        references=reference_context,
        participants=_tool_affordance_participants(behavior_spec, reference_context),
        is_unresolved=is_unresolved,
    )
    time_issues, bindings = _autonomous_time_binding_issues(context)
    return [
        *_autonomous_declaration_issues(context),
        *_autonomous_action_issues(context),
        *_autonomous_boundary_issues(context),
        *time_issues,
        *_autonomous_progression_issues(context, bindings),
        *_autonomous_evaluation_issues(context),
    ]


def _resolve_section_ref(
    ref: object,
    section: str,
    declarations: Mapping[str, object],
) -> str | None:
    """Resolve a bare or section-qualified reference to one SDL declaration."""

    if not isinstance(ref, str):
        return None
    if ref in declarations:
        return ref
    prefix = f"{section}."
    candidate = ref.removeprefix(prefix) if ref.startswith(prefix) else ""
    return candidate if candidate in declarations else None


def _tool_affordance_participants(
    behavior_spec: object,
    reference_context: _BehaviorSpecificationReferenceContext,
) -> set[str]:
    participants = {
        str(ref)
        for ref in getattr(behavior_spec, "participant_refs", []) or []
        if str(ref) in reference_context.participant_names
    }
    role_refs = {str(ref) for ref in getattr(behavior_spec, "participant_role_refs", []) or []}
    participants.update(
        participant_name
        for participant_name, role in reference_context.participant_roles_by_agent.items()
        if role in role_refs
    )
    return participants


def _tool_affordance_duplicate_issue(
    *,
    spec_name: str,
    affordance_id: str,
    tool_ref: object,
    action_refs: list[str],
    boundary_refs: list[str],
    seen_relations: dict[tuple[str, tuple[str, ...], tuple[str, ...]], str],
) -> ParticipantBehaviorIssue | None:
    signature = (str(tool_ref or ""), tuple(sorted(action_refs)), tuple(sorted(boundary_refs)))
    duplicate_of = seen_relations.get(signature)
    if duplicate_of is None:
        seen_relations[signature] = affordance_id
        return None
    return ParticipantBehaviorIssue(
        code="participant.tool-affordance-duplicate-relation",
        participant_name="",
        spec_name=spec_name,
        ref=affordance_id,
        message=duplicate_of,
    )


def _tool_affordance_action_issues(
    *,
    spec_name: str,
    affordance_id: str,
    action_ref: str,
    parent_actions: set[str],
    participants: set[str],
    agents_by_name: Mapping[str, object],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    if action_ref not in parent_actions:
        issues.append(
            ParticipantBehaviorIssue(
                code="participant.tool-affordance-action-widens-parent",
                participant_name="",
                spec_name=spec_name,
                ref=action_ref,
                action_name=affordance_id,
            )
        )
    for participant_name in sorted(participants):
        agent_actions = {str(ref) for ref in getattr(agents_by_name[participant_name], "actions", []) or []}
        if action_ref not in agent_actions:
            issues.append(
                ParticipantBehaviorIssue(
                    code="participant.tool-affordance-action-outside-participant",
                    participant_name=participant_name,
                    spec_name=spec_name,
                    ref=action_ref,
                    action_name=affordance_id,
                )
            )
    return issues


def _tool_affordance_boundary_issues(
    *,
    spec_name: str,
    affordance_id: str,
    boundary_ref: str,
    parent_boundaries: set[str],
    participants: set[str],
    agents_by_name: Mapping[str, object],
    observation_boundaries: Mapping[str, object],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    if boundary_ref not in parent_boundaries:
        issues.append(
            ParticipantBehaviorIssue(
                code="participant.tool-affordance-boundary-widens-parent",
                participant_name="",
                spec_name=spec_name,
                ref=boundary_ref,
                action_name=affordance_id,
            )
        )
    for participant_name in sorted(participants):
        agent_boundaries = {
            str(ref) for ref in getattr(agents_by_name[participant_name], "observation_boundaries", []) or []
        }
        if boundary_ref not in agent_boundaries:
            issues.append(
                ParticipantBehaviorIssue(
                    code="participant.tool-affordance-boundary-outside-participant",
                    participant_name=participant_name,
                    spec_name=spec_name,
                    ref=boundary_ref,
                    action_name=affordance_id,
                )
            )
    boundary = observation_boundaries.get(boundary_ref)
    if boundary is None:
        return issues
    binding_ref = tool_affordance_reference(spec_name, affordance_id)
    declared_refs = _observation_boundary_declared_refs(boundary)
    view_rule_refs = {str(getattr(rule, "information_ref", "")) for rule in getattr(boundary, "view_rules", []) or []}
    if binding_ref not in declared_refs or binding_ref not in view_rule_refs:
        issues.append(
            ParticipantBehaviorIssue(
                code="participant.tool-affordance-view-unclassified",
                participant_name="",
                spec_name=spec_name,
                ref=binding_ref,
                action_name=affordance_id,
                boundary_name=boundary_ref,
            )
        )
    return issues


def _resolved_reference_issues(
    refs: list[str],
    is_unresolved: Callable[[object], bool],
    build_issues: Callable[[str], list[ParticipantBehaviorIssue]],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    for ref in refs:
        if not is_unresolved(ref):
            issues.extend(build_issues(ref))
    return issues


def _tool_affordance_reference_issues(
    *,
    spec_name: str,
    behavior_spec: object,
    agents_by_name: Mapping[str, object],
    observation_boundaries: Mapping[str, object],
    reference_context: _BehaviorSpecificationReferenceContext,
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    parent_actions = {str(ref) for ref in getattr(behavior_spec, "action_contract_refs", []) or []}
    parent_boundaries = {str(ref) for ref in getattr(behavior_spec, "observation_boundary_refs", []) or []}
    participants = _tool_affordance_participants(behavior_spec, reference_context)
    seen_relations: dict[tuple[str, tuple[str, ...], tuple[str, ...]], str] = {}
    for affordance_id, binding in getattr(behavior_spec, "tool_affordances", {}).items():
        affordance_id = str(affordance_id)
        action_refs = [str(ref) for ref in getattr(binding, "action_contract_refs", []) or []]
        boundary_refs = [str(ref) for ref in getattr(binding, "observation_boundary_refs", []) or []]
        duplicate_issue = _tool_affordance_duplicate_issue(
            spec_name=spec_name,
            affordance_id=affordance_id,
            tool_ref=getattr(binding, "tool_ref", None),
            action_refs=action_refs,
            boundary_refs=boundary_refs,
            seen_relations=seen_relations,
        )
        if duplicate_issue is not None:
            issues.append(duplicate_issue)

        issues.extend(
            _resolved_reference_issues(
                action_refs,
                is_unresolved,
                lambda action_ref, affordance_id=affordance_id: _tool_affordance_action_issues(
                    spec_name=spec_name,
                    affordance_id=affordance_id,
                    action_ref=action_ref,
                    parent_actions=parent_actions,
                    participants=participants,
                    agents_by_name=agents_by_name,
                ),
            )
        )
        issues.extend(
            _resolved_reference_issues(
                boundary_refs,
                is_unresolved,
                lambda boundary_ref, affordance_id=affordance_id: _tool_affordance_boundary_issues(
                    spec_name=spec_name,
                    affordance_id=affordance_id,
                    boundary_ref=boundary_ref,
                    parent_boundaries=parent_boundaries,
                    participants=participants,
                    agents_by_name=agents_by_name,
                    observation_boundaries=observation_boundaries,
                ),
            )
        )
    return issues


def _behavior_specification_feature_issues(
    *,
    spec_name: str,
    behavior_spec: object,
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    for feature_ref in getattr(behavior_spec, "backend_feature_support_refs", []) or []:
        if is_unresolved(feature_ref):
            continue
        feature_issue = _backend_feature_support_issue(spec_name=spec_name, feature_ref=feature_ref)
        if feature_issue is not None:
            issues.append(feature_issue)
    return issues


def _behavior_specification_evidence_contract_issues(
    *,
    spec_name: str,
    behavior_spec: object,
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    for evidence_contract_ref in getattr(behavior_spec, "evidence_contract_refs", []) or []:
        if is_unresolved(evidence_contract_ref):
            continue
        evidence_issue = _evidence_contract_issue(
            spec_name=spec_name,
            evidence_contract_ref=evidence_contract_ref,
        )
        if evidence_issue is not None:
            issues.append(evidence_issue)
    return issues


def _behavior_specification_vocabulary_issues(
    *,
    spec_name: str,
    behavior_spec: object,
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    mode_issue = _behavior_mode_issue(
        spec_name=spec_name,
        behavior_mode=getattr(behavior_spec, "behavior_mode", None),
    )
    if mode_issue is not None:
        issues.append(mode_issue)
    from raes_contracts.controlled_vocabularies import validate_controlled_vocabulary_scope_values

    for field_name, scope, code in (
        (
            "ai_offensive_behavior_refs",
            "behavior_specifications.ai_offensive_behavior_refs",
            "participant.behavior-spec-ai-offensive-behavior-ungoverned",
        ),
        (
            "defensive_behavior_refs",
            "behavior_specifications.defensive_behavior_refs",
            "participant.behavior-spec-defensive-behavior-ungoverned",
        ),
        (
            "offensive_behavior_refs",
            "behavior_specifications.offensive_behavior_refs",
            "participant.behavior-spec-offensive-behavior-ungoverned",
        ),
    ):
        for ref in getattr(behavior_spec, field_name, []) or []:
            if is_unresolved(ref):
                continue
            try:
                validate_controlled_vocabulary_scope_values(scope, [str(ref)])
            except ValueError as exc:
                issues.append(
                    ParticipantBehaviorIssue(
                        code=code,
                        participant_name="",
                        spec_name=spec_name,
                        ref=str(ref),
                        message=str(exc),
                    )
                )
    issues.extend(
        _behavior_specification_feature_issues(
            spec_name=spec_name,
            behavior_spec=behavior_spec,
            is_unresolved=is_unresolved,
        )
    )
    issues.extend(
        _behavior_specification_evidence_contract_issues(
            spec_name=spec_name,
            behavior_spec=behavior_spec,
            is_unresolved=is_unresolved,
        )
    )
    return issues


def _behavior_specification_issues(
    behavior_specifications: Mapping[str, object],
    reference_context: _BehaviorSpecificationReferenceContext,
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    for spec_name, behavior_spec in behavior_specifications.items():
        normalized_spec_name = str(spec_name)
        issues.extend(
            _behavior_specification_reference_issues(
                spec_name=normalized_spec_name,
                behavior_spec=behavior_spec,
                reference_context=reference_context,
                is_unresolved=is_unresolved,
            )
        )
        issues.extend(
            _behavior_specification_vocabulary_issues(
                spec_name=normalized_spec_name,
                behavior_spec=behavior_spec,
                is_unresolved=is_unresolved,
            )
        )
        issues.extend(
            _autonomous_execution_reference_issues(
                spec_name=normalized_spec_name,
                behavior_spec=behavior_spec,
                reference_context=reference_context,
                is_unresolved=is_unresolved,
            )
        )
        issues.extend(
            _tool_affordance_reference_issues(
                spec_name=normalized_spec_name,
                behavior_spec=behavior_spec,
                agents_by_name=reference_context.agents_by_name,
                observation_boundaries=reference_context.observation_boundaries,
                reference_context=reference_context,
                is_unresolved=is_unresolved,
            )
        )
    autonomous_owner_by_participant: dict[str, str] = {}
    for spec_name, behavior_spec in behavior_specifications.items():
        if getattr(behavior_spec, "autonomous_execution", None) is None:
            continue
        participant_names = {
            str(ref)
            for ref in getattr(behavior_spec, "participant_refs", []) or []
            if str(ref) in reference_context.participant_names
        }
        for participant_name in sorted(participant_names):
            prior_owner = autonomous_owner_by_participant.setdefault(participant_name, str(spec_name))
            if prior_owner != str(spec_name):
                issues.append(
                    ParticipantBehaviorIssue(
                        code="participant.autonomous-participant-owner-conflict",
                        participant_name=participant_name,
                        spec_name=str(spec_name),
                        ref=prior_owner,
                    )
                )
    return issues


@dataclass(frozen=True)
class _ParticipantBehaviorSemanticRegistries:
    participant_roles_by_agent: Mapping[str, str]
    outcome_interpretation_rules: Mapping[str, object]
    clocks: Mapping[str, object]
    time_progression_policies: Mapping[str, object]
    temporal_constraints: Mapping[str, object]
    objectives: Mapping[str, object]

    @classmethod
    def from_keywords(
        cls,
        semantic_registries: Mapping[str, object],
    ) -> _ParticipantBehaviorSemanticRegistries:
        expected = {
            "participant_roles_by_agent",
            "outcome_interpretation_rules",
            "clocks",
            "time_progression_policies",
            "temporal_constraints",
            "objectives",
        }
        missing = expected - semantic_registries.keys()
        unexpected = semantic_registries.keys() - expected
        if missing or unexpected:
            details = []
            if missing:
                details.append(f"missing {', '.join(sorted(missing))}")
            if unexpected:
                details.append(f"unexpected {', '.join(sorted(unexpected))}")
            raise TypeError("invalid participant behavior semantic registries: " + "; ".join(details))
        return cls(
            participant_roles_by_agent=semantic_registries["participant_roles_by_agent"],
            outcome_interpretation_rules=semantic_registries["outcome_interpretation_rules"],
            clocks=semantic_registries["clocks"],
            time_progression_policies=semantic_registries["time_progression_policies"],
            temporal_constraints=semantic_registries["temporal_constraints"],
            objectives=semantic_registries["objectives"],
        )


def _behavior_reference_context(
    agents_by_name: Mapping[str, object],
    action_contracts: Mapping[str, object],
    observation_boundaries: Mapping[str, object],
    registries: _ParticipantBehaviorSemanticRegistries,
) -> _BehaviorSpecificationReferenceContext:
    return _BehaviorSpecificationReferenceContext(
        participant_names={str(name) for name in agents_by_name},
        participant_roles_by_agent=registries.participant_roles_by_agent,
        action_names={str(name) for name in action_contracts},
        observation_boundary_names={str(name) for name in observation_boundaries},
        outcome_rule_names={str(name) for name in registries.outcome_interpretation_rules},
        agents_by_name=agents_by_name,
        action_contracts=action_contracts,
        observation_boundaries=observation_boundaries,
        clocks=registries.clocks,
        time_progression_policies=registries.time_progression_policies,
        temporal_constraints=registries.temporal_constraints,
        objectives=registries.objectives,
    )


def analyze_participant_behavior(
    *,
    agents_by_name: Mapping[str, object],
    action_contracts: Mapping[str, object],
    observation_boundaries: Mapping[str, object],
    behavior_specifications: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
    **semantic_registries: object,
) -> ParticipantBehaviorAnalysis:
    """Validate and normalize participant action/observation references.

    ``agents.*.actions`` can stay as a legacy authoring affordance when no
    action-contract registry exists. Once a scenario declares
    ``action_contracts``, every authored action name must resolve to that
    governed registry so the compiler never treats raw names as behavior
    semantics.
    """

    references: list[ParticipantBehaviorReference] = []
    issues: list[ParticipantBehaviorIssue] = []
    registries = _ParticipantBehaviorSemanticRegistries.from_keywords(semantic_registries)
    reference_context = _behavior_reference_context(
        agents_by_name,
        action_contracts,
        observation_boundaries,
        registries,
    )

    for participant_name, agent in agents_by_name.items():
        action_references, action_issues = _action_references_for_agent(
            participant_name=participant_name,
            action_names=list(getattr(agent, "actions", []) or []),
            action_contracts=action_contracts,
            is_unresolved=is_unresolved,
        )
        boundary_references, boundary_issues = _observation_boundary_references_for_agent(
            participant_name=participant_name,
            boundary_names=list(getattr(agent, "observation_boundaries", []) or []),
            observation_boundaries=observation_boundaries,
            is_unresolved=is_unresolved,
        )
        references.extend(action_references)
        references.extend(boundary_references)
        issues.extend(action_issues)
        issues.extend(boundary_issues)

    issues.extend(
        _interaction_references_for_action_contracts(
            action_contracts=action_contracts,
            is_unresolved=is_unresolved,
        )
    )
    issues.extend(
        _visibility_issues_for_observation_boundaries(
            observation_boundaries=observation_boundaries,
            is_unresolved=is_unresolved,
        )
    )
    issues.extend(
        _behavior_specification_issues(
            behavior_specifications,
            reference_context,
            is_unresolved,
        )
    )

    return ParticipantBehaviorAnalysis(references=tuple(references), issues=tuple(issues))
