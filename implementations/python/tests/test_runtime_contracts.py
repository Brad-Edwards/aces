"""Schema-first runtime contract tests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from aces_contracts.contracts import (
    AcesSemanticInvariantEntryModel,
    AcesSemanticInvariantProfileReferenceModel,
    BackendManifestV2Model,
    ExperimentApparatusContextModel,
    ExperimentRunModel,
    ExperimentStudyModel,
    ExperimentTaskModel,
    ProcessorManifestV2Model,
    schema_bundle,
    validate_aces_semantic_invariant_annotations,
    validate_experiment_apparatus_context_against_manifests,
    validate_experiment_run_against_task,
    validate_experiment_run_archival_datetimes,
    validate_experiment_study_against_tasks_and_runs,
)
from aces_contracts.manifest_authority import (
    BACKEND_SUPPORTED_CONTRACT_IDS,
    PROCESSOR_SUPPORTED_CONTRACT_IDS,
    PROCESSOR_SUPPORTED_SDL_VERSION_IDS,
)
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from aces.core.runtime import contracts as compat_runtime_contracts

EXPERIMENT_CORE_FIXTURE_MODELS = {
    "experiment-apparatus-context-v1": ExperimentApparatusContextModel,
    "experiment-run-v1": ExperimentRunModel,
    "experiment-study-v1": ExperimentStudyModel,
    "experiment-task-v1": ExperimentTaskModel,
}


def _experiment_fixture(contract_id: str, fixture_name: str = "reference.json") -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    fixture_path = repo_root / "contracts" / "fixtures" / "experiment-core" / contract_id / "valid" / fixture_name
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _processor_manifest_fixture() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    fixture_path = (
        repo_root
        / "contracts"
        / "fixtures"
        / "processor-manifest"
        / "processor-manifest-v2"
        / "valid"
        / "reference.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    payload["identity"]["version"] = "0.1.0"
    return payload


def _backend_manifest_fixture() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    fixture_path = (
        repo_root / "contracts" / "fixtures" / "backend-manifest" / "backend-manifest-v2" / "valid" / "stub.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    payload["identity"]["name"] = "stub-backend"
    payload["identity"]["version"] = "0.1.0"
    return payload


def _assert_schema_and_model_reject(contract_id: str, payload: dict) -> None:
    schemas = schema_bundle()
    validator = Draft202012Validator(schemas[contract_id])
    assert list(validator.iter_errors(payload))
    with pytest.raises(ValidationError):
        EXPERIMENT_CORE_FIXTURE_MODELS[contract_id].model_validate(payload)


def _invariant_ids(schema: dict) -> set[str]:
    return {invariant["id"] for invariant in schema.get("x-aces-invariants", [])}


def _invariant_by_id(schema: dict, invariant_id: str) -> dict:
    return {invariant["id"]: invariant for invariant in schema.get("x-aces-invariants", [])}[invariant_id]


def test_published_contract_schemas_exist_and_match_bundle():
    repo_root = Path(__file__).resolve().parents[3]
    schemas_dir = repo_root / "contracts" / "schemas"
    published = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in schemas_dir.rglob("*.json")}

    generated = schema_bundle()

    assert set(generated) == set(published)
    for name, schema in generated.items():
        assert published[name] == schema


def test_compat_contract_imports_reexport_neutral_contracts():
    assert compat_runtime_contracts.ProcessorManifestV2Model is ProcessorManifestV2Model
    assert compat_runtime_contracts.BackendManifestV2Model is BackendManifestV2Model
    assert compat_runtime_contracts.schema_bundle() == schema_bundle()


def test_closed_world_contract_models_for_runtime_envelopes():
    generated = schema_bundle()

    for contract_id, schema in generated.items():
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].startswith("https://aces.dev/schemas/")
        validate_aces_semantic_invariant_annotations(contract_id, schema)

    assert generated["aces-semantic-invariants-v1"]["additionalProperties"] is False
    assert (
        generated["aces-semantic-invariants-v1"]["properties"]["profile_reference_schema"]["const"]
        == "#/$defs/AcesSemanticInvariantProfileReferenceModel"
    )
    assert "AcesSemanticInvariantProfileReferenceModel" in generated["aces-semantic-invariants-v1"]["$defs"]
    assert generated["aces-semantic-invariants-v1"]["required"] == [
        "schema_version",
        "profile_id",
        "uri",
        "keyword",
        "invariant_entry_schema",
        "profile_reference_schema",
        "invariants",
    ]
    assert list(Draft202012Validator(generated["aces-semantic-invariants-v1"]).iter_errors({}))
    assert generated["workflow-result-envelope-v1"]["additionalProperties"] is False
    assert generated["evaluation-result-envelope-v1"]["additionalProperties"] is False
    assert generated["operation-receipt-v1"]["additionalProperties"] is False
    assert generated["operation-status-v1"]["additionalProperties"] is False
    assert generated["runtime-snapshot-v1"]["additionalProperties"] is False
    assert generated["backend-manifest-v2"]["additionalProperties"] is False
    assert generated["processor-manifest-v2"]["additionalProperties"] is False
    assert generated["concept-families-v1"]["additionalProperties"] is False
    assert generated["reference-models-v1"]["additionalProperties"] is False
    assert generated["controlled-vocabularies-v1"]["additionalProperties"] is False
    assert generated["semantic-profile-v1"]["additionalProperties"] is False
    assert "backend-manifest-v1" not in generated


def test_experiment_core_schemas_publish_closed_world_contracts():
    generated = schema_bundle()

    for contract_id in EXPERIMENT_CORE_FIXTURE_MODELS:
        assert contract_id in generated
        assert generated[contract_id]["additionalProperties"] is False
        assert "schema_version" in generated[contract_id]["required"]

    task_schema = generated["experiment-task-v1"]
    apparatus_context_schema = generated["experiment-apparatus-context-v1"]
    run_schema = generated["experiment-run-v1"]
    study_schema = generated["experiment-study-v1"]

    assert task_schema["x-aces-semantic-profile"]["uri"] == "https://aces.dev/schemas/semantic-invariants/v1"
    assert "apparatus-archival-times-rfc3339-valid" in _invariant_ids(apparatus_context_schema)
    assert run_schema["x-aces-semantic-profile"]["required"] is True
    assert study_schema["x-aces-semantic-profile"]["keyword"] == "x-aces-invariants"
    assert run_schema["x-aces-semantic-profile"]["entry_schema_contract_id"] == "aces-semantic-invariants-v1"
    assert task_schema["properties"]["scenario_ref"]["$ref"] == "#/$defs/ExperimentScenarioReferenceModel"
    assert task_schema["properties"]["evaluation_protocol"]["$ref"] == "#/$defs/ExperimentEvaluationProtocolModel"
    assert (
        task_schema["$defs"]["ExperimentApparatusConstraintModel"]["properties"]["required_manifest_refs"]["items"][
            "$ref"
        ]
        == "#/$defs/ExperimentManifestReferenceModel"
    )
    metric_definitions_schema = task_schema["$defs"]["ExperimentEvaluationProtocolModel"]["properties"][
        "metric_definitions"
    ]
    assert metric_definitions_schema["type"] == "object"
    assert "metric-definition-key-matches-metric-id" in _invariant_ids(
        task_schema["$defs"]["ExperimentEvaluationProtocolModel"]
    )
    metric_key_invariant = _invariant_by_id(
        task_schema["$defs"]["ExperimentEvaluationProtocolModel"],
        "metric-definition-key-matches-metric-id",
    )
    assert metric_key_invariant["validator"].endswith(
        "ExperimentEvaluationProtocolModel._validate_metric_definition_keys"
    )
    assert metric_key_invariant["inputs"] == [
        {"contract_id": "experiment-task-v1", "instance_path": "#/evaluation_protocol"}
    ]
    assert (
        task_schema["$defs"]["ExperimentApparatusConstraintModel"]["properties"]["allowed_processor_refs"]["items"][
            "$ref"
        ]
        == "#/$defs/ExperimentProcessorReferenceModel"
    )
    assert (
        task_schema["$defs"]["ExperimentApparatusConstraintModel"]["properties"]["allowed_backend_refs"]["items"][
            "$ref"
        ]
        == "#/$defs/ExperimentBackendReferenceModel"
    )
    assert "apparatus-constraint-identity-manifest-resolves" in _invariant_ids(
        task_schema["$defs"]["ExperimentApparatusConstraintModel"]
    )
    assert "task-archival-times-rfc3339-valid" in _invariant_ids(task_schema)
    manifest_ref_schema = task_schema["$defs"]["ExperimentManifestReferenceModel"]
    assert "subject_ref" in manifest_ref_schema["properties"]
    metric_schema = task_schema["$defs"]["ExperimentMetricDefinitionModel"]
    assert metric_schema["required"] == [
        "metric_id",
        "metric_version",
        "name",
        "measured_construct",
        "unit_of_analysis",
        "value_kind",
        "direction",
        "evidence_requirements",
    ]
    assert run_schema["properties"]["apparatus_context"]["$ref"] == "#/$defs/ExperimentApparatusContextModel"
    apparatus_schema = run_schema["$defs"]["ExperimentApparatusContextModel"]
    component_schema = run_schema["$defs"]["ExperimentApparatusComponentModel"]
    assert apparatus_schema["properties"]["components"]["minProperties"] == 2
    assert apparatus_schema["properties"]["components"]["required"] == ["processor", "backend"]
    assert apparatus_schema["properties"]["selected_manifests"]["minItems"] == 1
    assert apparatus_schema["properties"]["clocks"]["minItems"] == 1
    assert apparatus_schema["properties"]["measurement_channels"]["minItems"] == 1
    assert apparatus_schema["properties"]["observed_setup_evidence"]["minItems"] == 1
    assert "schema_version" in apparatus_schema["required"]
    assert apparatus_schema["properties"]["selected_manifests"]["items"]["$ref"] == (
        "#/$defs/ExperimentManifestReferenceModel"
    )
    assert "canonical-apparatus-manifest-selected" in _invariant_ids(apparatus_schema)
    assert "apparatus-manifest-payload-identity-valid" in _invariant_ids(apparatus_schema)
    assert (
        component_schema["properties"]["manifest_ref"]["anyOf"][0]["$ref"] == "#/$defs/ExperimentManifestReferenceModel"
    )
    assert run_schema["properties"]["task_ref"]["$ref"] == "#/$defs/ExperimentTaskReferenceModel"
    assert (
        run_schema["properties"]["scenario_snapshot_ref"]["$ref"] == "#/$defs/ExperimentScenarioSnapshotReferenceModel"
    )
    assert "ended_at" in run_schema["required"]
    assert "clock_context" in run_schema["required"]
    assert "evidence_artifacts" in run_schema["required"]
    assert "result_summaries" in run_schema["required"]
    assert run_schema["properties"]["started_at"]["format"] == "date-time"
    assert run_schema["properties"]["ended_at"]["format"] == "date-time"
    assert "run-archival-times-rfc3339-valid" in _invariant_ids(run_schema)
    assert "ended-at-not-before-started-at" in _invariant_ids(run_schema)
    assert "result-evidence-ref-resolves" in _invariant_ids(run_schema)
    task_run_invariant = _invariant_by_id(run_schema, "task-run-protocol-binding-valid")
    assert task_run_invariant["validator"] == "aces_contracts.contracts.validate_experiment_run_against_task"
    assert task_run_invariant["inputs"] == [
        {"contract_id": "experiment-task-v1", "instance_path": "#"},
        {"contract_id": "experiment-run-v1", "instance_path": "#"},
    ]
    artifact_schema = run_schema["$defs"]["ExperimentArtifactRefModel"]
    assert artifact_schema["required"] == [
        "artifact_id",
        "role",
        "media_type",
        "uri",
        "checksum",
        "size_bytes",
        "created_at",
        "source",
    ]
    assert (
        artifact_schema["properties"]["satisfies_refs"]["items"]["$ref"] == "#/$defs/ExperimentEvidenceReferenceModel"
    )
    assert artifact_schema["properties"]["created_at"]["format"] == "date-time"
    assert "cost-resource-trace" in artifact_schema["properties"]["role"]["enum"]
    assert "scaffold" in artifact_schema["properties"]["role"]["enum"]
    result_schema = run_schema["$defs"]["ExperimentResultSummaryModel"]
    assert result_schema["required"] == ["metric_id", "value_status", "evidence_refs"]
    assert run_schema["properties"]["result_summaries"]["type"] == "object"
    assert study_schema["properties"]["study_kind"]["enum"] == ["study", "collection", "benchmark", "cohort"]
    assert "owner" in study_schema["required"]
    assert study_schema["properties"]["membership"]["type"] == "object"
    analysis_plan_schema = study_schema["$defs"]["ExperimentAnalysisPlanModel"]
    assert analysis_plan_schema["required"] == [
        "analysis_id",
        "description",
        "metrics",
        "primary_metric",
        "statistical_method",
        "uncertainty_method",
        "multiple_comparison_policy",
        "missing_data_policy",
    ]
    assert analysis_plan_schema["properties"]["metrics"]["minItems"] == 1
    assert (
        analysis_plan_schema["properties"]["statistical_method"]["$ref"] == "#/$defs/ExperimentStatisticalMethodModel"
    )
    assert (
        analysis_plan_schema["properties"]["uncertainty_method"]["$ref"] == "#/$defs/ExperimentUncertaintyMethodModel"
    )
    assert (
        analysis_plan_schema["properties"]["multiple_comparison_policy"]["$ref"]
        == "#/$defs/ExperimentMultipleComparisonPolicyModel"
    )
    assert analysis_plan_schema["properties"]["missing_data_policy"]["$ref"] == (
        "#/$defs/ExperimentMissingDataPolicyModel"
    )
    assert study_schema["properties"]["run_allocation"]["anyOf"][0]["$ref"] == (
        "#/$defs/ExperimentRunAllocationPlanModel"
    )
    run_allocation_schema = study_schema["$defs"]["ExperimentRunAllocationPlanModel"]
    assert "condition_assignments" in run_allocation_schema["required"]
    assert (
        run_allocation_schema["properties"]["condition_assignments"]["additionalProperties"]["$ref"]
        == "#/$defs/ExperimentConditionAssignmentModel"
    )
    assert "analysis-plan-substantive-methods-required" in _invariant_ids(analysis_plan_schema)
    assert "claim-bearing-study-analysis-plan-required" in _invariant_ids(study_schema)
    assert "study-analysis-metrics-grounded-in-task-protocols" in _invariant_ids(study_schema)
    assert "study-analysis-metrics-covered-by-evaluation-run-results" in _invariant_ids(study_schema)
    assert "study-run-allocation-covered-by-evaluation-run-members" in _invariant_ids(study_schema)
    assert "study-archival-times-rfc3339-valid" in _invariant_ids(study_schema)
    assert any(
        rule.get("if", {}).get("properties", {}).get("run_status", {}).get("const") == "invalidated"
        for rule in run_schema["allOf"]
    )


def test_aces_semantic_invariant_annotations_have_published_shape():
    generated = schema_bundle()
    run_schema = generated["experiment-run-v1"]
    profile = AcesSemanticInvariantProfileReferenceModel.model_validate(run_schema["x-aces-semantic-profile"])
    assert profile.entry_schema_pointer == "#/$defs/AcesSemanticInvariantEntryModel"

    task_run_invariant = _invariant_by_id(run_schema, "task-run-protocol-binding-valid")
    invariant = AcesSemanticInvariantEntryModel.model_validate(task_run_invariant)
    assert invariant.inputs[0].contract_id == "experiment-task-v1"

    corrupted_schema = deepcopy(run_schema)
    del corrupted_schema["x-aces-invariants"][0]["validator"]
    with pytest.raises(ValidationError):
        validate_aces_semantic_invariant_annotations("experiment-run-v1", corrupted_schema)

    unresolved_validator_schema = deepcopy(run_schema)
    unresolved_validator_schema["x-aces-invariants"][0]["validator"] = "aces_contracts.contracts.DoesNotExist"
    with pytest.raises(ValueError, match="does not resolve"):
        validate_aces_semantic_invariant_annotations("experiment-run-v1", unresolved_validator_schema)


def test_experiment_core_valid_fixtures_pass_model_validation():
    repo_root = Path(__file__).resolve().parents[3]
    fixture_root = repo_root / "contracts" / "fixtures" / "experiment-core"
    schemas = schema_bundle()

    for contract_id, model_cls in EXPERIMENT_CORE_FIXTURE_MODELS.items():
        validator = Draft202012Validator(schemas[contract_id])
        for path in sorted((fixture_root / contract_id / "valid").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            validator.validate(payload)
            model = model_cls.model_validate(payload)
            assert model.schema_version == payload["schema_version"]


def test_experiment_core_invalid_fixtures_fail_schema_and_model_validation():
    repo_root = Path(__file__).resolve().parents[3]
    fixture_root = repo_root / "contracts" / "fixtures" / "experiment-core"
    schemas = schema_bundle()

    for contract_id, model_cls in EXPERIMENT_CORE_FIXTURE_MODELS.items():
        validator = Draft202012Validator(schemas[contract_id])
        for path in sorted((fixture_root / contract_id / "invalid").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert list(validator.iter_errors(payload)), path
            with pytest.raises(ValidationError):
                model_cls.model_validate(payload)


def test_experiment_core_requires_schema_versions_on_wire_artifacts():
    for contract_id, model_cls in EXPERIMENT_CORE_FIXTURE_MODELS.items():
        payload = _experiment_fixture(contract_id)
        del payload["schema_version"]

        assert list(Draft202012Validator(schema_bundle()[contract_id]).iter_errors(payload))
        with pytest.raises(ValidationError):
            model_cls.model_validate(payload)

    run_payload = _experiment_fixture("experiment-run-v1")
    del run_payload["apparatus_context"]["schema_version"]
    assert list(Draft202012Validator(schema_bundle()["experiment-run-v1"]).iter_errors(run_payload))
    with pytest.raises(ValidationError):
        ExperimentRunModel.model_validate(run_payload)


def test_experiment_core_rejects_under_specified_apparatus_contexts():
    payload = _experiment_fixture("experiment-apparatus-context-v1")

    missing_backend = deepcopy(payload)
    del missing_backend["components"]["backend"]
    _assert_schema_and_model_reject("experiment-apparatus-context-v1", missing_backend)

    missing_selected_manifest = deepcopy(payload)
    missing_selected_manifest["selected_manifests"] = []
    _assert_schema_and_model_reject("experiment-apparatus-context-v1", missing_selected_manifest)

    untyped_measurement_channel = deepcopy(payload)
    untyped_measurement_channel["measurement_channels"][0]["ref_kind"] = "evidence"
    _assert_schema_and_model_reject("experiment-apparatus-context-v1", untyped_measurement_channel)


def test_experiment_core_validates_apparatus_context_against_manifest_payloads():
    apparatus = ExperimentApparatusContextModel.model_validate(_experiment_fixture("experiment-apparatus-context-v1"))
    processor_manifest = ProcessorManifestV2Model.model_validate(_processor_manifest_fixture())
    backend_manifest = BackendManifestV2Model.model_validate(_backend_manifest_fixture())

    validate_experiment_apparatus_context_against_manifests(apparatus, processor_manifest, backend_manifest)

    mismatched_processor_payload = _processor_manifest_fixture()
    mismatched_processor_payload["identity"]["name"] = "different-processor"
    with pytest.raises(ValueError, match="processor"):
        validate_experiment_apparatus_context_against_manifests(
            apparatus,
            ProcessorManifestV2Model.model_validate(mismatched_processor_payload),
            backend_manifest,
        )

    apparatus_with_digest = _experiment_fixture("experiment-apparatus-context-v1")
    apparatus_with_digest["components"]["processor"]["manifest_ref"]["ref_digest"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    apparatus_with_digest["selected_manifests"][0]["ref_digest"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    with pytest.raises(ValueError, match="supplied manifest payload digest"):
        validate_experiment_apparatus_context_against_manifests(
            ExperimentApparatusContextModel.model_validate(apparatus_with_digest),
            processor_manifest,
            backend_manifest,
        )
    with pytest.raises(ValueError, match="digest"):
        validate_experiment_apparatus_context_against_manifests(
            ExperimentApparatusContextModel.model_validate(apparatus_with_digest),
            processor_manifest,
            backend_manifest,
            processor_manifest_digest="sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        )

    apparatus_with_uppercase_digest = _experiment_fixture("experiment-apparatus-context-v1")
    apparatus_with_uppercase_digest["components"]["processor"]["manifest_ref"]["ref_digest"] = (
        "sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    )
    apparatus_with_uppercase_digest["selected_manifests"][0]["ref_digest"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    validate_experiment_apparatus_context_against_manifests(
        ExperimentApparatusContextModel.model_validate(apparatus_with_uppercase_digest),
        processor_manifest,
        backend_manifest,
        processor_manifest_digest="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )

    selected_manifest_digest_mismatch = _experiment_fixture("experiment-apparatus-context-v1")
    selected_manifest_digest_mismatch["components"]["processor"]["manifest_ref"]["ref_digest"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    selected_manifest_digest_mismatch["selected_manifests"][0]["ref_digest"] = (
        "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    with pytest.raises(ValidationError, match="selected_manifests"):
        ExperimentApparatusContextModel.model_validate(selected_manifest_digest_mismatch)


def test_experiment_core_rejects_empty_or_unsubstantiated_run_results():
    payload = _experiment_fixture("experiment-run-v1")

    missing_evidence = deepcopy(payload)
    missing_evidence["evidence_artifacts"] = []
    _assert_schema_and_model_reject("experiment-run-v1", missing_evidence)

    result_without_metric = deepcopy(payload)
    del result_without_metric["result_summaries"]["foothold-achieved-result"]["metric_id"]
    _assert_schema_and_model_reject("experiment-run-v1", result_without_metric)

    result_without_evidence = deepcopy(payload)
    result_without_evidence["result_summaries"]["foothold-achieved-result"]["evidence_refs"] = []
    _assert_schema_and_model_reject("experiment-run-v1", result_without_evidence)

    artifact_without_checksum = deepcopy(payload)
    del artifact_without_checksum["evidence_artifacts"][0]["checksum"]
    _assert_schema_and_model_reject("experiment-run-v1", artifact_without_checksum)

    redacted_parameter_with_value = deepcopy(payload)
    redacted_parameter_with_value["parameter_set"][0]["redaction"] = "redacted"
    _assert_schema_and_model_reject("experiment-run-v1", redacted_parameter_with_value)

    reversed_time = deepcopy(payload)
    reversed_time["ended_at"] = "2026-05-26T00:09:00Z"
    with pytest.raises(ValidationError):
        ExperimentRunModel.model_validate(reversed_time)

    missing_result_evidence_artifact = deepcopy(payload)
    missing_result_evidence_artifact["result_summaries"]["foothold-achieved-result"]["evidence_refs"][0]["ref_id"] = (
        "missing-evidence"
    )
    with pytest.raises(ValidationError):
        ExperimentRunModel.model_validate(missing_result_evidence_artifact)


def test_experiment_core_validates_task_run_protocol_binding():
    task_payload = _experiment_fixture("experiment-task-v1")
    run_payload = _experiment_fixture("experiment-run-v1")
    task = ExperimentTaskModel.model_validate(task_payload)
    run = ExperimentRunModel.model_validate(run_payload)

    validate_experiment_run_against_task(task, run)

    undeclared_metric = deepcopy(run_payload)
    undeclared_metric["result_summaries"]["foothold-achieved-result"]["metric_id"] = "undeclared-metric"
    with pytest.raises(ValueError, match="metric_id"):
        validate_experiment_run_against_task(task, ExperimentRunModel.model_validate(undeclared_metric))

    missing_task_observation = deepcopy(run_payload)
    missing_task_observation["evidence_artifacts"][0]["satisfies_refs"] = []
    with pytest.raises(ValueError, match="observation requirements"):
        validate_experiment_run_against_task(task, ExperimentRunModel.model_validate(missing_task_observation))

    digest_bound_task = deepcopy(task_payload)
    digest_bound_task["evaluation_protocol"]["observation_requirements"][0]["ref_digest"] = (
        "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    digest_bound_task["evaluation_protocol"]["observation_requirements"][0]["ref_path"] = (
        "runs/run-techvault-001/evaluation-history.json"
    )
    validate_experiment_run_against_task(ExperimentTaskModel.model_validate(digest_bound_task), run)

    uppercase_digest_task = deepcopy(digest_bound_task)
    uppercase_digest_task["scenario_ref"]["ref_digest"] = (
        "sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    )
    uppercase_digest_task["apparatus_constraints"]["required_manifest_refs"][0]["ref_digest"] = (
        "sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    )
    uppercase_digest_task["evaluation_protocol"]["observation_requirements"][0]["ref_digest"] = (
        "sha256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
    )
    uppercase_digest_run_payload = deepcopy(run_payload)
    uppercase_digest_run_payload["apparatus_context"]["components"]["processor"]["manifest_ref"]["ref_digest"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    uppercase_digest_run_payload["scenario_snapshot_ref"]["ref_digest"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    uppercase_digest_run_payload["apparatus_context"]["selected_manifests"][0]["ref_digest"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    validate_experiment_run_against_task(
        ExperimentTaskModel.model_validate(uppercase_digest_task),
        ExperimentRunModel.model_validate(uppercase_digest_run_payload),
    )

    mismatched_observation_digest = deepcopy(digest_bound_task)
    mismatched_observation_digest["evaluation_protocol"]["observation_requirements"][0]["ref_digest"] = (
        "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    )
    with pytest.raises(ValueError, match="observation requirements"):
        validate_experiment_run_against_task(ExperimentTaskModel.model_validate(mismatched_observation_digest), run)

    mismatched_metric_evidence_path = deepcopy(task_payload)
    mismatched_metric_evidence_path["evaluation_protocol"]["metric_definitions"]["foothold-achieved"][
        "evidence_requirements"
    ][0] = {
        "ref_kind": "evidence",
        "ref_id": "evaluation-history",
        "ref_path": "runs/run-techvault-001/different-history.json",
    }
    with pytest.raises(ValueError, match="metric evidence requirements"):
        validate_experiment_run_against_task(
            ExperimentTaskModel.model_validate(mismatched_metric_evidence_path),
            run,
        )

    wrong_task_version = deepcopy(run_payload)
    wrong_task_version["task_ref"]["ref_version"] = "2.0.0"
    with pytest.raises(ValueError, match="task_ref"):
        validate_experiment_run_against_task(task, ExperimentRunModel.model_validate(wrong_task_version))

    generic_scenario_task = deepcopy(task_payload)
    generic_scenario_task["scenario_ref"] = {"ref_kind": "scenario", "ref_id": "scenario-techvault"}
    mismatched_scenario_run = deepcopy(run_payload)
    mismatched_scenario_run["scenario_snapshot_ref"]["ref_id"] = "different-scenario"
    with pytest.raises(ValueError, match="scenario_snapshot_ref"):
        validate_experiment_run_against_task(
            ExperimentTaskModel.model_validate(generic_scenario_task),
            ExperimentRunModel.model_validate(mismatched_scenario_run),
        )

    disallowed_processor = deepcopy(run_payload)
    disallowed_processor["apparatus_context"]["components"]["processor"]["identity"]["name"] = "different-processor"
    disallowed_processor["apparatus_context"]["components"]["processor"]["manifest_ref"]["ref_id"] = (
        "different-processor"
    )
    disallowed_processor["apparatus_context"]["components"]["processor"]["manifest_ref"]["subject_ref"]["ref_id"] = (
        "different-processor"
    )
    disallowed_processor["apparatus_context"]["selected_manifests"][0]["ref_id"] = "different-processor"
    disallowed_processor["apparatus_context"]["selected_manifests"][0]["subject_ref"]["ref_id"] = "different-processor"
    with pytest.raises(ValueError, match="allowed_processor_refs"):
        validate_experiment_run_against_task(task, ExperimentRunModel.model_validate(disallowed_processor))

    task_with_extra_manifest = deepcopy(task_payload)
    task_with_extra_manifest["apparatus_constraints"]["required_manifest_refs"].append(
        {
            "ref_kind": "manifest",
            "ref_id": "missing-measurement-manifest",
            "ref_version": "backend-manifest/v2",
            "subject_ref": {
                "ref_kind": "backend",
                "ref_id": "missing-measurement-backend",
                "ref_version": "1.0.0",
            },
        }
    )
    with pytest.raises(ValueError, match="required_manifest_refs"):
        validate_experiment_run_against_task(ExperimentTaskModel.model_validate(task_with_extra_manifest), run)

    missing_capability = deepcopy(run_payload)
    missing_capability["apparatus_context"]["compatibility_declarations"] = [
        {
            "ref_kind": "profile",
            "ref_id": "reference-stack-v1",
            "ref_version": "semantic-profile/v1",
        }
    ]
    with pytest.raises(ValueError, match="required_capabilities"):
        validate_experiment_run_against_task(task, ExperimentRunModel.model_validate(missing_capability))


def test_experiment_core_validates_study_analysis_metrics_against_task_protocols():
    task = ExperimentTaskModel.model_validate(_experiment_fixture("experiment-task-v1"))
    run = ExperimentRunModel.model_validate(_experiment_fixture("experiment-run-v1"))
    study = ExperimentStudyModel.model_validate(_experiment_fixture("experiment-study-v1"))

    validate_experiment_study_against_tasks_and_runs(study, [task], [run])

    ungrounded_metric_payload = _experiment_fixture("experiment-study-v1")
    ungrounded_metric_payload["analysis_plan"]["metrics"] = ["undeclared-study-metric"]
    ungrounded_metric_payload["analysis_plan"]["primary_metric"] = "undeclared-study-metric"
    ungrounded_metric_study = ExperimentStudyModel.model_validate(ungrounded_metric_payload)
    with pytest.raises(ValueError, match="included task protocols"):
        validate_experiment_study_against_tasks_and_runs(ungrounded_metric_study, [task], [run])

    task_with_unreported_metric_payload = _experiment_fixture("experiment-task-v1")
    task_with_unreported_metric_payload["evaluation_protocol"]["metric_definitions"]["exfiltration-achieved"] = (
        deepcopy(task_with_unreported_metric_payload["evaluation_protocol"]["metric_definitions"]["foothold-achieved"])
    )
    task_with_unreported_metric_payload["evaluation_protocol"]["metric_definitions"]["exfiltration-achieved"][
        "metric_id"
    ] = "exfiltration-achieved"
    task_with_unreported_metric = ExperimentTaskModel.model_validate(task_with_unreported_metric_payload)
    study_with_unreported_metric_payload = _experiment_fixture("experiment-study-v1")
    study_with_unreported_metric_payload["analysis_plan"]["metrics"] = ["exfiltration-achieved"]
    study_with_unreported_metric_payload["analysis_plan"]["primary_metric"] = "exfiltration-achieved"
    study_with_unreported_metric = ExperimentStudyModel.model_validate(study_with_unreported_metric_payload)
    with pytest.raises(ValueError, match="included evaluation runs"):
        validate_experiment_study_against_tasks_and_runs(
            study_with_unreported_metric, [task_with_unreported_metric], [run]
        )

    run_with_explicit_missing_payload = _experiment_fixture("experiment-run-v1")
    missing_result = deepcopy(run_with_explicit_missing_payload["result_summaries"]["foothold-achieved-result"])
    missing_result["metric_id"] = "exfiltration-achieved"
    missing_result["value_status"] = "missing"
    missing_result.pop("value")
    run_with_explicit_missing_payload["result_summaries"]["exfiltration-achieved-result"] = missing_result
    validate_experiment_study_against_tasks_and_runs(
        study_with_unreported_metric,
        [task_with_unreported_metric],
        [ExperimentRunModel.model_validate(run_with_explicit_missing_payload)],
    )

    missing_task_artifact = ExperimentStudyModel.model_validate(_experiment_fixture("experiment-study-v1"))
    with pytest.raises(ValueError, match="task membership"):
        validate_experiment_study_against_tasks_and_runs(missing_task_artifact, [], [run])


def test_experiment_core_validates_study_run_allocation_against_evaluation_members():
    task = ExperimentTaskModel.model_validate(_experiment_fixture("experiment-task-v1"))
    run = ExperimentRunModel.model_validate(_experiment_fixture("experiment-run-v1"))
    study_payload = _experiment_fixture("experiment-study-v1")
    study = ExperimentStudyModel.model_validate(study_payload)

    validate_experiment_study_against_tasks_and_runs(study, [task], [run])

    no_evaluation_run_payload = deepcopy(study_payload)
    del no_evaluation_run_payload["membership"]["run-001"]
    no_evaluation_run_study = ExperimentStudyModel.model_validate(no_evaluation_run_payload)
    with pytest.raises(ValueError, match="evaluation-run membership"):
        validate_experiment_study_against_tasks_and_runs(no_evaluation_run_study, [task], [run])

    ungrouped_run_payload = deepcopy(study_payload)
    del ungrouped_run_payload["membership"]["run-001"]["grouping"]
    ungrouped_run_study = ExperimentStudyModel.model_validate(ungrouped_run_payload)
    with pytest.raises(ValueError, match="evaluation-run membership groupings"):
        validate_experiment_study_against_tasks_and_runs(ungrouped_run_study, [task], [run])

    undeclared_group_payload = deepcopy(study_payload)
    undeclared_group_payload["membership"]["run-001"]["grouping"] = "candidate"
    undeclared_group_study = ExperimentStudyModel.model_validate(undeclared_group_payload)
    with pytest.raises(ValueError, match="compared_conditions"):
        validate_experiment_study_against_tasks_and_runs(undeclared_group_study, [task], [run])

    under_target_payload = deepcopy(study_payload)
    under_target_payload["run_allocation"]["target_runs_per_condition"] = 2
    under_target_study = ExperimentStudyModel.model_validate(under_target_payload)
    with pytest.raises(ValueError, match="target_runs_per_condition"):
        validate_experiment_study_against_tasks_and_runs(under_target_study, [task], [run])

    collection_with_allocation_payload = deepcopy(study_payload)
    collection_with_allocation_payload["study_kind"] = "collection"
    del collection_with_allocation_payload["analysis_plan"]
    del collection_with_allocation_payload["membership"]["run-001"]["grouping"]
    collection_with_allocation = ExperimentStudyModel.model_validate(collection_with_allocation_payload)
    with pytest.raises(ValueError, match="run_allocation requires evaluation-run membership groupings"):
        validate_experiment_study_against_tasks_and_runs(collection_with_allocation, [task], [run])

    duplicate_condition_payload = deepcopy(study_payload)
    duplicate_condition_payload["run_allocation"]["compared_conditions"].append("baseline")
    _assert_schema_and_model_reject("experiment-study-v1", duplicate_condition_payload)

    missing_assignment_payload = deepcopy(study_payload)
    del missing_assignment_payload["run_allocation"]["condition_assignments"]
    _assert_schema_and_model_reject("experiment-study-v1", missing_assignment_payload)

    opaque_condition_ref_payload = deepcopy(study_payload)
    opaque_condition_ref_payload["run_allocation"]["condition_assignments"]["baseline"]["required_refs"] = [
        {"ref_kind": "other", "ref_id": "opaque-treatment-token"}
    ]
    _assert_schema_and_model_reject("experiment-study-v1", opaque_condition_ref_payload)

    opaque_condition_parameter_payload = deepcopy(study_payload)
    opaque_condition_parameter_payload["run_allocation"]["condition_assignments"]["baseline"]["required_refs"] = []
    opaque_condition_parameter_payload["run_allocation"]["condition_assignments"]["baseline"]["required_parameters"] = [
        {"name": "opaque-treatment-token", "value": "token-a", "value_kind": "other"}
    ]
    _assert_schema_and_model_reject("experiment-study-v1", opaque_condition_parameter_payload)

    redacted_condition_parameter_payload = deepcopy(study_payload)
    redacted_condition_parameter_payload["run_allocation"]["condition_assignments"]["baseline"]["required_refs"] = []
    redacted_condition_parameter_payload["run_allocation"]["condition_assignments"]["baseline"][
        "required_parameters"
    ] = [{"name": "assignment-secret", "value": "token-a", "value_kind": "protocol", "redaction": "redacted"}]
    _assert_schema_and_model_reject("experiment-study-v1", redacted_condition_parameter_payload)

    undeclared_blocking_factor_payload = deepcopy(study_payload)
    undeclared_blocking_factor_payload["run_allocation"]["blocking_factors"].append("undeclared-block")
    with pytest.raises(ValidationError, match="blocking_factors"):
        ExperimentStudyModel.model_validate(undeclared_blocking_factor_payload)

    empty_blocking_factor_levels_payload = deepcopy(study_payload)
    empty_blocking_factor_levels_payload["factors"]["empty-block"] = {
        "name": "Empty block",
        "factor_kind": "blocking",
    }
    empty_blocking_factor_levels_payload["run_allocation"]["blocking_factors"].append("empty-block")
    with pytest.raises(ValidationError, match="declared levels"):
        ExperimentStudyModel.model_validate(empty_blocking_factor_levels_payload)

    invalid_blocking_factor_kind_payload = deepcopy(study_payload)
    invalid_blocking_factor_kind_payload["run_allocation"]["blocking_factors"].append("participant-policy")
    with pytest.raises(ValidationError, match="blocking, stratification, apparatus, or control"):
        ExperimentStudyModel.model_validate(invalid_blocking_factor_kind_payload)

    duplicate_factor_levels_payload = deepcopy(study_payload)
    duplicate_factor_levels_payload["run_allocation"]["compared_conditions"].append("candidate")
    duplicate_factor_levels_payload["run_allocation"]["condition_assignments"]["candidate"] = deepcopy(
        duplicate_factor_levels_payload["run_allocation"]["condition_assignments"]["baseline"]
    )
    duplicate_factor_levels_payload["run_allocation"]["condition_assignments"]["candidate"]["condition_id"] = (
        "candidate"
    )
    duplicate_factor_levels_payload["run_allocation"]["condition_assignments"]["candidate"]["required_refs"][0][
        "ref_id"
    ] = "candidate-policy"
    with pytest.raises(ValidationError, match="distinct factor-level combinations"):
        ExperimentStudyModel.model_validate(duplicate_factor_levels_payload)

    duplicate_criteria_payload = deepcopy(study_payload)
    duplicate_criteria_payload["factors"]["participant-policy"]["levels"].append("candidate")
    duplicate_criteria_payload["run_allocation"]["compared_conditions"].append("candidate")
    duplicate_criteria_payload["run_allocation"]["condition_assignments"]["candidate"] = deepcopy(
        duplicate_criteria_payload["run_allocation"]["condition_assignments"]["baseline"]
    )
    duplicate_criteria_payload["run_allocation"]["condition_assignments"]["candidate"]["condition_id"] = "candidate"
    duplicate_criteria_payload["run_allocation"]["condition_assignments"]["candidate"]["factor_levels"][
        "participant-policy"
    ] = "candidate"
    with pytest.raises(ValidationError, match="distinct run-level criteria"):
        ExperimentStudyModel.model_validate(duplicate_criteria_payload)

    duplicate_mixed_type_criteria_payload = deepcopy(study_payload)
    duplicate_mixed_type_criteria_payload["factors"]["participant-policy"]["levels"].append("candidate")
    duplicate_mixed_type_criteria_payload["run_allocation"]["compared_conditions"].append("candidate")
    duplicate_mixed_type_criteria_payload["run_allocation"]["condition_assignments"]["baseline"]["required_refs"] = []
    duplicate_mixed_type_criteria_payload["run_allocation"]["condition_assignments"]["baseline"][
        "required_parameters"
    ] = [
        {"name": "same-name", "value": 1, "value_kind": "protocol"},
        {"name": "same-name", "value": "1", "value_kind": "protocol"},
    ]
    duplicate_mixed_type_criteria_payload["run_allocation"]["condition_assignments"]["candidate"] = deepcopy(
        duplicate_mixed_type_criteria_payload["run_allocation"]["condition_assignments"]["baseline"]
    )
    duplicate_mixed_type_criteria_payload["run_allocation"]["condition_assignments"]["candidate"]["condition_id"] = (
        "candidate"
    )
    duplicate_mixed_type_criteria_payload["run_allocation"]["condition_assignments"]["candidate"]["factor_levels"][
        "participant-policy"
    ] = "candidate"
    with pytest.raises(ValidationError, match="distinct run-level criteria"):
        ExperimentStudyModel.model_validate(duplicate_mixed_type_criteria_payload)

    unknown_factor_payload = deepcopy(study_payload)
    unknown_factor_payload["run_allocation"]["condition_assignments"]["baseline"]["factor_levels"] = {
        "undeclared-factor": "baseline"
    }
    with pytest.raises(ValidationError, match="declared factors"):
        ExperimentStudyModel.model_validate(unknown_factor_payload)

    unknown_factor_level_payload = deepcopy(study_payload)
    unknown_factor_level_payload["run_allocation"]["condition_assignments"]["baseline"]["factor_levels"] = {
        "participant-policy": "candidate"
    }
    with pytest.raises(ValidationError, match="declared factor levels"):
        ExperimentStudyModel.model_validate(unknown_factor_level_payload)

    unsatisfied_condition_payload = deepcopy(study_payload)
    unsatisfied_condition_payload["run_allocation"]["condition_assignments"]["baseline"]["required_refs"][0][
        "ref_id"
    ] = "candidate-policy"
    unsatisfied_condition_study = ExperimentStudyModel.model_validate(unsatisfied_condition_payload)
    with pytest.raises(ValueError, match="condition assignments"):
        validate_experiment_study_against_tasks_and_runs(unsatisfied_condition_study, [task], [run])

    overlapping_condition_payload = deepcopy(study_payload)
    overlapping_condition_payload["factors"]["participant-policy"]["levels"].append("candidate")
    overlapping_condition_payload["run_allocation"]["compared_conditions"].append("candidate")
    overlapping_condition_payload["run_allocation"]["condition_assignments"]["baseline"]["required_refs"] = [
        {
            "ref_kind": "processor",
            "ref_id": "aces-reference-processor",
            "ref_version": "0.1.0",
        }
    ]
    overlapping_condition_payload["run_allocation"]["condition_assignments"]["candidate"] = deepcopy(
        overlapping_condition_payload["run_allocation"]["condition_assignments"]["baseline"]
    )
    overlapping_condition_payload["run_allocation"]["condition_assignments"]["candidate"]["condition_id"] = "candidate"
    overlapping_condition_payload["run_allocation"]["condition_assignments"]["candidate"]["factor_levels"][
        "participant-policy"
    ] = "candidate"
    overlapping_condition_payload["run_allocation"]["condition_assignments"]["candidate"]["required_refs"].append(
        {
            "ref_kind": "participant-implementation",
            "ref_id": "baseline-policy",
            "ref_version": "1.0.0",
        }
    )
    overlapping_condition_payload["membership"]["run-001"]["grouping"] = "candidate"
    overlapping_condition_study = ExperimentStudyModel.model_validate(overlapping_condition_payload)
    with pytest.raises(ValueError, match="exactly one condition"):
        validate_experiment_study_against_tasks_and_runs(overlapping_condition_study, [task], [run])

    duplicate_run_condition_payload = deepcopy(study_payload)
    duplicate_run_condition_payload["factors"]["participant-policy"]["levels"].append("candidate")
    duplicate_run_condition_payload["run_allocation"]["compared_conditions"].append("candidate")
    duplicate_run_condition_payload["run_allocation"]["condition_assignments"]["candidate"] = deepcopy(
        duplicate_run_condition_payload["run_allocation"]["condition_assignments"]["baseline"]
    )
    duplicate_run_condition_payload["run_allocation"]["condition_assignments"]["candidate"]["condition_id"] = (
        "candidate"
    )
    duplicate_run_condition_payload["run_allocation"]["condition_assignments"]["candidate"]["factor_levels"][
        "participant-policy"
    ] = "candidate"
    duplicate_run_condition_payload["run_allocation"]["condition_assignments"]["candidate"]["required_refs"][0][
        "ref_id"
    ] = "candidate-policy"
    duplicate_run_condition_payload["membership"]["run-001-candidate"] = deepcopy(
        duplicate_run_condition_payload["membership"]["run-001"]
    )
    duplicate_run_condition_payload["membership"]["run-001-candidate"]["grouping"] = "candidate"
    duplicate_run_condition_study = ExperimentStudyModel.model_validate(duplicate_run_condition_payload)
    with pytest.raises(ValueError, match="same run"):
        validate_experiment_study_against_tasks_and_runs(duplicate_run_condition_study, [task], [run])

    invalidated_run_payload = _experiment_fixture("experiment-run-v1")
    invalidated_run_payload["run_status"] = "invalidated"
    invalidated_run_payload["invalidation"] = {
        "invalidated_at": "2026-05-26T00:41:00Z",
        "reason": "Apparatus drift invalidated the run for study analysis.",
    }
    with pytest.raises(ValueError, match="invalidated"):
        validate_experiment_study_against_tasks_and_runs(
            study,
            [task],
            [ExperimentRunModel.model_validate(invalidated_run_payload)],
        )

    collection_analysis_payload = deepcopy(study_payload)
    collection_analysis_payload["study_kind"] = "collection"
    del collection_analysis_payload["run_allocation"]
    collection_analysis_study = ExperimentStudyModel.model_validate(collection_analysis_payload)
    with pytest.raises(ValueError, match="invalidated"):
        validate_experiment_study_against_tasks_and_runs(
            collection_analysis_study,
            [task],
            [ExperimentRunModel.model_validate(invalidated_run_payload)],
        )


def test_experiment_core_rejects_untyped_task_and_study_relationships():
    task_payload = _experiment_fixture("experiment-task-v1")
    task_payload["apparatus_constraints"]["allowed_processor_refs"][0]["ref_kind"] = "manifest"
    _assert_schema_and_model_reject("experiment-task-v1", task_payload)

    processor_without_matching_manifest = _experiment_fixture("experiment-task-v1")
    processor_without_matching_manifest["apparatus_constraints"]["allowed_processor_refs"][0]["ref_id"] = (
        "different-processor"
    )
    with pytest.raises(ValidationError):
        ExperimentTaskModel.model_validate(processor_without_matching_manifest)

    metric_key_mismatch = _experiment_fixture("experiment-task-v1")
    metric_key_mismatch["evaluation_protocol"]["metric_definitions"]["foothold-achieved"]["metric_id"] = (
        "different-metric"
    )
    with pytest.raises(ValidationError):
        ExperimentTaskModel.model_validate(metric_key_mismatch)

    study_payload = _experiment_fixture("experiment-study-v1")
    study_payload["membership"]["run-001"]["target_ref"]["ref_kind"] = "task"
    _assert_schema_and_model_reject("experiment-study-v1", study_payload)

    study_without_analysis = _experiment_fixture("experiment-study-v1")
    del study_without_analysis["analysis_plan"]
    _assert_schema_and_model_reject("experiment-study-v1", study_without_analysis)

    study_without_validity_notes = _experiment_fixture("experiment-study-v1")
    study_without_validity_notes["validity_notes"] = []
    _assert_schema_and_model_reject("experiment-study-v1", study_without_validity_notes)

    analysis_without_methods = _experiment_fixture("experiment-study-v1")
    analysis_without_methods["analysis_plan"] = {
        "analysis_id": "baseline-proportion",
        "description": "Under-specified analysis plan.",
    }
    _assert_schema_and_model_reject("experiment-study-v1", analysis_without_methods)

    apparatus_payload = _experiment_fixture("experiment-apparatus-context-v1")
    apparatus_payload["components"]["processor"]["manifest_ref"]["ref_id"] = "unselected-processor"
    with pytest.raises(ValidationError):
        ExperimentApparatusContextModel.model_validate(apparatus_payload)

    apparatus_subject_mismatch = _experiment_fixture("experiment-apparatus-context-v1")
    apparatus_subject_mismatch["components"]["processor"]["manifest_ref"]["subject_ref"]["ref_version"] = "9.9.9"
    with pytest.raises(ValidationError):
        ExperimentApparatusContextModel.model_validate(apparatus_subject_mismatch)

    analysis_primary_metric_mismatch = _experiment_fixture("experiment-study-v1")
    analysis_primary_metric_mismatch["analysis_plan"]["primary_metric"] = "undeclared-metric"
    with pytest.raises(ValidationError):
        ExperimentStudyModel.model_validate(analysis_primary_metric_mismatch)


def test_experiment_core_accepts_rfc3339_leap_second_datetimes():
    payload = _experiment_fixture("experiment-run-v1")
    payload["started_at"] = "2016-12-31t23:59:60z"
    payload["ended_at"] = "2017-01-01t00:00:00z"
    payload["evidence_artifacts"][0]["created_at"] = "2016-12-31t23:59:60z"

    schema = schema_bundle()["experiment-run-v1"]
    assert not list(Draft202012Validator(schema).iter_errors(payload))
    validate_experiment_run_archival_datetimes(payload)
    model = ExperimentRunModel.model_validate(payload)
    assert model.started_at == "2016-12-31t23:59:60z"


def test_experiment_core_rejects_invalid_rfc3339_leap_second_datetimes():
    payload = _experiment_fixture("experiment-run-v1")
    payload["started_at"] = "2026-05-26t00:00:60z"

    with pytest.raises(ValidationError):
        ExperimentRunModel.model_validate(payload)


def test_experiment_core_publishes_callable_rfc3339_semantic_invariants_for_artifacts():
    payload = _experiment_fixture("experiment-run-v1")
    payload["evidence_artifacts"][0]["created_at"] = "2026-05-26T00:00:60Z"
    schema = schema_bundle()["experiment-run-v1"]

    assert "run-archival-times-rfc3339-valid" in _invariant_ids(schema)
    assert not list(Draft202012Validator(schema).iter_errors(payload))
    with pytest.raises(ValueError, match="leap-second"):
        validate_experiment_run_archival_datetimes(payload)
    with pytest.raises(ValidationError):
        ExperimentRunModel.model_validate(payload)


def test_sdl_schema_rejects_redacted_runtime_mount_and_bind_raw_values():
    validator = Draft202012Validator(schema_bundle()["sdl-authoring-input-v1"])

    validator.validate(
        {
            "name": "redaction-contract",
            "nodes": {
                "n": {
                    "type": "vm",
                    "runtime": {
                        "mounts": [{"target": "/host-keys", "source_sensitivity": "operator_secret"}],
                        "local_control_interfaces": [
                            {"path": "/run/docker.sock", "bind_source_sensitivity": "operator_secret"}
                        ],
                    },
                }
            },
        }
    )

    invalid_mount_options = {
        "name": "redaction-contract",
        "nodes": {
            "n": {
                "type": "vm",
                "runtime": {
                    "mounts": [
                        {
                            "target": "/",
                            "options": ["lowerdir=/var/lib/containerd/snapshots/1/fs"],
                            "options_sensitivity": "redacted",
                        }
                    ]
                },
            }
        },
    }
    invalid_bind_source = {
        "name": "redaction-contract",
        "nodes": {
            "n": {
                "type": "vm",
                "runtime": {
                    "local_control_interfaces": [
                        {
                            "path": "/run/docker.sock",
                            "bind_source": "/var/run/docker.sock",
                            "bind_source_sensitivity": "operator_secret",
                        }
                    ]
                },
            }
        },
    }

    for sensitivity in (
        "operator_secret",
        "operator-secret",
        "OPERATOR_SECRET",
        "OPERATOR-SECRET",
        "Operator-Secret",
        "redacted",
        "REDACTED",
    ):
        invalid_mount_source = {
            "name": "redaction-contract",
            "nodes": {
                "n": {
                    "type": "vm",
                    "runtime": {
                        "mounts": [
                            {
                                "target": "/host-keys",
                                "source": "/home/operator/.ssh",
                                "source_sensitivity": sensitivity,
                            }
                        ]
                    },
                }
            },
        }
        assert list(validator.iter_errors(invalid_mount_source)), sensitivity

    assert list(validator.iter_errors(invalid_mount_options))
    assert list(validator.iter_errors(invalid_bind_source))


def test_manifest_schemas_publish_backend_and_processor_v2_with_surface_specific_constraints():
    generated = schema_bundle()
    backend_v2_compatibility = generated["backend-manifest-v2"]["$defs"]["BackendCompatibilityModel"]
    backend_v2_realization = generated["backend-manifest-v2"]["$defs"]["RealizationSupportDeclarationModel"]
    processor_v2_compatibility = generated["processor-manifest-v2"]["$defs"]["ProcessorCompatibilityModel"]
    processor_v2_caps = generated["processor-manifest-v2"]["$defs"]["ProcessorCapabilitiesV2Model"]

    assert generated["backend-manifest-v2"]["properties"]["identity"]["$ref"] == "#/$defs/ApparatusIdentityModel"
    assert (
        generated["backend-manifest-v2"]["properties"]["compatibility"]["$ref"] == "#/$defs/BackendCompatibilityModel"
    )
    assert generated["backend-manifest-v2"]["properties"]["realization_support"]["items"]["$ref"] == (
        "#/$defs/RealizationSupportDeclarationModel"
    )
    assert generated["backend-manifest-v2"]["properties"]["supported_contract_versions"]["minItems"] == 1
    assert generated["backend-manifest-v2"]["properties"]["supported_contract_versions"]["items"]["enum"] == list(
        BACKEND_SUPPORTED_CONTRACT_IDS
    )
    assert generated["backend-manifest-v2"]["properties"]["realization_support"]["minItems"] == 1
    assert backend_v2_compatibility["required"] == ["processors"]
    assert backend_v2_compatibility["properties"]["processors"]["minItems"] == 1
    assert "backends" not in backend_v2_compatibility["properties"]
    assert "participant_implementations" not in backend_v2_compatibility["properties"]
    assert backend_v2_realization["properties"]["disclosure_kinds"]["minItems"] == 1
    assert backend_v2_realization["allOf"] == [
        {
            "anyOf": [
                {
                    "required": ["supported_constraint_kinds"],
                    "properties": {"supported_constraint_kinds": {"minItems": 1}},
                },
                {
                    "required": ["supported_exact_requirement_kinds"],
                    "properties": {"supported_exact_requirement_kinds": {"minItems": 1}},
                },
            ]
        },
        {
            "if": {
                "properties": {"support_mode": {"const": "exact-only"}},
                "required": ["support_mode"],
            },
            "then": {
                "required": ["supported_exact_requirement_kinds"],
                "properties": {
                    "supported_constraint_kinds": {"maxItems": 0},
                    "supported_exact_requirement_kinds": {"minItems": 1},
                },
            },
        },
    ]
    assert generated["backend-manifest-v2"]["required"] == [
        "identity",
        "supported_contract_versions",
        "compatibility",
        "realization_support",
        "concept_bindings",
        "capabilities",
    ]
    assert generated["processor-manifest-v2"]["properties"]["identity"]["$ref"] == "#/$defs/ApparatusIdentityModel"
    assert (
        generated["processor-manifest-v2"]["properties"]["compatibility"]["$ref"]
        == "#/$defs/ProcessorCompatibilityModel"
    )
    assert generated["processor-manifest-v2"]["properties"]["supported_contract_versions"]["minItems"] == 1
    assert generated["processor-manifest-v2"]["properties"]["supported_contract_versions"]["items"]["enum"] == list(
        PROCESSOR_SUPPORTED_CONTRACT_IDS
    )
    assert "realization_support" not in generated["processor-manifest-v2"]["properties"]
    assert processor_v2_compatibility["properties"]["backends"]["minItems"] == 1
    assert processor_v2_compatibility["required"] == ["backends"]
    assert "processors" not in processor_v2_compatibility["properties"]
    assert "participant_implementations" not in processor_v2_compatibility["properties"]
    assert processor_v2_caps["properties"]["supported_sdl_versions"]["minItems"] == 1
    assert processor_v2_caps["properties"]["supported_sdl_versions"]["items"]["enum"] == list(
        PROCESSOR_SUPPORTED_SDL_VERSION_IDS
    )
    assert processor_v2_caps["properties"]["supported_features"]["minItems"] == 1
    assert processor_v2_caps["required"] == ["supported_sdl_versions", "supported_features"]
    assert generated["processor-manifest-v2"]["required"] == [
        "identity",
        "supported_contract_versions",
        "compatibility",
        "concept_bindings",
        "capabilities",
    ]


def test_concept_binding_schema_in_v2_manifests():
    generated = schema_bundle()

    for schema_name in ("backend-manifest-v2", "processor-manifest-v2"):
        schema = generated[schema_name]
        assert "concept_bindings" in schema["properties"], f"{schema_name} should have concept_bindings"
        assert "concept_bindings" in schema["required"], f"{schema_name} should require concept_bindings"
        bindings_prop = schema["properties"]["concept_bindings"]
        assert bindings_prop["type"] == "array"
        assert bindings_prop["minItems"] == 1
        assert "$ref" in bindings_prop["items"]
        assert "ConceptBindingEntryModel" in bindings_prop["items"]["$ref"]

    binding_def = generated["backend-manifest-v2"]["$defs"]["ConceptBindingEntryModel"]
    assert binding_def["additionalProperties"] is False
    assert "scope" in binding_def["properties"]
    assert "family" in binding_def["properties"]
    assert binding_def["properties"]["scope"]["pattern"]
    assert binding_def["properties"]["family"]["pattern"]


def test_concept_authority_schema_enforces_keyed_catalog_and_provenance_rules():
    generated = schema_bundle()
    concept_catalog = generated["concept-families-v1"]
    family_definition = concept_catalog["$defs"]["ConceptFamilyDefinitionModel"]
    provenance_rules = {
        rule["if"]["properties"]["provenance"]["const"]: rule["then"] for rule in family_definition["allOf"]
    }

    assert concept_catalog["properties"]["families"]["type"] == "object"
    assert concept_catalog["properties"]["families"]["minProperties"] == 1
    assert concept_catalog["properties"]["families"]["propertyNames"] == {"minLength": 1}
    assert (
        concept_catalog["properties"]["families"]["additionalProperties"]["$ref"]
        == "#/$defs/ConceptFamilyDefinitionModel"
    )
    assert family_definition["properties"]["title"]["minLength"] == 1
    assert family_definition["properties"]["description"]["minLength"] == 1
    assert provenance_rules["adopted"]["required"] == ["authority", "authority_reference"]
    assert provenance_rules["adopted"]["properties"]["authority"] == {"type": "string", "minLength": 1}
    assert provenance_rules["adopted"]["properties"]["authority_reference"] == {"type": "string", "minLength": 1}
    assert provenance_rules["adapted"]["required"] == ["authority", "authority_reference"]
    assert provenance_rules["adapted"]["properties"]["authority"] == {"type": "string", "minLength": 1}
    assert provenance_rules["adapted"]["properties"]["authority_reference"] == {"type": "string", "minLength": 1}
    assert provenance_rules["native"]["required"] == [
        "extension_scope",
        "relation_rules",
        "non_ambiguity_constraints",
    ]
    assert provenance_rules["native"]["properties"]["extension_scope"] == {"type": "string", "minLength": 1}
    assert provenance_rules["native"]["properties"]["relation_rules"] == {"type": "array", "minItems": 1}
    assert provenance_rules["native"]["properties"]["non_ambiguity_constraints"] == {
        "type": "array",
        "minItems": 1,
    }
    assert provenance_rules["native"]["not"]["anyOf"] == [
        {"required": ["authority"]},
        {"required": ["authority_reference"]},
    ]


def test_semantic_profile_schema_publishes_phase_assumptions():
    generated = schema_bundle()
    semantic_profile = generated["semantic-profile-v1"]
    phase_definition = semantic_profile["$defs"]["SemanticProfilePhaseModel"]
    assumption_definition = semantic_profile["$defs"]["SemanticBehaviorAssumptionModel"]

    assert semantic_profile["properties"]["profile_id"]["pattern"]
    assert semantic_profile["properties"]["concept_catalog_version"]["const"] == "concept-families/v1"
    assert semantic_profile["required"] == [
        "profile_id",
        "title",
        "description",
        "concept_catalog_version",
        "authoring",
        "exchange",
        "processing",
        "execution",
    ]
    assert phase_definition["properties"]["required_contracts"]["minItems"] == 1
    assert phase_definition["properties"]["required_concept_families"]["minItems"] == 1
    assert phase_definition["properties"]["required_bindings"]["type"] == "array"
    assert phase_definition["properties"]["behavior_assumptions"]["minItems"] == 1
    assert assumption_definition["properties"]["id"]["pattern"]
    assert assumption_definition["properties"]["statement"]["minLength"] == 1


def test_reference_model_schema_publishes_catalog():
    generated = schema_bundle()
    reference_models = generated["reference-models-v1"]
    model_definition = reference_models["$defs"]["ReferenceModelDefinitionModel"]
    schema_binding_definition = reference_models["$defs"]["ReferenceModelSchemaBindingModel"]

    assert reference_models["properties"]["models"]["type"] == "object"
    assert reference_models["properties"]["models"]["minProperties"] == 1
    assert reference_models["properties"]["models"]["propertyNames"] == {"minLength": 1}
    assert reference_models["properties"]["models"]["additionalProperties"]["$ref"] == (
        "#/$defs/ReferenceModelDefinitionModel"
    )
    assert reference_models["required"] == ["models"]
    assert model_definition["required"] == [
        "title",
        "description",
        "concept_family",
        "authoritative_schema",
        "key_fields",
    ]
    assert model_definition["properties"]["key_fields"]["minItems"] == 1
    assert schema_binding_definition["required"] == ["contract_id", "schema_pointer", "instance_path"]
    assert schema_binding_definition["properties"]["schema_pointer"]["pattern"]
    assert schema_binding_definition["properties"]["instance_path"]["pattern"]


def test_controlled_vocabulary_schema_publishes_catalog():
    generated = schema_bundle()
    controlled_vocabularies = generated["controlled-vocabularies-v1"]
    vocabulary_definition = controlled_vocabularies["$defs"]["ControlledVocabularyDefinitionModel"]
    term_definition = controlled_vocabularies["$defs"]["ControlledVocabularyTermModel"]

    assert controlled_vocabularies["properties"]["vocabularies"]["type"] == "object"
    assert controlled_vocabularies["properties"]["vocabularies"]["minProperties"] == 1
    assert controlled_vocabularies["properties"]["vocabularies"]["propertyNames"] == {"minLength": 1}
    assert controlled_vocabularies["properties"]["vocabularies"]["additionalProperties"]["$ref"] == (
        "#/$defs/ControlledVocabularyDefinitionModel"
    )
    assert controlled_vocabularies["required"] == ["vocabularies"]
    assert vocabulary_definition["required"] == [
        "title",
        "description",
        "kind",
        "extension_policy",
        "terms",
    ]
    assert vocabulary_definition["properties"]["governed_scopes"]["type"] == "array"
    assert vocabulary_definition["properties"]["terms"]["minProperties"] == 1
    assert term_definition["required"] == ["title", "description"]
