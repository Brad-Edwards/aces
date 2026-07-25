"""Portable validation and normalization for compiled participant actions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import isfinite
from typing import cast

from aces_contracts.participant_binding import (
    ParticipantActionArgumentScalar,
    ParticipantActionArgumentValue,
    ParticipantValidatedActionSelection,
)

from .resources import ParticipantActionContractRuntime


def _values_equal(left: object, right: object) -> bool:
    return type(left) is type(right) and left == right


def _is_string(value: object) -> bool:
    return isinstance(value, str)


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _is_boolean(value: object) -> bool:
    return isinstance(value, bool)


_SCALAR_TYPE_PREDICATES = {
    "string": _is_string,
    "reference": _is_string,
    "integer": _is_integer,
    "number": _is_finite_number,
    "boolean": _is_boolean,
}

_SCALAR_TYPE_ERRORS = {
    "string": "must be a string",
    "reference": "must be a reference",
    "integer": "must be an integer",
    "number": "must be a finite number",
    "boolean": "must be a boolean",
}


def _require_scalar_type(value: object, value_type: str, argument_name: str) -> ParticipantActionArgumentScalar:
    predicate = _SCALAR_TYPE_PREDICATES.get(value_type)
    if predicate is None:
        raise ValueError(f"argument {argument_name!r} has an unsupported compiled value_type")
    if not predicate(value):
        raise ValueError(f"argument {argument_name!r} {_SCALAR_TYPE_ERRORS[value_type]}")
    return cast(ParticipantActionArgumentScalar, value)


def _apply_scalar_normalization(
    value: ParticipantActionArgumentScalar,
    normalization: str,
    argument_name: str,
) -> ParticipantActionArgumentScalar:
    if normalization == "identity":
        return value
    if normalization == "trim":
        if not isinstance(value, str):
            raise ValueError(f"argument {argument_name!r} trim normalization requires string values")
        return value.strip()
    raise ValueError(f"argument {argument_name!r} has an unsupported compiled normalization")


def _validate_scalar_length(
    value: ParticipantActionArgumentScalar,
    definition: Mapping[str, object],
    argument_name: str,
) -> None:
    if not isinstance(value, str):
        return
    min_length = definition.get("min_length")
    max_length = definition.get("max_length")
    if isinstance(min_length, int) and len(value) < min_length:
        raise ValueError(f"argument {argument_name!r} violates min_length")
    if isinstance(max_length, int) and len(value) > max_length:
        raise ValueError(f"argument {argument_name!r} violates max_length")


def _validate_scalar_range(
    value: ParticipantActionArgumentScalar,
    definition: Mapping[str, object],
    argument_name: str,
) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return
    minimum = definition.get("minimum")
    maximum = definition.get("maximum")
    if isinstance(minimum, (int, float)) and value < minimum:
        raise ValueError(f"argument {argument_name!r} violates minimum")
    if isinstance(maximum, (int, float)) and value > maximum:
        raise ValueError(f"argument {argument_name!r} violates maximum")


def _validate_scalar_allowed_values(
    value: ParticipantActionArgumentScalar,
    definition: Mapping[str, object],
    argument_name: str,
) -> None:
    allowed_values = definition.get("allowed_values", [])
    if not isinstance(allowed_values, Sequence) or isinstance(allowed_values, (str, bytes)):
        return
    if allowed_values and not any(_values_equal(value, allowed) for allowed in allowed_values):
        raise ValueError(f"argument {argument_name!r} violates allowed_values")


def _normalize_scalar(
    value: object,
    definition: Mapping[str, object],
    argument_name: str,
) -> ParticipantActionArgumentScalar:
    value_type = str(definition.get("value_type", ""))
    normalized = _require_scalar_type(value, value_type, argument_name)
    normalization = str(definition.get("normalization", ""))
    normalized = _apply_scalar_normalization(normalized, normalization, argument_name)
    _validate_scalar_length(normalized, definition, argument_name)
    _validate_scalar_range(normalized, definition, argument_name)
    _validate_scalar_allowed_values(normalized, definition, argument_name)
    return normalized


def _normalize_collection(
    value: object,
    definition: Mapping[str, object],
    argument_name: str,
) -> tuple[ParticipantActionArgumentScalar, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"argument {argument_name!r} must carry a collection")
    _validate_collection_size(value, definition, argument_name)
    normalized = tuple(_normalize_scalar(item, definition, argument_name) for item in value)
    _validate_collection_uniqueness(normalized, definition, argument_name)
    return normalized


def _validate_collection_size(
    value: list[object] | tuple[object, ...],
    definition: Mapping[str, object],
    argument_name: str,
) -> None:
    min_items = definition.get("min_items")
    max_items = definition.get("max_items")
    if isinstance(min_items, int) and len(value) < min_items:
        raise ValueError(f"argument {argument_name!r} violates min_items")
    if isinstance(max_items, int) and len(value) > max_items:
        raise ValueError(f"argument {argument_name!r} violates max_items")


def _validate_collection_uniqueness(
    value: tuple[ParticipantActionArgumentScalar, ...],
    definition: Mapping[str, object],
    argument_name: str,
) -> None:
    if definition.get("unique_items") is True:
        for index, item in enumerate(value):
            if any(_values_equal(item, prior) for prior in value[:index]):
                raise ValueError(f"argument {argument_name!r} collection values must be unique")


def _normalize_value(
    value: object,
    definition: Mapping[str, object],
    argument_name: str,
) -> ParticipantActionArgumentValue:
    cardinality = str(definition.get("cardinality", ""))
    if cardinality == "one":
        if isinstance(value, (list, tuple)):
            raise ValueError(f"argument {argument_name!r} must carry one value")
        return _normalize_scalar(value, definition, argument_name)
    if cardinality != "many":
        raise ValueError(f"argument {argument_name!r} has an unsupported compiled cardinality")
    return _normalize_collection(value, definition, argument_name)


def _definition_index(
    contract: ParticipantActionContractRuntime,
) -> dict[str, Mapping[str, object]]:
    definitions: dict[str, Mapping[str, object]] = {}
    for definition in contract.argument_definitions:
        name = definition.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("compiled participant action argument definitions require names")
        if name in definitions:
            raise ValueError("compiled participant action argument definition names must be unique")
        definitions[name] = definition
    return definitions


@dataclass
class _ArgumentResolution:
    normalized: list[tuple[str, ParticipantActionArgumentValue]] = field(default_factory=list)
    defaulted: list[str] = field(default_factory=list)
    omitted: list[str] = field(default_factory=list)
    normalization_refs: list[str] = field(default_factory=list)
    omission_refs: list[str] = field(default_factory=list)
    default_refs: list[str] = field(default_factory=list)
    loss_refs: list[str] = field(default_factory=list)


_OMITTED_ARGUMENT = object()


def _validate_resolution_request(
    contract: ParticipantActionContractRuntime,
    action_contract_address: str,
    argument_shape_ref: str,
    proposal_ref: str,
    proposed_arguments: Mapping[str, object],
) -> None:
    if action_contract_address != contract.address:
        raise ValueError("action_contract_address does not match the compiled action contract")
    if not contract.argument_shape_ref or argument_shape_ref != contract.argument_shape_ref:
        raise ValueError("argument_shape_ref does not match the compiled action contract")
    if not isinstance(proposal_ref, str) or not proposal_ref:
        raise ValueError("proposal_ref must be non-empty")
    if not isinstance(proposed_arguments, Mapping):
        raise ValueError("proposed_arguments must be a mapping")


def _validate_known_arguments(
    definitions: Mapping[str, Mapping[str, object]],
    proposed_arguments: Mapping[str, object],
) -> None:
    unknown = sorted(set(proposed_arguments) - definitions.keys())
    if unknown:
        raise ValueError("proposal contains unknown arguments: " + ", ".join(unknown))


def _record_disclosures(definition: Mapping[str, object], resolution: _ArgumentResolution) -> None:
    resolution.normalization_refs.append(str(definition["normalization_disclosure_ref"]))
    resolution.omission_refs.append(str(definition["omission_disclosure_ref"]))
    resolution.loss_refs.append(str(definition["loss_disclosure_ref"]))


def _resolve_argument_value(
    name: str,
    definition: Mapping[str, object],
    proposed_arguments: Mapping[str, object],
    resolution: _ArgumentResolution,
) -> object:
    if name in proposed_arguments:
        return proposed_arguments[name]
    omission = str(definition.get("omission", ""))
    if omission == "reject":
        raise ValueError(f"proposal omits required argument {name!r}")
    if omission == "omit":
        resolution.omitted.append(name)
        return _OMITTED_ARGUMENT
    if omission != "use_default" or "default" not in definition or definition.get("default") is None:
        raise ValueError(f"argument {name!r} has an invalid compiled omission policy")
    resolution.defaulted.append(name)
    default_ref = definition.get("default_disclosure_ref")
    if not isinstance(default_ref, str) or not default_ref:
        raise ValueError(f"argument {name!r} default lacks a disclosure ref")
    resolution.default_refs.append(default_ref)
    return definition["default"]


def resolve_participant_action_arguments(
    contract: ParticipantActionContractRuntime,
    *,
    action_contract_address: str,
    argument_shape_ref: str,
    proposal_ref: str,
    proposed_arguments: Mapping[str, object],
) -> ParticipantValidatedActionSelection:
    """Normalize concrete proposal values against one compiled action shape."""

    _validate_resolution_request(
        contract,
        action_contract_address,
        argument_shape_ref,
        proposal_ref,
        proposed_arguments,
    )
    definitions = _definition_index(contract)
    _validate_known_arguments(definitions, proposed_arguments)
    resolution = _ArgumentResolution()
    for name, definition in sorted(definitions.items()):
        _record_disclosures(definition, resolution)
        raw_value = _resolve_argument_value(name, definition, proposed_arguments, resolution)
        if raw_value is _OMITTED_ARGUMENT:
            continue
        resolution.normalized.append((name, _normalize_value(raw_value, definition, name)))

    return ParticipantValidatedActionSelection(
        action_contract_address=action_contract_address,
        argument_shape_ref=argument_shape_ref,
        proposal_ref=proposal_ref,
        normalized_arguments=tuple(resolution.normalized),
        defaulted_argument_names=tuple(resolution.defaulted),
        omitted_argument_names=tuple(resolution.omitted),
        normalization_disclosure_refs=tuple(dict.fromkeys(resolution.normalization_refs)),
        omission_disclosure_refs=tuple(dict.fromkeys(resolution.omission_refs)),
        default_disclosure_refs=tuple(dict.fromkeys(resolution.default_refs)),
        loss_disclosure_refs=tuple(dict.fromkeys(resolution.loss_refs)),
    )


__all__ = ("resolve_participant_action_arguments",)
