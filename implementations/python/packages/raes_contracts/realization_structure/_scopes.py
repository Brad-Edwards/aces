"""Evaluation of lexical scopes independently of materialized constraints."""

from __future__ import annotations

from ._common import RealizationRelationResult, RelationBudget, actual_identity, pointer_tokens, relation_result
from ._models import (
    RealizationClosurePosture,
    RealizationConstraintDocument,
    RealizationDelegatedValue,
    RealizationKeyedCollectionConstraint,
    RealizationRecordConstraint,
    RealizationRelationStatus,
    RealizationSequenceConstraint,
    RecursiveRealizationStructure,
    identity_key,
)


def _scope_failure(
    status: RealizationRelationStatus,
    address: str,
    message: str,
) -> list[RealizationRelationResult]:
    return [relation_result(status, address, message)]


def _spend_operation(
    budget: RelationBudget,
    address: str,
) -> list[RealizationRelationResult] | None:
    if exhausted := budget.spend_operation():
        return _scope_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            address,
            f"Scope evaluation exceeded {exhausted}.",
        )
    return None


def _indexed_keyed_actual(
    actual: list[object],
    rule: RealizationKeyedCollectionConstraint,
    address: str,
    budget: RelationBudget,
) -> tuple[dict[str, object] | None, list[RealizationRelationResult] | None]:
    indexed: dict[str, object] = {}
    aliases: dict[str, tuple[str | int | bool, ...]] = {}
    for alias in rule.aliases:
        if exhausted := budget.spend_identity():
            return None, _scope_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                address,
                f"Scope identity resolution exceeded {exhausted}.",
            )
        aliases[identity_key(alias.identity)] = alias.target
    for item in actual:
        if exhausted := budget.spend_identity():
            return None, _scope_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                address,
                f"Scope identity resolution exceeded {exhausted}.",
            )
        identity = actual_identity(item, rule.identity_fields)
        if identity is None:
            return None, _scope_failure(
                RealizationRelationStatus.INVALID,
                address,
                "A scoped keyed member has no complete concrete semantic identity.",
            )
        source_key = identity_key(identity)
        canonical = aliases.get(source_key, identity)
        if source_key in aliases and (exhausted := budget.spend_identity()):
            return None, _scope_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                address,
                f"Scope identity resolution exceeded {exhausted}.",
            )
        key = identity_key(canonical)
        if key in indexed:
            return None, _scope_failure(
                RealizationRelationStatus.INVALID,
                address,
                "A scoped keyed collection contains a duplicate semantic identity.",
            )
        indexed[key] = item
    return indexed, None


def _keyed_rule_members(
    rule: RealizationKeyedCollectionConstraint,
    address: str,
    budget: RelationBudget,
) -> tuple[dict[str, RecursiveRealizationStructure] | None, list[RealizationRelationResult] | None]:
    members: dict[str, RecursiveRealizationStructure] = {}
    for member in rule.members:
        if exhausted := budget.spend_identity():
            return None, _scope_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                address,
                f"Scope identity resolution exceeded {exhausted}.",
            )
        members[identity_key(member.identity)] = member.constraint
    return members, None


def _resolve_scope_target(
    document: RealizationConstraintDocument,
    actual: object,
    address: str,
    budget: RelationBudget,
) -> tuple[object | None, RecursiveRealizationStructure | None, bool, list[RealizationRelationResult] | None]:
    current_actual = actual
    current_rule: RecursiveRealizationStructure | None = document.root
    for token in pointer_tokens(address):
        if failure := _spend_operation(budget, address):
            return None, None, False, failure
        if isinstance(current_actual, dict):
            if token not in current_actual:
                return None, None, False, None
            current_actual = current_actual[token]
            if isinstance(current_rule, RealizationRecordConstraint):
                current_rule = current_rule.fields.get(token)
            elif not isinstance(current_rule, (RealizationDelegatedValue, type(None))):
                return (
                    None,
                    None,
                    False,
                    _scope_failure(
                        RealizationRelationStatus.UNSUPPORTED,
                        address,
                        "A scope cannot select record fields through this constraint kind.",
                    ),
                )
            else:
                current_rule = None
            continue
        if isinstance(current_actual, list):
            if isinstance(current_rule, RealizationKeyedCollectionConstraint):
                if not token.startswith("@sha256:"):
                    return (
                        None,
                        None,
                        False,
                        _scope_failure(
                            RealizationRelationStatus.UNSUPPORTED,
                            address,
                            "A keyed-collection scope must use a semantic member identity.",
                        ),
                    )
                actual_members, failure = _indexed_keyed_actual(current_actual, current_rule, address, budget)
                if failure is not None:
                    return None, None, False, failure
                rule_members, failure = _keyed_rule_members(current_rule, address, budget)
                if failure is not None:
                    return None, None, False, failure
                assert actual_members is not None and rule_members is not None
                key = token.removeprefix("@")
                if key not in actual_members:
                    return None, None, False, None
                current_actual = actual_members[key]
                current_rule = rule_members.get(key)
                continue
            if token.isdigit() and isinstance(current_rule, (RealizationSequenceConstraint, type(None))):
                index = int(token)
                if index >= len(current_actual):
                    return None, None, False, None
                current_actual = current_actual[index]
                current_rule = (
                    current_rule.items[index]
                    if isinstance(current_rule, RealizationSequenceConstraint) and index < len(current_rule.items)
                    else None
                )
                continue
            return (
                None,
                None,
                False,
                _scope_failure(
                    RealizationRelationStatus.UNSUPPORTED,
                    address,
                    "A collection scope cannot be interpreted without its collection shape.",
                ),
            )
        return (
            None,
            None,
            False,
            _scope_failure(
                RealizationRelationStatus.UNSUPPORTED,
                address,
                "A scope descends through a non-container value.",
            ),
        )
    return current_actual, current_rule, True, None


