"""Semantic admission for bounded scenario-family variation points."""

from __future__ import annotations

import math
from dataclasses import dataclass

from aces_contracts.bounded_domains import (
    BooleanDomain,
    EnumDomain,
    ExactDomain,
    NumericIntervalDomain,
    NumericType,
)
from pydantic import ValidationError

from .._errors import SDLValidationError
from .._identifiers import QualifiedName
from ..variables import Variable, VariableType
from ..variation import (
    COLLECTION_TARGET_SPECS,
    REFERENCE_TARGET_SPECS,
    TIMING_TARGET_SPECS,
    VARIATION_SATISFIABILITY_STATE_LIMIT,
    AlternativeVariationPoint,
    GovernedReferenceVariationPoint,
    LogicalTimingVariationPoint,
    OrderVariationPoint,
    ParameterVariationPoint,
    SelectionRelation,
    SubsetVariationPoint,
    VariationPoint,
    structural_members,
)

_SelectionVariable = tuple[str, str]
_SelectionLiteral = tuple[_SelectionVariable, bool]


@dataclass(frozen=True)
class _SelectionGroup:
    members: tuple[_SelectionVariable, ...]
    minimum: int
    maximum: int


class _SelectionBudgetExceeded(RuntimeError):
    pass


class _SelectionSatisfiability:
    def __init__(
        self,
        groups: list[_SelectionGroup],
        clauses: list[tuple[_SelectionLiteral, _SelectionLiteral]],
    ) -> None:
        self._groups = groups
        self._clauses = clauses
        self._variables = tuple(sorted(variable for group in groups for variable in group.members))
        self._remaining_states = VARIATION_SATISFIABILITY_STATE_LIMIT
        occurrence_count = {variable: 0 for variable in self._variables}
        for clause in clauses:
            for variable, _value in clause:
                occurrence_count[variable] += 1
        self._branch_order = tuple(sorted(self._variables, key=lambda item: (-occurrence_count[item], item)))

    def has_witness(self, required: dict[_SelectionVariable, bool] | None = None) -> bool:
        assignments = dict(required or {})
        return self._search(assignments, seen=set())

    def _search(
        self,
        assignments: dict[_SelectionVariable, bool],
        *,
        seen: set[frozenset[tuple[_SelectionVariable, bool]]],
    ) -> bool:
        self._remaining_states -= 1
        if self._remaining_states < 0:
            raise _SelectionBudgetExceeded
        if not self._propagate(assignments):
            return False
        state = frozenset(assignments.items())
        if state in seen:
            return False
        seen.add(state)
        variable = next((item for item in self._branch_order if item not in assignments), None)
        if variable is None:
            return True
        for value in (True, False):
            branch = dict(assignments)
            branch[variable] = value
            if self._search(branch, seen=seen):
                return True
        return False

    def _propagate(self, assignments: dict[_SelectionVariable, bool]) -> bool:
        changed = True
        while changed:
            changed = False
            for clause in self._clauses:
                unassigned: list[_SelectionLiteral] = []
                satisfied = False
                for variable, value in clause:
                    if variable not in assignments:
                        unassigned.append((variable, value))
                    elif assignments[variable] is value:
                        satisfied = True
                        break
                if satisfied:
                    continue
                if not unassigned:
                    return False
                if len(unassigned) == 1:
                    variable, value = unassigned[0]
                    if not self._assign(assignments, variable, value):
                        return False
                    changed = True
            for group in self._groups:
                selected = sum(assignments.get(member) is True for member in group.members)
                unknown = [member for member in group.members if member not in assignments]
                if selected > group.maximum or selected + len(unknown) < group.minimum:
                    return False
                forced_value: bool | None = None
                if selected == group.maximum:
                    forced_value = False
                elif selected + len(unknown) == group.minimum:
                    forced_value = True
                if forced_value is not None:
                    for member in unknown:
                        if not self._assign(assignments, member, forced_value):
                            return False
                        changed = True
        return True

    @staticmethod
    def _assign(
        assignments: dict[_SelectionVariable, bool],
        variable: _SelectionVariable,
        value: bool,
    ) -> bool:
        if variable in assignments:
            return assignments[variable] is value
        assignments[variable] = value
        return True


