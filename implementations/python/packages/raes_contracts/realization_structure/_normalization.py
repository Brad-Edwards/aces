"""Literal normalization for recursive realization constraints."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from ._build import RealizationConstraintBuildResult, build_failure
from ._common import RelationBudget, actual_identity, pointer, pointer_tokens
from ._limits import admit_normalization_metadata
from ._models import (
    DEFAULT_REALIZATION_CONSTRAINT_LIMITS,
    DEFAULT_UNDEFINED_REALIZATION_CLOSURE,
    RealizationClosure,
    RealizationCollectionMember,
    RealizationCollectionProfile,
    RealizationConstraintDocument,
    RealizationConstraintLimits,
    RealizationKeyedCollectionConstraint,
    RealizationLiteral,
    RealizationOrigin,
    RealizationRecordConstraint,
    RealizationRelationStatus,
    RealizationScope,
    RealizationSequenceConstraint,
    RecursiveRealizationStructure,
    identity_key,
)


def normalize_realization_literal(
    value: object,
    *,
    semantic_profile: str,
    default_closure: RealizationClosure = DEFAULT_UNDEFINED_REALIZATION_CLOSURE,
    scopes: tuple[RealizationScope, ...] = (),
    collection_profiles: tuple[RealizationCollectionProfile, ...] = (),
    origins: Mapping[str, RealizationOrigin | str] | None = None,
    limits: RealizationConstraintLimits = DEFAULT_REALIZATION_CONSTRAINT_LIMITS,
) -> RealizationConstraintBuildResult:
    """Lower ordinary JSON literals without requiring wrappers around scalars."""

    budget = RelationBudget(limits)
    origins = origins or {}
    result = _normalization_metadata_failure(scopes, collection_profiles, origins, budget)
    profiles, profile_failure = _collection_profile_map(collection_profiles)
    result = result or profile_failure
    normalized_scopes: tuple[RealizationScope, ...] = ()
    if result is None:
        normalized_scopes, result = _normalize_scope_identities(scopes, value, profiles, budget)
    if result is None:
        result = _normalize_document(
            value,
            semantic_profile,
            default_closure,
            normalized_scopes,
            origins,
            profiles,
            budget,
        )
    return result


def _normalization_metadata_failure(
    scopes: tuple[RealizationScope, ...],
    collection_profiles: tuple[RealizationCollectionProfile, ...],
    origins: Mapping[str, RealizationOrigin | str],
    budget: RelationBudget,
) -> RealizationConstraintBuildResult | None:
    violation = admit_normalization_metadata(scopes, collection_profiles, origins, budget)
    return (
        None
        if violation is None
        else build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            violation.pointer,
            violation.message,
        )
    )


def _collection_profile_map(
    collection_profiles: tuple[RealizationCollectionProfile, ...],
) -> tuple[dict[str, RealizationCollectionProfile], RealizationConstraintBuildResult | None]:
    profile_pointers = [profile.field_pointer for profile in collection_profiles]
    profiles = {profile.field_pointer: profile for profile in collection_profiles}
    failure = (
        None
        if len(profile_pointers) == len(profiles)
        else build_failure(
            RealizationRelationStatus.INVALID,
            "",
            "Collection profiles must have unique field_pointer values.",
        )
    )
    return profiles, failure


def _normalize_document(
    value: object,
    semantic_profile: str,
    default_closure: RealizationClosure,
    normalized_scopes: tuple[RealizationScope, ...],
    origins: Mapping[str, RealizationOrigin | str],
    profiles: Mapping[str, RealizationCollectionProfile],
    budget: RelationBudget,
) -> RealizationConstraintBuildResult:
    normalized, result = normalize_literal_node(value, (), (), budget, origins, profiles)
    if result is None:
        assert normalized is not None
        document = RealizationConstraintDocument(
            semantic_profile=semantic_profile,
            default_closure=default_closure,
            scopes=normalized_scopes,
            root=normalized,
        )
        result = RealizationConstraintBuildResult(RealizationRelationStatus.CONFORMANT, document)
    assert result is not None
    return result


MISSING_SCOPE_VALUE = object()


@dataclass
class _ScopeCursor:
    source_path: list[str]
    semantic_path: list[str]
    current: object


def _advance_keyed_scope(
    cursor: _ScopeCursor,
    token: str,
    profile: RealizationCollectionProfile,
    address: str,
    budget: RelationBudget,
) -> RealizationConstraintBuildResult | None:
    failure = None
    assert isinstance(cursor.current, list)
    if not token.isdigit() or int(token) >= len(cursor.current):
        failure = build_failure(
            RealizationRelationStatus.INVALID,
            address,
            "A keyed-collection scope must resolve an authored member position.",
        )
    elif exhausted := budget.spend_identity():
        failure = build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            address,
            f"Scope normalization exceeded {exhausted}.",
        )
    else:
        item = cursor.current[int(token)]
        identity = actual_identity(item, profile.identity_fields)
        if identity is None:
            failure = build_failure(
                RealizationRelationStatus.INVALID,
                address,
                "A keyed-collection scope resolves a member without concrete semantic identity.",
            )
        else:
            cursor.semantic_path.append(f"@{identity_key(identity)}")
            cursor.source_path.append(token)
            cursor.current = item
    return failure


def _advance_plain_scope(cursor: _ScopeCursor, token: str) -> None:
    cursor.semantic_path.append(token)
    cursor.source_path.append(token)
    if isinstance(cursor.current, Mapping):
        cursor.current = cursor.current.get(token, MISSING_SCOPE_VALUE)
    elif isinstance(cursor.current, list) and token.isdigit() and int(token) < len(cursor.current):
        cursor.current = cursor.current[int(token)]
    else:
        cursor.current = MISSING_SCOPE_VALUE


def _normalize_one_scope(
    scope: RealizationScope,
    value: object,
    collection_profiles: Mapping[str, RealizationCollectionProfile],
    budget: RelationBudget,
) -> tuple[RealizationScope | None, RealizationConstraintBuildResult | None]:
    cursor = _ScopeCursor([], [], value)
    failure = None
    for token in pointer_tokens(scope.field_pointer):
        exhausted = budget.spend_operation()
        if exhausted is not None:
            failure = build_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                scope.field_pointer,
                f"Scope normalization exceeded {exhausted}.",
            )
        else:
            profile = collection_profiles.get(pointer(tuple(cursor.source_path)))
            if isinstance(cursor.current, list) and profile is not None:
                failure = _advance_keyed_scope(cursor, token, profile, scope.field_pointer, budget)
            else:
                _advance_plain_scope(cursor, token)
        if failure is not None:
            break
    normalized = (
        None
        if failure is not None
        else scope.model_copy(update={"field_pointer": pointer(tuple(cursor.semantic_path))})
    )
    return normalized, failure


def _normalize_scope_identities(
    scopes: tuple[RealizationScope, ...],
    value: object,
    collection_profiles: Mapping[str, RealizationCollectionProfile],
    budget: RelationBudget,
) -> tuple[tuple[RealizationScope, ...], RealizationConstraintBuildResult | None]:
    normalized: list[RealizationScope] = []
    failure = None
    for scope in scopes:
        if exhausted := budget.spend_operation():
            failure = build_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                scope.field_pointer,
                f"Scope normalization exceeded {exhausted}.",
            )
        else:
            converted, failure = _normalize_one_scope(scope, value, collection_profiles, budget)
            if failure is None:
                assert converted is not None
                normalized.append(converted)
        if failure is not None:
            break
    pointers = [scope.field_pointer for scope in normalized]
    if failure is None and len(pointers) != len(set(pointers)):
        failure = build_failure(
            RealizationRelationStatus.INVALID,
            "",
            "Scope normalization produced duplicate semantic member addresses.",
        )
    return (() if failure is not None else tuple(normalized)), failure


def _normalization_origin(
    origins: Mapping[str, RealizationOrigin | str],
    path: tuple[str, ...],
) -> RealizationOrigin:
    return RealizationOrigin(origins.get(pointer(path), RealizationOrigin.AUTHOR))


@dataclass(frozen=True)
class _NormalizationContext:
    budget: RelationBudget
    origins: Mapping[str, RealizationOrigin | str]
    collection_profiles: Mapping[str, RealizationCollectionProfile]


def normalize_literal_node(
    value: object,
    semantic_path: tuple[str, ...],
    source_path: tuple[str, ...],
    budget: RelationBudget,
    origins: Mapping[str, RealizationOrigin | str],
    collection_profiles: Mapping[str, RealizationCollectionProfile],
) -> tuple[RecursiveRealizationStructure | None, RealizationConstraintBuildResult | None]:
    """Normalize one subtree while retaining the compatibility-call boundary."""

    context = _NormalizationContext(budget, origins, collection_profiles)
    return _normalize_literal_node(value, semantic_path, source_path, context)


def _normalize_literal_node(
    value: object,
    semantic_path: tuple[str, ...],
    source_path: tuple[str, ...],
    context: _NormalizationContext,
) -> tuple[RecursiveRealizationStructure | None, RealizationConstraintBuildResult | None]:
    current_pointer = pointer(semantic_path)
    normalized = None
    failure = None
    if exhausted := context.budget.spend_node(len(semantic_path)):
        failure = build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            f"Literal normalization exceeded {exhausted}.",
        )
    if failure is None:
        origin = _normalization_origin(context.origins, source_path)
        if isinstance(value, dict):
            normalized, failure = _normalize_record(value, semantic_path, source_path, context, origin)
        elif isinstance(value, list):
            normalized, failure = _normalize_collection(value, semantic_path, source_path, context, origin)
        else:
            normalized, failure = _normalize_scalar(value, current_pointer, context.budget, origin)
    return normalized, failure


def _normalize_record(
    value: Mapping[object, object],
    semantic_path: tuple[str, ...],
    source_path: tuple[str, ...],
    context: _NormalizationContext,
    origin: RealizationOrigin,
) -> tuple[RecursiveRealizationStructure | None, RealizationConstraintBuildResult | None]:
    fields: dict[str, RecursiveRealizationStructure] = {}
    failure = None
    if len(value) > context.budget.limits.max_members:
        failure = build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            pointer(semantic_path),
            "Literal normalization exceeded max_members.",
        )
    else:
        for key, child in value.items():
            if not isinstance(key, str):
                failure = build_failure(
                    RealizationRelationStatus.INVALID,
                    pointer(semantic_path),
                    "Literal normalization requires string record keys.",
                )
            else:
                normalized, failure = _normalize_literal_node(
                    child,
                    (*semantic_path, key),
                    (*source_path, key),
                    context,
                )
                if failure is None:
                    assert normalized is not None
                    fields[key] = normalized
            if failure is not None:
                break
    node = (
        None
        if failure is not None
        else RealizationRecordConstraint(kind="recursive-record", fields=fields, origin=origin)
    )
    return node, failure


def _normalize_collection(
    value: list[object],
    semantic_path: tuple[str, ...],
    source_path: tuple[str, ...],
    context: _NormalizationContext,
    origin: RealizationOrigin,
) -> tuple[RecursiveRealizationStructure | None, RealizationConstraintBuildResult | None]:
    failure = None
    node = None
    if len(value) > context.budget.limits.max_members:
        failure = build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            pointer(semantic_path),
            "Literal normalization exceeded max_members.",
        )
    else:
        profile = context.collection_profiles.get(pointer(source_path))
        if profile is not None:
            node, failure = _normalize_keyed_collection(value, semantic_path, source_path, context, profile, origin)
        else:
            node, failure = _normalize_sequence(value, semantic_path, source_path, context, origin)
    return node, failure


def _normalize_sequence(
    value: list[object],
    semantic_path: tuple[str, ...],
    source_path: tuple[str, ...],
    context: _NormalizationContext,
    origin: RealizationOrigin,
) -> tuple[RecursiveRealizationStructure | None, RealizationConstraintBuildResult | None]:
    items: list[RecursiveRealizationStructure] = []
    failure = None
    for index, child in enumerate(value):
        normalized, failure = _normalize_literal_node(
            child,
            (*semantic_path, str(index)),
            (*source_path, str(index)),
            context,
        )
        if failure is not None:
            break
        assert normalized is not None
        items.append(normalized)
    node = (
        None
        if failure is not None
        else RealizationSequenceConstraint(kind="sequence", items=tuple(items), origin=origin)
    )
    return node, failure


def _normalize_scalar(
    value: object,
    address: str,
    budget: RelationBudget,
    origin: RealizationOrigin,
) -> tuple[RecursiveRealizationStructure | None, RealizationConstraintBuildResult | None]:
    failure = None
    if type(value) not in (str, int, float, bool, type(None)):
        failure = build_failure(
            RealizationRelationStatus.INVALID,
            address,
            "Literal normalization accepts only JSON-compatible values.",
        )
    elif isinstance(value, str) and len(value.encode("utf-8")) > budget.limits.max_scalar_bytes:
        failure = build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            address,
            "Literal normalization exceeded max_scalar_bytes.",
        )
    elif isinstance(value, float) and not math.isfinite(value):
        failure = build_failure(
            RealizationRelationStatus.INVALID,
            address,
            "Literal normalization requires finite JSON numbers.",
        )
    elif type(value) is int and value.bit_length() > budget.limits.max_scalar_bytes * 8:
        failure = build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            address,
            "Literal normalization exceeded the integer-size limit.",
        )
    node = None if failure is not None else RealizationLiteral(kind="literal", value=value, origin=origin)
    return node, failure


def _normalize_keyed_collection(
    value: list[object],
    semantic_path: tuple[str, ...],
    source_path: tuple[str, ...],
    context: _NormalizationContext,
    profile: RealizationCollectionProfile,
    origin: RealizationOrigin,
) -> tuple[RecursiveRealizationStructure | None, RealizationConstraintBuildResult | None]:
    members: list[RealizationCollectionMember] = []
    identities: set[str] = set()
    failure = None
    for index, child in enumerate(value):
        if exhausted := context.budget.spend_identity():
            failure = build_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                pointer(semantic_path),
                f"Profiled collection normalization exceeded {exhausted}.",
            )
        else:
            identity = actual_identity(child, profile.identity_fields)
            if identity is None:
                failure = build_failure(
                    RealizationRelationStatus.INVALID,
                    pointer((*semantic_path, str(index))),
                    "A profiled collection member has no complete concrete semantic identity.",
                )
            else:
                key = identity_key(identity)
                if key in identities:
                    failure = build_failure(
                        RealizationRelationStatus.INVALID,
                        pointer(semantic_path),
                        "A profiled collection contains a duplicate semantic identity.",
                    )
                else:
                    identities.add(key)
                    normalized, failure = _normalize_literal_node(
                        child,
                        (*semantic_path, f"@{key}"),
                        (*source_path, str(index)),
                        context,
                    )
                    if failure is None:
                        assert normalized is not None
                        members.append(RealizationCollectionMember(identity=identity, constraint=normalized))
        if failure is not None:
            break
    node = (
        None
        if failure is not None
        else RealizationKeyedCollectionConstraint(
            kind="keyed-collection",
            collection_kind=profile.collection_kind,
            identity_fields=profile.identity_fields,
            members=tuple(members),
            closure=profile.closure,
            origin=origin,
        )
    )
    return node, failure
