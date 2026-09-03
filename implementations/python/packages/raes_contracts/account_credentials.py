"""Closed value-free contracts for account credential runtime projection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Annotated, Any, Literal

from pydantic import Field

from .contracts.base import ContractModel


class ValueFreeSecretFixtureMaterialModel(ContractModel):
    """Presence-only runtime posture for deliberate fixture material."""

    classification: Literal["secret_fixture"]
    value_present: Literal[True]


class ValueFreeOperatorSecretMaterialModel(ContractModel):
    """Presence-only runtime posture for an operator-managed reference."""

    classification: Literal["operator_secret"]
    reference_present: Literal[True]


ValueFreeAccountCredentialMaterial = Annotated[
    ValueFreeSecretFixtureMaterialModel | ValueFreeOperatorSecretMaterialModel,
    Field(discriminator="classification"),
]


class ValueFreeAccountCredentialBindingModel(ContractModel):
    """The complete credential-binding shape admitted by generic runtime state."""

    credential_id: str = Field(min_length=1, max_length=64)
    purpose: str = Field(min_length=1, max_length=256)
    auth_method: str = Field(min_length=1, max_length=256)
    material: ValueFreeAccountCredentialMaterial


def account_placement_has_credential_bindings(payload: object) -> bool:
    """Return whether a canonical account-placement payload carries bindings."""

    if not isinstance(payload, Mapping):
        return False
    spec = payload.get("spec")
    return isinstance(spec, Mapping) and bool(spec.get("credential_bindings"))


def value_free_account_placement_payload(payload: Mapping[str, object]) -> dict[str, Any]:
    """Project only the canonical account-placement credential-binding path."""

    projected = deepcopy(dict(payload))
    spec = projected.get("spec")
    if not isinstance(spec, Mapping):
        return projected
    bindings = spec.get("credential_bindings")
    if not isinstance(bindings, Sequence) or isinstance(bindings, (str, bytes)):
        return projected

    safe_spec = deepcopy(dict(spec))
    safe_spec["credential_bindings"] = [_value_free_binding(binding) for binding in bindings]
    projected["spec"] = safe_spec
    return projected


def _value_free_binding(binding: object) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        raise ValueError("credential binding must be a mapping")
    material = binding.get("material")
    if not isinstance(material, Mapping):
        raise ValueError("credential binding material must be a mapping")
    classification = material.get("classification")
    if classification == "secret_fixture" and ("value" in material or material.get("value_present") is True):
        safe_material: dict[str, object] = {"classification": classification, "value_present": True}
    elif classification == "operator_secret" and (
        "reference_id" in material or material.get("reference_present") is True
    ):
        safe_material = {"classification": classification, "reference_present": True}
    else:
        raise ValueError("credential binding material does not satisfy the closed runtime projection")
    safe = ValueFreeAccountCredentialBindingModel.model_validate(
        {
            "credential_id": binding.get("credential_id"),
            "purpose": binding.get("purpose"),
            "auth_method": binding.get("auth_method"),
            "material": safe_material,
        }
    )
    return safe.model_dump(mode="json")


__all__ = [
    "ValueFreeAccountCredentialBindingModel",
    "ValueFreeAccountCredentialMaterial",
    "ValueFreeOperatorSecretMaterialModel",
    "ValueFreeSecretFixtureMaterialModel",
    "account_placement_has_credential_bindings",
    "value_free_account_placement_payload",
]
