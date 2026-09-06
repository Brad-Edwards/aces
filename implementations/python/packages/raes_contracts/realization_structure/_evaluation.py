"""Bounded evaluation of recursive realization constraints."""

from __future__ import annotations

from collections.abc import Mapping

from ..bounded_domains import scalar_in_domain
from ._common import (
    RealizationRelationResult,
    RelationBudget,
    actual_identity,
    closure_for,
    combine_relation_results,
    json_equal,
    pointer,
    relation_result,
    validate_bounded_value,
)
from ._limits import admit_constraint_document
from ._models import (
    DEFAULT_REALIZATION_CONSTRAINT_LIMITS,
    RealizationAllOf,
    RealizationClosurePosture,
    RealizationConstraintDocument,
    RealizationConstraintLimits,
    RealizationDefinitionReference,
    RealizationDelegatedValue,
    RealizationDomainValue,
    RealizationGraphReference,
    RealizationKeyedCollectionConstraint,
    RealizationKnowledgeValue,
    RealizationLiteral,
    RealizationPresence,
    RealizationRelationStatus,
    RealizationSequenceConstraint,
    RecursiveRealizationStructure,
    identity_key,
)
from ._scopes import evaluate_scope_overlays


def _evaluate_recursive_node(
    document: RealizationConstraintDocument,
    rule: RecursiveRealizationStructure,
    actual: object,
    path: tuple[str, ...],
    depth: int,
    budget: RelationBudget,
    reference_stack: tuple[str, ...] = (),
    reference_hops: int = 0,
) -> RealizationRelationResult:
    current_pointer = pointer(path)
    if exhausted := budget.spend_node(depth):
        return relation_result(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            f"Recursive realization evaluation exceeded {exhausted}.",
        )
    if isinstance(rule, RealizationLiteral):
        status = (
            RealizationRelationStatus.CONFORMANT
            if json_equal(rule.value, actual)
            else RealizationRelationStatus.NONCONFORMANT
        )
        return (
            RealizationRelationResult(status)
            if status is RealizationRelationStatus.CONFORMANT
            else relation_result(status, current_pointer, "Observed value does not satisfy the exact typed constraint.")
        )
    if isinstance(rule, RealizationKnowledgeValue):
        return relation_result(
            RealizationRelationStatus.UNRESOLVED,
            current_pointer,
            f"The {rule.state} knowledge state cannot establish conformance.",
        )
    if isinstance(rule, RealizationDelegatedValue):
        return RealizationRelationResult(RealizationRelationStatus.CONFORMANT)
    if isinstance(rule, RealizationDomainValue):
        status = (
            RealizationRelationStatus.CONFORMANT
            if scalar_in_domain(actual, rule.domain)
            else RealizationRelationStatus.NONCONFORMANT
        )
        return (
            RealizationRelationResult(status)
            if status is RealizationRelationStatus.CONFORMANT
            else relation_result(status, current_pointer, "Observed value is outside the declared bounded domain.")
        )
    if isinstance(rule, RealizationGraphReference):
        status = (
            RealizationRelationStatus.CONFORMANT
            if scalar_in_domain(actual, rule.domain)
            else RealizationRelationStatus.NONCONFORMANT
        )
        return (
            RealizationRelationResult(status)
            if status is RealizationRelationStatus.CONFORMANT
            else relation_result(status, current_pointer, "Graph identity is outside its governed reference domain.")
        )
    if isinstance(rule, RealizationDefinitionReference):
        if reference_hops >= budget.limits.max_reference_hops:
            return relation_result(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                current_pointer,
                "Constraint definition resolution exceeded max_reference_hops.",
            )
        if rule.target in reference_stack:
            return relation_result(
                RealizationRelationStatus.INVALID,
                current_pointer,
                "Constraint definitions contain a reference cycle.",
            )
        target = document.definitions.get(rule.target)
        if target is None:
            return relation_result(
                RealizationRelationStatus.INVALID,
                current_pointer,
                "Constraint definition reference does not resolve in this document.",
            )
        return _evaluate_recursive_node(
            document,
            target,
            actual,
            path,
            depth,
            budget,
            (*reference_stack, rule.target),
            reference_hops + 1,
        )
    if isinstance(rule, RealizationAllOf):
        return combine_relation_results(
            [
                _evaluate_recursive_node(
                    document,
                    constraint,
                    actual,
                    path,
                    depth,
                    budget,
                    reference_stack,
                    reference_hops,
                )
                for constraint in rule.constraints
            ],
            max_diagnostics=budget.limits.max_diagnostics,
        )
    if isinstance(rule, RealizationKeyedCollectionConstraint):
        return _evaluate_keyed_collection(document, rule, actual, path, depth, budget, reference_stack, reference_hops)
    if isinstance(rule, RealizationSequenceConstraint):
        return _evaluate_sequence(document, rule, actual, path, depth, budget, reference_stack, reference_hops)
    if not isinstance(actual, dict):
        return relation_result(
            RealizationRelationStatus.NONCONFORMANT,
            current_pointer,
            "Observed value is not a record required by the recursive constraint.",
        )
    results: list[RealizationRelationResult] = []
    for key, child in rule.fields.items():
        present = key in actual
        child_pointer = pointer((*path, key))
        if child.presence is RealizationPresence.FORBIDDEN:
            if present:
                results.append(
                    relation_result(
                        RealizationRelationStatus.NONCONFORMANT,
                        child_pointer,
                        "A forbidden member is present.",
                    )
                )
            continue
        if not present:
            if child.presence is RealizationPresence.REQUIRED:
                results.append(
                    relation_result(
                        RealizationRelationStatus.NONCONFORMANT,
                        child_pointer,
                        "A required member is absent.",
                    )
                )
            continue
        results.append(
            _evaluate_recursive_node(
                document,
                child,
                actual[key],
                (*path, key),
                depth + 1,
                budget,
                reference_stack,
                reference_hops,
            )
        )
    closure = closure_for(document, rule.closure, path, budget)
    if closure is None:
        return relation_result(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            "Closure resolution exceeded max_operations.",
        )
    if closure.posture is RealizationClosurePosture.UNDEFINED:
        results.append(
            relation_result(
                RealizationRelationStatus.UNSUPPORTED,
                current_pointer,
                "No effective closure policy is selected for this record.",
            )
        )
    elif closure.posture is RealizationClosurePosture.CLOSED and actual.keys() - rule.fields.keys():
        results.append(
            relation_result(
                RealizationRelationStatus.NONCONFORMANT,
                current_pointer,
                "A closed record contains an undeclared member in its named universe.",
            )
        )
    return combine_relation_results(results, max_diagnostics=budget.limits.max_diagnostics)


