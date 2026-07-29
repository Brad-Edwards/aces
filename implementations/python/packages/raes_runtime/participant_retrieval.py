"""Participant retrieval projections for the runtime control plane."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from raes_contracts.contracts import (
    ParticipantContextViewModel,
    ParticipantHistoryViewModel,
    ParticipantStatusViewModel,
)
from raes_contracts.contracts.participant_crossing import (
    ParticipantCrossingInteractionKind,
    ParticipantCrossingSubjectKind,
)
from raes_contracts.planning import RuntimeDomain
from raes_contracts.runtime_state import OperationState, RuntimeSnapshot

from .control_plane_security import ControlPlaneIdentity, ParticipantAudienceSubjectBinding
from .control_plane_store import ControlPlaneOperationRecord
from .participant_crossing_egress import ParticipantViewSerialization, serialize_participant_view
from .participant_crossing_mediation import ParticipantCrossingEvidence

_CURRENT_SNAPSHOT_REF = "runtime.snapshot.current"
_CROSSING_RESOLVER_REQUIRED = "participant crossing policy resolver is required"


@dataclass(frozen=True)
class _ContextViewOptions:
    episode_id: str | None = None
    derivation_basis_ref: str | None = None
    payload_ref: str | None = None
    derived_from_refs: tuple[str, ...] = ()
    identity: object | None = None
    audience_binding: ParticipantAudienceSubjectBinding | None = None
    crossing_evidence: ParticipantCrossingEvidence | None = None
    idempotency_key: str = ""

    @classmethod
    def from_fields(cls, fields: dict[str, object]) -> _ContextViewOptions:
        unknown = set(fields) - {
            "episode_id",
            "derivation_basis_ref",
            "payload_ref",
            "derived_from_refs",
            "identity",
            "audience_binding",
            "crossing_evidence",
            "idempotency_key",
        }
        if unknown:
            names = ", ".join(sorted(unknown))
            raise TypeError(f"unexpected participant context options: {names}")
        episode_id = _optional_string(fields.get("episode_id"), "episode_id")
        derivation_basis_ref = _optional_string(fields.get("derivation_basis_ref"), "derivation_basis_ref")
        payload_ref = _optional_string(fields.get("payload_ref"), "payload_ref")
        derived_from_refs = fields.get("derived_from_refs", ())
        idempotency_key = fields.get("idempotency_key", "")
        crossing_evidence = fields.get("crossing_evidence")
        audience_binding = fields.get("audience_binding")
        if not isinstance(derived_from_refs, tuple) or not all(isinstance(item, str) for item in derived_from_refs):
            raise TypeError("derived_from_refs must be a tuple of strings")
        if not isinstance(idempotency_key, str):
            raise TypeError("idempotency_key must be a string")
        if crossing_evidence is not None and not isinstance(crossing_evidence, ParticipantCrossingEvidence):
            raise TypeError("crossing_evidence must be ParticipantCrossingEvidence")
        if audience_binding is not None and not isinstance(audience_binding, ParticipantAudienceSubjectBinding):
            raise TypeError("audience_binding must be ParticipantAudienceSubjectBinding")
        return cls(
            episode_id=episode_id,
            derivation_basis_ref=derivation_basis_ref,
            payload_ref=payload_ref,
            derived_from_refs=derived_from_refs,
            identity=fields.get("identity"),
            audience_binding=audience_binding,
            crossing_evidence=crossing_evidence,
            idempotency_key=idempotency_key,
        )


class ParticipantRetrievalMixin:
    """API-408 participant retrieval projections over recorded runtime state."""

    _snapshot: RuntimeSnapshot
    _operations: dict[str, ControlPlaneOperationRecord]

    def deliver_participant_directed_view(
        self,
        participant_address: str,
        view: ParticipantStatusViewModel,
        *,
        identity: object | None = None,
        crossing_evidence: ParticipantCrossingEvidence | None = None,
        idempotency_key: str = "",
    ) -> ParticipantStatusViewModel:
        """Deliver an already-projected carrier as a participant-directed crossing.

        ADR-085 governs a participant-directed inject as disclosure/observation
        *at delivery*, and RUN-319's capability mapping already requires
        ``participant_directed_inject_delivery`` for that interaction kind — but
        there was no public way to perform one, so callers had to reach into the
        egress module directly. Disclosure and delivery stay separate governed
        transition facts: this records the delivery crossing for a carrier whose
        projection was already decided, and it proves neither consumption nor
        participant observation.
        """

        if getattr(self, "_crossing_policy_resolver", None) is None:
            raise ValueError(_CROSSING_RESOLVER_REQUIRED)
        episode_state = self._snapshot.participant_episode_results.get(participant_address)
        episode_id = _string_value(episode_state, "episode_id") if episode_state is not None else None
        return serialize_participant_view(
            self,
            view,
            ParticipantViewSerialization(
                participant_address=participant_address,
                episode_id=_required_episode_id(episode_id),
                subject_kind=ParticipantCrossingSubjectKind.PARTICIPANT_STATUS_VIEW,
                interaction_kind=ParticipantCrossingInteractionKind.PARTICIPANT_INJECT_DELIVERY,
                projection_ref=view.visibility_projection_ref,
                identity=identity,
                crossing_evidence=crossing_evidence,
                idempotency_key=idempotency_key,
            ),
        )

    def get_participant_status_view(
        self,
        participant_address: str,
        *,
        identity: object | None = None,
        audience_binding: ParticipantAudienceSubjectBinding | None = None,
        crossing_evidence: ParticipantCrossingEvidence | None = None,
        idempotency_key: str = "",
    ) -> ParticipantStatusViewModel | None:
        if not _participant_exists(self._snapshot, participant_address):
            return None
        episode_state = self._snapshot.participant_episode_results.get(participant_address)
        episode_id = _string_value(episode_state, "episode_id") if episode_state is not None else None
        view = ParticipantStatusViewModel.model_validate(
            {
                "view_id": _view_id("status", participant_address, episode_id),
                "participant_address": participant_address,
                "episode_id": episode_id,
                "generated_at": _utc_now(),
                "source_snapshot_ref": _CURRENT_SNAPSHOT_REF,
                "episode_state": _project_scope(episode_state) if episode_state is not None else None,
                "open_operation_refs": _open_participant_operation_refs(self._operations, participant_address),
                "visibility_projection_ref": _visibility_projection_ref(participant_address, "status"),
                "marking_definition_refs": [],
                "redaction_policy_ref": None,
            }
        )
        if getattr(self, "_crossing_policy_resolver", None) is None:
            if crossing_evidence is not None:
                raise ValueError(_CROSSING_RESOLVER_REQUIRED)
            return view
        crossing_evidence = _resolve_trusted_view_evidence(
            self,
            participant_address=participant_address,
            episode_id=_required_episode_id(episode_id),
            interaction_kind=ParticipantCrossingInteractionKind.STATUS_PROJECTION,
            projection_ref=view.visibility_projection_ref,
            identity=identity,
            audience_binding=audience_binding,
            supplied=crossing_evidence,
        )
        return serialize_participant_view(
            self,
            view,
            ParticipantViewSerialization(
                participant_address=participant_address,
                episode_id=_required_episode_id(episode_id),
                subject_kind=ParticipantCrossingSubjectKind.PARTICIPANT_STATUS_VIEW,
                interaction_kind=ParticipantCrossingInteractionKind.STATUS_PROJECTION,
                projection_ref=view.visibility_projection_ref,
                identity=identity,
                crossing_evidence=crossing_evidence,
                idempotency_key=idempotency_key,
            ),
        )

    def get_participant_history_view(
        self,
        participant_address: str,
        episode_id: str,
        *,
        identity: object | None = None,
        audience_binding: ParticipantAudienceSubjectBinding | None = None,
        crossing_evidence: ParticipantCrossingEvidence | None = None,
        idempotency_key: str = "",
    ) -> ParticipantHistoryViewModel | None:
        if not _participant_episode_exists(self._snapshot, participant_address, episode_id):
            return None
        episode_history = [
            _project_scope(event)
            for event in self._snapshot.participant_episode_history.get(participant_address, [])
            if event.get("episode_id") == episode_id
        ]
        behavior_history = [
            _project_scope(event)
            for event in self._snapshot.participant_behavior_history.get(participant_address, [])
            if event.get("episode_id") == episode_id
        ]
        view = ParticipantHistoryViewModel.model_validate(
            {
                "view_id": _view_id("history", participant_address, episode_id),
                "participant_address": participant_address,
                "episode_id": episode_id,
                "generated_at": _utc_now(),
                "source_snapshot_ref": _CURRENT_SNAPSHOT_REF,
                "episode_history": episode_history,
                "behavior_history": behavior_history,
                "visibility_projection_ref": _visibility_projection_ref(participant_address, "history"),
                "redaction_policy_ref": None,
                "completeness": "complete",
                "completeness_basis": None,
                "marking_definition_refs": [],
            }
        )
        if getattr(self, "_crossing_policy_resolver", None) is None:
            if crossing_evidence is not None:
                raise ValueError(_CROSSING_RESOLVER_REQUIRED)
            return view
        crossing_evidence = _resolve_trusted_view_evidence(
            self,
            participant_address=participant_address,
            episode_id=episode_id,
            interaction_kind=ParticipantCrossingInteractionKind.HISTORY_PROJECTION,
            projection_ref=view.visibility_projection_ref,
            identity=identity,
            audience_binding=audience_binding,
            supplied=crossing_evidence,
        )
        return serialize_participant_view(
            self,
            view,
            ParticipantViewSerialization(
                participant_address=participant_address,
                episode_id=episode_id,
                subject_kind=ParticipantCrossingSubjectKind.PARTICIPANT_HISTORY_VIEW,
                interaction_kind=ParticipantCrossingInteractionKind.HISTORY_PROJECTION,
                projection_ref=view.visibility_projection_ref,
                identity=identity,
                crossing_evidence=crossing_evidence,
                idempotency_key=idempotency_key,
            ),
        )

    def get_participant_context_view(
        self,
        participant_address: str,
        *,
        view_ref: str,
        **context_fields: object,
    ) -> ParticipantContextViewModel | None:
        options = _ContextViewOptions.from_fields(context_fields)
        if not _context_participant_exists(self._snapshot, participant_address, options.episode_id):
            return None
        source_refs = tuple(options.derived_from_refs or (_CURRENT_SNAPSHOT_REF,))
        source_ref = source_refs[0]
        source_id = "source-snapshot"
        resolved_observation_point = options.episode_id or _CURRENT_SNAPSHOT_REF
        resolved_derivation_basis_ref = options.derivation_basis_ref or view_ref
        view = ParticipantContextViewModel.model_validate(
            {
                "view_id": _view_id("context", participant_address, options.episode_id or view_ref),
                "participant_address": participant_address,
                "episode_id": options.episode_id,
                "generated_at": _utc_now(),
                "source_snapshot_ref": _CURRENT_SNAPSHOT_REF,
                "view_ref": view_ref,
                "meaning_ref": view_ref,
                "participant_scope": "participant_local",
                "audience_scope": "participant_visible",
                "observation_point": resolved_observation_point,
                "derived_from_refs": list(source_refs),
                "source_layers": [
                    {
                        "source_id": source_id,
                        "source_layer": "source_snapshot",
                        "ref": source_ref,
                        "temporal_relation": "same_observation_point",
                        "observation_point": resolved_observation_point,
                        "evidence_refs": list(source_refs),
                        "provenance_refs": list(source_refs),
                    }
                ],
                "transformation": {
                    "transformation_rule_ref": resolved_derivation_basis_ref,
                    "description": "API-408 derived context view relation declared by the governed view reference",
                    "input_source_ids": [source_id],
                    "output_semantics_ref": view_ref,
                },
                "comparability": {
                    "comparability_class": "portable_equivalent",
                    "comparison_basis_ref": f"comparability.{view_ref}",
                    "backend_disclosure_refs": [],
                    "limitations": [
                        "Comparable only under the declared view, transformation, visibility, and evidence basis"
                    ],
                },
                "evidence_refs": list(source_refs),
                "provenance_refs": list(source_refs),
                "semantic_limitations": [
                    "Context-view payload remains a referenced derived view, not backend-private state"
                ],
                "derivation_basis_ref": options.derivation_basis_ref,
                "payload_ref": options.payload_ref,
                "visibility_projection_ref": _visibility_projection_ref(participant_address, "context"),
                "marking_definition_refs": [],
                "redaction_policy_ref": None,
            }
        )
        if getattr(self, "_crossing_policy_resolver", None) is None:
            if options.crossing_evidence is not None:
                raise ValueError(_CROSSING_RESOLVER_REQUIRED)
            result = view
        else:
            resolved_episode_id = options.episode_id or _string_value(
                self._snapshot.participant_episode_results.get(participant_address),
                "episode_id",
            )
            crossing_evidence = _resolve_trusted_view_evidence(
                self,
                participant_address=participant_address,
                episode_id=_required_episode_id(resolved_episode_id),
                interaction_kind=ParticipantCrossingInteractionKind.DECISION_SURFACE_PROJECTION,
                projection_ref=view.visibility_projection_ref,
                identity=options.identity,
                audience_binding=options.audience_binding,
                supplied=options.crossing_evidence,
            )
            result = serialize_participant_view(
                self,
                view,
                ParticipantViewSerialization(
                    participant_address=participant_address,
                    episode_id=_required_episode_id(resolved_episode_id),
                    subject_kind=ParticipantCrossingSubjectKind.PARTICIPANT_CONTEXT_VIEW,
                    interaction_kind=ParticipantCrossingInteractionKind.DECISION_SURFACE_PROJECTION,
                    projection_ref=view.visibility_projection_ref,
                    identity=options.identity,
                    crossing_evidence=crossing_evidence,
                    idempotency_key=options.idempotency_key,
                ),
            )
        return result


def _resolve_trusted_view_evidence(
    control_plane: object,
    *,
    participant_address: str,
    episode_id: str,
    interaction_kind: ParticipantCrossingInteractionKind,
    projection_ref: str,
    identity: object | None,
    audience_binding: ParticipantAudienceSubjectBinding | None,
    supplied: ParticipantCrossingEvidence | None,
) -> ParticipantCrossingEvidence:
    if supplied is not None:
        return supplied
    resolver = getattr(control_plane, "_crossing_policy_resolver", None)
    provider = getattr(resolver, "resolve_participant_view_evidence", None)
    if not callable(provider):
        raise ValueError("participant view crossing evidence is unavailable")
    binding = _trusted_audience_binding(
        identity,
        participant_address=participant_address,
        supplied=audience_binding,
    )
    resolved = provider(
        snapshot=control_plane._snapshot,
        participant_address=participant_address,
        episode_id=episode_id,
        interaction_kind=interaction_kind,
        projection_ref=projection_ref,
        audience_binding=binding,
    )
    if not isinstance(resolved, ParticipantCrossingEvidence):
        raise ValueError("participant view crossing evidence is unavailable")
    return resolved


def _trusted_audience_binding(
    identity: object | None,
    *,
    participant_address: str,
    supplied: ParticipantAudienceSubjectBinding | None,
) -> ParticipantAudienceSubjectBinding:
    if not isinstance(identity, ControlPlaneIdentity):
        raise ValueError("participant view audience binding is unavailable")
    matches = tuple(
        binding
        for binding in identity.participant_audience_subjects
        if binding.participant_address == participant_address
    )
    if supplied is not None:
        if supplied not in matches:
            raise ValueError("participant view audience binding is unavailable")
        return supplied
    if len(matches) != 1:
        raise ValueError("participant view audience binding is unavailable")
    return matches[0]


def _string_value(payload: dict[str, object] | None, key: str) -> str | None:
    if payload is None:
        return None
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def _optional_string(value: object, name: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{name} must be a string or None")
    return value


def _context_participant_exists(
    snapshot: RuntimeSnapshot,
    participant_address: str,
    episode_id: str | None,
) -> bool:
    if episode_id is not None:
        return _participant_episode_exists(snapshot, participant_address, episode_id)
    return _participant_exists(snapshot, participant_address)


def _required_episode_id(value: str | None) -> str:
    if value is None:
        raise ValueError("participant projection requires an exact episode identity")
    return value


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _participant_exists(snapshot: RuntimeSnapshot, participant_address: str) -> bool:
    return (
        participant_address in snapshot.participant_episode_results
        or participant_address in snapshot.participant_episode_history
        or participant_address in snapshot.participant_behavior_history
    )


def _participant_episode_exists(snapshot: RuntimeSnapshot, participant_address: str, episode_id: str) -> bool:
    episode_state = snapshot.participant_episode_results.get(participant_address)
    if _string_value(episode_state, "episode_id") == episode_id:
        return True
    histories = (
        snapshot.participant_episode_history.get(participant_address, []),
        snapshot.participant_behavior_history.get(participant_address, []),
    )
    return any(event.get("episode_id") == episode_id for history in histories for event in history)


def _project_scope(payload: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if key not in {"participant_address", "episode_id"}}


def _open_participant_operation_refs(
    operations: Mapping[str, ControlPlaneOperationRecord],
    participant_address: str,
) -> list[str]:
    return [
        operation_id
        for operation_id, record in sorted(operations.items())
        if record.status.domain == RuntimeDomain.PARTICIPANT
        and record.status.state in {OperationState.ACCEPTED, OperationState.RUNNING}
        and participant_address in record.status.changed_addresses
    ]


def _view_id(kind: str, participant_address: str, suffix: str | None) -> str:
    return f"runtime.participant-view.{kind}.{participant_address}.{suffix or 'current'}"


def _visibility_projection_ref(participant_address: str, kind: str) -> str:
    return f"runtime.visibility-projection.{kind}.{participant_address}.v1"
