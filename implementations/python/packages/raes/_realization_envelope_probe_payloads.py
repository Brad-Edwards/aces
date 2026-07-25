"""Structurally plausible payload candidates for realization-envelope probes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum

from raes_contracts.realization_envelope import Posture
from pydantic import BaseModel

from ._realization_envelope_domains import out_of_domain_candidates
from ._realization_envelope_engine import (
    LeafConstraint,
    assign_path,
    fresh_extra_key,
    navigate,
    remove_path,
    tokenize_path,
)
from .scenario import InstantiatedScenario


@dataclass(frozen=True)
class ProbePayloadCandidate:
    """One not-yet-validated negative-probe payload."""

    path: str
    domain_kind: str
    variation: str
    payload: dict[str, object]


def _minimal_discriminator_payload(
    base_payload: dict[str, object], path: str, variation_value: object
) -> dict[str, object] | None:
    """Return a minimal variant for a nested ``type`` discriminator."""

    tokens = tokenize_path(path)
    if len(tokens) < 2 or tokens[-1] != "type":
        return None
    payload = deepcopy(base_payload)
    if assign_path(payload, tokens[:-1], {"type": variation_value}) is not None:
        return None
    return payload


def value_probe_payloads(
    base_payload: dict[str, object],
    base_scenario: InstantiatedScenario,
    path: str,
    constraint: LeafConstraint,
) -> list[ProbePayloadCandidate]:
    """Build candidates for one constrained scalar path."""

    probes: list[ProbePayloadCandidate] = []
    tokens = tokenize_path(path)
    found, current = navigate(base_scenario, tokens)
    for variation_value in out_of_domain_candidates(constraint.domain, current if found else None):
        payload = deepcopy(base_payload)
        if assign_path(payload, tokens, variation_value) is None:
            probes.append(ProbePayloadCandidate(path, constraint.domain.kind, "value-outside-domain", payload))
        minimal = _minimal_discriminator_payload(base_payload, path, variation_value)
        if minimal is not None:
            probes.append(ProbePayloadCandidate(path, constraint.domain.kind, "value-outside-domain", minimal))
    if constraint.posture is Posture.EXACT:
        omitted = deepcopy(base_payload)
        if remove_path(omitted, tokens):
            probes.append(ProbePayloadCandidate(path, constraint.domain.kind, "omitted-required-exact", omitted))
    return probes


def _extra_dimension_values(current: object) -> list[object]:
    if isinstance(current, Enum):
        values: list[object] = [member.value for member in type(current) if member is not current]
    elif isinstance(current, bool):
        values = [not current]
    elif isinstance(current, (int, float)):
        values = [current + 1]
    elif isinstance(current, str):
        values = ["out-of-envelope" if current != "out-of-envelope" else "out-of-envelope-x"]
    elif isinstance(current, dict):
        values = [{"out-of-envelope": "out-of-envelope"}]
    elif isinstance(current, list):
        values = [["out-of-envelope"]]
    else:
        values = []
    return values


def _model_extra_dimension_payloads(
    base_payload: dict[str, object],
    scope_path: str,
    scope_value: BaseModel,
    admitted: set[str],
) -> list[ProbePayloadCandidate]:
    probes: list[ProbePayloadCandidate] = []
    for field_name in sorted(set(type(scope_value).model_fields) - admitted):
        for variation_value in _extra_dimension_values(getattr(scope_value, field_name)):
            payload = deepcopy(base_payload)
            tokens = tokenize_path(scope_path) + [field_name] if scope_path else [field_name]
            if assign_path(payload, tokens, variation_value) is None:
                address = f"{scope_path}.{field_name}" if scope_path else field_name
                probes.append(ProbePayloadCandidate(address, "closed-scope", "extra-dimension", payload))
    return probes


def closed_scope_probe_payloads(
    base_payload: dict[str, object],
    base_scenario: InstantiatedScenario,
    closed: dict[str, set[str]],
) -> list[ProbePayloadCandidate]:
    """Build candidates for SDL fields excluded by each closed scope."""

    probes: list[ProbePayloadCandidate] = []
    for scope_path in sorted(closed):
        scope_value = base_scenario if not scope_path else navigate(base_scenario, tokenize_path(scope_path))[1]
        if isinstance(scope_value, BaseModel):
            probes.extend(_model_extra_dimension_payloads(base_payload, scope_path, scope_value, closed[scope_path]))
            continue
        extra_key = fresh_extra_key(closed[scope_path])
        payload = deepcopy(base_payload)
        tokens = tokenize_path(scope_path) + [extra_key] if scope_path else [extra_key]
        if assign_path(payload, tokens, "out-of-envelope") is None:
            address = f"{scope_path}.{extra_key}" if scope_path else extra_key
            probes.append(ProbePayloadCandidate(address, "closed-scope", "extra-dimension", payload))
    return probes
