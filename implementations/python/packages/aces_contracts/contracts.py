"""Schema-first external contract models for ACES artifact boundaries."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from aces_sdl.participant_attribution_semantics import (
    ParticipantAttributionCandidateKind,
    ParticipantAttributionOrderingBasisKind,
    ParticipantAttributionSupportClass,
)
from aces_sdl.participant_behavior import (
    ParticipantEffectClass,
    ParticipantFailureClass,
    ParticipantInteractionClass,
    ParticipantPreconditionClass,
)
from aces_sdl.participant_outcome_semantics import (
    OutcomeInterpretationSourceLayer,
    OutcomeInterpretationTargetLayer,
)
from aces_sdl.participant_temporal_semantics import (
    ParticipantTemporalEventPoint,
    ParticipantTimeDomain,
)
from aces_sdl.scenario import InstantiatedScenario, Scenario
from pydantic import BaseModel, ConfigDict, Field, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from .manifest_authority import (
    BACKEND_SUPPORTED_CONTRACT_IDS,
    PROCESSOR_SUPPORTED_CONTRACT_IDS,
    PROCESSOR_SUPPORTED_SDL_VERSION_IDS,
    validate_backend_supported_contract_versions,
    validate_processor_supported_contract_versions,
    validate_processor_supported_sdl_versions,
)
from .versions import (
    BACKEND_MANIFEST_V2_SCHEMA_VERSION,
    CONCEPT_FAMILIES_SCHEMA_VERSION,
    CONTROLLED_VOCABULARIES_SCHEMA_VERSION,
    EVALUATION_STATE_SCHEMA_VERSION,
    EXPERIMENT_APPARATUS_CONTEXT_SCHEMA_VERSION,
    EXPERIMENT_RUN_SCHEMA_VERSION,
    EXPERIMENT_STUDY_SCHEMA_VERSION,
    EXPERIMENT_TASK_SCHEMA_VERSION,
    OPERATION_SCHEMA_VERSION,
    PARTICIPANT_EPISODE_STATE_SCHEMA_VERSION,
    PROCESSOR_MANIFEST_V2_SCHEMA_VERSION,
    REFERENCE_MODELS_SCHEMA_VERSION,
    RUNTIME_SNAPSHOT_SCHEMA_VERSION,
    SCENARIO_INSTANTIATION_REQUEST_SCHEMA_VERSION,
    SEMANTIC_PROFILE_SCHEMA_VERSION,
    WORKFLOW_CANCELLATION_REQUEST_SCHEMA_VERSION,
    WORKFLOW_STATE_SCHEMA_VERSION,
)
from .vocabulary import (
    ConceptFamilyId,
    ConceptProvenanceCategory,
    ProcessorFeature,
    RealizationSupportMode,
    WorkflowFeature,
    WorkflowStatePredicateFeature,
)


class ContractModel(BaseModel):
    """Base model for closed-world external contracts."""

    model_config = ConfigDict(extra="forbid")


NonEmptyString = Annotated[str, Field(min_length=1)]
Rfc3339DateTimeString = Annotated[
    str,
    Field(
        min_length=1,
        pattern=(
            r"^\d{4}-\d{2}-\d{2}[Tt](?:[01]\d|2[0-3]):[0-5]\d:(?:[0-5]\d|60)"
            r"(?:\.\d+)?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
        ),
        json_schema_extra={"format": "date-time"},
    ),
]
HexDigestString = Annotated[str, Field(min_length=1, pattern=r"^[A-Fa-f0-9]+$")]
PrefixedDigestString = Annotated[
    str,
    Field(
        min_length=1,
        pattern=(
            r"^(?:sha256:[A-Fa-f0-9]{64}|sha384:[A-Fa-f0-9]{96}|"
            r"sha512:[A-Fa-f0-9]{128}|blake3:[A-Fa-f0-9]{64})$"
        ),
    ),
]
NonNegativeInteger = Annotated[int, Field(ge=0)]
PositiveInteger = Annotated[int, Field(ge=1)]
UnitIntervalFloat = Annotated[float, Field(gt=0, le=1)]
SemanticProfileId = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*-v[0-9]+$")]
SemanticAssumptionId = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
ReferenceModelId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")]
JsonPointerString = Annotated[str, Field(pattern=r"^#(?:/[A-Za-z0-9_.$~-]+)+$")]
JsonInstancePathString = Annotated[str, Field(pattern=r"^#(?:/[A-Za-z0-9_.$~-]+)*$")]
InstancePath = Annotated[str, Field(pattern=r"^[a-z_][a-z0-9_]*(?:\.(?:[a-z_][a-z0-9_]*|\*))*$")]
ControlledVocabularyTermId = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")]

_BACKEND_CONCEPT_BINDING_SCOPES = frozenset(
    {
        "capabilities.provisioner.supported_node_types",
        "capabilities.provisioner.supported_os_families",
        "capabilities.provisioner.supported_content_types",
        "capabilities.provisioner.supported_account_features",
        "capabilities.orchestrator.supported_sections",
        "capabilities.evaluator.supported_sections",
        "capabilities.participant_runtime.supported_participant_roles",
        "capabilities.participant_runtime.supported_behavior_features",
        "capabilities.participant_runtime.supported_interaction_features",
    }
)

_PROCESSOR_CONCEPT_BINDING_SCOPES = frozenset(
    {
        "capabilities.supported_sdl_versions",
        "capabilities.supported_features",
    }
)

_CONTROLLED_VOCABULARY_GOVERNED_SCOPES = frozenset(
    {
        "capabilities.supported_features",
        "capabilities.orchestrator.supported_workflow_features",
        "capabilities.orchestrator.supported_workflow_state_predicates",
        *_BACKEND_CONCEPT_BINDING_SCOPES,
    }
)

_CHECKSUM_VALUE_PATTERNS = {
    "sha256": r"^[A-Fa-f0-9]{64}$",
    "sha384": r"^[A-Fa-f0-9]{96}$",
    "sha512": r"^[A-Fa-f0-9]{128}$",
    "blake3": r"^[A-Fa-f0-9]{64}$",
}

_RFC3339_DATETIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt](?:[01]\d|2[0-3]):[0-5]\d:(?P<second>[0-5]\d|60)"
    r"(?:\.\d+)?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)
_VALID_UTC_LEAP_SECOND_DATES = frozenset(
    {
        (1972, 6, 30),
        (1972, 12, 31),
        (1973, 12, 31),
        (1974, 12, 31),
        (1975, 12, 31),
        (1976, 12, 31),
        (1977, 12, 31),
        (1978, 12, 31),
        (1979, 12, 31),
        (1981, 6, 30),
        (1982, 6, 30),
        (1983, 6, 30),
        (1985, 6, 30),
        (1987, 12, 31),
        (1989, 12, 31),
        (1990, 12, 31),
        (1992, 6, 30),
        (1993, 6, 30),
        (1994, 6, 30),
        (1995, 12, 31),
        (1997, 6, 30),
        (1998, 12, 31),
        (2005, 12, 31),
        (2008, 12, 31),
        (2012, 6, 30),
        (2015, 6, 30),
        (2016, 12, 31),
    }
)

_ACES_SEMANTIC_INVARIANT_PROFILE_URI = "https://aces.dev/schemas/semantic-invariants/v1"


def _canonical_digest(digest: str | None) -> str | None:
    return digest.casefold() if digest is not None else None


def _parse_rfc3339_datetime(field_name: str, value: str) -> datetime:
    match = _RFC3339_DATETIME_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(f"{field_name} must be a valid RFC 3339 date-time")
    normalized_value = f"{value[:-1]}+00:00" if value.endswith(("Z", "z")) else value
    if match.group("second") == "60":
        normalized_value = f"{normalized_value[:17]}59{normalized_value[19:]}"
    try:
        parsed = datetime.fromisoformat(normalized_value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid RFC 3339 date-time") from exc
    if match.group("second") == "60":
        utc_leap_second = parsed.astimezone(UTC)
        if (
            (utc_leap_second.year, utc_leap_second.month, utc_leap_second.day) not in _VALID_UTC_LEAP_SECOND_DATES
            or utc_leap_second.hour != 23
            or utc_leap_second.minute != 59
            or utc_leap_second.second != 59
        ):
            raise ValueError(f"{field_name} must use a valid RFC 3339 leap-second instant")
        parsed += timedelta(seconds=1)
    return parsed


def _payload_get(payload: Any, field_name: str) -> Any:
    if isinstance(payload, Mapping):
        return payload.get(field_name)
    return getattr(payload, field_name, None)


def _validate_rfc3339_payload_field(payload: Any, field_name: str) -> None:
    value = _payload_get(payload, field_name)
    if value is not None:
        _parse_rfc3339_datetime(field_name, value)


def _validate_artifact_collection_created_at(field_name: str, artifacts: Any) -> None:
    for index, artifact in enumerate(artifacts or []):
        created_at = _payload_get(artifact, "created_at")
        if created_at is not None:
            _parse_rfc3339_datetime(f"{field_name}/{index}/created_at", created_at)


def _add_aces_invariant(
    json_schema: JsonSchemaValue,
    invariant_id: str,
    description: str,
    *,
    validator: str,
    inputs: list[dict[str, str]],
) -> None:
    invariants = json_schema.setdefault("x-aces-invariants", [])
    if isinstance(invariants, list):
        invariants.append(
            {
                "id": invariant_id,
                "description": description,
                "level": "error",
                "validator": validator,
                "inputs": inputs,
            }
        )


def _schema_contains_aces_invariants(schema_node: Any) -> bool:
    if isinstance(schema_node, dict):
        if "x-aces-invariants" in schema_node:
            return True
        return any(_schema_contains_aces_invariants(value) for value in schema_node.values())
    if isinstance(schema_node, list):
        return any(_schema_contains_aces_invariants(value) for value in schema_node)
    return False


def _attach_aces_semantic_profile(contract_id: str, json_schema: dict[str, Any]) -> None:
    if _schema_contains_aces_invariants(json_schema):
        json_schema["x-aces-semantic-profile"] = {
            "id": "aces-semantic-invariants-v1",
            "uri": _ACES_SEMANTIC_INVARIANT_PROFILE_URI,
            "contract_id": contract_id,
            "keyword": "x-aces-invariants",
            "required": True,
            "entry_schema_contract_id": "aces-semantic-invariants-v1",
            "entry_schema_pointer": "#/$defs/AcesSemanticInvariantEntryModel",
        }


def _attach_experiment_datetime_invariants(contract_id: str, json_schema: dict[str, Any]) -> None:
    invariant_by_contract = {
        "experiment-task-v1": (
            "task-archival-times-rfc3339-valid",
            "Task artifact_refs created_at values must be valid RFC 3339 date-times, including only known "
            "valid UTC leap-second instants.",
            "aces_contracts.contracts.validate_experiment_task_archival_datetimes",
            [{"contract_id": "experiment-task-v1", "instance_path": "#/artifact_refs"}],
        ),
        "experiment-apparatus-context-v1": (
            "apparatus-archival-times-rfc3339-valid",
            "Apparatus declared_at and observed_setup_evidence created_at values must be valid RFC 3339 "
            "date-times, including only known valid UTC leap-second instants.",
            "aces_contracts.contracts.validate_experiment_apparatus_context_archival_datetimes",
            [
                {"contract_id": "experiment-apparatus-context-v1", "instance_path": "#/declared_at"},
                {"contract_id": "experiment-apparatus-context-v1", "instance_path": "#/observed_setup_evidence"},
            ],
        ),
        "experiment-run-v1": (
            "run-archival-times-rfc3339-valid",
            "Run started_at, ended_at, invalidation invalidated_at, and evidence_artifacts created_at values "
            "must be valid RFC 3339 date-times, including only known valid UTC leap-second instants.",
            "aces_contracts.contracts.validate_experiment_run_archival_datetimes",
            [
                {"contract_id": "experiment-run-v1", "instance_path": "#/started_at"},
                {"contract_id": "experiment-run-v1", "instance_path": "#/ended_at"},
                {"contract_id": "experiment-run-v1", "instance_path": "#/invalidation"},
                {"contract_id": "experiment-run-v1", "instance_path": "#/evidence_artifacts"},
            ],
        ),
        "experiment-study-v1": (
            "study-archival-times-rfc3339-valid",
            "Study report_artifacts and export_artifacts created_at values must be valid RFC 3339 date-times, "
            "including only known valid UTC leap-second instants.",
            "aces_contracts.contracts.validate_experiment_study_archival_datetimes",
            [
                {"contract_id": "experiment-study-v1", "instance_path": "#/report_artifacts"},
                {"contract_id": "experiment-study-v1", "instance_path": "#/export_artifacts"},
            ],
        ),
    }
    invariant = invariant_by_contract.get(contract_id)
    if invariant is None:
        return
    invariant_id, description, validator, inputs = invariant
    _add_aces_invariant(
        json_schema,
        invariant_id,
        description,
        validator=validator,
        inputs=inputs,
    )


def _schema_id_for_contract_id(contract_id: str) -> str:
    if contract_id == "aces-semantic-invariants-v1":
        return _ACES_SEMANTIC_INVARIANT_PROFILE_URI
    return f"https://aces.dev/schemas/{contract_id}.json"


def _attach_json_schema_metadata(contract_id: str, json_schema: dict[str, Any]) -> None:
    json_schema.setdefault("$schema", _JSON_SCHEMA_DRAFT_2020_12)
    json_schema.setdefault("$id", _schema_id_for_contract_id(contract_id))


_SEMANTIC_PROFILE_PHASE_ALLOWED_BINDING_SCOPES = {
    "authoring": frozenset(),
    "exchange": frozenset(),
    "processing": _PROCESSOR_CONCEPT_BINDING_SCOPES,
    "execution": _BACKEND_CONCEPT_BINDING_SCOPES,
}

_JSON_SCHEMA_KEY = "$schema"
_JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
_ACES_SEMANTIC_INVARIANTS_SCHEMA_VERSION = "aces-semantic-invariants/v1"


class AcesSemanticInvariantInputModel(ContractModel):
    """Input contract and instance path required by one ACES semantic invariant."""

    contract_id: NonEmptyString
    instance_path: JsonInstancePathString


class AcesSemanticInvariantEntryModel(ContractModel):
    """Machine-readable semantic invariant annotation entry."""

    id: NonEmptyString
    description: NonEmptyString
    level: Literal["error"]
    validator: NonEmptyString
    inputs: list[AcesSemanticInvariantInputModel] = Field(min_length=1)


class AcesSemanticInvariantProfileModel(ContractModel):
    """Published shape for ACES semantic-invariant annotations."""

    schema_version: Literal[_ACES_SEMANTIC_INVARIANTS_SCHEMA_VERSION]
    profile_id: Literal["aces-semantic-invariants-v1"]
    uri: Literal["https://aces.dev/schemas/semantic-invariants/v1"]
    keyword: Literal["x-aces-invariants"]
    invariant_entry_schema: Literal["#/$defs/AcesSemanticInvariantEntryModel"]
    profile_reference_schema: Literal["#/$defs/AcesSemanticInvariantProfileReferenceModel"]
    invariants: list[AcesSemanticInvariantEntryModel]


class AcesSemanticInvariantProfileReferenceModel(ContractModel):
    """Host-schema reference to the ACES semantic-invariant profile."""

    id: Literal["aces-semantic-invariants-v1"]
    uri: Literal["https://aces.dev/schemas/semantic-invariants/v1"]
    contract_id: NonEmptyString
    keyword: Literal["x-aces-invariants"]
    required: Literal[True]
    entry_schema_contract_id: Literal["aces-semantic-invariants-v1"]
    entry_schema_pointer: Literal["#/$defs/AcesSemanticInvariantEntryModel"]


def _aces_semantic_invariant_profile_schema_for_bundle() -> dict[str, Any]:
    json_schema = AcesSemanticInvariantProfileModel.model_json_schema()
    json_schema.setdefault("$defs", {})["AcesSemanticInvariantProfileReferenceModel"] = (
        AcesSemanticInvariantProfileReferenceModel.model_json_schema()
    )
    return json_schema


def _iter_aces_semantic_invariant_entries(schema_node: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if isinstance(schema_node, dict):
        invariants = schema_node.get("x-aces-invariants")
        if invariants is not None:
            if not isinstance(invariants, list):
                raise ValueError("x-aces-invariants must be an array")
            entries.extend(invariants)
        for value in schema_node.values():
            entries.extend(_iter_aces_semantic_invariant_entries(value))
    elif isinstance(schema_node, list):
        for value in schema_node:
            entries.extend(_iter_aces_semantic_invariant_entries(value))
    return entries


def _validate_aces_semantic_invariant_annotations(
    *,
    contract_id: str,
    json_schema: dict[str, Any],
    known_contract_ids: frozenset[str],
) -> None:
    invariant_entries = _iter_aces_semantic_invariant_entries(json_schema)
    profile_payload = json_schema.get("x-aces-semantic-profile")
    if not invariant_entries:
        if profile_payload is not None:
            raise ValueError(f"schema '{contract_id}' declares a semantic profile without semantic invariants")
        return

    profile = AcesSemanticInvariantProfileReferenceModel.model_validate(profile_payload)
    if profile.contract_id != contract_id:
        raise ValueError(f"schema '{contract_id}' semantic profile contract_id must match the published contract id")

    seen_invariant_ids: set[str] = set()
    for invariant_payload in invariant_entries:
        invariant = AcesSemanticInvariantEntryModel.model_validate(invariant_payload)
        if invariant.id in seen_invariant_ids:
            raise ValueError(f"schema '{contract_id}' has duplicate semantic invariant id '{invariant.id}'")
        seen_invariant_ids.add(invariant.id)
        for invariant_input in invariant.inputs:
            if invariant_input.contract_id not in known_contract_ids:
                raise ValueError(
                    f"semantic invariant '{invariant.id}' references unknown input contract "
                    f"'{invariant_input.contract_id}'"
                )


def validate_aces_semantic_invariant_annotations(contract_id: str, json_schema: dict[str, Any]) -> None:
    """Validate ACES semantic-invariant metadata on a published JSON Schema."""

    known_contract_ids = frozenset(schema_bundle())
    _validate_aces_semantic_invariant_annotations(
        contract_id=contract_id,
        json_schema=json_schema,
        known_contract_ids=known_contract_ids,
    )


class InstantiationRequestModel(ContractModel):
    schema_version: Literal[SCENARIO_INSTANTIATION_REQUEST_SCHEMA_VERSION] = (
        SCENARIO_INSTANTIATION_REQUEST_SCHEMA_VERSION
    )
    profile: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class WorkflowStepStateModel(ContractModel):
    lifecycle: str
    outcome: str | None = None
    attempts: int


class WorkflowExecutionStateModel(ContractModel):
    state_schema_version: Literal[WORKFLOW_STATE_SCHEMA_VERSION] = WORKFLOW_STATE_SCHEMA_VERSION
    workflow_status: str
    run_id: str
    started_at: str
    updated_at: str
    terminal_reason: str | None = None
    compensation_status: str
    compensation_started_at: str | None = None
    compensation_updated_at: str | None = None
    compensation_failures: list[dict[str, Any]] = Field(default_factory=list)
    steps: dict[str, WorkflowStepStateModel] = Field(default_factory=dict)


class WorkflowHistoryEventModel(ContractModel):
    event_type: str
    timestamp: str
    step_name: str | None = None
    branch_name: str | None = None
    join_step: str | None = None
    outcome: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class WorkflowCancellationRequestModel(ContractModel):
    schema_version: Literal[WORKFLOW_CANCELLATION_REQUEST_SCHEMA_VERSION] = WORKFLOW_CANCELLATION_REQUEST_SCHEMA_VERSION
    run_id: str | None = None
    reason: str = "cancelled by operator"


class EvaluationResultStateModel(ContractModel):
    state_schema_version: Literal[EVALUATION_STATE_SCHEMA_VERSION] = EVALUATION_STATE_SCHEMA_VERSION
    resource_type: str
    run_id: str
    status: str
    observed_at: str
    updated_at: str
    passed: bool | None = None
    score: float | int | None = None
    max_score: int | None = None
    detail: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class EvaluationHistoryEventModel(ContractModel):
    event_type: str
    timestamp: str
    status: str
    passed: bool | None = None
    score: float | int | None = None
    max_score: int | None = None
    detail: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ParticipantEpisodeStateModel(ContractModel):
    state_schema_version: Literal[PARTICIPANT_EPISODE_STATE_SCHEMA_VERSION] = PARTICIPANT_EPISODE_STATE_SCHEMA_VERSION
    participant_address: str
    episode_id: str
    sequence_number: int
    status: str
    terminal_reason: str | None = None
    initialized_at: str
    updated_at: str
    terminated_at: str | None = None
    last_control_action: str
    previous_episode_id: str | None = None


class ParticipantEpisodeHistoryEventModel(ContractModel):
    event_type: str
    timestamp: str
    participant_address: str
    episode_id: str
    sequence_number: int
    terminal_reason: str | None = None
    control_action: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ParticipantObservationDetailsModel(ContractModel):
    visible_refs: list[NonEmptyString] = Field(default_factory=list)
    disclosed_refs: list[NonEmptyString] = Field(default_factory=list)
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)


class ParticipantActionPreconditionResultModel(ContractModel):
    precondition_id: NonEmptyString
    precondition_class: ParticipantPreconditionClass
    status: Literal["satisfied", "unsatisfied", "unresolved"]
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    action_contract_address: NonEmptyString
    observation_point: NonEmptyString
    support_refs: list[NonEmptyString] = Field(default_factory=list)
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    diagnostics: list[NonEmptyString] = Field(default_factory=list)


class ParticipantActionEffectResultModel(ContractModel):
    effect_id: NonEmptyString
    effect_class: ParticipantEffectClass
    description: NonEmptyString
    target_refs: list[NonEmptyString] = Field(default_factory=list)
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    diagnostics: list[NonEmptyString] = Field(default_factory=list)


class ParticipantActionResultModel(ContractModel):
    status: Literal["accepted", "rejected", "withheld", "succeeded", "failed", "partial_success", "unknown"]
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    action_instance_id: NonEmptyString
    action_contract_address: NonEmptyString
    observation_point: NonEmptyString
    preconditions: list[ParticipantActionPreconditionResultModel] = Field(default_factory=list)
    effects: list[ParticipantActionEffectResultModel] = Field(default_factory=list)
    failure_class: ParticipantFailureClass | None = None
    observations: list[NonEmptyString] = Field(default_factory=list)
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    diagnostics: list[NonEmptyString] = Field(default_factory=list)


class ParticipantTemporalRuntimeContextModel(ContractModel):
    temporal_contract_id: NonEmptyString
    time_domain: ParticipantTimeDomain
    clock_authority: NonEmptyString
    event_points: list[ParticipantTemporalEventPoint] = Field(min_length=1)
    observation_point: NonEmptyString
    backend_disclosure_refs: list[NonEmptyString] = Field(default_factory=list)
    reset_boundary: NonEmptyString | None = None
    replay_boundary: NonEmptyString | None = None


class ParticipantAttributionCandidateModel(ContractModel):
    candidate_kind: ParticipantAttributionCandidateKind
    ref: NonEmptyString
    description: NonEmptyString


class ParticipantAttributionOrderingBasisModel(ContractModel):
    basis_kind: ParticipantAttributionOrderingBasisKind
    relation_ref: NonEmptyString
    description: NonEmptyString
    ordered_event_refs: list[NonEmptyString] = Field(default_factory=list)


class ParticipantAttributionEvidenceBasisModel(ContractModel):
    capture_apparatus: NonEmptyString
    granularity: NonEmptyString
    loss_model: NonEmptyString
    redaction_policy: NonEmptyString
    observer_effects: list[NonEmptyString] = Field(min_length=1)


class ParticipantAttributionEdgeModel(ContractModel):
    edge_id: NonEmptyString
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    observation_point: NonEmptyString
    cause_candidate: ParticipantAttributionCandidateModel
    effect_candidate: ParticipantAttributionCandidateModel
    ordering_basis: ParticipantAttributionOrderingBasisModel
    evidence_basis: ParticipantAttributionEvidenceBasisModel
    support_class: ParticipantAttributionSupportClass
    confidence: NonEmptyString
    strength: NonEmptyString
    limitations: list[NonEmptyString] = Field(min_length=1)
    evidence_refs: list[NonEmptyString] = Field(min_length=1)
    interpretation_rule_ref: NonEmptyString | None = None


class ParticipantOutcomeSourceRecordModel(ContractModel):
    source_id: NonEmptyString
    source_layer: OutcomeInterpretationSourceLayer
    ref: NonEmptyString
    observed_value: NonEmptyString
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    provenance_refs: list[NonEmptyString] = Field(default_factory=list)
    diagnostics: list[NonEmptyString] = Field(default_factory=list)


class ParticipantOutcomeTargetRecordModel(ContractModel):
    target_id: NonEmptyString
    target_layer: OutcomeInterpretationTargetLayer
    ref: NonEmptyString
    interpreted_value: NonEmptyString
    evidence_refs: list[NonEmptyString] = Field(min_length=1)
    limitations: list[NonEmptyString] = Field(min_length=1)
    governance_ref: NonEmptyString | None = None
    diagnostics: list[NonEmptyString] = Field(default_factory=list)


class ParticipantOutcomeInterpretationRecordModel(ContractModel):
    interpretation_id: NonEmptyString
    rule_address: NonEmptyString
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    observation_point: NonEmptyString
    source_bindings: list[ParticipantOutcomeSourceRecordModel] = Field(min_length=1)
    target_bindings: list[ParticipantOutcomeTargetRecordModel] = Field(min_length=1)
    evidence_refs: list[NonEmptyString] = Field(min_length=1)
    limitations: list[NonEmptyString] = Field(min_length=1)
    diagnostics: list[NonEmptyString] = Field(default_factory=list)


class ParticipantBehaviorHistoryEventModel(ContractModel):
    event_type: str
    timestamp: str
    participant_address: str
    episode_id: str
    action_instance_id: str
    action_contract_address: str | None = None
    observation_boundary_address: str | None = None
    observation_status: str | None = None
    actor_provenance: str | None = None
    state_transition_kind: str | None = None
    post_state_digest: str | None = None
    joint_action_set_id: str | None = None
    realized_order: int | None = Field(default=None, ge=0)
    interaction_class: ParticipantInteractionClass | None = None
    interaction_ref: str | None = None
    shared_state_refs: list[NonEmptyString] = Field(default_factory=list)
    action_result: ParticipantActionResultModel | None = None
    attribution_edges: list[ParticipantAttributionEdgeModel] = Field(default_factory=list)
    outcome_interpretations: list[ParticipantOutcomeInterpretationRecordModel] = Field(default_factory=list)
    temporal_contexts: list[ParticipantTemporalRuntimeContextModel] = Field(default_factory=list)
    details: ParticipantObservationDetailsModel = Field(default_factory=ParticipantObservationDetailsModel)


class PlanOperationModel(ContractModel):
    action: str
    address: str
    resource_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    ordering_dependencies: list[str] = Field(default_factory=list)
    refresh_dependencies: list[str] = Field(default_factory=list)


class ProvisioningPlanModel(ContractModel):
    operations: list[PlanOperationModel] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)


class OrchestrationPlanModel(ContractModel):
    operations: list[PlanOperationModel] = Field(default_factory=list)
    startup_order: list[str] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)


class EvaluationPlanModel(ContractModel):
    operations: list[PlanOperationModel] = Field(default_factory=list)
    startup_order: list[str] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)


class SnapshotEntryModel(ContractModel):
    address: str
    domain: str
    resource_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    ordering_dependencies: list[str] = Field(default_factory=list)
    refresh_dependencies: list[str] = Field(default_factory=list)
    status: str = "ready"


class RuntimeSnapshotEnvelopeModel(ContractModel):
    """Published envelope for a live runtime snapshot.

    Participant episode surfaces (``participant_episode_results`` and
    ``participant_episode_history``) are both keyed by the stable
    ``participant_address`` of the participant the state/history belongs
    to. SEM-208 participant behavior history is keyed the same way and
    records action, observation, and state-transition events with compiled
    behavior-contract addresses. The episode results map carries the
    currently-live episode state per participant; prior episodes survive only
    through append-only history streams and the ``previous_episode_id`` chain
    on each state.
    """

    schema_version: Literal[RUNTIME_SNAPSHOT_SCHEMA_VERSION] = RUNTIME_SNAPSHOT_SCHEMA_VERSION
    entries: dict[str, SnapshotEntryModel] = Field(default_factory=dict)
    orchestration_results: dict[str, WorkflowExecutionStateModel] = Field(default_factory=dict)
    orchestration_history: dict[str, list[WorkflowHistoryEventModel]] = Field(default_factory=dict)
    evaluation_results: dict[str, EvaluationResultStateModel] = Field(default_factory=dict)
    evaluation_history: dict[str, list[EvaluationHistoryEventModel]] = Field(default_factory=dict)
    participant_episode_results: dict[str, ParticipantEpisodeStateModel] = Field(default_factory=dict)
    participant_episode_history: dict[str, list[ParticipantEpisodeHistoryEventModel]] = Field(default_factory=dict)
    participant_behavior_history: dict[str, list[ParticipantBehaviorHistoryEventModel]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperationReceiptModel(ContractModel):
    schema_version: Literal[OPERATION_SCHEMA_VERSION] = OPERATION_SCHEMA_VERSION
    operation_id: str
    domain: str
    submitted_at: str
    accepted: bool
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)


class OperationStatusModel(ContractModel):
    schema_version: Literal[OPERATION_SCHEMA_VERSION] = OPERATION_SCHEMA_VERSION
    operation_id: str
    domain: str
    state: str
    submitted_at: str
    updated_at: str
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    changed_addresses: list[str] = Field(default_factory=list)


class ProvisionerCapabilitiesModel(ContractModel):
    name: NonEmptyString
    supported_node_types: list[NonEmptyString] = Field(min_length=1)
    supported_os_families: list[NonEmptyString] = Field(min_length=1)
    supported_content_types: list[NonEmptyString] = Field(default_factory=list)
    supported_account_features: list[NonEmptyString] = Field(default_factory=list)
    max_total_nodes: int | None = Field(default=None, gt=0)
    supports_acls: bool = False
    supports_accounts: bool = False
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_account_support(self) -> ProvisionerCapabilitiesModel:
        _validate_controlled_vocabulary_terms(
            "capabilities.provisioner.supported_node_types",
            self.supported_node_types,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.provisioner.supported_os_families",
            self.supported_os_families,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.provisioner.supported_content_types",
            self.supported_content_types,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.provisioner.supported_account_features",
            self.supported_account_features,
        )
        if self.supports_accounts and not self.supported_account_features:
            raise ValueError("provisioners that support accounts must declare supported_account_features")
        if not self.supports_accounts and self.supported_account_features:
            raise ValueError("supported_account_features require supports_accounts=true")
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
                {
                    "if": {
                        "properties": {"supports_accounts": {"const": True}},
                        "required": ["supports_accounts"],
                    },
                    "then": {
                        "required": ["supported_account_features"],
                        "properties": {"supported_account_features": {"minItems": 1}},
                    },
                },
                {
                    "if": {
                        "properties": {"supports_accounts": {"const": False}},
                        "required": ["supports_accounts"],
                    },
                    "then": {
                        "properties": {"supported_account_features": {"maxItems": 0}},
                    },
                },
            ]
        )
        return json_schema


class OrchestratorCapabilitiesModel(ContractModel):
    name: NonEmptyString
    supported_sections: list[NonEmptyString] = Field(min_length=1)
    supports_workflows: bool = False
    supports_condition_refs: bool = True
    supports_inject_bindings: bool = True
    supported_workflow_features: list[WorkflowFeature] = Field(default_factory=list)
    supported_workflow_state_predicates: list[WorkflowStatePredicateFeature] = Field(default_factory=list)
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_workflow_support(self) -> OrchestratorCapabilitiesModel:
        _validate_controlled_vocabulary_terms(
            "capabilities.orchestrator.supported_sections",
            self.supported_sections,
        )
        if self.supports_workflows:
            if "workflows" not in self.supported_sections:
                raise ValueError("orchestrators that support workflows must include 'workflows' in supported_sections")
            if not self.supported_workflow_features:
                raise ValueError("orchestrators that support workflows must declare supported_workflow_features")
        else:
            if "workflows" in self.supported_sections:
                raise ValueError("'workflows' in supported_sections requires supports_workflows=true")
            if self.supported_workflow_features:
                raise ValueError("supported_workflow_features require supports_workflows=true")
            if self.supported_workflow_state_predicates:
                raise ValueError("supported_workflow_state_predicates require supports_workflows=true")
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
                {
                    "if": {
                        "properties": {"supports_workflows": {"const": True}},
                        "required": ["supports_workflows"],
                    },
                    "then": {
                        "required": ["supported_workflow_features", "supported_sections"],
                        "properties": {
                            "supported_workflow_features": {"minItems": 1},
                            "supported_sections": {"contains": {"const": "workflows"}},
                        },
                    },
                },
                {
                    "if": {
                        "properties": {"supports_workflows": {"const": False}},
                        "required": ["supports_workflows"],
                    },
                    "then": {
                        "properties": {
                            "supported_workflow_features": {"maxItems": 0},
                            "supported_workflow_state_predicates": {"maxItems": 0},
                            "supported_sections": {"not": {"contains": {"const": "workflows"}}},
                        },
                    },
                },
            ]
        )
        return json_schema


class EvaluatorCapabilitiesModel(ContractModel):
    name: NonEmptyString
    supported_sections: list[NonEmptyString] = Field(min_length=1)
    supports_scoring: bool = True
    supports_objectives: bool = True
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_evaluator_support(self) -> EvaluatorCapabilitiesModel:
        _validate_controlled_vocabulary_terms(
            "capabilities.evaluator.supported_sections",
            self.supported_sections,
        )
        if not self.supports_scoring and not self.supports_objectives:
            raise ValueError("evaluators must support scoring, objectives, or both")
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
                "not": {
                    "allOf": [
                        {
                            "properties": {"supports_scoring": {"const": False}},
                            "required": ["supports_scoring"],
                        },
                        {
                            "properties": {"supports_objectives": {"const": False}},
                            "required": ["supports_objectives"],
                        },
                    ]
                }
            }
        )
        return json_schema


class ApparatusIdentityModel(ContractModel):
    name: NonEmptyString
    version: NonEmptyString


class BackendCompatibilityModel(ContractModel):
    processors: list[NonEmptyString] = Field(min_length=1)


class ProcessorCompatibilityModel(ContractModel):
    backends: list[NonEmptyString] = Field(min_length=1)


class RealizationSupportDeclarationModel(ContractModel):
    domain: NonEmptyString
    support_mode: RealizationSupportMode
    supported_constraint_kinds: list[NonEmptyString] = Field(default_factory=list)
    supported_exact_requirement_kinds: list[NonEmptyString] = Field(default_factory=list)
    disclosure_kinds: list[NonEmptyString] = Field(min_length=1)
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_realization_support(self) -> RealizationSupportDeclarationModel:
        if not self.supported_constraint_kinds and not self.supported_exact_requirement_kinds:
            raise ValueError(
                "realization_support declarations must declare supported_constraint_kinds "
                "or supported_exact_requirement_kinds"
            )
        if self.support_mode == RealizationSupportMode.EXACT_ONLY and self.supported_constraint_kinds:
            raise ValueError("exact-only realization support must not declare supported_constraint_kinds")
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
                        "properties": {"support_mode": {"const": RealizationSupportMode.EXACT_ONLY.value}},
                        "required": ["support_mode"],
                    },
                    "then": {
                        "required": ["supported_exact_requirement_kinds"],
                        "properties": {
                            "supported_exact_requirement_kinds": {"minItems": 1},
                            "supported_constraint_kinds": {"maxItems": 0},
                        },
                    },
                },
            ]
        )
        return json_schema


class ConceptBindingEntryModel(ContractModel):
    """Binds a vocabulary surface in an artifact to a canonical concept family."""

    scope: NonEmptyString = Field(
        ...,
        pattern=r"^[a-z_][a-z0-9_.]*[a-z0-9_]$",
    )
    family: ConceptFamilyId


class ProcessorCapabilitiesV2Model(ContractModel):
    supported_sdl_versions: list[NonEmptyString] = Field(min_length=1)
    supported_features: list[ProcessorFeature] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_declared_authority(self) -> ProcessorCapabilitiesV2Model:
        validate_processor_supported_sdl_versions(self.supported_sdl_versions)
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema["properties"]["supported_sdl_versions"]["items"]["enum"] = list(PROCESSOR_SUPPORTED_SDL_VERSION_IDS)
        return json_schema


class ParticipantRuntimeCapabilitiesModel(ContractModel):
    """Participant-episode lifecycle capability block (RUN-311).

    A backend that declares this block advertises that it implements
    the full participant episode control surface on the
    ``ParticipantRuntime`` protocol: ``initialize`` / ``reset`` /
    ``restart`` / ``terminate`` plus ``status`` / ``results`` /
    ``history``. Consumers of the manifest can infer the
    ``FULL_REMOTE_CONTROL_PLANE`` conformance profile from this block.

    API-405 support dimensions live here because they are backend apparatus
    claims: which participant roles, behavior features, and interaction
    features this participant runtime can actually realize.
    """

    name: NonEmptyString
    supported_participant_roles: list[NonEmptyString] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    supported_behavior_features: list[NonEmptyString] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    supported_interaction_features: list[NonEmptyString] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    constraints: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_api_405_declarations(self) -> ParticipantRuntimeCapabilitiesModel:
        _validate_unique_string_values("supported_participant_roles", self.supported_participant_roles)
        _validate_unique_string_values("supported_behavior_features", self.supported_behavior_features)
        _validate_unique_string_values("supported_interaction_features", self.supported_interaction_features)
        _validate_controlled_vocabulary_terms(
            "capabilities.participant_runtime.supported_participant_roles",
            self.supported_participant_roles,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.participant_runtime.supported_behavior_features",
            self.supported_behavior_features,
        )
        _validate_controlled_vocabulary_terms(
            "capabilities.participant_runtime.supported_interaction_features",
            self.supported_interaction_features,
        )
        return self


class BackendCapabilitiesV2Model(ContractModel):
    provisioner: ProvisionerCapabilitiesModel
    orchestrator: OrchestratorCapabilitiesModel | None = None
    evaluator: EvaluatorCapabilitiesModel | None = None
    participant_runtime: ParticipantRuntimeCapabilitiesModel | None = None


class ProcessorManifestV2Model(ContractModel):
    schema_version: Literal[PROCESSOR_MANIFEST_V2_SCHEMA_VERSION] = PROCESSOR_MANIFEST_V2_SCHEMA_VERSION
    identity: ApparatusIdentityModel
    supported_contract_versions: list[NonEmptyString] = Field(min_length=1)
    compatibility: ProcessorCompatibilityModel
    concept_bindings: list[ConceptBindingEntryModel] = Field(min_length=1)
    constraints: dict[str, str] = Field(default_factory=dict)
    capabilities: ProcessorCapabilitiesV2Model

    @model_validator(mode="after")
    def _validate_unique_binding_scopes(self) -> ProcessorManifestV2Model:
        validate_processor_supported_contract_versions(self.supported_contract_versions)
        scopes = [binding.scope for binding in self.concept_bindings]
        if len(scopes) != len(set(scopes)):
            raise ValueError("concept_bindings must not contain duplicate scopes")
        _validate_canonical_concept_bindings(self, allowed_scopes=_PROCESSOR_CONCEPT_BINDING_SCOPES)
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema["properties"]["supported_contract_versions"]["items"]["enum"] = list(
            PROCESSOR_SUPPORTED_CONTRACT_IDS
        )
        return json_schema


class BackendManifestV2Model(ContractModel):
    schema_version: Literal[BACKEND_MANIFEST_V2_SCHEMA_VERSION] = BACKEND_MANIFEST_V2_SCHEMA_VERSION
    identity: ApparatusIdentityModel
    supported_contract_versions: list[NonEmptyString] = Field(min_length=1)
    compatibility: BackendCompatibilityModel
    realization_support: list[RealizationSupportDeclarationModel] = Field(min_length=1)
    concept_bindings: list[ConceptBindingEntryModel] = Field(min_length=1)
    constraints: dict[str, str] = Field(default_factory=dict)
    capabilities: BackendCapabilitiesV2Model

    @model_validator(mode="after")
    def _validate_unique_binding_scopes(self) -> BackendManifestV2Model:
        validate_backend_supported_contract_versions(self.supported_contract_versions)
        scopes = [binding.scope for binding in self.concept_bindings]
        if len(scopes) != len(set(scopes)):
            raise ValueError("concept_bindings must not contain duplicate scopes")
        _validate_canonical_concept_bindings(self, allowed_scopes=_BACKEND_CONCEPT_BINDING_SCOPES)
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema["properties"]["supported_contract_versions"]["items"]["enum"] = list(BACKEND_SUPPORTED_CONTRACT_IDS)
        return json_schema


class ExperimentReferenceModel(ContractModel):
    """Typed reference to an experiment-core or adjacent ACES artifact."""

    ref_kind: Literal[
        "processor",
        "backend",
        "participant-implementation",
        "scenario",
        "scenario-snapshot",
        "task",
        "protocol",
        "apparatus-context",
        "run",
        "result",
        "study",
        "manifest",
        "profile",
        "capability",
        "evidence",
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


class ExperimentTaskReferenceModel(ExperimentReferenceModel):
    """Reference constrained to an experiment task."""

    ref_kind: Literal["task"]


class ExperimentScenarioSnapshotReferenceModel(ExperimentReferenceModel):
    """Reference constrained to a sealed scenario snapshot."""

    ref_kind: Literal["scenario-snapshot"]


class ExperimentManifestReferenceModel(ExperimentReferenceModel):
    """Reference constrained to an apparatus or capability manifest."""

    ref_kind: Literal["manifest"]
    subject_ref: ExperimentReferenceModel | None = None


class ExperimentProcessorReferenceModel(ExperimentReferenceModel):
    """Reference constrained to a processor identity."""

    ref_kind: Literal["processor"]


class ExperimentBackendReferenceModel(ExperimentReferenceModel):
    """Reference constrained to a backend identity."""

    ref_kind: Literal["backend"]


class ExperimentEvidenceReferenceModel(ExperimentReferenceModel):
    """Reference constrained to evidence artifacts."""

    ref_kind: Literal["evidence"]


class ExperimentMeasurementChannelReferenceModel(ExperimentReferenceModel):
    """Reference constrained to a declared measurement channel."""

    ref_kind: Literal["measurement-channel"]


class ExperimentConditionAssignmentReferenceModel(ExperimentReferenceModel):
    """Auditable run-level reference that can ground a study condition assignment."""

    ref_kind: Literal[
        "processor",
        "backend",
        "participant-implementation",
        "scenario-snapshot",
        "task",
        "apparatus-context",
        "manifest",
        "profile",
        "capability",
        "measurement-channel",
    ]


def _manifest_reference_key(
    reference: ExperimentManifestReferenceModel,
) -> tuple[str, str | None, str | None, str | None, str | None, str | None, str | None]:
    subject_ref = reference.subject_ref
    return (
        reference.ref_id,
        reference.ref_version,
        _canonical_digest(reference.ref_digest),
        reference.ref_path,
        subject_ref.ref_kind if subject_ref is not None else None,
        subject_ref.ref_id if subject_ref is not None else None,
        subject_ref.ref_version if subject_ref is not None else None,
    )


def _reference_satisfies_requirement(
    candidate: ExperimentReferenceModel, requirement: ExperimentReferenceModel
) -> bool:
    if candidate.ref_kind != requirement.ref_kind or candidate.ref_id != requirement.ref_id:
        return False
    if requirement.ref_version is not None and candidate.ref_version != requirement.ref_version:
        return False
    if requirement.ref_digest is not None and _canonical_digest(candidate.ref_digest) != _canonical_digest(
        requirement.ref_digest
    ):
        return False
    if requirement.ref_path is not None and candidate.ref_path != requirement.ref_path:
        return False

    requirement_subject = getattr(requirement, "subject_ref", None)
    if requirement_subject is None:
        return True
    candidate_subject = getattr(candidate, "subject_ref", None)
    if candidate_subject is None:
        return False
    return _reference_satisfies_requirement(candidate_subject, requirement_subject)


def _reference_identity_satisfies_requirement(
    candidate: ExperimentReferenceModel, requirement: ExperimentReferenceModel
) -> bool:
    if candidate.ref_kind != requirement.ref_kind or candidate.ref_id != requirement.ref_id:
        return False
    if requirement.ref_version is not None and candidate.ref_version != requirement.ref_version:
        return False

    requirement_subject = getattr(requirement, "subject_ref", None)
    if requirement_subject is None:
        return True
    candidate_subject = getattr(candidate, "subject_ref", None)
    if candidate_subject is None:
        return False
    return _reference_identity_satisfies_requirement(candidate_subject, requirement_subject)


def _identity_matches_reference(identity: ApparatusIdentityModel, reference: ExperimentReferenceModel) -> bool:
    if identity.name != reference.ref_id:
        return False
    return reference.ref_version is None or identity.version == reference.ref_version


def _format_reference(reference: ExperimentReferenceModel) -> str:
    if reference.ref_version is None:
        return f"{reference.ref_kind}:{reference.ref_id}"
    return f"{reference.ref_kind}:{reference.ref_id}@{reference.ref_version}"


class ExperimentChecksumModel(ContractModel):
    """Checksum metadata for an experiment-core artifact reference."""

    algorithm: Literal["sha256", "sha384", "sha512", "blake3"]
    value: HexDigestString

    @model_validator(mode="after")
    def _validate_checksum_length(self) -> ExperimentChecksumModel:
        if re.fullmatch(_CHECKSUM_VALUE_PATTERNS[self.algorithm], self.value) is None:
            raise ValueError(f"checksum value must match {self.algorithm} hex digest length")
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
                {
                    "if": {"properties": {"algorithm": {"const": algorithm}}, "required": ["algorithm"]},
                    "then": {"properties": {"value": {"pattern": pattern}}},
                }
                for algorithm, pattern in _CHECKSUM_VALUE_PATTERNS.items()
            ]
        )
        return json_schema


class ExperimentArtifactRefModel(ContractModel):
    """Reference to an artifact that supports a task, run, apparatus, or study."""

    artifact_id: NonEmptyString
    role: Literal[
        "protocol",
        "metric-definition",
        "scenario-snapshot",
        "manifest",
        "apparatus-evidence",
        "observation",
        "result",
        "analysis",
        "report",
        "export",
        "starter-file",
        "evaluator",
        "subtask",
        "gold-step",
        "milestone",
        "human-assistance",
        "scaffold",
        "baseline",
        "cost-resource-trace",
        "other",
    ]
    media_type: NonEmptyString
    uri: NonEmptyString
    checksum: ExperimentChecksumModel
    size_bytes: NonNegativeInteger
    created_at: Rfc3339DateTimeString
    source: NonEmptyString
    satisfies_refs: list[ExperimentEvidenceReferenceModel] = Field(default_factory=list)
    sensitivity: Literal["public", "internal", "restricted", "redacted"] = "internal"
    description: NonEmptyString | None = None

    @model_validator(mode="after")
    def _validate_artifact_created_at(self) -> ExperimentArtifactRefModel:
        _parse_rfc3339_datetime("created_at", self.created_at)
        return self


class ExperimentValidityNoteModel(ContractModel):
    """Validity threat, limitation, or mitigation note for experiment interpretation."""

    category: Literal[
        "construct",
        "internal",
        "external",
        "conclusion",
        "statistical",
        "apparatus",
        "reproducibility",
        "security",
        "other",
    ]
    note: NonEmptyString
    mitigation: NonEmptyString | None = None


class ExperimentMetricDefinitionModel(ContractModel):
    """Metric definition bound to a measured construct and unit of analysis."""

    metric_id: NonEmptyString
    metric_version: NonEmptyString
    name: NonEmptyString
    measured_construct: NonEmptyString
    unit_of_analysis: NonEmptyString
    value_kind: Literal["boolean", "integer", "number", "duration", "count", "category", "text"]
    direction: Literal["higher-is-better", "lower-is-better", "target", "descriptive"]
    aggregation: NonEmptyString | None = None
    missingness_policy: NonEmptyString | None = None
    uncertainty_policy: NonEmptyString | None = None
    evidence_requirements: list[ExperimentEvidenceReferenceModel] = Field(min_length=1)


class ExperimentEvaluationProtocolModel(ContractModel):
    """Evaluation protocol that binds metrics and observation requirements."""

    protocol_id: NonEmptyString
    protocol_version: NonEmptyString
    intent: NonEmptyString
    unit_of_analysis: NonEmptyString
    metric_definitions: dict[NonEmptyString, ExperimentMetricDefinitionModel] = Field(min_length=1)
    observation_requirements: list[ExperimentEvidenceReferenceModel] = Field(min_length=1)
    aggregation_policy: NonEmptyString | None = None
    acceptance_policy: NonEmptyString | None = None

    @model_validator(mode="after")
    def _validate_metric_definition_keys(self) -> ExperimentEvaluationProtocolModel:
        mismatches = [
            metric_key
            for metric_key, definition in self.metric_definitions.items()
            if definition.metric_id != metric_key
        ]
        if mismatches:
            joined = ", ".join(sorted(mismatches))
            raise ValueError(f"metric_definitions keys must match embedded metric_id: {joined}")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        _add_aces_invariant(
            json_schema,
            "metric-definition-key-matches-metric-id",
            "Every metric_definitions object key must match the embedded metric_id value.",
            validator="aces_contracts.contracts.ExperimentEvaluationProtocolModel._validate_metric_definition_keys",
            inputs=[{"contract_id": "experiment-task-v1", "instance_path": "#/evaluation_protocol"}],
        )
        return json_schema


class ExperimentSplitAndLeakageControlsModel(ContractModel):
    """Controls for data partitioning, hidden material, and leakage risk."""

    partitioning_strategy: NonEmptyString | None = None
    grouping_constraints: list[NonEmptyString] = Field(default_factory=list)
    temporal_availability: NonEmptyString | None = None
    hidden_material_policy: NonEmptyString | None = None
    leakage_checks: list[NonEmptyString] = Field(default_factory=list)
    unresolved_risks: list[NonEmptyString] = Field(default_factory=list)


class ExperimentApparatusConstraintModel(ContractModel):
    """Apparatus compatibility and capability constraints for a task."""

    allowed_processor_refs: list[ExperimentProcessorReferenceModel] = Field(default_factory=list)
    allowed_backend_refs: list[ExperimentBackendReferenceModel] = Field(default_factory=list)
    required_manifest_refs: list[ExperimentManifestReferenceModel] = Field(default_factory=list)
    required_capabilities: list[NonEmptyString] = Field(default_factory=list)
    notes: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_allowed_identity_manifest_refs(self) -> ExperimentApparatusConstraintModel:
        required_manifest_keys = {
            (
                manifest.subject_ref.ref_kind,
                manifest.subject_ref.ref_id,
                manifest.subject_ref.ref_version,
                manifest.ref_version,
            )
            for manifest in self.required_manifest_refs
            if manifest.subject_ref is not None
        }
        for ref in self.allowed_processor_refs:
            if (
                "processor",
                ref.ref_id,
                ref.ref_version,
                PROCESSOR_MANIFEST_V2_SCHEMA_VERSION,
            ) not in required_manifest_keys:
                raise ValueError(
                    "allowed_processor_refs entries must have a matching required_manifest_refs "
                    f"entry with processor subject_ref='{ref.ref_id}' and "
                    f"manifest ref_version='{PROCESSOR_MANIFEST_V2_SCHEMA_VERSION}'"
                )
        for ref in self.allowed_backend_refs:
            if (
                "backend",
                ref.ref_id,
                ref.ref_version,
                BACKEND_MANIFEST_V2_SCHEMA_VERSION,
            ) not in required_manifest_keys:
                raise ValueError(
                    "allowed_backend_refs entries must have a matching required_manifest_refs "
                    f"entry with backend subject_ref='{ref.ref_id}' and "
                    f"manifest ref_version='{BACKEND_MANIFEST_V2_SCHEMA_VERSION}'"
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
        _add_aces_invariant(
            json_schema,
            "apparatus-constraint-identity-manifest-resolves",
            "Every allowed processor/backend identity reference must have a matching required manifest ref_id "
            "with matching subject identity and manifest schema version.",
            validator="aces_contracts.contracts.ExperimentApparatusConstraintModel._validate_allowed_identity_manifest_refs",
            inputs=[{"contract_id": "experiment-task-v1", "instance_path": "#/apparatus_constraints"}],
        )
        return json_schema


class ExperimentTaskModel(ContractModel):
    """Experiment task contract that separates scenario material from protocol intent."""

    schema_version: Literal[EXPERIMENT_TASK_SCHEMA_VERSION]
    task_id: NonEmptyString
    task_version: NonEmptyString
    title: NonEmptyString
    description: NonEmptyString
    scenario_ref: ExperimentScenarioReferenceModel
    evaluation_protocol: ExperimentEvaluationProtocolModel
    intended_use: NonEmptyString
    non_use: list[NonEmptyString] = Field(default_factory=list)
    population_or_construct: NonEmptyString
    split_and_leakage_controls: ExperimentSplitAndLeakageControlsModel | None = None
    apparatus_constraints: ExperimentApparatusConstraintModel | None = None
    validity_notes: list[ExperimentValidityNoteModel] = Field(default_factory=list)
    artifact_refs: list[ExperimentArtifactRefModel] = Field(default_factory=list)


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


class ExperimentStochasticControlModel(ContractModel):
    """Seed, randomization, sampling, or scheduler control for reproducibility."""

    control_id: NonEmptyString
    role: Literal["seed", "randomization", "sampling", "scheduler", "agent-policy", "other"]
    value: str | int | None = None
    description: NonEmptyString | None = None


class ExperimentClockContextModel(ContractModel):
    """Clock authority and time-domain metadata for run interpretation."""

    clock_id: NonEmptyString
    authority: NonEmptyString
    time_domain: Literal["wall-clock", "monotonic", "simulated", "logical", "other"]
    synchronization: NonEmptyString | None = None


class ExperimentApparatusComponentModel(ContractModel):
    """Identity and manifest context for one apparatus component."""

    component_kind: Literal[
        "processor",
        "backend",
        "participant-implementation",
        "host",
        "container",
        "vm",
        "network",
        "device",
        "measurement-channel",
        "other",
    ]
    identity: ApparatusIdentityModel
    manifest_ref: ExperimentManifestReferenceModel | None = None
    compatibility_refs: list[ExperimentReferenceModel] = Field(default_factory=list)
    observed: bool = False
    limitations: list[NonEmptyString] = Field(default_factory=list)


class ExperimentApparatusContextModel(ContractModel):
    """Run-scoped apparatus context for interpreting experiment evidence."""

    schema_version: Literal[EXPERIMENT_APPARATUS_CONTEXT_SCHEMA_VERSION]
    apparatus_context_id: NonEmptyString
    context_version: NonEmptyString
    declared_at: Rfc3339DateTimeString
    components: dict[NonEmptyString, ExperimentApparatusComponentModel] = Field(min_length=2)
    selected_manifests: list[ExperimentManifestReferenceModel] = Field(min_length=1)
    compatibility_declarations: list[ExperimentReferenceModel] = Field(min_length=1)
    configuration_parameters: list[ExperimentParameterModel] = Field(min_length=1)
    stochastic_controls: list[ExperimentStochasticControlModel] = Field(min_length=1)
    clocks: list[ExperimentClockContextModel] = Field(min_length=1)
    measurement_channels: list[ExperimentMeasurementChannelReferenceModel] = Field(min_length=1)
    observed_setup_evidence: list[ExperimentArtifactRefModel] = Field(min_length=1)
    known_limitations: list[ExperimentValidityNoteModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_instrument_context(self) -> ExperimentApparatusContextModel:
        _parse_rfc3339_datetime("declared_at", self.declared_at)
        processor = self.components.get("processor")
        backend = self.components.get("backend")
        if processor is None or processor.component_kind != "processor":
            raise ValueError(
                "apparatus components must include a 'processor' component with component_kind='processor'"
            )
        if backend is None or backend.component_kind != "backend":
            raise ValueError("apparatus components must include a 'backend' component with component_kind='backend'")
        selected_manifest_keys = {_manifest_reference_key(ref) for ref in self.selected_manifests}
        for key, component in (("processor", processor), ("backend", backend)):
            if component.manifest_ref is None:
                raise ValueError(f"apparatus component '{key}' must include manifest_ref")
            subject_ref = component.manifest_ref.subject_ref
            if subject_ref is None:
                raise ValueError(f"apparatus component '{key}' manifest_ref must include subject_ref")
            if subject_ref.ref_kind != key:
                raise ValueError(f"apparatus component '{key}' manifest_ref subject_ref must use ref_kind='{key}'")
            if subject_ref.ref_id != component.identity.name or subject_ref.ref_version != component.identity.version:
                raise ValueError(f"apparatus component '{key}' manifest_ref subject_ref must match component identity")
            expected_manifest_version = (
                PROCESSOR_MANIFEST_V2_SCHEMA_VERSION if key == "processor" else BACKEND_MANIFEST_V2_SCHEMA_VERSION
            )
            if component.manifest_ref.ref_version != expected_manifest_version:
                raise ValueError(
                    f"apparatus component '{key}' manifest_ref must use ref_version='{expected_manifest_version}'"
                )
            if _manifest_reference_key(component.manifest_ref) not in selected_manifest_keys:
                raise ValueError(f"apparatus component '{key}' manifest_ref must be present in selected_manifests")
        if not any(artifact.role == "apparatus-evidence" for artifact in self.observed_setup_evidence):
            raise ValueError("observed_setup_evidence must include at least one apparatus-evidence artifact")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        components_schema = json_schema.get("properties", {}).get("components")
        if isinstance(components_schema, dict):
            components_schema.setdefault("required", ["processor", "backend"])
            components_schema.setdefault("allOf", []).extend(
                [
                    {
                        "properties": {
                            "processor": {
                                "required": ["component_kind", "identity", "manifest_ref"],
                                "properties": {
                                    "component_kind": {"const": "processor"},
                                    "manifest_ref": {"type": "object"},
                                },
                            }
                        }
                    },
                    {
                        "properties": {
                            "backend": {
                                "required": ["component_kind", "identity", "manifest_ref"],
                                "properties": {
                                    "component_kind": {"const": "backend"},
                                    "manifest_ref": {"type": "object"},
                                },
                            }
                        }
                    },
                ]
            )
        _add_aces_invariant(
            json_schema,
            "canonical-apparatus-manifest-selected",
            "The canonical processor and backend component manifest_ref values must be present in selected_manifests.",
            validator="aces_contracts.contracts.ExperimentApparatusContextModel._validate_instrument_context",
            inputs=[{"contract_id": "experiment-apparatus-context-v1", "instance_path": "#"}],
        )
        _add_aces_invariant(
            json_schema,
            "apparatus-manifest-payload-identity-valid",
            "Canonical processor and backend manifest_ref values must resolve to manifest payloads with matching identities.",
            validator="aces_contracts.contracts.validate_experiment_apparatus_context_against_manifests",
            inputs=[
                {"contract_id": "experiment-apparatus-context-v1", "instance_path": "#"},
                {"contract_id": "processor-manifest-v2", "instance_path": "#"},
                {"contract_id": "backend-manifest-v2", "instance_path": "#"},
            ],
        )
        return json_schema


def _component_identity_satisfies_allowed_refs(
    component: ExperimentApparatusComponentModel,
    allowed_refs: list[ExperimentReferenceModel],
) -> bool:
    return any(_identity_matches_reference(component.identity, allowed_ref) for allowed_ref in allowed_refs)


def _apparatus_capability_ids(apparatus_context: ExperimentApparatusContextModel) -> set[str]:
    capability_ids = {
        reference.ref_id
        for reference in apparatus_context.compatibility_declarations
        if reference.ref_kind == "capability"
    }
    for component in apparatus_context.components.values():
        capability_ids.update(
            reference.ref_id for reference in component.compatibility_refs if reference.ref_kind == "capability"
        )
    return capability_ids


def _validate_apparatus_context_satisfies_constraints(
    apparatus_constraints: ExperimentApparatusConstraintModel,
    apparatus_context: ExperimentApparatusContextModel,
) -> None:
    processor = apparatus_context.components["processor"]
    backend = apparatus_context.components["backend"]

    if apparatus_constraints.allowed_processor_refs and not _component_identity_satisfies_allowed_refs(
        processor,
        apparatus_constraints.allowed_processor_refs,
    ):
        allowed = ", ".join(_format_reference(reference) for reference in apparatus_constraints.allowed_processor_refs)
        raise ValueError(f"run apparatus processor identity must satisfy task allowed_processor_refs: {allowed}")

    if apparatus_constraints.allowed_backend_refs and not _component_identity_satisfies_allowed_refs(
        backend,
        apparatus_constraints.allowed_backend_refs,
    ):
        allowed = ", ".join(_format_reference(reference) for reference in apparatus_constraints.allowed_backend_refs)
        raise ValueError(f"run apparatus backend identity must satisfy task allowed_backend_refs: {allowed}")

    missing_manifests = sorted(
        _format_reference(required_manifest)
        for required_manifest in apparatus_constraints.required_manifest_refs
        if not any(
            _reference_satisfies_requirement(selected_manifest, required_manifest)
            for selected_manifest in apparatus_context.selected_manifests
        )
    )
    if missing_manifests:
        joined = ", ".join(missing_manifests)
        raise ValueError(f"run apparatus selected_manifests must satisfy task required_manifest_refs: {joined}")

    available_capabilities = _apparatus_capability_ids(apparatus_context)
    missing_capabilities = sorted(
        capability
        for capability in apparatus_constraints.required_capabilities
        if capability not in available_capabilities
    )
    if missing_capabilities:
        joined = ", ".join(missing_capabilities)
        raise ValueError(f"run apparatus capabilities must satisfy task required_capabilities: {joined}")


def _validate_component_manifest_payload(
    *,
    component_key: Literal["processor", "backend"],
    component: ExperimentApparatusComponentModel,
    manifest: ProcessorManifestV2Model | BackendManifestV2Model,
    expected_schema_version: str,
    supplied_digest: str | None,
) -> None:
    if component.manifest_ref is None:
        raise ValueError(f"apparatus component '{component_key}' must include manifest_ref")
    if component.manifest_ref.ref_id != manifest.identity.name:
        raise ValueError(f"apparatus component '{component_key}' manifest_ref ref_id must match manifest identity name")
    if component.manifest_ref.ref_version != expected_schema_version:
        raise ValueError(
            f"apparatus component '{component_key}' manifest_ref ref_version must match manifest schema_version"
        )
    if component.identity.name != manifest.identity.name or component.identity.version != manifest.identity.version:
        raise ValueError(f"apparatus component '{component_key}' identity must match manifest identity")
    subject_ref = component.manifest_ref.subject_ref
    if subject_ref is None:
        raise ValueError(f"apparatus component '{component_key}' manifest_ref must include subject_ref")
    if not _identity_matches_reference(manifest.identity, subject_ref):
        raise ValueError(f"apparatus component '{component_key}' manifest_ref subject_ref must match manifest identity")
    if component.manifest_ref.ref_digest is not None:
        if supplied_digest is None:
            raise ValueError(
                f"apparatus component '{component_key}' manifest_ref digest requires a supplied manifest payload digest"
            )
        if _canonical_digest(component.manifest_ref.ref_digest) != _canonical_digest(supplied_digest):
            raise ValueError(
                f"apparatus component '{component_key}' manifest_ref digest must match manifest payload digest"
            )


def validate_experiment_apparatus_context_against_manifests(
    apparatus_context: ExperimentApparatusContextModel,
    processor_manifest: ProcessorManifestV2Model,
    backend_manifest: BackendManifestV2Model,
    *,
    processor_manifest_digest: str | None = None,
    backend_manifest_digest: str | None = None,
) -> None:
    """Validate apparatus manifest references against concrete manifest payloads."""

    _validate_component_manifest_payload(
        component_key="processor",
        component=apparatus_context.components["processor"],
        manifest=processor_manifest,
        expected_schema_version=PROCESSOR_MANIFEST_V2_SCHEMA_VERSION,
        supplied_digest=processor_manifest_digest,
    )
    _validate_component_manifest_payload(
        component_key="backend",
        component=apparatus_context.components["backend"],
        manifest=backend_manifest,
        expected_schema_version=BACKEND_MANIFEST_V2_SCHEMA_VERSION,
        supplied_digest=backend_manifest_digest,
    )


class ExperimentResultSummaryModel(ContractModel):
    """Reported metric value summary and evidence links for an experiment run."""

    metric_id: NonEmptyString
    value: str | int | float | bool | None = None
    value_status: Literal["reported", "missing", "withheld", "not-applicable"]
    evidence_refs: list[ExperimentEvidenceReferenceModel] = Field(min_length=1)
    uncertainty: NonEmptyString | None = None
    notes: NonEmptyString | None = None

    @model_validator(mode="after")
    def _validate_reported_value(self) -> ExperimentResultSummaryModel:
        if self.value_status == "reported" and self.value is None:
            raise ValueError("reported result summaries must include value")
        if self.value_status != "reported" and self.value is not None:
            raise ValueError("non-reported result summaries must not include value")
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
                {
                    "if": {
                        "properties": {"value_status": {"const": "reported"}},
                        "required": ["value_status"],
                    },
                    "then": {"required": ["value"], "properties": {"value": {"not": {"type": "null"}}}},
                },
                {
                    "if": {
                        "properties": {"value_status": {"enum": ["missing", "withheld", "not-applicable"]}},
                        "required": ["value_status"],
                    },
                    "then": {"properties": {"value": {"type": "null"}}},
                },
            ]
        )
        return json_schema


class ExperimentInvalidationModel(ContractModel):
    """Details explaining why an experiment run was invalidated."""

    invalidated_at: Rfc3339DateTimeString
    reason: NonEmptyString
    superseded_by: ExperimentReferenceModel | None = None

    @model_validator(mode="after")
    def _validate_invalidated_at(self) -> ExperimentInvalidationModel:
        _parse_rfc3339_datetime("invalidated_at", self.invalidated_at)
        return self


class ExperimentRunModel(ContractModel):
    """Archival provenance record for one execution of an experiment task."""

    schema_version: Literal[EXPERIMENT_RUN_SCHEMA_VERSION]
    run_id: NonEmptyString
    run_version: NonEmptyString
    task_ref: ExperimentTaskReferenceModel
    scenario_snapshot_ref: ExperimentScenarioSnapshotReferenceModel
    apparatus_context: ExperimentApparatusContextModel
    parameter_set: list[ExperimentParameterModel] = Field(min_length=1)
    stochastic_controls: list[ExperimentStochasticControlModel] = Field(min_length=1)
    started_at: Rfc3339DateTimeString
    ended_at: Rfc3339DateTimeString
    clock_context: ExperimentClockContextModel
    run_status: Literal["sealed", "completed", "failed", "aborted", "invalidated", "superseded"]
    outcome_status: Literal["succeeded", "failed", "partial", "inconclusive", "not-evaluated"]
    evidence_artifacts: list[ExperimentArtifactRefModel] = Field(min_length=1)
    result_summaries: dict[NonEmptyString, ExperimentResultSummaryModel] = Field(min_length=1)
    deviations: list[NonEmptyString] = Field(default_factory=list)
    invalidation: ExperimentInvalidationModel | None = None
    used_refs: list[ExperimentReferenceModel] = Field(default_factory=list)
    generated_refs: list[ExperimentReferenceModel] = Field(default_factory=list)
    derived_from_refs: list[ExperimentReferenceModel] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_archival_run(self) -> ExperimentRunModel:
        started_at = _parse_rfc3339_datetime("started_at", self.started_at)
        ended_at = _parse_rfc3339_datetime("ended_at", self.ended_at)
        if ended_at < started_at:
            raise ValueError("ended_at must be greater than or equal to started_at")
        if self.run_status == "invalidated" and self.invalidation is None:
            raise ValueError("invalidated experiment runs must include invalidation details")
        if self.outcome_status == "succeeded" and not any(
            result.value_status == "reported" for result in self.result_summaries.values()
        ):
            raise ValueError("succeeded experiment runs must include at least one reported result summary")
        evidence_artifact_ids = {artifact.artifact_id for artifact in self.evidence_artifacts}
        missing_evidence_refs = sorted(
            {
                evidence_ref.ref_id
                for result in self.result_summaries.values()
                for evidence_ref in result.evidence_refs
                if evidence_ref.ref_id not in evidence_artifact_ids
            }
        )
        if missing_evidence_refs:
            joined = ", ".join(missing_evidence_refs)
            raise ValueError(f"result_summaries evidence_refs must resolve to evidence_artifacts: {joined}")
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
                    "properties": {"run_status": {"const": "invalidated"}},
                    "required": ["run_status"],
                },
                "then": {
                    "required": ["invalidation"],
                    "properties": {"invalidation": {"type": "object"}},
                },
            }
        )
        _add_aces_invariant(
            json_schema,
            "ended-at-not-before-started-at",
            "ended_at must be greater than or equal to started_at.",
            validator="aces_contracts.contracts.ExperimentRunModel._validate_archival_run",
            inputs=[{"contract_id": "experiment-run-v1", "instance_path": "#"}],
        )
        _add_aces_invariant(
            json_schema,
            "result-evidence-ref-resolves",
            "Every result_summaries evidence_refs ref_id must match an evidence_artifacts artifact_id.",
            validator="aces_contracts.contracts.ExperimentRunModel._validate_archival_run",
            inputs=[{"contract_id": "experiment-run-v1", "instance_path": "#"}],
        )
        _add_aces_invariant(
            json_schema,
            "task-run-protocol-binding-valid",
            "Run apparatus, result metric ids, and concrete evidence artifacts must satisfy the referenced task protocol.",
            validator="aces_contracts.contracts.validate_experiment_run_against_task",
            inputs=[
                {"contract_id": "experiment-task-v1", "instance_path": "#"},
                {"contract_id": "experiment-run-v1", "instance_path": "#"},
            ],
        )
        return json_schema


def _artifact_satisfies_evidence_reference(
    artifact: ExperimentArtifactRefModel,
    evidence_reference: ExperimentEvidenceReferenceModel,
) -> bool:
    direct_artifact_match = artifact.artifact_id == evidence_reference.ref_id and evidence_reference.ref_version is None
    semantic_evidence_match = any(
        _reference_identity_satisfies_requirement(satisfied_ref, evidence_reference)
        for satisfied_ref in artifact.satisfies_refs
    )
    if not direct_artifact_match and not semantic_evidence_match:
        return False
    if evidence_reference.ref_digest is not None:
        artifact_digest = f"{artifact.checksum.algorithm}:{artifact.checksum.value}"
        if _canonical_digest(artifact_digest) != _canonical_digest(evidence_reference.ref_digest):
            return False
    return evidence_reference.ref_path is None or artifact.uri == evidence_reference.ref_path


def validate_experiment_run_against_task(task: ExperimentTaskModel, run: ExperimentRunModel) -> None:
    """Validate cross-artifact task/run semantic invariants."""

    if run.task_ref.ref_id != task.task_id or run.task_ref.ref_version != task.task_version:
        raise ValueError("run task_ref must match task task_id and task_version")

    if run.scenario_snapshot_ref.ref_id != task.scenario_ref.ref_id:
        raise ValueError("run scenario_snapshot_ref ref_id must match task scenario_ref ref_id")
    if task.scenario_ref.ref_kind == "scenario-snapshot":
        if run.scenario_snapshot_ref.ref_version != task.scenario_ref.ref_version:
            raise ValueError("run scenario_snapshot_ref ref_version must match task scenario_ref ref_version")
        if _canonical_digest(run.scenario_snapshot_ref.ref_digest) != _canonical_digest(task.scenario_ref.ref_digest):
            raise ValueError("run scenario_snapshot_ref ref_digest must match task scenario_ref ref_digest")

    if task.apparatus_constraints is not None:
        _validate_apparatus_context_satisfies_constraints(task.apparatus_constraints, run.apparatus_context)

    metric_definitions = task.evaluation_protocol.metric_definitions
    missing_metric_ids = sorted(
        {result.metric_id for result in run.result_summaries.values() if result.metric_id not in metric_definitions}
    )
    if missing_metric_ids:
        joined = ", ".join(missing_metric_ids)
        raise ValueError(f"run result metric_id values must be declared by the task evaluation protocol: {joined}")

    evidence_artifacts_by_id = {artifact.artifact_id: artifact for artifact in run.evidence_artifacts}
    missing_observation_requirements = sorted(
        requirement.ref_id
        for requirement in task.evaluation_protocol.observation_requirements
        if not any(_artifact_satisfies_evidence_reference(artifact, requirement) for artifact in run.evidence_artifacts)
    )
    if missing_observation_requirements:
        joined = ", ".join(missing_observation_requirements)
        raise ValueError(f"run evidence_artifacts must satisfy task observation requirements: {joined}")

    missing_metric_evidence: list[str] = []
    for result_id, result in run.result_summaries.items():
        result_artifacts = [
            evidence_artifacts_by_id[evidence_ref.ref_id]
            for evidence_ref in result.evidence_refs
            if evidence_ref.ref_id in evidence_artifacts_by_id
        ]
        for requirement in metric_definitions[result.metric_id].evidence_requirements:
            if not any(_artifact_satisfies_evidence_reference(artifact, requirement) for artifact in result_artifacts):
                missing_metric_evidence.append(f"{result_id}:{requirement.ref_id}")
    if missing_metric_evidence:
        joined = ", ".join(sorted(missing_metric_evidence))
        raise ValueError(f"run result evidence_refs must satisfy task metric evidence requirements: {joined}")


class ExperimentStudyMembershipModel(ContractModel):
    """Typed member reference within a study or collection."""

    target_ref: ExperimentReferenceModel
    role: Literal[
        "primary-task",
        "comparison-task",
        "calibration-run",
        "evaluation-run",
        "baseline-result",
        "comparison-result",
        "evidence",
        "analysis",
        "other",
    ]
    grouping: NonEmptyString | None = None
    inclusion_rationale: NonEmptyString | None = None

    @model_validator(mode="after")
    def _validate_role_target_kind(self) -> ExperimentStudyMembershipModel:
        allowed_ref_kinds = {
            "primary-task": {"task"},
            "comparison-task": {"task"},
            "calibration-run": {"run"},
            "evaluation-run": {"run"},
            "baseline-result": {"result"},
            "comparison-result": {"result"},
            "evidence": {"evidence"},
            "analysis": {"analysis-artifact"},
        }.get(self.role)
        if allowed_ref_kinds is not None and self.target_ref.ref_kind not in allowed_ref_kinds:
            expected = ", ".join(sorted(allowed_ref_kinds))
            raise ValueError(f"study membership role '{self.role}' requires target_ref.ref_kind in {{{expected}}}")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        role_kind_constraints = {
            ("primary-task", "comparison-task"): ["task"],
            ("calibration-run", "evaluation-run"): ["run"],
            ("baseline-result", "comparison-result"): ["result"],
            ("evidence",): ["evidence"],
            ("analysis",): ["analysis-artifact"],
        }
        json_schema.setdefault("allOf", []).extend(
            {
                "if": {"properties": {"role": {"enum": list(roles)}}, "required": ["role"]},
                "then": {
                    "properties": {
                        "target_ref": {
                            "required": ["ref_kind"],
                            "properties": {"ref_kind": {"enum": ref_kinds}},
                        }
                    }
                },
            }
            for roles, ref_kinds in role_kind_constraints.items()
        )
        return json_schema


class ExperimentStudyFactorModel(ContractModel):
    """Treatment, control, blocking, or apparatus factor for study analysis."""

    name: NonEmptyString
    factor_kind: Literal["treatment", "control", "blocking", "stratification", "apparatus", "other"]
    levels: list[NonEmptyString] = Field(default_factory=list)


class ExperimentConditionAssignmentModel(ContractModel):
    """Concrete treatment-condition assignment criteria for study evaluation runs."""

    condition_id: NonEmptyString
    factor_levels: dict[NonEmptyString, NonEmptyString] = Field(min_length=1)
    required_refs: list[ExperimentConditionAssignmentReferenceModel] = Field(default_factory=list)
    required_parameters: list[ExperimentConditionAssignmentParameterModel] = Field(default_factory=list)
    description: NonEmptyString | None = None

    @model_validator(mode="after")
    def _validate_run_level_criteria(self) -> ExperimentConditionAssignmentModel:
        if not self.required_refs and not self.required_parameters:
            raise ValueError("condition assignments must include required_refs or required_parameters")
        return self


class ExperimentRunAllocationPlanModel(ContractModel):
    """Structured run allocation, replication, and assignment plan."""

    allocation_unit: NonEmptyString
    allocation_method: NonEmptyString
    compared_conditions: list[NonEmptyString] = Field(min_length=1, json_schema_extra={"uniqueItems": True})
    condition_assignments: dict[NonEmptyString, ExperimentConditionAssignmentModel] = Field(min_length=1)
    target_runs_per_condition: PositiveInteger
    randomization_unit: NonEmptyString | None = None
    blocking_factors: list[NonEmptyString] = Field(default_factory=list, json_schema_extra={"uniqueItems": True})
    replication_policy: NonEmptyString
    stopping_rule: NonEmptyString | None = None

    @model_validator(mode="after")
    def _validate_condition_assignments(self) -> ExperimentRunAllocationPlanModel:
        condition_ids = set(self.compared_conditions)
        if len(condition_ids) != len(self.compared_conditions):
            raise ValueError("run_allocation compared_conditions must be unique")
        assignment_ids = set(self.condition_assignments)
        if assignment_ids != condition_ids:
            raise ValueError("run_allocation condition_assignments keys must match compared_conditions")
        mismatched_assignment_ids = sorted(
            assignment_key
            for assignment_key, assignment in self.condition_assignments.items()
            if assignment.condition_id != assignment_key
        )
        if mismatched_assignment_ids:
            joined = ", ".join(mismatched_assignment_ids)
            raise ValueError(f"run_allocation condition_assignments keys must match embedded condition_id: {joined}")
        if len(set(self.blocking_factors)) != len(self.blocking_factors):
            raise ValueError("run_allocation blocking_factors must be unique")
        if len(condition_ids) > 1:
            factor_levels_by_signature: dict[tuple[tuple[str, str], ...], list[str]] = {}
            criteria_by_signature: dict[
                tuple[
                    tuple[tuple[str, str, str | None, str | None, str | None], ...],
                    tuple[tuple[str, str, str, str], ...],
                ],
                list[str],
            ] = {}
            for condition_id, assignment in self.condition_assignments.items():
                factor_levels_signature = tuple(sorted(assignment.factor_levels.items()))
                factor_levels_by_signature.setdefault(factor_levels_signature, []).append(condition_id)
                signature = _condition_assignment_run_criteria_signature(assignment)
                criteria_by_signature.setdefault(signature, []).append(condition_id)
            duplicate_factor_level_conditions = sorted(
                ",".join(sorted(condition_ids))
                for condition_ids in factor_levels_by_signature.values()
                if len(condition_ids) > 1
            )
            if duplicate_factor_level_conditions:
                joined = "; ".join(duplicate_factor_level_conditions)
                raise ValueError(
                    "run_allocation condition_assignments must use distinct factor-level combinations across "
                    f"compared_conditions: {joined}"
                )
            duplicate_criteria_conditions = sorted(
                ",".join(sorted(condition_ids))
                for condition_ids in criteria_by_signature.values()
                if len(condition_ids) > 1
            )
            if duplicate_criteria_conditions:
                joined = "; ".join(duplicate_criteria_conditions)
                raise ValueError(
                    "run_allocation condition_assignments must use distinct run-level criteria across "
                    f"compared_conditions: {joined}"
                )
        return self


class ExperimentStatisticalMethodModel(ContractModel):
    """Statistical or estimation method declared before analysis."""

    method: NonEmptyString
    estimand: NonEmptyString
    unit_of_analysis: NonEmptyString
    comparison_family: NonEmptyString | None = None
    assumptions: list[NonEmptyString] = Field(min_length=1)


class ExperimentUncertaintyMethodModel(ContractModel):
    """Uncertainty reporting plan for study estimates."""

    method: NonEmptyString
    interval_level: UnitIntervalFloat
    procedure: NonEmptyString


class ExperimentMultipleComparisonPolicyModel(ContractModel):
    """Multiplicity policy for study-level families of comparisons."""

    family: NonEmptyString
    correction: NonEmptyString
    rationale: NonEmptyString


class ExperimentMissingDataPolicyModel(ContractModel):
    """Missing, failed, withheld, or not-applicable result handling."""

    missingness_assumption: NonEmptyString
    handling: NonEmptyString
    sensitivity_analysis: NonEmptyString | None = None


class ExperimentAnalysisPlanModel(ContractModel):
    """Analysis plan metadata for metrics, uncertainty, and missing data."""

    analysis_id: NonEmptyString
    description: NonEmptyString
    metrics: list[NonEmptyString] = Field(min_length=1)
    primary_metric: NonEmptyString
    statistical_method: ExperimentStatisticalMethodModel
    uncertainty_method: ExperimentUncertaintyMethodModel
    multiple_comparison_policy: ExperimentMultipleComparisonPolicyModel
    missing_data_policy: ExperimentMissingDataPolicyModel

    @model_validator(mode="after")
    def _validate_primary_metric(self) -> ExperimentAnalysisPlanModel:
        if self.primary_metric not in self.metrics:
            raise ValueError("analysis_plan primary_metric must be included in metrics")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        _add_aces_invariant(
            json_schema,
            "analysis-plan-substantive-methods-required",
            "Analysis plans must name metrics plus structured statistical, uncertainty, multiplicity, "
            "and missing-data policies.",
            validator="aces_contracts.contracts.ExperimentAnalysisPlanModel._validate_primary_metric",
            inputs=[{"contract_id": "experiment-study-v1", "instance_path": "#/analysis_plan"}],
        )
        return json_schema


class ExperimentStudyModel(ContractModel):
    """Study or collection contract for grouping experiment artifacts."""

    schema_version: Literal[EXPERIMENT_STUDY_SCHEMA_VERSION]
    study_id: NonEmptyString
    study_version: NonEmptyString
    study_kind: Literal["study", "collection", "benchmark", "cohort"]
    title: NonEmptyString
    owner: NonEmptyString
    description: NonEmptyString
    purpose: NonEmptyString
    research_questions: list[NonEmptyString] = Field(default_factory=list)
    membership: dict[NonEmptyString, ExperimentStudyMembershipModel] = Field(min_length=1)
    inclusion_criteria: list[NonEmptyString] = Field(min_length=1)
    factors: dict[NonEmptyString, ExperimentStudyFactorModel] = Field(default_factory=dict)
    run_allocation: ExperimentRunAllocationPlanModel | None = None
    analysis_plan: ExperimentAnalysisPlanModel | None = None
    validity_notes: list[ExperimentValidityNoteModel] = Field(default_factory=list)
    report_artifacts: list[ExperimentArtifactRefModel] = Field(default_factory=list)
    export_artifacts: list[ExperimentArtifactRefModel] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_claim_bearing_study(self) -> ExperimentStudyModel:
        if self.run_allocation is not None:
            undeclared_blocking_factors = sorted(
                factor_id for factor_id in self.run_allocation.blocking_factors if factor_id not in self.factors
            )
            if undeclared_blocking_factors:
                joined = ", ".join(undeclared_blocking_factors)
                raise ValueError(f"run_allocation blocking_factors must reference declared factors: {joined}")
            blocking_factors_without_levels = sorted(
                factor_id for factor_id in self.run_allocation.blocking_factors if not self.factors[factor_id].levels
            )
            if blocking_factors_without_levels:
                joined = ", ".join(blocking_factors_without_levels)
                raise ValueError(
                    f"run_allocation blocking_factors must reference factors with declared levels: {joined}"
                )
            invalid_blocking_factor_kinds = sorted(
                f"{factor_id}:{self.factors[factor_id].factor_kind}"
                for factor_id in self.run_allocation.blocking_factors
                if self.factors[factor_id].factor_kind not in {"blocking", "stratification", "apparatus", "control"}
            )
            if invalid_blocking_factor_kinds:
                joined = ", ".join(invalid_blocking_factor_kinds)
                raise ValueError(
                    "run_allocation blocking_factors must reference blocking, stratification, apparatus, "
                    f"or control factors: {joined}"
                )
            for assignment_key, assignment in self.run_allocation.condition_assignments.items():
                for factor_id, level in assignment.factor_levels.items():
                    factor = self.factors.get(factor_id)
                    if factor is None:
                        raise ValueError(
                            "run_allocation condition_assignments factor_levels must reference declared factors: "
                            f"{assignment_key}:{factor_id}"
                        )
                    if level not in factor.levels:
                        raise ValueError(
                            "run_allocation condition_assignments factor_levels must reference declared factor levels: "
                            f"{assignment_key}:{factor_id}:{level}"
                        )
        if self.study_kind in {"study", "benchmark"}:
            if not self.research_questions:
                raise ValueError("study and benchmark records must include at least one research question")
            if self.run_allocation is None:
                raise ValueError("study and benchmark records must include run_allocation")
            if self.analysis_plan is None:
                raise ValueError("study and benchmark records must include analysis_plan")
            if not self.validity_notes:
                raise ValueError("study and benchmark records must include validity_notes")
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
                    "properties": {"study_kind": {"enum": ["study", "benchmark"]}},
                    "required": ["study_kind"],
                },
                "then": {
                    "required": ["research_questions", "run_allocation", "analysis_plan", "validity_notes"],
                    "properties": {
                        "research_questions": {"minItems": 1},
                        "run_allocation": {"type": "object"},
                        "analysis_plan": {"type": "object"},
                        "validity_notes": {"minItems": 1},
                    },
                },
            }
        )
        _add_aces_invariant(
            json_schema,
            "claim-bearing-study-analysis-plan-required",
            "Study and benchmark records must include research questions, run allocation, a substantive analysis plan, "
            "and validity notes.",
            validator="aces_contracts.contracts.ExperimentStudyModel._validate_claim_bearing_study",
            inputs=[{"contract_id": "experiment-study-v1", "instance_path": "#"}],
        )
        _add_aces_invariant(
            json_schema,
            "study-analysis-metrics-grounded-in-task-protocols",
            "Study analysis_plan metrics must be declared by included experiment task protocols.",
            validator="aces_contracts.contracts.validate_experiment_study_against_tasks_and_runs",
            inputs=[
                {"contract_id": "experiment-study-v1", "instance_path": "#"},
                {"contract_id": "experiment-task-v1", "instance_path": "#"},
                {"contract_id": "experiment-run-v1", "instance_path": "#"},
            ],
        )
        _add_aces_invariant(
            json_schema,
            "study-analysis-metrics-covered-by-evaluation-run-results",
            "Study analysis_plan metrics must have result_summaries, including explicit missing/withheld "
            "statuses, in included evaluation runs.",
            validator="aces_contracts.contracts.validate_experiment_study_against_tasks_and_runs",
            inputs=[
                {"contract_id": "experiment-study-v1", "instance_path": "#"},
                {"contract_id": "experiment-task-v1", "instance_path": "#"},
                {"contract_id": "experiment-run-v1", "instance_path": "#"},
            ],
        )
        _add_aces_invariant(
            json_schema,
            "study-analysis-runs-eligible",
            "Study analysis_plan evaluation-run members must resolve unambiguously and exclude invalidated, "
            "superseded, and not-evaluated runs.",
            validator="aces_contracts.contracts.validate_experiment_study_against_tasks_and_runs",
            inputs=[
                {"contract_id": "experiment-study-v1", "instance_path": "#"},
                {"contract_id": "experiment-run-v1", "instance_path": "#"},
            ],
        )
        _add_aces_invariant(
            json_schema,
            "study-run-allocation-covered-by-evaluation-run-members",
            "Study run_allocation compared_conditions must be represented by eligible included evaluation-run "
            "membership groupings that meet target_runs_per_condition, use operational blocking factors, and satisfy "
            "exactly one distinct factor-level combination and auditable condition assignment.",
            validator="aces_contracts.contracts.validate_experiment_study_against_tasks_and_runs",
            inputs=[
                {"contract_id": "experiment-study-v1", "instance_path": "#"},
                {"contract_id": "experiment-task-v1", "instance_path": "#"},
                {"contract_id": "experiment-run-v1", "instance_path": "#"},
            ],
        )
        return json_schema


def validate_experiment_task_archival_datetimes(task: ExperimentTaskModel | Mapping[str, Any]) -> None:
    """Validate task-level archival timestamp semantics not carried by generic JSON Schema."""

    _validate_artifact_collection_created_at("artifact_refs", _payload_get(task, "artifact_refs"))


def validate_experiment_apparatus_context_archival_datetimes(
    apparatus_context: ExperimentApparatusContextModel | Mapping[str, Any],
) -> None:
    """Validate apparatus-context archival timestamp semantics not carried by generic JSON Schema."""

    _validate_rfc3339_payload_field(apparatus_context, "declared_at")
    _validate_artifact_collection_created_at(
        "observed_setup_evidence",
        _payload_get(apparatus_context, "observed_setup_evidence"),
    )


def validate_experiment_run_archival_datetimes(run: ExperimentRunModel | Mapping[str, Any]) -> None:
    """Validate run-level archival timestamp semantics not carried by generic JSON Schema."""

    _validate_rfc3339_payload_field(run, "started_at")
    _validate_rfc3339_payload_field(run, "ended_at")
    invalidation = _payload_get(run, "invalidation")
    if invalidation is not None:
        _validate_rfc3339_payload_field(invalidation, "invalidated_at")
    _validate_artifact_collection_created_at("evidence_artifacts", _payload_get(run, "evidence_artifacts"))


def validate_experiment_study_archival_datetimes(study: ExperimentStudyModel | Mapping[str, Any]) -> None:
    """Validate study-level archival timestamp semantics not carried by generic JSON Schema."""

    _validate_artifact_collection_created_at("report_artifacts", _payload_get(study, "report_artifacts"))
    _validate_artifact_collection_created_at("export_artifacts", _payload_get(study, "export_artifacts"))


def _task_reference_key(reference: ExperimentTaskReferenceModel) -> tuple[str, str | None]:
    return (reference.ref_id, reference.ref_version)


def _task_model_key(task: ExperimentTaskModel) -> tuple[str, str]:
    return (task.task_id, task.task_version)


def _run_model_key(run: ExperimentRunModel) -> tuple[str, str | None]:
    return (run.run_id, run.run_version)


def _task_ref_matches_task(reference: ExperimentReferenceModel, task: ExperimentTaskModel) -> bool:
    return (
        reference.ref_kind == "task"
        and reference.ref_id == task.task_id
        and (reference.ref_version is None or reference.ref_version == task.task_version)
    )


def _run_ref_matches_run(reference: ExperimentReferenceModel, run: ExperimentRunModel) -> bool:
    return (
        reference.ref_kind == "run"
        and reference.ref_id == run.run_id
        and (reference.ref_version is None or reference.ref_version == run.run_version)
    )


def _component_identity_matches_reference(
    component: ExperimentApparatusComponentModel,
    reference: ExperimentReferenceModel,
) -> bool:
    return component.component_kind == reference.ref_kind and _identity_matches_reference(component.identity, reference)


def _reference_in_collection(
    references: list[ExperimentReferenceModel],
    requirement: ExperimentReferenceModel,
) -> bool:
    return any(_reference_satisfies_requirement(reference, requirement) for reference in references)


def _run_satisfies_condition_reference(run: ExperimentRunModel, requirement: ExperimentReferenceModel) -> bool:
    apparatus_context = run.apparatus_context
    if requirement.ref_kind in {"processor", "backend", "participant-implementation"}:
        return any(
            _component_identity_matches_reference(component, requirement)
            for component in apparatus_context.components.values()
        )
    if requirement.ref_kind == "task":
        return _reference_satisfies_requirement(run.task_ref, requirement)
    if requirement.ref_kind == "scenario-snapshot":
        return _reference_satisfies_requirement(run.scenario_snapshot_ref, requirement)
    if requirement.ref_kind == "apparatus-context":
        return requirement.ref_id == apparatus_context.apparatus_context_id and (
            requirement.ref_version is None or requirement.ref_version == apparatus_context.context_version
        )
    if requirement.ref_kind == "manifest":
        return any(
            _reference_satisfies_requirement(selected_manifest, requirement)
            for selected_manifest in apparatus_context.selected_manifests
        )
    if requirement.ref_kind in {"profile", "capability"}:
        component_refs = [
            reference
            for component in apparatus_context.components.values()
            for reference in component.compatibility_refs
        ]
        return _reference_in_collection(
            apparatus_context.compatibility_declarations, requirement
        ) or _reference_in_collection(
            component_refs,
            requirement,
        )
    if requirement.ref_kind == "measurement-channel":
        return _reference_in_collection(apparatus_context.measurement_channels, requirement)
    if requirement.ref_kind == "evidence":
        return any(
            artifact.artifact_id == requirement.ref_id
            or any(
                _reference_satisfies_requirement(satisfied_ref, requirement)
                for satisfied_ref in artifact.satisfies_refs
            )
            for artifact in run.evidence_artifacts
        )
    return (
        _reference_in_collection(run.used_refs, requirement)
        or _reference_in_collection(run.generated_refs, requirement)
        or _reference_in_collection(run.derived_from_refs, requirement)
    )


def _parameter_satisfies_requirement(
    parameter: ExperimentParameterModel,
    requirement: ExperimentParameterModel,
) -> bool:
    return (
        parameter.name == requirement.name
        and parameter.value_kind == requirement.value_kind
        and parameter.value == requirement.value
    )


def _condition_assignment_run_criteria_signature(
    assignment: ExperimentConditionAssignmentModel,
) -> tuple[
    tuple[tuple[str, str, str | None, str | None, str | None], ...],
    tuple[tuple[str, str, str, str], ...],
]:
    reference_signature = tuple(
        sorted(
            (
                reference.ref_kind,
                reference.ref_id,
                reference.ref_version,
                _canonical_digest(reference.ref_digest),
                reference.ref_path,
            )
            for reference in assignment.required_refs
        )
    )
    parameter_signature = tuple(
        sorted(
            (
                parameter.name,
                parameter.value_kind,
                type(parameter.value).__name__,
                json.dumps(parameter.value, sort_keys=True, separators=(",", ":")),
            )
            for parameter in assignment.required_parameters
        )
    )
    return reference_signature, parameter_signature


def _run_satisfies_condition_assignment(
    run: ExperimentRunModel,
    assignment: ExperimentConditionAssignmentModel,
) -> list[str]:
    missing: list[str] = []
    missing.extend(
        _format_reference(reference)
        for reference in assignment.required_refs
        if not _run_satisfies_condition_reference(run, reference)
    )
    run_parameters = [*run.parameter_set, *run.apparatus_context.configuration_parameters]
    missing.extend(
        f"parameter:{parameter.name}:{parameter.value_kind}"
        for parameter in assignment.required_parameters
        if not any(_parameter_satisfies_requirement(candidate, parameter) for candidate in run_parameters)
    )
    return missing


def _run_is_eligible_for_study_analysis(run: ExperimentRunModel) -> bool:
    return run.run_status not in {"invalidated", "superseded"} and run.outcome_status != "not-evaluated"


def _validate_study_analysis_run_eligibility(
    study: ExperimentStudyModel,
    runs: list[ExperimentRunModel],
    evaluation_run_members: list[ExperimentStudyMembershipModel],
) -> None:
    if study.analysis_plan is None:
        return

    if not evaluation_run_members:
        raise ValueError("study analysis_plan requires at least one included evaluation-run membership")

    ambiguous_run_refs: list[str] = []
    ineligible_run_refs: list[str] = []
    for member in evaluation_run_members:
        reference_label = _format_reference(member.target_ref)
        matching_runs = [run for run in runs if _run_ref_matches_run(member.target_ref, run)]
        if len(matching_runs) > 1:
            ambiguous_run_refs.append(reference_label)
            continue
        for run in matching_runs:
            if not _run_is_eligible_for_study_analysis(run):
                ineligible_run_refs.append(f"{run.run_id}:{run.run_status}:{run.outcome_status}")

    if ambiguous_run_refs:
        joined = ", ".join(sorted(ambiguous_run_refs))
        raise ValueError(
            f"study evaluation-run memberships used for analysis must resolve to one supplied run artifact: {joined}"
        )
    if ineligible_run_refs:
        joined = ", ".join(sorted(ineligible_run_refs))
        raise ValueError(
            "study evaluation-run members used for analysis must not be invalidated, superseded, or not-evaluated: "
            f"{joined}"
        )


def _validate_study_run_allocation_coverage(
    study: ExperimentStudyModel,
    runs: list[ExperimentRunModel],
    evaluation_run_members: list[ExperimentStudyMembershipModel],
) -> None:
    allocation = study.run_allocation
    if allocation is None or study.analysis_plan is None:
        return

    if not evaluation_run_members:
        raise ValueError("study run_allocation requires at least one included evaluation-run membership")

    condition_set = set(allocation.compared_conditions)
    grouped_run_keys: dict[str, set[tuple[str, str | None]]] = {
        condition: set() for condition in allocation.compared_conditions
    }
    condition_by_run_key: dict[tuple[str, str | None], str] = {}
    ungrouped_run_refs: list[str] = []
    unknown_groupings: list[str] = []
    ambiguous_run_refs: list[str] = []
    duplicate_run_assignments: list[str] = []
    ineligible_run_refs: list[str] = []
    unsatisfied_condition_runs: list[str] = []
    ambiguous_condition_runs: list[str] = []

    for member in evaluation_run_members:
        reference_label = _format_reference(member.target_ref)
        if member.grouping is None:
            ungrouped_run_refs.append(reference_label)
            continue
        if member.grouping not in condition_set:
            unknown_groupings.append(f"{reference_label}:{member.grouping}")
            continue

        matching_runs = [run for run in runs if _run_ref_matches_run(member.target_ref, run)]
        if len(matching_runs) > 1:
            ambiguous_run_refs.append(reference_label)
            continue
        for run in matching_runs:
            run_key = _run_model_key(run)
            prior_condition = condition_by_run_key.get(run_key)
            if prior_condition is not None:
                duplicate_run_assignments.append(f"{run.run_id}:{prior_condition},{member.grouping}")
                continue
            if not _run_is_eligible_for_study_analysis(run):
                ineligible_run_refs.append(f"{run.run_id}:{run.run_status}:{run.outcome_status}")
                continue
            assignment = allocation.condition_assignments[member.grouping]
            missing_condition_inputs = _run_satisfies_condition_assignment(run, assignment)
            if missing_condition_inputs:
                joined_missing_inputs = "|".join(sorted(missing_condition_inputs))
                unsatisfied_condition_runs.append(f"{run.run_id}:{member.grouping}:{joined_missing_inputs}")
                continue
            satisfied_other_conditions = sorted(
                condition_id
                for condition_id, candidate_assignment in allocation.condition_assignments.items()
                if condition_id != member.grouping
                and not _run_satisfies_condition_assignment(run, candidate_assignment)
            )
            if satisfied_other_conditions:
                joined_other_conditions = "|".join(satisfied_other_conditions)
                ambiguous_condition_runs.append(f"{run.run_id}:{member.grouping}:{joined_other_conditions}")
                continue
            condition_by_run_key[run_key] = member.grouping
            grouped_run_keys[member.grouping].add(run_key)

    if ungrouped_run_refs:
        joined = ", ".join(sorted(ungrouped_run_refs))
        raise ValueError(f"study run_allocation requires evaluation-run membership groupings: {joined}")
    if unknown_groupings:
        joined = ", ".join(sorted(unknown_groupings))
        raise ValueError(f"study evaluation-run groupings must be declared in compared_conditions: {joined}")
    if ambiguous_run_refs:
        joined = ", ".join(sorted(ambiguous_run_refs))
        raise ValueError(
            f"study evaluation-run membership references must resolve to one supplied run artifact: {joined}"
        )
    if duplicate_run_assignments:
        joined = ", ".join(sorted(duplicate_run_assignments))
        raise ValueError(f"study evaluation-run members must not assign the same run to multiple conditions: {joined}")
    if ineligible_run_refs:
        joined = ", ".join(sorted(ineligible_run_refs))
        raise ValueError(
            "study evaluation-run members used for analysis must not be invalidated, superseded, or not-evaluated: "
            f"{joined}"
        )
    if unsatisfied_condition_runs:
        joined = ", ".join(sorted(unsatisfied_condition_runs))
        raise ValueError(f"study evaluation-run members must satisfy their condition assignments: {joined}")
    if ambiguous_condition_runs:
        joined = ", ".join(sorted(ambiguous_condition_runs))
        raise ValueError(f"study evaluation-run members must satisfy exactly one condition assignment: {joined}")

    under_target_conditions = sorted(
        f"{condition}:{len(run_keys)}/{allocation.target_runs_per_condition}"
        for condition, run_keys in grouped_run_keys.items()
        if len(run_keys) < allocation.target_runs_per_condition
    )
    if under_target_conditions:
        joined = ", ".join(under_target_conditions)
        raise ValueError(
            f"study run_allocation target_runs_per_condition must be satisfied by included evaluation runs: {joined}"
        )


def validate_experiment_study_against_tasks_and_runs(
    study: ExperimentStudyModel,
    tasks: list[ExperimentTaskModel],
    runs: list[ExperimentRunModel] | None = None,
) -> None:
    """Validate study-level analysis semantics against concrete task/run artifacts."""

    runs = runs or []
    task_refs = [
        member.target_ref for member in study.membership.values() if member.role in {"primary-task", "comparison-task"}
    ]
    matched_tasks = [task for task in tasks if any(_task_ref_matches_task(reference, task) for reference in task_refs)]
    missing_task_refs = sorted(
        _format_reference(reference)
        for reference in task_refs
        if not any(_task_ref_matches_task(reference, task) for task in tasks)
    )
    if missing_task_refs:
        joined = ", ".join(missing_task_refs)
        raise ValueError(f"study task membership references must resolve to supplied task artifacts: {joined}")

    run_refs = [
        member.target_ref
        for member in study.membership.values()
        if member.role in {"calibration-run", "evaluation-run"}
    ]
    evaluation_run_members = [member for member in study.membership.values() if member.role == "evaluation-run"]
    evaluation_run_refs = [member.target_ref for member in evaluation_run_members]
    matched_runs = [run for run in runs if any(_run_ref_matches_run(reference, run) for reference in run_refs)]
    matched_evaluation_runs = [
        run for run in runs if any(_run_ref_matches_run(reference, run) for reference in evaluation_run_refs)
    ]
    missing_run_refs = sorted(
        _format_reference(reference)
        for reference in run_refs
        if not any(_run_ref_matches_run(reference, run) for run in runs)
    )
    if run_refs and missing_run_refs:
        joined = ", ".join(missing_run_refs)
        raise ValueError(f"study run membership references must resolve to supplied run artifacts: {joined}")

    _validate_study_analysis_run_eligibility(study, runs, evaluation_run_members)
    _validate_study_run_allocation_coverage(study, runs, evaluation_run_members)

    task_by_key = {_task_model_key(task): task for task in matched_tasks}
    for run in matched_runs:
        task = task_by_key.get(_task_reference_key(run.task_ref))
        if task is None:
            raise ValueError("study run members must reference a supplied study task artifact")
        validate_experiment_run_against_task(task, run)

    if study.analysis_plan is None:
        return
    declared_metric_ids = {
        metric_id for task in matched_tasks for metric_id in task.evaluation_protocol.metric_definitions
    }
    if not declared_metric_ids:
        raise ValueError("study analysis_plan metrics require supplied task protocol artifacts")
    ungrounded_metrics = sorted(
        metric_id for metric_id in study.analysis_plan.metrics if metric_id not in declared_metric_ids
    )
    if ungrounded_metrics:
        joined = ", ".join(ungrounded_metrics)
        raise ValueError(f"study analysis_plan metrics must be declared by included task protocols: {joined}")
    missing_run_metrics = sorted(
        f"{run.run_id}:{metric_id}"
        for run in matched_evaluation_runs
        for metric_id in study.analysis_plan.metrics
        if metric_id not in {result.metric_id for result in run.result_summaries.values()}
    )
    if missing_run_metrics:
        joined = ", ".join(missing_run_metrics)
        raise ValueError(
            "study analysis_plan metrics must have result_summaries, including explicit missing/withheld "
            f"statuses, in included evaluation runs: {joined}"
        )


class ConceptFamilyDefinitionModel(ContractModel):
    title: NonEmptyString
    description: NonEmptyString
    provenance: ConceptProvenanceCategory
    authority: str | None = Field(default=None, min_length=1)
    authority_reference: str | None = Field(default=None, min_length=1)
    extension_scope: str | None = Field(default=None, min_length=1)
    relation_rules: list[NonEmptyString] = Field(default_factory=list, min_length=1)
    non_ambiguity_constraints: list[NonEmptyString] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_provenance_rules(self) -> ConceptFamilyDefinitionModel:
        if self.provenance in {ConceptProvenanceCategory.ADOPTED, ConceptProvenanceCategory.ADAPTED}:
            if self.authority is None or self.authority_reference is None:
                raise ValueError("adopted and adapted concept families require both authority and authority_reference")
        if self.provenance == ConceptProvenanceCategory.NATIVE and (
            self.authority is not None or self.authority_reference is not None
        ):
            raise ValueError("native concept families must not declare authority metadata")
        if self.provenance == ConceptProvenanceCategory.NATIVE:
            if self.extension_scope is None:
                raise ValueError("native concept families require extension_scope")
            if not self.relation_rules:
                raise ValueError("native concept families require relation_rules")
            if not self.non_ambiguity_constraints:
                raise ValueError("native concept families require non_ambiguity_constraints")
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
                {
                    "if": {
                        "properties": {"provenance": {"const": ConceptProvenanceCategory.ADOPTED.value}},
                        "required": ["provenance"],
                    },
                    "then": {
                        "required": ["authority", "authority_reference"],
                        "properties": {
                            "authority": {"type": "string", "minLength": 1},
                            "authority_reference": {"type": "string", "minLength": 1},
                        },
                    },
                },
                {
                    "if": {
                        "properties": {"provenance": {"const": ConceptProvenanceCategory.ADAPTED.value}},
                        "required": ["provenance"],
                    },
                    "then": {
                        "required": ["authority", "authority_reference"],
                        "properties": {
                            "authority": {"type": "string", "minLength": 1},
                            "authority_reference": {"type": "string", "minLength": 1},
                        },
                    },
                },
                {
                    "if": {
                        "properties": {"provenance": {"const": ConceptProvenanceCategory.NATIVE.value}},
                        "required": ["provenance"],
                    },
                    "then": {
                        "required": ["extension_scope", "relation_rules", "non_ambiguity_constraints"],
                        "properties": {
                            "extension_scope": {"type": "string", "minLength": 1},
                            "relation_rules": {"type": "array", "minItems": 1},
                            "non_ambiguity_constraints": {"type": "array", "minItems": 1},
                        },
                        "not": {
                            "anyOf": [
                                {"required": ["authority"]},
                                {"required": ["authority_reference"]},
                            ]
                        },
                    },
                },
            ]
        )
        return json_schema


class ConceptFamilyCatalogModel(ContractModel):
    schema_version: Literal[CONCEPT_FAMILIES_SCHEMA_VERSION] = CONCEPT_FAMILIES_SCHEMA_VERSION
    families: dict[NonEmptyString, ConceptFamilyDefinitionModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_family_keys(self) -> ConceptFamilyCatalogModel:
        if any(not family_id.strip() for family_id in self.families):
            raise ValueError("concept family identifiers must be non-empty")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        families_schema = json_schema.get("properties", {}).get("families")
        if isinstance(families_schema, dict):
            families_schema.setdefault("propertyNames", {"minLength": 1})
        return json_schema


class ReferenceModelSchemaBindingModel(ContractModel):
    contract_id: NonEmptyString
    schema_pointer: JsonPointerString
    instance_path: InstancePath


class ReferenceModelDefinitionModel(ContractModel):
    title: NonEmptyString
    description: NonEmptyString
    concept_family: ConceptFamilyId
    authoritative_schema: ReferenceModelSchemaBindingModel
    reused_schemas: list[ReferenceModelSchemaBindingModel] = Field(default_factory=list)
    key_fields: list[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_reference_model_definition(self) -> ReferenceModelDefinitionModel:
        if len(self.key_fields) != len(set(self.key_fields)):
            raise ValueError("reference model key_fields must not contain duplicates")

        authoritative_key = (
            self.authoritative_schema.contract_id,
            self.authoritative_schema.schema_pointer,
            self.authoritative_schema.instance_path,
        )
        reused_keys = [
            (binding.contract_id, binding.schema_pointer, binding.instance_path) for binding in self.reused_schemas
        ]
        if len(reused_keys) != len(set(reused_keys)):
            raise ValueError("reference model reused_schemas must not contain duplicate schema bindings")
        if authoritative_key in set(reused_keys):
            raise ValueError("reference model reused_schemas must not repeat authoritative_schema")
        return self


class ReferenceModelCatalogModel(ContractModel):
    schema_version: Literal[REFERENCE_MODELS_SCHEMA_VERSION] = REFERENCE_MODELS_SCHEMA_VERSION
    models: dict[NonEmptyString, ReferenceModelDefinitionModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_reference_models(self) -> ReferenceModelCatalogModel:
        known_families = _authoritative_concept_family_ids()
        unknown_families = {
            model.concept_family for model in self.models.values() if model.concept_family not in known_families
        }
        if unknown_families:
            unknown = ", ".join(sorted(unknown_families))
            raise ValueError(f"reference models include unknown concept families: {unknown}")

        known_contracts = _known_contract_ids()
        unknown_contracts = {
            binding.contract_id
            for model in self.models.values()
            for binding in (model.authoritative_schema, *model.reused_schemas)
            if binding.contract_id not in known_contracts
        }
        if unknown_contracts:
            unknown = ", ".join(sorted(unknown_contracts))
            raise ValueError(f"reference models include unknown contract ids: {unknown}")

        for model_id, model in self.models.items():
            _validate_reference_model_schema_binding(
                model_id=model_id,
                binding_label="authoritative_schema",
                binding=model.authoritative_schema,
                key_fields=model.key_fields,
            )
            for index, binding in enumerate(model.reused_schemas):
                _validate_reference_model_schema_binding(
                    model_id=model_id,
                    binding_label=f"reused_schemas[{index}]",
                    binding=binding,
                    key_fields=model.key_fields,
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
        models_schema = json_schema.get("properties", {}).get("models")
        if isinstance(models_schema, dict):
            models_schema.setdefault("propertyNames", {"minLength": 1})
        return json_schema


class ControlledVocabularyTermModel(ContractModel):
    title: NonEmptyString
    description: NonEmptyString


class ControlledVocabularyDefinitionModel(ContractModel):
    title: NonEmptyString
    description: NonEmptyString
    kind: Literal["enumeration", "vocabulary"]
    governed_scopes: list[NonEmptyString] = Field(default_factory=list)
    extension_policy: Literal["closed", "governed-extension"]
    extension_pattern: NonEmptyString | None = None
    terms: dict[ControlledVocabularyTermId, ControlledVocabularyTermModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_vocabulary_definition(self) -> ControlledVocabularyDefinitionModel:
        unknown_scopes = set(self.governed_scopes) - _CONTROLLED_VOCABULARY_GOVERNED_SCOPES
        if unknown_scopes:
            unknown = ", ".join(sorted(unknown_scopes))
            raise ValueError(f"controlled vocabulary includes unknown governed scopes: {unknown}")

        if len(self.governed_scopes) != len(set(self.governed_scopes)):
            raise ValueError("controlled vocabulary governed_scopes must not contain duplicates")

        if self.kind == "enumeration" and self.extension_policy != "closed":
            raise ValueError("enumeration controlled vocabularies must use extension_policy='closed'")

        if self.extension_policy == "closed":
            if self.extension_pattern is not None:
                raise ValueError("closed controlled vocabularies must not declare extension_pattern")
            return self

        if not self.governed_scopes:
            raise ValueError("governed-extension controlled vocabularies must declare governed_scopes")
        if self.extension_pattern is None:
            raise ValueError("governed-extension controlled vocabularies must declare extension_pattern")
        try:
            re.compile(self.extension_pattern)
        except re.error as exc:
            raise ValueError("controlled vocabulary extension_pattern must be a valid regex") from exc
        return self


class ControlledVocabularyCatalogModel(ContractModel):
    schema_version: Literal[CONTROLLED_VOCABULARIES_SCHEMA_VERSION] = CONTROLLED_VOCABULARIES_SCHEMA_VERSION
    vocabularies: dict[NonEmptyString, ControlledVocabularyDefinitionModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_vocabulary_catalog(self) -> ControlledVocabularyCatalogModel:
        scope_to_vocabulary: dict[str, str] = {}
        for vocabulary_id, definition in self.vocabularies.items():
            for scope in definition.governed_scopes:
                previous = scope_to_vocabulary.setdefault(scope, vocabulary_id)
                if previous != vocabulary_id:
                    raise ValueError(
                        f"governed scope '{scope}' is declared by multiple vocabularies: {previous}, {vocabulary_id}"
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
        vocabularies_schema = json_schema.get("properties", {}).get("vocabularies")
        if isinstance(vocabularies_schema, dict):
            vocabularies_schema.setdefault("propertyNames", {"minLength": 1})
        return json_schema


class SemanticBehaviorAssumptionModel(ContractModel):
    id: SemanticAssumptionId
    statement: NonEmptyString


class SemanticProfilePhaseModel(ContractModel):
    required_contracts: list[NonEmptyString] = Field(min_length=1)
    required_concept_families: list[ConceptFamilyId] = Field(min_length=1)
    required_bindings: list[ConceptBindingEntryModel] = Field(default_factory=list)
    behavior_assumptions: list[SemanticBehaviorAssumptionModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_phase_assumptions(self) -> SemanticProfilePhaseModel:
        if len(self.required_contracts) != len(set(self.required_contracts)):
            raise ValueError("semantic profile required_contracts must not contain duplicates")
        if len(self.required_concept_families) != len(set(self.required_concept_families)):
            raise ValueError("semantic profile required_concept_families must not contain duplicates")

        known_contracts = _known_contract_ids()
        unknown_contracts = set(self.required_contracts) - known_contracts
        if unknown_contracts:
            unknown = ", ".join(sorted(unknown_contracts))
            raise ValueError(f"semantic profile required_contracts include unknown contract ids: {unknown}")

        known_families = _authoritative_concept_family_ids()
        unknown_families = set(self.required_concept_families) - known_families
        if unknown_families:
            unknown = ", ".join(sorted(unknown_families))
            raise ValueError(f"semantic profile required_concept_families include unknown families: {unknown}")

        binding_scopes = [binding.scope for binding in self.required_bindings]
        if len(binding_scopes) != len(set(binding_scopes)):
            raise ValueError("semantic profile required_bindings must not contain duplicate scopes")

        undeclared_binding_families = {
            binding.family for binding in self.required_bindings if binding.family not in self.required_concept_families
        }
        if undeclared_binding_families:
            missing = ", ".join(sorted(undeclared_binding_families))
            raise ValueError(
                f"semantic profile required_bindings must use families declared in required_concept_families: {missing}"
            )

        assumption_ids = [assumption.id for assumption in self.behavior_assumptions]
        if len(assumption_ids) != len(set(assumption_ids)):
            raise ValueError("semantic profile behavior_assumptions must not contain duplicate ids")
        return self


class SemanticProfileModel(ContractModel):
    schema_version: Literal[SEMANTIC_PROFILE_SCHEMA_VERSION] = SEMANTIC_PROFILE_SCHEMA_VERSION
    profile_id: SemanticProfileId
    title: NonEmptyString
    description: NonEmptyString
    concept_catalog_version: Literal[CONCEPT_FAMILIES_SCHEMA_VERSION]
    authoring: SemanticProfilePhaseModel
    exchange: SemanticProfilePhaseModel
    processing: SemanticProfilePhaseModel
    execution: SemanticProfilePhaseModel

    @model_validator(mode="after")
    def _validate_phase_binding_scopes(self) -> SemanticProfileModel:
        for phase_name, allowed_scopes in _SEMANTIC_PROFILE_PHASE_ALLOWED_BINDING_SCOPES.items():
            phase = getattr(self, phase_name)
            declared_scopes = {binding.scope for binding in phase.required_bindings}
            invalid_scopes = declared_scopes - allowed_scopes
            if invalid_scopes:
                invalid = ", ".join(sorted(invalid_scopes))
                if allowed_scopes:
                    allowed = ", ".join(sorted(allowed_scopes))
                    raise ValueError(
                        f"semantic profile {phase_name} required_bindings include scopes outside the governed "
                        f"{phase_name} surfaces: {invalid}; allowed scopes: {allowed}"
                    )
                raise ValueError(
                    f"semantic profile {phase_name} does not define governed required_bindings surfaces: {invalid}"
                )
        return self


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@lru_cache(maxsize=1)
def _authoritative_concept_family_ids() -> frozenset[str]:
    catalog_path = _repo_root() / "contracts" / "concept-authority" / "concept-families-v1.json"
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog = ConceptFamilyCatalogModel.model_validate(payload)
    return frozenset(catalog.families)


@lru_cache(maxsize=1)
def _known_contract_ids() -> frozenset[str]:
    return frozenset(schema_bundle())


def _decode_json_pointer_segment(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def _resolve_schema_pointer(schema_root: dict[str, Any], pointer: str) -> dict[str, Any]:
    if not pointer.startswith("#/"):
        raise KeyError(pointer)

    current: Any = schema_root
    for raw_segment in pointer[2:].split("/"):
        segment = _decode_json_pointer_segment(raw_segment)
        if not isinstance(current, dict) or segment not in current:
            raise KeyError(pointer)
        current = current[segment]

    if not isinstance(current, dict):
        raise KeyError(pointer)
    return current


def _resolve_ref_schema(schema_root: dict[str, Any], schema_node: dict[str, Any]) -> dict[str, Any]:
    current = schema_node
    while "$ref" in current:
        ref = current["$ref"]
        if not isinstance(ref, str):
            raise KeyError(ref)
        current = _resolve_schema_pointer(schema_root, ref)
    return current


def _resolve_instance_path_schema(schema_root: dict[str, Any], instance_path: str) -> dict[str, Any]:
    current = schema_root
    for segment in instance_path.split("."):
        current = _resolve_ref_schema(schema_root, current)
        if segment == "*":
            additional_properties = current.get("additionalProperties")
            if not isinstance(additional_properties, dict):
                raise KeyError(instance_path)
            current = additional_properties
            continue

        properties = current.get("properties")
        if not isinstance(properties, dict) or segment not in properties or not isinstance(properties[segment], dict):
            raise KeyError(instance_path)
        current = properties[segment]
    return _resolve_ref_schema(schema_root, current)


def _validate_reference_model_schema_binding(
    *,
    model_id: str,
    binding_label: str,
    binding: ReferenceModelSchemaBindingModel,
    key_fields: list[str],
) -> None:
    schema_root = schema_bundle()[binding.contract_id]
    try:
        pointer_schema = _resolve_ref_schema(schema_root, _resolve_schema_pointer(schema_root, binding.schema_pointer))
    except KeyError as exc:
        raise ValueError(
            f"reference model {model_id} {binding_label} schema_pointer '{binding.schema_pointer}' "
            f"does not resolve within contract '{binding.contract_id}'"
        ) from exc

    try:
        instance_schema = _resolve_instance_path_schema(schema_root, binding.instance_path)
    except KeyError as exc:
        raise ValueError(
            f"reference model {model_id} {binding_label} instance_path '{binding.instance_path}' "
            f"does not resolve within contract '{binding.contract_id}'"
        ) from exc

    if pointer_schema != instance_schema:
        raise ValueError(
            f"reference model {model_id} {binding_label} instance_path '{binding.instance_path}' "
            f"does not resolve to schema_pointer '{binding.schema_pointer}' in contract '{binding.contract_id}'"
        )

    properties = pointer_schema.get("properties")
    if not isinstance(properties, dict):
        raise ValueError(
            f"reference model {model_id} {binding_label} schema_pointer '{binding.schema_pointer}' "
            "must resolve to an object schema with properties"
        )

    missing_key_fields = [field for field in key_fields if field not in properties]
    if missing_key_fields:
        missing = ", ".join(sorted(missing_key_fields))
        raise ValueError(
            f"reference model {model_id} key_fields are not declared by schema_pointer "
            f"'{binding.schema_pointer}' in contract '{binding.contract_id}': {missing}"
        )


def _scope_is_present(model: ContractModel, scope: str) -> bool:
    current: Any = model
    for segment in scope.split("."):
        if not isinstance(current, BaseModel):
            return False
        if segment not in type(current).model_fields:
            return False
        current = getattr(current, segment)
        if current is None:
            return False
    return True


def _validate_controlled_vocabulary_terms(scope: str, values: list[str]) -> None:
    if not values:
        return
    from .controlled_vocabularies import validate_controlled_vocabulary_scope_values

    validate_controlled_vocabulary_scope_values(scope, values)


def _validate_unique_string_values(field_name: str, values: list[str]) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        joined = ", ".join(duplicates)
        raise ValueError(f"{field_name} must not contain duplicate values: {joined}")


def _validate_canonical_concept_bindings(model: ContractModel, *, allowed_scopes: frozenset[str]) -> None:
    family_ids = _authoritative_concept_family_ids()
    for binding in getattr(model, "concept_bindings", ()):
        if binding.family not in family_ids:
            raise ValueError(f"concept_bindings family '{binding.family}' is not defined in concept-families-v1")
        if binding.scope not in allowed_scopes:
            allowed = ", ".join(sorted(allowed_scopes))
            raise ValueError(
                f"concept_bindings scope '{binding.scope}' is not a governed manifest vocabulary surface; "
                f"allowed scopes: {allowed}"
            )
        if not _scope_is_present(model, binding.scope):
            raise ValueError(
                f"concept_bindings scope '{binding.scope}' does not resolve to a declared field in this manifest"
            )


def _backend_profile_schema_for_bundle() -> dict[str, Any]:
    """Lazily import :class:`BackendProfileModel` to avoid an import cycle.

    ``backend_profiles`` imports :class:`ContractModel` and ``NonEmptyString``
    from this module, so eager import at module load would cycle. The
    deferred import here keeps the schema bundle wired up while letting
    ``backend_profiles`` build on the same closed-world primitives the rest
    of the contracts surface uses.
    """

    from .backend_profiles import BackendProfileModel

    return BackendProfileModel.model_json_schema()


def _event_stream_schema(title: str, item_schema: dict[str, Any]) -> dict[str, Any]:
    item_schema = dict(item_schema)
    defs = item_schema.pop("$defs", None)
    schema = {
        _JSON_SCHEMA_KEY: _JSON_SCHEMA_DRAFT_2020_12,
        "title": title,
        "type": "array",
        "items": item_schema,
    }
    if defs:
        schema["$defs"] = defs
    return schema


def schema_bundle() -> dict[str, dict[str, Any]]:
    """Return the repo-published JSON Schemas for external contracts."""

    bundle = {
        "aces-semantic-invariants-v1": _aces_semantic_invariant_profile_schema_for_bundle(),
        "sdl-authoring-input-v1": Scenario.model_json_schema(),
        "instantiated-scenario-v1": InstantiatedScenario.model_json_schema(),
        "scenario-instantiation-request-v1": InstantiationRequestModel.model_json_schema(),
        "backend-manifest-v2": BackendManifestV2Model.model_json_schema(),
        "processor-manifest-v2": ProcessorManifestV2Model.model_json_schema(),
        "concept-families-v1": ConceptFamilyCatalogModel.model_json_schema(),
        "reference-models-v1": ReferenceModelCatalogModel.model_json_schema(),
        "controlled-vocabularies-v1": ControlledVocabularyCatalogModel.model_json_schema(),
        "semantic-profile-v1": SemanticProfileModel.model_json_schema(),
        "backend-profile-v1": _backend_profile_schema_for_bundle(),
        "experiment-apparatus-context-v1": ExperimentApparatusContextModel.model_json_schema(),
        "experiment-run-v1": ExperimentRunModel.model_json_schema(),
        "experiment-study-v1": ExperimentStudyModel.model_json_schema(),
        "experiment-task-v1": ExperimentTaskModel.model_json_schema(),
        "provisioning-plan-v1": ProvisioningPlanModel.model_json_schema(),
        "orchestration-plan-v1": OrchestrationPlanModel.model_json_schema(),
        "evaluation-plan-v1": EvaluationPlanModel.model_json_schema(),
        "runtime-snapshot-v1": RuntimeSnapshotEnvelopeModel.model_json_schema(),
        "workflow-result-envelope-v1": WorkflowExecutionStateModel.model_json_schema(),
        "workflow-history-event-stream-v1": _event_stream_schema(
            "WorkflowHistoryEventStream",
            WorkflowHistoryEventModel.model_json_schema(),
        ),
        "workflow-cancellation-request-v1": WorkflowCancellationRequestModel.model_json_schema(),
        "evaluation-result-envelope-v1": EvaluationResultStateModel.model_json_schema(),
        "evaluation-history-event-stream-v1": _event_stream_schema(
            "EvaluationHistoryEventStream",
            EvaluationHistoryEventModel.model_json_schema(),
        ),
        "participant-episode-state-envelope-v1": ParticipantEpisodeStateModel.model_json_schema(),
        "participant-episode-history-event-stream-v1": _event_stream_schema(
            "ParticipantEpisodeHistoryEventStream",
            ParticipantEpisodeHistoryEventModel.model_json_schema(),
        ),
        "participant-behavior-history-event-stream-v1": _event_stream_schema(
            "ParticipantBehaviorHistoryEventStream",
            ParticipantBehaviorHistoryEventModel.model_json_schema(),
        ),
        "operation-receipt-v1": OperationReceiptModel.model_json_schema(),
        "operation-status-v1": OperationStatusModel.model_json_schema(),
    }
    for contract_id, json_schema in bundle.items():
        _attach_experiment_datetime_invariants(contract_id, json_schema)
        _attach_json_schema_metadata(contract_id, json_schema)
        _attach_aces_semantic_profile(contract_id, json_schema)
    known_contract_ids = frozenset(bundle)
    for contract_id, json_schema in bundle.items():
        _validate_aces_semantic_invariant_annotations(
            contract_id=contract_id,
            json_schema=json_schema,
            known_contract_ids=known_contract_ids,
        )
    return bundle


__all__ = [
    "AcesSemanticInvariantEntryModel",
    "AcesSemanticInvariantInputModel",
    "AcesSemanticInvariantProfileModel",
    "AcesSemanticInvariantProfileReferenceModel",
    "BACKEND_MANIFEST_V2_SCHEMA_VERSION",
    "ApparatusIdentityModel",
    "BackendCompatibilityModel",
    "BackendManifestV2Model",
    "BackendCapabilitiesV2Model",
    "CONCEPT_FAMILIES_SCHEMA_VERSION",
    "ConceptBindingEntryModel",
    "ConceptFamilyCatalogModel",
    "ConceptFamilyDefinitionModel",
    "ConceptFamilyId",
    "ConceptProvenanceCategory",
    "CONTROLLED_VOCABULARIES_SCHEMA_VERSION",
    "ControlledVocabularyCatalogModel",
    "ControlledVocabularyDefinitionModel",
    "ControlledVocabularyTermId",
    "ControlledVocabularyTermModel",
    "ContractModel",
    "ExperimentAnalysisPlanModel",
    "ExperimentApparatusComponentModel",
    "ExperimentApparatusConstraintModel",
    "ExperimentApparatusContextModel",
    "ExperimentArtifactRefModel",
    "ExperimentBackendReferenceModel",
    "ExperimentChecksumModel",
    "ExperimentClockContextModel",
    "ExperimentConditionAssignmentParameterModel",
    "ExperimentConditionAssignmentReferenceModel",
    "ExperimentEvidenceReferenceModel",
    "ExperimentEvaluationProtocolModel",
    "ExperimentInvalidationModel",
    "ExperimentManifestReferenceModel",
    "ExperimentMeasurementChannelReferenceModel",
    "ExperimentMetricDefinitionModel",
    "ExperimentMissingDataPolicyModel",
    "ExperimentMultipleComparisonPolicyModel",
    "ExperimentParameterModel",
    "ExperimentProcessorReferenceModel",
    "ExperimentReferenceModel",
    "ExperimentResultSummaryModel",
    "ExperimentRunAllocationPlanModel",
    "ExperimentRunModel",
    "ExperimentScenarioReferenceModel",
    "ExperimentScenarioSnapshotReferenceModel",
    "ExperimentSplitAndLeakageControlsModel",
    "ExperimentStatisticalMethodModel",
    "ExperimentStochasticControlModel",
    "ExperimentStudyFactorModel",
    "ExperimentStudyMembershipModel",
    "ExperimentStudyModel",
    "ExperimentTaskReferenceModel",
    "ExperimentTaskModel",
    "ExperimentUncertaintyMethodModel",
    "ExperimentValidityNoteModel",
    "EXPERIMENT_APPARATUS_CONTEXT_SCHEMA_VERSION",
    "EXPERIMENT_RUN_SCHEMA_VERSION",
    "EXPERIMENT_STUDY_SCHEMA_VERSION",
    "EXPERIMENT_TASK_SCHEMA_VERSION",
    "EvaluationHistoryEventModel",
    "EvaluationPlanModel",
    "EvaluationResultStateModel",
    "EVALUATION_STATE_SCHEMA_VERSION",
    "EvaluatorCapabilitiesModel",
    "InstantiationRequestModel",
    "OPERATION_SCHEMA_VERSION",
    "OperationReceiptModel",
    "OperationStatusModel",
    "OrchestrationPlanModel",
    "OrchestratorCapabilitiesModel",
    "PARTICIPANT_EPISODE_STATE_SCHEMA_VERSION",
    "ParticipantActionEffectResultModel",
    "ParticipantActionPreconditionResultModel",
    "ParticipantActionResultModel",
    "ParticipantAttributionCandidateModel",
    "ParticipantAttributionEdgeModel",
    "ParticipantAttributionEvidenceBasisModel",
    "ParticipantAttributionOrderingBasisModel",
    "ParticipantBehaviorHistoryEventModel",
    "ParticipantEpisodeHistoryEventModel",
    "ParticipantEpisodeStateModel",
    "ParticipantOutcomeInterpretationRecordModel",
    "ParticipantOutcomeSourceRecordModel",
    "ParticipantOutcomeTargetRecordModel",
    "ParticipantRuntimeCapabilitiesModel",
    "ParticipantTemporalRuntimeContextModel",
    "PlanOperationModel",
    "ProcessorFeature",
    "PROCESSOR_MANIFEST_V2_SCHEMA_VERSION",
    "ProcessorManifestV2Model",
    "ProcessorCompatibilityModel",
    "ProcessorCapabilitiesV2Model",
    "ProvisionerCapabilitiesModel",
    "ProvisioningPlanModel",
    "RealizationSupportDeclarationModel",
    "RealizationSupportMode",
    "ReferenceModelCatalogModel",
    "ReferenceModelDefinitionModel",
    "ReferenceModelSchemaBindingModel",
    "REFERENCE_MODELS_SCHEMA_VERSION",
    "RUNTIME_SNAPSHOT_SCHEMA_VERSION",
    "RuntimeSnapshotEnvelopeModel",
    "SCENARIO_INSTANTIATION_REQUEST_SCHEMA_VERSION",
    "SEMANTIC_PROFILE_SCHEMA_VERSION",
    "schema_bundle",
    "SemanticBehaviorAssumptionModel",
    "SemanticProfileModel",
    "SemanticProfilePhaseModel",
    "SnapshotEntryModel",
    "WorkflowCancellationRequestModel",
    "WORKFLOW_CANCELLATION_REQUEST_SCHEMA_VERSION",
    "WorkflowExecutionStateModel",
    "WorkflowFeature",
    "WorkflowHistoryEventModel",
    "WorkflowStatePredicateFeature",
    "WorkflowStepStateModel",
    "WORKFLOW_STATE_SCHEMA_VERSION",
    "validate_aces_semantic_invariant_annotations",
    "validate_experiment_apparatus_context_against_manifests",
    "validate_experiment_apparatus_context_archival_datetimes",
    "validate_experiment_run_against_task",
    "validate_experiment_run_archival_datetimes",
    "validate_experiment_study_against_tasks_and_runs",
    "validate_experiment_study_archival_datetimes",
    "validate_experiment_task_archival_datetimes",
]