def _evaluate_closed_target(
    document: RealizationConstraintDocument,
    actual: object,
    rule: RecursiveRealizationStructure | None,
    address: str,
    budget: RelationBudget,
) -> list[RealizationRelationResult]:
    scope_tokens = pointer_tokens(address)
    declared_by_scope: set[str] = set()
    for declared_scope in document.scopes:
        if failure := _spend_operation(budget, address):
            return failure
        tokens = pointer_tokens(declared_scope.field_pointer)
        if tokens[: len(scope_tokens)] == scope_tokens and len(tokens) > len(scope_tokens):
            declared_by_scope.add(tokens[len(scope_tokens)])
    if isinstance(actual, dict):
        declared = set(rule.fields) if isinstance(rule, RealizationRecordConstraint) else set()
        declared.update(token for token in declared_by_scope if not token.startswith("@") and not token.isdigit())
        return (
            _scope_failure(
                RealizationRelationStatus.NONCONFORMANT,
                address,
                "A closed scope contains an undeclared record member in its named universe.",
            )
            if actual.keys() - declared
            else []
        )
    if isinstance(actual, list):
        if isinstance(rule, RealizationKeyedCollectionConstraint):
            indexed, failure = _indexed_keyed_actual(actual, rule, address, budget)
            if failure is not None:
                return failure
            declared, failure = _keyed_rule_members(rule, address, budget)
            if failure is not None:
                return failure
            assert indexed is not None and declared is not None
            declared_keys = set(declared) | {token.removeprefix("@") for token in declared_by_scope}
            has_extras = bool(indexed.keys() - declared_keys)
        elif isinstance(rule, RealizationSequenceConstraint):
            declared_indices = set(range(len(rule.items))) | {
                int(token) for token in declared_by_scope if token.isdigit()
            }
            has_extras = any(index not in declared_indices for index in range(len(actual)))
        else:
            declared_indices = {int(token) for token in declared_by_scope if token.isdigit()}
            has_extras = any(index not in declared_indices for index in range(len(actual)))
        return (
            _scope_failure(
                RealizationRelationStatus.NONCONFORMANT,
                address,
                "A closed scope contains an undeclared collection member in its named universe.",
            )
            if has_extras
            else []
        )
    return _scope_failure(
        RealizationRelationStatus.UNSUPPORTED,
        address,
        "A closure scope must address a record or collection value.",
    )


def evaluate_scope_overlays(
    document: RealizationConstraintDocument,
    actual: object,
    budget: RelationBudget,
) -> list[RealizationRelationResult]:
    """Apply every declared scope, including those beneath open or delegated nodes."""

    results: list[RealizationRelationResult] = []
    for scope in document.scopes:
        target, rule, present, failure = _resolve_scope_target(
            document,
            actual,
            scope.field_pointer,
            budget,
        )
        if failure is not None:
            results.extend(failure)
            continue
        if not present:
            continue
        if not isinstance(target, (dict, list)):
            results.extend(
                _scope_failure(
                    RealizationRelationStatus.UNSUPPORTED,
                    scope.field_pointer,
                    "A closure scope must address a record or collection value.",
                )
            )
            continue
        if scope.closure.posture is RealizationClosurePosture.OPEN:
            continue
        if isinstance(rule, RealizationDelegatedValue):
            rule = None
        elif rule is not None and not isinstance(
            rule,
            (RealizationRecordConstraint, RealizationKeyedCollectionConstraint, RealizationSequenceConstraint),
        ):
            results.extend(
                _scope_failure(
                    RealizationRelationStatus.UNSUPPORTED,
                    scope.field_pointer,
                    "A closure scope cannot be interpreted for this constraint kind.",
                )
            )
            continue
        results.extend(_evaluate_closed_target(document, target, rule, scope.field_pointer, budget))
    return results
