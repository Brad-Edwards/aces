"""Experiment manifest, evidence, and measurement reference contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from ..versions import BACKEND_MANIFEST_V2_SCHEMA_VERSION, PROCESSOR_MANIFEST_V2_SCHEMA_VERSION
from .experiment_references import ExperimentReferenceModel
from .schema_invariants import _add_aces_invariant


class ExperimentManifestReferenceModel(ExperimentReferenceModel):
    """Reference constrained to an apparatus or capability manifest."""

    ref_kind: Literal["manifest"]
    subject_ref: ExperimentReferenceModel | None = None

    @model_validator(mode="after")
    def _validate_manifest_reference_scope(self) -> ExperimentManifestReferenceModel:
        if self.ref_path is not None:
            raise ValueError("manifest references must not carry ref_path")
        if self.subject_ref is not None and (
            self.subject_ref.ref_digest is not None or self.subject_ref.ref_path is not None
        ):
            raise ValueError("manifest subject_ref must not carry ref_digest or ref_path")
        if self.ref_digest is not None:
            if self.subject_ref is None or self.subject_ref.ref_kind not in {"processor", "backend"}:
                raise ValueError(
                    "digest-bound manifest references must use processor/backend subject_ref values "
                    "validated against concrete manifest payloads"
                )
            expected_manifest_version = (
                PROCESSOR_MANIFEST_V2_SCHEMA_VERSION
                if self.subject_ref.ref_kind == "processor"
                else BACKEND_MANIFEST_V2_SCHEMA_VERSION
            )
            if self.ref_version != expected_manifest_version:
                raise ValueError(
                    "digest-bound processor/backend manifest references must use the supported manifest schema version"
                )
        if self.subject_ref is not None and self.subject_ref.ref_kind in {"processor", "backend"}:
            if self.ref_id != self.subject_ref.ref_id:
                raise ValueError("processor/backend manifest references ref_id must match subject_ref.ref_id")
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
                {"properties": {"ref_path": {"type": "null"}}},
                {
                    "if": {
                        "properties": {"ref_digest": {"type": "string"}},
                        "required": ["ref_digest"],
                    },
                    "then": {
                        "required": ["subject_ref"],
                        "properties": {
                            "subject_ref": {
                                "required": ["ref_kind"],
                                "properties": {"ref_kind": {"enum": ["processor", "backend"]}},
                            }
                        },
                    },
                },
                {
                    "if": {
                        "properties": {
                            "ref_digest": {"type": "string"},
                            "subject_ref": {
                                "properties": {"ref_kind": {"const": "processor"}},
                                "required": ["ref_kind"],
                            },
                        },
                        "required": ["ref_digest", "subject_ref"],
                    },
                    "then": {"properties": {"ref_version": {"const": PROCESSOR_MANIFEST_V2_SCHEMA_VERSION}}},
                },
                {
                    "if": {
                        "properties": {
                            "ref_digest": {"type": "string"},
                            "subject_ref": {
                                "properties": {"ref_kind": {"const": "backend"}},
                                "required": ["ref_kind"],
                            },
                        },
                        "required": ["ref_digest", "subject_ref"],
                    },
                    "then": {"properties": {"ref_version": {"const": BACKEND_MANIFEST_V2_SCHEMA_VERSION}}},
                },
                {
                    "if": {"properties": {"subject_ref": {"type": "object"}}, "required": ["subject_ref"]},
                    "then": {
                        "properties": {
                            "subject_ref": {
                                "properties": {
                                    "ref_digest": {"type": "null"},
                                    "ref_path": {"type": "null"},
                                }
                            }
                        }
                    },
                },
            ]
        )
        _add_aces_invariant(
            json_schema,
            "manifest-reference-digest-scope-valid",
            "Manifest digest qualifiers are limited to processor/backend manifest refs that can be checked "
            "against concrete manifest payload digests; manifest path qualifiers are not accepted in v1.",
            validator="aces_contracts.contracts.ExperimentManifestReferenceModel._validate_manifest_reference_scope",
            inputs=[
                {"contract_id": "experiment-task-v1", "instance_path": "#/$defs/ExperimentManifestReferenceModel"},
                {
                    "contract_id": "experiment-apparatus-context-v1",
                    "instance_path": "#/$defs/ExperimentManifestReferenceModel",
                },
                {"contract_id": "experiment-run-v1", "instance_path": "#/$defs/ExperimentManifestReferenceModel"},
            ],
        )
        return json_schema


class ExperimentProcessorReferenceModel(ExperimentReferenceModel):
    """Reference constrained to a processor identity."""

    ref_kind: Literal["processor"]

    @model_validator(mode="after")
    def _validate_identity_reference_scope(self) -> ExperimentProcessorReferenceModel:
        if "ref_digest" in self.model_fields_set or "ref_path" in self.model_fields_set:
            raise ValueError("processor identity references must not carry ref_digest or ref_path")
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


class ExperimentBackendReferenceModel(ExperimentReferenceModel):
    """Reference constrained to a backend identity."""

    ref_kind: Literal["backend"]

    @model_validator(mode="after")
    def _validate_identity_reference_scope(self) -> ExperimentBackendReferenceModel:
        if "ref_digest" in self.model_fields_set or "ref_path" in self.model_fields_set:
            raise ValueError("backend identity references must not carry ref_digest or ref_path")
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


class ExperimentEvidenceReferenceModel(ExperimentReferenceModel):
    """Reference constrained to evidence artifacts."""

    ref_kind: Literal["evidence"]


class ExperimentEvidenceSatisfactionReferenceModel(ExperimentEvidenceReferenceModel):
    """Evidence concept reference that an artifact claims to satisfy."""

    @model_validator(mode="after")
    def _validate_satisfaction_reference_scope(self) -> ExperimentEvidenceSatisfactionReferenceModel:
        if "ref_digest" in self.model_fields_set or "ref_path" in self.model_fields_set:
            raise ValueError("artifact satisfies_refs must not carry ref_digest or ref_path")
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


class ExperimentRunEvidenceArtifactReferenceModel(ExperimentEvidenceReferenceModel):
    """Run-internal reference to a concrete evidence artifact id."""

    @model_validator(mode="after")
    def _validate_run_evidence_artifact_reference_scope(self) -> ExperimentRunEvidenceArtifactReferenceModel:
        if any(field in self.model_fields_set for field in ("ref_version", "ref_digest", "ref_path")):
            raise ValueError("run result evidence_refs are artifact-id references and must not carry qualifiers")
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
            properties.pop("ref_version", None)
            properties.pop("ref_digest", None)
            properties.pop("ref_path", None)
        return json_schema


class ExperimentCaptureSpecReferenceModel(ExperimentReferenceModel):
    """Reference constrained to a declarative capture specification."""

    ref_kind: Literal["capture-spec"]

    @model_validator(mode="after")
    def _validate_capture_spec_reference_scope(self) -> ExperimentCaptureSpecReferenceModel:
        if "ref_digest" in self.model_fields_set or "ref_path" in self.model_fields_set:
            raise ValueError("capture-spec references must not carry ref_digest or ref_path")
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


class ExperimentEvidenceRecordReferenceModel(ExperimentReferenceModel):
    """Reference constrained to a raw captured evidence record."""

    ref_kind: Literal["evidence-record"]

    @model_validator(mode="after")
    def _validate_evidence_record_reference_scope(self) -> ExperimentEvidenceRecordReferenceModel:
        if "ref_digest" in self.model_fields_set or "ref_path" in self.model_fields_set:
            raise ValueError("evidence-record references must not carry ref_digest or ref_path")
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