def _value_matches_variable(value: object, variable: Variable) -> bool:
    if variable.type is VariableType.STRING:
        return isinstance(value, str)
    if variable.type is VariableType.INTEGER:
        return isinstance(value, int) and not isinstance(value, bool)
    if variable.type is VariableType.BOOLEAN:
        return isinstance(value, bool)
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite_values(domain: object) -> list[object] | None:
    if isinstance(domain, ExactDomain):
        return [domain.value]
    if isinstance(domain, EnumDomain):
        return list(domain.values)
    if isinstance(domain, BooleanDomain):
        return [domain.value] if domain.value is not None else [False, True]
    return None


def _typed_contains(values: list[object], candidate: object) -> bool:
    return any(type(value) is type(candidate) and value == candidate for value in values)


def _integer_interval_members(domain: NumericIntervalDomain, limit: int) -> list[int] | None:
    lower = math.ceil(domain.lower)
    upper = math.floor(domain.upper)
    if not domain.lower_closed and lower == domain.lower:
        lower += 1
    if not domain.upper_closed and upper == domain.upper:
        upper -= 1
    count = max(0, upper - lower + 1)
    if count > limit:
        return None
    return list(range(lower, upper + 1))


def _domain_has_member(domain: object) -> bool:
    finite = _finite_values(domain)
    if finite is not None:
        return bool(finite)
    if not isinstance(domain, NumericIntervalDomain):
        return False
    if domain.numeric_type is NumericType.NUMBER:
        return True
    lower = math.ceil(domain.lower)
    upper = math.floor(domain.upper)
    if not domain.lower_closed and lower == domain.lower:
        lower += 1
    if not domain.upper_closed and upper == domain.upper:
        upper -= 1
    return lower <= upper


