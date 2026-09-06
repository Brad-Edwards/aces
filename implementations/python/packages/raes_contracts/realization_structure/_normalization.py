"""Literal normalization for recursive realization constraints."""

from __future__ import annotations

import math
from collections.abc import Mapping

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
    if violation := admit_normalization_metadata(scopes, collection_profiles, origins, budget):
        return build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            violation.pointer,
            violation.message,
        )
    profile_pointers = [profile.field_pointer for profile in collection_profiles]
    if len(profile_pointers) != len(set(profile_pointers)):
        return build_failure(
            RealizationRelationStatus.INVALID,
            "",
            "Collection profiles must have unique field_pointer values.",
        )
    profiles = {profile.field_pointer: profile for profile in collection_profiles}
    normalized_scopes, scope_failure = _normalize_scope_identities(scopes, value, profiles, budget)
    if scope_failure is not None:
        return scope_failure
    normalized, failure = normalize_literal_node(value, (), (), budget, origins, profiles)
    if failure is not None:
        return failure
    assert normalized is not None
    document = RealizationConstraintDocument(
        semantic_profile=semantic_profile,
        default_closure=default_closure,
        scopes=normalized_scopes,
        root=normalized,
    )
    return RealizationConstraintBuildResult(RealizationRelationStatus.CONFORMANT, document)


MISSING_SCOPE_VALUE = object()


def _normalize_scope_identities(
    scopes: tuple[RealizationScope, ...],
    value: object,
    collection_profiles: Mapping[str, RealizationCollectionProfile],
    budget: RelationBudget,
) -> tuple[tuple[RealizationScope, ...], RealizationConstraintBuildResult | None]:
    normalized: list[RealizationScope] = []
    for scope in scopes:
        if exhausted := budget.spend_operation():
            return (), build_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                scope.field_pointer,
                f"Scope normalization exceeded {exhausted}.",
            )
        source_path: list[str] = []
        semantic_path: list[str] = []
        current = value
        for token in pointer_tokens(scope.field_pointer):
            if exhausted := budget.spend_operation():
                return (), build_failure(
                    RealizationRelationStatus.LIMIT_EXCEEDED,
                    scope.field_pointer,
                    f"Scope normalization exceeded {exhausted}.",
                )
            profile = collection_profiles.get(pointer(tuple(source_path)))
            if isinstance(current, list) and profile is not None:
                if not token.isdigit() or int(token) >= len(current):
                    return (), build_failure(
                        RealizationRelationStatus.INVALID,
                        scope.field_pointer,
                        "A keyed-collection scope must resolve an authored member position.",
                    )
                item = current[int(token)]
                if exhausted := budget.spend_identity():
                    return (), build_failure(
                        RealizationRelationStatus.LIMIT_EXCEEDED,
                        scope.field_pointer,
                        f"Scope normalization exceeded {exhausted}.",
                    )
                identity = actual_identity(item, profile.identity_fields)
                if identity is None:
                    return (), build_failure(
                        RealizationRelationStatus.INVALID,
                        scope.field_pointer,
                        "A keyed-collection scope resolves a member without concrete semantic identity.",
                    )
                semantic_path.append(f"@{identity_key(identity)}")
                source_path.append(token)
                current = item
                continue
            semantic_path.append(token)
            source_path.append(token)
            if isinstance(current, Mapping):
                current = current.get(token, MISSING_SCOPE_VALUE)
            elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
                current = current[int(token)]
            else:
                current = MISSING_SCOPE_VALUE
        normalized.append(scope.model_copy(update={"field_pointer": pointer(tuple(semantic_path))}))
    pointers = [scope.field_pointer for scope in normalized]
    if len(pointers) != len(set(pointers)):
        return (), build_failure(
            RealizationRelationStatus.INVALID,
            "",
            "Scope normalization produced duplicate semantic member addresses.",
        )
    return tuple(normalized), None


def _normalization_origin(
    origins: Mapping[str, RealizationOrigin | str],
    path: tuple[str, ...],
) -> RealizationOrigin:
    return RealizationOrigin(origins.get(pointer(path), RealizationOrigin.AUTHOR))


