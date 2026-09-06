"""Lossless conversion between legacy and recursive realization contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..diagnostics import Diagnostic
from ._build import RealizationConstraintBuildResult, build_failure
from ._common import (
    RelationBudget,
    actual_identity,
    closure_for,
    json_equal,
    pointer,
    recursive_diagnostic,
    validate_bounded_value,
)
from ._compatibility_checks import (
    CompatibilityLimit,
    constraint_is_exact,
    indexed_collection_for_downgrade,
)
from ._legacy import (
    ExactRealizationValue,
    OpenRealizationValue,
    RealizationCollection,
    RealizationRecord,
    RealizationStructure,
    realization_member_identity,
)
from ._limits import admit_constraint_document
from ._models import (
    DEFAULT_REALIZATION_CONSTRAINT_LIMITS,
    RealizationClosure,
    RealizationClosurePosture,
    RealizationCollectionMember,
    RealizationConstraintDocument,
    RealizationConstraintLimits,
    RealizationDelegatedValue,
    RealizationKeyedCollectionConstraint,
    RealizationLiteral,
    RealizationOrigin,
    RealizationPresence,
    RealizationRecordConstraint,
    RealizationRelationStatus,
    RealizationSequenceConstraint,
    RecursiveRealizationStructure,
    identity_key,
)
from ._normalization import normalize_literal_node


@dataclass(frozen=True)
class RealizationCompatibilityResult:
    """Lossless compatibility conversion for the pre-#1203 structure subset."""

    status: RealizationRelationStatus
    structure: RealizationStructure | None = None
    diagnostics: tuple[Diagnostic, ...] = ()


def upgrade_legacy_realization_structure(
    structure: RealizationStructure,
    expected: object,
    *,
    semantic_profile: str,
    limits: RealizationConstraintLimits = DEFAULT_REALIZATION_CONSTRAINT_LIMITS,
) -> RealizationConstraintBuildResult:
    """Lift the existing value-free plan rule into the recursive authority."""

    value_budget = RelationBudget(limits)
    if invalid := validate_bounded_value(expected, (), 0, value_budget):
        return RealizationConstraintBuildResult(invalid.status, diagnostics=invalid.diagnostics)
    budget = RelationBudget(limits)
    root, failure = _upgrade_legacy_node(structure, expected, (), semantic_profile, budget)
    if failure is not None:
        return failure
    assert root is not None
    return RealizationConstraintBuildResult(
        RealizationRelationStatus.CONFORMANT,
        RealizationConstraintDocument(
            semantic_profile=semantic_profile,
            default_closure=RealizationClosure(
                posture="closed",
                universe="legacy-realization-structure/v1",
                profile=semantic_profile,
            ),
            root=root,
        ),
    )


def _compatibility_closure(additional: bool, semantic_profile: str) -> RealizationClosure:
    return RealizationClosure(
        posture="open" if additional else "closed",
        universe="legacy-realization-structure/v1",
        profile=semantic_profile,
    )


