"""Issue #259 codex review cycle 2: reference models that delete inherited
``ref_digest``/``ref_path``/``ref_version`` properties from their generated
JSON Schema must also drop those keys from ``model_dump()`` -- otherwise a
producer serializes a payload its own published schema (``additionalProperties:
false``) forbids. ``PrunedReferenceFieldsMixin`` (in
``raes_contracts.contracts.experiment_references``) is the single shared
mechanism that derives both the schema pruning and the dump pruning from one
``_PRUNED_REF_FIELDS`` declaration per model, so this test module is the
durable structural gate for the whole category: parametrized over every
model that uses the mixin today, so a future model that forgets it is caught
here rather than downstream.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ValidationError
from raes_contracts.contracts import (
    ExperimentApparatusCompatibilityReferenceModel,
    ExperimentBackendReferenceModel,
    ExperimentCaptureSpecReferenceModel,
    ExperimentDerivedMeasureReferenceModel,
    ExperimentEvidenceRecordReferenceModel,
    ExperimentMeasurementChannelReferenceModel,
    ExperimentProcessorReferenceModel,
    ExperimentTaskReferenceModel,
)
from raes_contracts.contracts.experiment_manifest_references import (
    ExperimentEvidenceSatisfactionReferenceModel,
    ExperimentRunEvidenceArtifactReferenceModel,
)
from raes_contracts.contracts.validation_disclosure import (
    ValidationBasisDisclosureDocumentModel,
    ValidationProducerReferenceModel,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PUBLISHED_DISCLOSURE_SCHEMA_PATH = REPO_ROOT / "contracts/schemas/profiles/validation-basis-disclosure-v1.json"

# (model class, minimal valid kwargs, pruned field names, error match for each
# pruned field when explicitly supplied). Every model below narrows ref_kind
# to a value that can never carry the pruned fields; its own model_validator
# rejects them if explicitly set, and its own __get_pydantic_json_schema__
# (via the mixin) deletes them from the generated schema's properties.
_PRUNED_REFERENCE_MODEL_CASES: list[tuple[type[BaseModel], dict[str, Any], tuple[str, ...], str]] = [
    (
        ValidationProducerReferenceModel,
        {"ref_kind": "processor", "ref_id": "proc-1"},
        ("ref_digest", "ref_path"),
        "validation producer references must not carry ref_digest or ref_path",
    ),
    (
        ExperimentTaskReferenceModel,
        {"ref_kind": "task", "ref_id": "task-1"},
        ("ref_digest", "ref_path"),
        "task references must not carry ref_digest or ref_path",
    ),
    (
        ExperimentDerivedMeasureReferenceModel,
        {"ref_kind": "derived-measure", "ref_id": "measure-1"},
        ("ref_digest", "ref_path"),
        "derived-measure references must not carry ref_digest or ref_path",
    ),
    (
        ExperimentMeasurementChannelReferenceModel,
        {"ref_kind": "measurement-channel", "ref_id": "channel-1"},
        ("ref_digest", "ref_path"),
        "measurement-channel references must not carry ref_digest or ref_path",
    ),
    (
        ExperimentApparatusCompatibilityReferenceModel,
        {"ref_kind": "profile", "ref_id": "compat-1"},
        ("ref_digest", "ref_path"),
        "apparatus compatibility references must not carry ref_digest or ref_path",
    ),
    (
        ExperimentProcessorReferenceModel,
        {"ref_kind": "processor", "ref_id": "proc-1"},
        ("ref_digest", "ref_path"),
        "processor identity references must not carry ref_digest or ref_path",
    ),
    (
        ExperimentBackendReferenceModel,
        {"ref_kind": "backend", "ref_id": "backend-1"},
        ("ref_digest", "ref_path"),
        "backend identity references must not carry ref_digest or ref_path",
    ),
    (
        ExperimentEvidenceSatisfactionReferenceModel,
        {"ref_kind": "evidence", "ref_id": "evidence-1"},
        ("ref_digest", "ref_path"),
        "artifact satisfies_refs must not carry ref_digest or ref_path",
    ),
    (
        ExperimentRunEvidenceArtifactReferenceModel,
        {"ref_kind": "evidence", "ref_id": "artifact-1"},
        ("ref_version", "ref_digest", "ref_path"),
        "run result evidence_refs are artifact-id references and must not carry qualifiers",
    ),
    (
        ExperimentCaptureSpecReferenceModel,
        {"ref_kind": "capture-spec", "ref_id": "capture-1"},
        ("ref_digest", "ref_path"),
        "capture-spec references must not carry ref_digest or ref_path",
    ),
    (
        ExperimentEvidenceRecordReferenceModel,
        {"ref_kind": "evidence-record", "ref_id": "record-1"},
        ("ref_digest", "ref_path"),
        "evidence-record references must not carry ref_digest or ref_path",
    ),
]

_CASE_IDS = [case[0].__name__ for case in _PRUNED_REFERENCE_MODEL_CASES]


def _pruned_field_probe_value(field_name: str) -> str:
    if field_name == "ref_digest":
        return "sha256:" + "a" * 64
    return "probe-value"


@pytest.mark.parametrize(
    ("model_cls", "kwargs", "pruned_fields", "error_match"), _PRUNED_REFERENCE_MODEL_CASES, ids=_CASE_IDS
)
def test_pruned_reference_model_dump_validates_against_its_own_schema(
    model_cls: type[BaseModel],
    kwargs: dict[str, Any],
    pruned_fields: tuple[str, ...],
    error_match: str,
) -> None:
    # The exact defect from issue #259 codex review cycle 2: model_dump() must
    # not emit keys the model's own generated schema (additionalProperties:
    # false, properties pruned) forbids.
    del error_match
    instance = model_cls.model_validate(kwargs)
    dumped = instance.model_dump(mode="json")
    for field_name in pruned_fields:
        assert field_name not in dumped, f"{model_cls.__name__}.model_dump() must not emit pruned field {field_name!r}"
    Draft202012Validator(model_cls.model_json_schema()).validate(dumped)


@pytest.mark.parametrize(
    ("model_cls", "kwargs", "pruned_fields", "error_match"), _PRUNED_REFERENCE_MODEL_CASES, ids=_CASE_IDS
)
def test_pruned_reference_model_still_rejects_explicit_pruned_fields(
    model_cls: type[BaseModel],
    kwargs: dict[str, Any],
    pruned_fields: tuple[str, ...],
    error_match: str,
) -> None:
    # The schema/serializer pruning must not weaken the existing
    # model_fields_set-based rejection of explicitly supplied pruned fields.
    for field_name in pruned_fields:
        bad_kwargs = dict(kwargs)
        bad_kwargs[field_name] = _pruned_field_probe_value(field_name)
        with pytest.raises(ValidationError, match=error_match):
            model_cls.model_validate(bad_kwargs)


def test_validation_producer_reference_dump_validates_against_published_disclosure_schema() -> None:
    # The specific case codex named: build a full published
    # ValidationBasisDisclosureDocumentModel carrying a producer_refs entry,
    # dump it, and validate the dump against the PUBLISHED schema file (not
    # just the freshly generated in-process schema), proving the fix holds
    # for the artifact that actually ships.
    disclosure_payload: dict[str, Any] = {
        "profile_id": "aces-structural-validation",
        "profile_version": "v1",
        "subject_kind": "scenario",
        "subject_ref": {"ref_kind": "scenario", "ref_id": "scenario-1"},
        "achieved_strength": "structural",
        "gate_results": [
            {"gate_kind": "syntax_validation", "outcome": "passed"},
            {"gate_kind": "schema_validation", "outcome": "passed"},
            {"gate_kind": "vocabulary_validation", "outcome": "passed"},
        ],
        "producer_refs": [
            {"ref_kind": "processor", "ref_id": "proc-1"},
            {"ref_kind": "participant-implementation", "ref_id": "participant-1", "ref_version": "v1"},
        ],
        "recorded_at": "2026-07-24T00:00:00Z",
    }
    document = ValidationBasisDisclosureDocumentModel.model_validate(
        {"schema_version": "validation-basis-disclosure/v1", "disclosure": disclosure_payload}
    )

    dumped = document.model_dump(mode="json")
    for producer_ref in dumped["disclosure"]["producer_refs"]:
        assert "ref_digest" not in producer_ref
        assert "ref_path" not in producer_ref

    published_schema = json.loads(PUBLISHED_DISCLOSURE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(published_schema).validate(dumped)