class _VariationMixin:
    def _verify_variation_points(self) -> None:
        for point_name, point in getattr(self._s, "variation_points", {}).items():
            if isinstance(point, ParameterVariationPoint):
                self._verify_parameter_point(point_name, point)
            elif isinstance(point, GovernedReferenceVariationPoint):
                self._verify_reference_point(point_name, point, list(point.domain.allowed_refs))
            elif isinstance(point, AlternativeVariationPoint):
                self._verify_reference_point(
                    point_name,
                    point,
                    [member.reference for member in point.alternatives.values()],
                )
                self._verify_member_relations(point_name, point)
            elif isinstance(point, (SubsetVariationPoint, OrderVariationPoint)):
                self._verify_collection_point(point_name, point)
                self._verify_member_relations(point_name, point)
            elif isinstance(point, LogicalTimingVariationPoint):
                self._verify_timing_point(point_name, point)
        if not self._errors:
            self._verify_family_satisfiability()

    def _verify_parameter_point(self, name: str, point: ParameterVariationPoint) -> None:
        variable = self._s.variables.get(point.target.variable)
        if variable is None:
            self._err(f"Variation point '{name}' target variable is undefined")
            return
        if not _domain_has_member(point.domain):
            self._err(f"Variation point '{name}' domain is empty")
            return
        finite = _finite_values(point.domain)
        type_matches = (
            all(_value_matches_variable(value, variable) for value in finite)
            if finite is not None
            else self._numeric_domain_matches_variable(point.domain, variable)
        )
        if not type_matches:
            self._err(f"Variation point '{name}' domain does not match variable type")
            return
        if variable.allowed_values and not self._domain_within_allowed_values(point.domain, variable):
            self._err(f"Variation point '{name}' domain exceeds the variable allowed_values constraint")

    @staticmethod
    def _numeric_domain_matches_variable(domain: object, variable: Variable) -> bool:
        if not isinstance(domain, NumericIntervalDomain):
            return False
        if variable.type is VariableType.INTEGER:
            return domain.numeric_type is NumericType.INTEGER
        return variable.type is VariableType.NUMBER

    @staticmethod
    def _domain_within_allowed_values(domain: object, variable: Variable) -> bool:
        allowed = list(variable.allowed_values)
        finite = _finite_values(domain)
        if finite is not None:
            return all(_typed_contains(allowed, value) for value in finite)
        if not isinstance(domain, NumericIntervalDomain) or domain.numeric_type is not NumericType.INTEGER:
            return False
        members = _integer_interval_members(domain, len(allowed))
        return members is not None and all(_typed_contains(allowed, value) for value in members)

    def _verify_reference_point(
        self,
        name: str,
        point: GovernedReferenceVariationPoint | AlternativeVariationPoint,
        candidates: list[str],
    ) -> None:
        owner_section, target_section = REFERENCE_TARGET_SPECS[point.target.slot]
        owner_valid = self._resolves_to(point.target.owner, owner_section)
        if not owner_valid:
            self._err(f"Variation point '{name}' target owner is undefined or has the wrong type")
        for reference in candidates:
            if not self._resolves_to(reference, target_section):
                self._err(f"Variation point '{name}' candidate reference is undefined or has the wrong type")
            elif owner_valid and not self._candidate_is_valid_for_slot(
                owner_section=owner_section,
                owner_reference=point.target.owner,
                slot=point.target.slot.value,
                candidate=reference,
                collection=False,
            ):
                self._err(f"Variation point '{name}' candidate is invalid for target slot")

    def _verify_collection_point(
        self,
        name: str,
        point: SubsetVariationPoint | OrderVariationPoint,
    ) -> None:
        owner_section, target_section = COLLECTION_TARGET_SPECS[point.target.slot]
        owner_valid = self._resolves_to(point.target.owner, owner_section)
        if not owner_valid:
            self._err(f"Variation point '{name}' target owner is undefined or has the wrong type")
        for member in point.members.values():
            if not self._resolves_to(member.reference, target_section):
                self._err(f"Variation point '{name}' candidate reference is undefined or has the wrong type")
            elif owner_valid and not self._candidate_is_valid_for_slot(
                owner_section=owner_section,
                owner_reference=point.target.owner,
                slot=point.target.slot.value,
                candidate=member.reference,
                collection=True,
            ):
                self._err(f"Variation point '{name}' candidate is invalid for target slot")

    def _verify_timing_point(self, name: str, point: LogicalTimingVariationPoint) -> None:
        owner_section, value_type, required_unit = TIMING_TARGET_SPECS[point.target.slot]
        if not self._resolves_to(point.target.owner, owner_section):
            self._err(f"Variation point '{name}' target owner is undefined or has the wrong type")
        if point.unit is not required_unit:
            self._err(f"Variation point '{name}' unit does not match target")
        if not _domain_has_member(point.domain):
            self._err(f"Variation point '{name}' domain is empty")
            return
        finite = _finite_values(point.domain)
        if finite is not None:
            matches = all(
                isinstance(value, int) and not isinstance(value, bool)
                if value_type == "integer"
                else isinstance(value, (int, float)) and not isinstance(value, bool)
                for value in finite
            )
        else:
            matches = isinstance(point.domain, NumericIntervalDomain) and (
                value_type == "number" or point.domain.numeric_type is NumericType.INTEGER
            )
        if not matches:
            self._err(f"Variation point '{name}' domain does not match timing target type")

    def _verify_member_relations(self, name: str, point: VariationPoint) -> None:
        for member_name, member in structural_members(point).items():
            required = self._relation_pairs(name, member_name, member.requires)
            excluded = self._relation_pairs(name, member_name, member.excludes)
            if required.intersection(excluded):
                self._err(f"Variation point '{name}' member '{member_name}' has contradictory relations")

    def _relation_pairs(
        self,
        owner_point: str,
        owner_member: str,
        relations: list[SelectionRelation],
    ) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for relation in relations:
            matches = self._variation_point_matches(relation.point)
            if not matches:
                self._err(f"Variation point '{owner_point}' member '{owner_member}' relation point is undefined")
                continue
            if len(matches) > 1:
                self._err(f"Variation point '{owner_point}' member '{owner_member}' relation point is ambiguous")
                continue
            target_name = matches[0]
            target_members = structural_members(self._s.variation_points[target_name])
            for member in relation.members:
                if member not in target_members:
                    self._err(f"Variation point '{owner_point}' member '{owner_member}' relation member is undefined")
                pairs.add((target_name, member))
        return pairs

    def _variation_point_matches(self, reference: str) -> list[str]:
        rendered = reference.removeprefix("variation_points.")
        matches: list[str] = []
        for name in self._s.variation_points:
            if rendered == name or rendered == QualifiedName.parse(name).parts[-1]:
                matches.append(name)
        return matches

    def _verify_family_satisfiability(self) -> None:
        groups: list[_SelectionGroup] = []
        clauses: list[tuple[_SelectionLiteral, _SelectionLiteral]] = []
        for point_name, point in getattr(self._s, "variation_points", {}).items():
            members = structural_members(point)
            if not members:
                continue
            variables = tuple((point_name, member_name) for member_name in sorted(members))
            if isinstance(point, AlternativeVariationPoint):
                minimum = maximum = 1
            elif isinstance(point, SubsetVariationPoint):
                minimum = point.minimum
                maximum = len(members) if point.maximum is None else point.maximum
            else:
                minimum = maximum = len(members)
            groups.append(_SelectionGroup(variables, minimum, maximum))
            for member_name, member in members.items():
                source = (point_name, member_name)
                clauses.extend(self._selection_relation_clauses(source, member.requires, required=True))
                clauses.extend(self._selection_relation_clauses(source, member.excludes, required=False))

        if not groups:
            return
        solver = _SelectionSatisfiability(groups, clauses)
        try:
            if not solver.has_witness():
                self._err("Variation point constraints have no satisfying selection")
                return
            for group in groups:
                for point_name, member_name in group.members:
                    if not solver.has_witness({(point_name, member_name): True}):
                        self._err(
                            f"Variation point '{point_name}' member '{member_name}' cannot participate "
                            "in any satisfying selection"
                        )
        except _SelectionBudgetExceeded:
            self._err("Variation point constraints exceed the deterministic satisfiability budget")

    def _selection_relation_clauses(
        self,
        source: _SelectionVariable,
        relations: list[SelectionRelation],
        *,
        required: bool,
    ) -> list[tuple[_SelectionLiteral, _SelectionLiteral]]:
        clauses: list[tuple[_SelectionLiteral, _SelectionLiteral]] = []
        for relation in relations:
            matches = self._variation_point_matches(relation.point)
            if len(matches) != 1:
                continue
            target_point = matches[0]
            for target_member in relation.members:
                clauses.append(((source, False), ((target_point, target_member), required)))
        return clauses

    def _candidate_is_valid_for_slot(
        self,
        *,
        owner_section: str,
        owner_reference: str,
        slot: str,
        candidate: str,
        collection: bool,
    ) -> bool:
        owner_addresses = self._resolved_addresses(owner_reference, owner_section)
        if len(owner_addresses) != 1:
            return False
        owner_name = owner_addresses[0].removeprefix(f"{owner_section}.")
        field_name = slot.split(".", 1)[1]
        payload = self._s.model_dump(mode="python", by_alias=True)
        owner_payload = payload.get(owner_section, {}).get(owner_name)
        if not isinstance(owner_payload, dict):
            return False
        if collection:
            current = owner_payload.get(field_name)
            owner_payload[field_name] = (
                {candidate: current.get(candidate, "")} if isinstance(current, dict) else [candidate]
            )
        else:
            owner_payload[field_name] = candidate
        payload["variation_points"] = {}
        try:
            candidate_scenario = type(self._s).model_validate(payload)
            type(self)(candidate_scenario).validate()
        except (ValidationError, SDLValidationError):
            return False
        return True

    def _resolved_addresses(self, reference: str, section: str) -> list[str]:
        if self._declaration_index is None:
            raise RuntimeError("declaration index must exist before variation validation")
        candidates = self._declaration_index.resolve(reference)
        if section == "targetable":
            return sorted(
                address
                for address in candidates
                if (declaration := self._declaration_index.declaration_for(address)) is not None
                and declaration.targetable
            )
        return sorted(address for address in candidates if address.startswith(f"{section}."))

    def _resolves_to(self, reference: str, section: str) -> bool:
        return len(self._resolved_addresses(reference, section)) == 1


__all__ = ["_VariationMixin"]
