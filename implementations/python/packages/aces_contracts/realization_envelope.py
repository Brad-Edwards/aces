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

Issue #100 publishes the expression inside a configuration-bound backend carrier
at ``contracts/schemas/realization-envelope/realization-envelope-v1.json``. The carrier
adds typed material-configuration, transformation, support, and observation
disclosures while the relation continues to operate on the same expression.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from aces_contracts.bounded_domains import (
    BooleanDomain,
    DomainDescriptor,
    DomainScalar,
    EnumDomain,
    ExactDomain,
    GovernedReferenceDomain,
    NumericIntervalDomain,
    NumericType,
    RecordDomain,
    scalar_in_domain,
    scalar_matches_numeric_type,
)
from aces_contracts.contracts import ContractModel, NonEmptyString, RealizationEnvelopeIdentityModel
from aces_contracts.versions import REALIZATION_ENVELOPE_SCHEMA_VERSION
from aces_contracts.vocabulary import Closure

__all__ = [
    "BackendRealizationEnvelopeModel",
    "REALIZATION_ENVELOPE_SCHEMA_VERSION",
    "BooleanDomain",
    "Closure",
    "ClosureOverlay",
    "ConcernDisposition",
    "DomainDescriptor",
    "EnumDomain",
    "EnvelopeBinding",
    "EnvelopeScope",
    "ExactDomain",
    "GovernedReferenceDomain",
    "NumericIntervalDomain",
    "NumericType",
    "ObservationStrength",
    "Posture",
    "RealizationEnvelopeModel",
    "RealizationEnvelopeIdentityModel",
    "RealizationConcern",
    "RealizationConcernDisclosureModel",
    "RealizerConfigurationModel",
    "IntegerBoundsModel",
    "RecordDomain",
    "WitnessPolicy",
    "TransformationKind",
    "scalar_in_domain",
    "scalar_matches_numeric_type",
    "realization_envelope_digest",
    "realizer_configuration_digest",
    "scope_specificity",
    "validate_backend_realization_envelope",
]

_ENVELOPE_PATH_RE = re.compile(r"^[^.\[\]]+(?:\.[^.\[\]]+|\[\d+\])*$")


def _require_envelope_path(path: str, *, allow_root: bool) -> None:
    if allow_root and path == "":
        return
    if _ENVELOPE_PATH_RE.fullmatch(path) is None:
        raise ValueError("path must use the complete canonical SDL path grammar")


class EnvelopeScope(str, Enum):
    """Semantic extent where a posture or closure applies (most local first)."""

    FIELD = "field"
    NODE = "node"
    TOPOLOGY = "topology"
    APP = "app"
    SCENARIO = "scenario"


_SCOPE_SPECIFICITY = {
    EnvelopeScope.SCENARIO: 0,
    EnvelopeScope.TOPOLOGY: 1,
    EnvelopeScope.APP: 1,
    EnvelopeScope.NODE: 2,
    EnvelopeScope.FIELD: 3,
}


def scope_specificity(scope: EnvelopeScope) -> int:
    """Return semantic specificity; topology and app are sibling scopes."""

    return _SCOPE_SPECIFICITY[scope]


class Posture(str, Enum):
    """Author/backend intent for a bound value or child scope."""

    OPEN = "open"
    CONSTRAINED = "constrained"
    EXACT = "exact"


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
        _require_envelope_path(self.path, allow_root=False)
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

    @model_validator(mode="after")
    def _validate_path(self) -> ClosureOverlay:
        _require_envelope_path(self.path, allow_root=True)
        return self


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
        self._validate_binding_entries()
        self._validate_closure_entries()

    def _validate_binding_entries(self) -> None:
        seen: dict[tuple[str, int], EnvelopeBinding] = {}
        for binding in self.bindings:
            if binding.domain is not None and binding.domain not in self.domains:
                raise ValueError(f"binding path '{binding.path}' references unknown domain '{binding.domain}'")
            if binding.posture is Posture.EXACT and binding.domain is not None:
                if not _is_singleton_domain(self.domains[binding.domain]):
                    raise ValueError(f"exact posture binding path '{binding.path}' requires a singleton domain")
            key = (binding.path, scope_specificity(binding.scope))
            existing = seen.get(key)
            if existing is not None and (
                existing.domain,
                existing.posture,
                existing.overrideable,
            ) != (
                binding.domain,
                binding.posture,
                binding.overrideable,
            ):
                # Equal-specificity, incompatible binding is invalid, not
                # merge-order dependent (envelope-semantics.md R2).
                raise ValueError(
                    f"conflicting equal-specificity bindings for path '{binding.path}' "
                    f"at equivalent scopes '{existing.scope.value}' and '{binding.scope.value}'"
                )
            seen[key] = binding

    def _validate_closure_entries(self) -> None:
        seen_closure: dict[tuple[str, int], tuple[EnvelopeScope, Closure]] = {}
        for overlay in self.closure:
            key = (overlay.path, scope_specificity(overlay.scope))
            existing_closure = seen_closure.get(key)
            if existing_closure is not None and existing_closure[1] is not overlay.closure:
                raise ValueError(
                    f"conflicting equal-specificity closure overlays for path '{overlay.path}' "
                    f"at equivalent scopes '{existing_closure[0].value}' and '{overlay.scope.value}'"
                )
            seen_closure[key] = (overlay.scope, overlay.closure)

    def _validate_witness_policy(self) -> None:
        if self.witness_policy is None:
            return
        for domain_name, value in self.witness_policy.selections.items():
            descriptor = self.domains.get(domain_name)
            if descriptor is None:
                raise ValueError(f"witness policy selects unknown domain '{domain_name}'")
            if not scalar_in_domain(value, descriptor):
                raise ValueError(f"witness policy selection for domain '{domain_name}' is not a domain member")


# Per-domain-kind predicates, dispatched by type to keep the public entry points
# flat (SonarCloud caps returns/complexity per function; type-dispatch chains
# otherwise trip S1142 / cognitive-complexity).
_SINGLETON_DOMAIN_CHECKS: dict[type, Callable[..., bool]] = {
    ExactDomain: lambda descriptor: True,
    EnumDomain: lambda descriptor: len(descriptor.values) == 1,
    BooleanDomain: lambda descriptor: descriptor.value is not None,
    NumericIntervalDomain: lambda descriptor: descriptor.lower == descriptor.upper,
    GovernedReferenceDomain: lambda descriptor: len(descriptor.allowed_refs) == 1,
}


def _is_singleton_domain(descriptor: DomainDescriptor) -> bool:
    check = _SINGLETON_DOMAIN_CHECKS.get(type(descriptor))
    return bool(check(descriptor)) if check is not None else False


# Import after the expression types are defined: the carrier embeds
# RealizationEnvelopeModel and this module preserves the original public API.
from aces_contracts.realization_envelope_carrier import (
    BackendRealizationEnvelopeModel,
    ConcernDisposition,
    IntegerBoundsModel,
    ObservationStrength,
    RealizationConcern,
    RealizationConcernDisclosureModel,
    RealizerConfigurationModel,
    TransformationKind,
    realization_envelope_digest,
    realizer_configuration_digest,
    validate_backend_realization_envelope,
)
