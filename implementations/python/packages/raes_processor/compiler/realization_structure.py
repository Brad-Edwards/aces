"""Lower mixed authored constraints without copying values into authority."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel
from raes.explicitness import ExplicitnessClass, ExplicitnessRecord
from raes.scenario import InstantiatedScenario
from raes_contracts.realization_structure import (
    ExactRealizationValue,
    OpenRealizationValue,
    RealizationCollection,
    RealizationRecord,
    RealizationStructure,
    realization_member_identity,
)

from ..semantics.realization_concerns import RegisteredRealizationConcern
from .realization_authority_posture import designated_registered_posture
from .realization_concern_explicitness import semantic_explicitness_leaves


@dataclass
class _StructureCompiler:
    scenario: InstantiatedScenario
    registered: RegisteredRealizationConcern
    records: Mapping[str, ExplicitnessRecord]

    def is_open(self, pointer: str) -> bool:
        return (
            designated_registered_posture(
                self.scenario,
                field_pointer=pointer,
                declaration_name=self.registered.declaration_name,
            ).explicitness
            is ExplicitnessClass.OPEN
        )

    def build(self, value: object, path: str, pointer: str, *, depth: int = 0) -> RealizationStructure:
        if depth > 64:
            raise ValueError("realization structure exceeds the supported depth")
        record = self.records.get(path)
        if isinstance(value, dict):
            fields = {}
            for key, child in value.items():
                source_key = key.removesuffix("_present").removesuffix("_commitment")
                child_path = f"{path}.{source_key}"
                if child_path not in self.records:
                    child_open = self.is_open(f"{pointer}/{_escape(source_key)}")
                    if self.is_open(pointer) != child_open:
                        fields[key] = (
                            OpenRealizationValue(kind="open") if child_open else ExactRealizationValue(kind="exact")
                        )
                    continue
                fields[key] = self.build(child, child_path, f"{pointer}/{_escape(source_key)}", depth=depth + 1)
            return RealizationRecord(kind="record", fields=fields, additional=self.is_open(pointer))
        if isinstance(value, list):
            # Root keyed collections are handled before recursion. A nested
            # collection whose complete value is exact retains its projector's
            # ordering/comparison semantics. Unsupported mixed nesting rejects.
            if record is None or record.classification is ExplicitnessClass.EXACT:
                return ExactRealizationValue(kind="exact")
            raise ValueError("mixed nested collection has no declared identity policy")
        if record is not None and record.classification is ExplicitnessClass.CONSTRAINED:
            raise ValueError("mixed scalar bound has no publication-safe domain")
        if record is not None and record.classification is ExplicitnessClass.OPEN:
            return OpenRealizationValue(kind="open", taxonomy_sentinel=True)
        return ExactRealizationValue(kind="exact")


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def compile_realization_structure(
    scenario: InstantiatedScenario,
    registered: RegisteredRealizationConcern,
    records: Mapping[str, ExplicitnessRecord],
    *,
    authored_value: object,
    field_pointer: str,
) -> tuple[RealizationStructure | None, bool, bool]:
    """Return structural authority, unsupported-demand flag and openness."""

    compiler = _StructureCompiler(scenario, registered, records)
    root_open = compiler.is_open(field_pointer)
    descriptor = registered.descriptor
    identity_fields = descriptor.collection_identity_fields
    record = records.get(registered.field_path)
    nested_open = any(
        designation.field_pointer.startswith(f"{field_pointer}/") and compiler.is_open(designation.field_pointer)
        for designation in scenario.instantiation_provenance.realization_designations
    )
    if record is not None and record.classification is ExplicitnessClass.EXACT and not root_open and not nested_open:
        return None, False, False
    if not identity_fields:
        leaves = semantic_explicitness_leaves(
            records, field_path=registered.field_path, excluded_fields=descriptor.explicitness_excluded_fields
        )
        mixed_open = any(r.classification is ExplicitnessClass.OPEN for r in leaves)
        if mixed_open and not isinstance(authored_value, (list, dict, BaseModel)):
            return OpenRealizationValue(kind="open", taxonomy_sentinel=True), False, root_open
        return None, mixed_open, root_open
    source = list(authored_value) if isinstance(authored_value, list) else []
    if not source:
        return None, False, root_open
    try:
        projection = descriptor.project(authored_value)
        if not isinstance(projection, list):
            raise ValueError("keyed concern must project a collection")
        indices = {}
        for index, item in enumerate(source):
            raw = item.model_dump(mode="json") if isinstance(item, BaseModel) else item
            if not isinstance(raw, dict):
                raise ValueError("keyed concern must contain records")
            identity = tuple(raw[key] for key in identity_fields)
            if identity in indices:
                raise ValueError("duplicate authored identity")
            indices[identity] = index
        members = {}
        for item in projection:
            identity = tuple(item[key] for key in identity_fields)
            index = indices[identity]
            digest = realization_member_identity(item, identity_fields)
            if digest is None:
                raise ValueError("collection identity is not a concrete scalar tuple")
            members[digest] = compiler.build(item, f"{registered.field_path}[{index}]", f"{field_pointer}/{index}")
        return (
            RealizationCollection(
                kind="collection", members=members, identity_fields=identity_fields, additional=root_open
            ),
            False,
            root_open or nested_open,
        )
    except (TypeError, ValueError, KeyError):
        return None, True, root_open
