"""Realization-envelope relation: membership, subsumption, witness, negative probes.

One deterministic semantic relation over :class:`RealizationEnvelopeModel` and
validated SDL instances (ADR-070 §2, ``specs/formal/realization/envelope-semantics.md``
R1-R8). Membership, subsumption, witness generation, and negative-probe generation
share a single domain-comparison and closure engine
(:mod:`aces_sdl._realization_envelope_engine`) — there are no separate author-side,
backend-side, or conformance-side interpretations.

Guarantees:

- **Membership (R1)** — a concrete instance is in an envelope only when it is
  structurally and semantically valid SDL with no unresolved variables *and* every
  effective binding and closed-world scope is satisfied. Invalid SDL is never a
  member.
- **Subsumption (R4)** — ``subsumes(offered, requested)`` is set inclusion reduced
  to bounded per-path domain-subset, closed-scope key-set, and closure-compatibility
  checks. No sampling, approximation, solver, or backend probing.
- **Witness (R5)** — ``witness`` deterministically selects one candidate from the
  envelope's own bindings (no externally supplied scenario) and then runs the
  ordinary ``parse``/``instantiate``/``validate`` pipeline. A witness is one
  executable in-envelope instance; it is not proof of subsumption or backend honesty.
- **Negative probes (R6)** — ``generate_negative_probes`` derives out-of-envelope
  variants of a valid witness for the closed dimensions that can be varied, so
  conformance can require refusal.

Diagnostics name the relation kind, envelope id, SDL path, and domain kind — never
raw sensitive values (R8 / ADR-070 §7).
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.realization_envelope import Posture, RealizationEnvelopeModel, WitnessPolicy, scalar_in_domain
from pydantic import ValidationError

from ._errors import SDLInstantiationError, SDLValidationError
from ._realization_envelope_engine import (
    _MISSING,
    assign_path,
    domain_subset,
    effective_constraints,
    fresh_extra_key,
    navigate,
    normalize_scalar,
    out_of_domain_value,
    overridability_violations,
    present_children,
    remove_path,
    tokenize_path,
    witness_value,
)
from .instantiate import instantiate_scenario
from .scenario import InstantiatedScenario, Scenario
from .validator import SemanticValidator

__all__ = [
    "NegativeProbe",
    "RelationKind",
    "RelationResult",
    "WitnessResult",
    "generate_negative_probes",
    "member",
    "subsumes",
    "witness",
]

_DOMAIN = "realization-envelope"


class RelationKind:
    """Relation kind labels used in diagnostic codes."""

    MEMBERSHIP = "membership"
    SUBSUMPTION = "subsumption"
    WITNESS = "witness"
    NEGATIVE_PROBE = "negative-probe"


@dataclass(frozen=True)
class RelationResult:
    """Result of a membership or subsumption evaluation."""

    holds: bool
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class WitnessResult:
    """A generated witness scenario, or diagnostics proving none can be generated."""

    scenario: InstantiatedScenario | None
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class NegativeProbe:
    """An out-of-envelope variant of a valid witness for a closed dimension."""

    path: str
    domain_kind: str
    variation: str
    payload: dict[str, Any]


def _diag(code: str, address: str, message: str, severity: Severity = Severity.ERROR) -> Diagnostic:
    return Diagnostic(code=f"{_DOMAIN}.{code}", domain=_DOMAIN, address=address, message=message, severity=severity)


def _envelope_r2_diagnostics(envelope: RealizationEnvelopeModel) -> tuple[Diagnostic, ...]:
    """R2 well-formedness: reject a more-specific binding that widens a fixed value.

    An envelope that violates the overridability rule is ill-formed; the relation
    answers deny (not a member / no witness) rather than silently resolving against
    a broader-than-authored set.
    """

    return tuple(
        _diag(
            "invalid.non-overrideable-widen",
            path,
            "a more-specific binding widens a non-overrideable inherited value",
        )
        for path in overridability_violations(envelope)
    )


# --------------------------------------------------------------------------- #
# Membership (R1, R3)                                                          #
# --------------------------------------------------------------------------- #


def member(instance: InstantiatedScenario, envelope: RealizationEnvelopeModel) -> RelationResult:
    """Decide whether ``instance`` is a member of ``envelope`` (R1)."""

    invalid = _envelope_r2_diagnostics(envelope)
    if invalid:
        return RelationResult(False, invalid)

    diagnostics: list[Diagnostic] = []

    if not getattr(instance, "semantic_validated", False):
        try:
            SemanticValidator(instance).validate()
        except SDLValidationError:
            return RelationResult(
                False,
                (
                    _diag(
                        f"{RelationKind.MEMBERSHIP}.invalid-sdl", envelope.id, "instance failed SDL semantic validation"
                    ),
                ),
            )

    constraints, closed = effective_constraints(envelope)
    satisfied = True

    for path, constraint in constraints.items():
        found, value = navigate(instance, tokenize_path(path))
        if not found or value is None:
            # A constrained/exact dimension left unspecified (missing field, or an
            # optional field defaulting to ``None``) is not a member. Domains never
            # admit ``None`` (they range over scalars), so this is always absence.
            satisfied = False
            diagnostics.append(
                _diag(f"{RelationKind.MEMBERSHIP}.path-absent", path, "constrained path is unspecified in the instance")
            )
            continue
        if not scalar_in_domain(normalize_scalar(value), constraint.domain):
            satisfied = False
            diagnostics.append(
                _diag(
                    f"{RelationKind.MEMBERSHIP}.domain-mismatch",
                    path,
                    f"value is not in the {constraint.domain.kind} domain",
                )
            )

    for scope_path in sorted(closed):
        admitted = closed[scope_path]
        if scope_path:
            found, scope_value = navigate(instance, tokenize_path(scope_path))
            if not found:
                continue
        else:
            scope_value = instance
        for child in sorted(present_children(scope_value)):
            if child not in admitted:
                satisfied = False
                address = f"{scope_path}.{child}" if scope_path else child
                diagnostics.append(
                    _diag(
                        f"{RelationKind.MEMBERSHIP}.closed-world-extra",
                        address,
                        "closed-world scope admits no unspecified realizable dimension",
                    )
                )

    return RelationResult(satisfied, tuple(diagnostics))


# --------------------------------------------------------------------------- #
# Subsumption (R4)                                                            #
# --------------------------------------------------------------------------- #


def subsumes(offered: RealizationEnvelopeModel, requested: RealizationEnvelopeModel) -> RelationResult:
    """Decide whether every scenario in ``requested`` is in ``offered`` (R4)."""

    invalid = _envelope_r2_diagnostics(offered) + _envelope_r2_diagnostics(requested)
    if invalid:
        return RelationResult(False, invalid)

    offered_constraints, offered_closed = effective_constraints(offered)
    requested_constraints, requested_closed = effective_constraints(requested)
    diagnostics: list[Diagnostic] = []
    holds = True

    for path in sorted(set(offered_constraints) | set(requested_constraints)):
        offered_constraint = offered_constraints.get(path)
        requested_constraint = requested_constraints.get(path)
        if offered_constraint is None:
            # Offered is open/universal at this path: it admits any requested value.
            continue
        if requested_constraint is None:
            holds = False
            diagnostics.append(
                _diag(
                    f"{RelationKind.SUBSUMPTION}.requested-unconstrained",
                    path,
                    "requested leaves a path open that offered constrains",
                )
            )
            continue
        if not domain_subset(requested_constraint.domain, offered_constraint.domain):
            holds = False
            diagnostics.append(
                _diag(
                    f"{RelationKind.SUBSUMPTION}.domain-not-subset",
                    path,
                    "requested domain is not a subset of the offered domain",
                )
            )

    for scope_path in sorted(offered_closed):
        offered_admitted = offered_closed[scope_path]
        if scope_path not in requested_closed:
            holds = False
            diagnostics.append(
                _diag(
                    f"{RelationKind.SUBSUMPTION}.closure-mismatch",
                    scope_path or "<scenario>",
                    "offered is closed-world where requested is open-world",
                )
            )
            continue
        if not requested_closed[scope_path] <= offered_admitted:
            holds = False
            diagnostics.append(
                _diag(
                    f"{RelationKind.SUBSUMPTION}.closed-extra",
                    scope_path or "<scenario>",
                    "requested admits a closed dimension offered does not",
                )
            )

    return RelationResult(holds, tuple(diagnostics))


# --------------------------------------------------------------------------- #
# Witness generation (R5)                                                     #
# --------------------------------------------------------------------------- #


def witness(envelope: RealizationEnvelopeModel, policy: WitnessPolicy | None = None) -> WitnessResult:
    """Deterministically derive one in-envelope scenario instance (R5)."""

    invalid = _envelope_r2_diagnostics(envelope)
    if invalid:
        return WitnessResult(None, invalid)

    effective_policy = policy if policy is not None else envelope.witness_policy
    constraints, _closed = effective_constraints(envelope)
    payload: dict[str, Any] = {}
    diagnostics: list[Diagnostic] = []

    for path in sorted(constraints):
        value, error = witness_value(constraints[path], effective_policy)
        if error is not None:
            diagnostics.append(_diag(f"{RelationKind.WITNESS}.no-witness", path, error))
            continue
        assign_error = assign_path(payload, tokenize_path(path), value)
        if assign_error is not None:
            diagnostics.append(_diag(f"{RelationKind.WITNESS}.no-witness", path, assign_error))

    if diagnostics:
        return WitnessResult(None, tuple(diagnostics))

    try:
        raw = Scenario.model_validate(payload)
        raw._set_semantic_validated(False)
        instantiated = instantiate_scenario(raw, validate_semantics=True)
    except (ValidationError, SDLValidationError, SDLInstantiationError):
        return WitnessResult(
            None,
            (
                _diag(
                    f"{RelationKind.WITNESS}.invalid",
                    envelope.id,
                    "generated witness did not pass SDL structural/semantic validation "
                    "(the envelope does not fully determine a valid scenario instance)",
                ),
            ),
        )

    return WitnessResult(instantiated, ())


# --------------------------------------------------------------------------- #
# Negative probes (R6)                                                        #
# --------------------------------------------------------------------------- #


def generate_negative_probes(
    envelope: RealizationEnvelopeModel,
) -> tuple[tuple[NegativeProbe, ...], tuple[Diagnostic, ...]]:
    """Derive out-of-envelope probes for the envelope's closed dimensions (R6)."""

    base = witness(envelope)
    if base.scenario is None:
        return (), (
            _diag(
                f"{RelationKind.NEGATIVE_PROBE}.no-witness",
                envelope.id,
                "cannot derive a witness base for negative probes",
            ),
        )

    # ``mode="json"`` yields plain JSON scalars (enums as their string value), so
    # each probe payload is a portable, re-parseable scenario request.
    base_payload = base.scenario.model_dump(mode="json", by_alias=True)
    constraints, closed = effective_constraints(envelope)
    probes: list[NegativeProbe] = []

    for path in sorted(constraints):
        constraint = constraints[path]
        variation_value = out_of_domain_value(constraint.domain)
        if variation_value is _MISSING:
            continue
        payload = deepcopy(base_payload)
        if assign_path(payload, tokenize_path(path), variation_value) is not None:
            continue
        probes.append(
            NegativeProbe(
                path=path, domain_kind=constraint.domain.kind, variation="value-outside-domain", payload=payload
            )
        )

        if constraint.posture is Posture.EXACT:
            omitted = deepcopy(base_payload)
            if remove_path(omitted, tokenize_path(path)):
                probes.append(
                    NegativeProbe(
                        path=path,
                        domain_kind=constraint.domain.kind,
                        variation="omitted-required-exact",
                        payload=omitted,
                    )
                )

    for scope_path in sorted(closed):
        admitted = closed[scope_path]
        extra_key = fresh_extra_key(admitted)
        payload = deepcopy(base_payload)
        tokens = tokenize_path(scope_path) + [extra_key] if scope_path else [extra_key]
        if assign_path(payload, tokens, "out-of-envelope") is not None:
            continue
        address = f"{scope_path}.{extra_key}" if scope_path else extra_key
        probes.append(
            NegativeProbe(path=address, domain_kind="closed-scope", variation="extra-dimension", payload=payload)
        )

    return tuple(probes), ()
