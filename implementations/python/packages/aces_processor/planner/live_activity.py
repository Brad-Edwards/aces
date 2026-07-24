"""Planner admission for compiled deterministic live-activity profiles."""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction

from aces_backend_protocols.capabilities import BackendManifest

from ..models import Diagnostic, RuntimeModel

_ADDRESS = "provision.live-activity"


def _unsupported(
    code: str,
    label: str,
    required: list[str],
    supported: frozenset[str],
) -> list[Diagnostic]:
    return [
        Diagnostic(
            code=code,
            domain="provisioning",
            address=_ADDRESS,
            message=f"Backend does not support live activity {label} '{value}'.",
        )
        for value in sorted(set(required) - supported)
    ]


def _quantity(value: object) -> Fraction:
    return Fraction(value.numerator, value.denominator)


def _fleet_budget_diagnostics(model: RuntimeModel) -> list[Diagnostic]:
    grouped: defaultdict[str, list[object]] = defaultdict(list)
    for profile in model.activity_profiles.values():
        for budget in profile.budget_envelopes:
            grouped[budget.dimension].append(budget)

    diagnostics: list[Diagnostic] = []
    for dimension, budgets in sorted(grouped.items()):
        envelope_keys = {
            (
                budget.unit,
                budget.window_seconds,
                _quantity(budget.fleet_capacity),
            )
            for budget in budgets
        }
        if len(envelope_keys) != 1:
            diagnostics.append(
                Diagnostic(
                    code="live-activity.fleet-envelope-conflict",
                    domain="provisioning",
                    address=_ADDRESS,
                    message=f"Selected live activity profiles disagree on the '{dimension}' fleet envelope.",
                )
            )
            continue
        fleet_capacity = next(iter(envelope_keys))[2]
        if sum((_quantity(budget.range_capacity) for budget in budgets), start=Fraction()) > fleet_capacity:
            diagnostics.append(
                Diagnostic(
                    code="live-activity.fleet-capacity-exceeded",
                    domain="provisioning",
                    address=_ADDRESS,
                    message=f"Selected live activity ranges exceed the '{dimension}' fleet capacity.",
                )
            )
    return diagnostics


def validate_live_activity_support(
    model: RuntimeModel,
    manifest: BackendManifest,
) -> list[Diagnostic]:
    if not model.activity_profiles:
        return []
    capability = manifest.live_activity
    if capability is None:
        return [
            Diagnostic(
                code="live-activity.capability-missing",
                domain="provisioning",
                address=_ADDRESS,
                message="Scenario requires live activity, but the backend declares no live-activity capability.",
            )
        ]
    diagnostics: list[Diagnostic] = []
    required_contracts = {"live-activity-profile-v1", "live-activity-occurrence-v1"}
    for contract_id in sorted(required_contracts - manifest.supported_contract_versions):
        diagnostics.append(
            Diagnostic(
                code="live-activity.contract-unsupported",
                domain="provisioning",
                address=_ADDRESS,
                message=f"Backend does not publish required live activity contract '{contract_id}'.",
            )
        )
    for profile in model.activity_profiles.values():
        diagnostics.extend(
            _unsupported(
                "live-activity.profile-unsupported",
                "contract profile",
                [profile.contract_profile],
                capability.supported_contract_profiles,
            )
        )
        diagnostics.extend(
            _unsupported(
                "live-activity.operation-unsupported",
                "operation profile",
                profile.required_operation_profiles,
                capability.supported_operation_profiles,
            )
        )
        diagnostics.extend(
            _unsupported(
                "live-activity.schedule-unsupported",
                "schedule profile",
                profile.required_schedule_profiles,
                capability.supported_schedule_profiles,
            )
        )
        diagnostics.extend(
            _unsupported(
                "live-activity.readback-unsupported",
                "readback profile",
                profile.required_readback_profiles,
                capability.supported_readback_profiles,
            )
        )
        diagnostics.extend(
            _unsupported(
                "live-activity.lifecycle-unsupported",
                "lifecycle profile",
                profile.required_lifecycle_profiles,
                capability.supported_lifecycle_profiles,
            )
        )
        diagnostics.extend(
            _unsupported(
                "live-activity.resource-dimension-unsupported",
                "resource dimension",
                profile.required_resource_dimensions,
                capability.supported_resource_dimensions,
            )
        )
        diagnostics.extend(
            _unsupported(
                "live-activity.dependency-kind-unsupported",
                "dependency kind",
                profile.required_dependency_kinds,
                capability.supported_dependency_kinds,
            )
        )
        for required, supported, code, label in (
            (
                profile.requires_bounded_retry,
                capability.supports_bounded_retry,
                "live-activity.bounded-retry-unsupported",
                "bounded retry",
            ),
            (
                profile.requires_generation_lifecycle,
                capability.supports_generation_lifecycle,
                "live-activity.generation-lifecycle-unsupported",
                "generation lifecycle",
            ),
            (
                profile.requires_participant_reservation,
                capability.supports_participant_reservation,
                "live-activity.participant-reservation-unsupported",
                "participant reservation",
            ),
            (
                profile.requires_readback_provenance,
                capability.supports_readback_provenance,
                "live-activity.readback-provenance-unsupported",
                "readback provenance",
            ),
        ):
            if required and not supported:
                diagnostics.append(
                    Diagnostic(
                        code=code,
                        domain="provisioning",
                        address=_ADDRESS,
                        message=f"Backend does not support required live activity {label}.",
                    )
                )
    diagnostics.extend(_fleet_budget_diagnostics(model))
    return diagnostics


__all__ = ["validate_live_activity_support"]
