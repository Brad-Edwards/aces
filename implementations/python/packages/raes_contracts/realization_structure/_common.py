"""Shared finite-work and diagnostic helpers for realization relations."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from ..diagnostics import Diagnostic
from ._models import (
    RealizationClosure,
    RealizationClosurePosture,
    RealizationConstraintDocument,
    RealizationConstraintLimits,
    RealizationRelationStatus,
)


@dataclass
class RelationBudget:
    limits: RealizationConstraintLimits
    nodes: int = 0
    operations: int = 0
    identity_checks: int = 0

    def spend_node(self, depth: int) -> str | None:
        self.nodes += 1
        if depth > self.limits.max_depth:
            return "max_depth"
        if self.nodes > self.limits.max_nodes:
            return "max_nodes"
        return self.spend_operation()

    def spend_operation(self) -> str | None:
        self.operations += 1
        return "max_operations" if self.operations > self.limits.max_operations else None

    def spend_identity(self) -> str | None:
        self.identity_checks += 1
        return "max_identity_checks" if self.identity_checks > self.limits.max_identity_checks else None


@dataclass(frozen=True)
class RealizationRelationResult:
    """One bounded relation outcome; only ``conformant`` is a success claim."""

    status: RealizationRelationStatus
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def conformant(self) -> bool:
        return self.status is RealizationRelationStatus.CONFORMANT


def combine_relation_results(
    results: list[RealizationRelationResult],
    *,
    max_diagnostics: int,
) -> RealizationRelationResult:
    precedence = (
        RealizationRelationStatus.LIMIT_EXCEEDED,
        RealizationRelationStatus.INVALID,
        RealizationRelationStatus.UNSUPPORTED,
        RealizationRelationStatus.NONCONFORMANT,
        RealizationRelationStatus.UNRESOLVED,
    )
    for status in precedence:
        matching = [result for result in results if result.status is status]
        if matching:
            diagnostics = tuple(diagnostic for result in matching for diagnostic in result.diagnostics)[
                :max_diagnostics
            ]
            return RealizationRelationResult(status, diagnostics)
    return RealizationRelationResult(RealizationRelationStatus.CONFORMANT)


def recursive_diagnostic(code: str, pointer: str, message: str) -> Diagnostic:
    return Diagnostic(code=code, domain="realization", address=pointer, message=message)


def relation_result(status: RealizationRelationStatus, pointer: str, message: str) -> RealizationRelationResult:
    return RealizationRelationResult(
        status,
        (recursive_diagnostic(f"realization.{status.value}", pointer, message),),
    )


def pointer_tokens(pointer: str) -> tuple[str, ...]:
    return tuple(token.replace("~1", "/").replace("~0", "~") for token in pointer.split("/")[1:])


def escape_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def pointer(path: tuple[str, ...]) -> str:
    return "" if not path else "/" + "/".join(escape_pointer_token(token) for token in path)


def closure_for(
    document: RealizationConstraintDocument,
    local: RealizationClosure,
    path: tuple[str, ...],
    budget: RelationBudget | None = None,
) -> RealizationClosure | None:
    if local.posture is not RealizationClosurePosture.UNDEFINED:
        return local
    candidates = []
    for scope in document.scopes:
        if budget is not None and budget.spend_operation() is not None:
            return None
        tokens = pointer_tokens(scope.field_pointer)
        if tokens == path[: len(tokens)]:
            candidates.append(scope)
    return (
        max(candidates, key=lambda scope: len(pointer_tokens(scope.field_pointer))).closure
        if candidates
        else document.default_closure
    )


def actual_identity(
    item: object,
    identity_fields: tuple[str, ...],
) -> tuple[str | int | bool, ...] | None:
    if not isinstance(item, Mapping):
        return None
    values = tuple(item.get(field) for field in identity_fields)
    if any(type(value) not in (str, int, bool) for value in values):
        return None
    return values  # type: ignore[return-value]


def json_equal(expected: object, actual: object) -> bool:
    """Compare JSON values without Python's bool/int equivalence."""

    if type(expected) is not type(actual):
        return False
    if isinstance(expected, dict) and isinstance(actual, dict):
        return expected.keys() == actual.keys() and all(
            json_equal(value, actual[key]) for key, value in expected.items()
        )
    if isinstance(expected, list) and isinstance(actual, list):
        return len(expected) == len(actual) and all(
            json_equal(left, right) for left, right in zip(expected, actual, strict=True)
        )
    return expected == actual


def validate_bounded_value(
    value: object,
    path: tuple[str, ...],
    depth: int,
    budget: RelationBudget,
) -> RealizationRelationResult | None:
    current_pointer = pointer(path)
    if exhausted := budget.spend_node(depth):
        return relation_result(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            f"Realization value validation exceeded {exhausted}.",
        )
    if isinstance(value, str) and len(value.encode("utf-8")) > budget.limits.max_scalar_bytes:
        return relation_result(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            "Realization value validation exceeded max_scalar_bytes.",
        )
    if isinstance(value, float) and not math.isfinite(value):
        return relation_result(
            RealizationRelationStatus.INVALID,
            current_pointer,
            "Realization values must use finite JSON numbers.",
        )
    if type(value) is int and value.bit_length() > budget.limits.max_scalar_bytes * 8:
        return relation_result(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            "Realization value validation exceeded the integer-size limit.",
        )
    if type(value) not in (str, int, float, bool, type(None), dict, list):
        return relation_result(
            RealizationRelationStatus.INVALID,
            current_pointer,
            "Realization value is not JSON-compatible.",
        )
    if isinstance(value, (dict, list)):
        if len(value) > budget.limits.max_members:
            return relation_result(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                current_pointer,
                "Realization value validation exceeded max_members.",
            )
        children = value.items() if isinstance(value, dict) else enumerate(value)
        for key, child in children:
            if isinstance(value, dict) and not isinstance(key, str):
                return relation_result(
                    RealizationRelationStatus.INVALID,
                    current_pointer,
                    "Realization record keys must be strings.",
                )
            if invalid := validate_bounded_value(child, (*path, str(key)), depth + 1, budget):
                return invalid
    return None
