"""Runtime context and preflight for plan-owned realization authority."""

from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import uuid4

from raes_backend_protocols.capabilities import BackendManifest
from raes_contracts.artifact_requirements import ArtifactAvailabilityContext
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.planning import ProvisioningPlan, RealizationAuthorityMode
from raes_processor.models import CompiledRealizationRequirement
from raes_processor.planner import realization_authority_diagnostics

from .diagnostics import _failure_diagnostic


@dataclass(frozen=True)
class _RealizationApplyContext:
    requirements: tuple[CompiledRealizationRequirement, ...] = ()
    plan: ProvisioningPlan | None = None
    manifest: BackendManifest | None = None
    artifact_availability: ArtifactAvailabilityContext | None = None


def _apply_authority_diagnostics(
    realization: _RealizationApplyContext,
    address: str,
) -> list[Diagnostic]:
    diagnostics = (
        realization_authority_diagnostics(realization.plan, realization.manifest)
        if realization.plan is not None
        else []
    )
    missing_manifest = (
        realization.plan is not None
        and not diagnostics
        and realization.manifest is None
        and any(entry.mode is not RealizationAuthorityMode.CLOSED for entry in realization.plan.realization_authority)
    )
    if missing_manifest:
        diagnostics = [
            _failure_diagnostic(
                "runtime.backend-contract-invalid",
                address,
                "Resolved realization authority requires the selected backend manifest.",
            )
        ]
    return diagnostics


def _bind_submitted_plan(
    args: tuple[object, ...],
    realization: _RealizationApplyContext,
    operation_id: str | None,
) -> tuple[tuple[object, ...], _RealizationApplyContext]:
    """Bind a per-apply operation id to the submitted plan and authority context."""

    submitted_plan = next((arg for arg in args if isinstance(arg, ProvisioningPlan)), None)
    if submitted_plan is None:
        return args, realization
    bound_plan = replace(
        submitted_plan,
        operation_id=operation_id or submitted_plan.operation_id or str(uuid4()),
    )
    bound_args = tuple(bound_plan if arg is submitted_plan else arg for arg in args)
    if realization.plan is None or realization.plan is submitted_plan:
        realization = replace(realization, plan=bound_plan)
    return bound_args, realization


__all__ = ["_RealizationApplyContext", "_apply_authority_diagnostics", "_bind_submitted_plan"]
