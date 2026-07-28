"""Contextual admission of experiment selection intent against expanded SDL."""

from __future__ import annotations

import math

from raes_contracts.bounded_domains import (
    BooleanDomain,
    EnumDomain,
    ExactDomain,
    NumericIntervalDomain,
    NumericType,
    scalar_in_domain,
)
from raes_contracts.contracts import ExperimentSpecModel, LiteralBindingValueModel
from raes_contracts.contracts.experiment_selection import (
    MAX_SELECTION_OUTPUT_BOUND,
    ExperimentEnumerateSelectionPolicyModel,
    ExperimentFixedSelectionPolicyModel,
    ExperimentProductSelectionPolicyModel,
    ExperimentSampleSelectionPolicyModel,
    ExperimentSelectionMemberOutcomeModel,
    ExperimentSelectionOrderOutcomeModel,
    ExperimentSelectionReferenceOutcomeModel,
    ExperimentSelectionSubsetOutcomeModel,
    ExperimentStratifiedSelectionPolicyModel,
)

from .scenario import ExpandedScenario
from .variation import (
    AlternativeVariationPoint,
    GovernedReferenceVariationPoint,
    LogicalTimingVariationPoint,
    OrderVariationPoint,
    ParameterVariationPoint,
    SubsetVariationPoint,
    VariationPoint,
)


def validate_experiment_selection_against_family(
    spec: ExperimentSpecModel,
    *,
    family: ExpandedScenario,
) -> ExperimentSpecModel:
    """Validate authoring policy intent against one trusted expanded family.

    This gate intentionally does not compile coordinates or selected scenarios.
    It verifies only point resolution, domain membership, supported policy
    semantics, and the experiment/family identity join owned by issue #787.
    """

    if not isinstance(family, ExpandedScenario) or not family.semantic_validated:
        raise ValueError("experiment selection requires a semantically admitted ExpandedScenario")
    policies = spec.run_plan.selection_policies
    if not policies:
        return spec
    intended = spec.intended_scenario_ref
    family_id = family.name
    if intended is None or intended.ref_kind != "scenario" or intended.ref_id != family_id:
        raise ValueError("experiment selection family identity must match intended_scenario_ref")
    _validate_binding_family_identity(spec, family_id)
    for policy in policies.values():
        if isinstance(policy, ExperimentProductSelectionPolicyModel):
            continue
        point = _resolve_point(family, policy.point_ref)
        if isinstance(policy, ExperimentFixedSelectionPolicyModel):
            _validate_outcome(point, policy.outcome)
        elif isinstance(policy, ExperimentEnumerateSelectionPolicyModel):
            cardinality = _finite_policy_population(point)
            if cardinality != policy.output_bound:
                raise ValueError("enumerate policy output_bound must equal the finite point domain cardinality")
        elif isinstance(policy, ExperimentSampleSelectionPolicyModel):
            _finite_policy_population(point)
        elif isinstance(policy, ExperimentStratifiedSelectionPolicyModel):
            for outcome in policy.outcomes.values():
                _validate_outcome(point, outcome)
    return spec


def _validate_binding_family_identity(spec: ExperimentSpecModel, family_id: str) -> None:
    descriptors = spec.binding_descriptors
    if descriptors is None:
        return
    for descriptor in descriptors.descriptors:
        target_family = getattr(descriptor.target, "scenario_family_id", family_id)
        if target_family != family_id:
            raise ValueError("scenario binding target family identity does not match selection family")


def _resolve_point(family: ExpandedScenario, point_ref: str) -> VariationPoint:
    point = family.variation_points.get(point_ref)
    if point is None:
        raise ValueError(f"selection policy variation point {point_ref!r} is not declared")
    return point


def _finite_policy_population(point: VariationPoint) -> int:
    if isinstance(point, (ParameterVariationPoint, LogicalTimingVariationPoint)):
        cardinality = _scalar_domain_cardinality(point.domain)
    elif isinstance(point, GovernedReferenceVariationPoint):
        cardinality = len(point.domain.allowed_refs)
    elif isinstance(point, AlternativeVariationPoint):
        cardinality = len(point.alternatives)
    else:
        raise ValueError("selection policy kind is unsupported for subset or order variation points")
    if cardinality > MAX_SELECTION_OUTPUT_BOUND:
        raise ValueError("selection policy finite population exceeds the admission bound")
    return cardinality


def _scalar_domain_cardinality(domain: object) -> int:
    if isinstance(domain, ExactDomain):
        return 1
    if isinstance(domain, EnumDomain):
        return len(domain.values)
    if isinstance(domain, BooleanDomain):
        return 1 if domain.value is not None else 2
    if not isinstance(domain, NumericIntervalDomain) or domain.numeric_type is not NumericType.INTEGER:
        raise ValueError("continuous or unsupported domains cannot be enumerated or sampled")
    lower = math.ceil(domain.lower)
    upper = math.floor(domain.upper)
    if not domain.lower_closed and lower == domain.lower:
        lower += 1
    if not domain.upper_closed and upper == domain.upper:
        upper -= 1
    cardinality = upper - lower + 1
    if cardinality < 1:
        raise ValueError("selection policy domain is empty")
    return cardinality


def _validate_outcome(point: VariationPoint, outcome: object) -> None:
    if isinstance(point, (ParameterVariationPoint, LogicalTimingVariationPoint)):
        if not isinstance(outcome, LiteralBindingValueModel) or not scalar_in_domain(outcome.value, point.domain):
            raise ValueError("fixed selection literal is outside the declared point domain")
        return
    if isinstance(point, GovernedReferenceVariationPoint):
        if (
            not isinstance(outcome, ExperimentSelectionReferenceOutcomeModel)
            or outcome.reference_id not in point.domain.allowed_refs
        ):
            raise ValueError("fixed selection reference is outside the declared point domain")
        return
    if isinstance(point, AlternativeVariationPoint):
        if (
            not isinstance(outcome, ExperimentSelectionMemberOutcomeModel)
            or outcome.member_id not in point.alternatives
        ):
            raise ValueError("fixed selection member is outside the declared point domain")
        return
    if isinstance(point, SubsetVariationPoint):
        _validate_subset_outcome(point, outcome)
        return
    if isinstance(point, OrderVariationPoint):
        _validate_order_outcome(point, outcome)
        return
    raise ValueError("unsupported variation point kind")


def _validate_subset_outcome(point: SubsetVariationPoint, outcome: object) -> None:
    if not isinstance(outcome, ExperimentSelectionSubsetOutcomeModel):
        raise ValueError("subset variation point requires a subset selection outcome")
    selected = set(outcome.member_ids)
    if not selected.issubset(point.members):
        raise ValueError("subset selection includes an undeclared member")
    maximum = len(point.members) if point.maximum is None else point.maximum
    if not point.minimum <= len(selected) <= maximum:
        raise ValueError("subset selection violates declared cardinality")


def _validate_order_outcome(point: OrderVariationPoint, outcome: object) -> None:
    if not isinstance(outcome, ExperimentSelectionOrderOutcomeModel):
        raise ValueError("order variation point requires an order selection outcome")
    if set(outcome.member_ids) != set(point.members):
        raise ValueError("order selection must contain every declared member exactly once")
    positions = {member: index for index, member in enumerate(outcome.member_ids)}
    if any(positions[edge.before] >= positions[edge.after] for edge in point.precedence):
        raise ValueError("order selection violates declared precedence")
    if any(positions[member] != position for member, position in point.fixed_positions.items()):
        raise ValueError("order selection violates declared fixed positions")


__all__ = ["validate_experiment_selection_against_family"]
