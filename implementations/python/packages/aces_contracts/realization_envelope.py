"""Realization-envelope expression contract (ADR-070, envelope-semantics.md).

A realization envelope is a closed, versioned expression that denotes a *set* of
SDL scenario instances. The same expression is used in both directions: an author
describes an acceptable scenario family, and a backend describes the family it can
realize. The membership / subsumption / witness / negative-probe relation over
this contract lives in :mod:`aces_sdl.realization_envelope`.

The model is deliberately *closed* (``extra="forbid"`` plus a finite discriminated
union of domain kinds). That closedness is the portability guarantee of
``envelope-semantics.md`` R3 / ADR-070 §3: arbitrary Python predicates, backend
callbacks, external queries, unbounded regex, recursion, and non-linear arithmetic
are simply not representable, which keeps membership and subsumption reducible to
local structural checks and witness generation deterministic.

Schema publication (a bundled ``contracts/schemas/`` artifact with a publication
ledger) and backend-manifest carriage are downstream siblings, not this issue:
``envelope-semantics.md`` "Realization Status" lists the *schema carrier* and
*manifest evolution* separately from the *relation helper*, ADR-070 §5 defers
manifest carriage to a schema-evolution question, and the issue-668 preflight note
records "the current unpublished envelope shape". This module therefore ships the
unpublished, first-class contract shape the relation operates over.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from aces_contracts.contracts import ContractModel, NonEmptyString

# Version identity for the envelope expression. Kept local to this module rather
# than in ``versions.py`` (which is scoped to *published* external contracts):
# the envelope schema is intentionally unpublished at this stage — schema
# publication and manifest carriage are downstream siblings (module docstring).
REALIZATION_ENVELOPE_SCHEMA_VERSION = "realization-envelope/v1"

__all__ = [
    "REALIZATION_ENVELOPE_SCHEMA_VERSION",
    "BooleanDomain",
    "Closure",
    "ClosureOverlay",
    "DomainDescriptor",
    "EnumDomain",
    "EnvelopeBinding",
    "EnvelopeScope",
    "ExactDomain",
    "GovernedReferenceDomain",
    "NumericIntervalDomain",
    "NumericType",
    "Posture",
    "RealizationEnvelopeModel",
    "RecordDomain",
    "WitnessPolicy",
    "scalar_in_domain",
    "scalar_matches_numeric_type",
]

# Portable envelope values are JSON scalars. ``bool`` is intentionally distinct
# from ``int`` here (see ``scalar_matches_numeric_type``); Pydantic preserves the
# authored Python type on a closed model, so ``True`` never collapses to ``1``.
DomainScalar = bool | int | float | str


class EnvelopeScope(str, Enum):
    """Semantic extent where a posture or closure applies (most local first)."""

    FIELD = "field"
    NODE = "node"
    TOPOLOGY = "topology"
    APP = "app"
    SCENARIO = "scenario"


class Posture(str, Enum):
    """Author/backend intent for a bound value or child scope."""

    OPEN = "open"
    CONSTRAINED = "constrained"
    EXACT = "exact"


class Closure(str, Enum):
    """Whether unspecified realizable dimensions under a scope are admitted."""

    OPEN_WORLD = "open-world"
    CLOSED_WORLD = "closed-world"


class NumericType(str, Enum):
    """Declared numeric type for a numeric-interval domain."""

    INTEGER = "integer"
    NUMBER = "number"


class ExactDomain(ContractModel):
    """A singleton value set: values equal to ``value``."""

    kind: Literal["exact"] = "exact"
    value: DomainScalar


class EnumDomain(ContractModel):
    """A finite value set: values equal to one listed member."""

    kind: Literal["enum"] = "enum"
    values: list[DomainScalar] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_unique(self) -> EnumDomain:
        # ``list`` (not ``set``) preserves authored order and the bool/int
        # distinction; dedupe on a type-tagged key so ``True`` and ``1`` stay
        # separate members.
        seen: set[tuple[str, object]] = set()
        for member in self.values:
            key = (type(member).__name__, member)
            if key in seen:
                raise ValueError("enum domain values must be unique")
            seen.add(key)
        return self


class BooleanDomain(ContractModel):
    """Booleans: both ``true``/``false``, or an exact boolean when ``value`` set."""

    kind: Literal["boolean"] = "boolean"
    value: bool | None = None


class NumericIntervalDomain(ContractModel):
    """Numbers of ``numeric_type`` inside a bounded interval.

    Both endpoints are required (the fragment admits only *bounded* intervals,
    ``envelope-semantics.md`` R3). An integer interval requires integral
    endpoints. Empty intervals are rejected at construction.
    """

    kind: Literal["numeric-interval"] = "numeric-interval"
    numeric_type: NumericType
    lower: float
    upper: float
    lower_closed: bool = True
    upper_closed: bool = True

    @model_validator(mode="after")
    def _validate_interval(self) -> NumericIntervalDomain:
        if self.numeric_type is NumericType.INTEGER:
            if self.lower != int(self.lower) or self.upper != int(self.upper):
                raise ValueError("integer numeric-interval endpoints must be integral")
        if self.lower > self.upper:
            raise ValueError("numeric-interval lower endpoint must not exceed upper")
        if self.lower == self.upper and not (self.lower_closed and self.upper_closed):
            raise ValueError("degenerate numeric-interval must be closed on both endpoints")
        return self


class GovernedReferenceDomain(ContractModel):
    """References in a finite governed set under a named authority."""

    kind: Literal["governed-reference"] = "governed-reference"
    authority: NonEmptyString
    allowed_refs: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_unique(self) -> GovernedReferenceDomain:
        if len(self.allowed_refs) != len(set(self.allowed_refs)):
            raise ValueError("governed-reference allowed_refs must be unique")
        return self


class RecordDomain(ContractModel):
    """Product structure: each declared field references another named domain.

    ``extra`` controls undeclared fields: ``False`` (closed) rejects any field not
    named in ``fields``; ``True`` (open) admits them. Field values reference domain
    names resolved against the envelope's ``domains`` map, keeping the structure
    acyclic and free of inline recursion.
    """

    kind: Literal["record"] = "record"
    fields: dict[NonEmptyString, NonEmptyString] = Field(min_length=1)
    extra: bool = False


DomainDescriptor = Annotated[
    ExactDomain | EnumDomain | BooleanDomain | NumericIntervalDomain | GovernedReferenceDomain | RecordDomain,
    Field(discriminator="kind"),
]


class EnvelopeBinding(ContractModel):
    """Binds an SDL path (or governed scope ref) to a domain at a scope.

    ``domain`` names a descriptor in the envelope's ``domains`` map and is required
    for ``constrained`` / ``exact`` posture and forbidden for ``open`` posture (an
    open value is left to a downstream realizer). ``overrideable`` allows a
    more-specific binding to widen a value an enclosing closed scope fixed
    (``envelope-semantics.md`` R2).
    """

    path: NonEmptyString
    scope: EnvelopeScope
    posture: Posture
    domain: str | None = None
    overrideable: bool = False

    @model_validator(mode="after")
    def _validate_posture_domain(self) -> EnvelopeBinding:
        if self.posture is Posture.OPEN and self.domain is not None:
            raise ValueError("open posture binding must not name a domain")
        if self.posture in (Posture.CONSTRAINED, Posture.EXACT) and not self.domain:
            raise ValueError(f"{self.posture.value} posture binding must name a domain")
        return self


class ClosureOverlay(ContractModel):
    """Declares open-world or closed-world closure at a scope path."""

    path: str = ""
    scope: EnvelopeScope
    closure: Closure


class WitnessPolicy(ContractModel):
    """Deterministic default-selection policy for witness generation.

    ``selections`` overrides the default choice for named domains (each value must
    be a member of the referenced domain); ``seed`` records the selection basis for
    reproducibility. Neither introduces randomness: witness generation stays a pure
    function of ``(envelope, policy)``.
    """

    seed: str | None = None
    selections: dict[NonEmptyString, DomainScalar] = Field(default_factory=dict)


class RealizationEnvelopeModel(ContractModel):
    """A versioned expression denoting a set of SDL scenario instances."""

    schema_version: Literal["realization-envelope/v1"] = "realization-envelope/v1"
    id: NonEmptyString
    scope: EnvelopeScope
    domains: dict[NonEmptyString, DomainDescriptor] = Field(default_factory=dict)
    bindings: list[EnvelopeBinding] = Field(default_factory=list)
    closure: list[ClosureOverlay] = Field(default_factory=list)
    witness_policy: WitnessPolicy | None = None
    source_ref: str | None = None
    contract_id: str | None = None
    digest: str | None = None

    @model_validator(mode="after")
    def _validate_envelope(self) -> RealizationEnvelopeModel:
        self._validate_domain_references()
        self._validate_acyclic_records()
        self._validate_bindings()
        self._validate_witness_policy()
        return self

    def _validate_domain_references(self) -> None:
        for name, descriptor in self.domains.items():
            if isinstance(descriptor, RecordDomain):
                for field_name, domain_name in descriptor.fields.items():
                    if domain_name not in self.domains:
                        raise ValueError(
                            f"record domain '{name}' field '{field_name}' references unknown domain '{domain_name}'"
                        )

    def _validate_acyclic_records(self) -> None:
        # DFS over record field references; ADR-070 §3 admits only acyclic
        # record/product structure.
        visiting: set[str] = set()
        done: set[str] = set()

        def visit(name: str) -> None:
            if name in done:
                return
            if name in visiting:
                raise ValueError(f"record domain reference cycle through '{name}'")
            descriptor = self.domains.get(name)
            visiting.add(name)
            if isinstance(descriptor, RecordDomain):
                for domain_name in descriptor.fields.values():
                    visit(domain_name)
            visiting.discard(name)
            done.add(name)

        for name in self.domains:
            visit(name)

    def _validate_bindings(self) -> None:
        seen: dict[tuple[str, str], EnvelopeBinding] = {}
        for binding in self.bindings:
            if binding.domain is not None and binding.domain not in self.domains:
                raise ValueError(f"binding path '{binding.path}' references unknown domain '{binding.domain}'")
            if binding.posture is Posture.EXACT and binding.domain is not None:
                if not _is_singleton_domain(self.domains[binding.domain]):
                    raise ValueError(f"exact posture binding path '{binding.path}' requires a singleton domain")
            key = (binding.path, binding.scope.value)
            existing = seen.get(key)
            if existing is not None and (existing.domain, existing.posture) != (binding.domain, binding.posture):
                # Equal-specificity, incompatible binding is invalid, not
                # merge-order dependent (envelope-semantics.md R2).
                raise ValueError(
                    f"conflicting equal-specificity bindings for path '{binding.path}' at scope '{binding.scope.value}'"
                )
            seen[key] = binding

    def _validate_witness_policy(self) -> None:
        if self.witness_policy is None:
            return
        for domain_name, value in self.witness_policy.selections.items():
            descriptor = self.domains.get(domain_name)
            if descriptor is None:
                raise ValueError(f"witness policy selects unknown domain '{domain_name}'")
            if not scalar_in_domain(value, descriptor):
                raise ValueError(f"witness policy selection for domain '{domain_name}' is not a domain member")


def _is_singleton_domain(descriptor: DomainDescriptor) -> bool:
    if isinstance(descriptor, ExactDomain):
        return True
    if isinstance(descriptor, EnumDomain):
        return len(descriptor.values) == 1
    if isinstance(descriptor, BooleanDomain):
        return descriptor.value is not None
    if isinstance(descriptor, NumericIntervalDomain):
        return descriptor.lower == descriptor.upper
    if isinstance(descriptor, GovernedReferenceDomain):
        return len(descriptor.allowed_refs) == 1
    return False


def scalar_matches_numeric_type(value: object, numeric_type: NumericType) -> bool:
    """Return whether ``value`` is a number of the declared numeric type.

    ``bool`` is never a number here (it is its own domain kind).
    """
    if isinstance(value, bool):
        return False
    if numeric_type is NumericType.INTEGER:
        return isinstance(value, int)
    return isinstance(value, (int, float))


def scalar_in_domain(value: object, descriptor: DomainDescriptor) -> bool:
    """Structural membership for the scalar domain kinds.

    This is the single scalar-membership engine, hosted in the contract layer so
    both the contract's own ``witness_policy`` validation and the higher-level
    relation in ``aces_sdl.realization_envelope`` (which cannot be imported here
    without a dependency cycle) share one definition. Record domains are product
    structures, not scalars, and are handled by the relation engine.
    """
    if isinstance(descriptor, ExactDomain):
        return type(value) is type(descriptor.value) and value == descriptor.value
    if isinstance(descriptor, EnumDomain):
        return any(type(value) is type(member) and value == member for member in descriptor.values)
    if isinstance(descriptor, BooleanDomain):
        if not isinstance(value, bool):
            return False
        return descriptor.value is None or value == descriptor.value
    if isinstance(descriptor, NumericIntervalDomain):
        if not scalar_matches_numeric_type(value, descriptor.numeric_type):
            return False
        numeric = float(value)
        lower_ok = numeric >= descriptor.lower if descriptor.lower_closed else numeric > descriptor.lower
        upper_ok = numeric <= descriptor.upper if descriptor.upper_closed else numeric < descriptor.upper
        return lower_ok and upper_ok
    if isinstance(descriptor, GovernedReferenceDomain):
        return isinstance(value, str) and value in descriptor.allowed_refs
    return False
