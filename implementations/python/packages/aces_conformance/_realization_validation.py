"""Validation helpers for realization-honesty evidence."""

from __future__ import annotations

from aces_contracts.diagnostics import Diagnostic, Severity
from aces_contracts.planning import ProvisioningPlan
from aces_contracts.realization_envelope import (
    BackendRealizationEnvelopeModel,
    ConcernDisposition,
    ObservationStrength,
    RealizationConcern,
)
from aces_contracts.realization_observation import RealizationObservation

from ._realization_models import RealizationProbeEvidence, RealizationProbeRequest

_DOMAIN = "conformance"
_RESOURCE_CONCERNS: dict[str, frozenset[RealizationConcern]] = {
    "network": frozenset({RealizationConcern.TOPOLOGY, RealizationConcern.NETWORK}),
    "node": frozenset(
        {
            RealizationConcern.TOPOLOGY,
            RealizationConcern.ARCHITECTURE,
            RealizationConcern.IMAGE,
            RealizationConcern.RESOURCE_ALLOCATION,
            RealizationConcern.NETWORK,
            RealizationConcern.SERVICE,
            RealizationConcern.ACL,
        }
    ),
    "content-placement": frozenset({RealizationConcern.CONTENT_PLACEMENT}),
    "account-placement": frozenset({RealizationConcern.ACCOUNT_PLACEMENT}),
    "feature-binding": frozenset({RealizationConcern.FEATURE_BINDING}),
}
_STRENGTH_RANK = {
    ObservationStrength.NONE: 0,
    ObservationStrength.DRIVER_REPORTED: 1,
    ObservationStrength.DAEMON_OBSERVED: 2,
    ObservationStrength.GUEST_OBSERVED: 3,
}


def diagnostic(code: str, address: str, message: str) -> Diagnostic:
    """Return a sanitized conformance error diagnostic."""

    return Diagnostic(code=code, domain=_DOMAIN, address=address, message=message, severity=Severity.ERROR)


def required_strengths(
    envelope: BackendRealizationEnvelopeModel,
) -> dict[RealizationConcern, ObservationStrength]:
    """Return required observation strength by supported concern."""

    return {
        disclosure.concern: disclosure.observation_strength
        for disclosure in envelope.concerns
        if disclosure.disposition is not ConcernDisposition.UNSUPPORTED
    }


def operation_inventory_diagnostics(
    plan: ProvisioningPlan,
    evidence: RealizationProbeEvidence,
    strengths: dict[RealizationConcern, ObservationStrength],
) -> list[Diagnostic]:
    """Check exact operation accounting and expected-observation coverage."""

    expected_operations = {operation.address for operation in plan.actionable_operations}
    accounted = set(evidence.accounted_operations)
    diagnostics: list[Diagnostic] = []
    if accounted != expected_operations or set(evidence.changed_addresses) != expected_operations:
        diagnostics.append(
            diagnostic(
                "conformance.operation-accounting-incomplete",
                "runtime.provisioning.operations",
                "Every actionable provisioning operation must have exactly one terminal accounting result.",
            )
        )
    inventory = {(item.address, item.concern) for item in evidence.expected_observations}
    for operation in plan.actionable_operations:
        required = _RESOURCE_CONCERNS.get(operation.resource_type, frozenset()) & strengths.keys()
        if any((operation.address, concern) not in inventory for concern in required):
            diagnostics.append(
                diagnostic(
                    "conformance.observation-inventory-incomplete",
                    operation.address,
                    "The independent expected-observation inventory omits a required realization concern.",
                )
            )
    return diagnostics


def observation_diagnostics(
    request: RealizationProbeRequest,
    evidence: RealizationProbeEvidence,
    strengths: dict[RealizationConcern, ObservationStrength],
) -> list[Diagnostic]:
    """Check observation value, strength, binding, provenance, and freshness."""

    observed: dict[tuple[str, str, RealizationConcern], list[RealizationObservation]] = {}
    for item in evidence.observations:
        observed.setdefault((item.address, item.field_path, item.concern), []).append(item)
    diagnostics: list[Diagnostic] = []
    for expected in evidence.expected_observations:
        key = (expected.address, expected.field_path, expected.concern)
        candidates = observed.get(key, [])
        if len(candidates) != 1 or candidates[0].value != expected.value:
            diagnostics.append(
                diagnostic(
                    "conformance.observation-missing",
                    expected.address,
                    "A required addressed realization observation is missing, duplicated, or mismatched.",
                )
            )
            continue
        item = candidates[0]
        required = strengths.get(expected.concern, ObservationStrength.NONE)
        if _STRENGTH_RANK[item.source] < _STRENGTH_RANK[required]:
            diagnostics.append(
                diagnostic(
                    "conformance.observation-strength-insufficient",
                    expected.address,
                    "The realization observation is weaker than the configuration requires.",
                )
            )
        binding = (
            item.operation_id == expected.address
            and item.probe_digest == request.probe_digest
            and item.envelope_digest == request.envelope_digest
            and item.configuration_digest == request.configuration_digest
            and item.observer_version == request.observer_version
            and item.binding_verified
        )
        if not binding:
            diagnostics.append(
                diagnostic(
                    "conformance.observation-binding-invalid",
                    expected.address,
                    "The realization observation is not bound to this operation, probe, envelope, and observer.",
                )
            )
        if item.origin != "observed":
            diagnostics.append(
                diagnostic(
                    "conformance.observation-not-independent",
                    expected.address,
                    "Planned or echoed state cannot satisfy an independent realization observation.",
                )
            )
        if item.sequence is None or item.sequence <= evidence.baseline_sequence:
            diagnostics.append(
                diagnostic(
                    "conformance.observation-stale",
                    expected.address,
                    "The realization observation is not fresh for this probe execution.",
                )
            )
    return diagnostics


def transformation_diagnostics(evidence: RealizationProbeEvidence) -> list[Diagnostic]:
    """Reject all material transformations lacking executable governed evidence."""

    diagnostics: list[Diagnostic] = []
    for transformation in evidence.transformations:
        code = (
            "conformance.transformation-undisclosed"
            if not transformation.disclosed
            else "conformance.transformation-unverified"
        )
        diagnostics.append(
            diagnostic(
                code,
                transformation.address,
                "A material realization transformation lacks a governed executable rule and exact evidence.",
            )
        )
    return diagnostics
