"""ACT-604 portable participant information-state contracts and joins."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from pydantic import Field, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from ..versions import PARTICIPANT_INFORMATION_RECONSTRUCTION_PROFILE_V1_SCHEMA_VERSION
from .base import ContractModel, NonEmptyString, PrefixedDigestString, SemanticProfileId
from .participant_decision_state_cut import (
    ParticipantDecisionSurfaceSequenceCutModel,
    ParticipantDecisionSurfaceStateCutModel,
)
from .participant_envelopes import ParticipantRuntimeBaseEnvelopeModel
from .participant_information_state_sources import require_source_coordinate, validate_resolved_source
from .participant_observation import ParticipantObservationEnvelopeModel
from .participant_runtime import ParticipantRuntimeInformationGuarantee
from .schema_invariants import _add_raes_invariant

if TYPE_CHECKING:
    from .participant_decision_surface_v2 import ParticipantDecisionSurfaceV2Model

ParticipantInformationSourceContract = Literal[
    "participant-observation-envelope-v1",
    "participant-context-view-v1",
    "participant-shared-state-record-v1",
    "participant-behavior-history-event-stream-v1",
    "participant-episode-state-envelope-v1",
]

ParticipantInformationSourceRelation = Literal[
    "authored_initial",
    "observed",
    "derived",
    "disclosed",
    "shared_state_projection",
]

ParticipantInformationMemoryScope = Literal[
    "episode_local_reset",
    "persistent_across_episodes",
]

ParticipantInformationOrderSemantics = Literal[
    "sequence_prefix",
    "causal_frontier",
]

ParticipantInformationSourceKey = tuple[str, str]


@dataclass(frozen=True)
class ParticipantInformationStateSourceCoordinate:
    """Trusted resolver result binding one source to the record's governed cut."""

    participant_address: str
    episode_id: str
    state_cut: ParticipantDecisionSurfaceStateCutModel
    audience_scope_ref: str
    visibility_projection_ref: str
    projection_policy_revision: str
    redaction_policy_ref: str
    redaction_policy_revision: str


@dataclass(frozen=True)
class ParticipantInformationStateValidationContext:
    """Non-wire authority needed to validate one information-state claim."""

    occurrence_histories: Mapping[str, Sequence[ParticipantObservationEnvelopeModel]]
    resolved_sources: Mapping[ParticipantInformationSourceKey, object]
    source_coordinates: Mapping[ParticipantInformationSourceKey, ParticipantInformationStateSourceCoordinate]
    proof_digests: Mapping[str, str]
    decision_surfaces: Sequence[ParticipantDecisionSurfaceV2Model] = field(default_factory=tuple)


ParticipantInformationStateContextResolver = Callable[
    ["ParticipantInformationStateRecordModel", object | None],
    ParticipantInformationStateValidationContext | None,
]


class ParticipantInformationStateSourceRefModel(ContractModel):
    """One closed typed relation to an incumbent information source."""

    contract_id: ParticipantInformationSourceContract
    ref: NonEmptyString
    relation: ParticipantInformationSourceRelation


class ParticipantInformationReconstructionProfileModel(ContractModel):
    """One immutable, non-executable reconstruction profile declaration."""

    schema_version: Literal[PARTICIPANT_INFORMATION_RECONSTRUCTION_PROFILE_V1_SCHEMA_VERSION]
    profile_id: SemanticProfileId
    title: NonEmptyString
    description: NonEmptyString
    algorithm_id: NonEmptyString
    algorithm_version: NonEmptyString
    information_state_schema_version: NonEmptyString
    projection_version: NonEmptyString
    determinism_basis: Literal["exact_occurrence_prefix_and_proof_digest"]
    accepted_input_contracts: list[ParticipantInformationSourceContract] = Field(min_length=1)
    accepted_order_semantics: list[ParticipantInformationOrderSemantics] = Field(min_length=1)
    fixture_format: NonEmptyString
    proof_artifact_format: NonEmptyString
    normative_artifact_ref: NonEmptyString
    normative_artifact_digest: PrefixedDigestString

    @model_validator(mode="after")
    def _validate_closed_profile(self) -> ParticipantInformationReconstructionProfileModel:
        for field_name in ("accepted_input_contracts", "accepted_order_semantics"):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} values must be unique")
        return self


