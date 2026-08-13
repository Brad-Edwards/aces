"""Schema-bundle fragment for artifact transformation and synthesis contracts."""

from __future__ import annotations

from typing import Any

from .artifact_transformations import ArtifactTransformationReportModel
from .candidate_synthesis import (
    CandidateSynthesisInputModel,
    CandidateSynthesisProfileDefinitionModel,
    CandidateSynthesisRecordModel,
)


def transformation_schema_bundle() -> dict[str, dict[str, Any]]:
    """Return the transformation-domain portion of the published bundle."""

    return {
        "artifact-transformation-report-v1": ArtifactTransformationReportModel.model_json_schema(),
        "sdl-candidate-synthesis-input-v1": CandidateSynthesisInputModel.model_json_schema(),
        "sdl-candidate-synthesis-profile-v1": CandidateSynthesisProfileDefinitionModel.model_json_schema(),
        "sdl-candidate-synthesis-record-v1": CandidateSynthesisRecordModel.model_json_schema(),
    }


__all__ = ["transformation_schema_bundle"]
