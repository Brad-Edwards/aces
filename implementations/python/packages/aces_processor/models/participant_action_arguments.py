"""Portable validation and normalization for compiled participant actions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite

from aces_contracts.participant_binding import (
    ParticipantActionArgumentScalar,
    ParticipantActionArgumentValue,
    ParticipantValidatedActionSelection,
)

from .resources import ParticipantActionContractRuntime


def _values_equal(left: object, right: object) -> bool:
    return type(left) is type(right) and left == right


def _require_scalar_type(value: object, value_type: str, argument_name: str) -> ParticipantActionArgumentScalar:
    if value_type in {"string", "reference"}:
        if not isinstance(value, str):
            raise ValueError(f"argument {argument_name!r} must be a {value_type}")
        return value
    if value_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"argument {argument_name!r} must be an integer")
        return value
    if value_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
            raise ValueError(f"argument {argument_name!r} must be a finite number")
        return value
    if value_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"argument {argument_name!r} must be a boolean")
        return value
    raise ValueError(f"argument {argument_name!r} has an unsupported compiled value_type")


def _normalize_scalar(
    value: object,
    definition: Mapping[str, object],
    argument_name: str,
) -> ParticipantActionArgumentScalar:
    value_type = str(definition.get("value_type", ""))
    normalized = _require_scalar_type(value, value_type, argument_name)
    normalization = str(definition.get("normalization", ""))
    if normalization == "trim":
        if not isinstance(normalized, str):
            raise ValueError(f"argument {argument_name!r} trim normalization requires string values")
        normalized = normalized.strip()
    elif normalization != "identity":
        raise ValueError(f"argument {argument_name!r} has an unsupported compiled normalization")

    min_length = definition.get("min_length")
    max_length = definition.get("max_length")
    if isinstance(normalized, str):
        if isinstance(min_length, int) and len(normalized) < min_length:
            raise ValueError(f"argument {argument_name!r} violates min_length")
        if isinstance(max_length, int) and len(normalized) > max_length:
            raise ValueError(f"argument {argument_name!r} violates max_length")

    minimum = definition.get("minimum")
    maximum = definition.get("maximum")
    if isinstance(normalized, (int, float)) and not isinstance(normalized, bool):
        if isinstance(minimum, (int, float)) and normalized < minimum:
            raise ValueError(f"argument {argument_name!r} violates minimum")
        if isinstance(maximum, (int, float)) and normalized > maximum:
            raise ValueError(f"argument {argument_name!r} violates maximum")

    allowed_values = definition.get("allowed_values", [])
    if isinstance(allowed_values, Sequence) and not isinstance(allowed_values, (str, bytes)):
        if allowed_values and not any(_values_equal(normalized, allowed) for allowed in allowed_values):
            raise ValueError(f"argument {argument_name!r} violates allowed_values")
    return normalized


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
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"argument {argument_name!r} must carry a collection")
    min_items = definition.get("min_items")
    max_items = definition.get("max_items")
    if isinstance(min_items, int) and len(value) < min_items:
        raise ValueError(f"argument {argument_name!r} violates min_items")
    if isinstance(max_items, int) and len(value) > max_items:
        raise ValueError(f"argument {argument_name!r} violates max_items")
    normalized = tuple(_normalize_scalar(item, definition, argument_name) for item in value)
    if definition.get("unique_items") is True:
        for index, item in enumerate(normalized):
            if any(_values_equal(item, prior) for prior in normalized[:index]):
                raise ValueError(f"argument {argument_name!r} collection values must be unique")
    return normalized


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


def resolve_participant_action_arguments(
    contract: ParticipantActionContractRuntime,
    *,
    action_contract_address: str,
    argument_shape_ref: str,
    proposal_ref: str,
    proposed_arguments: Mapping[str, object],
) -> ParticipantValidatedActionSelection:
    """Normalize concrete proposal values against one compiled action shape."""

    if action_contract_address != contract.address:
        raise ValueError("action_contract_address does not match the compiled action contract")
    if not contract.argument_shape_ref or argument_shape_ref != contract.argument_shape_ref:
        raise ValueError("argument_shape_ref does not match the compiled action contract")
    if not isinstance(proposal_ref, str) or not proposal_ref:
        raise ValueError("proposal_ref must be non-empty")
    if not isinstance(proposed_arguments, Mapping):
        raise ValueError("proposed_arguments must be a mapping")

    definitions = _definition_index(contract)
    unknown = sorted(set(proposed_arguments) - definitions.keys())
    if unknown:
        raise ValueError("proposal contains unknown arguments: " + ", ".join(unknown))

    normalized: list[tuple[str, ParticipantActionArgumentValue]] = []
    defaulted: list[str] = []
    omitted: list[str] = []
    normalization_refs: list[str] = []
    omission_refs: list[str] = []
    default_refs: list[str] = []
    loss_refs: list[str] = []

    for name, definition in sorted(definitions.items()):
        normalization_refs.append(str(definition["normalization_disclosure_ref"]))
        omission_refs.append(str(definition["omission_disclosure_ref"]))
        loss_refs.append(str(definition["loss_disclosure_ref"]))
        if name in proposed_arguments:
            raw_value = proposed_arguments[name]
        else:
            omission = str(definition.get("omission", ""))
            if omission == "reject":
                raise ValueError(f"proposal omits required argument {name!r}")
            if omission == "omit":
                omitted.append(name)
                continue
            if omission != "use_default" or "default" not in definition or definition.get("default") is None:
                raise ValueError(f"argument {name!r} has an invalid compiled omission policy")
            raw_value = definition["default"]
            defaulted.append(name)
            default_ref = definition.get("default_disclosure_ref")
            if not isinstance(default_ref, str) or not default_ref:
                raise ValueError(f"argument {name!r} default lacks a disclosure ref")
            default_refs.append(default_ref)
        normalized.append((name, _normalize_value(raw_value, definition, name)))

    return ParticipantValidatedActionSelection(
        action_contract_address=action_contract_address,
        argument_shape_ref=argument_shape_ref,
        proposal_ref=proposal_ref,
        normalized_arguments=tuple(normalized),
        defaulted_argument_names=tuple(defaulted),
        omitted_argument_names=tuple(omitted),
        normalization_disclosure_refs=tuple(dict.fromkeys(normalization_refs)),
        omission_disclosure_refs=tuple(dict.fromkeys(omission_refs)),
        default_disclosure_refs=tuple(dict.fromkeys(default_refs)),
        loss_disclosure_refs=tuple(dict.fromkeys(loss_refs)),
    )


__all__ = ("resolve_participant_action_arguments",)