def _upgrade_legacy_node(
    structure: RealizationStructure,
    expected: object,
    path: tuple[str, ...],
    semantic_profile: str,
    budget: RelationBudget,
) -> tuple[RecursiveRealizationStructure | None, RealizationConstraintBuildResult | None]:
    current_pointer = pointer(path)
    if exhausted := budget.spend_node(len(path)):
        return None, build_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            current_pointer,
            f"Legacy structure conversion exceeded {exhausted}.",
        )
    if isinstance(structure, OpenRealizationValue):
        if structure.taxonomy_sentinel:
            return None, build_failure(
                RealizationRelationStatus.UNSUPPORTED,
                current_pointer,
                "Recursive delegation cannot preserve the legacy taxonomy-sentinel exclusion.",
            )
        return RealizationDelegatedValue(kind="delegated"), None
    if isinstance(structure, ExactRealizationValue):
        return normalize_literal_node(expected, path, path, budget, {}, {})
    if isinstance(structure, RealizationRecord):
        if not isinstance(expected, Mapping):
            return None, build_failure(
                RealizationRelationStatus.INVALID,
                current_pointer,
                "Legacy record conversion requires a record baseline.",
            )
        for key in structure.fields:
            if budget.spend_operation() is not None or len(key.encode("utf-8")) > budget.limits.max_scalar_bytes:
                return None, build_failure(
                    RealizationRelationStatus.LIMIT_EXCEEDED,
                    current_pointer,
                    "Legacy record metadata exceeded its configured work limits.",
                )
        if any(key.endswith(("_present", "_commitment")) for key in structure.fields):
            return None, build_failure(
                RealizationRelationStatus.UNSUPPORTED,
                current_pointer,
                "Recursive conversion does not reinterpret legacy suffixed field names.",
            )
        if not structure.additional and set(expected) != set(structure.fields):
            return None, build_failure(
                RealizationRelationStatus.UNSUPPORTED,
                current_pointer,
                "A closed legacy record with unbound baseline fields has no lossless recursive form.",
            )
        fields: dict[str, RecursiveRealizationStructure] = {}
        for key, child in structure.fields.items():
            if key not in expected:
                return None, build_failure(
                    RealizationRelationStatus.UNSUPPORTED,
                    pointer((*path, key)),
                    "A legacy record child absent from its baseline has no lossless recursive form.",
                )
            child_expected = expected[key]
            upgraded, failure = _upgrade_legacy_node(
                child,
                child_expected,
                (*path, key),
                semantic_profile,
                budget,
            )
            if failure is not None:
                return None, failure
            assert upgraded is not None
            fields[key] = upgraded
        return (
            RealizationRecordConstraint(
                kind="recursive-record",
                fields=fields,
                closure=_compatibility_closure(structure.additional, semantic_profile),
            ),
            None,
        )
    if not isinstance(expected, list):
        return None, build_failure(
            RealizationRelationStatus.INVALID,
            current_pointer,
            "Legacy collection conversion requires a list baseline.",
        )
    for field in structure.identity_fields:
        if budget.spend_operation() is not None or len(field.encode("utf-8")) > budget.limits.max_scalar_bytes:
            return None, build_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                current_pointer,
                "Legacy collection metadata exceeded its configured work limits.",
            )
    indexed, indexing_failure = _budgeted_indexed_collection(
        expected,
        structure.identity_fields,
        path,
        budget,
    )
    if indexing_failure is not None:
        return None, indexing_failure
    if indexed is None or set(indexed) != set(structure.members):
        return None, build_failure(
            RealizationRelationStatus.INVALID,
            current_pointer,
            "Legacy collection identities disagree with the baseline.",
        )
    members: list[RealizationCollectionMember] = []
    for digest, child in structure.members.items():
        item = indexed[digest]
        identity = actual_identity(item, structure.identity_fields)
        assert identity is not None
        if exhausted := budget.spend_identity():
            return None, build_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                current_pointer,
                f"Legacy collection conversion exceeded {exhausted}.",
            )
        upgraded, failure = _upgrade_legacy_node(
            child,
            item,
            (*path, f"@{digest}"),
            semantic_profile,
            budget,
        )
        if failure is not None:
            return None, failure
        assert upgraded is not None
        members.append(RealizationCollectionMember(identity=identity, constraint=upgraded))
    return (
        RealizationKeyedCollectionConstraint(
            kind="keyed-collection",
            collection_kind="legacy-projected-collection",
            identity_fields=structure.identity_fields,
            members=tuple(members),
            closure=_compatibility_closure(structure.additional, semantic_profile),
        ),
        None,
    )


def downgrade_recursive_realization_structure(
    document: RealizationConstraintDocument,
    expected: object,
    *,
    limits: RealizationConstraintLimits = DEFAULT_REALIZATION_CONSTRAINT_LIMITS,
) -> RealizationCompatibilityResult:
    """Project the recursive authority only when the legacy subset is lossless."""

    if document.scopes or document.definitions:
        diagnostic = recursive_diagnostic(
            "realization.unsupported",
            "",
            "Legacy structure cannot preserve recursive scopes or definitions.",
        )
        return RealizationCompatibilityResult(
            RealizationRelationStatus.UNSUPPORTED,
            diagnostics=(diagnostic,),
        )

    budget = RelationBudget(limits)
    if violation := admit_constraint_document(document, budget):
        return _compatibility_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            violation.pointer,
            violation.message,
        )
    value_budget = RelationBudget(limits)
    if invalid := validate_bounded_value(expected, (), 0, value_budget):
        return RealizationCompatibilityResult(invalid.status, diagnostics=invalid.diagnostics)
    try:
        structure, error = _downgrade_recursive_node(document, document.root, expected, (), budget)
    except CompatibilityLimit as exc:
        return _compatibility_failure(
            RealizationRelationStatus.LIMIT_EXCEEDED,
            exc.address,
            exc.message,
        )
    if error is not None:
        diagnostic = recursive_diagnostic("realization.unsupported", pointer(error[0]), error[1])
        return RealizationCompatibilityResult(
            RealizationRelationStatus.UNSUPPORTED,
            diagnostics=(diagnostic,),
        )
    return RealizationCompatibilityResult(RealizationRelationStatus.CONFORMANT, structure)


def _compatibility_failure(
    status: RealizationRelationStatus,
    address: str,
    message: str,
) -> RealizationCompatibilityResult:
    return RealizationCompatibilityResult(
        status,
        diagnostics=(recursive_diagnostic(f"realization.{status.value}", address, message),),
    )