def normalize_literal_node(
    value: object,
    semantic_path: tuple[str, ...],
    source_path: tuple[str, ...],
    budget: RelationBudget,
    origins: Mapping[str, RealizationOrigin | str],
    collection_profiles: Mapping[str, RealizationCollectionProfile],
) -> tuple[RecursiveRealizationStructure | None, RealizationConstraintBuildResult | None]:
    current_pointer = pointer(semantic_path)
    if exhausted := budget.spend_node(len(semantic_path)):
        return None, build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            f"Literal normalization exceeded {exhausted}.",
        )
    origin = _normalization_origin(origins, source_path)
    if isinstance(value, dict):
        if len(value) > budget.limits.max_members:
            return None, build_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                current_pointer,
                "Literal normalization exceeded max_members.",
            )
        fields: dict[str, RecursiveRealizationStructure] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                return None, build_failure(
                    RealizationRelationStatus.INVALID,
                    current_pointer,
                    "Literal normalization requires string record keys.",
                )
            normalized, failure = normalize_literal_node(
                child,
                (*semantic_path, key),
                (*source_path, key),
                budget,
                origins,
                collection_profiles,
            )
            if failure is not None:
                return None, failure
            assert normalized is not None
            fields[key] = normalized
        return RealizationRecordConstraint(kind="recursive-record", fields=fields, origin=origin), None
    if isinstance(value, list):
        if len(value) > budget.limits.max_members:
            return None, build_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                current_pointer,
                "Literal normalization exceeded max_members.",
            )
        collection_profile = collection_profiles.get(pointer(source_path))
        if collection_profile is not None:
            return _normalize_keyed_collection(
                value,
                semantic_path,
                source_path,
                budget,
                origins,
                collection_profiles,
                collection_profile,
                origin,
            )
        items: list[RecursiveRealizationStructure] = []
        for index, child in enumerate(value):
            normalized, failure = normalize_literal_node(
                child,
                (*semantic_path, str(index)),
                (*source_path, str(index)),
                budget,
                origins,
                collection_profiles,
            )
            if failure is not None:
                return None, failure
            assert normalized is not None
            items.append(normalized)
        return RealizationSequenceConstraint(kind="sequence", items=tuple(items), origin=origin), None
    if type(value) not in (str, int, float, bool, type(None)):
        return None, build_failure(
            RealizationRelationStatus.INVALID,
            current_pointer,
            "Literal normalization accepts only JSON-compatible values.",
        )
    if isinstance(value, str) and len(value.encode("utf-8")) > budget.limits.max_scalar_bytes:
        return None, build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            "Literal normalization exceeded max_scalar_bytes.",
        )
    if isinstance(value, float) and not math.isfinite(value):
        return None, build_failure(
            RealizationRelationStatus.INVALID,
            current_pointer,
            "Literal normalization requires finite JSON numbers.",
        )
    if type(value) is int and value.bit_length() > budget.limits.max_scalar_bytes * 8:
        return None, build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            "Literal normalization exceeded the integer-size limit.",
        )
    return RealizationLiteral(kind="literal", value=value, origin=origin), None


def _normalize_keyed_collection(
    value: list[object],
    semantic_path: tuple[str, ...],
    source_path: tuple[str, ...],
    budget: RelationBudget,
    origins: Mapping[str, RealizationOrigin | str],
    collection_profiles: Mapping[str, RealizationCollectionProfile],
    profile: RealizationCollectionProfile,
    origin: RealizationOrigin,
) -> tuple[RecursiveRealizationStructure | None, RealizationConstraintBuildResult | None]:
    members: list[RealizationCollectionMember] = []
    identities: set[str] = set()
    for index, child in enumerate(value):
        if exhausted := budget.spend_identity():
            return None, build_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                pointer(semantic_path),
                f"Profiled collection normalization exceeded {exhausted}.",
            )
        identity = actual_identity(child, profile.identity_fields)
        if identity is None:
            return None, build_failure(
                RealizationRelationStatus.INVALID,
                pointer((*semantic_path, str(index))),
                "A profiled collection member has no complete concrete semantic identity.",
            )
        key = identity_key(identity)
        if key in identities:
            return None, build_failure(
                RealizationRelationStatus.INVALID,
                pointer(semantic_path),
                "A profiled collection contains a duplicate semantic identity.",
            )
        identities.add(key)
        normalized, failure = normalize_literal_node(
            child,
            (*semantic_path, f"@{key}"),
            (*source_path, str(index)),
            budget,
            origins,
            collection_profiles,
        )
        if failure is not None:
            return None, failure
        assert normalized is not None
        members.append(RealizationCollectionMember(identity=identity, constraint=normalized))
    return (
        RealizationKeyedCollectionConstraint(
            kind="keyed-collection",
            collection_kind=profile.collection_kind,
            identity_fields=profile.identity_fields,
            members=tuple(members),
            closure=profile.closure,
            origin=origin,
        ),
        None,
    )
