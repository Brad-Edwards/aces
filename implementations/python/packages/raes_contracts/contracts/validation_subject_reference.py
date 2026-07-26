"""ASR-515 validation-basis disclosure subject/producer reference contracts.

Split out of ``validation_disclosure`` (issue #259) to keep each module under
the repo's 500-line source-file cap. Owns the two reference shapes a
validation-basis disclosure carries: the concrete subject the disclosure is
about (``ValidationSubjectReferenceModel``) and the processor/backend/
participant implementation that ran a gate (``ValidationProducerReferenceModel``).
"""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from .experiment_references import ExperimentReferenceModel, PrunedReferenceFieldsMixin

# Every ValidationSubjectReferenceModel.ref_kind value except scenario-snapshot,
# which is the only one that binds by digest.
_SUBJECT_REF_KINDS_WITHOUT_DIGEST: tuple[str, ...] = (
    "scenario",
    "task",
    "run",
    "study",
    "backend",
    "participant-implementation",
    "result",
)

# task/run/study are the versioned carrier kinds (ExperimentTaskModel,
# ExperimentRunModel, ExperimentStudyModel each declare required NonEmptyString
# {label}_id/{label}_version). A disclosure referencing one of these MUST bind
# to a concrete version, or a producer could omit ref_version and replay a
# validation-strength claim established for one revision across a later
# revision that reuses the same id (the carrier identity invariant these
# schemas promise). scenario stays id-only (ExperimentScenarioReferenceModel
# precedent) and scenario-snapshot binds by digest, which is a strictly
# stronger binding than a version; backend/participant-implementation/result
# are not necessarily versioned subjects, so their optional-version semantics
# are unchanged.
_SUBJECT_REF_KINDS_REQUIRING_VERSION: tuple[str, ...] = ("task", "run", "study")


class ValidationSubjectReferenceModel(ExperimentReferenceModel):
    """Reference to a validation-basis disclosure's concrete subject.

    Constrained to the eight ref_kind values the ASR-511 catalog's subject
    kinds map onto. A ``scenario-snapshot`` reference must bind by digest
    (``ref_digest``, sourced from ``canonical_instantiated_sdl_digest()``)
    rather than modifying the snapshot contract. ``task``/``run``/``study``
    reference the versioned experiment-core carriers and must bind by
    ``ref_version`` -- a disclosure with the right id but no version could
    otherwise be replayed against a later revision that reuses the same id,
    defeating the carrier identity invariant those contracts promise.
    ``scenario`` stays an id-only reference (matching the identity-only
    ``ExperimentScenarioReferenceModel`` precedent), and ``backend``/
    ``participant-implementation``/``result`` keep optional-version semantics
    because those subjects are not necessarily versioned.
    """

    ref_kind: Literal[
        "scenario",
        "scenario-snapshot",
        "task",
        "run",
        "study",
        "backend",
        "participant-implementation",
        "result",
    ]

    @model_validator(mode="after")
    def _validate_validation_subject_reference_scope(self) -> ValidationSubjectReferenceModel:
        if self.ref_kind == "scenario-snapshot":
            if self.ref_digest is None:
                raise ValueError("scenario-snapshot validation subject references must include ref_digest")
            if self.ref_path is not None:
                raise ValueError("scenario-snapshot validation subject references must not carry ref_path")
        elif self.ref_digest is not None or self.ref_path is not None:
            raise ValueError(f"{self.ref_kind} validation subject references must not carry ref_digest or ref_path")
        if self.ref_kind in _SUBJECT_REF_KINDS_REQUIRING_VERSION and self.ref_version is None:
            raise ValueError(
                f"{self.ref_kind} validation subject references must include ref_version; omitting it would let a "
                "disclosure for one revision be replayed against a later revision that reuses the same ref_id"
            )
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.setdefault("allOf", []).extend(
            [
                {
                    "if": {"properties": {"ref_kind": {"const": "scenario-snapshot"}}, "required": ["ref_kind"]},
                    "then": {
                        "required": ["ref_digest"],
                        "properties": {"ref_digest": {"type": "string"}, "ref_path": {"type": "null"}},
                    },
                },
                {
                    "if": {
                        "properties": {"ref_kind": {"enum": list(_SUBJECT_REF_KINDS_WITHOUT_DIGEST)}},
                        "required": ["ref_kind"],
                    },
                    "then": {"properties": {"ref_digest": {"type": "null"}, "ref_path": {"type": "null"}}},
                },
                {
                    "if": {
                        "properties": {"ref_kind": {"enum": list(_SUBJECT_REF_KINDS_REQUIRING_VERSION)}},
                        "required": ["ref_kind"],
                    },
                    "then": {
                        "required": ["ref_version"],
                        "properties": {"ref_version": {"type": "string", "minLength": 1}},
                    },
                },
            ]
        )
        return json_schema


class ValidationProducerReferenceModel(PrunedReferenceFieldsMixin, ExperimentReferenceModel):
    """Reference constrained to the processor/backend/participant implementation that ran a gate."""

    ref_kind: Literal["processor", "backend", "participant-implementation"]
    _PRUNED_REF_FIELDS: ClassVar[tuple[str, ...]] = ("ref_digest", "ref_path")

    @model_validator(mode="after")
    def _validate_producer_reference_scope(self) -> ValidationProducerReferenceModel:
        if "ref_digest" in self.model_fields_set or "ref_path" in self.model_fields_set:
            raise ValueError("validation producer references must not carry ref_digest or ref_path")
        return self


__all__ = [
    "ValidationProducerReferenceModel",
    "ValidationSubjectReferenceModel",
]
