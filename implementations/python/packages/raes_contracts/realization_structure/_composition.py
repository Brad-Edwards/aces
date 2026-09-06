"""Composition and refinement relations for realization constraints."""

from __future__ import annotations

from ..bounded_domains import scalar_in_domain
from ..canonical import canonical_json_digest
from ._build import RealizationConstraintBuildResult, build_failure
from ._common import RealizationRelationResult, RelationBudget, json_equal, relation_result
from ._limits import admit_constraint_document
from ._models import (
    DEFAULT_REALIZATION_CONSTRAINT_LIMITS,
    RealizationAllOf,
    RealizationConstraintDocument,
    RealizationConstraintLimits,
    RealizationDelegatedValue,
    RealizationDomainValue,
    RealizationLiteral,
    RealizationPresence,
    RealizationRelationStatus,
    RecursiveRealizationStructure,
)


def compose_realization_constraints(
    left: RealizationConstraintDocument | None,
    right: RealizationConstraintDocument | None,
    *,
    limits: RealizationConstraintLimits = DEFAULT_REALIZATION_CONSTRAINT_LIMITS,
) -> RealizationConstraintBuildResult:
    """Conjoin two documents canonically; conflicts never depend on input order."""

    if left is None or right is None:
        return build_failure(
            RealizationRelationStatus.INVALID,
            "",
            "Constraint composition requires two complete documents.",
        )
    budget = RelationBudget(limits)
    for document in (left, right):
        if violation := admit_constraint_document(document, budget):
            return build_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                violation.pointer,
                violation.message,
            )
    if (
        left.semantic_profile != right.semantic_profile
        or left.default_closure != right.default_closure
        or left.scopes != right.scopes
        or left.definitions != right.definitions
    ):
        return build_failure(
            RealizationRelationStatus.UNSUPPORTED,
            "",
            "Constraint documents use incompatible profiles, scopes, closures, or definitions.",
        )
    try:
        root, conflict = _compose_recursive_nodes(left.root, right.root, budget)
    except ValueError:
        return build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            "",
            "Constraint composition exceeded the bounded conjunction width.",
        )
    if conflict is not None:
        return build_failure(RealizationRelationStatus.NONCONFORMANT, "", conflict)
    assert root is not None
    return RealizationConstraintBuildResult(
        RealizationRelationStatus.CONFORMANT,
        left.model_copy(update={"root": root}),
    )


def _canonical_constraints(
    nodes: list[RecursiveRealizationStructure],
    budget: RelationBudget,
) -> list[RecursiveRealizationStructure]:
    unique = {}
    for node in nodes:
        if budget.spend_operation() is not None:
            raise ValueError("constraint canonicalization exceeded max_operations")
        unique[canonical_json_digest(node.model_dump(mode="json"))] = node
    constraints = [unique[key] for key in sorted(unique)]
    nondelegated_origins = {node.origin for node in constraints if not isinstance(node, RealizationDelegatedValue)}
    return [
        node
        for node in constraints
        if not isinstance(node, RealizationDelegatedValue) or node.origin not in nondelegated_origins
    ]


def _compose_recursive_nodes(
    left: RecursiveRealizationStructure,
    right: RecursiveRealizationStructure,
    budget: RelationBudget,
) -> tuple[RecursiveRealizationStructure | None, str | None]:
    presence = _intersect_presence(left.presence, right.presence)
    if presence is None:
        return None, "Constraint presence declarations conflict."
    left_value = left.model_copy(update={"presence": RealizationPresence.REQUIRED})
    right_value = right.model_copy(update={"presence": RealizationPresence.REQUIRED})
    if presence is RealizationPresence.FORBIDDEN:
        constraints = _canonical_constraints([left_value, right_value], budget)
        node = (
            constraints[0] if len(constraints) == 1 else RealizationAllOf(kind="all-of", constraints=tuple(constraints))
        )
        return node.model_copy(update={"presence": presence}), None
    if type(left_value) is type(right_value) and json_equal(
        left_value.model_dump(mode="json"), right_value.model_dump(mode="json")
    ):
        return left_value.model_copy(update={"presence": presence}), None
    if isinstance(left_value, RealizationDelegatedValue) and left_value.origin is right_value.origin:
        return right_value.model_copy(update={"presence": presence}), None
    if isinstance(right_value, RealizationDelegatedValue) and right_value.origin is left_value.origin:
        return left_value.model_copy(update={"presence": presence}), None
    if isinstance(left_value, RealizationLiteral) and isinstance(right_value, RealizationLiteral):
        if not json_equal(left_value.value, right_value.value):
            return None, "Exact typed constraints conflict."
        if left_value.origin is right_value.origin:
            return left_value.model_copy(update={"presence": presence}), None
    if isinstance(left_value, RealizationLiteral) and isinstance(right_value, RealizationDomainValue):
        if not scalar_in_domain(left_value.value, right_value.domain):
            return None, "Exact value is outside the conjoined domain."
        if left_value.origin is right_value.origin:
            return left_value.model_copy(update={"presence": presence}), None
    if isinstance(right_value, RealizationLiteral) and isinstance(left_value, RealizationDomainValue):
        if not scalar_in_domain(right_value.value, left_value.domain):
            return None, "Exact value is outside the conjoined domain."
        if right_value.origin is left_value.origin:
            return right_value.model_copy(update={"presence": presence}), None
    flattened: list[RecursiveRealizationStructure] = []
    for node in (left_value, right_value):
        flattened.extend(node.constraints if isinstance(node, RealizationAllOf) else (node,))
    constraints = _canonical_constraints(flattened, budget)
    exact = next((node for node in constraints if isinstance(node, RealizationLiteral)), None)
    if exact is not None:
        for constraint in constraints:
            if isinstance(constraint, RealizationLiteral) and not json_equal(exact.value, constraint.value):
                return None, "Exact typed constraints conflict."
            if isinstance(constraint, RealizationDomainValue) and not scalar_in_domain(exact.value, constraint.domain):
                return None, "Exact value is outside the conjoined domain."
        constraints = [
            node
            for node in constraints
            if not isinstance(node, RealizationDomainValue) or node.origin is not exact.origin
        ]
    if len(constraints) == 1:
        return constraints[0].model_copy(update={"presence": presence}), None
    return RealizationAllOf(kind="all-of", constraints=tuple(constraints), presence=presence), None


def _intersect_presence(
    left: RealizationPresence,
    right: RealizationPresence,
) -> RealizationPresence | None:
    if {left, right} == {RealizationPresence.REQUIRED, RealizationPresence.FORBIDDEN}:
        return None
    if RealizationPresence.REQUIRED in (left, right):
        return RealizationPresence.REQUIRED
    if RealizationPresence.FORBIDDEN in (left, right):
        return RealizationPresence.FORBIDDEN
    return RealizationPresence.OPTIONAL


def realization_constraint_refines(
    candidate: RealizationConstraintDocument,
    baseline: RealizationConstraintDocument,
    *,
    limits: RealizationConstraintLimits = DEFAULT_REALIZATION_CONSTRAINT_LIMITS,
) -> RealizationRelationResult:
    """Recognize refinement when conjunction leaves the candidate unchanged."""

    composed = compose_realization_constraints(candidate, baseline, limits=limits)
    if composed.status is not RealizationRelationStatus.CONFORMANT:
        return RealizationRelationResult(composed.status, composed.diagnostics)
    if composed.document == candidate:
        return RealizationRelationResult(RealizationRelationStatus.CONFORMANT)
    return relation_result(
        RealizationRelationStatus.NONCONFORMANT,
        "",
        "The candidate is not a recognized structural refinement of the baseline.",
    )
