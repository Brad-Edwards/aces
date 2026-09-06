"""Semantic-equivalence checks used by the legacy compatibility boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ._common import RelationBudget, closure_for, json_equal, pointer
from ._legacy import realization_member_identity
from ._models import (
    RealizationClosurePosture,
    RealizationConstraintDocument,
    RealizationLiteral,
    RealizationOrigin,
    RealizationPresence,
    RealizationRecordConstraint,
    RealizationSequenceConstraint,
    RecursiveRealizationStructure,
)


@dataclass(frozen=True)
class CompatibilityLimit(Exception):
    address: str
    message: str


def indexed_collection_for_downgrade(
    value: list[object],
    fields: tuple[str, ...],
    path: tuple[str, ...],
    budget: RelationBudget,
) -> dict[str, object] | None:
    members: dict[str, object] = {}
    for item in value:
        if exhausted := budget.spend_identity():
            raise CompatibilityLimit(pointer(path), f"Legacy projection exceeded {exhausted}.")
        identity = realization_member_identity(item, fields)
        if identity is None or identity in members:
            return None
        members[identity] = item
    return members


def constraint_is_exact(
    document: RealizationConstraintDocument,
    node: RecursiveRealizationStructure,
    expected: object,
    path: tuple[str, ...],
) -> bool:
    """Return true only when a recursive subtree admits exactly one JSON value."""

    if node.presence is not RealizationPresence.REQUIRED or node.origin is not RealizationOrigin.AUTHOR:
        return False
    if isinstance(node, RealizationLiteral):
        return json_equal(node.value, expected)
    if isinstance(node, RealizationRecordConstraint):
        if not isinstance(expected, Mapping) or set(expected) != set(node.fields):
            return False
        closure = closure_for(document, node.closure, path)
        assert closure is not None
        if closure.posture is not RealizationClosurePosture.CLOSED:
            return False
        return all(
            constraint_is_exact(document, child, expected[key], (*path, key)) for key, child in node.fields.items()
        )
    if isinstance(node, RealizationSequenceConstraint):
        if (
            not isinstance(expected, list)
            or len(expected) != len(node.items)
            or not node.min_items <= len(expected) <= node.max_items
        ):
            return False
        closure = closure_for(document, node.closure, path)
        assert closure is not None
        if closure.posture is not RealizationClosurePosture.CLOSED:
            return False
        return all(
            constraint_is_exact(document, child, expected[index], (*path, str(index)))
            for index, child in enumerate(node.items)
        )
    return False
