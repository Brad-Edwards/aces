"""Experiment reference base/scenario/task contracts and parameter primitives."""

from __future__ import annotations

from typing import Literal

from pydantic import GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from .base import ContractModel, NonEmptyString, PrefixedDigestString


class ExperimentReferenceModel(ContractModel):
    """Typed reference to an experiment-core or adjacent ACES artifact."""

    ref_kind: Literal[
        "processor",
        "backend",
        "participant-implementation",
        "scenario",
        "scenario-snapshot",
        "task",
        "authoring-input",
        "protocol",
        "apparatus-context",
        "run",
        "metric-definition",
        "result",
        "study",
        "manifest",
        "profile",
        "capability",
        "capture-spec",
        "evidence",
        "evidence-record",
        "derived-measure",
        "measurement-channel",
        "analysis-artifact",
        "other",
    ]
    ref_id: NonEmptyString
    ref_version: NonEmptyString | None = None
    ref_digest: PrefixedDigestString | None = None
    ref_path: NonEmptyString | None = None


class ExperimentScenarioReferenceModel(ExperimentReferenceModel):
    """Reference constrained to authored scenario material."""

    ref_kind: Literal["scenario", "scenario-snapshot"]

    @model_validator(mode="after")
    def _validate_generic_scenario_reference_scope(self) -> ExperimentScenarioReferenceModel:
        if self.ref_kind == "scenario" and (
            self.ref_version is not None or self.ref_digest is not None or self.ref_path is not None
        ):
            raise ValueError(
                "generic scenario references are id-only; use scenario-snapshot for version, digest, or path binding"
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
        json_schema.setdefault("allOf", []).append(
            {
                "if": {
                    "properties": {"ref_kind": {"const": "scenario"}},
                    "required": ["ref_kind"],
                },
                "then": {
                    "properties": {
                        "ref_version": {"type": "null"},
                        "ref_digest": {"type": "null"},
                        "ref_path": {"type": "null"},
                    }
                },
            }
        )
        return json_schema


class ExperimentTaskReferenceModel(ExperimentReferenceModel):
    """Reference constrained to an experiment task."""

    ref_kind: Literal["task"]

    @model_validator(mode="after")
    def _validate_task_reference_scope(self) -> ExperimentTaskReferenceModel:
        if "ref_digest" in self.model_fields_set or "ref_path" in self.model_fields_set:
            raise ValueError("task references must not carry ref_digest or ref_path")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        properties = json_schema.get("properties")
        if isinstance(properties, dict):
            properties.pop("ref_digest", None)
            properties.pop("ref_path", None)
        return json_schema


class ExperimentScenarioSnapshotReferenceModel(ExperimentReferenceModel):
    """Reference constrained to a sealed scenario snapshot."""

    ref_kind: Literal["scenario-snapshot"]


class AssociatedArtifactParentReferenceModel(ExperimentReferenceModel):
    """Reference constrained to a supported associated-artifact parent."""

    ref_kind: Literal[
        "scenario",
        "scenario-snapshot",
        "task",
        "authoring-input",
        "apparatus-context",
        "run",
        "study",
    ]

    @model_validator(mode="after")
    def _validate_associated_artifact_parent(self) -> AssociatedArtifactParentReferenceModel:
        if self.ref_kind == "scenario":
            if self.ref_version is not None or self.ref_digest is not None or self.ref_path is not None:
                raise ValueError("generic scenario parents are id-only; use scenario-snapshot for snapshot binding")
        elif self.ref_kind != "scenario-snapshot" and (self.ref_digest is not None or self.ref_path is not None):
            raise ValueError(
                "experiment associated-artifact parents must not carry ref_digest or ref_path without a "
                "normative parent canonicalization profile"
            )
        return self


class ExperimentParameterModel(ContractModel):
    """Redaction-aware parameter captured for a task, run, or apparatus context."""

    name: NonEmptyString
    value: str | int | float | bool | None
    value_kind: Literal["configuration", "protocol", "apparatus", "analysis", "other"]
    redaction: Literal["none", "redacted", "withheld"] = "none"

    @model_validator(mode="after")
    def _validate_redacted_parameter_value(self) -> ExperimentParameterModel:
        if self.redaction != "none" and self.value is not None:
            raise ValueError("redacted or withheld experiment parameters must not include concrete values")
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
                "if": {
                    "properties": {"redaction": {"enum": ["redacted", "withheld"]}},
                    "required": ["redaction"],
                },
                "then": {"properties": {"value": {"type": "null"}}},
            }
        )
        return json_schema


class ExperimentConditionAssignmentParameterModel(ExperimentParameterModel):
    """Auditable parameter value that can ground a study condition assignment."""

    value_kind: Literal["configuration", "protocol", "apparatus", "analysis"]
    redaction: Literal["none"] = "none"

    @model_validator(mode="after")
    def _validate_auditable_condition_parameter(self) -> ExperimentConditionAssignmentParameterModel:
        if self.redaction != "none":
            raise ValueError("condition assignment parameters must not be redacted or withheld")
        return self
