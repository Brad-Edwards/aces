"""Canonical finite-domain materialization for trial-compiler-v1."""

from __future__ import annotations

import math

from raes.variation import (
    AlternativeVariationPoint,
    GovernedReferenceVariationPoint,
    LogicalTimingVariationPoint,
    ParameterVariationPoint,
    VariationPoint,
)
from raes_contracts.bounded_domains import BooleanDomain, EnumDomain, ExactDomain, NumericIntervalDomain, NumericType
from raes_contracts.canonical import canonical_json_bytes
from raes_contracts.contracts import (
    ExperimentSelectionMemberOutcomeModel,
    ExperimentSelectionReferenceOutcomeModel,
    LiteralBindingValueModel,
)

from .models import CompilationFailure


def _canonical_scalar_key(value: object) -> bytes:
    if value is None:
        scalar_type = "null"
    elif isinstance(value, bool):
        scalar_type = "boolean"
    elif isinstance(value, int):
        scalar_type = "integer"
    elif isinstance(value, float):
        scalar_type = "number"
    else:
        scalar_type = "string"
    return canonical_json_bytes({"type": scalar_type, "value": value})


def _integer_interval_bounds(domain: NumericIntervalDomain) -> tuple[int, int]:
    if domain.numeric_type is not NumericType.INTEGER:
        raise CompilationFailure(
            "domain-not-finite",
            "/family/variation_points",
            "trial-compiler-v1 admits only finite scalar domains",
        )
    lower = math.ceil(domain.lower)
    upper = math.floor(domain.upper)
    if not domain.lower_closed and lower == domain.lower:
        lower += 1
    if not domain.upper_closed and upper == domain.upper:
        upper -= 1
    return lower, upper


def _integer_interval_values(domain: NumericIntervalDomain) -> list[int]:
    lower, upper = _integer_interval_bounds(domain)
    return list(range(lower, upper + 1))


def _domain_cardinality(point: VariationPoint) -> int:
    if isinstance(point, (ParameterVariationPoint, LogicalTimingVariationPoint)):
        domain = point.domain
        if isinstance(domain, ExactDomain):
            return 1
        if isinstance(domain, EnumDomain):
            return len(domain.values)
        if isinstance(domain, BooleanDomain):
            return 1 if domain.value is not None else 2
        if isinstance(domain, NumericIntervalDomain):
            lower, upper = _integer_interval_bounds(domain)
            return max(0, upper - lower + 1)
        raise CompilationFailure(
            "domain-not-finite",
            "/family/variation_points",
            "trial-compiler-v1 admits only finite scalar domains",
        )
    if isinstance(point, GovernedReferenceVariationPoint):
        return len(point.domain.allowed_refs)
    if isinstance(point, AlternativeVariationPoint):
        return len(point.alternatives)
    raise CompilationFailure(
        "domain-kind-unsupported",
        "/family/variation_points",
        "the selected policy does not support this variation-point kind",
    )


def _scalar_values(point: ParameterVariationPoint | LogicalTimingVariationPoint) -> list[object]:
    domain = point.domain
    if isinstance(domain, ExactDomain):
        return [domain.value]
    if isinstance(domain, EnumDomain):
        return sorted(domain.values, key=_canonical_scalar_key)
    if isinstance(domain, BooleanDomain):
        return [domain.value] if domain.value is not None else [False, True]
    if isinstance(domain, NumericIntervalDomain):
        return _integer_interval_values(domain)
    raise CompilationFailure(
        "domain-not-finite",
        "/family/variation_points",
        "trial-compiler-v1 admits only finite scalar domains",
    )


def canonical_domain_outcomes(point: VariationPoint, *, maximum: int) -> list[object]:
    """Materialize one finite point domain in its exact canonical v1 order."""

    cardinality = _domain_cardinality(point)
    if cardinality == 0:
        raise CompilationFailure(
            "domain-empty",
            "/family/variation_points",
            "a selected variation-point domain is empty",
        )
    if cardinality > maximum:
        raise CompilationFailure(
            "domain-limit-exceeded",
            "/family/variation_points",
            "a variation-point domain exceeds the compilation limit",
        )
    if isinstance(point, (ParameterVariationPoint, LogicalTimingVariationPoint)):
        outcomes: list[object] = [
            LiteralBindingValueModel(kind="literal", value=value) for value in _scalar_values(point)
        ]
    elif isinstance(point, GovernedReferenceVariationPoint):
        outcomes = [
            ExperimentSelectionReferenceOutcomeModel(kind="reference", reference_id=reference_id)
            for reference_id in sorted(point.domain.allowed_refs)
        ]
    elif isinstance(point, AlternativeVariationPoint):
        outcomes = [
            ExperimentSelectionMemberOutcomeModel(kind="member", member_id=member_id)
            for member_id in sorted(point.alternatives)
        ]
    else:
        raise CompilationFailure(
            "domain-kind-unsupported",
            "/family/variation_points",
            "the selected policy does not support this variation-point kind",
        )
    return outcomes


__all__ = ["canonical_domain_outcomes"]