def _downgrade_recursive_node(
    document: RealizationConstraintDocument,
    node: RecursiveRealizationStructure,
    expected: object,
    path: tuple[str, ...],
    budget: RelationBudget,
) -> tuple[RealizationStructure | None, tuple[tuple[str, ...], str] | None]:
    if exhausted := budget.spend_node(len(path)):
        raise CompatibilityLimit(pointer(path), f"Legacy projection exceeded {exhausted}.")
    if node.presence is not RealizationPresence.REQUIRED or node.origin is not RealizationOrigin.AUTHOR:
        return None, (path, "Legacy structure cannot preserve presence or non-author origin.")
    if isinstance(node, RealizationDelegatedValue):
        return OpenRealizationValue(kind="open"), None
    if isinstance(node, RealizationLiteral):
        return (
            (ExactRealizationValue(kind="exact"), None)
            if json_equal(node.value, expected)
            else (None, (path, "Recursive literal disagrees with the compatibility baseline."))
        )
    if isinstance(node, RealizationSequenceConstraint):
        exact = constraint_is_exact(document, node, expected, path)
        return (
            (ExactRealizationValue(kind="exact"), None)
            if exact
            else (None, (path, "Ordered sequence cannot be represented losslessly by the legacy baseline."))
        )
    if isinstance(node, RealizationRecordConstraint):
        return _downgrade_record(document, node, expected, path, budget)
    if isinstance(node, RealizationKeyedCollectionConstraint):
        return _downgrade_collection(document, node, expected, path, budget)
    return None, (path, "Recursive node kind has no lossless legacy structure representation.")


def _downgrade_record(
    document: RealizationConstraintDocument,
    node: RealizationRecordConstraint,
    expected: object,
    path: tuple[str, ...],
    budget: RelationBudget,
) -> tuple[RealizationStructure | None, tuple[tuple[str, ...], str] | None]:
    if not isinstance(expected, Mapping):
        return None, (path, "Recursive record requires a record compatibility baseline.")
    if any(key.endswith(("_present", "_commitment")) for key in node.fields):
        return None, (path, "Legacy structure cannot preserve suffixed recursive field names.")
    fields: dict[str, RealizationStructure] = {}
    for key, child in node.fields.items():
        downgraded, error = _downgrade_recursive_node(
            document,
            child,
            expected.get(key),
            (*path, key),
            budget,
        )
        if error is not None:
            return None, error
        assert downgraded is not None
        fields[key] = downgraded
    closure = closure_for(document, node.closure, path)
    assert closure is not None
    if closure.posture is RealizationClosurePosture.UNDEFINED:
        return None, (path, "Legacy record projection requires an effective closure.")
    if closure.posture is RealizationClosurePosture.CLOSED and set(expected) != set(node.fields):
        return None, (path, "Legacy closed-record baseline behavior would not be preserved.")
    return (
        RealizationRecord(
            kind="record",
            fields=fields,
            additional=closure.posture is RealizationClosurePosture.OPEN,
        ),
        None,
    )


def _downgrade_collection(
    document: RealizationConstraintDocument,
    node: RealizationKeyedCollectionConstraint,
    expected: object,
    path: tuple[str, ...],
    budget: RelationBudget,
) -> tuple[RealizationStructure | None, tuple[tuple[str, ...], str] | None]:
    if not isinstance(expected, list):
        return None, (path, "Recursive keyed collection requires a list compatibility baseline.")
    if node.aliases or node.min_items != 0 or node.max_items != 4096:
        return None, (path, "Legacy collection cannot preserve aliases or non-default cardinality.")
    indexed = indexed_collection_for_downgrade(expected, node.identity_fields, path, budget)
    if indexed is None:
        return None, (path, "Compatibility baseline has invalid collection identities.")
    members: dict[str, RealizationStructure] = {}
    for member in node.members:
        if exhausted := budget.spend_identity():
            raise CompatibilityLimit(pointer(path), f"Legacy projection exceeded {exhausted}.")
        digest = identity_key(member.identity)
        item = indexed.get(digest)
        if item is None:
            return None, (path, "Compatibility baseline omits a required collection identity.")
        downgraded, error = _downgrade_recursive_node(
            document,
            member.constraint,
            item,
            (*path, f"@{digest}"),
            budget,
        )
        if error is not None:
            return None, error
        assert downgraded is not None
        members[digest] = downgraded
    closure = closure_for(document, node.closure, path)
    assert closure is not None
    if closure.posture is RealizationClosurePosture.UNDEFINED:
        return None, (path, "Legacy collection projection requires an effective closure.")
    return (
        RealizationCollection(
            kind="collection",
            identity_fields=node.identity_fields,
            members=members,
            additional=closure.posture is RealizationClosurePosture.OPEN,
        ),
        None,
    )


def _budgeted_indexed_collection(
    value: list[object],
    fields: tuple[str, ...],
    path: tuple[str, ...],
    budget: RelationBudget,
) -> tuple[dict[str, object] | None, RealizationConstraintBuildResult | None]:
    members: dict[str, object] = {}
    for item in value:
        if exhausted := budget.spend_identity():
            return None, build_failure(
                RealizationRelationStatus.LIMIT_EXCEEDED,
                pointer(path),
                f"Legacy collection conversion exceeded {exhausted}.",
            )
        identity = realization_member_identity(item, fields)
        if identity is None or identity in members:
            return None, None
        members[identity] = item
    return members, None
