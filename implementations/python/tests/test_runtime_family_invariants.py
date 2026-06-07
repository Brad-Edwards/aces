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

import ast
import enum
import importlib
import pkgutil
import typing
from pathlib import Path

import aces_sdl
from aces_sdl import _runtime_service_families as rsf
from aces_sdl._base import parse_enum_or_var
from aces_sdl.runtime_configuration import RuntimeConfiguration
from aces_sdl.runtime_directory_identity import RuntimeIdentityRelationshipKind
from aces_sdl.runtime_values import parse_runtime_enum_or_var


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
KNOWN_VIOLATIONS: set[str] = set()

_SHARED_HELPER_DEFINITION_NAMES = frozenset(
    {
        "_absolute_refs",
        "_coerce_refs",
        "_normalize_enum",
        "_reject_duplicates",
        "_require_non_empty",
        "coerce_string_list",
        "parse_runtime_enum_or_var",
        "reject_duplicates",
        "require_non_empty",
        "validate_absolute_paths",
    }
)


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


def test_runtime_modules_do_not_redeclare_shared_validation_helpers() -> None:
    """Runtime families import shared helper policy instead of shadowing it."""

    package_dir = Path(aces_sdl.__file__).resolve().parent
    offenders: list[str] = []
    for path in sorted(package_dir.glob("runtime_*.py")):
        if path.name == "runtime_values.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in _SHARED_HELPER_DEFINITION_NAMES:
                offenders.append(f"{path.name}:{node.lineno}:{node.name}")

    assert not offenders, "Runtime modules must not redeclare shared validation helpers:\n  " + "\n  ".join(offenders)


def test_enum_or_var_helpers_share_hyphen_alias_normalization() -> None:
    """Runtime and base enum parsing share one author-facing normalization rule."""

    assert (
        parse_runtime_enum_or_var("member-of", RuntimeIdentityRelationshipKind, field_name="relationship_type")
        is RuntimeIdentityRelationshipKind.MEMBER_OF
    )
    assert (
        parse_enum_or_var("member-of", RuntimeIdentityRelationshipKind, field_name="relationship_type")
        is RuntimeIdentityRelationshipKind.MEMBER_OF
    )


def test_primary_id_field_exists_on_model() -> None:
    """Every registry primary id field must be a real field on its model."""

    for family in rsf.RUNTIME_SERVICE_FAMILIES:
        model = _element_model(family.collection_name)
        assert model is not None, f"{family.key}: no element model for {family.collection_name}"
        assert family.id_field in model.model_fields, (
            f"{family.key}: registry id_field '{family.id_field}' is not a field on {model.__name__}"
        )


def _runtime_family_enums() -> dict[str, type[enum.Enum]]:
    """Collect every Enum subclass *defined in* a runtime-family module.

    A runtime-family module is any ``aces_sdl`` submodule whose name starts
    with ``runtime_`` (this includes the ``*_vocab`` and ``*_definitions``
    modules). Only enums whose ``__module__`` is that module are returned, so
    enums merely re-exported or imported from another module are not
    double-counted against the wrong module.
    """

    found: dict[str, type[enum.Enum]] = {}
    for module_info in pkgutil.iter_modules(aces_sdl.__path__):
        name = module_info.name
        if not name.startswith("runtime_"):
            continue
        qualified = f"aces_sdl.{name}"
        module = importlib.import_module(qualified)
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and issubclass(value, enum.Enum)
                and value is not enum.Enum
                and value.__module__ == qualified
            ):
                found[f"{name}.{value.__name__}"] = value
    return found


def test_runtime_enums_open_or_closed_not_single_sentinel() -> None:
    """Runtime-family enums must be open (both sentinels) or closed (neither).

    The enum-sentinel convention (DSL-139, Brad-Edwards/aces#443) is: an OPEN
    observed-value taxonomy carries BOTH ``unknown`` and ``other``; a CLOSED
    structural/protocol/redaction-lattice vocabulary carries NEITHER. The
    single-sentinel state -- exactly one of ``{unknown, other}`` -- is the
    inconsistency this lint forbids. Any future runtime enum introduced in a
    single-sentinel state fails here, which is the drift guard.
    """

    enums = _runtime_family_enums()
    assert enums, "no runtime-family enums discovered; module iteration is broken"

    offenders: list[str] = []
    for qualified_name, enum_cls in sorted(enums.items()):
        values = {member.value for member in enum_cls}
        has_unknown = "unknown" in values
        has_other = "other" in values
        if has_unknown != has_other:
            present = "unknown" if has_unknown else "other"
            offenders.append(f"{qualified_name} (single-sentinel: only '{present}')")

    assert not offenders, (
        "Runtime-family enums must carry BOTH 'unknown' and 'other' (open) or "
        "NEITHER (closed), never exactly one. Single-sentinel enums:\n  " + "\n  ".join(offenders)
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
