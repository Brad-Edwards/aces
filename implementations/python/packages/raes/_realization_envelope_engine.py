"""Internal engine for the realization-envelope relation.

SDL-path navigation, most-specific-wins constraint flattening (R2), and closure
bookkeeping shared by the four relation kinds in
:mod:`raes.realization_envelope`. Domain-kind dispatch (subset, witness,
variation) lives in :mod:`raes._realization_envelope_domains`. Kept separate
from the public relation module so neither file exceeds the repo source-size cap.
This module has no diagnostic, parser, or validator dependency; those live in the
public module.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from aces_contracts.realization_envelope import (
    Closure,
    ClosureOverlay,
    DomainDescriptor,
    EnvelopeBinding,
    Posture,
    RealizationEnvelopeModel,
    RecordDomain,
    WitnessPolicy,
    scope_specificity,
)
from pydantic import BaseModel

from ._realization_envelope_domains import default_witness_value, domain_subset

PathToken = str | int


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
_FULL_PATH_RE = re.compile(r"^[^.\[\]]+(?:\.[^.\[\]]+|\[\d+\])*$")


def tokenize_path(path: str) -> list[PathToken]:
    """Split an SDL path into attribute/key segments and ``[i]`` list indices."""

    if _FULL_PATH_RE.fullmatch(path) is None:
        raise ValueError("path must use the complete canonical SDL path grammar")
    tokens: list[PathToken] = []
    for raw in _PATH_TOKEN_RE.findall(path):
        tokens.append(int(raw[1:-1]) if raw.startswith("[") else raw)
    return tokens


def _path_tokens(path: str) -> tuple[PathToken, ...]:
    return tuple(tokenize_path(path)) if path else ()


def _is_same_or_descendant(path: str, ancestor: str) -> bool:
    path_tokens = _path_tokens(path)
    ancestor_tokens = _path_tokens(ancestor)
    return len(ancestor_tokens) <= len(path_tokens) and path_tokens[: len(ancestor_tokens)] == ancestor_tokens


def _render_path(tokens: Sequence[PathToken]) -> str:
    rendered = ""
    for token in tokens:
        if isinstance(token, int):
            segment = f"[{token}]"
        elif rendered:
            segment = f".{token}"
        else:
            segment = token
        rendered += segment
    return rendered


def _navigate_step(current: object, token: PathToken) -> tuple[bool, object]:
    result: tuple[bool, object] = (False, None)
    if isinstance(token, int):
        if isinstance(current, Sequence) and not isinstance(current, (str, bytes)) and 0 <= token < len(current):
            result = (True, current[token])
    elif isinstance(current, BaseModel) and token in type(current).model_fields:
        result = (True, getattr(current, token))
    elif isinstance(current, Mapping) and token in current:
        result = (True, current[token])
    return result


def navigate(root: object, tokens: Sequence[PathToken]) -> tuple[bool, object]:
    """Resolve ``tokens`` against a model/mapping/sequence tree."""

    current: object = root
    for token in tokens:
        found, current = _navigate_step(current, token)
        if not found:
            return False, None
    return True, current


def normalize_scalar(value: object) -> object:
    """Reduce an SDL model value to a portable scalar for domain comparison.

    SDL string enums (e.g. ``OSFamily``, ``NodeType``) navigate out as ``Enum``
    instances; envelope domains carry plain JSON scalars. Comparing them requires
    the enum's underlying value. ``bool`` is preserved (it is its own domain kind).
    """

    return value.value if isinstance(value, Enum) else value


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
        return _model_present_children(value)
    if isinstance(value, Mapping):
        return {str(key) for key in value}
    return set()


def _model_present_children(model: BaseModel) -> set[str]:
    present: set[str] = set()
    for name, info in type(model).model_fields.items():
        schema_extra = info.json_schema_extra
        if isinstance(schema_extra, Mapping) and schema_extra.get("x-aces-realization-dimension") is False:
            continue
        child = getattr(model, name)
        if not _is_nonempty(child):
            continue
        if info.is_required() or child != info.get_default(call_default_factory=True):
            present.add(name)
    return present


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
        domain=domain, domain_name=domain_name, posture=posture, overrideable=overrideable
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
        if binding.domain is not None:
            _collect_record_closures(binding.path, envelope.domains[binding.domain], envelope, closed)
    return closed


def _prefixed_paths(constraints: dict[str, LeafConstraint], prefix: str) -> list[str]:
    return [path for path in constraints if _is_same_or_descendant(path, prefix)]


def _apply_binding(
    binding: EnvelopeBinding,
    envelope: RealizationEnvelopeModel,
    constraints: dict[str, LeafConstraint],
) -> None:
    if binding.posture is Posture.OPEN:
        for path in _prefixed_paths(constraints, binding.path):
            del constraints[path]
        return
    if binding.domain is None:
        return
    _expand_constraint(
        binding.path,
        envelope.domains[binding.domain],
        binding.domain,
        binding.posture,
        binding.overrideable,
        envelope,
        constraints,
    )


def _add_admitted_children(envelope: RealizationEnvelopeModel, scope_path: str, admitted: set[str]) -> None:
    scope_tokens = _path_tokens(scope_path)
    for binding in envelope.bindings:
        binding_tokens = _path_tokens(binding.path)
        if len(binding_tokens) < len(scope_tokens) or binding_tokens[: len(scope_tokens)] != scope_tokens:
            continue
        remainder = binding_tokens[len(scope_tokens) :]
        if remainder and isinstance(remainder[0], str):
            admitted.add(remainder[0])


def _open_closed_subtree(closed: dict[str, set[str]], open_path: str) -> None:
    """Shadow inherited closure only along ``open_path``, leaving siblings closed."""

    for path in tuple(closed):
        if _is_same_or_descendant(path, open_path):
            del closed[path]
    open_tokens = _path_tokens(open_path)
    ancestors = tuple(path for path in closed if _is_same_or_descendant(open_path, path))
    for ancestor in ancestors:
        current = _path_tokens(ancestor)
        remaining = open_tokens[len(current) :]
        for index, token in enumerate(remaining):
            current_path = _render_path(current)
            if isinstance(token, str):
                closed.setdefault(current_path, set()).add(token)
            current = (*current, token)
            if index < len(remaining) - 1:
                closed.setdefault(_render_path(current), set())


def effective_constraints(
    envelope: RealizationEnvelopeModel,
) -> tuple[dict[str, LeafConstraint], dict[str, set[str]]]:
    """Flatten bindings into per-path scalar constraints and closed-scope key sets.

    Most-specific-wins (R2) is realized by processing bindings shortest-path-first
    so a more-specific explicit binding overwrites a record expansion, and an
    ``open`` binding removes any constraint at (and under) its path.
    """

    constraints: dict[str, LeafConstraint] = {}
    for binding in sorted(envelope.bindings, key=_binding_specificity):
        _apply_binding(binding, envelope, constraints)

    closed = _record_closed_scopes(envelope)
    for overlay in sorted(envelope.closure, key=_overlay_specificity):
        if overlay.closure is Closure.CLOSED_WORLD:
            _add_admitted_children(envelope, overlay.path, closed.setdefault(overlay.path, set()))
        else:
            _open_closed_subtree(closed, overlay.path)
    return constraints, closed


def _binding_specificity(binding: EnvelopeBinding) -> tuple[int, int]:
    return len(tokenize_path(binding.path)), scope_specificity(binding.scope)


def _overlay_specificity(overlay: ClosureOverlay) -> tuple[int, int]:
    return len(tokenize_path(overlay.path)) if overlay.path else 0, scope_specificity(overlay.scope)


# --------------------------------------------------------------------------- #
# Overridability (R2 well-formedness)                                          #
# --------------------------------------------------------------------------- #


def _record_open_widenings(constraints: dict[str, LeafConstraint], prefix: str, violations: list[str]) -> None:
    for path in _prefixed_paths(constraints, prefix):
        if not constraints[path].overrideable:
            # open posture widens a fixed inherited value
            violations.append(path)
        del constraints[path]


def _record_overwrite_widenings(
    binding: EnvelopeBinding,
    envelope: RealizationEnvelopeModel,
    constraints: dict[str, LeafConstraint],
    violations: list[str],
) -> None:
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
        # A narrowing (subset) overwrite is allowed; a non-subset overwrite of a
        # non-overrideable inherited value is a forbidden widening.
        if (
            existing is not None
            and not existing.overrideable
            and not domain_subset(new_constraint.domain, existing.domain)
        ):
            violations.append(path)
        constraints[path] = new_constraint


def overridability_violations(envelope: RealizationEnvelopeModel) -> list[str]:
    """Paths where a more-specific binding illegally widens a fixed inherited value.

    Envelope-semantics.md R2: a more-specific binding may not widen a value an
    enclosing scope fixed (or excluded) unless the enclosing binding marked that
    child ``overrideable``. Replays the same shortest-path-first order as
    :func:`effective_constraints`. An empty list means the envelope is well-formed.
    """

    violations: list[str] = []
    constraints: dict[str, LeafConstraint] = {}
    for binding in sorted(envelope.bindings, key=_binding_specificity):
        if binding.posture is Posture.OPEN:
            _record_open_widenings(constraints, binding.path, violations)
        elif binding.domain is not None:
            _record_overwrite_widenings(binding, envelope, constraints, violations)
    return violations


# --------------------------------------------------------------------------- #
# Witness assembly helpers                                                     #
# --------------------------------------------------------------------------- #


def witness_value(constraint: LeafConstraint, policy: WitnessPolicy | None) -> tuple[object, str | None]:
    """Selected witness value for one leaf, honoring an explicit policy override (R5)."""

    if policy is not None and constraint.domain_name in policy.selections:
        return policy.selections[constraint.domain_name], None
    return default_witness_value(constraint.domain)


def assign_path(payload: dict[str, object], tokens: Sequence[PathToken], value: object) -> str | None:
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


def remove_path(payload: dict[str, object], tokens: Sequence[PathToken]) -> bool:
    """Delete the leaf at ``tokens`` from a nested dict payload; return whether removed."""

    current: object = payload
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
    """A child key not in ``admitted`` (for closed-scope extra-dimension probes)."""

    candidate = "out_of_envelope"
    while candidate in admitted:
        candidate += "_x"
    return candidate