class ParticipantInformationStateRecordModel(ParticipantRuntimeBaseEnvelopeModel):
    """Immutable participant-relative information state at one exact cut."""

    schema_name: Literal["raes.participant_runtime.information_state"]
    schema_version: Literal["1.0.0"]
    event_type: Literal["participant_information_state"]
    participant_address: NonEmptyString
    episode_id: NonEmptyString
    information_state_ref: NonEmptyString
    information_state_digest: PrefixedDigestString
    payload_ref: NonEmptyString
    state_cut: ParticipantDecisionSurfaceStateCutModel
    participant_memory_scope: ParticipantInformationMemoryScope
    memory_reset_authority_ref: NonEmptyString | None = None
    audience_scope_ref: NonEmptyString
    visibility_projection_ref: NonEmptyString
    projection_version: NonEmptyString
    projection_policy_revision: NonEmptyString
    redaction_policy_ref: NonEmptyString
    redaction_policy_revision: NonEmptyString
    information_guarantee: ParticipantRuntimeInformationGuarantee
    source_refs: list[ParticipantInformationStateSourceRefModel] = Field(min_length=1)
    occurrence_history_ref: NonEmptyString | None = None
    reconstruction_profile_ref: NonEmptyString | None = None
    reconstruction_algorithm_id: NonEmptyString | None = None
    reconstruction_algorithm_version: NonEmptyString | None = None
    reconstruction_proof_ref: NonEmptyString | None = None
    reconstructed_state_digest: PrefixedDigestString | None = None
    occurrence_order_witness_ref: NonEmptyString | None = None
    loss_disclosures: list[NonEmptyString] = Field(default_factory=list)
    predecessor_information_state_refs: list[NonEmptyString] = Field(default_factory=list)
    supersedes_information_state_ref: NonEmptyString | None = None

    @model_validator(mode="after")
    def _validate_information_state(self) -> ParticipantInformationStateRecordModel:
        source_keys = [(source.contract_id, source.ref) for source in self.source_refs]
        if len(source_keys) != len(set(source_keys)):
            raise ValueError("information state source refs must be unique")
        if len(self.predecessor_information_state_refs) != len(set(self.predecessor_information_state_refs)):
            raise ValueError("predecessor information state refs must be unique")
        if self.information_state_ref in self.predecessor_information_state_refs:
            raise ValueError("information state cannot be its own predecessor")
        if self.supersedes_information_state_ref == self.information_state_ref:
            raise ValueError("information state cannot supersede itself")

        if self.participant_memory_scope == "episode_local_reset":
            if self.memory_reset_authority_ref is None:
                raise ValueError("episode_local_reset requires memory_reset_authority_ref")
        elif self.memory_reset_authority_ref is not None:
            raise ValueError("persistent_across_episodes must not claim a reset authority")

        if self.information_guarantee in {"history_consistent", "perfect_recall"}:
            required = {
                "occurrence_history_ref": self.occurrence_history_ref,
                "reconstruction_profile_ref": self.reconstruction_profile_ref,
                "reconstruction_algorithm_id": self.reconstruction_algorithm_id,
                "reconstruction_algorithm_version": self.reconstruction_algorithm_version,
                "reconstruction_proof_ref": self.reconstruction_proof_ref,
                "reconstructed_state_digest": self.reconstructed_state_digest,
            }
            missing = sorted(name for name, value in required.items() if value is None)
            if missing:
                raise ValueError("strong information state requires: " + ", ".join(missing))
            if self.reconstructed_state_digest != self.information_state_digest:
                raise ValueError("reconstructed_state_digest must equal information_state_digest")
        if self.information_guarantee == "perfect_recall" and self.occurrence_order_witness_ref is None:
            raise ValueError("perfect_recall requires occurrence_order_witness_ref")
        if self.information_guarantee == "lossy_projection" and not self.loss_disclosures:
            raise ValueError("lossy_projection requires loss_disclosures")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler.resolve_ref_schema(handler(core_schema))
        strong_fields = (
            "occurrence_history_ref",
            "reconstruction_profile_ref",
            "reconstruction_algorithm_id",
            "reconstruction_algorithm_version",
            "reconstruction_proof_ref",
            "reconstructed_state_digest",
        )
        json_schema.setdefault("allOf", []).extend(
            [
                {
                    "if": {
                        "properties": {"information_guarantee": {"enum": ["history_consistent", "perfect_recall"]}},
                        "required": ["information_guarantee"],
                    },
                    "then": {
                        "required": list(strong_fields),
                        "properties": {field_name: {"type": "string", "minLength": 1} for field_name in strong_fields},
                    },
                },
                {
                    "if": {
                        "properties": {"information_guarantee": {"const": "perfect_recall"}},
                        "required": ["information_guarantee"],
                    },
                    "then": {
                        "required": ["occurrence_order_witness_ref"],
                        "properties": {"occurrence_order_witness_ref": {"type": "string", "minLength": 1}},
                    },
                },
                {
                    "if": {
                        "properties": {"information_guarantee": {"const": "lossy_projection"}},
                        "required": ["information_guarantee"],
                    },
                    "then": {
                        "required": ["loss_disclosures"],
                        "properties": {"loss_disclosures": {"minItems": 1}},
                    },
                },
            ]
        )
        _add_raes_invariant(
            json_schema,
            "participant-information-state-context-resolution",
            "Strong information-state claims resolve one profile, occurrence history, typed source set, proof "
            "digest, and exact participant/episode/cut/projection/memory coordinate.",
            validator=("raes_contracts.contracts.validate_participant_information_state_context"),
            inputs=[{"contract_id": "participant-information-state-record-v1", "instance_path": "#"}],
        )
        return json_schema


