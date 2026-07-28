"""Submission-admission diagnostics for the runtime control plane.

These helpers screen provisioning, orchestration, and evaluation plans before
``RuntimeControlPlane`` submits them, mirroring the async submission contract in
``control_plane.py``.
"""

from __future__ import annotations

from raes_backend_protocols.backend_manifest import BackendManifest
from raes_backend_protocols.domain_topology import domain_topology_plan_diagnostics
from raes_backend_protocols.service_materialization import service_materialization_plan_diagnostics
from raes_contracts.apparatus import (
    DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND,
    RUNTIME_REALIZATION_DOMAIN,
)
from raes_contracts.diagnostics import Diagnostic
from raes_contracts.planning import (
    EvaluationPlan,
    OrchestrationPlan,
    PlanOperation,
    ProvisioningPlan,
    RuntimeDomain,
    require_plan_operation_identity,
)
from raes_contracts.runtime_state import RuntimeSnapshot

_STATEFUL_ADMISSION_BY_RESOURCE_TYPE = {
    "generated-artifact": (
        "supports_generated_artifacts",
        "provisioner.generated-artifacts-unsupported",
        "generated artifacts",
    ),
    "persistent-volume": (
        "supports_persistent_volumes",
        "provisioner.persistent-volumes-unsupported",
        "persistent volumes",
    ),
}


def _submitted_plan_diagnostics(
    plan: ProvisioningPlan | OrchestrationPlan | EvaluationPlan,
    domain: RuntimeDomain,
    snapshot: RuntimeSnapshot,
    manifest: BackendManifest | None = None,
) -> list[Diagnostic]:
    admitted = set(snapshot.entries) | {operation.address for operation in plan.operations}
    diagnostics: list[Diagnostic] = []
    for operation in plan.operations:
        diagnostic = _submitted_operation_diagnostic(operation, domain, snapshot, admitted)
        if diagnostic is not None:
            diagnostics.append(diagnostic)
            break
    if not diagnostics and domain is RuntimeDomain.PROVISIONING and isinstance(plan, ProvisioningPlan):
        if manifest is None:
            raise ValueError("provisioning submission admission requires a backend manifest")
        stateful_diagnostic = _stateful_submission_diagnostic(plan, manifest)
        if stateful_diagnostic is not None:
            diagnostics.append(stateful_diagnostic)
        else:
            service_materialization_diagnostics = service_materialization_plan_diagnostics(
                plan,
                manifest.provisioner,
                manifest.realization_envelope,
            )
            if service_materialization_diagnostics:
                diagnostics.extend(service_materialization_diagnostics[:1])
                return diagnostics
            diagnostics.extend(
                domain_topology_plan_diagnostics(
                    plan,
                    snapshot=snapshot,
                    supported_domain_profiles=manifest.provisioner.supported_domain_profiles,
                )[:1]
            )
    return diagnostics


def _stateful_submission_diagnostic(
    plan: ProvisioningPlan,
    manifest: BackendManifest,
) -> Diagnostic | None:
    for operation in plan.operations:
        admission = _STATEFUL_ADMISSION_BY_RESOURCE_TYPE.get(operation.resource_type)
        if admission is None:
            continue
        capability_attribute, unsupported_code, resource_label = admission
        if not getattr(manifest.provisioner, capability_attribute):
            return Diagnostic(
                code=unsupported_code,
                domain="provisioning",
                address=operation.address,
                message=f"Provisioner does not support {resource_label}.",
            )
        exact_supported = any(
            declaration.domain == RUNTIME_REALIZATION_DOMAIN
            and DECLARED_CAPABILITY_MATCH_REQUIREMENT_KIND in declaration.supported_exact_requirement_kinds
            for declaration in manifest.realization_support
        )
        if not exact_supported:
            return Diagnostic(
                code="realization.unsupported-exact-requirement",
                domain="runtime-realization",
                address=operation.address,
                message=(
                    "Backend declares no exact realization support for the submitted "
                    f"{operation.resource_type} resource."
                ),
            )
    return None


def _submitted_operation_diagnostic(
    operation: PlanOperation,
    domain: RuntimeDomain,
    snapshot: RuntimeSnapshot,
    admitted: set[str],
) -> Diagnostic | None:
    diagnostic: Diagnostic | None = None
    address = f"runtime.control-plane.{domain.value}"
    try:
        require_plan_operation_identity(domain, operation.address, operation.resource_type)
    except ValueError:
        diagnostic = Diagnostic(
            code="runtime.plan-resource-incoherent",
            domain="runtime",
            address=address,
            message="Submitted plan operation disagrees with the endpoint resource identity.",
        )

    dependencies = {*operation.ordering_dependencies, *operation.refresh_dependencies}
    if diagnostic is None and dependencies - admitted:
        diagnostic = Diagnostic(
            code="runtime.plan-dependency-unresolved",
            domain="runtime",
            address=address,
            message="Submitted plan contains a dependency outside its operations and admitted snapshot.",
        )

    existing = snapshot.entries.get(operation.address)
    if (
        diagnostic is None
        and existing is not None
        and (existing.domain is not domain or existing.resource_type != operation.resource_type)
    ):
        diagnostic = Diagnostic(
            code="runtime.plan-resource-incoherent",
            domain="runtime",
            address=address,
            message="Submitted plan disagrees with the admitted snapshot resource identity.",
        )
    return diagnostic
