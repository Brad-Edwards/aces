"""Domain-kind dispatch for the realization-envelope relation.

Per-domain-kind logic — finite enumeration, subset comparison (R4), deterministic
witness selection (R5), and out-of-envelope variation (R6) — dispatched by type so
each public entry point stays flat. Kept separate from the flattening/path engine
so neither file exceeds the repo source-size cap and so the type-dispatch tables
live in one place. Pure functions over the contract types; no SDL, diagnostic, or
parser dependency.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from aces_contracts.realization_envelope import (
    BooleanDomain,
    DomainDescriptor,
    DomainScalar,
    EnumDomain,
    ExactDomain,
    GovernedReferenceDomain,
    NumericIntervalDomain,
    NumericType,
    scalar_in_domain,
)

# Sentinel meaning "no out-of-envelope value can be formed within the domain kind".
_MISSING = object()

WitnessSelection = tuple[object, str | None]


# --------------------------------------------------------------------------- #
# Finite enumeration                                                          #
# --------------------------------------------------------------------------- #

_FINITE_MEMBERS: dict[type, Callable[..., list[DomainScalar]]] = {
    ExactDomain: lambda d: [d.value],
    EnumDomain: lambda d: list(d.values),
    BooleanDomain: lambda d: [d.value] if d.value is not None else [False, True],
    GovernedReferenceDomain: lambda d: list(d.allowed_refs),
}


def finite_members(domain: DomainDescriptor) -> list[DomainScalar] | None:
    """Finite value list for a scalar domain, or ``None`` when infinite."""

    factory = _FINITE_MEMBERS.get(type(domain))
    return factory(domain) if factory is not None else None


# --------------------------------------------------------------------------- #
# Subset comparison (R4)                                                      #
# --------------------------------------------------------------------------- #


def _governed_subset(sub: DomainDescriptor, sup: DomainDescriptor) -> bool:
    # Governed references carry an authority that scopes their refs; subsumption
    # must not drop it. Only a same-authority governed-reference domain subsumes;
    # raw refs from a different kind are never authority-scoped.
    if not (isinstance(sub, GovernedReferenceDomain) and isinstance(sup, GovernedReferenceDomain)):
        return False
    if sub.authority != sup.authority:
        return False
    return set(sub.allowed_refs) <= set(sup.allowed_refs)


def _interval_subset(sub: NumericIntervalDomain, sup: NumericIntervalDomain) -> bool:
    if sup.numeric_type is NumericType.INTEGER and sub.numeric_type is NumericType.NUMBER:
        return False
    lower_ok = sup.lower < sub.lower or (sup.lower == sub.lower and (sup.lower_closed or not sub.lower_closed))
    upper_ok = sup.upper > sub.upper or (sup.upper == sub.upper and (sup.upper_closed or not sub.upper_closed))
    return lower_ok and upper_ok


def _numeric_subset(sub: NumericIntervalDomain, sup: DomainDescriptor) -> bool:
    if sub.lower == sub.upper:
        value: DomainScalar = int(sub.lower) if sub.numeric_type is NumericType.INTEGER else sub.lower
        return scalar_in_domain(value, sup)
    if isinstance(sup, NumericIntervalDomain):
        return _interval_subset(sub, sup)
    return False


def domain_subset(sub: DomainDescriptor, sup: DomainDescriptor) -> bool:
    """Return whether every value admitted by ``sub`` is admitted by ``sup``."""

    if isinstance(sub, GovernedReferenceDomain) or isinstance(sup, GovernedReferenceDomain):
        return _governed_subset(sub, sup)
    if isinstance(sub, NumericIntervalDomain):
        return _numeric_subset(sub, sup)
    members = finite_members(sub)
    return members is not None and all(scalar_in_domain(candidate, sup) for candidate in members)


# --------------------------------------------------------------------------- #
# Deterministic witness selection (R5)                                        #
# --------------------------------------------------------------------------- #


def _enum_sort_key(value: DomainScalar) -> tuple[int, str]:
    if isinstance(value, bool):
        kind = 0
    elif isinstance(value, (int, float)):
        kind = 1
    else:
        kind = 2
    return (kind, str(value))


def _integer_witness_value(domain: NumericIntervalDomain) -> WitnessSelection:
    lower = int(domain.lower)
    upper = int(domain.upper)
    candidate = lower if domain.lower_closed else lower + 1
    admissible = candidate < upper or (candidate == upper and domain.upper_closed)
    return (candidate, None) if admissible else (None, "integer interval admits no witness value")


def _real_witness_value(domain: NumericIntervalDomain) -> WitnessSelection:
    # A closed lower bound is itself admissible; an open lower bound on a
    # non-degenerate interval (open degenerate intervals are forbidden by the
    # contract) admits the interior midpoint.
    if domain.lower_closed:
        return domain.lower, None
    return (domain.lower + domain.upper) / 2, None


def _numeric_witness_value(domain: NumericIntervalDomain) -> WitnessSelection:
    if domain.numeric_type is NumericType.INTEGER:
        return _integer_witness_value(domain)
    return _real_witness_value(domain)


_WITNESS_SELECTORS: dict[type, Callable[..., WitnessSelection]] = {
    ExactDomain: lambda d: (d.value, None),
    EnumDomain: lambda d: (min(d.values, key=_enum_sort_key), None),
    BooleanDomain: lambda d: (d.value if d.value is not None else False, None),
    GovernedReferenceDomain: lambda d: (min(d.allowed_refs), None),
    NumericIntervalDomain: _numeric_witness_value,
}


def default_witness_value(domain: DomainDescriptor) -> WitnessSelection:
    """Deterministic default selection for a scalar domain (R5)."""

    selector = _WITNESS_SELECTORS.get(type(domain))
    if selector is None:
        return None, "record domains are not scalar witness leaves"
    return selector(domain)


def positive_probe_values(domain: DomainDescriptor) -> list[DomainScalar]:
    """Deterministic safe values that cover one bounded scalar domain.

    Finite domains enumerate every member. Numeric intervals contribute their
    admissible boundaries; for an open real boundary, where no portable epsilon
    exists, the deterministic witness supplies the safe interior representative.
    """

    members = finite_members(domain)
    if members is not None:
        values = sorted(members, key=_enum_sort_key)
    elif not isinstance(domain, NumericIntervalDomain):
        values = []
    elif domain.numeric_type is NumericType.INTEGER:
        lower = int(domain.lower) + (0 if domain.lower_closed else 1)
        upper = int(domain.upper) - (0 if domain.upper_closed else 1)
        values = [lower] if lower == upper else [lower, upper]
    else:
        values = []
        if domain.lower_closed:
            values.append(domain.lower)
        values.append((domain.lower + domain.upper) / 2)
        if domain.upper_closed:
            values.append(domain.upper)
    return list(dict.fromkeys(values))


# --------------------------------------------------------------------------- #
# Out-of-envelope variation (R6)                                             #
# --------------------------------------------------------------------------- #


def _perturb_scalar(value: DomainScalar) -> DomainScalar:
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return value + 1
    return f"{value}-out-of-envelope"


def _fresh_scalar_outside(members: list[DomainScalar]) -> object:
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


def _interval_out_of_domain(domain: NumericIntervalDomain) -> object:
    step: int | float = 1 if domain.numeric_type is NumericType.INTEGER else 1.0
    upper: int | float = int(domain.upper) if domain.numeric_type is NumericType.INTEGER else domain.upper
    return upper + step if domain.upper_closed else upper


_OUT_OF_DOMAIN: dict[type, Callable[..., object]] = {
    ExactDomain: lambda d: _perturb_scalar(d.value),
    EnumDomain: lambda d: _fresh_scalar_outside(list(d.values)),
    BooleanDomain: lambda d: _MISSING if d.value is None else (not d.value),
    GovernedReferenceDomain: lambda d: _fresh_scalar_outside(list(d.allowed_refs)),
    NumericIntervalDomain: _interval_out_of_domain,
}


def out_of_domain_value(domain: DomainDescriptor) -> object:
    """A scalar just outside ``domain``, or ``_MISSING`` when none can be formed."""

    factory = _OUT_OF_DOMAIN.get(type(domain))
    return factory(domain) if factory is not None else _MISSING


def out_of_domain_candidates(domain: DomainDescriptor, current: object) -> list[object]:
    """Candidate scalars outside ``domain``, preferring SDL enum members.

    A domain-blind synthetic string is not a safe negative probe when the SDL
    field is itself a closed enum.  The instantiated witness exposes that enum
    type, so enumerate its other legal members before falling back to the
    domain-kind perturbation used for open scalar fields.
    """

    candidates: list[object] = []
    if isinstance(current, Enum):
        candidates.extend(member.value for member in type(current) if not scalar_in_domain(member.value, domain))
    fallback = out_of_domain_value(domain)
    if fallback is not _MISSING:
        candidates.append(fallback)
    return list(dict.fromkeys(candidates))
