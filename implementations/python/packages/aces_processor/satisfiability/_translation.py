"""Total translation of the governed SDL v1 satisfiability fragment."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import rfc8785
from aces_contracts.diagnostics import DiagnosticModel
from aces_contracts.satisfiability import (
    ConstraintClauseKind,
    ConstraintClauseModel,
    ConstraintSort,
    ConstraintSymbolModel,
    NormalizedConstraintModel,
)
from aces_sdl.canonical import canonical_sdl_digest
from aces_sdl.infrastructure import ACLAction
from aces_sdl.nodes import OSFamily
from aces_sdl.scenario import ExpandedScenario, Scenario
from aces_sdl.value_parsing import extract_variable_name, normalize_enum_value, variable_names_in_value
from aces_sdl.variables import Variable, VariableType

_MAX_SYMBOLS = 128
_MAX_CLAUSES = 512
_MAX_DOMAIN_MEMBERS = 256
_MAX_DIAGNOSTICS = 64
_DOMAIN_CODE = "scenario-satisfiability.unsupported-domain"
_TARGET_CODE = "scenario-satisfiability.unsupported-target"
_RESOURCE_CODE = "scenario-satisfiability.resource-limit"


@dataclass(frozen=True)
class TranslationResult:
    """Normalized model plus any fail-closed coverage diagnostics."""

    model: NormalizedConstraintModel
    diagnostics: tuple[DiagnosticModel, ...]


class _DiagnosticAccumulator:
    """Keep unsupported evidence within its closed contract at every boundary."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], DiagnosticModel] = {}
        self._overflowed = False

    def add(self, diagnostic: DiagnosticModel) -> None:
        key = (diagnostic.address, diagnostic.code)
        if key in self._items or self._overflowed:
            return
        if len(self._items) < _MAX_DIAGNOSTICS:
            self._items[key] = diagnostic
            return

        # Replace the last deterministically visited detail with one stable
        # overflow record. The traversal order is canonical, so the retained
        # evidence is reproducible without ever exceeding the contract bound.
        self._items.pop(next(reversed(self._items)))
        overflow = _diagnostic(
            _RESOURCE_CODE,
            "",
            "The analysis produced more unsupported diagnostics than the evidence profile permits.",
        )
        self._items[(overflow.address, overflow.code)] = overflow
        self._overflowed = True

    def as_tuple(self) -> tuple[DiagnosticModel, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: (item.address, item.code)))


def translate_scenario(
    scenario: Scenario | ExpandedScenario,
    *,
    source_digest: str,
) -> TranslationResult:
    """Translate every remaining variable occurrence or reject it explicitly."""

    payload = scenario.model_dump(
        mode="python",
        by_alias=True,
        exclude={"variables", "imports", "module", "expansion_provenance"},
    )
    occurrences = tuple(_variable_occurrences(payload))
    referenced = {name for _, name, _ in occurrences}
    selected = {
        name: variable for name, variable in scenario.variables.items() if name in referenced or variable.required
    }
    diagnostics = _DiagnosticAccumulator()
    symbols: dict[str, ConstraintSymbolModel] = {}

    selected_items = sorted(selected.items())
    if len(selected_items) > _MAX_SYMBOLS:
        diagnostics.add(_diagnostic(_RESOURCE_CODE, "/variables", "The analysis exceeds the symbol limit."))
        selected_items = selected_items[:_MAX_SYMBOLS]
    for name, variable in selected_items:
        symbol = _symbol(name, variable, diagnostics)
        if symbol is not None:
            symbols[name] = symbol

    clauses: list[ConstraintClauseModel] = []

    def append_clause(clause: ConstraintClauseModel) -> None:
        if len(clauses) < _MAX_CLAUSES:
            clauses.append(clause)
        else:
            diagnostics.add(_diagnostic(_RESOURCE_CODE, "", "The analysis exceeds the clause limit."))

    for name, symbol in symbols.items():
        append_clause(
            ConstraintClauseModel(
                clause_id=_stable_id("domain", name),
                kind=ConstraintClauseKind.DECLARED_DOMAIN,
                symbol_id=symbol.symbol_id,
                source_address=f"/variables/{_pointer(name)}",
                allowed_values=symbol.domain,
            )
        )

    for address, name, embedded in occurrences:
        symbol = symbols.get(name)
        if embedded or symbol is None:
            diagnostics.add(
                _diagnostic(
                    _TARGET_CODE,
                    address,
                    "The variable occurrence is outside the selected translation profile.",
                )
            )
            continue
        allowed = _target_domain(address, symbol)
        if allowed is None:
            diagnostics.add(
                _diagnostic(
                    _TARGET_CODE,
                    address,
                    "The variable occurrence is outside the selected translation profile.",
                )
            )
            continue
        append_clause(
            ConstraintClauseModel(
                clause_id="target:" + hashlib.sha256(address.encode("utf-8")).hexdigest(),
                kind=ConstraintClauseKind.TARGET_DOMAIN,
                symbol_id=symbol.symbol_id,
                source_address=address,
                allowed_values=allowed,
            )
        )

    model = NormalizedConstraintModel(
        profile="aces-finite-domain-constraints/v1",
        theory_profile="aces-finite-domain-theory/v1",
        translation_profile="aces-sdl-authoring-translation/v1",
        source_digest=source_digest,
        authored_digest=canonical_sdl_digest(scenario).as_dict(),
        symbols=tuple(sorted(symbols.values(), key=lambda item: item.symbol_id)),
        clauses=tuple(sorted(clauses, key=lambda item: item.clause_id)),
    )
    return TranslationResult(
        model=model,
        diagnostics=diagnostics.as_tuple(),
    )


