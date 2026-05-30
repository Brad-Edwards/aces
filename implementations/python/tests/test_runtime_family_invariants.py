"""Executable cross-family structural invariant lint for runtime service families.

Enforces the single structural invariant set required by DSL-139 (consistency
epic Brad-Edwards/aces#439 and children #442 / #443 / #444): every registered
runtime service family must use a ``Runtime<Noun>`` model class, a
``singular(collection_name) + "_id"`` primary identifier field, and a plural
typed-child container registered through ``_runtime_service_families``.

The remaining pre-existing violations are tracked explicitly in
``KNOWN_VIOLATIONS`` and driven to empty as the existing families are
reconciled. The point of this lint is the *drift* guarantee: any **new**
family that violates an invariant, or any reconciliation that resolves a
violation without updating this allowlist, fails the suite immediately. When
``KNOWN_VIOLATIONS`` is empty the invariant set is fully enforced for the whole
surface, old and new.
"""

from __future__ import annotations

import typing

from aces_sdl import _runtime_service_families as rsf
from aces_sdl.runtime_configuration import RuntimeConfiguration


def _singularize(plural: str) -> str:
    """Mechanical singular of a runtime container collection name."""

    if plural.endswith("ies"):
        return plural[:-3] + "y"
    if plural.endswith("s"):
        return plural[:-1]
    return plural


def _element_model(collection_name: str) -> type | None:
    """Return the element model class for a ``list[X]`` runtime container field."""

    field = RuntimeConfiguration.model_fields.get(collection_name)
    if field is None:
        return None
    args = typing.get_args(field.annotation)
    return args[0] if args else None


def _current_violations() -> set[str]:
    """Compute the live set of structural-invariant violations across families."""

    violations: set[str] = set()
    for family in rsf.RUNTIME_SERVICE_FAMILIES:
        model = _element_model(family.collection_name)
        if model is None or not model.__name__.startswith("Runtime"):
            violations.add(f"class-name:{family.key}")
        expected_id = _singularize(family.collection_name) + "_id"
        if family.id_field != expected_id:
            violations.add(f"primary-id:{family.key}")
    config_fields = set(RuntimeConfiguration.model_fields)
    if "process" in config_fields and "processes" in config_fields:
        violations.add("scalar-twin:runtime_configuration.process")
    return violations


# Pre-existing violations as of the start of the DSL-139 reconciliation. Each
# entry is removed in the same commit that resolves it; an empty set means the
# whole surface satisfies the invariant set.
KNOWN_VIOLATIONS: set[str] = {
    "primary-id:service-listeners",
    "primary-id:identity-authorities",
    "primary-id:file-services",
    "primary-id:mail-services",
    "primary-id:network-sensors",
    "primary-id:network-detection-engines",
    "primary-id:security-monitoring-managers",
    "primary-id:ssh-servers",
    "scalar-twin:runtime_configuration.process",
}


def test_runtime_family_invariants_no_new_drift() -> None:
    """Live violations must exactly match the tracked allowlist (no drift)."""

    current = _current_violations()
    new = sorted(current - KNOWN_VIOLATIONS)
    resolved = sorted(KNOWN_VIOLATIONS - current)
    assert current == KNOWN_VIOLATIONS, (
        "Runtime service-family structural-invariant drift detected.\n"
        f"  NEW violations (fix the family, or this change is wrong): {new}\n"
        f"  RESOLVED but still allow-listed (remove from KNOWN_VIOLATIONS): {resolved}"
    )


def test_primary_id_field_exists_on_model() -> None:
    """Every registry primary id field must be a real field on its model."""

    for family in rsf.RUNTIME_SERVICE_FAMILIES:
        model = _element_model(family.collection_name)
        assert model is not None, f"{family.key}: no element model for {family.collection_name}"
        assert family.id_field in model.model_fields, (
            f"{family.key}: registry id_field '{family.id_field}' is not a field on {model.__name__}"
        )


def test_registered_child_refs_exist_on_models() -> None:
    """Every registered child collection/id must exist on its parent model."""

    def _check(model: type, children: tuple[rsf.RuntimeReferenceChild, ...]) -> None:
        for child in children:
            assert child.collection_name in model.model_fields, (
                f"{model.__name__}: child collection '{child.collection_name}' is not a field"
            )
            child_model = typing.get_args(model.model_fields[child.collection_name].annotation)
            element = child_model[0] if child_model else None
            assert element is not None, f"{model.__name__}.{child.collection_name} is not a typed list"
            assert child.id_field in element.model_fields, (
                f"{element.__name__}: child id_field '{child.id_field}' is not a field"
            )
            _check(element, child.children)

    for family in rsf.RUNTIME_SERVICE_FAMILIES:
        model = _element_model(family.collection_name)
        assert model is not None
        _check(model, family.child_refs)
