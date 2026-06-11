"""API-406/407/408/411 participant backend-facing contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aces_contracts.contracts import (
    ParticipantContextViewModel,
    ParticipantHistoryViewModel,
    ParticipantLifecycleEventModel,
    ParticipantObservationEnvelopeModel,
    ParticipantOutcomeReportModel,
    ParticipantSharedStateRecordModel,
    ParticipantStatusViewModel,
    schema_bundle,
)
from jsonschema import Draft202012Validator
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_ROOT = REPO_ROOT / "contracts" / "fixtures"

PARTICIPANT_RUNTIME_FIXTURE_MODELS = {
    "participant-lifecycle-event-v1": ParticipantLifecycleEventModel,
    "participant-observation-envelope-v1": ParticipantObservationEnvelopeModel,
    "participant-shared-state-record-v1": ParticipantSharedStateRecordModel,
    "participant-outcome-report-v1": ParticipantOutcomeReportModel,
}
CONTROL_PLANE_VIEW_FIXTURE_MODELS = {
    "participant-status-view-v1": ParticipantStatusViewModel,
    "participant-history-view-v1": ParticipantHistoryViewModel,
    "participant-context-view-v1": ParticipantContextViewModel,
}
FIXTURE_ROOTS_BY_CONTRACT = {
    **{contract_id: FIXTURES_ROOT / "participant-runtime" for contract_id in PARTICIPANT_RUNTIME_FIXTURE_MODELS},
    **{contract_id: FIXTURES_ROOT / "control-plane" for contract_id in CONTROL_PLANE_VIEW_FIXTURE_MODELS},
}
ALL_FIXTURE_MODELS = {**PARTICIPANT_RUNTIME_FIXTURE_MODELS, **CONTROL_PLANE_VIEW_FIXTURE_MODELS}

_ORDERING_BASIS_TERMS = [
    "total_order",
    "partial_order",
    "simultaneous",
    "serialized_backend_order",
    "simulation_tick",
    "control_plane_order",
    "logical_clock",
    "vector_clock",
    "wall_clock_only",
    "unknown",
    "unsupported",
]


def _valid_fixture(contract_id: str) -> dict:
    fixture_dir = FIXTURE_ROOTS_BY_CONTRACT[contract_id] / contract_id / "valid"
    path = sorted(fixture_dir.glob("*.json"))[0]
    return json.loads(path.read_text(encoding="utf-8"))


def test_participant_backend_contracts_are_published_closed_world():
    generated = schema_bundle()
    for contract_id in ALL_FIXTURE_MODELS:
        assert contract_id in generated
        schema = generated[contract_id]
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == f"https://aces.dev/schemas/{contract_id}.json"
        assert schema["additionalProperties"] is False


def test_participant_runtime_carriers_embed_one_shared_base_envelope():
    generated = schema_bundle()
    base_envelope_fields = {
        "event_id",
        "schema_name",
        "schema_version",
        "event_type",
        "extension_policy",
        "event_classification",
        "source_status",
        "participant_address",
        "episode_id",
        "sequence_number",
        "occurred_at",
        "recorded_at",
        "ingested_at",
        "clock_authority",
        "temporal_context",
        "ordering_basis",
        "logical_order_ref",
        "predecessor_event_refs",
        "actor_ref",
        "producer_ref",
        "source_system_ref",
        "source_record_ref",
        "source_raw_ref",
        "source_pipeline",
        "raw_data_integrity",
        "confidence",
        "provenance_refs",
        "evidence_refs",
        "marking_definition_refs",
        "object_marking_refs",
        "markings",
        "granular_markings",
        "redaction_policy_ref",
        "authorization_scope",
    }
    for contract_id in PARTICIPANT_RUNTIME_FIXTURE_MODELS:
        schema = generated[contract_id]
        assert base_envelope_fields <= set(schema["properties"]), contract_id
        assert schema["properties"]["ordering_basis"]["enum"] == _ORDERING_BASIS_TERMS
        substructures = (
            "EventClassificationModel",
            "SourceStatusModel",
            "SourcePipelineModel",
            "RawDataIntegrityModel",
        )
        for substructure in substructures:
            assert substructure in schema["$defs"], (contract_id, substructure)


def test_participant_outcome_report_publishes_no_score_or_reward_surface():
    schema = schema_bundle()["participant-outcome-report-v1"]
    forbidden = {"score", "reward", "objective_success", "max_score", "return_value"}
    assert not forbidden & set(schema["properties"])
    source_schema = schema["$defs"]["ParticipantOutcomeReportSourceModel"]
    assert source_schema["properties"]["source_kind"]["enum"] == ["action_result", "episode_status", "evidence"]
    assert schema["properties"]["outcome_sources"]["minItems"] == 1


def test_participant_history_view_schema_requires_completeness_basis_when_not_complete():
    schema = schema_bundle()["participant-history-view-v1"]
    assert {
        "if": {
            "properties": {"completeness": {"enum": ["truncated", "filtered"]}},
            "required": ["completeness"],
        },
        "then": {
            "required": ["completeness_basis"],
            "properties": {"completeness_basis": {"type": "string", "minLength": 1}},
        },
    } in schema["allOf"]


def test_participant_views_reuse_published_episode_shapes():
    generated = schema_bundle()
    status_schema = generated["participant-status-view-v1"]
    history_schema = generated["participant-history-view-v1"]

    assert "ParticipantEpisodeStateModel" in status_schema["$defs"]
    assert history_schema["properties"]["episode_history"]["items"]["$ref"] == (
        "#/$defs/ParticipantEpisodeHistoryEventModel"
    )
    assert history_schema["properties"]["behavior_history"]["items"]["$ref"] == (
        "#/$defs/ParticipantBehaviorHistoryEventModel"
    )
    context_schema = generated["participant-context-view-v1"]
    assert context_schema["properties"]["derived_from_refs"]["minItems"] == 1


def test_participant_backend_contract_valid_fixtures_pass_schema_and_model_validation():
    generated = schema_bundle()
    for contract_id, model_cls in ALL_FIXTURE_MODELS.items():
        fixture_root = FIXTURE_ROOTS_BY_CONTRACT[contract_id] / contract_id
        validator = Draft202012Validator(generated[contract_id])
        valid_paths = sorted((fixture_root / "valid").glob("*.json"))
        assert valid_paths, f"{contract_id} must publish at least one valid fixture"
        for path in valid_paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            validator.validate(payload)
            model_cls.model_validate(payload)


def test_participant_backend_contract_invalid_fixtures_fail_schema_and_model_validation():
    generated = schema_bundle()
    for contract_id, model_cls in ALL_FIXTURE_MODELS.items():
        fixture_root = FIXTURE_ROOTS_BY_CONTRACT[contract_id] / contract_id
        validator = Draft202012Validator(generated[contract_id])
        invalid_paths = sorted((fixture_root / "invalid").glob("*.json"))
        assert invalid_paths, f"{contract_id} must publish at least one invalid fixture"
        for path in invalid_paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert list(validator.iter_errors(payload)), path
            with pytest.raises(ValidationError):
                model_cls.model_validate(payload)


def test_participant_history_view_requires_completeness_basis_unless_complete():
    payload = _valid_fixture("participant-history-view-v1")
    payload["completeness"] = "filtered"
    payload["completeness_basis"] = None

    with pytest.raises(ValidationError, match="completeness_basis"):
        ParticipantHistoryViewModel.model_validate(payload)

    payload["completeness"] = "complete"
    model = ParticipantHistoryViewModel.model_validate(payload)
    assert model.completeness_basis is None


def test_participant_lifecycle_event_rejects_unknown_mapping_loss():
    payload = _valid_fixture("participant-lifecycle-event-v1")
    payload["mapping_loss"] = "collapsed"

    with pytest.raises(ValidationError, match="mapping_loss"):
        ParticipantLifecycleEventModel.model_validate(payload)


def test_participant_observation_envelope_rejects_unknown_information_guarantee():
    payload = _valid_fixture("participant-observation-envelope-v1")
    payload["information_guarantee"] = "total_recall"

    with pytest.raises(ValidationError, match="information_guarantee"):
        ParticipantObservationEnvelopeModel.model_validate(payload)


def test_participant_shared_state_record_rejects_unknown_conflict_policy():
    payload = _valid_fixture("participant-shared-state-record-v1")
    payload["conflict_policy"] = "last_write_wins"

    with pytest.raises(ValidationError, match="conflict_policy"):
        ParticipantSharedStateRecordModel.model_validate(payload)
