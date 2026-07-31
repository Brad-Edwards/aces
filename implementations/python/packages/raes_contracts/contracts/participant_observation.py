"""Participant-visible observation contracts."""

from __future__ import annotations

from pydantic import Field, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from .base import ContractModel, NonEmptyString, Rfc3339DateTimeString
from .participant_envelopes import ParticipantRuntimeBaseEnvelopeModel
from .participant_runtime import (
    ParticipantRuntimeDeliveryBasis,
    ParticipantRuntimeInformationGuarantee,
)


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

    @model_validator(mode="after")
    def _validate_information_guarantee(self) -> ParticipantObservationEnvelopeModel:
        if self.information_guarantee in {"history_consistent", "perfect_recall"}:
            required_refs = {
                "action_observation_history_ref": self.action_observation_history_ref,
                "information_state_ref": self.information_state_ref,
                "reconstruction_algorithm_ref": self.reconstruction_algorithm_ref,
                "reconstruction_proof_ref": self.reconstruction_proof_ref,
            }
            missing = sorted(name for name, value in required_refs.items() if value is None)
            if missing:
                raise ValueError("strong information guarantee requires: " + ", ".join(missing))
        if self.information_guarantee == "lossy_projection" and self.loss_descriptor is None:
            raise ValueError("lossy_projection requires loss_descriptor")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        json_schema = handler.resolve_ref_schema(handler(core_schema))
        json_schema.setdefault("allOf", []).extend(
            [
                {
                    "if": {
                        "properties": {"information_guarantee": {"enum": ["history_consistent", "perfect_recall"]}},
                        "required": ["information_guarantee"],
                    },
                    "then": {
                        "required": [
                            "action_observation_history_ref",
                            "information_state_ref",
                            "reconstruction_algorithm_ref",
                            "reconstruction_proof_ref",
                        ],
                        "properties": {
                            field_name: {"type": "string", "minLength": 1}
                            for field_name in (
                                "action_observation_history_ref",
                                "information_state_ref",
                                "reconstruction_algorithm_ref",
                                "reconstruction_proof_ref",
                            )
                        },
                    },
                },
                {
                    "if": {
                        "properties": {"information_guarantee": {"const": "lossy_projection"}},
                        "required": ["information_guarantee"],
                    },
                    "then": {
                        "required": ["loss_descriptor"],
                        "properties": {"loss_descriptor": {"type": "object"}},
                    },
                },
            ]
        )
        return json_schema
