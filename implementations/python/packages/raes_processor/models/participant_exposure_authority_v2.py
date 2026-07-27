"""Exact-state-cut authority records and resolvers for SEM-226 v2 exposure."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from raes_contracts.contracts import ParticipantImplementationSelectionModel

from .participant_exposure_authority import ParticipantExposureAssessment


@dataclass(frozen=True)
class ParticipantExposurePolicyDecisionV2:
    """The projection-policy decision effective at one exact state cut."""

    policy_ref: str
    revision: str
    decision_ref: str
    decision_cut_ref: str
    evidence_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class ParticipantExposureAuthorizationRecordV2:
    """An item authorization evaluated at one exact state cut."""

    authorization_record_ref: str
    item_ref: str
    source_ref: str
    source_layer_ref: str
    participant_address: str
    episode_id: str
    audience_scope_ref: str
    decision_epoch: int
    decision_cut_ref: str
    implementation_selection_ref: str
    projection_policy_ref: str
    projection_policy_revision: str
    projection_policy_decision_ref: str
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


class ParticipantExposureApparatusResolverV2(Protocol):
    """Resolve the selected apparatus at an exact state cut."""

    def __call__(
        self,
        *,
        implementation_selection_ref: str,
        exposure_policy_ref: str,
        decision_cut_ref: str,
    ) -> ParticipantImplementationSelectionModel | None: ...


class ParticipantExposureProjectionPolicyResolverV2(Protocol):
    """Resolve the projection-policy decision at an exact state cut."""

    def __call__(
        self,
        *,
        projection_policy_ref: str,
        participant_address: str,
        audience_scope_ref: str,
        decision_cut_ref: str,
    ) -> ParticipantExposurePolicyDecisionV2 | None: ...


class ParticipantExposureAuthorizationResolverV2(Protocol):
    """Resolve an exact-cut item authorization by stable record reference."""

    def __call__(
        self,
        *,
        authorization_record_ref: str,
        item_ref: str,
        decision_cut_ref: str,
    ) -> ParticipantExposureAuthorizationRecordV2 | None: ...


@dataclass(frozen=True)
class ParticipantExposureResolversV2:
    apparatus: ParticipantExposureApparatusResolverV2
    projection_policy: ParticipantExposureProjectionPolicyResolverV2
    authorization: ParticipantExposureAuthorizationResolverV2


class ParticipantExposureProjectionV2(Protocol):
    """Exact-cut coordinates consumed by the v2 exposure selector."""

    participant_address: str
    episode_id: str
    decision_epoch: int
    decision_cut_ref: str
    implementation_selection_ref: str
    decision_control_mode: str
    audience_scope_ref: str
    projection_policy_ref: str
    projection_policy_revision: str
    projection_policy_decision_ref: str
    exposure_policy_ref: str
    visible_context_refs: tuple[str, ...]
    exposure_assessments: Mapping[str, ParticipantExposureAssessment]
    evidence_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    marking_definition_refs: tuple[str, ...]
    redaction_policy_ref: str | None