def validate_participant_information_state_context(
    record: ParticipantInformationStateRecordModel,
    *,
    reconstruction_profiles: Mapping[str, ParticipantInformationReconstructionProfileModel],
    occurrence_histories: Mapping[str, Sequence[ParticipantObservationEnvelopeModel]],
    resolved_sources: Mapping[tuple[str, str], object],
    proof_digests: Mapping[str, str],
    source_coordinates: Mapping[
        ParticipantInformationSourceKey,
        ParticipantInformationStateSourceCoordinate,
    ]
    | None = None,
    decision_surfaces: Sequence[ParticipantDecisionSurfaceV2Model] = (),
) -> None:
    """Resolve ACT-604's cross-contract exact-cut and strong-claim conditions."""

    declared_source_keys = {(source.contract_id, source.ref) for source in record.source_refs}
    profile: ParticipantInformationReconstructionProfileModel | None = None
    if record.information_guarantee in {"history_consistent", "perfect_recall"}:
        profile_ref = record.reconstruction_profile_ref
        if profile_ref is None or profile_ref not in reconstruction_profiles:
            raise ValueError("information state reconstruction profile does not resolve")
        profile = reconstruction_profiles[profile_ref]
        if profile.profile_id != profile_ref:
            raise ValueError("information state reconstruction profile identity does not match")
        if profile.information_state_schema_version != record.schema_version:
            raise ValueError("information state schema version does not match reconstruction profile")
        if profile.projection_version != record.projection_version:
            raise ValueError("information state projection version does not match reconstruction profile")
        if (
            profile.algorithm_id != record.reconstruction_algorithm_id
            or profile.algorithm_version != record.reconstruction_algorithm_version
        ):
            raise ValueError("information state reconstruction algorithm does not match profile")
        if record.state_cut.cut_kind not in profile.accepted_order_semantics:
            raise ValueError("information state cut order is not admitted by reconstruction profile")

        history_ref = record.occurrence_history_ref
        if history_ref is None or history_ref not in occurrence_histories:
            raise ValueError("information state occurrence history does not resolve")
        history = occurrence_histories[history_ref]
        if not history:
            raise ValueError("strong information state requires a non-empty occurrence history")
        for observation in history:
            if ("participant-observation-envelope-v1", observation.observation_ref) not in declared_source_keys:
                raise ValueError("strong information state must preserve every occurrence as a typed source ref")
            if observation.participant_address != record.participant_address:
                raise ValueError("information state occurrence participant does not match")
            if observation.episode_id != record.episode_id:
                raise ValueError("information state occurrence episode does not match")
            if observation.action_observation_history_ref != history_ref:
                raise ValueError("information state occurrence history ref does not match")
            if observation.visibility_projection_ref != record.visibility_projection_ref:
                raise ValueError("information state occurrence visibility projection does not match")
            if isinstance(record.state_cut, ParticipantDecisionSurfaceSequenceCutModel) and (
                observation.sequence_number is None or observation.sequence_number > record.state_cut.anchor_order
            ):
                raise ValueError("information state occurrence lies after the exact sequence cut")

    governed_source_coordinates = source_coordinates or {}
    for source in record.source_refs:
        key = (source.contract_id, source.ref)
        if profile is not None and source.contract_id not in profile.accepted_input_contracts:
            raise ValueError("information state source contract is not admitted by profile")
        if key not in resolved_sources:
            raise ValueError("information state source ref does not resolve")
        require_source_coordinate(record, key, governed_source_coordinates)
        validate_resolved_source(record, source, resolved_sources[key])

    if profile is not None:
        proof_ref = record.reconstruction_proof_ref
        if proof_ref is None or proof_ref not in proof_digests:
            raise ValueError("information state reconstruction proof does not resolve")
        if proof_digests[proof_ref] != record.information_state_digest:
            raise ValueError("information state proof digest does not match claimed digest")

    for surface in decision_surfaces:
        if surface.participant_view.information_state_ref != record.information_state_ref:
            continue
        assurance = surface.assurance
        view = surface.participant_view
        if view.participant_address != record.participant_address or view.episode_id != record.episode_id:
            raise ValueError("decision surface information-state identity does not match")
        if assurance.audience_scope_ref != record.audience_scope_ref:
            raise ValueError("decision surface information-state audience scope does not match")
        if assurance.derivation_anchor.state_cut != record.state_cut:
            raise ValueError("decision surface information-state cut does not match")
        if assurance.projection_policy_revision != record.projection_policy_revision:
            raise ValueError("decision surface information-state projection revision does not match")
        if assurance.visibility_projection_ref != record.visibility_projection_ref:
            raise ValueError("decision surface information-state visibility projection does not match")
        if assurance.participant_memory_scope != record.participant_memory_scope:
            raise ValueError("decision surface information-state memory scope does not match")
        if assurance.memory_reset_authority_ref != record.memory_reset_authority_ref:
            raise ValueError("decision surface information-state reset authority does not match")
        if view.redaction_policy_ref != record.redaction_policy_ref:
            raise ValueError("decision surface information-state redaction policy does not match")


