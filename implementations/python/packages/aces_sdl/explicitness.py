"""SEM-218 explicitness classification for authored SDL declarations."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel

from ._base import extract_variable_name
from .variables import Variable

__all__ = [
    "ExplicitnessClass",
    "ExplicitnessProvenance",
    "ExplicitnessRecord",
    "ExplicitnessResult",
    "classify_scenario_explicitness",
    "derive_instantiated_explicitness",
]

_VARIABLE_TOKEN_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_-]*)\}")
_OPEN_ENUM_SENTINELS = frozenset({"unknown", "other"})
_EXPLICITNESS_ORDER: dict[ExplicitnessClass, int] = {}


class ExplicitnessClass(str, Enum):
    """SEM-218 author-intent class for a declaration."""

    EXACT = "exact"
    CONSTRAINED = "constrained"
    OPEN = "open"


class ExplicitnessProvenance(str, Enum):
    """Where the classified value came from in the SDL lifecycle."""

    AUTHOR_DECLARED = "author-declared"
    PROCESSOR_DERIVED = "processor-derived"
    BACKEND_REALIZED = "backend-realized"


_EXPLICITNESS_ORDER.update(
    {
        ExplicitnessClass.OPEN: 0,
        ExplicitnessClass.CONSTRAINED: 1,
        ExplicitnessClass.EXACT: 2,
    }
)


@dataclass(frozen=True)
class ExplicitnessRecord:
    """Classification metadata for one SDL model path."""

    path: str
    classification: ExplicitnessClass
    provenance: ExplicitnessProvenance = ExplicitnessProvenance.AUTHOR_DECLARED
    reason: str = ""
    variables: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExplicitnessResult:
    """Classifier result plus non-fatal diagnostics for validation."""

    records: dict[str, ExplicitnessRecord]
    errors: tuple[str, ...] = ()


def classify_scenario_explicitness(scenario: BaseModel) -> ExplicitnessResult:
    """Classify authored SDL declarations on ``scenario``."""

    variables = getattr(scenario, "variables", {})
    classifier = _ExplicitnessClassifier(variables)
    classifier.visit(scenario, "")
    return ExplicitnessResult(records=dict(classifier.records), errors=tuple(classifier.errors))


def derive_instantiated_explicitness(
    raw_scenario: BaseModel,
    instantiated_scenario: BaseModel,
) -> ExplicitnessResult:
    """Derive instantiated explicitness without promoting substitutions to exact."""

    raw_result = classify_scenario_explicitness(raw_scenario)
    instantiated_paths = _authored_paths(instantiated_scenario)
    records: dict[str, ExplicitnessRecord] = {}
    for path, record in raw_result.records.items():
        if path not in instantiated_paths:
            continue
        provenance = (
            ExplicitnessProvenance.PROCESSOR_DERIVED if record.variables else ExplicitnessProvenance.AUTHOR_DECLARED
        )
        reason = record.reason
        if record.variables:
            reason = "parameter/default substitution preserved authored explicitness class"
        records[path] = ExplicitnessRecord(
            path=record.path,
            classification=record.classification,
            provenance=provenance,
            reason=reason,
            variables=record.variables,
        )
    return ExplicitnessResult(records=records, errors=raw_result.errors)


class _ExplicitnessClassifier:
    def __init__(self, variables: dict[str, Variable]) -> None:
        self._variables = variables
        self.records: dict[str, ExplicitnessRecord] = {}
        self.errors: list[str] = []

    def visit(self, value: object, path: str) -> ExplicitnessRecord | None:
        if isinstance(value, BaseModel):
            return self._visit_model(value, path)
        if isinstance(value, dict):
            return self._visit_mapping(value, path)
        if isinstance(value, list):
            return self._visit_sequence(value, path)
        if not path:
            return None
        return self._record_scalar(value, path)

    def _visit_model(self, model: BaseModel, path: str) -> ExplicitnessRecord | None:
        child_records: list[ExplicitnessRecord] = []
        fields_set = set(model.model_fields_set)
        for field_name in model.__class__.model_fields:
            if field_name not in fields_set:
                continue
            child_path = f"{path}.{field_name}" if path else field_name
            child_record = self.visit(getattr(model, field_name), child_path)
            if child_record is not None:
                child_records.append(child_record)
        return self._record_container(path, child_records)

    def _visit_mapping(self, value: dict[object, object], path: str) -> ExplicitnessRecord | None:
        child_records: list[ExplicitnessRecord] = []
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            child_record = self.visit(child, child_path)
            if child_record is not None:
                child_records.append(child_record)
        return self._record_container(path, child_records)

    def _visit_sequence(self, value: list[object], path: str) -> ExplicitnessRecord | None:
        child_records: list[ExplicitnessRecord] = []
        for index, child in enumerate(value):
            child_record = self.visit(child, f"{path}[{index}]")
            if child_record is not None:
                child_records.append(child_record)
        return self._record_container(path, child_records)

    def _record_container(
        self,
        path: str,
        child_records: list[ExplicitnessRecord],
    ) -> ExplicitnessRecord | None:
        if not path:
            return None
        classification = _weakest_class(record.classification for record in child_records)
        variables = tuple(sorted({name for record in child_records for name in record.variables}))
        record = ExplicitnessRecord(
            path=path,
            classification=classification,
            reason="derived from child declarations" if child_records else "authored empty structure",
            variables=variables,
        )
        self.records[path] = record
        return record

    def _record_scalar(self, value: object, path: str) -> ExplicitnessRecord:
        variable_names = _variable_names(value)
        if variable_names:
            missing = tuple(name for name in variable_names if name not in self._variables)
            if missing:
                self.errors.append(
                    f"Cannot classify explicitness for '{path}': undefined variable(s) {', '.join(missing)}"
                )
            record = ExplicitnessRecord(
                path=path,
                classification=ExplicitnessClass.CONSTRAINED,
                reason=_variable_constraint_reason(variable_names, self._variables),
                variables=variable_names,
            )
            self.records[path] = record
            return record

        classification = ExplicitnessClass.OPEN if _is_open_enum_sentinel(value) else ExplicitnessClass.EXACT
        reason = "open taxonomy sentinel" if classification is ExplicitnessClass.OPEN else "authored concrete value"
        record = ExplicitnessRecord(path=path, classification=classification, reason=reason)
        self.records[path] = record
        return record


def _variable_names(value: object) -> tuple[str, ...]:
    if not isinstance(value, str):
        return ()
    full_name = extract_variable_name(value)
    if full_name is not None:
        return (full_name,)
    return tuple(dict.fromkeys(_VARIABLE_TOKEN_RE.findall(value)))


def _variable_constraint_reason(variable_names: tuple[str, ...], variables: dict[str, Variable]) -> str:
    parts: list[str] = []
    for variable_name in variable_names:
        variable = variables.get(variable_name)
        if variable is None:
            parts.append(f"{variable_name}: undefined")
            continue
        if variable.allowed_values:
            parts.append(f"{variable_name}: allowed_values")
        else:
            parts.append(f"{variable_name}: type {variable.type.value}")
    return "; ".join(parts)


def _is_open_enum_sentinel(value: object) -> bool:
    return isinstance(value, Enum) and isinstance(value.value, str) and value.value in _OPEN_ENUM_SENTINELS


def _weakest_class(classes: Iterable[ExplicitnessClass]) -> ExplicitnessClass:
    weakest = ExplicitnessClass.EXACT
    for classification in classes:
        if _EXPLICITNESS_ORDER[classification] < _EXPLICITNESS_ORDER[weakest]:
            weakest = classification
    return weakest


def _authored_paths(value: object) -> set[str]:
    paths: set[str] = set()

    def visit(nested: object, path: str) -> None:
        if path:
            paths.add(path)
        if isinstance(nested, BaseModel):
            for field_name in nested.__class__.model_fields:
                if field_name not in nested.model_fields_set:
                    continue
                child_path = f"{path}.{field_name}" if path else field_name
                visit(getattr(nested, field_name), child_path)
            return
        if isinstance(nested, dict):
            for key, child in nested.items():
                child_path = f"{path}.{key}" if path else str(key)
                visit(child, child_path)
            return
        if isinstance(nested, list):
            for index, child in enumerate(nested):
                visit(child, f"{path}[{index}]")

    visit(value, "")
    return paths