def _evaluate_keyed_collection(
    document: RealizationConstraintDocument,
    rule: RealizationKeyedCollectionConstraint,
    actual: object,
    path: tuple[str, ...],
    depth: int,
    budget: RelationBudget,
    reference_stack: tuple[str, ...],
    reference_hops: int,
) -> RealizationRelationResult:
    current_pointer = pointer(path)
    if not isinstance(actual, list):
        return relation_result(
            RealizationRelationStatus.NONCONFORMANT,
            current_pointer,
            "Observed value is not the required keyed collection.",
        )
    if len(actual) > budget.limits.max_members:
        return relation_result(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            "Keyed collection evaluation exceeded max_members.",
        )
    if not rule.min_items <= len(actual) <= rule.max_items:
        return relation_result(
            RealizationRelationStatus.NONCONFORMANT,
            current_pointer,
            "Observed keyed collection violates its declared cardinality.",
        )
    indexed: dict[str, object] = {}
    aliases: dict[str, tuple[str | int | bool, ...]] = {}
    for alias in rule.aliases:
        if exhausted := budget.spend_identity():
            return relation_result(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                current_pointer,
                f"Keyed collection alias evaluation exceeded {exhausted}.",
            )
        aliases[identity_key(alias.identity)] = alias.target
    for item in actual:
        if exhausted := budget.spend_identity():
            return relation_result(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                current_pointer,
                f"Keyed collection evaluation exceeded {exhausted}.",
            )
        identity = actual_identity(item, rule.identity_fields)
        if identity is None:
            return relation_result(
                RealizationRelationStatus.INVALID,
                current_pointer,
                "A keyed collection member has no complete concrete semantic identity.",
            )
        source_key = identity_key(identity)
        canonical_identity = aliases.get(source_key, identity)
        if source_key in aliases and (exhausted := budget.spend_identity()):
            return relation_result(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                current_pointer,
                f"Keyed collection alias evaluation exceeded {exhausted}.",
            )
        key = identity_key(canonical_identity)
        if key in indexed:
            return relation_result(
                RealizationRelationStatus.INVALID,
                current_pointer,
                "A keyed collection contains a duplicate or ambiguous semantic identity.",
            )
        if source_key in aliases:
            assert isinstance(item, Mapping)
            canonical_item = dict(item)
            for field, value in zip(rule.identity_fields, canonical_identity, strict=True):
                canonical_item[field] = value
            indexed[key] = canonical_item
        else:
            indexed[key] = item
    results: list[RealizationRelationResult] = []
    declared = {}
    for member in rule.members:
        if exhausted := budget.spend_identity():
            return relation_result(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                current_pointer,
                f"Keyed collection declaration evaluation exceeded {exhausted}.",
            )
        declared[identity_key(member.identity)] = member
    for key, member in declared.items():
        present = key in indexed
        member_pointer = f"{current_pointer}/@{key.removeprefix('sha256:')[:16]}"
        if member.constraint.presence is RealizationPresence.FORBIDDEN:
            if present:
                results.append(
                    relation_result(
                        RealizationRelationStatus.NONCONFORMANT,
                        member_pointer,
                        "A forbidden collection member is present.",
                    )
                )
            continue
        if not present:
            if member.constraint.presence is RealizationPresence.REQUIRED:
                results.append(
                    relation_result(
                        RealizationRelationStatus.NONCONFORMANT,
                        member_pointer,
                        "A required collection member is absent.",
                    )
                )
            continue
        results.append(
            _evaluate_recursive_node(
                document,
                member.constraint,
                indexed[key],
                (*path, f"@{key}"),
                depth + 1,
                budget,
                reference_stack,
                reference_hops,
            )
        )
    closure = closure_for(document, rule.closure, path, budget)
    if closure is None:
        return relation_result(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            "Closure resolution exceeded max_operations.",
        )
    extras = indexed.keys() - declared.keys()
    if closure.posture is RealizationClosurePosture.UNDEFINED:
        results.append(
            relation_result(
                RealizationRelationStatus.UNSUPPORTED,
                current_pointer,
                "No effective closure policy is selected for this keyed collection.",
            )
        )
    elif closure.posture is RealizationClosurePosture.CLOSED and extras:
        results.append(
            relation_result(
                RealizationRelationStatus.NONCONFORMANT,
                current_pointer,
                "A closed keyed collection contains an additional member in its named universe.",
            )
        )
    return combine_relation_results(results, max_diagnostics=budget.limits.max_diagnostics)