def validate_participant_information_state_resolved_context(
    record: ParticipantInformationStateRecordModel,
    resolver: ParticipantInformationStateContextResolver | None,
    scope: object | None = None,
) -> None:
    """Fail closed and apply the governed contextual invariant in production."""

    if resolver is None:
        raise ValueError("participant information-state context resolver is required")
    try:
        context = resolver(record, scope)
    except Exception as exc:
        raise ValueError("participant information-state context resolution failed") from exc
    if not isinstance(context, ParticipantInformationStateValidationContext):
        raise ValueError("participant information-state context did not resolve")
    if any(
        not isinstance(coordinate, ParticipantInformationStateSourceCoordinate)
        for coordinate in context.source_coordinates.values()
    ):
        raise ValueError("participant information-state source coordinate resolution is invalid")

    reconstruction_profiles: dict[str, ParticipantInformationReconstructionProfileModel] = {}
    if record.reconstruction_profile_ref is not None:
        from ..participant_information_reconstruction_profiles import (
            load_participant_information_reconstruction_profile,
        )

        profile = load_participant_information_reconstruction_profile(record.reconstruction_profile_ref)
        reconstruction_profiles[profile.profile_id] = profile

    try:
        validate_participant_information_state_context(
            record,
            reconstruction_profiles=reconstruction_profiles,
            occurrence_histories=context.occurrence_histories,
            resolved_sources=context.resolved_sources,
            source_coordinates=context.source_coordinates,
            proof_digests=context.proof_digests,
            decision_surfaces=context.decision_surfaces,
        )
    except (AttributeError, KeyError, TypeError) as exc:
        raise ValueError("participant information-state resolved context is malformed") from exc


__all__ = (
    "ParticipantInformationStateContextResolver",
    "ParticipantInformationReconstructionProfileModel",
    "ParticipantInformationStateRecordModel",
    "ParticipantInformationStateSourceCoordinate",
    "ParticipantInformationStateSourceRefModel",
    "ParticipantInformationStateValidationContext",
    "validate_participant_information_state_context",
    "validate_participant_information_state_resolved_context",
)
