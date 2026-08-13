"""Runtime observation restoration for control-plane persistence."""

from typing import Any

from raes_contracts.contracts import RealizationObservationDisclosureModel
from raes_contracts.realization_observation import ObservedOperatingSystemIdentity
from raes_contracts.runtime_state import RealizationObservationDisclosure
from raes_contracts.vocabulary import ObservationStrength, RealizationVerificationScope


def realization_observation_from_payload(payload: dict[str, Any]) -> RealizationObservationDisclosure:
    """Restore one validated observation disclosure from persisted JSON."""

    model = RealizationObservationDisclosureModel.model_validate(payload)
    operating_system = model.operating_system
    return RealizationObservationDisclosure(
        address=model.address,
        field_path=model.field_path,
        domain=model.domain,
        requirement_kind=model.requirement_kind,
        verification_scope=RealizationVerificationScope(model.verification_scope),
        observation_strength=ObservationStrength(model.observation_strength),
        observed_value=model.observed_value,
        operating_system=(
            ObservedOperatingSystemIdentity(
                family=operating_system.family,
                distribution=operating_system.distribution,
                version=operating_system.version,
            )
            if operating_system is not None
            else None
        ),
        operation_id=model.operation_id,
        envelope_digest=model.envelope_digest,
        configuration_digest=model.configuration_digest,
        observer_version=model.observer_version,
        sequence=model.sequence,
        binding_verified=model.binding_verified,
    )