def _evaluate_sequence(
    document: RealizationConstraintDocument,
    rule: RealizationSequenceConstraint,
    actual: object,
    path: tuple[str, ...],
    depth: int,
    budget: RelationBudget,
    reference_stack: tuple[str, ...],
    reference_hops: int,
) -> RealizationRelationResult:
    current_pointer = pointer(path)
    if not isinstance(actual, list):
        return relation_result(
            RealizationRelationStatus.NONCONFORMANT,
            current_pointer,
            "Observed value is not the required ordered sequence.",
        )
    if len(actual) > budget.limits.max_members:
        return relation_result(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            "Ordered sequence evaluation exceeded max_members.",
        )
    if not rule.min_items <= len(actual) <= rule.max_items:
        return relation_result(
            RealizationRelationStatus.NONCONFORMANT,
            current_pointer,
            "Observed sequence violates its declared cardinality.",
        )
    results: list[RealizationRelationResult] = []
    for index, child in enumerate(rule.items):
        present = index < len(actual)
        item_pointer = pointer((*path, str(index)))
        if child.presence is RealizationPresence.FORBIDDEN:
            if present:
                results.append(
                    relation_result(
                        RealizationRelationStatus.NONCONFORMANT,
                        item_pointer,
                        "A forbidden sequence occurrence is present.",
                    )
                )
            continue
        if not present:
            if child.presence is RealizationPresence.REQUIRED:
                results.append(
                    relation_result(
                        RealizationRelationStatus.NONCONFORMANT,
                        item_pointer,
                        "A required sequence occurrence is absent.",
                    )
                )
            continue
        results.append(
            _evaluate_recursive_node(
                document,
                child,
                actual[index],
                (*path, str(index)),
                depth + 1,
                budget,
                reference_stack,
                reference_hops,
            )
        )
    closure = closure_for(document, rule.closure, path, budget)
    if closure is None:
        return relation_result(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            "Closure resolution exceeded max_operations.",
        )
    if closure.posture is RealizationClosurePosture.UNDEFINED:
        results.append(
            relation_result(
                RealizationRelationStatus.UNSUPPORTED,
                current_pointer,
                "No effective closure policy is selected for this ordered sequence.",
            )
        )
    elif closure.posture is RealizationClosurePosture.CLOSED and len(actual) > len(rule.items):
        results.append(
            relation_result(
                RealizationRelationStatus.NONCONFORMANT,
                current_pointer,
                "A closed ordered sequence contains additional occurrences.",
            )
        )
    return combine_relation_results(results, max_diagnostics=budget.limits.max_diagnostics)


def evaluate_realization_constraint(
    document: RealizationConstraintDocument,
    actual: object,
    *,
    limits: RealizationConstraintLimits = DEFAULT_REALIZATION_CONSTRAINT_LIMITS,
) -> RealizationRelationResult:
    """Evaluate one value without treating unknown or exhausted work as success."""

    admission_budget = RelationBudget(limits)
    if violation := admit_constraint_document(document, admission_budget):
        return relation_result(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            violation.pointer,
            violation.message,
        )
    budget = RelationBudget(limits)
    if invalid := validate_bounded_value(actual, (), 0, budget):
        return invalid
    scopes = evaluate_scope_overlays(document, actual, budget)
    evaluated = _evaluate_recursive_node(document, document.root, actual, (), 0, budget)
    return combine_relation_results(
        [evaluated, *scopes],
        max_diagnostics=limits.max_diagnostics,
    )
