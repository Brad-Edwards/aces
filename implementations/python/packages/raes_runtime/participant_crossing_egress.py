"""Atomic RUN-319 mediation for participant retrieval serialization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import TypeVar

from raes_contracts.contracts.base import ContractModel
from raes_contracts.contracts.participant_crossing import (
    ParticipantCrossingDirection,
    ParticipantCrossingInteractionKind,
    ParticipantCrossingOperation,
    ParticipantCrossingSubjectKind,
    ParticipantCrossingSubjectReferenceModel,
)

from .participant_crossing_mediation import (
    ParticipantCrossingEvidence,
    ParticipantCrossingIntent,
    commit_prepared_crossing,
    prepare_participant_crossing,
)

_ViewT = TypeVar("_ViewT", bound=ContractModel)


def serialize_participant_view(
    control_plane: object,
    view: _ViewT,
    *,
    participant_address: str,
    episode_id: str,
    subject_kind: ParticipantCrossingSubjectKind,
    interaction_kind: ParticipantCrossingInteractionKind,
    projection_ref: str,
    identity: object,
    crossing_evidence: ParticipantCrossingEvidence | None,
    idempotency_key: str,
) -> _ViewT:
    """Return a view only after its exact governed projection is committed."""

    if crossing_evidence is None:
        raise ValueError("configured participant egress requires crossing evidence")
    with control_plane._participant_control_lock:
        subject = _view_subject(
            view,
            participant_address=participant_address,
            episode_id=episode_id,
            subject_kind=subject_kind,
        )
        canonical = ParticipantCrossingIntent.model_validate(
            {
                **crossing_evidence.model_dump(mode="json"),
                "participant_address": participant_address,
                "episode_id": episode_id,
                "direction": ParticipantCrossingDirection.EGRESS,
                "interaction_kind": interaction_kind,
                "subject": subject,
                "controller_ref": "runtime.control-plane.participant-retrieval",
                "authority_basis_refs": ["runtime.authority:participant-projection"],
                "requested_operation": ParticipantCrossingOperation.PROJECTION,
                "action_or_projection_ref": projection_ref,
                "effective_order": _next_effective_order(control_plane, participant_address),
                "order_model": "logical_clock",
            },
        )
        prepared = prepare_participant_crossing(
            control_plane,
            canonical,
            identity=identity,
            idempotency_key=idempotency_key,
            incumbent_carrier=view,
        )
        if prepared.existing_receipt is not None:
            if not prepared.existing_receipt.accepted:
                raise PermissionError("participant projection was not permitted")
            if prepared.record.result_payload is None:
                raise ValueError("idempotent participant projection is missing its governed result")
            return type(view).model_validate(prepared.record.result_payload)
        if not prepared.record.receipt.accepted:
            commit_prepared_crossing(control_plane, prepared)
            raise PermissionError("participant projection was not permitted")

        governed = view
        if prepared.governed_subject != subject:
            transformer = getattr(control_plane._crossing_policy_resolver, "transform_egress", None)
            if not callable(transformer):
                raise ValueError("transformed participant egress requires a trusted view transformer")
            candidate = transformer(prepared.intent, prepared.governed_subject, view)
            if not isinstance(candidate, type(view)):
                raise ValueError("participant egress transformation returned an invalid governed view")
            governed = candidate
            actual = _view_subject(
                governed,
                participant_address=participant_address,
                episode_id=episode_id,
                subject_kind=prepared.governed_subject.subject_kind,
            )
            if actual != prepared.governed_subject:
                raise ValueError("trusted egress transformation does not match its governed identity")
        prepared = replace(
            prepared,
            record=replace(
                prepared.record,
                result_payload=governed.model_dump(mode="json"),
            ),
        )
        commit_prepared_crossing(control_plane, prepared)
        return governed


def _view_subject(
    view: ContractModel,
    *,
    participant_address: str,
    episode_id: str,
    subject_kind: ParticipantCrossingSubjectKind,
) -> ParticipantCrossingSubjectReferenceModel:
    payload = view.model_dump(mode="json")
    payload.pop("generated_at", None)
    view_ref = payload.get("view_id")
    if not isinstance(view_ref, str) or not view_ref:
        raise ValueError("participant projection requires an exact view identity")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return ParticipantCrossingSubjectReferenceModel(
        subject_kind=subject_kind,
        contract_id=f"{subject_kind.value}-v1",
        subject_ref=view_ref,
        subject_digest=f"sha256:{hashlib.sha256(encoded).hexdigest()}",
        participant_address=participant_address,
        episode_id=episode_id,
    )


def _next_effective_order(control_plane: object, participant_address: str) -> int:
    histories = (
        control_plane._snapshot.participant_behavior_history,
        control_plane._snapshot.participant_control_history,
        control_plane._snapshot.participant_crossing_history,
    )
    return sum(len(history.get(participant_address, ())) for history in histories) + 1


__all__ = ("serialize_participant_view",)
