"""Runtime context and preflight for plan-owned realization authority."""

from __future__ import annotations

from dataclasses import dataclass

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


__all__ = ["_RealizationApplyContext", "_apply_authority_diagnostics"]
