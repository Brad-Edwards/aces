"""Bounded admission of recursive constraint and metadata inputs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ._common import RelationBudget, pointer
from ._models import (
    RealizationAllOf,
    RealizationCollectionProfile,
    RealizationConstraintDocument,
    RealizationDefinitionReference,
    RealizationDomainValue,
    RealizationGraphReference,
    RealizationKeyedCollectionConstraint,
    RealizationLiteral,
    RealizationRecordConstraint,
    RealizationScope,
    RealizationSequenceConstraint,
    RecursiveRealizationStructure,
)


@dataclass(frozen=True)
class LimitViolation:
    pointer: str
    message: str


def _spend_operation(
    budget: RelationBudget,
    path: tuple[str, ...],
    activity: str,
) -> LimitViolation | None:
    if exhausted := budget.spend_operation():
        return LimitViolation(pointer(path), f"{activity} exceeded {exhausted}.")
    return None


def _admit_metadata(
    value: object,
    path: tuple[str, ...],
    depth: int,
    budget: RelationBudget,
) -> LimitViolation | None:
    if depth > budget.limits.max_depth:
        return LimitViolation(pointer(path), "Constraint metadata exceeded max_depth.")
    if violation := _spend_operation(budget, path, "Constraint metadata admission"):
        return violation
    if isinstance(value, str):
        if len(value.encode("utf-8")) > budget.limits.max_scalar_bytes:
            return LimitViolation(pointer(path), "Constraint metadata exceeded max_scalar_bytes.")
        return None
    if isinstance(value, dict):
        if len(value) > budget.limits.max_members:
            return LimitViolation(pointer(path), "Constraint metadata exceeded max_members.")
        for key, child in value.items():
            if violation := _admit_metadata(key, (*path, str(key), "$key"), depth + 1, budget):
                return violation
            if violation := _admit_metadata(child, (*path, str(key)), depth + 1, budget):
                return violation
        return None
    if isinstance(value, (list, tuple)):
        if len(value) > budget.limits.max_members:
            return LimitViolation(pointer(path), "Constraint metadata exceeded max_members.")
        for index, child in enumerate(value):
            if violation := _admit_metadata(child, (*path, str(index)), depth + 1, budget):
                return violation
    return None


def _admit_node(
    node: RecursiveRealizationStructure,
    path: tuple[str, ...],
    depth: int,
    budget: RelationBudget,
) -> LimitViolation | None:
    if exhausted := budget.spend_node(depth):
        return LimitViolation(pointer(path), f"Constraint admission exceeded {exhausted}.")
    if violation := _admit_metadata(
        {
            "kind": node.kind,
            "presence": getattr(node.presence, "value", node.presence),
            "origin": getattr(node.origin, "value", node.origin),
        },
        (*path, "$header"),
        0,
        budget,
    ):
        return violation
    if isinstance(node, RealizationLiteral):
        return _admit_metadata(node.value, (*path, "value"), 0, budget)
    if isinstance(node, (RealizationDomainValue, RealizationGraphReference)):
        if violation := _admit_metadata(node.domain.model_dump(mode="json"), (*path, "domain"), 0, budget):
            return violation
        if isinstance(node, RealizationGraphReference):
            return _admit_metadata(node.cycle_policy, (*path, "cycle_policy"), 0, budget)
        return None
    if isinstance(node, RealizationDefinitionReference):
        return _admit_metadata(node.target, (*path, "target"), 0, budget)
    if isinstance(node, RealizationRecordConstraint):
        if violation := _admit_metadata(node.closure.model_dump(mode="json"), (*path, "closure"), 0, budget):
            return violation
        if len(node.fields) > budget.limits.max_members:
            return LimitViolation(pointer(path), "Constraint record exceeded max_members.")
        for key, child in node.fields.items():
            if violation := _admit_metadata(key, (*path, key, "$key"), 0, budget):
                return violation
            if violation := _admit_node(child, (*path, key), depth + 1, budget):
                return violation
        return None
    if isinstance(node, RealizationKeyedCollectionConstraint):
        if violation := _admit_keyed_metadata(node, path, budget):
            return violation
        for index, member in enumerate(node.members):
            if exhausted := budget.spend_identity():
                return LimitViolation(pointer((*path, str(index))), f"Constraint admission exceeded {exhausted}.")
            if violation := _admit_metadata(member.identity, (*path, str(index), "identity"), 0, budget):
                return violation
            if violation := _admit_node(member.constraint, (*path, str(index)), depth + 1, budget):
                return violation
        return None
    if isinstance(node, RealizationSequenceConstraint):
        if violation := _admit_metadata(node.closure.model_dump(mode="json"), (*path, "closure"), 0, budget):
            return violation
        if violation := _admit_metadata(
            {"min_items": node.min_items, "max_items": node.max_items},
            (*path, "cardinality"),
            0,
            budget,
        ):
            return violation
        children = node.items
    elif isinstance(node, RealizationAllOf):
        children = node.constraints
    else:
        return None
    if len(children) > budget.limits.max_members:
        return LimitViolation(pointer(path), "Constraint children exceeded max_members.")
    for index, child in enumerate(children):
        if violation := _admit_node(child, (*path, str(index)), depth + 1, budget):
            return violation
    return None


def _admit_keyed_metadata(
    node: RealizationKeyedCollectionConstraint,
    path: tuple[str, ...],
    budget: RelationBudget,
) -> LimitViolation | None:
    metadata = {
        "collection_kind": node.collection_kind,
        "identity_fields": node.identity_fields,
        "closure": node.closure.model_dump(mode="json"),
        "min_items": node.min_items,
        "max_items": node.max_items,
    }
    if violation := _admit_metadata(metadata, (*path, "$collection"), 0, budget):
        return violation
    if len(node.aliases) > budget.limits.max_members:
        return LimitViolation(pointer(path), "Constraint aliases exceeded max_members.")
    for index, alias in enumerate(node.aliases):
        if exhausted := budget.spend_identity():
            return LimitViolation(
                pointer((*path, "aliases", str(index))), f"Constraint admission exceeded {exhausted}."
            )
        if violation := _admit_metadata(
            {"identity": alias.identity, "target": alias.target},
            (*path, "aliases", str(index)),
            0,
            budget,
        ):
            return violation
    return None


def admit_constraint_document(
    document: RealizationConstraintDocument,
    budget: RelationBudget,
) -> LimitViolation | None:
    """Bound every structural and metadata input before a recursive relation."""

    header = {
        "contract_id": document.contract_id,
        "semantic_profile": document.semantic_profile,
        "default_closure": document.default_closure.model_dump(mode="json"),
    }
    if violation := _admit_metadata(header, ("$document",), 0, budget):
        return violation
    if len(document.scopes) > budget.limits.max_members:
        return LimitViolation("/scopes", "Constraint scopes exceeded max_members.")
    for index, scope in enumerate(document.scopes):
        if violation := _admit_metadata(scope.model_dump(mode="json"), ("scopes", str(index)), 0, budget):
            return violation
    if violation := _admit_node(document.root, ("root",), 0, budget):
        return violation
    for name, definition in document.definitions.items():
        if violation := _admit_metadata(name, ("definitions", name, "$key"), 0, budget):
            return violation
        if violation := _admit_node(definition, ("definitions", name), 0, budget):
            return violation
    return None


def admit_normalization_metadata(
    scopes: tuple[RealizationScope, ...],
    profiles: tuple[RealizationCollectionProfile, ...],
    origins: Mapping[str, object],
    budget: RelationBudget,
) -> LimitViolation | None:
    """Bound address overlays supplied beside an ordinary literal."""

    if max(len(scopes), len(profiles), len(origins)) > budget.limits.max_members:
        return LimitViolation("", "Normalization metadata exceeded max_members.")
    groups = (scopes, profiles)
    for group_index, group in enumerate(groups):
        for index, item in enumerate(group):
            if violation := _admit_metadata(
                item.model_dump(mode="json"),
                ("$metadata", str(group_index), str(index)),
                0,
                budget,
            ):
                return violation
    for address, origin in origins.items():
        if violation := _admit_metadata(
            {"address": address, "origin": str(origin)},
            ("$metadata", "origins", address),
            0,
            budget,
        ):
            return violation
    return None
