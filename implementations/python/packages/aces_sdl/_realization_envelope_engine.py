"""Internal engine for the realization-envelope relation.

Pure, dependency-light helpers shared by the four relation kinds in
:mod:`aces_sdl.realization_envelope`: SDL-path navigation, most-specific-wins
constraint flattening (R2), scalar/record closure, domain-subset comparison (R4),
deterministic witness selection (R5), and out-of-envelope variation (R6). Kept
separate from the public relation module so neither file exceeds the repo
source-size cap. This module has no diagnostic, parser, or validator dependency;
those live in the public module.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from aces_contracts.realization_envelope import (
    BooleanDomain,
    Closure,
    DomainDescriptor,
    EnumDomain,
    ExactDomain,
    GovernedReferenceDomain,
    NumericIntervalDomain,
    NumericType,
    Posture,
    RealizationEnvelopeModel,
    RecordDomain,
    WitnessPolicy,
    scalar_in_domain,
)
from pydantic import BaseModel

# Sentinel meaning "no out-of-envelope value can be formed within the domain kind".
_MISSING = object()


@dataclass(frozen=True)
class LeafConstraint:
    """A flattened scalar constraint at a concrete SDL path."""

    domain: DomainDescriptor
    domain_name: str
    posture: Posture
    overrideable: bool


# --------------------------------------------------------------------------- #
# Path handling                                                               #
# --------------------------------------------------------------------------- #

_PATH_TOKEN_RE = re.compile(r"[^.\[\]]+|\[\d+\]")


def tokenize_path(path: str) -> list[str | int]:
    """Split an SDL path into attribute/key segments and ``[i]`` list indices."""

    tokens: list[str | int] = []
    for raw in _PATH_TOKEN_RE.findall(path):
        if raw.startswith("["):
            tokens.append(int(raw[1:-1]))
        else:
            tokens.append(raw)
    return tokens


def navigate(root: object, tokens: Sequence[str | int]) -> tuple[bool, object]:
    """Resolve ``tokens`` against a model/mapping/sequence tree."""

    current: object = root
    for token in tokens:
        if isinstance(token, int):
            if isinstance(current, Sequence) and not isinstance(current, (str, bytes)) and 0 <= token < len(current):
                current = current[token]
                continue
            return False, None
        if isinstance(current, BaseModel):
            if token in type(current).model_fields:
                current = getattr(current, token)
                continue
            return False, None
        if isinstance(current, Mapping):
            if token in current:
                current = current[token]
                continue
            return False, None
        return False, None
    return True, current


def normalize_scalar(value: object) -> object:
    """Reduce an SDL model value to a portable scalar for domain comparison.

    SDL string enums (e.g. ``OSFamily``, ``NodeType``) navigate out as ``Enum``
    instances; envelope domains carry plain JSON scalars. Comparing them requires
    the enum's underlying value. ``bool`` is preserved (it is its own domain kind).
    """

    if isinstance(value, Enum):
        return value.value
    return value


def _is_nonempty(value: object) -> bool:
    if value is None:
        return False
    return not (isinstance(value, (dict, list, tuple, set)) and len(value) == 0)


def present_children(value: object) -> set[str]:
    """Immediate realizable child keys carrying a value under ``value``.

    A child is a *present realizable dimension* when it is non-empty and either a
    required field or set to something other than its declared default. This is
    robust to the instantiation round-trip (``model_dump`` → ``model_validate``),
    which marks every field as set and so makes ``model_fields_set`` unusable:
    default identity scalars (e.g. ``version="*"``) are not realizable dimensions
    and must not count as closed-world extras (envelope-semantics.md I3).
    """

    if isinstance(value, BaseModel):
        present: set[str] = set()
        fields = type(value).model_fields
        for name, info in fields.items():
            child = getattr(value, name)
            if not _is_nonempty(child):
                continue
            if info.is_required():
                present.add(name)
                continue
            if child != info.get_default(call_default_factory=True):
                present.add(name)
        return present
    if isinstance(value, Mapping):
        return {str(key) for key in value}
    return set()


# --------------------------------------------------------------------------- #
# Effective constraints (most-specific-wins flattening, R2)                    #
# --------------------------------------------------------------------------- #


def _expand_constraint(
    path: str,
    domain: DomainDescriptor,
    domain_name: str,
    posture: Posture,
    overrideable: bool,
    envelope: RealizationEnvelopeModel,
    constraints: dict[str, LeafConstraint],
) -> None:
    if isinstance(domain, RecordDomain):
        for field_name, referenced in domain.fields.items():
            _expand_constraint(
                f"{path}.{field_name}",
                envelope.domains[referenced],
                referenced,
                posture,
                overrideable,
                envelope,
                constraints,
            )
        return
    constraints[path] = LeafConstraint(
        domain=domain,
        domain_name=domain_name,
        posture=posture,
        overrideable=overrideable,
    )


def _collect_record_closures(
    path: str,
    domain: DomainDescriptor,
    envelope: RealizationEnvelopeModel,
    closed: dict[str, set[str]],
) -> None:
    if not isinstance(domain, RecordDomain):
        return
    if not domain.extra:
        closed[path] = set(domain.fields)
    for field_name, referenced in domain.fields.items():
        _collect_record_closures(f"{path}.{field_name}", envelope.domains[referenced], envelope, closed)


def _record_closed_scopes(envelope: RealizationEnvelopeModel) -> dict[str, set[str]]:
    """Closed record domains contribute an admitted-child-key set at their path."""

    closed: dict[str, set[str]] = {}
    for binding in envelope.bindings:
        if binding.domain is None:
            continue
        _collect_record_closures(binding.path, envelope.domains[binding.domain], envelope, closed)
    return closed


def effective_constraints(
    envelope: RealizationEnvelopeModel,
) -> tuple[dict[str, LeafConstraint], dict[str, set[str]]]:
    """Flatten bindings into per-path scalar constraints and closed-scope key sets.

    Most-specific-wins (R2) is realized by processing bindings shortest-path-first
    so a more-specific explicit binding overwrites a record expansion, and an
    ``open`` binding removes any constraint at (and under) its path.
    """

    constraints: dict[str, LeafConstraint] = {}
    ordered = sorted(envelope.bindings, key=lambda b: len(tokenize_path(b.path)))
    for binding in ordered:
        if binding.posture is Posture.OPEN:
            prefix = binding.path
            for existing in [p for p in constraints if p == prefix or p.startswith(prefix + ".")]:
                del constraints[existing]
            continue
        if binding.domain is None:  # guaranteed non-None for constrained/exact by the contract validator
            continue
        _expand_constraint(
            binding.path,
            envelope.domains[binding.domain],
            binding.domain,
            binding.posture,
            binding.overrideable,
            envelope,
            constraints,
        )

    closed = _record_closed_scopes(envelope)
    for overlay in envelope.closure:
        if overlay.closure is not Closure.CLOSED_WORLD:
            continue
        admitted = closed.setdefault(overlay.path, set())
        prefix = overlay.path + "." if overlay.path else ""
        for binding in envelope.bindings:
            if not binding.path.startswith(prefix):
                continue
            remainder = binding.path[len(prefix) :]
            first = tokenize_path(remainder)[0] if remainder else None
            if isinstance(first, str):
                admitted.add(first)
    return constraints, closed


def overridability_violations(envelope: RealizationEnvelopeModel) -> list[str]:
    """Paths where a more-specific binding illegally widens a fixed inherited value.

    Envelope-semantics.md R2: a more-specific binding may not widen a value an
    enclosing scope fixed (or excluded) unless the enclosing binding marked that
    child ``overrideable``. Replays the same shortest-path-first order as
    :func:`effective_constraints` and reports each leaf where an ``open`` binding
    removes, or a broader domain overwrites, a non-overrideable inherited
    constraint. An empty list means the envelope is well-formed under R2.
    """

    violations: list[str] = []
    constraints: dict[str, LeafConstraint] = {}
    for binding in sorted(envelope.bindings, key=lambda b: len(tokenize_path(b.path))):
        if binding.posture is Posture.OPEN:
            prefix = binding.path
            for path in [p for p in constraints if p == prefix or p.startswith(prefix + ".")]:
                if not constraints[path].overrideable:
                    violations.append(path)  # open widens a fixed inherited value
                del constraints[path]
            continue
        if binding.domain is None:
            continue
        new_leaves: dict[str, LeafConstraint] = {}
        _expand_constraint(
            binding.path,
            envelope.domains[binding.domain],
            binding.domain,
            binding.posture,
            binding.overrideable,
            envelope,
            new_leaves,
        )
        for path, new_constraint in new_leaves.items():
            existing = constraints.get(path)
            # A narrowing (subset) overwrite is always allowed; a non-subset overwrite
            # of a non-overrideable inherited value is a forbidden widening.
            if (
                existing is not None
                and not existing.overrideable
                and not domain_subset(new_constraint.domain, existing.domain)
            ):
                violations.append(path)
            constraints[path] = new_constraint
    return violations


# --------------------------------------------------------------------------- #
# Domain subset (R4)                                                          #
# --------------------------------------------------------------------------- #


def _finite_members(domain: DomainDescriptor) -> list[Any] | None:
    """Finite value list for a scalar domain, or ``None`` when infinite."""

    if isinstance(domain, ExactDomain):
        return [domain.value]
    if isinstance(domain, EnumDomain):
        return list(domain.values)
    if isinstance(domain, BooleanDomain):
        return [domain.value] if domain.value is not None else [False, True]
    if isinstance(domain, GovernedReferenceDomain):
        return list(domain.allowed_refs)
    return None


def _interval_subset(sub: NumericIntervalDomain, sup: NumericIntervalDomain) -> bool:
    if sup.numeric_type is NumericType.INTEGER and sub.numeric_type is NumericType.NUMBER:
        return False
    lower_ok = sup.lower < sub.lower or (sup.lower == sub.lower and (sup.lower_closed or not sub.lower_closed))
    upper_ok = sup.upper > sub.upper or (sup.upper == sub.upper and (sup.upper_closed or not sub.upper_closed))
    return lower_ok and upper_ok


def domain_subset(sub: DomainDescriptor, sup: DomainDescriptor) -> bool:
    """Return whether every value admitted by ``sub`` is admitted by ``sup``."""

    # Governed references carry an authority that scopes their refs; subsumption
    # must not drop it (raw ref strings from a different kind or a different
    # authority are not authority-scoped and never subsume). A governed-reference
    # domain is subsumed only by another governed-reference domain under the same
    # authority, and never subsumes — or is subsumed by — a non-governed kind.
    if isinstance(sub, GovernedReferenceDomain) or isinstance(sup, GovernedReferenceDomain):
        if not (isinstance(sub, GovernedReferenceDomain) and isinstance(sup, GovernedReferenceDomain)):
            return False
        if sub.authority != sup.authority:
            return False
        return set(sub.allowed_refs) <= set(sup.allowed_refs)

    if isinstance(sub, NumericIntervalDomain):
        if sub.lower == sub.upper:
            value: Any = int(sub.lower) if sub.numeric_type is NumericType.INTEGER else sub.lower
            return scalar_in_domain(value, sup)
        if isinstance(sup, NumericIntervalDomain):
            return _interval_subset(sub, sup)
        return False

    members = _finite_members(sub)
    if members is None:  # only numeric intervals are infinite, and they are handled above
        return False
    return all(scalar_in_domain(candidate, sup) for candidate in members)


# --------------------------------------------------------------------------- #
# Witness selection (R5)                                                      #
# --------------------------------------------------------------------------- #


def _enum_sort_key(value: Any) -> tuple[int, str]:
    kind = 0 if isinstance(value, bool) else 1 if isinstance(value, (int, float)) else 2
    return (kind, str(value))


def default_witness_value(domain: DomainDescriptor) -> tuple[Any, str | None]:
    """Deterministic default selection for a scalar domain (R5)."""

    if isinstance(domain, ExactDomain):
        return domain.value, None
    if isinstance(domain, EnumDomain):
        return sorted(domain.values, key=_enum_sort_key)[0], None
    if isinstance(domain, BooleanDomain):
        return (domain.value if domain.value is not None else False), None
    if isinstance(domain, GovernedReferenceDomain):
        return sorted(domain.allowed_refs)[0], None
    if isinstance(domain, NumericIntervalDomain):
        return _numeric_witness_value(domain)
    return None, "record domains are not scalar witness leaves"


def _numeric_witness_value(domain: NumericIntervalDomain) -> tuple[Any, str | None]:
    """Deterministic in-interval witness value, or an error if the interval is empty."""

    if domain.numeric_type is NumericType.INTEGER:
        lower = int(domain.lower)
        upper = int(domain.upper)
        candidate = lower if domain.lower_closed else lower + 1
        if candidate < upper or (candidate == upper and domain.upper_closed):
            return candidate, None
        return None, "integer interval admits no witness value"
    # Real interval. A closed lower bound is itself admissible; an open lower bound
    # on a non-degenerate interval (the contract forbids open degenerate intervals)
    # admits the interior midpoint.
    if domain.lower_closed:
        return domain.lower, None
    return (domain.lower + domain.upper) / 2, None


def witness_value(constraint: LeafConstraint, policy: WitnessPolicy | None) -> tuple[Any, str | None]:
    if policy is not None and constraint.domain_name in policy.selections:
        return policy.selections[constraint.domain_name], None
    return default_witness_value(constraint.domain)


def assign_path(payload: dict[str, Any], tokens: Sequence[str | int], value: Any) -> str | None:
    """Set ``value`` at ``tokens`` in a nested dict payload.

    Returns an error string if the path uses list indices, which witness assembly
    does not support (SDL sections are keyed mappings).
    """

    current = payload
    for token in tokens[:-1]:
        if isinstance(token, int):
            return "list-indexed paths are not supported for witness generation"
        nested = current.get(token)
        if not isinstance(nested, dict):
            nested = {}
            current[token] = nested
        current = nested
    last = tokens[-1]
    if isinstance(last, int):
        return "list-indexed paths are not supported for witness generation"
    current[last] = value
    return None


# --------------------------------------------------------------------------- #
# Out-of-envelope variation (R6)                                             #
# --------------------------------------------------------------------------- #


def _perturb_scalar(value: Any) -> Any:
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 1.0
    return f"{value}-out-of-envelope"


def _fresh_scalar_outside(members: Sequence[Any]) -> Any:
    if all(isinstance(member, bool) for member in members):
        return _MISSING
    numeric = [m for m in members if isinstance(m, (int, float)) and not isinstance(m, bool)]
    if numeric and len(numeric) == len(members):
        return max(numeric) + 1
    candidate = "out-of-envelope"
    existing = {str(member) for member in members}
    while candidate in existing:
        candidate += "-x"
    return candidate


def out_of_domain_value(domain: DomainDescriptor) -> Any:
    """A scalar just outside ``domain``, or ``_MISSING`` when none can be formed."""

    if isinstance(domain, ExactDomain):
        return _perturb_scalar(domain.value)
    if isinstance(domain, EnumDomain):
        return _fresh_scalar_outside(domain.values)
    if isinstance(domain, BooleanDomain):
        if domain.value is None:
            return _MISSING  # both booleans are admitted; nothing safely variable within the kind
        return not domain.value
    if isinstance(domain, GovernedReferenceDomain):
        return _fresh_scalar_outside(domain.allowed_refs)
    if isinstance(domain, NumericIntervalDomain):
        step = 1 if domain.numeric_type is NumericType.INTEGER else 1.0
        upper = int(domain.upper) if domain.numeric_type is NumericType.INTEGER else domain.upper
        return upper + step if domain.upper_closed else upper
    return _MISSING


def remove_path(payload: dict[str, Any], tokens: Sequence[str | int]) -> bool:
    current: Any = payload
    for token in tokens[:-1]:
        if not isinstance(current, dict) or not isinstance(token, str) or token not in current:
            return False
        current = current[token]
    last = tokens[-1]
    if isinstance(current, dict) and isinstance(last, str) and last in current:
        del current[last]
        return True
    return False


def fresh_extra_key(admitted: set[str]) -> str:
    candidate = "out_of_envelope"
    while candidate in admitted:
        candidate += "_x"
    return candidate
