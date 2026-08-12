"""Runtime evaluation for the compute-substrate realization concern."""

from __future__ import annotations

from typing import TYPE_CHECKING

from raes.explicitness import ExplicitnessClass
from raes_backend_protocols.capabilities import BackendManifest
from raes_contracts.bounded_domains import scalar_in_domain
from raes_contracts.diagnostics import Diagnostic, Severity
from raes_contracts.planning import ChangeAction, ProvisioningPlan
from raes_contracts.runtime_state import (
    RealizationObservationDisclosure,
    RealizationProvenanceEntry,
    RuntimeSnapshot,
)
from raes_contracts.vocabulary import observation_strength_satisfies

from .realization_runtime_common import (
    BACKEND_CONTRACT_INVALID,
    manifest_corroborates,
    matching_observation,
    realization_provenance_entry,
    silent_approximation_diagnostic,
)

if TYPE_CHECKING:
    from .realization import CompiledRealizationRequirement


def evaluate_compute_substrate(
    requirement: CompiledRealizationRequirement,
    declared_plan: ProvisioningPlan,
    returned_snapshot: RuntimeSnapshot,
    manifest: BackendManifest | None,
) -> tuple[Diagnostic | None, RealizationProvenanceEntry | None]:
    """Validate the observed substrate without consulting planned payload values."""

    op = next((item for item in declared_plan.operations if item.address == requirement.address), None)
    if op is None or op.action is ChangeAction.DELETE:
        return None, None
    if manifest is None or manifest.realization_envelope is None:
        return _evidence_diagnostic(requirement), None
    observation = matching_observation(requirement, returned_snapshot)
    if observation is None or not _binding_matches(observation, declared_plan, returned_snapshot, manifest):
        return _evidence_diagnostic(requirement), None
    if (
        requirement.required_observation_strength is not None
        and not observation_strength_satisfies(
            observation.observation_strength,
            requirement.required_observation_strength,
        )
    ) or not manifest_corroborates(requirement, observation, manifest):
        return _evidence_diagnostic(requirement), None
    if requirement.value_domain is not None and not scalar_in_domain(
        observation.observed_value,
        requirement.value_domain,
    ):
        return silent_approximation_diagnostic(requirement), None
    honoured = requirement.explicitness is ExplicitnessClass.EXACT
    return None, realization_provenance_entry(requirement, honoured)


def _binding_matches(
    observation: RealizationObservationDisclosure,
    declared_plan: ProvisioningPlan,
    returned_snapshot: RuntimeSnapshot,
    manifest: BackendManifest,
) -> bool:
    identity = declared_plan.realization_envelope
    carrier = manifest.realization_envelope
    claim = (
        next(
            (item for item in carrier.concerns if item.concern.value == "compute-substrate"),
            None,
        )
        if carrier is not None
        else None
    )
    operation = next(
        (item for item in declared_plan.operations if item.address == observation.address),
        None,
    )
    return bool(
        identity is not None
        and returned_snapshot.realization_envelope == identity
        and carrier is not None
        and carrier.identity == identity
        and claim is not None
        and claim.mechanism == observation.observed_value
        and operation is not None
        and (
            operation.action is ChangeAction.UNCHANGED
            or (declared_plan.operation_id is not None and observation.operation_id == declared_plan.operation_id)
        )
        and observation.envelope_digest == identity.digest
        and observation.configuration_digest == identity.configuration_digest
        and observation.binding_verified
    )


def _evidence_diagnostic(
    requirement: CompiledRealizationRequirement,
) -> Diagnostic:
    return Diagnostic(
        code=BACKEND_CONTRACT_INVALID,
        domain=requirement.domain,
        address=requirement.address,
        message=(
            "Backend returned no independently observed, operation- and apparatus-bound "
            f"compute substrate for '{requirement.field_path}'; plan values, handles, and "
            "configuration claims are not realization evidence."
        ),
        severity=Severity.ERROR,
    )


__all__ = ["evaluate_compute_substrate"]
