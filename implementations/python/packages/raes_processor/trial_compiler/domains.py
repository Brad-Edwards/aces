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

_DOMAIN_ADDRESS = "/family/variation_points"
_FINITE_DOMAIN_MESSAGE = "trial-compiler-v1 admits only finite scalar domains"


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
            _DOMAIN_ADDRESS,
            _FINITE_DOMAIN_MESSAGE,
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


def _scalar_domain_cardinality(
    point: ParameterVariationPoint | LogicalTimingVariationPoint,
) -> int:
    domain = point.domain
    if isinstance(domain, ExactDomain):
        cardinality = 1
    elif isinstance(domain, EnumDomain):
        cardinality = len(domain.values)
    elif isinstance(domain, BooleanDomain):
        cardinality = 1 if domain.value is not None else 2
    elif isinstance(domain, NumericIntervalDomain):
        lower, upper = _integer_interval_bounds(domain)
        cardinality = max(0, upper - lower + 1)
    else:
        raise CompilationFailure("domain-not-finite", _DOMAIN_ADDRESS, _FINITE_DOMAIN_MESSAGE)
    return cardinality


def _domain_cardinality(point: VariationPoint) -> int:
    if isinstance(point, (ParameterVariationPoint, LogicalTimingVariationPoint)):
        cardinality = _scalar_domain_cardinality(point)
    elif isinstance(point, GovernedReferenceVariationPoint):
        cardinality = len(point.domain.allowed_refs)
    elif isinstance(point, AlternativeVariationPoint):
        cardinality = len(point.alternatives)
    else:
        raise CompilationFailure(
            "domain-kind-unsupported",
            _DOMAIN_ADDRESS,
            "the selected policy does not support this variation-point kind",
        )
    return cardinality


def _scalar_values(point: ParameterVariationPoint | LogicalTimingVariationPoint) -> list[object]:
    domain = point.domain
    values: list[object]
    if isinstance(domain, ExactDomain):
        values = [domain.value]
    elif isinstance(domain, EnumDomain):
        values = sorted(domain.values, key=_canonical_scalar_key)
    elif isinstance(domain, BooleanDomain):
        values = [domain.value] if domain.value is not None else [False, True]
    elif isinstance(domain, NumericIntervalDomain):
        values = _integer_interval_values(domain)
    else:
        raise CompilationFailure("domain-not-finite", _DOMAIN_ADDRESS, _FINITE_DOMAIN_MESSAGE)
    return values


def canonical_domain_outcomes(point: VariationPoint, *, maximum: int) -> list[object]:
    """Materialize one finite point domain in its exact canonical v1 order."""

    cardinality = _domain_cardinality(point)
    if cardinality == 0:
        raise CompilationFailure(
            "domain-empty",
            _DOMAIN_ADDRESS,
            "a selected variation-point domain is empty",
        )
    if cardinality > maximum:
        raise CompilationFailure(
            "domain-limit-exceeded",
            _DOMAIN_ADDRESS,
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
            _DOMAIN_ADDRESS,
            "the selected policy does not support this variation-point kind",
        )
    return outcomes


__all__ = ["canonical_domain_outcomes"]
