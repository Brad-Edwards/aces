"""Safe JSON ingress for SDL candidate-synthesis inputs."""

from __future__ import annotations

from .contracts.candidate_synthesis import CandidateSynthesisInputModel
from .json_ingress import parse_bounded_json_object


def parse_candidate_synthesis_input(
    source: str | bytes | bytearray,
    *,
    max_bytes: int = 1_048_576,
) -> CandidateSynthesisInputModel:
    """Parse one bounded, duplicate-rejecting candidate-synthesis input."""

    return CandidateSynthesisInputModel.model_validate(parse_bounded_json_object(source, max_bytes=max_bytes))


__all__ = ["parse_candidate_synthesis_input"]
