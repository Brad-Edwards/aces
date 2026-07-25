"""Participant implementation manifest and provenance contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from raes_conformance.conformance import _validate_payload
from raes_contracts.contracts import (
    ParticipantImplementationManifestModel,
    ParticipantImplementationProvenanceModel,
)
from raes_contracts.manifest_authority import PARTICIPANT_IMPLEMENTATION_SUPPORTED_CONTRACT_IDS
from pydantic import ValidationError

FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"
MANIFEST_VALID_DIR = (
    FIXTURES_ROOT / "participant-implementation-manifest" / "participant-implementation-manifest-v1" / "valid"
)
MANIFEST_INVALID_DIR = (
    FIXTURES_ROOT / "participant-implementation-manifest" / "participant-implementation-manifest-v1" / "invalid"
)
PROVENANCE_VALID_DIR = (
    FIXTURES_ROOT / "participant-implementation-provenance" / "participant-implementation-provenance-v1" / "valid"
)
PROVENANCE_INVALID_DIR = (
    FIXTURES_ROOT / "participant-implementation-provenance" / "participant-implementation-provenance-v1" / "invalid"
)


def _manifest_payload() -> dict[str, object]:
    return {
        "schema_version": "participant-implementation-manifest/v1",
        "identity": {"name": "reference-red-agent", "version": "1.0.0"},
        "implementation_kind": "agent",
        "supported_contract_versions": [
            "participant-implementation-manifest-v1",
            "participant-implementation-provenance-v1",
            "participant-episode-state-envelope-v1",
            "participant-episode-history-event-stream-v1",
            "participant-behavior-history-event-stream-v1",
        ],
        "compatibility": {
            "participant_runtimes": ["stub-participant-runtime"],
            "processors": ["aces-reference-processor"],
            "backends": ["stub"],
        },
        "concept_bindings": [
            {"scope": "implementation_kind", "family": "apparatus-declarations"},
            {"scope": "capabilities.supported_participant_contracts", "family": "apparatus-declarations"},
            {"scope": "capabilities.supported_decision_surface_modes", "family": "apparatus-declarations"},
            {"scope": "capabilities.tool_affordance_expectations", "family": "tools-and-artifacts"},
            {"scope": "capabilities.exposure_policy_kinds", "family": "provenance-and-evidence"},
        ],
        "constraints": {"max_parallel_episodes": "1"},
        "capabilities": {
            "supported_participant_contracts": [
                "participant-episode-state-envelope-v1",
                "participant-episode-history-event-stream-v1",
                "participant-behavior-history-event-stream-v1",
            ],
            "supported_decision_surface_modes": ["autonomous", "policy-directed"],
            "tool_affordance_expectations": ["shell", "http-api"],
            "exposure_policy_kinds": ["task-statement", "observation-stream"],
        },
    }


def _provenance_payload() -> dict[str, object]:
    return {
        "schema_version": "participant-implementation-provenance/v1",
        "run_id": "run-2026-05-29-001",
        "participant_implementations": [
            {
                "participant_address": "participants.red",
                "implementation_identity": {"name": "reference-red-agent", "version": "1.0.0"},
                "manifest_ref": "contracts/fixtures/participant-implementation-manifest/reference.json",
                "manifest_digest": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
                "configuration_ref": "configs/red-agent.json",
                "configuration_digest": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
                "selected_decision_surface_mode": "policy-directed",
                "participant_contract_versions": [
                    "participant-episode-state-envelope-v1",
                    "participant-behavior-history-event-stream-v1",
                ],
                "exposure_policy": {
                    "policy_id": "red-agent-policy",
                    "policy_version": "1.0.0",
                    "policy_digest": "sha256:3333333333333333333333333333333333333333333333333333333333333333",
                    "exposure_policy_kinds": ["task-statement", "tool-affordance"],
                    "disclosed_refs": ["scenario.tasks.red"],
                    "withheld_refs": ["scenario.hidden.answer-key"],
                    "tool_affordance_refs": ["tool.shell", "tool.http-api"],
                    "visibility_scope_refs": ["participants.red.visible"],
                    "constraints": {"hidden_truth": "withheld"},
                },
            }
        ],
        "processor_manifest_ref": "processor-manifest-v2:aces-reference-processor",
        "backend_manifest_ref": "backend-manifest-v2:stub",
        "metadata": {"apparatus_record": "participant-implementation-selection"},
    }


def test_participant_implementation_manifest_roundtrip():
    payload = _manifest_payload()

    model = ParticipantImplementationManifestModel.model_validate(payload)

    assert model.identity.name == "reference-red-agent"
    assert model.implementation_kind == "agent"
    assert model.supported_contract_versions == list(PARTICIPANT_IMPLEMENTATION_SUPPORTED_CONTRACT_IDS)
    assert model.model_dump(mode="json") == payload


def test_participant_implementation_manifest_rejects_unknown_contract_claim():
    payload = _manifest_payload()
    payload["supported_contract_versions"] = ["semantic-profile-v1"]

    with pytest.raises(ValidationError, match="supported_contract_versions"):
        ParticipantImplementationManifestModel.model_validate(payload)


def test_participant_implementation_manifest_rejects_unsupported_participant_contract():
    payload = _manifest_payload()
    payload["capabilities"]["supported_participant_contracts"].append("semantic-profile-v1")  # type: ignore[index, union-attr]

    with pytest.raises(ValidationError, match="supported_participant_contracts"):
        ParticipantImplementationManifestModel.model_validate(payload)


def test_participant_implementation_manifest_rejects_empty_compatibility():
    payload = _manifest_payload()
    payload["compatibility"] = {}

    with pytest.raises(ValidationError, match="compatibility"):
        ParticipantImplementationManifestModel.model_validate(payload)


def test_participant_implementation_manifest_rejects_unguarded_vocabulary_value():
    payload = _manifest_payload()
    payload["capabilities"]["supported_decision_surface_modes"].append("custom-mode")  # type: ignore[index, union-attr]

    with pytest.raises(ValidationError, match="participant-decision-surface-modes"):
        ParticipantImplementationManifestModel.model_validate(payload)


def test_participant_implementation_provenance_roundtrip():
    payload = _provenance_payload()

    model = ParticipantImplementationProvenanceModel.model_validate(payload)

    assert model.run_id == "run-2026-05-29-001"
    assert model.participant_implementations[0].participant_address == "participants.red"
    assert model.participant_implementations[0].exposure_policy.withheld_refs == ["scenario.hidden.answer-key"]
    assert model.model_dump(mode="json") == payload


def test_participant_implementation_provenance_rejects_duplicate_participant_addresses():
    payload = _provenance_payload()
    payload["participant_implementations"].append(dict(payload["participant_implementations"][0]))  # type: ignore[index, union-attr]

    with pytest.raises(ValidationError, match="participant_address"):
        ParticipantImplementationProvenanceModel.model_validate(payload)


def test_participant_implementation_provenance_rejects_empty_exposure_policy():
    payload = _provenance_payload()
    payload["participant_implementations"][0]["exposure_policy"] = {  # type: ignore[index]
        "policy_id": "empty",
        "exposure_policy_kinds": ["task-statement"],
    }

    with pytest.raises(ValidationError, match="exposure policy"):
        ParticipantImplementationProvenanceModel.model_validate(payload)


def test_participant_implementation_valid_fixtures_pass_validation():
    for path in sorted(MANIFEST_VALID_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        model = ParticipantImplementationManifestModel.model_validate(payload)
        assert model.identity.name, f"Valid manifest fixture {path.name} should have a name"

    for path in sorted(PROVENANCE_VALID_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        model = ParticipantImplementationProvenanceModel.model_validate(payload)
        assert model.run_id, f"Valid provenance fixture {path.name} should have a run id"


def test_participant_implementation_invalid_fixtures_fail_validation():
    for path in sorted(MANIFEST_INVALID_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        with pytest.raises(ValidationError):
            ParticipantImplementationManifestModel.model_validate(payload)

    for path in sorted(PROVENANCE_INVALID_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        with pytest.raises(ValidationError):
            ParticipantImplementationProvenanceModel.model_validate(payload)


def test_participant_implementation_contracts_are_registered_with_conformance():
    assert not _validate_payload("participant-implementation-manifest-v1", _manifest_payload())
    assert not _validate_payload("participant-implementation-provenance-v1", _provenance_payload())

    invalid_manifest = _manifest_payload()
    invalid_manifest["capabilities"] = {}
    manifest_diagnostics = _validate_payload("participant-implementation-manifest-v1", invalid_manifest)
    assert {diagnostic.code for diagnostic in manifest_diagnostics} == {"conformance.schema-invalid"}

    invalid_provenance = _provenance_payload()
    invalid_provenance["participant_implementations"] = []
    provenance_diagnostics = _validate_payload("participant-implementation-provenance-v1", invalid_provenance)
    assert {diagnostic.code for diagnostic in provenance_diagnostics} == {"conformance.schema-invalid"}
