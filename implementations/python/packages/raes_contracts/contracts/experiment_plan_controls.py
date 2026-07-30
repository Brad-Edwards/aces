"""Reusable execution-control declarations for experiment run plans."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ContractModel, NonEmptyString, PositiveInteger
from .experiment_references import ExperimentParameterModel


class ExperimentEpisodeControlModel(ContractModel):
    """Declarative episode execution controls for a planned experiment.

    Captures the pre-run execution-control facts — turn order, logical step
    count, and episode termination — that ADR-069 requires for CAGE-2
    execution-control equivalence but that the archival experiment-core
    contracts only record after a run has executed.
    """

    turn_order: Literal["sequential", "simultaneous", "round-robin", "scenario-defined", "other"]
    termination_rule: NonEmptyString
    max_steps: PositiveInteger | None = None
    termination_condition_refs: list[NonEmptyString] = Field(
        default_factory=list, json_schema_extra={"uniqueItems": True}
    )
    description: NonEmptyString | None = None


class ExperimentRedVariantSelectionModel(ContractModel):
    """Selection of one red-agent variant bound into a planned experiment."""

    variant_id: NonEmptyString
    agent_ref: NonEmptyString
    parameters: list[ExperimentParameterModel] = Field(default_factory=list)
    description: NonEmptyString | None = None


__all__ = ["ExperimentEpisodeControlModel", "ExperimentRedVariantSelectionModel"]
