"""Name-level participant behavior semantics (SEM-208/209/210)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass


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
    participant_roles: set[str]
    action_names: set[str]
    observation_boundary_names: set[str]
    outcome_rule_names: set[str]


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
        from aces_contracts.controlled_vocabularies import validate_controlled_vocabulary_value

        validate_controlled_vocabulary_value("participant-decision-surface-modes", str(behavior_mode))
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
        from aces_contracts.controlled_vocabularies import validate_controlled_vocabulary_value

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
    from aces_contracts.manifest_authority import (
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
    *,
    behavior_specifications: Mapping[str, object],
    agents_by_name: Mapping[str, object],
    participant_roles: set[str],
    action_contracts: Mapping[str, object],
    observation_boundaries: Mapping[str, object],
    outcome_interpretation_rules: Mapping[str, object],
    is_unresolved: Callable[[object], bool],
) -> list[ParticipantBehaviorIssue]:
    issues: list[ParticipantBehaviorIssue] = []
    reference_context = _BehaviorSpecificationReferenceContext(
        participant_names={str(name) for name in agents_by_name},
        participant_roles=participant_roles,
        action_names={str(name) for name in action_contracts},
        observation_boundary_names={str(name) for name in observation_boundaries},
        outcome_rule_names={str(name) for name in outcome_interpretation_rules},
    )
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
    return issues


def analyze_participant_behavior(
    *,
    agents_by_name: Mapping[str, object],
    action_contracts: Mapping[str, object],
    observation_boundaries: Mapping[str, object],
    outcome_interpretation_rules: Mapping[str, object],
    behavior_specifications: Mapping[str, object],
    participant_roles: set[str],
    is_unresolved: Callable[[object], bool],
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
            behavior_specifications=behavior_specifications,
            agents_by_name=agents_by_name,
            participant_roles=participant_roles,
            action_contracts=action_contracts,
            observation_boundaries=observation_boundaries,
            outcome_interpretation_rules=outcome_interpretation_rules,
            is_unresolved=is_unresolved,
        )
    )

    return ParticipantBehaviorAnalysis(references=tuple(references), issues=tuple(issues))
