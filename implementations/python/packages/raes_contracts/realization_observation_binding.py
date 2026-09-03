"""Execution-binding predicates for independently observed realization facts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from raes_contracts.realization_envelope import ObservationStrength

if TYPE_CHECKING:
    from raes_contracts.planning import ProvisioningPlan
    from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel
    from raes_contracts.realization_observation import RealizationObservation


def operating_system_observation_binding_valid(
    observation: RealizationObservation,
    plan: ProvisioningPlan,
    envelope: BackendRealizationEnvelopeModel,
) -> bool:
    """Return whether a guest OS observation is bound to this operation."""

    return bool(
        observation.source is ObservationStrength.GUEST_OBSERVED
        and observation.operation_id == plan.operation_id
        and observation.envelope_digest == envelope.digest
        and observation.configuration_digest == envelope.configuration.configuration_digest
        and observation.observer_version
        and observation.sequence is not None
        and observation.sequence >= 0
        and observation.binding_verified
    )
