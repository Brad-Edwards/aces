"""Participant runtime envelope contracts (lifecycle, observation, shared state, joint action, time)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from ..participant_behavior import (
    ParticipantAdmissionDisposition,
    ParticipantPhaseRealization,
    ParticipantRuntimeLifecyclePhase,
)
from .base import (
    ClosedUnitIntervalFloat,
    ContractModel,
    NonEmptyString,
    NonNegativeInteger,
    PositiveInteger,
    PrefixedDigestString,
    Rfc3339DateTimeString,
)
from .participant_runtime import (
    ParticipantRuntimeAtomicityScope,
    ParticipantRuntimeConflictClass,
    ParticipantRuntimeConflictPolicy,
    ParticipantRuntimeDeliveryBasis,
    ParticipantRuntimeInformationGuarantee,
    ParticipantRuntimeIsolationGuarantee,
    ParticipantRuntimeJointActionConflictPolicy,
    ParticipantRuntimeMappingLoss,
    ParticipantRuntimeOrderingBasis,
    ParticipantRuntimeTimeClaimStrength,
    ParticipantRuntimeTimeManagementMode,
)


class EventClassificationModel(ContractModel):
    """ACES-native normalized event classification tuple (ADR-054)."""

    category_uid: int
    category_name: NonEmptyString
    class_uid: int
    class_name: NonEmptyString
    activity_id: int
    activity_name: NonEmptyString
    type_uid: int
    type_name: NonEmptyString
    severity_id: int
    severity: NonEmptyString


class SourceStatusModel(ContractModel):
    """Normalized source status claim for one participant runtime record."""

    status_id: int
    status: NonEmptyString
    status_code: NonEmptyString
    status_detail: NonEmptyString
    source_status_label: NonEmptyString
    source_status_mapping: NonEmptyString


class SourcePipelineModel(ContractModel):
    """Source product, identity, and pipeline-time facts for a mapped record."""

    product_ref: NonEmptyString
    product_version: NonEmptyString | None = None
    log_provider: NonEmptyString | None = None
    log_source: NonEmptyString | None = None
    log_name: NonEmptyString | None = None
    original_event_uid: NonEmptyString | None = None
    original_time: Rfc3339DateTimeString | None = None
    processed_time: Rfc3339DateTimeString | None = None
    logged_time: Rfc3339DateTimeString | None = None
    transmit_time: Rfc3339DateTimeString | None = None
    correlation_uid: NonEmptyString | None = None
    sequence: NonNegativeInteger | None = None


class RawDataIntegrityModel(ContractModel):
    """Hash, size, and truncation facts for raw data behind a runtime claim."""

    raw_data_hash: PrefixedDigestString | None = None
    raw_data_hash_algorithm: NonEmptyString | None = None
    raw_data_size: NonNegativeInteger | None = None
    raw_data_is_truncated: bool | None = None
    raw_data_untruncated_size: NonNegativeInteger | None = None


class ParticipantRuntimeBaseEnvelopeModel(ContractModel):
    """Shared ADR-054 base envelope for participant-runtime family carriers.

    Every published carrier in the ``participant-runtime`` family embeds this
    envelope exactly once: identity, classification and source status,
    participant/episode scoping, the three distinct timestamps with clock
    authority, ordering, actor/source refs, raw-data integrity, confidence,
    provenance/evidence refs, and the marking surface. No carrier redefines
    local identity, versioning, marking, or extension semantics.
    """

    event_id: NonEmptyString
    schema_name: NonEmptyString
    schema_version: NonEmptyString
    event_type: NonEmptyString
    extension_policy: NonEmptyString
    event_classification: EventClassificationModel | None = None
    source_status: SourceStatusModel | None = None
    participant_address: NonEmptyString | None = None
    episode_id: NonEmptyString | None = None
    sequence_number: NonNegativeInteger | None = None
    occurred_at: Rfc3339DateTimeString
    recorded_at: Rfc3339DateTimeString
    ingested_at: Rfc3339DateTimeString
    clock_authority: NonEmptyString
    temporal_context: NonEmptyString | None = None
    ordering_basis: ParticipantRuntimeOrderingBasis
    logical_order_ref: NonEmptyString | None = None
    predecessor_event_refs: list[NonEmptyString] = Field(default_factory=list)
    actor_ref: NonEmptyString
    producer_ref: NonEmptyString
    source_system_ref: NonEmptyString | None = None
    source_record_ref: NonEmptyString | None = None
    source_raw_ref: NonEmptyString | None = None
    source_pipeline: SourcePipelineModel | None = None
    raw_data_integrity: RawDataIntegrityModel | None = None
    confidence: ClosedUnitIntervalFloat | None = None
    provenance_refs: list[NonEmptyString] = Field(default_factory=list)
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    marking_definition_refs: list[NonEmptyString] = Field(default_factory=list)
    object_marking_refs: list[NonEmptyString] = Field(default_factory=list)
    markings: list[NonEmptyString] = Field(default_factory=list)
    granular_markings: dict[NonEmptyString, list[NonEmptyString]] = Field(default_factory=dict)
    redaction_policy_ref: NonEmptyString | None = None
    authorization_scope: NonEmptyString


class ParticipantLifecycleEventModel(ParticipantRuntimeBaseEnvelopeModel):
    """RUN-306 lifecycle boundary record for one participant action event."""

    phase: ParticipantRuntimeLifecyclePhase
    phase_realization: ParticipantPhaseRealization
    admission_disposition: ParticipantAdmissionDisposition | None = None
    operation_ref: NonEmptyString | None = None
    action_ref: NonEmptyString | None = None
    action_contract_ref: NonEmptyString | None = None
    command_ref: NonEmptyString | None = None
    actor_provenance: NonEmptyString
    action_validity_basis_ref: NonEmptyString | None = None
    observation_refs: list[NonEmptyString] = Field(default_factory=list)
    shared_state_read_refs: list[NonEmptyString] = Field(default_factory=list)
    shared_state_write_refs: list[NonEmptyString] = Field(default_factory=list)
    emitted_state_update_refs: list[NonEmptyString] = Field(default_factory=list)
    attribution_edge_refs: list[NonEmptyString] = Field(default_factory=list)
    outcome_interpretation_refs: list[NonEmptyString] = Field(default_factory=list)
    joint_action_set_ref: NonEmptyString | None = None
    source_status_label: NonEmptyString | None = None
    mapping_loss: ParticipantRuntimeMappingLoss | None = None
    mapping_loss_detail: NonEmptyString | None = None


class ParticipantObservationLossDescriptorModel(ContractModel):
    """Declared projection-loss facts for one participant-visible observation."""

    kind: NonEmptyString
    fields_redacted: list[NonEmptyString] = Field(default_factory=list)


class ParticipantObservationStochasticContextModel(ContractModel):
    """Seed and randomization-policy references behind one observation."""

    seed_ref: NonEmptyString | None = None
    randomization_policy_ref: NonEmptyString | None = None


class ParticipantObservationEnvelopeModel(ParticipantRuntimeBaseEnvelopeModel):
    """SEM-210 participant-visible observation record with explicit guarantees."""

    observation_ref: NonEmptyString
    phase_ref: NonEmptyString | None = None
    visibility_projection_ref: NonEmptyString
    information_guarantee: ParticipantRuntimeInformationGuarantee
    delivery_basis: ParticipantRuntimeDeliveryBasis
    delivery_point_ref: NonEmptyString | None = None
    delivered_at: Rfc3339DateTimeString | None = None
    action_observation_history_ref: NonEmptyString | None = None
    information_state_ref: NonEmptyString | None = None
    hidden_state_refs: list[NonEmptyString] = Field(default_factory=list)
    centralized_state_refs: list[NonEmptyString] = Field(default_factory=list)
    loss_descriptor: ParticipantObservationLossDescriptorModel | None = None
    stochastic_context: ParticipantObservationStochasticContextModel | None = None
    noise_model_ref: NonEmptyString | None = None
    reconstruction_algorithm_ref: NonEmptyString | None = None
    reconstruction_proof_ref: NonEmptyString | None = None
    belief_support_ref: NonEmptyString | None = None
    redacted_field_refs: list[NonEmptyString] = Field(default_factory=list)


class ParticipantSharedStateAccessModel(ContractModel):
    """RUN-307 read/write access record over one shared-state address."""

    state_address: NonEmptyString
    access_kind: Literal["read", "write", "read_write"]
    read_revision: NonEmptyString | None = None
    write_revision: NonEmptyString | None = None
    read_digest: PrefixedDigestString | None = None
    write_digest: PrefixedDigestString | None = None
    snapshot_ref: NonEmptyString | None = None
    access_purpose: NonEmptyString
    atomic_group_ref: NonEmptyString | None = None
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_revision_markers(self) -> ParticipantSharedStateAccessModel:
        if self.access_kind in {"read", "read_write"} and self.read_revision is None and self.read_digest is None:
            raise ValueError("shared state read access requires read_revision or read_digest")
        if self.access_kind in {"write", "read_write"} and self.write_revision is None and self.write_digest is None:
            raise ValueError("shared state write access requires write_revision or write_digest")
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
                        "properties": {"access_kind": {"enum": ["read", "read_write"]}},
                        "required": ["access_kind"],
                    },
                    "then": {
                        "anyOf": [
                            {"required": ["read_revision"], "properties": {"read_revision": {"type": "string"}}},
                            {"required": ["read_digest"], "properties": {"read_digest": {"type": "string"}}},
                        ]
                    },
                },
                {
                    "if": {
                        "properties": {"access_kind": {"enum": ["write", "read_write"]}},
                        "required": ["access_kind"],
                    },
                    "then": {
                        "anyOf": [
                            {"required": ["write_revision"], "properties": {"write_revision": {"type": "string"}}},
                            {"required": ["write_digest"], "properties": {"write_digest": {"type": "string"}}},
                        ]
                    },
                },
            ]
        )
        return json_schema


class ParticipantSharedStateRecordModel(ParticipantRuntimeBaseEnvelopeModel):
    """RUN-307 versioned shared operational state-change report."""

    state_address: NonEmptyString
    state_scope: NonEmptyString
    state_kind: NonEmptyString
    revision: NonEmptyString | None = None
    digest: PrefixedDigestString | None = None
    predecessor_revision_refs: list[NonEmptyString] = Field(default_factory=list)
    conflict_policy: ParticipantRuntimeConflictPolicy
    visibility_projection_basis: NonEmptyString | None = None
    provenance: NonEmptyString
    value_ref: NonEmptyString | None = None
    accesses: list[ParticipantSharedStateAccessModel] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_revision_marker(self) -> ParticipantSharedStateRecordModel:
        if self.revision is None and self.digest is None:
            raise ValueError("participant shared state record requires revision or digest")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.setdefault("anyOf", []).extend(
            [
                {"required": ["revision"], "properties": {"revision": {"type": "string"}}},
                {"required": ["digest"], "properties": {"digest": {"type": "string"}}},
            ]
        )
        return json_schema


class ParticipantJointActionAccessSetModel(ContractModel):
    """Read/write footprint for one member event in a joint action record."""

    member_event_ref: NonEmptyString
    shared_state_read_refs: list[NonEmptyString] = Field(default_factory=list)
    shared_state_write_refs: list[NonEmptyString] = Field(default_factory=list)
    exclusive_resource_refs: list[NonEmptyString] = Field(default_factory=list)
    visibility_effect_refs: list[NonEmptyString] = Field(default_factory=list)
    evidence_stream_refs: list[NonEmptyString] = Field(default_factory=list)


def _exact_string_permutation(values: list[str], expected: set[str]) -> bool:
    return len(values) == len(expected) and set(values) == expected


def _joint_action_actual_conflict(access_sets: list[ParticipantJointActionAccessSetModel]) -> str:
    read_write_conflict = False
    for left_index, left in enumerate(access_sets):
        left_reads = set(left.shared_state_read_refs)
        left_writes = set(left.shared_state_write_refs) | {f"resource:{ref}" for ref in left.exclusive_resource_refs}
        for right in access_sets[left_index + 1 :]:
            right_reads = set(right.shared_state_read_refs)
            right_writes = set(right.shared_state_write_refs) | {
                f"resource:{ref}" for ref in right.exclusive_resource_refs
            }
            if left_writes & right_writes:
                return "write_write"
            if (left_writes & right_reads) or (left_reads & right_writes):
                read_write_conflict = True
    return "read_write" if read_write_conflict else "none"


def _joint_action_member_ref_set(member_event_refs: list[str]) -> set[str]:
    member_refs = list(member_event_refs)
    member_ref_set = set(member_refs)
    if len(member_refs) != len(member_ref_set):
        raise ValueError("joint action member_event_refs must be unique")
    return member_ref_set


def _validate_joint_action_members(record: ParticipantJointActionRecordModel, member_ref_set: set[str]) -> None:
    access_event_refs = [access.member_event_ref for access in record.access_sets]
    if not _exact_string_permutation(access_event_refs, member_ref_set):
        raise ValueError("joint action access_sets must cover member_event_refs exactly once")
    if record.realized_order and not _exact_string_permutation(record.realized_order, member_ref_set):
        raise ValueError("joint action realized_order must be an exact permutation of member_event_refs")


def _validate_joint_action_disclosure(record: ParticipantJointActionRecordModel) -> None:
    if record.unsupported_disclosure and record.exact_concurrency_claim:
        raise ValueError("unsupported concurrency disclosure cannot carry an exact concurrency claim")
    if record.exact_concurrency_claim and record.time_management_context_ref is None:
        raise ValueError("exact concurrency claims require time_management_context_ref")


def _joint_action_unsupported_policy_applies(record: ParticipantJointActionRecordModel) -> bool:
    if record.conflict_policy != "unsupported":
        return False
    if not record.unsupported_disclosure or record.exact_concurrency_claim:
        raise ValueError("unsupported conflict_policy requires unsupported_disclosure and no exact claim")
    return True


def _validate_joint_action_conflict(record: ParticipantJointActionRecordModel, actual_conflict: str) -> None:
    if not record.unsupported_disclosure and record.conflict_class != actual_conflict:
        raise ValueError("joint action conflict_class must match declared access-set conflicts")
    if record.conflict_class == "none" and actual_conflict != "none":
        raise ValueError("joint action conflict_class cannot be none when access sets conflict")
    _validate_joint_action_conflict_policy(record, actual_conflict)
    _validate_joint_action_atomicity(record, actual_conflict)


def _validate_joint_action_conflict_policy(record: ParticipantJointActionRecordModel, actual_conflict: str) -> None:
    if record.isolation_guarantee == "serializable" and not record.realized_order:
        raise ValueError("serializable joint action isolation requires realized_order")
    if record.conflict_policy == "serialize" and not record.realized_order:
        raise ValueError("serialize conflict_policy requires realized_order")
    if record.conflict_policy == "retry" and (record.retry_limit is None or not record.rollback_event_refs):
        raise ValueError("retry conflict_policy requires retry_limit and rollback_event_refs")
    if record.conflict_policy == "none" and actual_conflict != "none":
        raise ValueError("none conflict_policy is only valid when access sets do not conflict")


def _validate_joint_action_atomicity(record: ParticipantJointActionRecordModel, actual_conflict: str) -> None:
    has_recovery_evidence = bool(record.realized_order or record.rollback_event_refs)
    if record.atomicity_scope == "multi_object" and actual_conflict != "none" and not has_recovery_evidence:
        raise ValueError("multi_object conflicting joint actions require realized_order or rollback_event_refs")


class ParticipantJointActionRecordModel(ParticipantRuntimeBaseEnvelopeModel):
    """RUN-308 joint action / concurrency record over behavior events."""

    joint_action_set_id: NonEmptyString
    member_event_refs: list[NonEmptyString] = Field(min_length=1)
    access_sets: list[ParticipantJointActionAccessSetModel] = Field(min_length=1)
    conflict_class: ParticipantRuntimeConflictClass
    conflict_policy: ParticipantRuntimeJointActionConflictPolicy
    isolation_guarantee: ParticipantRuntimeIsolationGuarantee
    atomicity_scope: ParticipantRuntimeAtomicityScope
    realized_order: list[NonEmptyString] = Field(default_factory=list)
    simultaneity_group_ref: NonEmptyString | None = None
    time_management_context_ref: NonEmptyString | None = None
    participant_observation_refs: list[NonEmptyString] = Field(default_factory=list)
    rollback_event_refs: list[NonEmptyString] = Field(default_factory=list)
    retry_limit: NonNegativeInteger | None = None
    timeout_policy_ref: NonEmptyString | None = None
    fairness_policy_ref: NonEmptyString | None = None
    unsupported_disclosure: bool = False
    exact_concurrency_claim: bool = False

    @model_validator(mode="after")
    def _validate_joint_action_record(self) -> ParticipantJointActionRecordModel:
        member_ref_set = _joint_action_member_ref_set(self.member_event_refs)
        _validate_joint_action_members(self, member_ref_set)
        _validate_joint_action_disclosure(self)
        if _joint_action_unsupported_policy_applies(self):
            return self

        actual_conflict = _joint_action_actual_conflict(self.access_sets)
        _validate_joint_action_conflict(self, actual_conflict)
        return self


def _validate_time_management_claim(context: ParticipantTimeManagementContextModel) -> None:
    if context.unsupported_disclosure and context.claim_strength == "exact":
        raise ValueError("unsupported time-management disclosure cannot carry an exact claim")
    if context.basis == "wall_clock_only" and context.claim_strength != "display":
        raise ValueError("wall_clock_only time basis supports display claims only")
    if context.claim_strength in {"bounded", "exact"} and context.clock_ref is None:
        raise ValueError("bounded or exact time-management claims require clock_ref")


def _validate_time_management_mode(context: ParticipantTimeManagementContextModel) -> None:
    if context.mode == "backend_serialized":
        _validate_backend_serialized_time_management(context)
    elif context.mode in {"devs", "fmi"}:
        if context.clock_ref is None or context.basis == "wall_clock_only":
            raise ValueError("devs and fmi modes require a non-wall-clock basis and clock_ref")
    else:
        _validate_simple_time_management_mode(context)


def _validate_simple_time_management_mode(context: ParticipantTimeManagementContextModel) -> None:
    if context.mode == "lookahead" and context.lookahead is None:
        raise ValueError("lookahead mode requires lookahead")
    if context.mode == "pacing" and context.advance_by is None:
        raise ValueError("pacing mode requires advance_by")
    if context.mode == "rollback" and not context.rollback_event_refs:
        raise ValueError("rollback mode requires rollback_event_refs")
    if context.mode == "unsupported" and not context.unsupported_disclosure:
        raise ValueError("unsupported time-management mode requires unsupported_disclosure")


def _validate_backend_serialized_time_management(context: ParticipantTimeManagementContextModel) -> None:
    if not context.backend_serialized or context.basis != "serialized_backend_order" or context.clock_ref is None:
        raise ValueError("backend_serialized mode requires serialized_backend_order basis and clock_ref")


class ParticipantTimeManagementContextModel(ParticipantRuntimeBaseEnvelopeModel):
    """RUN-308 time-management basis for concurrent or distributed runtime claims."""

    context_id: NonEmptyString
    mode: ParticipantRuntimeTimeManagementMode
    claim_strength: ParticipantRuntimeTimeClaimStrength
    basis: ParticipantRuntimeOrderingBasis
    clock_ref: NonEmptyString | None = None
    lookahead: NonNegativeInteger | None = None
    advance_by: PositiveInteger | None = None
    rollback_event_refs: list[NonEmptyString] = Field(default_factory=list)
    unsupported_disclosure: bool = False
    backend_serialized: bool = False

    @model_validator(mode="after")
    def _validate_time_management_context(self) -> ParticipantTimeManagementContextModel:
        _validate_time_management_claim(self)
        _validate_time_management_mode(self)
        return self
