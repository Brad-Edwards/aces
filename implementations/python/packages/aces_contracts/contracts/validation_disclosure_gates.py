"""ASR-515 validation-basis disclosure gate-result/limitation contracts.

Split out of ``validation_disclosure`` (issue #259) to keep each module under
the repo's 500-line source-file cap. Owns the ADR-072 strength-ordering gate
vocabulary and the two row shapes a disclosure carries: the executed gate
outcome (``ValidationGateResultModel``) and the profile-declared limitation
(``ValidationLimitationModel``).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from .base import ContractModel, NonEmptyString
from .experiment_manifest_references import ExperimentEvidenceRecordReferenceModel

# Diagnostic code references are bounded identifiers, matching
# ``aces_contracts.diagnostics.DiagnosticModel.code`` exactly, so a disclosure
# can point at a governed diagnostic without inlining its message or payload.
DiagnosticCodeRef = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$", max_length=128)]

# ADR-072 strength ordering, applied to the ACTUAL gate rows a disclosure
# carries. Cumulative by rank: structural < semantic < behavioral, and
# evidence_backed/falsification_backed build on the semantic floor (matching
# the catalog's own required_gate_kinds for those two profiles). Structural
# acceptance never implies semantic; semantic never implies behavioral.
_STRUCTURAL_STRENGTH_GATES: tuple[str, ...] = ("syntax_validation", "schema_validation", "vocabulary_validation")
_SEMANTIC_STRENGTH_GATES: tuple[str, ...] = (
    *_STRUCTURAL_STRENGTH_GATES,
    "semantic_invariant_validation",
    "reference_resolution",
)
_BEHAVIORAL_STRENGTH_GATES: tuple[str, ...] = (*_SEMANTIC_STRENGTH_GATES, "behavioral_execution")
_EVIDENCE_BACKED_STRENGTH_GATES: tuple[str, ...] = (
    *_SEMANTIC_STRENGTH_GATES,
    "evidence_preservation",
    "provenance_validation",
    "limitation_disclosure",
)
_FALSIFICATION_BACKED_STRENGTH_GATES: tuple[str, ...] = (
    *_EVIDENCE_BACKED_STRENGTH_GATES,
    "falsification_protocol",
    "evidence_status",
)
_STRENGTH_REQUIRED_GATES: dict[str, tuple[str, ...]] = {
    "structural": _STRUCTURAL_STRENGTH_GATES,
    "semantic": _SEMANTIC_STRENGTH_GATES,
    "behavioral": _BEHAVIORAL_STRENGTH_GATES,
    "evidence_backed": _EVIDENCE_BACKED_STRENGTH_GATES,
    "falsification_backed": _FALSIFICATION_BACKED_STRENGTH_GATES,
}
_STRENGTH_RANK: dict[str, int] = {
    "structural": 1,
    "semantic": 2,
    "behavioral": 3,
    "evidence_backed": 4,
    "falsification_backed": 5,
}
_EVIDENCE_REF_REQUIRED_STRENGTHS = frozenset({"evidence_backed", "falsification_backed"})


class ValidationGateResultModel(ContractModel):
    """One executed gate's outcome, contributing to a validation-basis disclosure.

    Gate rows are declarative results, never callables, module names, shell
    commands, or remote URLs to execute (the profile's owning validator,
    parser, or conformance runner is the authority for whether the gate ran).
    """

    gate_kind: NonEmptyString
    outcome: Literal[
        "passed",
        "failed",
        "partial",
        "not_run",
        "unknown",
        "unsupported",
        "withheld",
        "not_applicable",
    ]
    detail: NonEmptyString | None = None
    diagnostic_refs: list[DiagnosticCodeRef] = Field(default_factory=list)
    evidence_refs: list[ExperimentEvidenceRecordReferenceModel] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_gate_result_not_applicable_detail(self) -> ValidationGateResultModel:
        if self.outcome == "not_applicable" and self.detail is None:
            raise ValueError("not_applicable gate results must include detail; it is never a silent pass")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.setdefault("allOf", []).append(
            {
                "if": {"properties": {"outcome": {"const": "not_applicable"}}, "required": ["outcome"]},
                "then": {"required": ["detail"], "properties": {"detail": {"type": "string", "minLength": 1}}},
            }
        )
        return json_schema


class ValidationLimitationModel(ContractModel):
    """A bounded, profile-declared limitation on a validation-basis disclosure."""

    limitation_category: NonEmptyString
    detail: NonEmptyString


__all__ = [
    "DiagnosticCodeRef",
    "ValidationGateResultModel",
    "ValidationLimitationModel",
]
