"""Neutral addressed realization-observation evidence DTOs."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from raes_contracts.addressing import require_compiled_address
from raes_contracts.bounded_domains import scalar_in_domain
from raes_contracts.controlled_vocabularies import validate_controlled_vocabulary_value
from raes_contracts.realization_envelope import ObservationStrength, RealizationConcern
from raes_contracts.vocabulary import RealizationVerificationScope


@dataclass(frozen=True)
class RealizationObservation:
    """One independently read realization fact with optional conformance binding.

    Backend-local observers can keep using the five core fields. Conformance
    requires every binding field below and rejects observations that omit them;
    the defaults preserve the existing non-conformance driver boundary.
    """

    address: str
    field_path: str
    concern: RealizationConcern
    source: ObservationStrength
    value: object
    operation_id: str | None = None
    probe_digest: str | None = None
    envelope_digest: str | None = None
    configuration_digest: str | None = None
    observer_version: str | None = None
    sequence: int | None = None
    origin: str = "observed"
    binding_verified: bool = False


@dataclass(frozen=True)
class RealizationObservationDisclosure:
    """Corroboration metadata for one realized inventory concern.

    Most concern disclosures remain value-free.  ``compute-substrate`` is a
    deliberately non-sensitive governed exception: its independently observed
    mechanism is needed to distinguish authored demand from actual selection.
    """

    address: str
    field_path: str
    domain: str
    requirement_kind: str
    verification_scope: RealizationVerificationScope
    observation_strength: ObservationStrength
    observed_value: str | None = None
    operation_id: str | None = None
    envelope_digest: str | None = None
    configuration_digest: str | None = None
    observer_version: str | None = None
    sequence: int | None = None
    binding_verified: bool = False

    def __post_init__(self) -> None:
        require_compiled_address(self.address)
        for field_name in ("field_path", "domain", "requirement_kind"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"RealizationObservationDisclosure.{field_name} must be non-empty")
        if not isinstance(self.verification_scope, RealizationVerificationScope):
            raise TypeError("verification_scope must be RealizationVerificationScope")
        if not isinstance(self.observation_strength, ObservationStrength):
            raise TypeError("observation_strength must be ObservationStrength")
        if self.observation_strength is ObservationStrength.NONE:
            raise ValueError("realization observation disclosure must provide non-none evidence")
        if self.requirement_kind == "compute-substrate":
            self._validate_compute_substrate_binding()
        elif self._has_execution_binding():
            raise ValueError("value-bearing execution bindings are reserved for compute-substrate disclosures")

    def _validate_compute_substrate_binding(self) -> None:
        if self.observed_value is None:
            raise ValueError("compute-substrate disclosure must carry its governed observed value")
        validate_controlled_vocabulary_value("compute-substrates", self.observed_value)
        self._validate_binding_text_fields()
        self._validate_binding_digests()
        if self.sequence is None or self.sequence < 0:
            raise ValueError("compute-substrate disclosure sequence must be non-negative")
        if not self.binding_verified:
            raise ValueError("compute-substrate disclosure must carry a verified execution binding")

    def _validate_binding_text_fields(self) -> None:
        for field_name in ("operation_id", "envelope_digest", "configuration_digest", "observer_version"):
            value = getattr(self, field_name)
            if value is None or not value.strip():
                raise ValueError(f"compute-substrate disclosure must carry {field_name}")

    def _validate_binding_digests(self) -> None:
        for field_name in ("envelope_digest", "configuration_digest"):
            if re.fullmatch(r"sha256:[a-f0-9]{64}", getattr(self, field_name)) is None:
                raise ValueError(f"compute-substrate disclosure {field_name} must be a sha256 digest")

    def _has_execution_binding(self) -> bool:
        return self.binding_verified or any(
            value is not None
            for value in (
                self.observed_value,
                self.operation_id,
                self.envelope_digest,
                self.configuration_digest,
                self.observer_version,
                self.sequence,
            )
        )


def bind_compute_substrate_observations(
    *,
    plan: object,
    observations: Sequence[RealizationObservation],
    envelope: object,
    previous: Sequence[RealizationObservationDisclosure] = (),
) -> tuple[RealizationObservationDisclosure, ...]:
    """Bind native substrate readback to one plan execution and apparatus.

    The backend provisioner performs this association after its driver returns
    independently read native state.  A handle or selected configuration alone
    cannot produce a disclosure.
    """

    _require_binding_inputs(plan, envelope, "substrate observation binding")
    non_substrate = tuple(item for item in previous if item.requirement_kind != "compute-substrate")
    if not plan.realization_constraints:
        return non_substrate
    if plan.operation_id is None or plan.realization_envelope != envelope.identity:
        raise ValueError("substrate observation binding requires matching operation and envelope identity")
    operations = {operation.address: operation for operation in plan.operations}
    native_by_address = _native_observations_by_address(observations)
    previous_by_address = {item.address: item for item in previous if item.requirement_kind == "compute-substrate"}
    disclosures = tuple(
        disclosure
        for constraint in plan.realization_constraints
        if (
            disclosure := _bound_compute_substrate_disclosure(
                constraint=constraint,
                operation=operations.get(constraint.address),
                native=native_by_address.get(constraint.address),
                prior=previous_by_address.get(constraint.address),
                plan=plan,
                envelope=envelope,
            )
        )
        is not None
    )
    return (*non_substrate, *disclosures)


def _native_observations_by_address(
    observations: Sequence[RealizationObservation],
) -> dict[str, RealizationObservation]:
    native = tuple(
        observation for observation in observations if observation.concern is RealizationConcern.COMPUTE_SUBSTRATE
    )
    by_address = {observation.address: observation for observation in native}
    if len(by_address) != len(native):
        raise ValueError("compute-substrate observations must identify unique addresses")
    return by_address


def _require_binding_inputs(plan: object, envelope: object, boundary: str) -> None:
    from raes_contracts.planning import ProvisioningPlan
    from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel

    if not isinstance(plan, ProvisioningPlan) or not isinstance(envelope, BackendRealizationEnvelopeModel):
        raise TypeError(f"{boundary} requires typed plan and envelope")


def _bound_compute_substrate_disclosure(
    *,
    constraint: object,
    operation: object,
    native: RealizationObservation | None,
    prior: RealizationObservationDisclosure | None,
    plan: object,
    envelope: object,
) -> RealizationObservationDisclosure | None:
    from raes_contracts.planning import ChangeAction, PlannedRealizationConstraint, PlanOperation, ProvisioningPlan
    from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel

    typed = all(
        (
            isinstance(constraint, PlannedRealizationConstraint),
            isinstance(operation, PlanOperation),
            isinstance(plan, ProvisioningPlan),
            isinstance(envelope, BackendRealizationEnvelopeModel),
        )
    )
    disclosure = None
    if typed and operation.action is not ChangeAction.DELETE:
        if (
            operation.action is ChangeAction.UNCHANGED
            and prior is not None
            and _prior_disclosure_reusable(prior, constraint, envelope)
        ):
            disclosure = prior
        elif native is not None and _native_compute_substrate_observation_valid(native, envelope):
            disclosure = RealizationObservationDisclosure(
                address=constraint.address,
                field_path=constraint.field_path,
                domain="runtime-realization",
                requirement_kind="compute-substrate",
                verification_scope=RealizationVerificationScope.PRESENCE,
                observation_strength=native.source,
                observed_value=native.value,
                operation_id=plan.operation_id,
                envelope_digest=envelope.digest,
                configuration_digest=envelope.configuration.configuration_digest,
                observer_version=native.observer_version,
                sequence=native.sequence,
                binding_verified=True,
            )
    return disclosure


def compute_substrate_readback_addresses(
    *,
    plan: object,
    envelope: object,
    previous: Sequence[RealizationObservationDisclosure] = (),
) -> tuple[str, ...]:
    """Return addresses that require fresh native substrate observation."""

    _require_binding_inputs(plan, envelope, "substrate readback selection")
    operations = {operation.address: operation for operation in plan.operations}
    previous_by_address = {item.address: item for item in previous if item.requirement_kind == "compute-substrate"}
    addresses: list[str] = []
    for constraint in plan.realization_constraints:
        operation = operations.get(constraint.address)
        if _requires_compute_substrate_readback(
            operation,
            previous_by_address.get(constraint.address),
            constraint,
            envelope,
        ):
            addresses.append(constraint.address)
    return tuple(addresses)


def _requires_compute_substrate_readback(
    operation: object,
    prior: RealizationObservationDisclosure | None,
    constraint: object,
    envelope: object,
) -> bool:
    from raes_contracts.planning import ChangeAction, PlanOperation

    if not isinstance(operation, PlanOperation) or operation.action is ChangeAction.DELETE:
        return False
    if operation.action is not ChangeAction.UNCHANGED or prior is None:
        return True
    return not _prior_disclosure_reusable(prior, constraint, envelope)


def missing_compute_substrate_readbacks(
    *,
    plan: object,
    observations: Sequence[RealizationObservation],
    envelope: object,
    previous: Sequence[RealizationObservationDisclosure] = (),
) -> tuple[str, ...]:
    """Return required addresses without a valid fresh native observation."""

    required = set(
        compute_substrate_readback_addresses(
            plan=plan,
            envelope=envelope,
            previous=previous,
        )
    )
    observed = {item.address for item in observations if _native_compute_substrate_observation_valid(item, envelope)}
    return tuple(sorted(required - observed))


def _prior_disclosure_reusable(
    disclosure: RealizationObservationDisclosure,
    constraint: object,
    envelope: object,
) -> bool:
    from raes_contracts.planning import PlannedRealizationConstraint
    from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel

    if not isinstance(constraint, PlannedRealizationConstraint) or not isinstance(
        envelope, BackendRealizationEnvelopeModel
    ):
        return False
    if (
        disclosure.field_path != constraint.field_path
        or disclosure.envelope_digest != envelope.digest
        or disclosure.configuration_digest != envelope.configuration.configuration_digest
    ):
        return False
    return constraint.value_domain is None or scalar_in_domain(disclosure.observed_value, constraint.value_domain)


def _native_compute_substrate_observation_valid(
    observation: RealizationObservation,
    envelope: object,
) -> bool:
    from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel

    return bool(
        isinstance(envelope, BackendRealizationEnvelopeModel)
        and isinstance(observation.value, str)
        and observation.source is not ObservationStrength.NONE
        and observation.envelope_digest == envelope.digest
        and observation.configuration_digest == envelope.configuration.configuration_digest
        and observation.observer_version
        and observation.sequence is not None
        and observation.sequence >= 0
        and observation.binding_verified
    )


__all__ = [
    "RealizationObservation",
    "RealizationObservationDisclosure",
    "bind_compute_substrate_observations",
    "compute_substrate_readback_addresses",
    "missing_compute_substrate_readbacks",
]
