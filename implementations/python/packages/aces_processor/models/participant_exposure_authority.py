"""Trusted authority records and resolvers for SEM-226 exposure."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from aces_contracts.contracts import ParticipantImplementationSelectionModel


@dataclass(frozen=True)
class ParticipantExposurePolicyRevision:
    """One authoritative projection-policy revision and effective order."""

    policy_ref: str
    revision: str
    effective_order: int


@dataclass(frozen=True)
class ParticipantExposureAuthorizationRecord:
    """Governed authorization resolved independently of a projection request."""

    authorization_record_ref: str
    item_ref: str
    source_ref: str
    source_layer_ref: str
    participant_address: str
    episode_id: str
    audience_scope_ref: str
    effective_from_order: int
    effective_through_order: int | None
    implementation_selection_ref: str
    projection_policy_ref: str
    projection_policy_revision: str
    exposure_policy_ref: str
    exposure_policy_version: str
    exposure_policy_digest: str
    visibility_basis_ref: str
    operation: str
    operation_basis_ref: str
    actor_ref: str
    controller_ref: str
    authority_basis_ref: str
    backend_support_ref: str
    source_marking_definition_refs: tuple[str, ...]
    result_marking_definition_refs: tuple[str, ...]
    source_provenance_refs: tuple[str, ...]
    result_provenance_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    loss_and_limitations: tuple[str, ...]
    declassification_basis_ref: str | None = None
    redaction_policy_ref: str | None = None
    transformation_rule_ref: str | None = None


@dataclass(frozen=True)
class ParticipantExposureOccurrenceRecord:
    """Authoritative delivery occurrence resolved from runtime evidence."""

    occurrence_ref: str
    item_ref: str
    authorization_record_ref: str
    participant_address: str
    episode_id: str
    delivery_basis_ref: str
    delivery_order: int
    observation_ref: str
    action_instance_id: str
    observation_boundary_address: str
    evidence_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class ParticipantExposureRealizationAssessment:
    """A request to bind one exposure to an authoritative occurrence."""

    occurrence_ref: str


@dataclass(frozen=True)
class ParticipantExposureAssessment:
    """Stable refs used to resolve one governed exposure decision."""

    item_ref: str
    authorization_record_ref: str
    realization: ParticipantExposureRealizationAssessment | None = None


class ParticipantExposureApparatusResolver(Protocol):
    """Resolve a run's selected participant implementation and exposure policy."""

    def __call__(
        self,
        *,
        implementation_selection_ref: str,
        exposure_policy_ref: str,
        observation_order: int,
    ) -> ParticipantImplementationSelectionModel | None: ...


class ParticipantExposureProjectionPolicyResolver(Protocol):
    """Resolve authoritative revisions for a participant/audience policy."""

    def __call__(
        self,
        *,
        projection_policy_ref: str,
        participant_address: str,
        audience_scope_ref: str,
    ) -> Sequence[ParticipantExposurePolicyRevision]: ...


class ParticipantExposureAuthorizationResolver(Protocol):
    """Resolve a governed item authorization by its stable record ref."""

    def __call__(
        self,
        *,
        authorization_record_ref: str,
        item_ref: str,
    ) -> ParticipantExposureAuthorizationRecord | None: ...


class ParticipantExposureOccurrenceResolver(Protocol):
    """Resolve a realized delivery by its stable occurrence ref."""

    def __call__(self, *, occurrence_ref: str) -> ParticipantExposureOccurrenceRecord | None: ...


@dataclass(frozen=True)
class ParticipantExposureResolvers:
    """Trusted dependencies for policy, authorization, and occurrence resolution."""

    apparatus: ParticipantExposureApparatusResolver
    projection_policy: ParticipantExposureProjectionPolicyResolver
    authorization: ParticipantExposureAuthorizationResolver
    occurrence: ParticipantExposureOccurrenceResolver


class ParticipantExposureProjection(Protocol):
    """Projection coordinates consumed by the reusable exposure selector."""

    participant_address: str
    episode_id: str
    observation_order: int
    observation_point: str
    implementation_selection_ref: str
    decision_control_mode: str
    audience_scope_ref: str
    projection_policy_ref: str
    projection_policy_revision: str
    exposure_policy_ref: str
    visible_context_refs: tuple[str, ...]
    exposure_assessments: Mapping[str, ParticipantExposureAssessment]
    evidence_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    marking_definition_refs: tuple[str, ...]
    redaction_policy_ref: str | None