def _symbol(
    name: str,
    variable: Variable,
    diagnostics: _DiagnosticAccumulator,
) -> ConstraintSymbolModel | None:
    address = f"/variables/{_pointer(name)}"
    if variable.type is VariableType.NUMBER:
        diagnostics.add(_diagnostic(_DOMAIN_CODE, address, "The variable sort is not supported by this profile."))
        return None
    sort = {
        VariableType.STRING: ConstraintSort.STRING,
        VariableType.INTEGER: ConstraintSort.INTEGER,
        VariableType.BOOLEAN: ConstraintSort.BOOLEAN,
    }[variable.type]
    values: tuple[str | int | bool, ...]
    if variable.allowed_values:
        values = tuple(variable.allowed_values)  # type: ignore[assignment]
    elif variable.type is VariableType.BOOLEAN:
        values = (False, True)
    else:
        diagnostics.add(
            _diagnostic(_DOMAIN_CODE, address, "The variable requires an explicit finite allowed-values domain.")
        )
        return None
    canonical = tuple(sorted(values, key=rfc8785.dumps))
    if len(canonical) > _MAX_DOMAIN_MEMBERS or len({rfc8785.dumps(item) for item in canonical}) != len(canonical):
        diagnostics.add(_diagnostic(_DOMAIN_CODE, address, "The variable domain is invalid or exceeds its limit."))
        return None
    return ConstraintSymbolModel(
        symbol_id=_stable_id("symbol", name),
        variable=name,
        sort=sort,
        domain=canonical,
    )


def _variable_occurrences(value: Any, address: str = ""):
    if isinstance(value, dict):
        for key in sorted(value, key=str):
            yield from _variable_occurrences(value[key], f"{address}/{_pointer(str(key))}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _variable_occurrences(item, f"{address}/{index}")
        return
    if not isinstance(value, str):
        return
    whole = extract_variable_name(value)
    if whole is not None:
        yield address, whole, False
        return
    for name in variable_names_in_value(value):
        yield address, name, True


def _target_domain(
    address: str,
    symbol: ConstraintSymbolModel,
) -> tuple[str | int | bool, ...] | None:
    parts = address.split("/")[1:]
    if len(parts) == 3 and parts[0] == "nodes" and parts[2] == "os" and symbol.sort is ConstraintSort.STRING:
        vocabulary = {item.value for item in OSFamily}
        return tuple(value for value in symbol.domain if normalize_enum_value(value) in vocabulary)  # type: ignore[arg-type]
    if (
        len(parts) == 5
        and parts[0] == "infrastructure"
        and parts[2] == "acls"
        and parts[4] == "action"
        and symbol.sort is ConstraintSort.STRING
    ):
        vocabulary = {item.value for item in ACLAction}
        return tuple(value for value in symbol.domain if normalize_enum_value(value) in vocabulary)  # type: ignore[arg-type]
    if (
        len(parts) == 3
        and parts[0] == "infrastructure"
        and parts[2] == "count"
        and symbol.sort is ConstraintSort.INTEGER
    ):
        return tuple(value for value in symbol.domain if isinstance(value, int) and value >= 1)  # type: ignore[return-value]
    if (
        len(parts) == 4
        and parts[0] == "infrastructure"
        and parts[2] == "properties"
        and parts[3] == "internal"
        and symbol.sort is ConstraintSort.BOOLEAN
    ):
        return symbol.domain
    return None


def _diagnostic(code: str, address: str, message: str) -> DiagnosticModel:
    return DiagnosticModel(
        code=code,
        domain="scenario-satisfiability",
        address=address,
        message=message,
        severity="error",
    )


def _pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _stable_id(prefix: str, value: str) -> str:
    """Keep ids closed and collision-resistant for every legal SDL identifier."""

    return f"{prefix}:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"
